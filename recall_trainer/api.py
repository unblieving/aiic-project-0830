from __future__ import annotations

from typing import Any

from recall_trainer.llm import RecallCoachClient
from recall_trainer.state_machine import (
    SessionConfig,
    TrainingSession,
    advance_scaffold,
    answer_current_question,
    get_result_summary,
    mark_stuck,
    serialize_session,
    start_session,
)


class ApiApp:
    def __init__(self, llm: RecallCoachClient | None = None) -> None:
        self.llm = llm or RecallCoachClient()
        self.sessions: dict[str, TrainingSession] = {}

    def handle(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        try:
            if method == "POST" and path == "/api/session":
                return self._start(payload)
            if method == "POST" and path == "/api/stuck":
                return self._stuck(payload)
            if method == "POST" and path == "/api/scaffold":
                return self._scaffold(payload)
            if method == "POST" and path == "/api/answer":
                return self._answer(payload)
            if method == "GET" and path.startswith("/api/result"):
                return self._result(path)
        except ValueError as error:
            return {"error": str(error)}
        return {"error": "Route not found."}

    def _start(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = SessionConfig(
            role=str(payload.get("role", "backend")),
            domains=list(payload.get("domains", [])),
            self_ratings=dict(payload.get("selfRatings", {})),
        )
        session = start_session(config)
        self.sessions[session.id] = session
        return serialize_session(session)

    def _stuck(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = self._get_session(payload)
        session = mark_stuck(session)
        response = serialize_session(session)
        response["scaffold"] = self.llm.generate_scaffold(
            "L1",
            session.current_attempt.original_question,
            session.current_attempt.first_answer,
        )
        return response

    def _scaffold(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = self._get_session(payload)
        session = advance_scaffold(session, str(payload.get("answer", "")))
        response = serialize_session(session)
        if session.status.value.startswith("SCAFFOLD"):
            response["scaffold"] = self.llm.generate_scaffold(
                session.current_hint_level.value,
                session.current_attempt.original_question,
                session.current_attempt.first_answer,
            )
        else:
            response["scaffold"] = "好，现在不看刚才的提示，重新完整回答一次最开始的问题。"
        return response

    def _answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = self._get_session(payload)
        session = answer_current_question(session, str(payload.get("answer", "")))
        return serialize_session(session)

    def _result(self, path: str) -> dict[str, Any]:
        _, _, query = path.partition("?")
        session_id = ""
        for item in query.split("&"):
            key, _, value = item.partition("=")
            if key == "sessionId":
                session_id = value
        session = self.sessions.get(session_id)
        if session is None:
            return {"error": "Session not found."}
        return get_result_summary(session)

    def _get_session(self, payload: dict[str, Any]) -> TrainingSession:
        session_id = str(payload.get("sessionId", ""))
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found.")
        return session
