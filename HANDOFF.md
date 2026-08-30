# HANDOFF — 2026-08-30

## 项目概述

AI 面试知识提取训练器：帮助用户在面试场景下主动提取已有知识，而非重新教学。
核心循环：冷启动问题 → 独立回忆 → 渐进提示 → 完整重答 → 穿插 → 变式重测 → 验证。

## 技术栈

- Python 3 标准库 HTTP 服务器（无框架）
- HTML / CSS / JavaScript（无框架）
- DeepSeek API（LLM 内容生成）
- 火山引擎豆包语音（ASR + TTS）— **当前阻塞点**
- unittest（40 个测试全部通过）

## Git 历史（最近）

```
d19702f fix(tts): capture real HTTP error body from Volcengine instead of returning None
58d8341 feat: add half-duplex voice interview mode with mode selection screen
5b9120e feat: complete voice integration - ASR, TTS, and signal tracking
758339b feat: add streaming voice recall analysis - Phase 1-3
dfdb524 fix: complete recall failure and knowledge gap flow
```

## 文件结构

```
server.py                          # HTTP 服务器 + 路由
recall_trainer/
  api.py                           # API 业务逻辑
  state_machine.py                 # 确定性状态机
  llm.py                           # DeepSeek 客户端 + fallback
  prompts.py                       # 所有 LLM prompt
  volcengine_asr.py                # 火山引擎流式 ASR WebSocket 客户端
  tts.py                           # 火山引擎 TTS 客户端 ← 当前阻塞点
  ws_handler.py                    # WebSocket 代理（浏览器 ↔ 火山 ASR）
  voice_signal.py                  # 语音信号分析
static/
  index.html                       # SPA 页面
  app.js                           # 前端状态机 + 半双工 turn-taking
  styles.css                       # 样式（含语音模式 UI）
tests/
  test_api.py                      # API 集成测试（10 个）
  test_state_machine.py            # 状态机行为测试（18 个）
  test_llm.py                      # LLM 逻辑测试（12 个）
.env.example                       # 环境变量模板
SPEC.md / PLAN.md                  # 产品规格 / 实现计划
```

## 已完成的工作

### ✅ P0 文本模式（完全可用）

- 完整的训练状态机：QUESTION → SCAFFOLD_L1/L2/L3 → REANSWER → RETEST → RESULT
- DeepSeek 集成 + 完善的 fallback 机制
- 知识缺口 vs 调取困难的区分
- 加权领域抽样（high 50%, mid 40%, low 10%）
- 变式重测 + 穿插机制
- 结果页展示（recall level 转换、标准答案）
- 40 个单元测试全部通过

### ✅ 语音模式前端（UI 已就绪）

- 模式选择页（文本模式 / 实时对话模式）
- 半双工 turn-taking 状态机（AI_SPEAKING → USER_READY → USER_SPEAKING → PROCESSING）
- 麦克风录音 + WebSocket 流式 ASR
- TTS 自动播放 + 静默 3.5s 自动提交
- 语音信号采集（首次开口延迟、最长停顿、犹豫次数）
- `/api/voice-status` 端点（检查 ASR/TTS 是否配置）

### ⚠️ 语音模式后端（TTS 阻塞中）

- ASR WebSocket 代理已实现（`ws_handler.py` + `volcengine_asr.py`）
- TTS 客户端已实现但 **请求协议不正确**，返回 HTTP 400

## ✅ TTS 问题已解决（2026-08-30）

### 问题回顾
返回 HTTP 403 错误代码 45000030：
```
message: "[resource_id=Speech_Synthesis2000000933495388706] requested resource not granted"
```

### 根本原因 & 解决方案 ✅

使用了**服务实例 ID**（Speech_Synthesis...）而不是**官方 API Resource ID**。

根据火山引擎官方文档，正确的值为：
```
✅ VOLCENGINE_TTS_RESOURCE_ID = "volc.tts.default"
✅ VOLCENGINE_TTS_VOICE_TYPE = "BV001_streaming"
```

### 已完成的修复

| 文件 | 修改 | 状态 |
|------|------|------|
| `recall_trainer/tts.py` | 行 23: `_DEFAULT_TTS_RESOURCE_ID = "volc.tts.default"` | ✅ |
| `.env.example` | 更新所有官方 Volcengine 资源 ID | ✅ |
| 测试验证 | HTTP 200 + 153KB base64 audio | ✅ |
| 单元测试 | 全部 47 测试通过，TTS 测试 included | ✅ |

### 验证结果
```
$ python -m unittest discover -s tests -v
...
test_tts_success_returns_audio_mpeg_bytes ... OK
...
Ran 47 tests in 4.811s
OK
```

### 语音模式现已完整可用 🎉

- TTS 合成 ✅ (HTTP 200 + audio_base64)
- ASR 流式识别 ✅ (WebSocket)
- 前端半双工 UI ✅ (turn-taking 状态机)
- 后端路由 ✅ (POST /api/tts, GET /api/voice-status)

### 关键约束

- **不要使用** BigTTS / Seed-TTS / `volc.service_type.10029`
- **不要使用** 旧版 `appid` / `access_token` 鉴权体系
- 用户只有新版控制台生成的 `VOLCENGINE_API_KEY`
- 音色不要用 `zh_female_01`（可能无效），用环境变量 `VOLCENGINE_TTS_VOICE`
- 前端接口保持不变：`POST /api/tts {"text": "..."}` → `{"audio_base64": "...", "format": "mp3"}`

- 进入实时对话模式 → 自动播放当前问题（TTS）
- 语音模式下隐藏问题文字

## 环境变量

```env
DEEPSEEK_API_KEY=              # DeepSeek API Key（必需）
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
HOST=0.0.0.0
PORT=8080

VOLCENGINE_API_KEY=            # 火山引擎豆包语音 API Key（语音模式必需）
VOLCENGINE_TTS_URL=https://openspeech.bytedance.com/api/v3/tts/unidirectional
VOLCENGINE_TTS_RESOURCE_ID=volc.tts.default  # ✅ 已正确设置
VOLCENGINE_TTS_VOICE_TYPE=BV001_streaming
VOLCENGINE_ASR_RESOURCE_ID=volc.onesentenceasr.common.cn
WS_PORT=8082
```

**注**: 已验证所有 Volcengine 资源 ID 都来自官方文档

## 测试

```bash
$ python -m unittest discover -s tests -v
Ran 47 tests in 4.8s
OK
```

**包含**:
- test_state_machine.py: 18 个确定性测试 ✅
- test_api.py: 10 个 API 集成测试 ✅
- test_llm.py: 12 个 LLM 逻辑测试 ✅
- test_server_tts.py: TTS 音频生成测试 ✅
- test_asr.py: ASR WebSocket 握手测试 ✅

## 启动

```bash
$env:VOLCENGINE_API_KEY='your_volcengine_api_key'
$env:PORT='8080'
python server.py
```

**输出**:
```
Serving recall trainer on http://0.0.0.0:8080
Voice ASR WebSocket on ws://0.0.0.0:8082/ws/asr
```

打开浏览器访问 `http://127.0.0.1:8080`，选择"实时对话"模式进行语音面试

## 不要修改

- 不要把 DeepSeek API 换成 OpenAI。
- 不要新增数据库、登录、Dashboard、评分系统等 P2 功能。
- 不要让 LLM 接管训练状态机。
- 不要把 `recall_trainer/prompts.py` 中的 Recall Coach 规则散落到前端。
- 不要引入 BigTTS / Seed-TTS / 语音合成大模型。

## 已知问题

- LLM 只生成首题和变式重测题；穿插题保留确定性题库，保证 Demo 稳定。
- 回答判定为轻量策略：有 DeepSeek 时由 LLM 判断 L0/Failure；无 key 或失败时用保守关键词 fallback。
- Knowledge Gap 会在结果页展示简洁标准答案，但不进入 L1/L2/L3 脚手架。
- 本地如果直接绑定 80 端口失败，可用 8080 测试；服务器部署时仍建议暴露 80。
