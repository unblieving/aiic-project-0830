import unittest

from recall_trainer.state_machine import (
    RecallLevel,
    SessionConfig,
    TrainingStatus,
    advance_scaffold,
    answer_current_question,
    build_weighted_domain_sequence,
    get_result_summary,
    mark_stuck,
    recover_from_scaffold,
    start_session,
)


class StateMachineTests(unittest.TestCase):
    def test_start_session_requires_one_to_three_domains(self):
        with self.assertRaises(ValueError):
            start_session(SessionConfig(role="backend", domains=[], self_ratings={}))

        with self.assertRaises(ValueError):
            start_session(
                SessionConfig(
                    role="backend",
                    domains=["network", "os", "db", "ds"],
                    self_ratings={
                        "network": "high",
                        "os": "mid",
                        "db": "low",
                        "ds": "mid",
                    },
                )
            )

    def test_start_session_creates_cold_question_from_selected_domain(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network"],
                self_ratings={"network": "high"},
            )
        )

        self.assertEqual(session.status, TrainingStatus.QUESTION)
        self.assertEqual(session.current_attempt.topic, "TCP 三次握手")
        self.assertEqual(session.current_attempt.self_rating, "high")
        self.assertIn("TCP", session.current_attempt.original_question)

    def test_start_session_builds_about_six_questions(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os", "db"],
                self_ratings={"network": "high", "os": "mid", "db": "low"},
            )
        )

        self.assertEqual(len(session.questions), 6)

    def test_self_ratings_weight_domain_sampling(self):
        sequence = build_weighted_domain_sequence(
            ["network", "os", "db"],
            {"network": "high", "os": "mid", "db": "low"},
            total=6,
        )

        self.assertEqual(sequence.count("network"), 3)
        self.assertEqual(sequence.count("os"), 2)
        self.assertEqual(sequence.count("db"), 1)

    def test_weighted_sampling_normalizes_missing_rating_levels(self):
        sequence = build_weighted_domain_sequence(
            ["network", "db"],
            {"network": "high", "db": "low"},
            total=6,
        )

        self.assertEqual(sequence.count("network"), 5)
        self.assertEqual(sequence.count("db"), 1)

    def test_stuck_progresses_through_scaffolds_then_requires_reanswer(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network"],
                self_ratings={"network": "high"},
            )
        )

        session = mark_stuck(session)
        self.assertEqual(session.status, TrainingStatus.SCAFFOLD_L1)
        self.assertEqual(session.current_hint_level, RecallLevel.L1)

        session = advance_scaffold(session, "还是想不起来")
        self.assertEqual(session.status, TrainingStatus.SCAFFOLD_L2)
        self.assertEqual(session.current_hint_level, RecallLevel.L2)

        session = advance_scaffold(session, "和双方确认有关")
        self.assertEqual(session.status, TrainingStatus.SCAFFOLD_L3)
        self.assertEqual(session.current_hint_level, RecallLevel.L3)

        session = advance_scaffold(session, "可以讲了")
        self.assertEqual(session.status, TrainingStatus.REANSWER)
        self.assertEqual(session.current_attempt.first_recall_level, RecallLevel.L3)

    def test_reanswer_schedules_delayed_variant_retest_after_interleaving(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os"],
                self_ratings={"network": "high", "os": "mid"},
            )
        )
        session = mark_stuck(session)
        session = advance_scaffold(session, "不知道")
        session = advance_scaffold(session, "双方确认")
        session = advance_scaffold(session, "可以讲了")
        session = answer_current_question(session, "三次握手确认双方发送和接收能力")

        self.assertEqual(session.status, TrainingStatus.QUESTION)
        self.assertNotEqual(session.current_attempt.topic, "TCP 三次握手")

        session = answer_current_question(session, "进程是资源分配单位")
        self.assertEqual(session.status, TrainingStatus.RETEST)
        self.assertEqual(session.current_attempt.topic, "TCP 三次握手")
        self.assertNotEqual(
            session.current_attempt.original_question,
            session.current_attempt.retest_question,
        )

    def test_user_can_recover_at_l2_then_must_reanswer(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os"],
                self_ratings={"network": "high", "os": "mid"},
            )
        )
        session = mark_stuck(session)
        session = advance_scaffold(session, "和双方确认有关")
        session = recover_from_scaffold(session, "我想起来一些了")

        self.assertEqual(session.status, TrainingStatus.REANSWER)
        self.assertEqual(session.current_attempt.first_recall_level, RecallLevel.L2)

    def test_result_summary_shows_first_to_retest_recall_transition(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os"],
                self_ratings={"network": "high", "os": "mid"},
            )
        )
        session = mark_stuck(session)
        session = advance_scaffold(session, "不知道")
        session = advance_scaffold(session, "双方确认")
        session = advance_scaffold(session, "可以讲了")
        session = answer_current_question(session, "三次握手确认双方发送和接收能力")
        session = answer_current_question(session, "进程和线程不同")
        session = answer_current_question(session, "两次握手可能产生历史连接问题")

        summary = get_result_summary(session)

        tcp = summary["attempts"][0]
        self.assertEqual(tcp["topic"], "TCP 三次握手")
        self.assertEqual(tcp["self_rating"], "high")
        self.assertEqual(tcp["first_recall_level"], "L3")
        self.assertEqual(tcp["retest_recall_level"], "L0")
        self.assertEqual(tcp["transition"], "L3 -> L0")
        self.assertTrue(tcp["verified"])

    def test_failed_retest_is_not_marked_verified(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os"],
                self_ratings={"network": "high", "os": "mid"},
            )
        )
        session = mark_stuck(session)
        session = recover_from_scaffold(session, "双方确认")
        session = answer_current_question(session, "三次握手确认双方发送和接收能力")
        session = answer_current_question(session, "进程和线程不同")
        session = answer_current_question(session, "还是不会", RecallLevel.FAILURE)

        tcp = get_result_summary(session)["attempts"][0]
        self.assertEqual(tcp["retest_recall_level"], "Failure")
        self.assertEqual(tcp["transition"], "L1 -> Failure")
        self.assertFalse(tcp["verified"])

    def test_knowledge_gap_skips_scaffolding_and_continues(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os"],
                self_ratings={"network": "high", "os": "mid"},
            )
        )

        session = answer_current_question(session, "TCP 是数据库索引", RecallLevel.KNOWLEDGE_GAP)

        first = get_result_summary(session)["attempts"][0]
        self.assertEqual(first["first_recall_level"], "Knowledge Gap")
        self.assertTrue(first["knowledge_gap"])
        self.assertEqual(session.status, TrainingStatus.QUESTION)
        self.assertNotEqual(session.current_attempt.topic, "TCP 三次握手")

    def test_recall_failure_answer_enters_scaffolding(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os"],
                self_ratings={"network": "high", "os": "mid"},
            )
        )

        session = answer_current_question(session, "我想不起来了", RecallLevel.FAILURE)

        self.assertEqual(session.status, TrainingStatus.SCAFFOLD_L1)
        self.assertEqual(session.current_hint_level, RecallLevel.L1)
        self.assertIsNone(session.current_attempt.first_recall_level)

    def test_result_summary_counts_knowledge_gaps_separately(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os"],
                self_ratings={"network": "high", "os": "mid"},
            )
        )

        session = answer_current_question(session, "TCP 是数据库索引", RecallLevel.KNOWLEDGE_GAP)
        summary = get_result_summary(session)

        self.assertEqual(summary["knowledge_gaps"], 1)
        self.assertEqual(summary["recall_failures"], 0)
        self.assertEqual(summary["independent_first"], 0)

    def test_all_queued_retests_are_asked_before_result(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["network", "os", "db"],
                self_ratings={"network": "high", "os": "mid", "db": "low"},
            )
        )
        session.current_index = 0
        session.status = TrainingStatus.RETEST
        session.retest_queue = [1]
        session.questions[0].first_recall_level = RecallLevel.L1
        session.questions[1].first_recall_level = RecallLevel.L2

        session = answer_current_question(session, "TCP 变式回答")
        self.assertEqual(session.status, TrainingStatus.RETEST)
        self.assertEqual(session.current_attempt.topic, "进程与线程")

        session = answer_current_question(session, "OS 变式回答")
        self.assertEqual(session.status, TrainingStatus.RESULT)

    def test_single_domain_has_interleaving_question_before_retest(self):
        session = start_session(
            SessionConfig(
                role="backend",
                domains=["os"],
                self_ratings={"os": "mid"},
            )
        )
        session = mark_stuck(session)
        session = recover_from_scaffold(session, "资源")
        session = answer_current_question(session, "进程线程完整回答")

        self.assertEqual(session.status, TrainingStatus.QUESTION)
        self.assertNotEqual(session.current_attempt.topic, "进程与线程")


if __name__ == "__main__":
    unittest.main()
