# 当插件用 / Install as a plugin

这个仓库现在不只是一种库，也可以直接装成一个插件：三个斜杠命令 + 一个技能。

## 装法一：插件市场（Claude Code）

```bash
/plugin marketplace add D-King-Me/ai-handshake
/plugin install ai-handshake@ai-handshake
```

装完就有：

| 入口 | 作用 |
|---|---|
| `/handshake-ping` | 逐家握手，出四态表（`01` `10` `00` `11`） |
| `/handshake-say` | 指定一家说一句话，拿回原样回复 |
| `/handshake-add` | 加一家新供应商（只新增一个 `plugins/*.json`） |
| `skills/handshake` | 遇到多模型选家、探状态、接新家时自动参照的口径 |

## 装法二：拷进本地插件目录

```bash
git clone https://github.com/D-King-Me/ai-handshake.git
export HANDSHAKE_KEYS="$PWD/ai-handshake/keys.json"
```

插件实质就四个文件：`.claude-plugin/plugin.json`、`commands/*.md`、`skills/handshake/SKILL.md`。不用任何构建，没有依赖安装这一步。

## 装法三：只用命令行，不装插件

```bash
python hello.py --ping all
python hello.py --say "你好" --only local
python plugin.py
python plugin_check.py
```

## 钥匙放哪

按优先级：环境变量 → `keys.json` → 插件里的 `key_file`（明文文件，只适合本机服务）。

| 家 | 环境变量 | 备注 |
|---|---|---|
| ark（豆包方舟） | `ARK_API_KEY` / `ARK_MODEL` | 模型名或端点号必须自己填 |
| deepseek | `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` | 默认 `deepseek-chat` |
| openai | `OPENAI_API_KEY` / `OPENAI_MODEL` | 默认 `gpt-4o-mini` |
| local | `LOCAL_BASE_URL` / `LOCAL_MODEL` | 默认 `http://127.0.0.1:8080/v1` |

没配钥匙不报错，只标 `11 隔离`。

## 体检

```bash
python plugin_check.py          # 只校验 plugins/*.json 的形状
python plugin_check.py --ping   # 形状过了再逐家握手
```

退出码：`0` 全绿、`1` 有坏文件或重名、`2` 插件目录不存在。坏文件不会被加载，也不会抛错 —— 但会在这里被单拎出来。

## 自己改一份

```json
{
  "name": "mine",
  "label": "我家模型",
  "base_url": "https://example.com/v1",
  "env_key": "MINE_API_KEY",
  "model": "my-model"
}
```

丢进 `plugins/` 就生效，重启即可，不改代码。同名插件顶掉内置（这是设计内的）。
