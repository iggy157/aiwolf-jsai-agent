"""Step A (ThreadDecision): pre-talk reasoning about thread relevance and action.

Step A (発話前判断). 発話を生成する前に, 現在のスレッド一覧と新着 talk から「どの
スレッドに返信すべきか / skip すべきか / over すべきか / 新規スレッドを立てるべきか」
を ``llm.thread`` 系統に問い合わせる.

LLM 出力は strict JSON で, 1 度だけリトライ. それでもパース失敗の場合は
``{action: 'reply', target_thread: None, reason: '...'}`` にフォールバックして
Step B (発話生成) を妨げない.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

DecisionAction = Literal["reply", "skip", "over", "new_thread"]
_ALLOWED_ACTIONS: tuple[str, ...] = ("reply", "skip", "over", "new_thread")
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_FALLBACK_REASON = "Step A 出力のパースに失敗したため reply にフォールバック"


@dataclass(frozen=True)
class StepADecision:
    """Parsed result of Step A (ThreadDecision) LLM call.

    Step A LLM 呼び出しのパース結果. ``action`` は固定 4 値, ``target_thread`` は
    ``reply`` 時のみ意味を持つ ID, それ以外は None でも可.

    Attributes:
        target_thread (int | None): Target thread ID for ``reply`` (None otherwise) /
            返信先スレッド ID (reply 時のみ意味あり)
        action (DecisionAction): One of reply / skip / over / new_thread /
            次の発話アクション
        reason (str): Short one-sentence reason / 1 文の短い理由
    """

    target_thread: int | None
    action: DecisionAction
    reason: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly dict (for structure log).

        構造ログ用の JSON 互換 dict を返す.
        """
        return asdict(self)


class ThreadDecision:
    """Run Step A: ask the thread LLM what to do next.

    Step A を実行する: 発話生成前にスレッド LLM に「次に何をすべきか」を尋ねる.

    LLM 呼び出し本体は ``invoker`` (``Callable[[str], str | None]``) として外から
    注入する. これにより ``Agent`` 側の cost / logger 配線にそのまま乗せつつ,
    本クラスは「プロンプト構築 + 出力パース + リトライ + フォールバック」だけを担当する.
    """

    def __init__(
        self,
        invoker: Callable[[str], str | None],
    ) -> None:
        """Initialize with an LLM invoker.

        LLM 呼び出し関数 (``invoker``) を注入して初期化する.

        Args:
            invoker (Callable[[str], str | None]): Function that takes the prompt and
                returns the raw response text (or None on failure) /
                プロンプトを受け取って生レスポンス文字列を返す関数 (失敗時 None)
        """
        self._invoke = invoker

    def decide(self, prompt: str) -> StepADecision:
        """Send ``prompt`` to the thread LLM and parse the JSON output.

        ``prompt`` をスレッド LLM に送り, JSON 出力をパースする. 1 度だけリトライ
        (同じ prompt を再送) し, それでも失敗なら ``reply`` フォールバックを返す.

        Args:
            prompt (str): The Step A prompt string / Step A プロンプト

        Returns:
            StepADecision: Parsed decision (or fallback) / パース済み判断 (失敗時はフォールバック)
        """
        for attempt in range(2):
            raw = self._invoke(prompt)
            parsed = _parse(raw)
            if parsed is not None:
                return parsed
            logger.warning("Step A parse failed (attempt %d/2)", attempt + 1)
        return StepADecision(target_thread=None, action="reply", reason=_FALLBACK_REASON)


def _parse(raw: str | None) -> StepADecision | None:  # noqa: PLR0911
    """Parse a raw LLM response into ``StepADecision`` (None on failure).

    生 LLM レスポンスを ``StepADecision`` にパースする. 失敗時は None.
    ```json ... ``` フェンスを除去し, JSON ロード後に schema を検証する.
    """
    if raw is None:
        return None
    text = _FENCE_RE.sub("", raw.strip()).strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    action = data.get("action")
    if action not in _ALLOWED_ACTIONS:
        return None
    target_raw = data.get("target_thread")
    target: int | None = None
    if target_raw is not None:
        try:
            target = int(target_raw)
        except (TypeError, ValueError):
            return None
    reason_raw = data.get("reason", "")
    reason = str(reason_raw) if reason_raw is not None else ""
    return StepADecision(
        target_thread=target,
        action=action,  # type: ignore[arg-type]
        reason=reason,
    )
