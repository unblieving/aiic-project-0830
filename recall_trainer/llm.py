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

    def generate_question(self, role: str, domain: str, rating: str) -> dict[str, str]:
        fallback = _fallback_question(domain)
        if not self.api_key:
            return fallback
        prompt = QUESTION_PROMPT.format(role=role, domain=domain, rating=rating)
        try:
            content = self._call_deepseek(prompt)
            parsed = json.loads(content)
            return {
                "topic": str(parsed.get("topic") or fallback["topic"]),
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

    def judge_recall(self, question: str, answer: str) -> str:
        fallback = _fallback_judge(answer)
        if not self.api_key:
            return fallback
        prompt = JUDGE_PROMPT.format(question=question, answer=answer)
        try:
            parsed = json.loads(self._call_deepseek(prompt))
            level = str(parsed.get("recall_level", fallback))
            return level if level in {"L0", "Failure"} else fallback
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
        return "Failure"
    failure_markers = ["不会", "不知道", "想不起来", "记不清", "不清楚", "忘了"]
    if any(marker in text for marker in failure_markers):
        return "Failure"
    return "L0" if len(text) >= 8 else "Failure"
