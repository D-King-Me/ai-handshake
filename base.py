# -*- coding: utf-8 -*-
"""ai-handshake —— 一个接口，接通多家大模型。

口径：外面各家（方舟 / DeepSeek / OpenAI / 任意 OpenAI 兼容的本地服务）
全部当成同一个东西看 —— 输入 {"messages"}，输出 {"text"}。
换一家只是换地址和钥匙，不改调用方代码。

零依赖：只用 Python 标准库，不装任何 SDK。

    from base import all_adapters
    a = [x for x in all_adapters() if x.name == "deepseek"][0]
    print(a.chat([{"role": "user", "content": "你好"}]))

开源许可：MIT
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS_FILE = Path(os.environ.get("HANDSHAKE_KEYS", HERE / "keys.json"))

# ---- 四态两比特：先定状态，再决定要不要算 ----
STATE_OK = "01"        # 通了，可用
STATE_SLOW = "10"      # 通了但慢/贵/不稳，降级排在后面
STATE_UNSURE = "00"    # 不确定：超时、限流、空回复，重试一次再定
STATE_ISOLATED = "11"  # 隔离：没钥匙、地址错、被墙，直接排除，不算它

SLOW_MS = 8000


def load_keys() -> dict:
    """keys.json 存在就读，读不到就当空，绝不抛错。"""
    try:
        with open(KEYS_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class Adapter(object):
    """一家 = 一个子类。子类只改四处：name / label / base_url / (env_key, model)。"""

    name = "base"
    label = "基类"
    env_key = ""      # 钥匙的读取来源名，例如 ARK_API_KEY
    env_model = ""    # 模型名/端点号可被环境变量覆盖
    base_url = ""
    model = ""
    timeout = 60
    key_file = None   # 可选：明文钥匙文件路径（例如服务器上的 secrets 目录）

    def __init__(self):
        self._keys = load_keys()
        if self.env_model:
            self.model = os.environ.get(self.env_model, self.model)

    # ---------- 钥匙 ----------
    def key(self) -> str:
        k = os.environ.get(self.env_key) if self.env_key else ""
        if not k:
            k = str(self._keys.get(self.name, "") or "")
        if not k and self.key_file:
            try:
                k = Path(self.key_file).read_text(encoding="utf-8").strip()
            except Exception:
                k = ""
        return k.strip()

    def key_hint(self) -> str:
        if not self.env_key:
            return "本机服务，无钥匙要求"
        return "环境变量 %s 或 keys.json[\"%s\"]" % (self.env_key, self.name)

    # ---------- 一次问答 ----------
    def chat(self, messages, temperature=0.3, max_tokens=512, extra=None):
        """extra 用来透传厂商私有参数，例如 {"thinking": {"type": "enabled"}}。"""
        if not self.base_url:
            raise RuntimeError("base_url 未设置")
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if extra:
            body.update(extra)

        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        k = self.key()
        if k:
            req.add_header("Authorization", "Bearer " + k)

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
        data = json.loads(raw)
        choices = data.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return (msg.get("content") or "").strip()

    # ---------- 握手 ----------
    def ping(self, probe="只回两个字：收到"):
        row = {"name": self.name, "label": self.label, "model": self.model,
               "state": STATE_ISOLATED, "ms": 0, "note": ""}

        if self.env_key and not self.key():
            row["note"] = "缺钥匙（%s）" % self.key_hint()
            return row
        if not self.model:
            row["note"] = "缺模型名/端点号（用环境变量补）"
            return row

        t0 = time.time()
        try:
            text = self.chat([{"role": "user", "content": probe}], max_tokens=32)
            row["ms"] = int((time.time() - t0) * 1000)
            if not text:
                row["state"] = STATE_UNSURE
                row["note"] = "回空"
            elif row["ms"] > SLOW_MS:
                row["state"] = STATE_SLOW
                row["note"] = "慢：%dms" % row["ms"]
            else:
                row["state"] = STATE_OK
                row["note"] = text[:40]
        except urllib.error.HTTPError as e:
            row["ms"] = int((time.time() - t0) * 1000)
            code = getattr(e, "code", 0)
            row["state"] = STATE_ISOLATED if code in (401, 403, 404) else STATE_UNSURE
            row["note"] = "HTTP %s" % code
        except Exception as e:
            row["ms"] = int((time.time() - t0) * 1000)
            msg = str(e) or e.__class__.__name__
            if "timed out" in msg.lower() or "timeout" in msg.lower():
                row["state"] = STATE_UNSURE
                row["note"] = "超时"
            else:
                row["state"] = STATE_ISOLATED
                row["note"] = msg[:60]
        return row


class ArkAdapter(Adapter):
    """火山方舟（豆包）。模型名或端点号必须自己填。"""
    name = "ark"
    label = "豆包方舟"
    env_key = "ARK_API_KEY"
    env_model = "ARK_MODEL"       # 例如 ep-2026xxxx 或模型名
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model = ""


class DeepSeekAdapter(Adapter):
    name = "deepseek"
    label = "DeepSeek 官方"
    env_key = "DEEPSEEK_API_KEY"
    env_model = "DEEPSEEK_MODEL"
    base_url = "https://api.deepseek.com/v1"
    model = "deepseek-chat"


class OpenAIAdapter(Adapter):
    name = "openai"
    label = "OpenAI"
    env_key = "OPENAI_API_KEY"
    env_model = "OPENAI_MODEL"
    base_url = "https://api.openai.com/v1"
    model = "gpt-4o-mini"


class LocalAdapter(Adapter):
    """任何 OpenAI 兼容的本地服务（llama.cpp / vLLM / Ollama / 自研内核）。

    LOCAL_BASE_URL=http://127.0.0.1:8080/v1
    LOCAL_MODEL=qwen2.5-1.5b
    """
    name = "local"
    label = "本机兼容服务"
    env_key = ""
    env_model = "LOCAL_MODEL"
    base_url = os.environ.get("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1")
    model = "qwen2.5-1.5b"
    timeout = 40


REGISTRY = [ArkAdapter, DeepSeekAdapter, OpenAIAdapter, LocalAdapter]


def all_adapters():
    return [cls() for cls in REGISTRY]
