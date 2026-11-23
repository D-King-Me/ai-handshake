# -*- coding: utf-8 -*-
"""插件体检：只校验 plugins/*.json 的形状，不真的发请求。

    python plugin_check.py            # 只看形状
    python plugin_check.py --ping     # 形状通过后再逐家握手

退出码：0 全绿；1 有坏文件或重名；2 目录不存在。
坏文件永远不会被加载，也不会抛错，但得让人看见它。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from base import REGISTRY  # noqa: E402

REQUIRED = ("name", "base_url")
KNOWN = ("name", "label", "base_url", "env_key", "env_model", "model",
         "timeout", "key_file")

# 这几类备注算“硬伤”：文件会被拒载，所以不能只提示不计数。
FATAL_PREFIX = ("缺必填", "JSON", "顶层", "base_url 不是", "timeout")


def check_one(path: Path):
    """返回 (ok, name, notes)。不抛错。"""
    notes = []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return False, "-", ["JSON 解析失败：%s" % e]
    if not isinstance(data, dict):
        return False, "-", ["顶层不是对象"]

    for k in REQUIRED:
        if not str(data.get(k) or "").strip():
            notes.append("缺必填字段 %s" % k)
    for k in data:
        if k not in KNOWN:
            notes.append("未知字段 %s（会被忽略）" % k)
    url = str(data.get("base_url") or "")
    if url and not url.startswith("http"):
        notes.append("base_url 不是 http(s) 开头")
    try:
        if int(data.get("timeout") or 60) <= 0:
            notes.append("timeout 必须为正整数")
    except Exception:
        notes.append("timeout 不是整数")

    name = str(data.get("name") or "-")
    ok = not any(n.startswith(FATAL_PREFIX) for n in notes)
    return ok, name, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ping", action="store_true", help="形状通过后逐家握手")
    ap.add_argument("--dir", default=os.environ.get("HANDSHAKE_PLUGINS", str(HERE / "plugins")))
    args = ap.parse_args()

    d = Path(args.dir)
    if not d.is_dir():
        print("插件目录不存在：%s（不影响内置四家）" % d)
        return 2

    builtin = {getattr(c, "name", "") for c in REGISTRY}
    files = sorted(d.glob("*.json"))
    print("目录：%s   文件：%d   内置：%s" % (d, len(files), ", ".join(sorted(builtin))))
    print("-" * 72)
    print("%-22s %-12s %-6s %s" % ("文件", "name", "结果", "备注"))
    print("-" * 72)

    bad = 0
    seen = {}
    for f in files:
        ok, name, notes = check_one(f)
        if name != "-":
            seen.setdefault(name, []).append(f.name)
        if name in builtin:
            notes.append("顶掉内置同名适配器（这是设计内的）")
        status = "通过" if ok else "坏文件"
        if not ok:
            bad += 1
        print("%-22s %-12s %-6s %s" % (f.name[:22], name[:12], status, "；".join(notes) or "-"))

    dup = {k: v for k, v in seen.items() if len(v) > 1}
    if dup:
        bad += len(dup)
        for k, v in dup.items():
            print("重名：%s 出现在 %s（只会加载一份）" % (k, "、".join(v)))

    print("-" * 72)
    print("总%d 个文件，坏/重名 %d。" % (len(files), bad))

    if args.ping and files:
        from plugin import all_adapters_with_plugins
        print()
        for a in all_adapters_with_plugins(d):
            r = a.ping()
            print("%-14s %-6s %-6s %s" % (r["label"][:14], r["state"], r["ms"], r["note"]))

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
