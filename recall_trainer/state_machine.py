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
    KNOWLEDGE_GAP = "Knowledge Gap"


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
    standard_answer: str = ""
    reference_answer: str = ""
    key_points: list[str] = field(default_factory=list)


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
        (
            "TCP 拥塞控制",
            "TCP 为什么需要拥塞控制？",
            "如果网络已经拥塞，TCP 继续快速发送数据会发生什么？",
        ),
        (
            "DNS 解析",
            "浏览器访问域名时，DNS 解析大致做了什么？",
            "为什么本地 DNS 缓存能加快访问？",
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
        ),
        (
            "虚拟内存",
            "操作系统为什么需要虚拟内存？",
            "如果进程直接使用物理地址，会带来什么问题？",
        ),
        (
            "用户态与内核态",
            "为什么操作系统要区分用户态和内核态？",
            "系统调用为什么需要从用户态切换到内核态？",
        ),
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
        ),
        (
            "MVCC",
            "MVCC 主要解决了数据库并发读写中的什么问题？",
            "为什么快照读可以减少读写阻塞？",
        ),
        (
            "B+ 树索引",
            "数据库索引为什么常用 B+ 树结构？",
            "为什么 B+ 树适合范围查询？",
        ),
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
        ),
        (
            "堆",
            "堆结构通常适合解决哪类 Top K 问题？",
            "为什么小顶堆可以维护前 K 大元素？",
        ),
        (
            "链表与数组",
            "数组和链表在查询、插入删除上的核心差异是什么？",
            "为什么数组随机访问快而链表插入删除更灵活？",
        ),
    ],
    "java": [
        (
            "JVM 垃圾回收",
            "JVM 垃圾回收主要解决什么问题？",
            "为什么可达性分析能判断对象是否还需要保留？",
        ),
        (
            "Java 线程池",
            "Java 线程池为什么能提升服务端性能？",
            "如果无节制创建线程，系统可能出现什么问题？",
        ),
        (
            "volatile",
            "Java 中 volatile 主要保证了什么？",
            "为什么 volatile 不能替代所有锁的场景？",
        ),
    ],
    "redis": [
        (
            "Redis 缓存击穿",
            "Redis 缓存击穿是什么场景？",
            "热点 key 失效时为什么可能打垮数据库？",
        ),
        (
            "Redis 持久化",
            "Redis RDB 和 AOF 的核心区别是什么？",
            "为什么 AOF 通常数据丢失更少但文件更大？",
        ),
        (
            "Redis 分布式锁",
            "Redis 实现分布式锁时为什么要设置过期时间？",
            "如果锁没有过期时间，服务宕机会导致什么问题？",
        ),
    ],
    "system_design": [
        (
            "限流",
            "服务端为什么需要限流？",
            "如果没有限流，突发流量会怎样影响系统？",
        ),
        (
            "消息队列",
            "消息队列在系统设计中主要解决什么问题？",
            "为什么异步削峰能保护下游服务？",
        ),
        (
            "缓存一致性",
            "系统设计里缓存和数据库为什么会出现一致性问题？",
            "更新数据库后缓存没处理好会出现什么现象？",
        ),
    ],
}

RATING_WEIGHTS = {
    "high": 0.5,
    "medium": 0.4,
    "mid": 0.4,
    "low": 0.1,
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
        if judged_level == RecallLevel.KNOWLEDGE_GAP:
            attempt.first_recall_level = RecallLevel.KNOWLEDGE_GAP
            _move_to_next_interleaving_question(session)
            return session
        if attempt.first_recall_level is None:
            attempt.first_recall_level = session.current_hint_level
        _schedule_retest(session)
        _move_to_next_interleaving_question(session)
        return session

    if session.status == TrainingStatus.QUESTION:
        attempt.first_answer = answer
        if judged_level == RecallLevel.FAILURE:
            session.status = TrainingStatus.SCAFFOLD_L1
            session.current_hint_level = RecallLevel.L1
            return session
        attempt.first_recall_level = judged_level or RecallLevel.L0
        if judged_level == RecallLevel.KNOWLEDGE_GAP:
            _move_to_next_interleaving_question(session)
            return session
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
                "knowledge_gap": attempt.first_recall_level == RecallLevel.KNOWLEDGE_GAP,
                "standard_answer": attempt.standard_answer,
                "reference_answer": attempt.reference_answer,
                "key_points": attempt.key_points,
                "user_answer": attempt.first_answer,
            }
        )

    improved_recall = sum(
        1
        for item in attempts
        if item["first_recall_level"] not in {"L0", "Knowledge Gap"}
        and item["retest_recall_level"] == "L0"
    )
    knowledge_gap_count = sum(1 for item in attempts if item["knowledge_gap"])

    return {
        "trained_topics": len(attempts),
        "independent_first": sum(1 for item in attempts if item["first_recall_level"] == "L0"),
        "recall_failures": sum(
            1
            for item in attempts
            if item["first_recall_level"] not in {"L0", "Knowledge Gap"}
        ),
        "knowledge_gaps": knowledge_gap_count,
        "knowledgeGapCount": knowledge_gap_count,
        "verified_after_training": sum(1 for item in attempts if item["verified"]),
        "improved_recall": improved_recall,
        "improvedRecallCount": improved_recall,
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
    domain_cursors = {domain: 0 for domain in config.domains}
    for domain in build_weighted_domain_sequence(config.domains, config.self_ratings, total=6):
        bank = QUESTION_BANK.get(domain, [])
        if not bank:
            continue
        topic, question, retest_question = bank[domain_cursors[domain] % len(bank)]
        domain_cursors[domain] += 1
        attempts.append(
            KnowledgeAttempt(
                topic=topic,
                domain=domain,
                original_question=question,
                self_rating=config.self_ratings[domain],
                retest_question=retest_question,
            )
        )
    if len(attempts) < 5:
        for domain in config.domains:
            bank = QUESTION_BANK.get(domain, [])
            for topic, question, retest_question in bank:
                if len(attempts) >= 5:
                    break
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


def build_weighted_domain_sequence(
    domains: list[str],
    self_ratings: dict[str, str],
    total: int = 6,
) -> list[str]:
    weighted = []
    for domain in domains:
        rating = self_ratings.get(domain, "medium")
        weighted.append((domain, RATING_WEIGHTS.get(rating, 0.4)))
    weight_sum = sum(weight for _domain, weight in weighted)
    if weight_sum <= 0:
        return domains[:total]

    raw_counts = [(domain, total * weight / weight_sum) for domain, weight in weighted]
    counts = {domain: int(raw) for domain, raw in raw_counts}
    for domain in domains:
        if counts.get(domain, 0) == 0:
            counts[domain] = 1

    while sum(counts.values()) > total:
        candidates = [domain for domain in counts if counts[domain] > 1]
        if not candidates:
            break
        domain = min(candidates, key=lambda item: dict(raw_counts)[item] - int(dict(raw_counts)[item]))
        counts[domain] -= 1

    remainders = sorted(
        raw_counts,
        key=lambda item: item[1] - int(item[1]),
        reverse=True,
    )
    cursor = 0
    while sum(counts.values()) < total and remainders:
        counts[remainders[cursor % len(remainders)][0]] += 1
        cursor += 1

    sequence: list[str] = []
    remaining = counts.copy()
    while len(sequence) < total and any(count > 0 for count in remaining.values()):
        for domain in domains:
            if remaining.get(domain, 0) > 0:
                sequence.append(domain)
                remaining[domain] -= 1
                if len(sequence) == total:
                    break
    return sequence


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
