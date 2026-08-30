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

## 🔴 当前阻塞点：火山引擎 TTS 400 错误

### 问题描述

用户在新版豆包语音控制台开通了三个"小模型"服务：
1. **语音合成**（小模型）
2. **流式语音识别**（小模型）
3. **一句话识别**（小模型）

**不是** BigTTS / 语音合成大模型 / Seed-TTS。

当前 `tts.py` 的请求：
```
POST https://openspeech.bytedance.com/api/v1/tts
Authorization: Bearer;{VOLCENGINE_API_KEY}
Content-Type: application/json

{
    "text": "...",
    "voice": "zh_female_01",
    "format": "mp3",
    "sample_rate": 24000
}
```

返回 **HTTP 400 Bad Request**。

### 已完成的排障准备

最新 commit `d19702f` 已修改 `tts.py`，现在会捕获真实的 400 response body：

```python
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")
    logger.error("[TTS] HTTP %s response=%s", exc.code, body)
    return {
        "error": "TTS upstream request failed",
        "upstream_status": exc.code,
        "upstream_message": body[:1000],
    }
```

但 `server.py` 的 `_handle_tts` 方法还没有更新来传递这个错误信息（当前仍然 `self._send_json(result)` 不管 result 里有没有 error）。

### 下一步操作（按优先级）

#### 1. 获取火山真实 400 body

重启服务器，调用 `POST /api/tts`，查看日志中的真实错误信息：

```bash
# 重启服务器
python server.py

# 测试 TTS
curl -s -X POST http://127.0.0.1:80/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"你好，这是一段语音测试。"}'

# 查看日志
tail -30 app.log
```

#### 2. 根据 400 body 修正 TTS 协议

可能的原因（需要看真实错误才能确定）：
- endpoint 不对（`/api/v1/tts` 可能是旧接口）
- 鉴权方式不对（`Authorization: Bearer;` 是旧 appid/access_token 体系）
- payload schema 不对（缺少 appid、cluster、voice_type 等字段）
- 新版 API Key 与旧接口不兼容
- voice `zh_female_01` 不是有效音色 ID

#### 3. 修正 server.py 的 /api/tts 错误处理

当前 `_handle_tts` 需要更新，让 TTS 失败时返回明确错误 JSON 而非 null：

```python
def _handle_tts(self, payload: dict) -> None:
    text = payload.get("text", "")
    if not text:
        self._send_json({"error": "No text provided"}, status=400)
        return
    from recall_trainer.tts import synthesize_speech
    result = synthesize_speech(text)
    if "error" in result:
        self._send_json(result, status=502)
    else:
        self._send_json(result)
```

#### 4. 写独立 TTS 测试脚本

创建 `scripts/test_tts.py`，直接调用 `synthesize_speech()` 验证 TTS 是否成功，不依赖 HTTP 服务器。

#### 5. TTS 成功后再接前端

TTS backend 跑通后：
- TTS 播放中 → `AI_SPEAKING` 状态
- 播放完成 → `USER_READY` 状态
- TTS 失败 → fallback 显示文字，session 继续

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
PORT=80

VOLCENGINE_API_KEY=            # 火山引擎豆包语音 API Key（语音模式必需）
VOLCENGINE_ASR_ENDPOINT=wss://openspeech.bytedance.com/api/v3/sauc/bigmodel
VOLCENGINE_ASR_CLUSTER=volcengine_streaming
VOLCENGINE_TTS_URL=https://openspeech.bytedance.com/api/v1/tts  # ← 可能需要改
VOLCENGINE_TTS_VOICE=          # ← 需要设置有效音色
WS_PORT=8082
```

## 测试

```bash
python -m unittest discover -s tests -v
# 40 tests, all passing
```

## 启动

```bash
python server.py
# Serving recall trainer on http://0.0.0.0:80
# Voice ASR WebSocket on ws://0.0.0.0:8082/ws/asr  (if VOLCENGINE_API_KEY set)
```

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
