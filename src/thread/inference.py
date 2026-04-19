"""Thread inference strategies.

スレッド割当戦略.

``ThreadInference`` は新着 talk を既存スレッド一覧と照らして, どのスレッドに紐付けるか
(あるいは新規スレッドを立てるか) を決定する関数オブジェクトのプロトコル.
``HeuristicThreadInference`` は LLM を使わず, broadcast キーワード・宛先呼称・turn 境界
の3点で決定論的に割り当てる. ``LLMThreadInference`` は Phase5 で追加する.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Protocol

from thread.models import ThreadAssignment

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiwolf_nlp_common.packet import Talk

    from thread.models import InferenceContext, Thread

logger = logging.getLogger(__name__)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class ThreadInference(Protocol):
    """Protocol for thread assignment strategies.

    スレッド割当戦略のプロトコル. 1 つの新着 talk と現在の thread 一覧を受け取り,
    ``ThreadAssignment`` を返す. ``ThreadManager`` 側で append-only に状態を更新する.
    """

    def assign(
        self,
        talk: Talk,
        threads: list[Thread],
        context: InferenceContext,
    ) -> ThreadAssignment:
        """Assign ``talk`` to an existing thread or signal a new one.

        新着 ``talk`` を既存スレッドに割り当てる, または新規スレッドを示す.

        Args:
            talk (Talk): The new incoming talk / 新着 talk
            threads (list[Thread]): Current threads (chronological by id) /
                現在のスレッド一覧 (id 昇順 = 概ね作成順)
            context (InferenceContext): Immutable game context / 不変ゲームコンテキスト

        Returns:
            ThreadAssignment: Decision about which thread to attach to /
                どのスレッドに紐付けるかの決定
        """
        ...


class HeuristicThreadInference:
    """Deterministic thread assignment without any LLM call.

    LLM を使わない決定論的なスレッド割当戦略. 以下の優先順位で判定する:

    1. broadcast キーワードを含む発話: 同 day 内に同一 turn の broadcast スレッドが
       あれば吸収, それ以外 (turn が変わっている / 同 day に broadcast 無し) は新規
       broadcast スレッドを立てる. これにより turn 境界が broadcast の集約境界となる.
    2. 他エージェント名への宛先呼称を含む発話: 名指された agent または発話者が
       参加している最新 thread (broadcast 以外, 同 day 限定) があれば吸収,
       無ければ新規スレッドを立てる.
    3. 宛先なし: 同 turn 内かつ同 day の既存スレッドのうち, 発話者が参加している
       最新スレッドに吸収. 無ければその turn の最新スレッドに吸収. それも無ければ
       独立スレッドを新規に立てる.

    曖昧な場合は ``保守的に独立スレッド化`` する (= 後で LLM 戦略に切り替えれば
    精度が上がるという前提). ``broadcast`` / ``role_relevant`` / ``mentions_self``
    などのフラグ更新は呼び出し側 (``ThreadManager``) で行う.
    """

    def assign(
        self,
        talk: Talk,
        threads: list[Thread],
        context: InferenceContext,
    ) -> ThreadAssignment:
        """Decide which thread the incoming ``talk`` belongs to.

        新着 ``talk`` をどのスレッドに紐付けるか決定する.

        Args:
            talk (Talk): The new talk / 新着 talk
            threads (list[Thread]): Current threads / 現在のスレッド一覧
            context (InferenceContext): Game context / ゲームコンテキスト

        Returns:
            ThreadAssignment: Decision / 割当結果
        """
        text = talk.text or ""
        speaker = talk.agent

        if self._is_broadcast(text, context.broadcast_keywords):
            return self._assign_broadcast(talk, threads)

        mentioned = self._extract_mentions(text, context.all_agents, speaker)
        if mentioned:
            return self._assign_with_mentions(talk, threads, mentioned)

        return self._assign_no_mention(talk, threads, speaker)

    @staticmethod
    def _is_broadcast(text: str, keywords: tuple[str, ...]) -> bool:
        """Return True if any broadcast keyword appears in ``text``.

        ``text`` に broadcast キーワードが1つでも含まれていれば True.
        """
        return any(kw and kw in text for kw in keywords)

    @staticmethod
    def _extract_mentions(
        text: str,
        all_agents: frozenset[str],
        speaker: str,
    ) -> list[str]:
        """Find agent names (other than speaker) referenced in ``text``.

        ``text`` の中から, 発話者以外のエージェント名 (substring match) を抽出する.
        ``@<name>`` 形式と素のエージェント名の双方を拾う. 重複排除した順序付きリスト.
        """
        found: list[str] = []
        seen: set[str] = set()
        for name in sorted(all_agents, key=len, reverse=True):
            if not name or name == speaker:
                continue
            if name in seen:
                continue
            if name in text:
                found.append(name)
                seen.add(name)
        return found

    def _assign_broadcast(
        self,
        talk: Talk,
        threads: list[Thread],
    ) -> ThreadAssignment:
        """Assign rule for broadcast utterances.

        broadcast 発話の割当ルール. 同 day 内に同一 turn の既存 broadcast thread が
        あればそこに吸収, そうでなければ新規 broadcast thread を立てる.
        """
        same_day_broadcasts = [
            t for t in threads if t.is_broadcast and t.last_active_day == talk.day
        ]
        if same_day_broadcasts:
            most_recent = max(same_day_broadcasts, key=lambda t: t.last_active_turn)
            if most_recent.last_active_turn == talk.turn:
                return ThreadAssignment(
                    thread_id=most_recent.id,
                    is_new_thread=False,
                    is_broadcast=True,
                    reason="同turn内の既存broadcastスレッドに吸収",
                )
        return ThreadAssignment(
            thread_id=-1,
            is_new_thread=True,
            is_broadcast=True,
            reason="broadcast: 新規スレッド (turn境界 or 同day内に既存なし)",
        )

    @staticmethod
    def _assign_with_mentions(
        talk: Talk,
        threads: list[Thread],
        mentioned: list[str],
    ) -> ThreadAssignment:
        """Assign rule when the talk contains mentions to other agents.

        発話に他エージェントへの宛先呼称が含まれる場合の割当ルール.
        broadcast 以外 / 同 day 限定で, 名指された agent または発話者のいずれかが
        参加している最新スレッドを探し, 見つかれば吸収, 無ければ新規スレッドを立てる.
        """
        candidates = [
            t
            for t in threads
            if not t.is_broadcast and t.last_active_day == talk.day
        ]
        # 後ろから (= 新しい順) 見て最初にヒットするものを採用.
        for t in reversed(candidates):
            if any(m in t.participants for m in mentioned) or talk.agent in t.participants:
                return ThreadAssignment(
                    thread_id=t.id,
                    is_new_thread=False,
                    is_broadcast=False,
                    reason=f"宛先呼称({','.join(mentioned)})と参加者が一致するスレッドに吸収",
                )
        return ThreadAssignment(
            thread_id=-1,
            is_new_thread=True,
            is_broadcast=False,
            reason=f"宛先呼称({','.join(mentioned)})に該当する既存スレッド無し, 新規作成",
        )

    @staticmethod
    def _assign_no_mention(
        talk: Talk,
        threads: list[Thread],
        speaker: str,
    ) -> ThreadAssignment:
        """Assign rule when there is no mention.

        宛先なし発話の割当ルール. 同 day かつ同 turn の broadcast 以外スレッドのうち,
        発話者参加の最新を優先, 無ければ同 turn 最新, それも無ければ独立スレッド.
        """
        same_turn = [
            t
            for t in threads
            if not t.is_broadcast
            and t.last_active_day == talk.day
            and t.last_active_turn == talk.turn
        ]
        if same_turn:
            speaker_threads = [t for t in same_turn if speaker in t.participants]
            chosen = speaker_threads[-1] if speaker_threads else same_turn[-1]
            why = "同turn内の自身参加スレッドに吸収" if speaker_threads else "同turn内の最新スレッドに吸収"
            return ThreadAssignment(
                thread_id=chosen.id,
                is_new_thread=False,
                is_broadcast=False,
                reason=why,
            )
        return ThreadAssignment(
            thread_id=-1,
            is_new_thread=True,
            is_broadcast=False,
            reason="分類曖昧: 独立スレッドとして新規作成 (保守的判定)",
        )


class LLMThreadInference:
    """LLM-based thread assignment using ``llm.thread`` per incoming talk.

    ``llm.thread`` 系統に 1 talk ごとに問い合わせる LLM 推定戦略. heuristic より
    柔軟だが LLM 呼出が増えコストもかかる. fallback として heuristic を併用し,
    LLM 出力のパース失敗時は heuristic に委ねて確実に割当を決める.

    プロンプト構築は外部 (``prompt_builder``) に委譲し, このクラス自身は Jinja
    ライブラリ依存を持たない. ``invoker`` は ``ThreadDecision`` と同じシグネチャ
    で agent 側から注入する (cost / agent_logger に乗せる).
    """

    def __init__(
        self,
        invoker: Callable[[str], str | None],
        prompt_builder: Callable[[Talk, list[Thread], InferenceContext], str],
        fallback: ThreadInference | None = None,
    ) -> None:
        """Initialize with invoker, prompt builder and optional fallback.

        Args:
            invoker (Callable[[str], str | None]): LLM stateless invoke function /
                LLM stateless 呼出
            prompt_builder (Callable[..., str]): Jinja prompt builder /
                Jinja でプロンプトを組み立てる関数
            fallback (ThreadInference | None): Strategy used on parse failure /
                LLM 出力パース失敗時の代替戦略 (省略時は ``HeuristicThreadInference``)
        """
        self._invoke = invoker
        self._build_prompt = prompt_builder
        self._fallback = fallback or HeuristicThreadInference()

    def assign(
        self,
        talk: Talk,
        threads: list[Thread],
        context: InferenceContext,
    ) -> ThreadAssignment:
        """Assign via LLM, falling back to heuristic on failure.

        LLM で割当を決定. 出力パース失敗時は heuristic にフォールバック.
        """
        prompt = self._build_prompt(talk, threads, context)
        raw = self._invoke(prompt)
        parsed = _parse_llm_assignment(raw, threads)
        if parsed is not None:
            return parsed
        logger.warning("LLM assignment parse failed; falling back to heuristic")
        return self._fallback.assign(talk, threads, context)


def _parse_llm_assignment(  # noqa: PLR0911
    raw: str | None,
    threads: list[Thread],
) -> ThreadAssignment | None:
    """Parse LLM assignment JSON output. Return None on failure.

    LLM 出力 (JSON) を ``ThreadAssignment`` にパース. 失敗時は None.
    期待スキーマ:
        {"action": "existing", "thread_id": <int>, "reason": "..."}
        {"action": "new", "is_broadcast": <bool>, "reason": "..."}
    ``thread_id`` が既存 thread に該当しない場合は None (= fallback) を返す.
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
    reason = str(data.get("reason") or "")
    if action == "existing":
        tid_raw = data.get("thread_id")
        try:
            tid = int(tid_raw) if tid_raw is not None else None
        except (TypeError, ValueError):
            return None
        if tid is None or not any(t.id == tid for t in threads):
            return None
        is_broadcast = next(t.is_broadcast for t in threads if t.id == tid)
        return ThreadAssignment(
            thread_id=tid,
            is_new_thread=False,
            is_broadcast=is_broadcast,
            reason=f"LLM: {reason}" if reason else "LLM",
        )
    if action == "new":
        is_broadcast = bool(data.get("is_broadcast", False))
        title_raw = data.get("title")
        title: str | None = str(title_raw).strip() if title_raw else None
        return ThreadAssignment(
            thread_id=-1,
            is_new_thread=True,
            is_broadcast=is_broadcast,
            reason=f"LLM(new{'/broadcast' if is_broadcast else ''}): {reason}" if reason else "LLM(new)",
            suggested_title=title or None,
        )
    return None
