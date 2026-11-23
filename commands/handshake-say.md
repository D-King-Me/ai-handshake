---
description: 用指定的那家模型说一句话，拿回原样回复
argument-hint: <家> <要说的话>
allowed-tools: Bash
---

参数：`$ARGUMENTS` 的第一段是家名（`ark` / `deepseek` / `openai` / `local`，或 `plugins/` 里任意插件的 `name`），其余全部是要说的话。

1. 跑：`python hello.py --say "<要说的话>" --only <家>`
2. 回复原文照贴，不润色、不总结。空回复要明说「空」，不能算成功。
3. 报缺钥匙时，只指出该家的环境变量名（如 `DEEPSEEK_API_KEY`），不解释第二遍。

注意：这是探针级调用，默认不开思考/高推理档（`extra` 里别传 `thinking`）。开了会显著加钱加延迟。
