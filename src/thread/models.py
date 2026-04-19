"""Data classes for the thread feature.

スレッド機能用のデータクラス群.

``Thread`` はスレッド1件分の状態を保持する append-only な構造体で,
タイトルや参加者・自分宛て / 役職関連フラグといったメタ情報を含む.
``ThreadAssignment`` は ``ThreadInference.assign()`` の戻り値で,
新着 talk をどのスレッドに紐付けたかを表す.
``InferenceContext`` は推定戦略に渡す不変コンテキスト
(自分の名前・役職・全エージェント名・キーワード辞書など) をまとめる.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiwolf_nlp_common.packet import Role


@dataclass
class Thread:
    """A single thread of grouped talks.

    1 つのスレッドを表す. 1 つの talk は一度割り当てられたら別スレッドに
    再分類されない (append-only) 設計のため, 過去の LLM 履歴と整合する.

    Attributes:
        id (int): Thread ID (1 始まりのシーケンシャル) / スレッドID
        title (str): Title generated heuristically at first appearance / 初出時に生成し以降固定するタイトル
        participants (set[str]): Agent names that have spoken in this thread /
            このスレッドで発言したエージェント名集合
        talk_keys (list[tuple[int, int, int]]): (day, turn, idx) of talks belonging to this thread /
            このスレッドに属する talk のキー一覧 (時系列順)
        is_broadcast (bool): True if started by a broadcast utterance ("みんな" 等) /
            broadcast 発話起点の場合 True
        role_relevant (bool): True if any talk in this thread is relevant to self_role /
            このスレッド内のいずれかの talk が自分の役職に関連していれば True
        mentions_self (bool): True if self has been mentioned or has spoken in this thread /
            このスレッドで自分が言及された / 自分が発言したことがあれば True
        created_day (int): Day when this thread was created / 作成された日
        created_turn (int): Turn when this thread was created / 作成された turn
        last_active_day (int): Day of the most recent talk in this thread / 最終アクティブ日
        last_active_turn (int): Turn of the most recent talk / 最終アクティブ turn
    """

    id: int
    title: str
    participants: set[str] = field(default_factory=set[str])
    talk_keys: list[tuple[int, int, int]] = field(default_factory=list[tuple[int, int, int]])
    is_broadcast: bool = False
    role_relevant: bool = False
    mentions_self: bool = False
    created_day: int = 0
    created_turn: int = 0
    last_active_day: int = 0
    last_active_turn: int = 0


@dataclass(frozen=True)
class ThreadAssignment:
    """Result of ``ThreadInference.assign()``.

    ``ThreadInference.assign()`` の戻り値. ``thread_id`` が既存スレッドの場合は
    ``is_new_thread=False``, 新規スレッドを立てる場合は ``thread_id`` は仮値で
    ``is_new_thread=True`` となる (実際の ID 採番は ``ThreadManager`` が行う).

    Attributes:
        thread_id (int): Existing thread ID (only meaningful when is_new_thread=False) /
            既存スレッドID (is_new_thread=True のときは使用されない)
        is_new_thread (bool): Whether to create a new thread / 新規スレッドを立てるか
        is_broadcast (bool): Whether the new thread should be a broadcast thread /
            新規スレッドを立てる場合, broadcast 種別かどうか
        reason (str): Short human-readable reason (logged) / 構造ログに残す短い理由
        suggested_title (str | None): Title to use when creating a new thread (LLM
            strategy のみ). None なら ThreadManager が heuristic タイトルを生成する /
            新規スレッド作成時に採用するタイトル (LLM 戦略のみ). None なら heuristic.
    """

    thread_id: int
    is_new_thread: bool
    is_broadcast: bool
    reason: str
    suggested_title: str | None = None


@dataclass(frozen=True)
class InferenceContext:
    """Immutable context passed to ``ThreadInference.assign()``.

    ``ThreadInference.assign()`` に渡す不変コンテキスト. ゲーム開始時に確定する
    情報 (自分の名前・役職・全エージェント名) と, 言語別に読み込んだキーワード辞書
    をまとめる.

    Attributes:
        self_agent (str): Self agent's name / 自分のエージェント名
        self_role (Role): Self agent's role / 自分の役職
        all_agents (frozenset[str]): All agent names in the game / ゲーム参加者全員の名前
        broadcast_keywords (tuple[str, ...]): Keywords that mark broadcast utterances /
            broadcast 発話を判定するキーワード
        role_keywords (tuple[str, ...]): Keywords relevant to self_role /
            自分の役職に関連するキーワード
    """

    self_agent: str
    self_role: Role
    all_agents: frozenset[str]
    broadcast_keywords: tuple[str, ...]
    role_keywords: tuple[str, ...]
