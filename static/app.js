const state = {
  sessionId: null,
  lastPayload: null,
};

// Voice state
const voiceState = {
  asrConfigured: false,
  ttsConfigured: false,
  wsPort: 8082,
  ws: null,
  audioContext: null,
  mediaStream: null,
  scriptProcessor: null,
  analyser: null,
  isRecording: false,
  recordingStartTime: 0,
  firstSpeechTime: 0,
  maxPauseMs: 0,
  currentPauseStart: 0,
  isSpeaking: false,
  finalTranscript: "",
  partialTranscript: "",
};

const domainNames = {
  network: "计算机网络",
  os: "操作系统",
  db: "数据库",
  ds: "数据结构",
  java: "Java / JVM / 并发",
  redis: "Redis",
  system_design: "系统设计",
};

const ratingNames = {
  low: "低",
  mid: "中",
  medium: "中",
  high: "高",
};

const setup = document.querySelector("#setup");
const training = document.querySelector("#training");
const result = document.querySelector("#result");
const ratings = document.querySelector("#ratings");
const answer = document.querySelector("#answer");
const coachBox = document.querySelector("#coach-box");
const trainingError = document.querySelector("#training-error");

document.querySelectorAll("input[name='domain']").forEach((input) => {
  input.addEventListener("change", renderRatings);
});

document.querySelector("#setup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = event.submitter || document.querySelector("#setup-form button[type='submit']");
  const domains = selectedDomains();
  const error = document.querySelector("#setup-error");
  error.textContent = "";
  if (domains.length < 1 || domains.length > 3) {
    error.textContent = "请选择 1 到 3 个知识领域。";
    return;
  }
  const selfRatings = {};
  domains.forEach((domain) => {
    selfRatings[domain] = document.querySelector(`#rating-${domain}`).value;
  });
  setBusy(submit, true, "生成中...");
  const payload = await api("/api/session", {
    role: document.querySelector("#role").value,
    domains,
    selfRatings,
  });
  setBusy(submit, false);
  if (payload.error) {
    error.textContent = payload.error;
    return;
  }
  state.sessionId = payload.id;
  showTraining(payload);
});

document.querySelector("#stuck").addEventListener("click", async () => {
  const payload = await api("/api/stuck", { sessionId: state.sessionId });
  showTraining(payload);
});

document.querySelector("#more-scaffold").addEventListener("click", async () => {
  const payload = await api("/api/scaffold", {
    sessionId: state.sessionId,
    answer: answer.value,
  });
  showTraining(payload);
});

document.querySelector("#recovered").addEventListener("click", async () => {
  const payload = await api("/api/scaffold", {
    sessionId: state.sessionId,
    answer: answer.value,
    recovered: true,
  });
  showTraining(payload);
});

document.querySelector("#submit-answer").addEventListener("click", async () => {
  const text = answer.value.trim();
  if (!text) {
    trainingError.textContent = "请先输入你的回答，哪怕只有一个确定的点。";
    return;
  }
  const requestBody = { sessionId: state.sessionId, answer: text };

  // If voice mode was used, include voice signals
  if (voiceState.finalTranscript || voiceState.partialTranscript) {
    requestBody.inputMode = "voice";
    requestBody.voiceSignals = getVoiceSignals();
  }

  const payload = await api("/api/answer", requestBody);
  resetVoiceState();
  showTraining(payload);
});

document.querySelector("#show-result").addEventListener("click", () => {
  showResult(state.lastPayload.summary);
});

document.querySelector("#restart").addEventListener("click", () => {
  window.location.reload();
});

// Voice: check status on load
(async function checkVoiceStatus() {
  try {
    const status = await api("/api/voice-status");
    if (status && !status.error) {
      voiceState.asrConfigured = status.asr_configured;
      voiceState.ttsConfigured = status.tts_configured;
      voiceState.wsPort = status.ws_port || 8082;
    }
  } catch (e) {
    // Voice not available
  }
  updateVoiceUI();
})();

// Voice: start recording
document.querySelector("#start-voice").addEventListener("click", startVoiceRecording);
document.querySelector("#stop-voice").addEventListener("click", stopVoiceRecording);

// TTS: play/stop
document.querySelector("#tts-play").addEventListener("click", playTTS);
document.querySelector("#tts-stop").addEventListener("click", stopTTS);

function renderRatings() {
  ratings.innerHTML = "";
  selectedDomains().forEach((domain) => {
    const label = document.createElement("label");
    label.textContent = `${domainNames[domain]}自评`;
    const select = document.createElement("select");
    select.id = `rating-${domain}`;
    select.innerHTML = `
      <option value="high">高</option>
      <option value="mid">中</option>
      <option value="low">低</option>
    `;
    label.appendChild(select);
    ratings.appendChild(label);
  });
}

function selectedDomains() {
  return Array.from(document.querySelectorAll("input[name='domain']:checked")).map((input) => input.value);
}

async function api(path, payload) {
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      return { error: "服务暂时不可用，请稍后重试。" };
    }
    return response.json();
  } catch (_error) {
    return { error: "网络连接失败，请确认服务正在运行。" };
  }
}

function setBusy(button, busy, label) {
  if (!button) {
    return;
  }
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.textContent = label;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }
}

function showTraining(payload) {
  state.lastPayload = payload;
  if (payload.error) {
    trainingError.textContent = payload.error;
    return;
  }
  setup.classList.add("hidden");
  result.classList.add("hidden");
  training.classList.remove("hidden");
  trainingError.textContent = "";
  document.querySelector("#status-pill").textContent = payload.status;
  document.querySelector("#topic").textContent = `${payload.current.topic} · 自评 ${ratingNames[payload.current.self_rating]}`;
  document.querySelector("#question").textContent = payload.current.question;
  coachBox.textContent = payload.scaffold || payload.notice || "";
  coachBox.classList.toggle("hidden", !payload.scaffold && !payload.notice);
  answer.value = "";

  const inScaffold = payload.status.startsWith("SCAFFOLD");
  const isResult = payload.status === "RESULT";
  document.querySelector("#stuck").classList.toggle("hidden", payload.status !== "QUESTION");
  document.querySelector("#recovered").classList.toggle("hidden", !inScaffold);
  document.querySelector("#more-scaffold").classList.toggle("hidden", !inScaffold);
  document.querySelector("#submit-answer").classList.toggle("hidden", isResult || inScaffold);
  document.querySelector("#show-result").classList.toggle("hidden", !isResult);

  if (payload.status === "REANSWER") {
    coachBox.textContent = payload.scaffold || "好，现在不看刚才的提示，重新完整回答一次最开始的问题。";
    coachBox.classList.remove("hidden");
  }

  // TTS: load audio for question or scaffold
  const ttsText = payload.scaffold || payload.current.question;
  loadTTSAudio(ttsText);
}

function showResult(summary) {
  training.classList.add("hidden");
  result.classList.remove("hidden");
  const metrics = document.querySelector("#metrics");
  metrics.replaceChildren(
    metricNode("训练知识点", summary.trained_topics),
    metricNode("首次独立提取", summary.independent_first),
    metricNode("Improved Recall", summary.improvedRecallCount ?? summary.improved_recall ?? 0),
    metricNode("发生 Recall Failure", summary.recall_failures),
    metricNode("Knowledge Gap", summary.knowledgeGapCount ?? summary.knowledge_gaps ?? 0),
    metricNode("训练后独立提取", summary.verified_after_training)
  );

  const attempts = document.querySelector("#attempts");
  attempts.replaceChildren(...summary.attempts.map(attemptNode));
}

function metricNode(label, value) {
  const node = document.createElement("div");
  node.className = "metric";
  node.append(document.createTextNode(label));
  const strong = document.createElement("strong");
  strong.textContent = value;
  node.append(strong);
  return node;
}

function attemptNode(attempt) {
  const article = document.createElement("article");
  article.className = "attempt";
  const title = document.createElement("h3");
  title.textContent = attempt.topic;
  const rating = document.createElement("p");
  rating.textContent = `自评：${ratingNames[attempt.self_rating] || attempt.self_rating}`;
  const first = document.createElement("p");
  first.textContent = `首次：${attempt.first_recall_level}`;
  const retest = document.createElement("p");
  retest.textContent = `变式重测：${attempt.retest_recall_level}${attempt.verified ? " ✓" : ""}`;
  const transition = document.createElement("p");
  transition.className = "transition";
  transition.textContent = `${attempt.transition}${attempt.verified ? " ✓" : ""}`;
  article.append(title, rating, first);
  if (attempt.knowledge_gap) {
    const gap = document.createElement("p");
    gap.className = "gap-label";
    gap.textContent = "Knowledge Gap";
    const userAnswer = document.createElement("p");
    userAnswer.textContent = `你的回答：${attempt.user_answer || "未形成有效回答"}`;
    const referenceTitle = document.createElement("p");
    referenceTitle.textContent = "参考答案：";
    const standard = document.createElement("pre");
    standard.className = "standard-answer";
    standard.textContent = formatReferenceAnswer(attempt);
    article.append(gap, userAnswer, referenceTitle, standard);
  } else {
    article.append(retest, transition);
  }
  return article;
}

function formatReferenceAnswer(attempt) {
  if (attempt.reference_answer && Array.isArray(attempt.key_points)) {
    const points = attempt.key_points.map((point) => `• ${point}`).join("\n");
    return `${attempt.reference_answer}\n\n关键点：\n${points}`;
  }
  return attempt.standard_answer || "已记录为知识缺口。";
}

// ============================================================
// Voice Functions
// ============================================================

function updateVoiceUI() {
  const startBtn = document.querySelector("#start-voice");
  const ttsPanel = document.querySelector("#tts-panel");
  if (!voiceState.asrConfigured) {
    startBtn.classList.add("voice-disabled");
    startBtn.title = "Voice service is not configured";
  } else {
    startBtn.classList.remove("voice-disabled");
    startBtn.title = "开始语音回答";
  }
  if (voiceState.ttsConfigured) {
    ttsPanel.classList.remove("hidden");
  } else {
    ttsPanel.classList.add("hidden");
  }
}

async function startVoiceRecording() {
  if (!voiceState.asrConfigured) {
    trainingError.textContent = "Voice service is not configured.";
    return;
  }
  if (voiceState.isRecording) return;
  trainingError.textContent = "";
  const startBtn = document.querySelector("#start-voice");
  const stopBtn = document.querySelector("#stop-voice");
  const statusText = document.querySelector("#voice-status");
  const transcriptPanel = document.querySelector("#voice-transcript");
  const transcriptText = document.querySelector("#transcript-text");
  const transcriptFinal = document.querySelector("#transcript-final");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true }
    });
    voiceState.mediaStream = stream;
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    voiceState.audioContext = audioCtx;
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    voiceState.analyser = analyser;
    source.connect(analyser);
    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    voiceState.scriptProcessor = processor;
    analyser.connect(processor);
    processor.connect(audioCtx.destination);
    const wsUrl = `ws://${window.location.hostname}:${voiceState.wsPort}/ws/asr`;
    const ws = new WebSocket(wsUrl);
    voiceState.ws = ws;
    ws.onopen = () => { ws.send(JSON.stringify({ type: "start" })); };
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "started") {
        statusText.textContent = "🔴 录音中...";
        startBtn.classList.add("recording");
      } else if (msg.type === "transcript") {
        if (msg.isFinal) {
          voiceState.finalTranscript = msg.text;
          transcriptFinal.textContent = msg.text;
          transcriptFinal.classList.remove("hidden");
          answer.value = msg.text;
        } else {
          voiceState.partialTranscript = msg.text;
          transcriptText.textContent = msg.text;
          answer.value = msg.text;
        }
      } else if (msg.type === "error") {
        statusText.textContent = `错误: ${msg.message}`;
        trainingError.textContent = `语音识别错误: ${msg.message}`;
      }
    };
    ws.onerror = () => {
      statusText.textContent = "WebSocket 连接失败";
      trainingError.textContent = "语音服务连接失败，请使用文字回答。";
    };
    ws.onclose = () => {
      if (voiceState.isRecording) statusText.textContent = "连接已断开";
    };
    voiceState.isRecording = true;
    voiceState.recordingStartTime = Date.now();
    voiceState.firstSpeechTime = 0;
    voiceState.maxPauseMs = 0;
    voiceState.currentPauseStart = 0;
    voiceState.isSpeaking = false;
    voiceState.finalTranscript = "";
    voiceState.partialTranscript = "";
    transcriptText.textContent = "";
    transcriptFinal.textContent = "";
    transcriptFinal.classList.add("hidden");
    processor.onaudioprocess = (e) => {
      if (!voiceState.isRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      let sum = 0;
      for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
      const rms = Math.sqrt(sum / inputData.length);
      const isSilent = rms < 0.01;
      const now = Date.now();
      if (!isSilent && !voiceState.isSpeaking) {
        voiceState.isSpeaking = true;
        if (voiceState.firstSpeechTime === 0) voiceState.firstSpeechTime = now;
        if (voiceState.currentPauseStart > 0) {
          const pauseDuration = now - voiceState.currentPauseStart;
          if (pauseDuration > voiceState.maxPauseMs) voiceState.maxPauseMs = pauseDuration;
          voiceState.currentPauseStart = 0;
        }
      } else if (isSilent && voiceState.isSpeaking) {
        voiceState.isSpeaking = false;
        voiceState.currentPauseStart = now;
      }
      const pcm = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]));
        pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      let binary = "";
      const bytes = new Uint8Array(pcm.buffer);
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
      const base64 = btoa(binary);
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "audio", audio: base64 }));
      }
    };
    startBtn.classList.add("hidden");
    stopBtn.classList.remove("hidden");
    transcriptPanel.classList.remove("hidden");
    statusText.textContent = "连接中...";
  } catch (err) {
    trainingError.textContent = `无法访问麦克风: ${err.message}`;
    cleanupVoiceRecording();
  }
}

function stopVoiceRecording() {
  if (!voiceState.isRecording) return;
  const statusText = document.querySelector("#voice-status");
  statusText.textContent = "处理中...";
  if (voiceState.ws && voiceState.ws.readyState === WebSocket.OPEN) {
    voiceState.ws.send(JSON.stringify({ type: "stop" }));
  }
  if (voiceState.scriptProcessor) voiceState.scriptProcessor.disconnect();
  if (voiceState.mediaStream) voiceState.mediaStream.getTracks().forEach((t) => t.stop());
  voiceState.isRecording = false;
  const startBtn = document.querySelector("#start-voice");
  const stopBtn = document.querySelector("#stop-voice");
  startBtn.classList.remove("hidden", "recording");
  stopBtn.classList.add("hidden");
  setTimeout(() => {
    if (voiceState.ws) { voiceState.ws.close(); voiceState.ws = null; }
    statusText.textContent = voiceState.finalTranscript ? "✓ 识别完成" : "录音结束";
  }, 2000);
}

function cleanupVoiceRecording() {
  if (voiceState.scriptProcessor) { voiceState.scriptProcessor.disconnect(); voiceState.scriptProcessor = null; }
  if (voiceState.analyser) { voiceState.analyser.disconnect(); voiceState.analyser = null; }
  if (voiceState.audioContext) { voiceState.audioContext.close().catch(() => {}); voiceState.audioContext = null; }
  if (voiceState.mediaStream) { voiceState.mediaStream.getTracks().forEach((t) => t.stop()); voiceState.mediaStream = null; }
  if (voiceState.ws) { voiceState.ws.close(); voiceState.ws = null; }
  voiceState.isRecording = false;
}

function getVoiceSignals() {
  const now = Date.now();
  const answerDurationMs = voiceState.recordingStartTime ? now - voiceState.recordingStartTime : 0;
  const firstSpeechLatencyMs = voiceState.firstSpeechTime ? voiceState.firstSpeechTime - voiceState.recordingStartTime : 0;
  let maxPause = voiceState.maxPauseMs;
  if (voiceState.currentPauseStart > 0 && !voiceState.isSpeaking) {
    const endPause = now - voiceState.currentPauseStart;
    if (endPause > maxPause) maxPause = endPause;
  }
  return { answerDurationMs, firstSpeechLatencyMs, maxPauseMs: maxPause };
}

function resetVoiceState() {
  cleanupVoiceRecording();
  voiceState.finalTranscript = "";
  voiceState.partialTranscript = "";
  voiceState.recordingStartTime = 0;
  voiceState.firstSpeechTime = 0;
  voiceState.maxPauseMs = 0;
  voiceState.currentPauseStart = 0;
  voiceState.isSpeaking = false;
  const transcriptPanel = document.querySelector("#voice-transcript");
  const transcriptText = document.querySelector("#transcript-text");
  const transcriptFinal = document.querySelector("#transcript-final");
  const statusText = document.querySelector("#voice-status");
  if (transcriptPanel) transcriptPanel.classList.add("hidden");
  if (transcriptText) transcriptText.textContent = "";
  if (transcriptFinal) { transcriptFinal.textContent = ""; transcriptFinal.classList.add("hidden"); }
  if (statusText) statusText.textContent = "";
}

// ============================================================
// TTS Functions
// ============================================================

let currentTTSText = "";

function playTTS() {
  if (!currentTTSText) return;
  const audio = document.querySelector("#tts-audio");
  if (audio.src) {
    audio.play().catch(() => {});
    document.querySelector("#tts-play").classList.add("hidden");
    document.querySelector("#tts-stop").classList.remove("hidden");
  }
}

function stopTTS() {
  const audio = document.querySelector("#tts-audio");
  audio.pause();
  audio.currentTime = 0;
  document.querySelector("#tts-play").classList.remove("hidden");
  document.querySelector("#tts-stop").classList.add("hidden");
}

async function loadTTSAudio(text) {
  if (!voiceState.ttsConfigured || !text) return;
  try {
    const result = await api("/api/tts", { text });
    if (result && result.audio_base64) {
      const audio = document.querySelector("#tts-audio");
      audio.src = `data:audio/${result.format || "mp3"};base64,${result.audio_base64}`;
      currentTTSText = text;
      const autoPlay = document.querySelector("#tts-auto");
      if (autoPlay && autoPlay.checked) audio.play().catch(() => {});
    }
  } catch (e) { /* TTS failure is non-fatal */ }
}

renderRatings();
