"""Thread feature: group talk history into threads for richer prompting.

トーク履歴をスレッド化し, より整理された形でプロンプトに渡すための機能.

以下を提供する:
- ``Thread`` / ``ThreadAssignment``: スレッドモデル.
- ``ThreadManager``: スレッド状態の保持と着信時の割当を行う中核クラス.
- ``HeuristicThreadInference``: LLM を使わない決定論的な割当戦略.
- ``LLMThreadInference``: ``llm.thread`` 系統で1件ずつ問い合わせる戦略 (Phase5).
"""

from thread.decision import StepADecision, ThreadDecision
from thread.inference import HeuristicThreadInference, LLMThreadInference, ThreadInference
from thread.models import InferenceContext, Thread, ThreadAssignment
from thread.structure_logger import (
    THREAD_STRUCTURE_SUBDIR,
    StructureLogger,
    render_markdown_summary,
)
from thread.thread_manager import ThreadManager

__all__ = [
    "THREAD_STRUCTURE_SUBDIR",
    "HeuristicThreadInference",
    "InferenceContext",
    "LLMThreadInference",
    "StepADecision",
    "StructureLogger",
    "Thread",
    "ThreadAssignment",
    "ThreadDecision",
    "ThreadInference",
    "ThreadManager",
    "render_markdown_summary",
]
