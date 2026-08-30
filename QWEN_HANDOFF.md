# qwen3.7-max 项目交接文档

交接对象：qwen3.7-max  
项目目录：`C:\Users\Lenovo\aiic-project-0830`  
项目名称：AI Interview Recall Trainer / AI 面试知识提取训练器  
当前日期：2026-08-30

## 1. 项目一句话

这是一个面向第一次准备技术面试的学生的 P0 MVP。核心不是“AI 给标准答案”，而是训练用户把已经学过但临场说不出来的知识主动提取出来。

产品主张：

```text
让存量知识，答得出来。
```

核心训练闭环：

```text
冷启动问题 -> 独立回答 -> 卡住/失败 -> L1/L2/L3 渐进提示
-> 撤掉提示完整重答 -> 穿插其他题 -> 变式重测 -> 结果验证
```

结果页最重要的信号是提示依赖变化，例如：

```text
TCP 三次握手: L2 -> L0
```

## 2. 当前完成情况

已完成：

- P0 产品说明与交付文档：`SPEC.md`、`PLAN.md`、`README.md`、`HANDOFF.md`、`PRODUCT_MEMO.md`、`SUBMISSION_CHECKLIST.md`。
- Python 标准库 HTTP 服务：`server.py`。
- 后端核心状态机：`QUESTION`、`SCAFFOLD_L1`、`SCAFFOLD_L2`、`SCAFFOLD_L3`、`REANSWER`、`RETEST`、`RESULT`。
- Setup 流程：岗位、1-3 个知识领域、每个领域自评。
- 训练策略：每轮约 5-6 题；按自评加权抽样领域，高 50%、中 40%、低 10%，并归一化。
- Recall Failure 与 Knowledge Gap 已区分：
  - Recall Failure 进入 L1/L2/L3 脚手架。
  - Knowledge Gap 跳过脚手架，结果页展示简洁参考答案。
- DeepSeek-compatible API 客户端：`recall_trainer/llm.py`。
- Prompt 集中管理：`recall_trainer/prompts.py`。
- 无 key 或 API 异常时的 mock fallback，可完整演示核心闭环。
- 前端单页训练界面：`static/index.html`、`static/styles.css`、`static/app.js`。
- 单元测试覆盖状态机、API、LLM fallback、Knowledge Gap、加权抽样、重测队列等行为。
- `PRODUCT_MEMO.md` 已存在，不再属于未完成项。

尚未完成或需要人工确认：

- 尚未确认已经部署到服务器 `43.132.173.100`。
- 尚未确认公网 `http://43.132.173.100` 可访问。
- 尚未录制 3 分钟 Demo 视频。
- `SUBMISSION_CHECKLIST.md` 中提交清单仍未打勾，提交前需要逐项核验。

## 3. 项目结构

```text
.
├── server.py
├── recall_trainer/
│   ├── __init__.py
│   ├── api.py
│   ├── llm.py
│   ├── prompts.py
│   └── state_machine.py
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/
│   ├── test_api.py
│   ├── test_llm.py
│   └── test_state_machine.py
├── README.md
├── SPEC.md
├── PLAN.md
├── HANDOFF.md
├── PRODUCT_MEMO.md
├── SUBMISSION_CHECKLIST.md
├── .env.example
├── .gitignore
└── LICENSE
```

各文件职责：

- `server.py`：使用 `ThreadingHTTPServer` 提供静态文件和 JSON API。默认监听 `0.0.0.0:80`，可通过 `PORT` 修改。
- `recall_trainer/state_machine.py`：核心业务状态机、题库 fallback、领域加权抽样、结果汇总。业务流程应优先在这里维护。
- `recall_trainer/api.py`：API 编排层，负责 session 管理、调用状态机、调用 LLM、组装返回 payload。
- `recall_trainer/llm.py`：DeepSeek-compatible chat API 封装和 mock fallback。环境变量缺失、超时、解析失败时都应保持可演示。
- `recall_trainer/prompts.py`：所有 LLM prompt 的集中位置。不要把 Recall Coach 规则散到前端。
- `static/index.html`：单页应用 DOM 结构。
- `static/styles.css`：视觉样式。
- `static/app.js`：前端状态、API 请求、训练/结果渲染。
- `tests/`：`unittest` 测试，当前是判断回归风险的主要手段。

## 4. 技术栈与运行方式

技术栈：

- Python 3 标准库 HTTP server
- 原生 HTML / CSS / JavaScript
- DeepSeek-compatible `/v1/chat/completions`
- Python `unittest`

本地运行：

```powershell
cd C:\Users\Lenovo\aiic-project-0830
$env:DEEPSEEK_API_KEY="your_deepseek_key"
python server.py
```

默认地址：

```text
http://localhost:80
```

如果本机 80 端口需要管理员权限，用 8080：

```powershell
cd C:\Users\Lenovo\aiic-project-0830
$env:PORT="8080"
$env:DEEPSEEK_API_KEY=""
python server.py
```

无 `DEEPSEEK_API_KEY` 时是 mock flow，仍可完成 Demo。

## 5. 验证方式

自动测试：

```powershell
cd C:\Users\Lenovo\aiic-project-0830
python -m unittest discover -s tests -v
```

建议手动 Demo 路径：

1. 打开首页。
2. 选择后端开发，勾选计算机网络、操作系统、数据库等 1-3 个领域。
3. 点击开始训练。
4. 第一题点击“我卡住了”。
5. 在 L1/L2 输入一点已有记忆，再点击“我想起来了”。
6. 按要求完整重答原题。
7. 回答穿插题。
8. 回答变式重测题。
9. 在结果页确认能看到 `Lx -> L0`、Improved Recall、Knowledge Gap 等信息。

## 6. API 概览

所有 API 都由 `ApiApp.handle()` 统一分发。

- `POST /api/session`
  - 输入：`role`、`domains`、`selfRatings`
  - 输出：新 session、首题、当前状态、summary
- `POST /api/stuck`
  - 输入：`sessionId`
  - 输出：进入 `SCAFFOLD_L1`，返回 L1 提示
- `POST /api/scaffold`
  - 输入：`sessionId`、`answer`、可选 `recovered`
  - 输出：继续 L2/L3，或进入 `REANSWER`
- `POST /api/answer`
  - 输入：`sessionId`、`answer`
  - 输出：根据当前状态推进到下一题、脚手架、重测或结果
- `GET /api/result?sessionId=...`
  - 输出：结果汇总

注意：当前 session 存在内存里，服务重启会丢失。这是 P0 可接受范围。

## 7. 业务边界

必须保留：

- 状态机掌控训练流程，LLM 只提供内容和轻量判断。
- DeepSeek-compatible API，不要替换成 OpenAI API。
- 没有 API key 时必须 fallback，Demo 不能崩。
- 卡住后先脚手架，不直接给标准答案。
- 恢复后必须撤掉提示完整重答。
- 训练后必须做穿插题和变式重测。
- 结果重点展示 `Lx -> Ly`，而不是综合分数。

不要扩展：

- 不要新增登录、数据库、Dashboard、排行榜、社交分享。
- 不要加入语音、视频、情绪识别、虚拟面试官。
- 不要做复杂 RAG、爬虫或外部题库抓取。
- 不要让 LLM 决定业务状态跳转。

## 8. 已知实现取舍

- 首题和变式题可以由 DeepSeek 生成；fallback 题库保证无 key 时可演示。
- 穿插题主要来自确定性题库，便于稳定 Demo。
- LLM 判断只返回 `L0`、`recall_failure`、`knowledge_gap` 三类，后端映射成内部枚举。
- 明显“我不知道/忘了/想不起来”等表达会直接判定为 Recall Failure，不再请求 DeepSeek。
- 结果页用 DOM API 渲染内容，没有把 LLM 文本直接写入 `innerHTML`。
- 前端是轻量 P0 UI，没有构建工具和前端框架。

## 9. 下一步建议

提交前优先级：

1. 运行自动测试并记录结果。
2. 本地用 `PORT=8080` 跑一次手动 Demo。
3. 部署到 `43.132.173.100`，确认 80 端口公网访问。
4. 录制 3 分钟内 Demo 视频。
5. 更新 `SUBMISSION_CHECKLIST.md` 勾选真实完成项。
6. 最后检查 `.env`、密钥、credentials 没有提交。

如果继续做产品迭代，建议顺序：

1. 提升回答质量判断，减少 fallback 关键词规则的误判。
2. 扩充高频题库和领域覆盖，但仍保持“做深做窄”。
3. 增加错题本和间隔复测，让 Surprise Retest 从单轮 Demo 变成长期训练。

## 10. 给 qwen3.7-max 的接手提醒

接手后先读：

1. `SPEC.md`
2. `README.md`
3. `PLAN.md`
4. `PRODUCT_MEMO.md`
5. `recall_trainer/state_machine.py`
6. `recall_trainer/api.py`
7. `static/app.js`
8. `tests/`

最容易误改的地方：

- 不要把 Knowledge Gap 当成 Recall Failure。前者是知识方向错或不会，后者是知道但提取失败。
- 不要在用户点“我卡住了”后直接展示完整答案。
- 不要省略重答阶段。用户被提示后必须重新完整组织答案。
- 不要把重测默认判成 L0。重测仍要经过判断，失败就记录 Failure。
- 不要提前进入结果页。还有待重测题时必须继续问完。

当前项目更像一个完成度较高的 P0 Demo，而不是长期产品。下一步工作的主线应是部署、录屏和提交材料确认，不是大规模功能扩展。
