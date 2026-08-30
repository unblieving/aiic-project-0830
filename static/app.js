// ============================================================
// State
// ============================================================

const state = {
  sessionId: null, lastPayload: null, mode: null,
  phase: null, questionType: null, questionId: null, isRetest: false,
};

const voice = {
  asrConfigured: false, ttsConfigured: false, asrMode: "one_sentence",
  mediaRecorder: null, audioChunks: [], recorderMimeType: "",
  audioContext: null, mediaStream: null,
  scriptProcessor: null, analyser: null,
  isRecording: false, recordingStartTime: 0, firstSpeechTime: 0,
  maxPauseMs: 0, currentPauseStart: 0, isSpeaking: false,
  finalTranscript: "", partialTranscript: "",
  turnState: "IDLE", isMuted: false,
  currentPromptText: "", currentPromptKind: "question",
  silenceTimer: null, silenceStart: 0, silenceBarInterval: null,
  autoSubmitDelay: 3500,
};

let activeTts = null;
let ttsGeneration = 0;
let lastSpokenPromptId = null;

const domainNames = {
  network: "计算机网络", os: "操作系统", db: "数据库",
  ds: "数据结构", java: "Java / JVM / 并发",
  redis: "Redis", system_design: "系统设计",
};

// Check voice status on load
(async function () {
  try {
    const s = await api("/api/voice-status");
    if (s && !s.error) {
      voice.asrConfigured = s.asr_configured;
      voice.ttsConfigured = s.tts_configured;
      voice.asrMode = s.asr_mode || "one_sentence";
    }
  } catch (e) { /* ok */ }
})();

// Setup form
const setupSection = document.querySelector("#setup");
const setupForm = document.querySelector("#setup-form");

setupSection.addEventListener("click", (event) => {
  if (event.target.closest("button, select, input, textarea, label, fieldset")) return;
  setupSection.classList.add("revealed");
});

document.querySelectorAll("input[name='domain']").forEach((el) => {
  el.addEventListener("change", renderRatings);
});

setupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = event.submitter || document.querySelector("#setup-form button[type='submit']");
  const domains = selectedDomains();
  const err = document.querySelector("#setup-error");
  err.textContent = "";
  if (domains.length < 1 || domains.length > 3) { err.textContent = "请选择 1 到 3 个知识领域。"; return; }
  const selfRatings = {};
  domains.forEach((d) => { selfRatings[d] = document.querySelector(`#rating-${d}`).value; });
  setBusy(btn, true, "生成中...");
  const payload = await api("/api/session", {
    role: document.querySelector("#role").value, domains, selfRatings,
  });
  setBusy(btn, false);
  if (payload.error) { err.textContent = payload.error; return; }
  state.sessionId = payload.id;
  state.lastPayload = payload;
  document.querySelector("#setup").classList.add("hidden");
  document.querySelector("#mode-select").classList.remove("hidden");
});

// Mode selection
document.querySelector("#mode-text").addEventListener("click", () => {
  state.mode = "text";
  document.querySelector("#mode-select").classList.add("hidden");
  document.querySelector("#training").classList.remove("hidden");
  document.querySelector("#text-mode-ui").classList.remove("hidden");
  document.querySelector("#voice-mode-ui").classList.add("hidden");
  showTraining(state.lastPayload);
});

document.querySelector("#mode-voice").addEventListener("click", () => {
  const me = document.querySelector("#mode-error");
  me.textContent = "";
  if (!voice.asrConfigured) {
    me.textContent = "语音服务未配置。请设置 VOLCENGINE_API_KEY，或选择文本模式。";
    return;
  }
  state.mode = "voice";
  document.querySelector("#mode-select").classList.add("hidden");
  document.querySelector("#training").classList.remove("hidden");
  document.querySelector("#text-mode-ui").classList.add("hidden");
  document.querySelector("#voice-mode-ui").classList.remove("hidden");
  showTraining(state.lastPayload);
});

// Text mode buttons
document.querySelector("#stuck").addEventListener("click", async () => {
  showTraining(await api("/api/stuck", { sessionId: state.sessionId }));
});
document.querySelector("#more-scaffold").addEventListener("click", async () => {
  showTraining(await api("/api/scaffold", {
    sessionId: state.sessionId, answer: document.querySelector("#answer").value,
  }));
});
document.querySelector("#recovered").addEventListener("click", async () => {
  showTraining(await api("/api/scaffold", {
    sessionId: state.sessionId, answer: document.querySelector("#answer").value, recovered: true,
  }));
});
document.querySelector("#submit-answer").addEventListener("click", (event) => {
  submitTextAnswer(event.currentTarget);
});
document.querySelector("#show-result").addEventListener("click", () => showResult());

// Voice mode buttons
document.querySelector("#voice-stuck").addEventListener("click", async () => {
  stopVoiceRecording(); setTurnState("PROCESSING");
  showTraining(await api("/api/stuck", { sessionId: state.sessionId }));
});
document.querySelector("#voice-more-scaffold").addEventListener("click", async () => {
  stopVoiceRecording(); setTurnState("PROCESSING");
  showTraining(await api("/api/scaffold", { sessionId: state.sessionId, answer: voice.finalTranscript }));
});
document.querySelector("#voice-recovered").addEventListener("click", async () => {
  stopVoiceRecording(); setTurnState("PROCESSING");
  showTraining(await api("/api/scaffold", {
    sessionId: state.sessionId, answer: voice.finalTranscript, recovered: true,
  }));
});
document.querySelector("#voice-submit").addEventListener("click", () => {
  if (voice.turnState === "USER_READY") {
    startVoiceRecording();
    return;
  }
  if (voice.turnState === "USER_SPEAKING") submitVoiceAnswer();
});
document.querySelector("#voice-show-result").addEventListener("click", () => showResult());
document.querySelector("#voice-mute").addEventListener("click", () => {
  voice.isMuted = !voice.isMuted;
  document.querySelector("#voice-mute").textContent = voice.isMuted ? "🔊 开启朗读" : "🔇 静音朗读";
  if (voice.isMuted && activeTts) {
    const current = activeTts;
    cancelTts(current.id, current.audio, current.objectUrl);
    setTurnState("USER_READY");
  }
});
document.querySelector("#restart").addEventListener("click", () => window.location.reload());

// Turn-taking state
function setTurnState(s) {
  voice.turnState = s;
  const ind = document.querySelector("#mic-indicator");
  const lbl = document.querySelector("#mic-label");
  const promptStatus = document.querySelector("#voice-prompt-status");
  const submit = document.querySelector("#voice-submit");
  if (!ind || !lbl) return;
  ind.className = "mic-indicator";
  if (s === "AI_SPEAKING") { ind.classList.add("speaking"); lbl.textContent = "AI 正在说话…"; if (promptStatus) promptStatus.textContent = "面试官正在提问..."; if (submit) submit.textContent = "开始回答"; }
  else if (s === "USER_READY") { lbl.textContent = "请开始回答"; if (promptStatus) promptStatus.textContent = "请开始回答"; if (submit) submit.textContent = "开始回答"; }
  else if (s === "USER_SPEAKING") { ind.classList.add("listening"); lbl.textContent = "正在录音"; if (submit) submit.textContent = "回答完成"; }
  else if (s === "PROCESSING") { ind.classList.add("processing"); lbl.textContent = "处理中…"; if (submit) submit.textContent = "处理中..."; }
  else { lbl.textContent = ""; }
  setVoiceControlsDisabled(s === "AI_SPEAKING");
}

// ============================================================
// Show training state
// ============================================================

function showTraining(payload) {
  if (payload.error) {
    const errEl = state.mode === "voice" ? document.querySelector("#voice-error") : document.querySelector("#training-error");
    if (errEl) errEl.textContent = payload.error;
    console.warn("[RENDER] blocked reason=api_error", payload.error);
    return;
  }
  state.lastPayload = payload;
  state.phase = payload.status;
  state.questionType = payload.status === "RETEST" ? "surprise_retest" : "question";
  state.questionId = [
    payload.id || state.sessionId || "session",
    payload.current?.topic || "",
    payload.current?.question || "",
  ].join("|");
  state.isRetest = payload.status === "RETEST";
  document.querySelector("#status-pill").textContent = payload.status;
  document.querySelector("#topic").textContent = payload.current.topic;
  const questionEl = document.querySelector("#question");
  const coachEl = document.querySelector("#coach-box");
  questionEl.textContent = payload.current.question;
  questionEl.classList.toggle("hidden", state.mode === "voice");
  coachEl.classList.add("hidden");
  updateVoiceQuestionCount(payload);

  const ids = ["stuck","recovered","more-scaffold","submit-answer","show-result",
               "voice-stuck","voice-recovered","voice-more-scaffold","voice-show-result"];
  ids.forEach((id) => {
    const el = document.querySelector(`#${id}`);
    if (el) el.classList.add("hidden");
  });
  const show = (id) => { const el = document.querySelector(`#${id}`); if (el) el.classList.remove("hidden"); };

  if (payload.status === "QUESTION") {
    show("stuck"); show("submit-answer"); show("voice-stuck");
    if (state.mode === "text") {
      document.querySelector("#answer").value = "";
      document.querySelector("#answer").focus();
    } else {
      resetVoiceTranscript();
      presentVoicePrompt(payload.current.question, "question", promptIdFor(payload, "question"));
    }
  }

  if (payload.status && payload.status.startsWith("SCAFFOLD")) {
    coachEl.textContent = payload.scaffold || "";
    if (state.mode === "text") coachEl.classList.remove("hidden");
    show("recovered"); show("more-scaffold");
    show("voice-recovered"); show("voice-more-scaffold");
    if (state.mode === "voice") {
      resetVoiceTranscript();
      presentVoicePrompt(payload.scaffold || "", "scaffold", promptIdFor(payload, "scaffold", payload.scaffold || ""));
    }
  }

  if (payload.status === "REANSWER") {
    show("submit-answer");
    const txt = payload.scaffold || "好，现在不看刚才的提示，重新完整回答一次最开始的问题。";
    coachEl.textContent = txt;
    if (state.mode === "text") coachEl.classList.remove("hidden");
    if (state.mode === "voice") { resetVoiceTranscript(); presentVoicePrompt(txt, "scaffold", promptIdFor(payload, "reanswer", txt)); }
  }

  if (payload.status === "RETEST") {
    show("submit-answer");
    if (state.mode === "voice") show("voice-stuck");
    if (state.mode === "text") {
      document.querySelector("#answer").value = "";
      document.querySelector("#answer").focus();
    } else {
      resetVoiceTranscript();
      presentVoicePrompt(payload.current.question, "question", promptIdFor(payload, "retest"));
    }
  }

  if (payload.status === "DONE" || payload.status === "RESULT") {
    show("show-result"); show("voice-show-result");
    if (state.mode === "voice") {
      stopVoiceRecording(); setTurnState("IDLE");
      speakText("本轮训练完成！点击查看结果。", "done");
    }
  }

  const errEl = state.mode === "voice" ? document.querySelector("#voice-error") : document.querySelector("#training-error");
  if (errEl) errEl.textContent = payload.notice || "";
}

async function showResult() {
  if (state.mode === "voice") stopVoiceRecording();
  const payload = await api(`/api/result?sessionId=${state.sessionId}`);
  console.log("[RESULT] raw result =", payload);
  document.querySelector("#training").classList.add("hidden");
  document.querySelector("#result").classList.remove("hidden");
  renderResult(payload);
}

// ============================================================
// TTS: play text, then start listening
// ============================================================

async function playTTSAndThenListen(text, promptId) {
  if (voice.isMuted || !voice.ttsConfigured) {
    showVoiceTextFallback("语音播放失败，已切换为文字显示");
    setTurnState("USER_READY");
    startVoiceRecording();
    return;
  }
  stopVoiceRecording();
  setTurnState("AI_SPEAKING");
  const completed = await speakText(text, promptId);
  if (!completed || lastSpokenPromptId !== promptId) return;
  setTurnState("USER_READY");
}

async function submitTextAnswer(btn) {
  console.log("[SUBMIT] clicked", {
    phase: state.phase,
    questionType: state.questionType,
    questionId: state.questionId,
    isRetest: state.isRetest,
  });
  const errEl = document.querySelector("#training-error");
  if (errEl) errEl.textContent = "";
  const answerEl = document.querySelector("#answer");
  const answer = answerEl.value.trim();
  console.log(`[SUBMIT] answer chars=${answer.length}`);
  if (!answer) {
    console.warn("[SUBMIT] blocked reason=empty_answer");
    if (errEl) errEl.textContent = "请先输入你的回答。";
    return;
  }

  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "正在分析…";
  try {
    const submitType = state.isRetest ? "surprise_retest" : "question";
    console.log("[SUBMIT] sending type=", submitType);
    const response = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId: state.sessionId, answer }),
    });
    console.log("[SUBMIT] response status=", response.status);
    const raw = await response.text();
    console.log("[SUBMIT] response body=", raw);
    const payload = JSON.parse(raw);
    if (!response.ok || payload.error) throw new Error(payload.error || `HTTP ${response.status}`);
    console.log("[SUBMIT] success next_state=", payload.status);
    showTraining(payload);
  } catch (err) {
    console.error("[SUBMIT] failed error=", err);
    if (errEl) errEl.textContent = `提交失败：${err.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

async function speakText(text, promptId) {
  if (!text) return true;
  const id = ++ttsGeneration;
  const old = activeTts;
  if (old) cancelTts(old.id, old.audio, old.objectUrl);

  console.log("[TTS REQUEST]", { text, reason: promptId, phase: voice.turnState });
  console.log("[TTS]", id, "fetch start");
  console.log(`[TTS #${id}] request textLength=${text.length}`);
  try {
    const response = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    });
    const contentType = response.headers.get("content-type") || "";
    console.log(`[TTS #${id}] response status=${response.status} content-type=${contentType}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    let blob;
    if (contentType.includes("audio/")) {
      blob = await response.blob();
    } else {
      const result = await response.json();
      if (!result || !result.audio_base64) throw new Error(result?.error || "TTS returned no audio");
      blob = base64ToAudioBlob(result.audio_base64, result.format || "mp3");
    }

    console.log("[TTS]", id, "blob bytes=", blob.size);
    console.log(`[TTS #${id}] blob size=${blob.size}`);
    if (!blob.size) throw new Error("empty audio blob");

    if (id !== ttsGeneration) {
      console.log(`[TTS #${id}] cancelled`);
      return false;
    }

    const objectUrl = URL.createObjectURL(blob);
    const audio = new Audio(objectUrl);
    activeTts = { id, audio, objectUrl };
    console.log("[TTS]", id, "created");
    await waitForAudioReady(id, audio);
    if (activeTts?.id !== id) {
      console.log(`[TTS #${id}] cancelled`);
      cancelTts(id, audio, objectUrl);
      return false;
    }

    console.log("[TTS]", id, "duration=", audio.duration);
    console.log(`[TTS #${id}] duration=${Number.isFinite(audio.duration) ? audio.duration.toFixed(3) : "unknown"}`);
    console.log("[TTS]", id, "play()");
    console.log(`[TTS #${id}] play start`);
    await audio.play();
    console.log("[TTS]", id, "play");
    console.log(`[TTS #${id}] play success`);
    const ended = await waitForAudioEnded(id, audio);
    if (!ended) {
      console.log(`[TTS #${id}] cancelled`);
      return false;
    }
    console.log("[TTS]", id, "ended");
    console.log(`[TTS #${id}] ended`);
    cleanupTts(id, objectUrl);
    return true;
  } catch (err) {
    if (id !== ttsGeneration) {
      console.log(`[TTS #${id}] cancelled`);
      return false;
    }
    console.log("[TTS]", id, "error", err);
    console.log(`[TTS #${id}] error`, err);
    showVoiceTextFallback("语音播放失败，已切换为文字显示");
    const current = activeTts;
    if (current?.id === id) cancelTts(id, current.audio, current.objectUrl);
    return true;
  }
}

function waitForAudioReady(id, audio) {
  return new Promise((resolve, reject) => {
    if (audio.readyState >= 1) { resolve(); return; }
    audio.onloadedmetadata = () => resolve();
    audio.oncanplay = () => resolve();
    audio.onerror = () => reject(new Error(`TTS #${id} audio metadata error`));
  });
}

function waitForAudioEnded(id, audio) {
  return new Promise((resolve, reject) => {
    audio.addEventListener("ended", () => resolve(true), { once: true });
    audio.addEventListener("tts-cancelled", () => resolve(false), { once: true });
    audio.addEventListener("pause", () => {
      console.log("[TTS]", id, "pause");
      console.log("[TTS DIAG]", ttsDiagnostics(audio));
    });
    audio.addEventListener("error", () => {
      console.log("[TTS DIAG]", ttsDiagnostics(audio));
      reject(new Error(`TTS #${id} audio playback error`));
    }, { once: true });
  });
}

function cancelTts(id, audio, objectUrl) {
  audio.dispatchEvent(new Event("tts-cancelled"));
  if (activeTts?.id === id) activeTts = null;
  try { audio.pause(); } catch {}
  cleanupTts(id, objectUrl);
}

function cleanupTts(id, objectUrl) {
  if (activeTts?.id !== id) {
    console.log("[TTS]", id, "skip stale cleanup");
  } else {
    activeTts = null;
  }
  try { URL.revokeObjectURL(objectUrl); } catch {}
  console.log("[TTS]", id, "cleanup");
  console.log(`[TTS #${id}] cleanup`);
}

function ttsDiagnostics(audio) {
  return {
    currentTime: audio.currentTime,
    duration: audio.duration,
    readyState: audio.readyState,
    networkState: audio.networkState,
  };
}

function base64ToAudioBlob(base64, format) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const mime = format === "wav" ? "audio/wav" : "audio/mpeg";
  return new Blob([bytes], { type: mime });
}

function presentVoicePrompt(text, kind, promptId) {
  voice.currentPromptText = text || "";
  voice.currentPromptKind = kind || "question";
  hideVoicePromptText();
  if (promptId === lastSpokenPromptId) return;
  lastSpokenPromptId = promptId;
  playTTSAndThenListen(voice.currentPromptText, promptId);
}

function hideVoicePromptText() {
  if (state.mode !== "voice") return;
  document.querySelector("#question").classList.add("hidden");
  document.querySelector("#coach-box").classList.add("hidden");
  const err = document.querySelector("#voice-error");
  if (err) err.textContent = "";
}

function showVoiceTextFallback(message) {
  if (state.mode !== "voice") return;
  const err = document.querySelector("#voice-error");
  if (err) err.textContent = message;
  if (voice.currentPromptKind === "scaffold") {
    const coach = document.querySelector("#coach-box");
    coach.textContent = voice.currentPromptText;
    coach.classList.remove("hidden");
  } else {
    const question = document.querySelector("#question");
    question.textContent = voice.currentPromptText;
    question.classList.remove("hidden");
  }
}

function updateVoiceQuestionCount(payload) {
  const el = document.querySelector("#voice-question-count");
  if (!el || !payload.summary) return;
  const total = payload.summary.total || 6;
  const answered = (payload.summary.attempts || []).filter((a) => a.first_answer || a.first_recall_level).length;
  const current = Math.min(total, answered + 1);
  el.textContent = `第 ${current} / ${total} 题`;
}

function setVoiceControlsDisabled(disabled) {
  ["voice-submit", "voice-stuck", "voice-recovered", "voice-more-scaffold"].forEach((id) => {
    const el = document.querySelector(`#${id}`);
    if (el) el.disabled = disabled;
  });
}

function promptIdFor(payload, kind, text) {
  const base = [
    payload.id || state.sessionId || "session",
    payload.status,
    payload.current?.topic || "",
    payload.current?.question || "",
    kind,
    text || "",
  ].join("|");
  return base;
}

// ============================================================
// Voice Recording (MediaRecorder -> /api/asr)
// ============================================================

function startVoiceRecording() {
  if (voice.isRecording || voice.turnState === "AI_SPEAKING") return;
  console.log("[REC] start");
  setTurnState("USER_SPEAKING");
  voice.audioChunks = [];
  voice.recorderMimeType = "";
  navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
    console.log("[REC] permission ok");
    voice.mediaStream = stream;

    const mimeType = supportedRecorderMimeType();
    const options = mimeType ? { mimeType } : {};
    const mediaRecorder = new MediaRecorder(stream, options);
    voice.mediaRecorder = mediaRecorder;
    voice.recorderMimeType = mediaRecorder.mimeType || mimeType || "audio/webm";
    console.log("[REC] mimeType=", voice.recorderMimeType);

    mediaRecorder.ondataavailable = (event) => {
      console.log("[REC] chunk bytes=", event.data ? event.data.size : 0);
      if (event.data && event.data.size > 0) voice.audioChunks.push(event.data);
    };
    mediaRecorder.onerror = (event) => {
      console.error("[REC] recorder error", event.error || event);
      showVoiceError(`录音失败：${(event.error && event.error.message) || "MediaRecorder error"}`);
    };

    setupVoiceSignalMeter(stream);
    voice.isRecording = true;
    voice.recordingStartTime = Date.now();
    voice.firstSpeechTime = 0; voice.maxPauseMs = 0;
    voice.currentPauseStart = 0; voice.isSpeaking = false;
    mediaRecorder.start(1000);
  }).catch((err) => {
    showVoiceError(`无法访问麦克风: ${err.message}`);
    setTurnState("IDLE");
  });
}

function supportedRecorderMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function setupVoiceSignalMeter(stream) {
  if (!window.AudioContext && !window.webkitAudioContext) return;
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  voice.audioContext = ctx;
  const src = ctx.createMediaStreamSource(stream);
  const an = ctx.createAnalyser(); an.fftSize = 256;
  voice.analyser = an; src.connect(an);
  const proc = ctx.createScriptProcessor(4096, 1, 1);
  voice.scriptProcessor = proc; an.connect(proc); proc.connect(ctx.destination);
  proc.onaudioprocess = (e) => {
    if (!voice.isRecording) return;
    const d = e.inputBuffer.getChannelData(0);
    let sum = 0;
    for (let i = 0; i < d.length; i++) sum += d[i] * d[i];
    updateVoiceSignals(Math.sqrt(sum / d.length));
  };
}

function updateVoiceSignals(rms) {
  const silent = rms < 0.01;
  const now = Date.now();
  if (!silent && !voice.isSpeaking) {
    voice.isSpeaking = true;
    if (voice.firstSpeechTime === 0) voice.firstSpeechTime = now;
    if (voice.currentPauseStart > 0) {
      const pd = now - voice.currentPauseStart;
      if (pd > voice.maxPauseMs) voice.maxPauseMs = pd;
      voice.currentPauseStart = 0;
    }
  } else if (silent && voice.isSpeaking) {
    voice.isSpeaking = false;
    voice.currentPauseStart = now;
  }
}

function stopVoiceRecording() {
  if (!voice.isRecording) return;
  clearSilenceTimer();
  if (voice.mediaRecorder && voice.mediaRecorder.state !== "inactive") voice.mediaRecorder.stop();
  cleanupRecordingResources();
}

function stopRecordingAndGetBlob() {
  return new Promise((resolve, reject) => {
    const recorder = voice.mediaRecorder;
    if (!voice.isRecording || !recorder) {
      resolve(new Blob([], { type: voice.recorderMimeType || "audio/webm" }));
      return;
    }
    console.log("[REC] chunks=", voice.audioChunks.length);
    recorder.onstop = () => {
      const blob = new Blob(voice.audioChunks, { type: voice.recorderMimeType || recorder.mimeType || "audio/webm" });
      console.log("[REC] final blob bytes=", blob.size, "type=", blob.type);
      cleanupRecordingResources();
      resolve(blob);
    };
    recorder.onerror = (event) => {
      cleanupRecordingResources();
      reject(event.error || new Error("MediaRecorder error"));
    };
    recorder.stop();
  });
}

function cleanupRecordingResources() {
  if (voice.scriptProcessor) { voice.scriptProcessor.disconnect(); voice.scriptProcessor = null; }
  if (voice.analyser) { voice.analyser.disconnect(); voice.analyser = null; }
  if (voice.audioContext) { voice.audioContext.close().catch(() => {}); voice.audioContext = null; }
  if (voice.mediaStream) { voice.mediaStream.getTracks().forEach((t) => t.stop()); voice.mediaStream = null; }
  voice.mediaRecorder = null;
  voice.isRecording = false;
}

function resetVoiceTranscript() {
  voice.finalTranscript = ""; voice.partialTranscript = "";
  voice.recordingStartTime = 0; voice.firstSpeechTime = 0;
  voice.maxPauseMs = 0; voice.currentPauseStart = 0; voice.isSpeaking = false;
  const ie = document.querySelector("#transcript-interim");
  const fe = document.querySelector("#transcript-final");
  if (ie) ie.textContent = "等待你开口…";
  if (fe) fe.textContent = "";
  clearSilenceTimer();
}

// ============================================================
// Silence detection & auto-submit
// ============================================================

function startSilenceTimer() {
  clearSilenceTimer();
  if (!voice.finalTranscript.trim() && !voice.partialTranscript.trim()) return;
  voice.silenceStart = Date.now();
  const bar = document.querySelector("#silence-bar");
  const fill = document.querySelector("#silence-fill");
  const lbl = document.querySelector("#silence-label");
  if (bar) bar.classList.remove("hidden");
  voice.silenceBarInterval = setInterval(() => {
    const el = Date.now() - voice.silenceStart;
    const pct = Math.min(100, (el / voice.autoSubmitDelay) * 100);
    if (fill) fill.style.width = `${pct}%`;
    const rem = Math.max(0, (voice.autoSubmitDelay - el) / 1000);
    if (lbl) lbl.textContent = `${rem.toFixed(1)}s 后自动提交`;
  }, 100);
  voice.silenceTimer = setTimeout(() => submitVoiceAnswer(), voice.autoSubmitDelay);
}

function resetSilenceTimer() { clearSilenceTimer(); }

function clearSilenceTimer() {
  if (voice.silenceTimer) { clearTimeout(voice.silenceTimer); voice.silenceTimer = null; }
  if (voice.silenceBarInterval) { clearInterval(voice.silenceBarInterval); voice.silenceBarInterval = null; }
  const bar = document.querySelector("#silence-bar");
  const fill = document.querySelector("#silence-fill");
  if (bar) bar.classList.add("hidden");
  if (fill) fill.style.width = "0%";
}

// ============================================================
// Submit voice answer
// ============================================================

async function submitVoiceAnswer() {
  clearSilenceTimer();
  setTurnState("PROCESSING");
  let blob;
  try {
    blob = await stopRecordingAndGetBlob();
  } catch (err) {
    console.error("[REC] stop error", err);
    showVoiceError(`录音失败：${err.message || err}`);
    setTurnState("USER_READY");
    return;
  }
  if (blob.size < 1000) {
    showVoiceError("没有录到有效音频，请重试。");
    setTurnState("USER_READY");
    return;
  }

  let text = "";
  try {
    text = await uploadAudioForTranscript(blob);
  } catch (err) {
    console.error("[ASR CLIENT] error", err);
    showVoiceError(`语音识别失败：${err.message}`);
    setTurnState("USER_READY");
    return;
  }
  if (!text) {
    showVoiceError("没有检测到语音，请重试。");
    setTurnState("USER_READY");
    return;
  }
  voice.finalTranscript = text;
  voice.partialTranscript = "";
  const fe = document.querySelector("#transcript-final");
  const ie = document.querySelector("#transcript-interim");
  if (fe) fe.textContent = `我说：${text}`;
  if (ie) ie.textContent = "";

  const vs = getVoiceSignals();
  const payload = await api("/api/answer", {
    sessionId: state.sessionId, answer: text,
    inputMode: "voice", voiceSignals: vs,
  });
  showTraining(payload);
}

async function uploadAudioForTranscript(blob) {
  console.log("[ASR CLIENT] upload bytes=", blob.size, "type=", blob.type);
  const response = await fetch("/api/asr", {
    method: "POST",
    headers: { "Content-Type": blob.type || "audio/webm" },
    body: blob,
  });
  console.log("[ASR CLIENT] status=", response.status);
  const raw = await response.text();
  console.log("[ASR CLIENT] raw response=", raw);
  let data;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    throw new Error(`ASR returned non-JSON response: ${raw.slice(0, 160)}`);
  }
  if (!response.ok || data.ok === false) throw new Error(data.error || `HTTP ${response.status}`);
  return (data.transcript || "").trim();
}

function showVoiceError(message) {
  const ve = document.querySelector("#voice-error");
  if (ve) ve.textContent = message;
}

function getVoiceSignals() {
  const now = Date.now();
  const dur = voice.recordingStartTime ? now - voice.recordingStartTime : 0;
  const lat = voice.firstSpeechTime ? voice.firstSpeechTime - voice.recordingStartTime : 0;
  let mp = voice.maxPauseMs;
  if (voice.currentPauseStart > 0 && !voice.isSpeaking) {
    const ep = now - voice.currentPauseStart;
    if (ep > mp) mp = ep;
  }
  return { answerDurationMs: dur, firstSpeechLatencyMs: lat, maxPauseMs: mp };
}

// ============================================================
// API helper
// ============================================================

async function api(path, body) {
  const opts = body ? {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  } : {};
  const r = await fetch(path, opts);
  return r.json();
}

// ============================================================
// UI helpers
// ============================================================

function setBusy(btn, busy, label) {
  btn.disabled = busy;
  if (busy) btn.dataset.originalText = btn.textContent;
  btn.textContent = busy ? label : btn.dataset.originalText || btn.textContent;
}

function selectedDomains() {
  return Array.from(document.querySelectorAll("input[name='domain']:checked")).map((i) => i.value);
}

function renderRatings() {
  const domains = selectedDomains();
  document.querySelector("#ratings").innerHTML = domains.map((d) => `
    <label>${domainNames[d]} 自评
      <select id="rating-${d}">
        <option value="low">低（不太确定）</option>
        <option value="mid" selected>中（大概知道）</option>
        <option value="high">高（比较熟）</option>
      </select>
    </label>`).join("");
}

// ============================================================
// Result rendering
// ============================================================

function renderResult(summary) {
  const totalQuestions = Number(summary.total_questions ?? 0);
  const recalledCount = Number(summary.recalled_count ?? 0);
  const knowledgeGapCount = Number(summary.knowledge_gap_count ?? 0);
  const recoveredCount = Number(summary.recovered_count ?? 0);
  const items = Array.isArray(summary.items) ? summary.items : [];
  document.querySelector("#metrics").innerHTML = `
    <div class="metric">题目数<strong>${totalQuestions}</strong></div>
    <div class="metric">成功调出<strong>${recalledCount}</strong></div>
    <div class="metric">知识缺口<strong>${knowledgeGapCount}</strong></div>`;
  const subtitle = document.querySelector("#result-summary");
  if (subtitle) {
    subtitle.textContent = `本轮 ${totalQuestions} 个知识点中，你成功调出 ${recalledCount} 个，其中 ${recoveredCount} 个是在提示后恢复的。`;
  }
  document.querySelector("#attempts").innerHTML = items.map(renderAttempt).join("");
}

function renderAttempt(a) {
  if (a.status === "independent_recall") {
    return `<div class="attempt"><strong>${escapeHtml(a.concept || a.topic || "")}</strong>
      <p>${escapeHtml(a.question || "")}</p>
      <p>✅ 独立调出</p>
      <p class="transition">无需提示即可回答</p></div>`;
  }
  if (a.status === "recovered") {
    const maxLevel = Number(a.max_scaffold_level || 0);
    return `<div class="attempt"><strong>${escapeHtml(a.concept || a.topic || "")}</strong>
      <p>${escapeHtml(a.question || "")}</p>
      <p>🟡 提示后成功调出</p>
      <p class="transition">${escapeHtml(recoveryPath(maxLevel))}</p>
      <p>你在第 ${maxLevel} 层提示后恢复了这个知识点。</p></div>`;
  }
  return `<div class="attempt"><strong>${escapeHtml(a.concept || a.topic || "")}</strong>
    <p>${escapeHtml(a.question || "")}</p>
    <p>❌ 知识缺口</p>
    <p>你的回答：${escapeHtml(a.user_answer || "")}</p>
    <p class="standard-answer">参考答案：${escapeHtml(fmtRef(a))}</p></div>`;
}

function fmtRef(a) {
  if (a.reference_answer) return a.reference_answer;
  return a.standard_answer || "已记录为知识缺口。";
}

function recoveryPath(maxLevel) {
  const parts = ["独立回忆"];
  for (let level = 1; level <= maxLevel; level++) parts.push(`L${level}`);
  parts.push("成功调出");
  return parts.join(" → ");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// Init
renderRatings();
