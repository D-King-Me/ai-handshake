# -*- coding: utf-8 -*-
"""插件层：加一家模型不用改代码，往 plugins/ 丢一个 json 就行。

插件格式：

    {
      "name": "moonshot",
      "label": "月之暗面",
      "base_url": "https://api.moonshot.cn/v1",
      "env_key": "MOONSHOT_API_KEY",
      "env_model": "MOONSHOT_MODEL",
      "model": "moonshot-v1-8k",
      "timeout": 60,
      "key_file": null
    }

只有 name 和 base_url 是必填，其余缺省按基类默认值。
同名插件会顶掉内置同名适配器（内置在前，插件在后，按文件名排序）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from base import Adapter, all_adapters

PLUGIN_DIR = Path(os.environ.get("HANDSHAKE_PLUGINS",
                                Path(__file__).resolve().parent / "plugins"))

FIELDS = ("name", "label", "base_url", "env_key", "env_model", "model", "timeout")


def spec_from_file(path) -> dict | None:
    """读一个插件文件，返回规格字典；坏文件返回 None，不抛错。"""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if not data.get("name") or not data.get("base_url"):
        return None
    spec = {k: data[k] for k in FIELDS if data.get(k) not in (None, "")}
    if data.get("key_file"):
        spec["key_file"] = str(data["key_file"])
    return spec


def adapter_from_spec(spec: dict) -> Adapter:
    """把规格字典变成一个可以直接用的适配器实例。"""
    attrs = dict(spec)
    attrs.setdefault("label", spec["name"])
    attrs.setdefault("timeout", 60)
    attrs.setdefault("env_key", "")
    attrs.setdefault("env_model", "")
    cls = type("Plugin_" + str(spec["name"]), (Adapter,), attrs)
    return cls()


def load_plugins(plugin_dir=None) -> list:
    d = Path(plugin_dir or PLUGIN_DIR)
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("*.json")):
        spec = spec_from_file(f)
        if spec:
            out.append(adapter_from_spec(spec))
    return out


def all_adapters_with_plugins(plugin_dir=None) -> list:
    """内置几家 + 插件目录里的插件。同名时插件优先。"""
    plugins = load_plugins(plugin_dir)
    names = {p.name for p in plugins}
    return [a for a in all_adapters() if a.name not in names] + plugins


if __name__ == "__main__":
    for a in all_adapters_with_plugins():
        print("%-6s %-14s %s  model=%s" % (a.name, a.label, a.base_url, a.model or "-"))
