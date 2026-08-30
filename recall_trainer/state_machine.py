from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class TrainingStatus(str, Enum):
    QUESTION = "QUESTION"
    SCAFFOLD_L1 = "SCAFFOLD_L1"
    SCAFFOLD_L2 = "SCAFFOLD_L2"
    SCAFFOLD_L3 = "SCAFFOLD_L3"
    REANSWER = "REANSWER"
    RETEST = "RETEST"
    RESULT = "RESULT"


class RecallLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    FAILURE = "Failure"


@dataclass(frozen=True)
class SessionConfig:
    role: str
    domains: list[str]
    self_ratings: dict[str, str]


@dataclass
class KnowledgeAttempt:
    topic: str
    domain: str
    original_question: str
    self_rating: str
    first_recall_level: RecallLevel | None = None
    first_answer: str = ""
    retest_question: str = ""
    retest_recall_level: RecallLevel | None = None
    retest_answer: str = ""
    verified: bool = False


@dataclass
class TrainingSession:
    id: str
    config: SessionConfig
    status: TrainingStatus
    questions: list[KnowledgeAttempt]
    current_index: int
    current_hint_level: RecallLevel
    retest_queue: list[int] = field(default_factory=list)
    interleave_remaining: int = 0

    @property
    def current_attempt(self) -> KnowledgeAttempt:
        return self.questions[self.current_index]


QUESTION_BANK = {
    "network": [
        (
            "TCP 三次握手",
            "TCP 为什么需要三次握手？",
            "如果 TCP 建立连接只进行两次握手，可能出现什么问题？",
        ),
        (
            "HTTP 与 HTTPS",
            "HTTPS 相比 HTTP 主要解决了什么问题？",
            "为什么只用 HTTP 传输登录信息会有风险？",
        ),
    ],
    "os": [
        (
            "进程与线程",
            "进程和线程的核心区别是什么？",
            "为什么线程切换通常比进程切换更轻？",
        ),
        (
            "死锁条件",
            "操作系统中死锁发生通常需要哪些条件？",
            "为什么破坏循环等待可以避免死锁？",
        )
    ],
    "db": [
        (
            "数据库索引",
            "数据库索引为什么能加速查询？",
            "为什么索引太多反而可能拖慢写入？",
        ),
        (
            "事务隔离",
            "数据库事务隔离级别主要想解决什么问题？",
            "为什么较低隔离级别可能出现不可重复读？",
        )
    ],
    "ds": [
        (
            "哈希表",
            "哈希表查询为什么通常接近 O(1)？",
            "哈希冲突会怎样影响查询性能？",
        ),
        (
            "二叉搜索树",
            "二叉搜索树为什么能支持较快查找？",
            "为什么退化成链表后查找效率会变差？",
        )
    ],
}


def start_session(config: SessionConfig) -> TrainingSession:
    if not 1 <= len(config.domains) <= 3:
        raise ValueError("Select 1 to 3 domains.")
    for domain in config.domains:
        if domain not in config.self_ratings:
            raise ValueError(f"Missing self rating for {domain}.")

    questions = _build_attempts(config)
    return TrainingSession(
        id=str(uuid4()),
        config=config,
        status=TrainingStatus.QUESTION,
        questions=questions,
        current_index=0,
        current_hint_level=RecallLevel.L0,
    )


def mark_stuck(session: TrainingSession) -> TrainingSession:
    session.status = TrainingStatus.SCAFFOLD_L1
    session.current_hint_level = RecallLevel.L1
    return session


def advance_scaffold(session: TrainingSession, user_text: str) -> TrainingSession:
    _append_first_answer(session, user_text)
    if session.status == TrainingStatus.SCAFFOLD_L1:
        session.status = TrainingStatus.SCAFFOLD_L2
        session.current_hint_level = RecallLevel.L2
    elif session.status == TrainingStatus.SCAFFOLD_L2:
        session.status = TrainingStatus.SCAFFOLD_L3
        session.current_hint_level = RecallLevel.L3
    elif session.status == TrainingStatus.SCAFFOLD_L3:
        session.status = TrainingStatus.REANSWER
        session.current_attempt.first_recall_level = session.current_hint_level
    else:
        raise ValueError(f"Cannot advance scaffold from {session.status}.")
    return session


def recover_from_scaffold(session: TrainingSession, user_text: str) -> TrainingSession:
    if session.status not in {
        TrainingStatus.SCAFFOLD_L1,
        TrainingStatus.SCAFFOLD_L2,
        TrainingStatus.SCAFFOLD_L3,
    }:
        raise ValueError(f"Cannot recover from {session.status}.")
    _append_first_answer(session, user_text)
    session.current_attempt.first_recall_level = session.current_hint_level
    session.status = TrainingStatus.REANSWER
    return session


def answer_current_question(
    session: TrainingSession,
    answer: str,
    judged_level: RecallLevel | None = None,
) -> TrainingSession:
    attempt = session.current_attempt
    if session.status == TrainingStatus.RETEST:
        attempt.retest_answer = answer
        attempt.retest_recall_level = judged_level or RecallLevel.L0
        attempt.verified = attempt.retest_recall_level == RecallLevel.L0
        if session.retest_queue:
            session.current_index = session.retest_queue.pop(0)
            session.current_hint_level = RecallLevel.L0
            session.status = TrainingStatus.RETEST
        else:
            session.status = TrainingStatus.RESULT
        return session

    if session.status == TrainingStatus.REANSWER:
        attempt.first_answer = answer
        if attempt.first_recall_level is None:
            attempt.first_recall_level = session.current_hint_level
        _schedule_retest(session)
        _move_to_next_interleaving_question(session)
        return session

    if session.status == TrainingStatus.QUESTION:
        attempt.first_answer = answer
        attempt.first_recall_level = judged_level or RecallLevel.L0
        _move_to_next_interleaving_question(session)
        return session

    raise ValueError(f"Cannot answer while in {session.status}.")


def get_result_summary(session: TrainingSession) -> dict[str, Any]:
    attempts = []
    for attempt in session.questions:
        if attempt.first_recall_level is None:
            continue
        first_level = attempt.first_recall_level.value
        retest_level = attempt.retest_recall_level.value if attempt.retest_recall_level else "-"
        attempts.append(
            {
                "topic": attempt.topic,
                "self_rating": attempt.self_rating,
                "first_recall_level": first_level,
                "retest_recall_level": retest_level,
                "transition": f"{first_level} -> {retest_level}",
                "verified": attempt.verified,
            }
        )

    return {
        "trained_topics": len(attempts),
        "independent_first": sum(1 for item in attempts if item["first_recall_level"] == "L0"),
        "recall_failures": sum(1 for item in attempts if item["first_recall_level"] != "L0"),
        "verified_after_training": sum(1 for item in attempts if item["verified"]),
        "attempts": attempts,
    }


def serialize_session(session: TrainingSession) -> dict[str, Any]:
    attempt = session.current_attempt
    return {
        "id": session.id,
        "status": session.status.value,
        "current_hint_level": session.current_hint_level.value,
        "current": {
            "topic": attempt.topic,
            "domain": attempt.domain,
            "question": attempt.retest_question if session.status == TrainingStatus.RETEST else attempt.original_question,
            "original_question": attempt.original_question,
            "retest_question": attempt.retest_question,
            "self_rating": attempt.self_rating,
        },
        "summary": get_result_summary(session),
    }


def _build_attempts(config: SessionConfig) -> list[KnowledgeAttempt]:
    attempts: list[KnowledgeAttempt] = []
    for domain in config.domains:
        for topic, question, retest_question in QUESTION_BANK.get(domain, []):
            attempts.append(
                KnowledgeAttempt(
                    topic=topic,
                    domain=domain,
                    original_question=question,
                    self_rating=config.self_ratings[domain],
                    retest_question=retest_question,
                )
            )
    if not attempts:
        raise ValueError("No questions available for selected domains.")
    return attempts


def _append_first_answer(session: TrainingSession, text: str) -> None:
    current = session.current_attempt
    if text.strip():
        current.first_answer = (current.first_answer + "\n" + text).strip()


def _schedule_retest(session: TrainingSession) -> None:
    session.retest_queue.append(session.current_index)
    session.interleave_remaining = 1


def _move_to_next_interleaving_question(session: TrainingSession) -> None:
    if session.retest_queue and session.interleave_remaining <= 0:
        session.current_index = session.retest_queue.pop(0)
        session.current_hint_level = RecallLevel.L0
        session.status = TrainingStatus.RETEST
        return

    if session.retest_queue:
        session.interleave_remaining -= 1

    next_index = _next_unfinished_first_attempt(session)
    if next_index is None:
        if session.retest_queue:
            session.current_index = session.retest_queue.pop(0)
            session.current_hint_level = RecallLevel.L0
            session.status = TrainingStatus.RETEST
        else:
            session.status = TrainingStatus.RESULT
        return

    session.current_index = next_index
    session.current_hint_level = RecallLevel.L0
    session.status = TrainingStatus.QUESTION


def _next_unfinished_first_attempt(session: TrainingSession) -> int | None:
    for index, attempt in enumerate(session.questions):
        if index == session.current_index:
            continue
        if attempt.first_recall_level is None:
            return index
    return None
