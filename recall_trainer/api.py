from __future__ import annotations

from typing import Any

from recall_trainer.llm import RecallCoachClient
from recall_trainer.voice_signal import VoiceSignals, build_voice_signals, voice_signals_suggest_recall_failure
from recall_trainer.state_machine import (
    QUESTION_BANK,
    SessionConfig,
    TrainingSession,
    advance_scaffold,
    answer_current_question,
    get_result_summary,
    mark_stuck,
    recover_from_scaffold,
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
        self._hydrate_first_question(session)
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
        if payload.get("recovered"):
            session = recover_from_scaffold(session, str(payload.get("answer", "")))
        else:
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
        active_attempt = session.current_attempt
        answer = str(payload.get("answer", ""))
        input_mode = str(payload.get("inputMode", "text"))
        voice_signals: VoiceSignals | None = None

        # Build voice signals if provided
        if input_mode == "voice" and payload.get("voiceSignals"):
            voice_signals = build_voice_signals(
                answer, payload["voiceSignals"]
            )

        judged_level = None
        if session.status.value in {"QUESTION", "RETEST"}:
            judged_level = self._judge_level(
                session.current_attempt.retest_question
                if session.status.value == "RETEST"
                else session.current_attempt.original_question,
                answer,
                voice_signals=voice_signals,
            )
        session = answer_current_question(session, answer, judged_level)
        if judged_level and judged_level.value == "Knowledge Gap":
            reference = self.llm.generate_reference_answer(
                active_attempt.topic,
                active_attempt.original_question,
            )
            active_attempt.reference_answer = reference["reference_answer"]
            active_attempt.key_points = reference["key_points"]
            points = "\n".join(f"{index + 1}. {point}" for index, point in enumerate(active_attempt.key_points))
            active_attempt.standard_answer = f"正确结论：{active_attempt.reference_answer}\n关键知识点：\n{points}"
        if session.status.value == "RETEST":
            attempt = session.current_attempt
            attempt.retest_question = self.llm.generate_retest(
                attempt.topic,
                attempt.original_question,
            )
        response = serialize_session(session)
        if session.status.value.startswith("SCAFFOLD"):
            response["scaffold"] = self.llm.generate_scaffold(
                session.current_hint_level.value,
                session.current_attempt.original_question,
                session.current_attempt.first_answer,
            )
        if judged_level and judged_level.value == "Knowledge Gap":
            response["notice"] = "这题更像是 Knowledge Gap：先记录为知识缺口，后面结果页给你简洁标准答案。"
        return response

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
        result_payload = get_result_summary(session)
        print("[RESULT SERVER]", result_payload)
        return result_payload

    def _get_session(self, payload: dict[str, Any]) -> TrainingSession:
        session_id = str(payload.get("sessionId", ""))
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found.")
        return session

    def _judge_level(self, question: str, answer: str, voice_signals: VoiceSignals | None = None):
        from recall_trainer.state_machine import RecallLevel

        # If voice signals strongly suggest recall failure, bias toward failure
        # but still let the semantic judge have the final say for knowledge gap
        voice_suggests_failure = voice_signals and voice_signals_suggest_recall_failure(voice_signals)

        # Build voice context for the judge
        voice_context = ""
        if voice_signals:
            voice_context = (
                f"\n语音信号（仅作为知识调取困难的证据，不能独立证明 Knowledge Gap）："
                f"\n- 首次开口延迟: {voice_signals.first_speech_latency_ms}ms"
                f"\n- 最长停顿: {voice_signals.max_pause_ms}ms"
                f"\n- 犹豫次数: {voice_signals.hesitation_count}"
                f"\n- 明确表达遗忘: {voice_signals.explicit_recall_failure}"
            )

        judged = self.llm.judge_recall(question, answer, voice_context=voice_context)

        # If voice signals suggest recall failure and judge didn't find
        # clear knowledge gap, prefer recall_failure
        if voice_suggests_failure and judged != "knowledge_gap":
            return RecallLevel.FAILURE

        if judged == "L0":
            return RecallLevel.L0
        if judged == "knowledge_gap":
            return RecallLevel.KNOWLEDGE_GAP
        return RecallLevel.FAILURE

    def _hydrate_first_question(self, session: TrainingSession) -> None:
        attempt = session.current_attempt
        try:
            generated = self.llm.generate_question(
                session.config.role,
                attempt.domain,
                attempt.self_rating,
            )
        except Exception:
            topic, question, _retest = QUESTION_BANK.get(attempt.domain, QUESTION_BANK["network"])[0]
            generated = {"topic": topic, "question": question}
        attempt.topic = generated["topic"]
        attempt.original_question = generated["question"]
