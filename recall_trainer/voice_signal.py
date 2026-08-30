"""Voice signal analyzer for recall difficulty detection.

Extracts timing and hesitation signals from speech to help
distinguish Recall Failure from Knowledge Gap.

IMPORTANT: Voice signals (pauses, hesitation) are evidence of
*Retrieval Difficulty*, NOT Knowledge Gap.  Knowledge Gap must
be determined by semantic content analysis (DeepSeek judge).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Hesitation and recall-failure marker lists
# ---------------------------------------------------------------------------

_EXPLICIT_RECALL_FAILURE_MARKERS: list[str] = [
    "不知道", "不太知道", "忘了", "忘记了", "想不起来",
    "记不起来", "不记得", "不记得了", "卡住了", "没想起来",
    "我忘了", "我卡住了", "我记得学过", "学过但是忘了",
    "这个我学过但是忘了", "有印象但是想不起来",
    "i don't know", "i dont know", "i forgot",
    "can't remember", "cant remember", "can't recall",
    "cant recall",
]

_HESITATION_MARKERS: list[str] = [
    "嗯", "额", "呃",
    "em", "emm", "emmm", "emmmm",
    "那个", "就是", "怎么说", "我想想",
    "这个……", "这个...",
]

# Pre-compile a regex for hesitation counting.
# We match whole-word occurrences to avoid over-counting
# normal speech that happens to contain these substrings.
_HESITATION_RE = re.compile(
    r"(?:" + "|".join(re.escape(m) for m in _HESITATION_MARKERS) + r")",
    re.IGNORECASE,
)


@dataclass
class VoiceSignals:
    """Collected voice timing and hesitation signals."""

    answer_duration_ms: int = 0
    first_speech_latency_ms: int = 0
    max_pause_ms: int = 0
    hesitation_count: int = 0
    explicit_recall_failure: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "answerDurationMs": self.answer_duration_ms,
            "firstSpeechLatencyMs": self.first_speech_latency_ms,
            "maxPauseMs": self.max_pause_ms,
            "hesitationCount": self.hesitation_count,
            "explicitRecallFailure": self.explicit_recall_failure,
        }


def analyze_transcript(transcript: str) -> dict[str, Any]:
    """Analyze a transcript string for hesitation and recall-failure markers.

    Returns a dict with ``hesitation_count`` and ``explicit_recall_failure``.
    """
    text = transcript.strip()
    if not text:
        return {"hesitation_count": 0, "explicit_recall_failure": False}

    lower = text.lower()

    # Check explicit recall failure
    explicit = any(marker in lower for marker in _EXPLICIT_RECALL_FAILURE_MARKERS)

    # Count hesitation markers
    hesitation_count = len(_HESITATION_RE.findall(text))

    return {
        "hesitation_count": hesitation_count,
        "explicit_recall_failure": explicit,
    }


def build_voice_signals(
    transcript: str,
    frontend_signals: dict[str, Any] | None = None,
) -> VoiceSignals:
    """Combine transcript analysis with frontend timing signals.

    ``frontend_signals`` may contain:
    - ``answerDurationMs``
    - ``firstSpeechLatencyMs``
    - ``maxPauseMs``
    """
    frontend_signals = frontend_signals or {}
    transcript_analysis = analyze_transcript(transcript)

    return VoiceSignals(
        answer_duration_ms=int(frontend_signals.get("answerDurationMs", 0)),
        first_speech_latency_ms=int(frontend_signals.get("firstSpeechLatencyMs", 0)),
        max_pause_ms=int(frontend_signals.get("maxPauseMs", 0)),
        hesitation_count=transcript_analysis["hesitation_count"],
        explicit_recall_failure=transcript_analysis["explicit_recall_failure"],
    )


def voice_signals_suggest_recall_failure(signals: VoiceSignals) -> bool:
    """Return True if voice signals strongly suggest Recall Failure.

    This is used as additional evidence for the judge.
    IMPORTANT: This never indicates Knowledge Gap.
    """
    if signals.explicit_recall_failure:
        return True
    # Long first speech latency suggests difficulty retrieving
    if signals.first_speech_latency_ms > 5000:
        return True
    # Long pause during answer suggests retrieval difficulty
    if signals.max_pause_ms > 4000:
        return True
    # Many hesitation markers suggest difficulty
    if signals.hesitation_count >= 5:
        return True
    return False
