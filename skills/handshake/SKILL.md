---
name: handshake
description: 多家大模型统一接入。当需要在 Ark（豆包）、DeepSeek、OpenAI 或任意 OpenAI 兼容本地服务之间选一家、探一家能不能用、或新加一家供应商时使用。握手返回四态两比特而非布尔。
---

# handshake

一个接口，接通多家。输入 `{"messages"}`，输出 `{"text"}`。零依赖，只用 Python 标准库。

## 什么时候用它

- 要跑一次“到底哪家能用”的实测，而不是凭记忆下结论。
- 要接一个新供应商，而又不想动调用方代码。
- 要在本机服务（llama.cpp / vLLM / Ollama / 自研内核）和云 API 之间做归一。

## 三个入口

```bash
python hello.py --ping all              # 逐家握手，出四态表
python hello.py --ping deepseek,local   # 只测这几家
python hello.py --say "你好" --only local   # 指定一家说一句
python plugin.py                        # 只看插件清单（内置 + plugins/）
python plugin_check.py                  # 校验 plugins/*.json，坏文件单拎出来
```

## 四态两比特（核心口径）

| 位 | 含义 | 处置 |
|---|---|---|
| `01` | 通，≤ `SLOW_MS`（默认 8000ms） | 进候选 |
| `10` | 通但慢/贵/不稳 | 降级，排到后面 |
| `00` | 超时 / 429 / 空回复 / 5xx | **只重试一次** |
| `11` | 401/403/404、连不上、缺钥匙、缺模型名 | 排除，条件改变前不再问 |

两条不能违反的：

1. `11` 不是“这次失败”，是“不必再开始”。它连 `chat()` 都没进过。把它当一个可以重试的 `False`，等于每次都为已知不通的那家付一笔延迟。
2. `00` 才允许重试，而且只一次。第二次仍不定就换下一家，不要无限探。

## 调用方长什么样

```python
from plugin import all_adapters_with_plugins

for a in all_adapters_with_plugins():
    if a.ping()["state"] == "01":
        return a.chat(messages)
```

## 加一家 = 一个 json

`plugins/<名>.json`，只有 `name` 和 `base_url` 必填。同名插件会顶掉内置同名适配器。

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

插件目录可以用 `HANDSHAKE_PLUGINS` 指到别处；钥匙可以用环境变量、`keys.json`，或插件里的 `key_file`（明文文件，只适合本机服务）。

## 三个坑

1. **探针不开思考档。** 心跳、自启动检查这类高频低价值调用，默认关思考；传了 `extra={"thinking": {"type": "enabled"}}` 会成倍增加 token 和延迟。
2. **钥匙不下盘到仓库。** `keys.json` 不进 Git；进日志的只有状态位、耗时和备注，不回显任何钥匙。
3. **别跨端口直连。** 本地服务最好走同源代理；从前端的 fetch 直指另一个端口，往往请求压根没发出去，却被当成“服务挂了”。

## 边界

这个技能只负责：统一形状、判状态、挑第一家 `01`。不做提示词工程，不做路由策略以外的编排，不替你做预算。
