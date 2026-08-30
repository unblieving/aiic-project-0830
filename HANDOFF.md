# HANDOFF

## 已完成

- P0 产品文档落地：`SPEC.md`、`PLAN.md`、`README.md`。
- Python 标准库 HTTP 服务：`server.py`。
- 核心状态机：setup、问题、卡住、L1/L2/L3、强制完整重答、穿插题、变式重测、结果。
- DeepSeek-compatible API 客户端：`recall_trainer/llm.py`。
- Prompt 集中管理：`recall_trainer/prompts.py`。
- 前端单页训练界面：`static/index.html`、`static/styles.css`、`static/app.js`。
- Mock fallback：没有 `DEEPSEEK_API_KEY` 或 API 调用失败时仍可完整 Demo。
- 单元测试覆盖核心状态机、API 行为、DeepSeek fallback。

## 尚未完成

- 尚未在服务器 `43.132.173.100` 上实际部署。
- 尚未录制 3 分钟 Demo 视频。
- 尚未撰写 Product Memo。
- 未做 P1/P2 功能。

## 不要修改

- 不要把 DeepSeek API 换成 OpenAI。
- 不要新增数据库、登录、Dashboard、评分系统、语音/视频等 P2 功能。
- 不要让 LLM 接管训练状态机。
- 不要把 `recall_trainer/prompts.py` 中的 Recall Coach 规则散落到前端。

## 已知问题

- 结果判定采用最小可演示策略：用户在 retest 提交非空回答即记为 L0。
- LLM 只生成首题和变式重测题；穿插题保留确定性题库，保证 Demo 稳定。
- 本地如果直接绑定 80 端口失败，可用 8080 测试；服务器部署时仍建议暴露 80。

## 启动方式

PowerShell:

```powershell
cd C:\Users\Lenovo\aiic-project-0830
$env:DEEPSEEK_API_KEY="your_deepseek_key"
python server.py
```

本地临时测试:

```powershell
cd C:\Users\Lenovo\aiic-project-0830
$env:PORT="8080"
$env:DEEPSEEK_API_KEY=""
python server.py
```

## 验证方式

```powershell
cd C:\Users\Lenovo\aiic-project-0830
python -m unittest discover -s tests -v
```

手动 Demo 路径:

1. 选择后端开发、计算机网络、操作系统。
2. 开始训练。
3. 点击“我卡住了”。
4. 在 L1/L2 输入一点已有记忆后点击“我想起来了”。
5. 按提示完整重答原题。
6. 回答穿插题。
7. 回答 TCP 变式重测题。
8. 结果页看到 `Lx -> L0`。
