---
description: 加一家新供应商：只丢一个 plugins/*.json，不改代码
argument-hint: <名> <base_url> [model]
allowed-tools: Bash, Write
---

按 `plugins/` 的既有格式新增一家，只有 `name` 和 `base_url` 必填，其余缺省按基类 `base.py` 的默认值。

1. 振 `plugins/deepseek.json` 的形状，写 `plugins/<名>.json`：

```json
{
  "name": "moonshot",
  "label": "月之暗面",
  "base_url": "https://api.moonshot.cn/v1",
  "env_key": "MOONSHOT_API_KEY",
  "env_model": "MOONSHOT_MODEL",
  "model": "moonshot-v1-8k",
  "timeout": 60
}
```

2. 校验：`python plugin_check.py`。坏文件不会被加载，也不会抛错 —— 但你会看到它被单拎出来。
3. 确认状态位：`python hello.py --ping <名>`。没配钥匙就是 `11 隔离`，这是正确结果，不是 bug。

规则：同名插件会顶掉内置同名适配器（内置在前，插件在后，按文件名排序）。想改 OpenAI 的默认模型，写个 `plugins/openai.json` 覆盖就行，不用动一行代码。
