const state = {
  sessionId: null,
  lastPayload: null,
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
  const payload = await api("/api/answer", { sessionId: state.sessionId, answer: text });
  showTraining(payload);
});

document.querySelector("#show-result").addEventListener("click", () => {
  showResult(state.lastPayload.summary);
});

document.querySelector("#restart").addEventListener("click", () => {
  window.location.reload();
});

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
}

function showResult(summary) {
  training.classList.add("hidden");
  result.classList.remove("hidden");
  const metrics = document.querySelector("#metrics");
  metrics.replaceChildren(
    metricNode("训练知识点", summary.trained_topics),
    metricNode("首次独立提取", summary.independent_first),
    metricNode("Improved Recall", summary.improved_recall),
    metricNode("发生 Recall Failure", summary.recall_failures),
    metricNode("Knowledge Gap", summary.knowledge_gaps),
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
    const standard = document.createElement("pre");
    standard.className = "standard-answer";
    standard.textContent = attempt.standard_answer || "已记录为知识缺口。";
    article.append(gap, standard);
  } else {
    article.append(retest, transition);
  }
  return article;
}

renderRatings();
