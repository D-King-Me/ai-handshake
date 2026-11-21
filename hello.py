# -*- coding: utf-8 -*-
"""握手自检脚本。

    python hello.py --ping all
    python hello.py --ping deepseek,local
    python hello.py --say "帮我看看这个 null 是什么" --only deepseek

结果写进 日志/握手记录.jsonl，一行一次。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from base import STATE_ISOLATED, STATE_OK, all_adapters, load_keys  # noqa: E402

LOG_DIR = os.path.join(HERE, "日志")
LOG_FILE = os.path.join(LOG_DIR, "握手记录.jsonl")

STATE_TEXT = {"01": "通  ", "10": "慢  ", "00": "不确定", "11": "隔离 "}


def pick(adapters, wanted):
    wanted = [w.strip().lower() for w in (wanted or "all").split(",") if w.strip()]
    if not wanted or "all" in wanted:
        return adapters
    return [a for a in adapters if a.name.lower() in wanted]


def write_log(rows):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            for r in rows:
                r = dict(r)
                r["ts"] = stamp
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return LOG_FILE
    except Exception as e:
        return "日志写入失败：%s" % e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ping", default="all")
    ap.add_argument("--say", default="")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    adapters = pick(all_adapters(), args.only or args.ping)
    rows = []

    if args.say:
        for a in adapters:
            if a.env_key and not a.key():
                print("[%s] 跳过：缺钥匙" % a.label)
                continue
            try:
                text = a.chat([{"role": "user", "content": args.say}])
                print("[%s] %s" % (a.label, text or "（空）"))
                rows.append({"name": a.name,
                             "state": STATE_OK if text else "00",
                             "ms": 0, "note": text[:80]})
            except Exception as e:
                print("[%s] 失败：%s" % (a.label, e))
                rows.append({"name": a.name, "state": STATE_ISOLATED,
                             "ms": 0, "note": str(e)[:60]})
    else:
        keys = load_keys()
        print("keys.json：%s" % ("已读到 %d 家" % len(keys) if keys else "没有（可只用环境变量）"))
        print("-" * 68)
        print("%-14s %-22s %-6s %-6s %s" % ("家", "模型", "状态", "ms", "备注"))
        print("-" * 68)
        for a in adapters:
            r = a.ping()
            rows.append(r)
            model = r["model"] or "-"
            print("%-14s %-22s %-6s %-6s %s" % (
                r["label"], model[:22], STATE_TEXT.get(r["state"], r["state"]),
                r["ms"], r["note"]))
        print("-" * 68)
        ok = [r for r in rows if r["state"] == STATE_OK]
        bad = [r for r in rows if r["state"] == STATE_ISOLATED]
        print("可用 %d 家，隔离 %d 家。" % (len(ok), len(bad)))
        if bad:
            print("隔离的：%s" % "、".join(r["label"] for r in bad))

    print("日志：%s" % write_log(rows))


if __name__ == "__main__":
    main()
