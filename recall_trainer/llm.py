from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from recall_trainer.prompts import (
    JUDGE_PROMPT,
    QUESTION_PROMPT,
    RETEST_PROMPT,
    SCAFFOLD_PROMPTS,
    STANDARD_ANSWER_PROMPT,
    SYSTEM_PROMPT,
)
from recall_trainer.state_machine import QUESTION_BANK


class RecallCoachClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 6,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
        self.timeout_seconds = timeout_seconds

    def generate_question(
        self,
        role: str,
        domain: str,
        rating: str,
        *,
        selected_domains: list[str] | None = None,
        already_asked_questions: list[str] | None = None,
        covered_concepts: list[str] | None = None,
        current_question_index: int = 1,
        total_questions: int = 5,
    ) -> dict[str, str]:
        fallback = _fallback_question(domain)
        if not self.api_key:
            return fallback
        prompt = QUESTION_PROMPT.format(
            role=role,
            domain=domain,
            rating=rating,
            selected_domains=", ".join(selected_domains or [domain]),
            already_asked_questions=json.dumps(already_asked_questions or [], ensure_ascii=False),
            covered_concepts=json.dumps(covered_concepts or [], ensure_ascii=False),
            current_question_index=current_question_index,
            total_questions=total_questions,
        )
        try:
            content = self._call_deepseek(prompt)
            parsed = json.loads(content)
            return {
                "topic": str(parsed.get("concept") or parsed.get("topic") or fallback["topic"]),
                "question": str(parsed.get("question") or fallback["question"]),
            }
        except (TimeoutError, ValueError, KeyError, urllib.error.URLError, json.JSONDecodeError):
            return fallback

    def generate_scaffold(self, level: str, question: str, answer: str) -> str:
        fallback = _fallback_scaffold(level, answer)
        if not self.api_key:
            return fallback
        prompt_template = SCAFFOLD_PROMPTS[level]
        prompt = prompt_template.format(question=question, answer=answer)
        try:
            return self._call_deepseek(prompt).strip() or fallback
        except (TimeoutError, ValueError, KeyError, urllib.error.URLError):
            return fallback

    def generate_retest(self, topic: str, question: str) -> str:
        fallback = _fallback_retest(topic, question)
        if not self.api_key:
            return fallback
        prompt = RETEST_PROMPT.format(topic=topic, question=question)
        try:
            parsed = json.loads(self._call_deepseek(prompt))
            return str(parsed.get("question") or fallback)
        except (TimeoutError, ValueError, KeyError, urllib.error.URLError, json.JSONDecodeError):
            return fallback

    def judge_recall(self, question: str, answer: str, voice_context: str = "") -> str:
        fallback = _fallback_judge(answer)
        if _is_explicit_retrieval_failure(answer):
            return "recall_failure"
        if not self.api_key:
            return fallback
        prompt = JUDGE_PROMPT.format(question=question, answer=answer)
        if voice_context:
            prompt += voice_context
        try:
            parsed = json.loads(self._call_deepseek(prompt))
            verdict = str(parsed.get("verdict") or "").lower()
            if verdict == "correct":
                level = "L0"
            elif verdict in {"partial", "incorrect"}:
                level = "knowledge_gap" if verdict == "incorrect" else "recall_failure"
            elif verdict == "recall_failure":
                level = "recall_failure"
            else:
                level = str(parsed.get("recall_type") or parsed.get("recall_level") or fallback)
            if level == "Failure":
                return "recall_failure"
            return level if level in {"L0", "recall_failure", "knowledge_gap"} else fallback
        except (TimeoutError, ValueError, KeyError, urllib.error.URLError, json.JSONDecodeError):
            return fallback

    def generate_standard_answer(self, topic: str, question: str) -> str:
        reference = self.generate_reference_answer(topic, question)
        return _format_reference_answer(reference)

    def generate_reference_answer(self, topic: str, question: str) -> dict[str, Any]:
        fallback = _fallback_standard_answer(topic)
        if not self.api_key:
            return fallback
        prompt = STANDARD_ANSWER_PROMPT.format(topic=topic, question=question)
        try:
            content = self._call_deepseek(prompt).strip()
            parsed = json.loads(content)
            reference_answer = str(parsed.get("reference_answer", "")).strip()
            key_points = [str(item).strip() for item in parsed.get("key_points", []) if str(item).strip()]
            if not reference_answer or not key_points:
                return fallback
            return {
                "reference_answer": reference_answer[:260],
                "key_points": key_points[:4],
            }
        except (TimeoutError, ValueError, KeyError, urllib.error.URLError, json.JSONDecodeError):
            return fallback

    def _call_deepseek(self, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


def _fallback_question(domain: str) -> dict[str, str]:
    topic, question, _retest = QUESTION_BANK.get(domain, QUESTION_BANK["network"])[0]
    return {"topic": topic, "question": question}


def _fallback_retest(topic: str, question: str) -> str:
    for questions in QUESTION_BANK.values():
        for known_topic, original, retest in questions:
            if known_topic == topic or original == question:
                return retest
    return f"换一种问法：{topic}在真实面试里最容易被追问什么？"


def _fallback_scaffold(level: str, answer: str) -> str:
    if level == "L1":
        return "先不用追求完整答案。告诉我一个你现在最确定的点。"
    if level == "L2":
        anchor = answer.strip().splitlines()[-1] if answer.strip() else "你刚才提到的方向"
        return f"好，就沿着你刚才说的“{anchor}”继续想。"
    return "可以尝试从双方发送与接收能力这个方向回忆。"


def _fallback_judge(answer: str) -> str:
    text = answer.strip()
    if not text:
        return "recall_failure"
    if _is_explicit_retrieval_failure(text):
        return "recall_failure"
    if _looks_like_gibberish(text):
        return "knowledge_gap"
    wrong_direction_markers = ["数据库索引", "排序算法", "哈希表", "加密", "安全传输", "https"]
    if "TCP" in text and any(marker in text for marker in wrong_direction_markers):
        return "knowledge_gap"
    return "L0" if len(text) >= 8 else "recall_failure"


def _fallback_standard_answer(topic: str) -> dict[str, Any]:
    known = {
        "TCP 三次握手": {
            "reference_answer": "TCP 三次握手的核心目的是确认客户端和服务端双方的发送与接收能力，并同步初始序列号，从而建立可靠连接。它本身不是为了提供数据加密。",
            "key_points": ["双方通信能力确认", "初始序列号同步", "避免历史连接干扰"],
        },
        "HTTP 与 HTTPS": {
            "reference_answer": "HTTPS 在 HTTP 基础上通过 TLS 提供加密、身份认证和完整性保护，降低明文传输、伪造服务端和内容篡改风险。",
            "key_points": ["TLS 加密传输", "证书验证身份", "完整性校验"],
        },
    }
    return known.get(
        topic,
        {
            "reference_answer": f"{topic}是该题的核心知识点，面试回答需要先说明它解决的问题，再讲清核心机制和典型追问场景。",
            "key_points": ["说明解决的问题", "讲清核心机制", "解释典型场景"],
        },
    )


def _format_reference_answer(reference: dict[str, Any]) -> str:
    points = "\n".join(f"{index + 1}. {point}" for index, point in enumerate(reference["key_points"]))
    return f"正确结论：{reference['reference_answer']}\n关键知识点：\n{points}"


def _is_explicit_retrieval_failure(answer: str) -> bool:
    text = answer.lower()
    markers = [
        "不知道",
        "不太知道",
        "忘了",
        "忘记了",
        "想不起来",
        "记不起来",
        "不记得",
        "卡住了",
        "没想起来",
        "i don't know",
        "i dont know",
        "i forgot",
        "can't remember",
        "cant remember",
    ]
    return any(marker in text for marker in markers)


def _looks_like_gibberish(answer: str) -> bool:
    text = answer.strip().lower()
    markers = ["哈哈", "随便", "乱写", "asdf", "房价"]
    if any(marker in text for marker in markers):
        return True
    if text.isdigit():
        return True
    ascii_letters = sum(1 for char in text if "a" <= char <= "z")
    return bool(text) and ascii_letters == len(text)
