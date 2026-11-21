# ai-handshake · 一个接口接通多家大模型

把方舟（豆包）、DeepSeek、OpenAI、以及任何 OpenAI 兼容的本地服务（llama.cpp / vLLM / Ollama / 自研内核）**统一成一个形状**：

```
输入 {"messages"}  →  输出 {"text"}
```

换一家只换地址和钥匙，不改调用方一行代码。**零依赖，只用 Python 标准库**，不装任何 SDK。

> 本项目来自 恒道AI 的握手层。它存在的理由很朴素：要接活、要接手别人抛出的未解异常，第一步得先让别人家的大模型能跟本机对上话。

---

## 为什么不是又一个 SDK 封装

大多数"多模型客户端"的做法是：装五个 SDK，写五套分支，每加一家改一遍代码。这个项目反过来 —— **把差异压到子类里的四个字段**（`name` / `label` / `base_url` / `env_key`+`model`），其余全部共用。

## 四态两比特：先定状态，再决定要不要算

握手不返回"成功/失败"，返回一个**状态位**：

| 位 | 含义 | 处置 |
|---|---|---|
| `01` | 通了 | 可用，进链路候选 |
| `10` | 通了但慢/贵/不稳 | 降级，排到后面 |
| `00` | 不确定（超时、限流、空回复） | 重试一次，仍不行就换下一家 |
| `11` | 隔离（没钥匙、地址错、被墙） | 直接排除，**不算它** |

这套口径的意义在于：**先判状态，再决定算不算**。被判 `11` 的那家，一次请求都不会发出去 —— 省下的不是算力，是"根本不必开始的那一次"。

详见 [`docs/STATE.md`](docs/STATE.md)。

## 用法

```bash
python hello.py --ping all          # 逐家握手，出结果表
python hello.py --ping deepseek     # 只测一家
python hello.py --say "你好" --only local
```

输出示例：

```
家             模型                   状态   ms     备注
----------------------------------------------------------------
豆包方舟       ep-2026xxxx           通     820    收到
DeepSeek 官方  deepseek-chat         通     965    收到
OpenAI         gpt-4o-mini           隔离   0      缺钥匙（环境变量 OPENAI_API_KEY 或 keys.json["openai"]）
本机兼容服务   qwen2.5-1.5b          隔离   0      [Errno 111] Connection refused
----------------------------------------------------------------
可用 2 家，隔离 2 家。
```

## 配钥匙（三种放法，按优先级）

1. **环境变量**（推荐）
   ```bash
   export ARK_API_KEY=...        # 方舟
   export ARK_MODEL=ep-2026xxxx  # 方舟必须自己填模型名或端点号
   export DEEPSEEK_API_KEY=...
   export OPENAI_API_KEY=...
   export LOCAL_BASE_URL=http://127.0.0.1:8080/v1
   export LOCAL_MODEL=qwen2.5-1.5b
   ```
2. **`keys.json`** —— 照 `keys.example.json` 改名，填：`{"ark": "...", "deepseek": "...", "openai": ""}`
3. **明文文件兜底** —— 在子类里设 `key_file = "/path/to/key.txt"`，适合只在本机跑的服务。

没配钥匙的那家不会报错，只会标成 `11 隔离`。

## 加一家新的

```python
class MyProvider(Adapter):
    name = "mine"
    label = "我家模型"
    env_key = "MINE_API_KEY"
    env_model = "MINE_MODEL"
    base_url = "https://example.com/v1"
    model = "my-model"
```

放进 `REGISTRY` 就完事。

## 透传厂商私有参数

有些厂商有私有开关（例如开"思考"）。用 `extra` 透传，不要改基类：

```python
text = a.chat(messages, extra={"thinking": {"type": "enabled"}})
```

**注意**：开思考/高推理档会显著增加 token 消耗与延迟。做探针、心跳、自启动检查这类高频低价值调用时，**默认关掉**。

## 自检与日志

每次握手写一行 JSON 到 `日志/握手记录.jsonl`（`keys.json` 里没有的东西一律不入日志、不回显）。

## 许可

MIT。见 [LICENSE](LICENSE)。

---

## English

`ai-handshake` is a zero-dependency, stdlib-only adapter that talks to Ark (Doubao), DeepSeek, OpenAI, and any OpenAI-compatible local server through a single `chat(messages) -> text` interface. Providers are declared as subclasses with four fields, so adding one costs a class, not a refactor.

Handshakes return a two-bit state (`01` ok, `10` slow, `00` unsure, `11` isolated) instead of a boolean, so an isolated provider is never even called.

MIT licensed.
