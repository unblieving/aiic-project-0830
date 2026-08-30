import unittest

from recall_trainer.state_machine import (
    RecallLevel,
    SessionConfig,
    TrainingStatus,
    advance_scaffold,
    answer_current_question,
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


if __name__ == "__main__":
    unittest.main()
