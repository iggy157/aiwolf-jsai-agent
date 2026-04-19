"""Thread state manager.

スレッド状態の保持・更新を担う中核クラス.

``Agent`` インスタンスごとに 1 つ生成され, ``set_packet`` / ``on_talk_received`` から
着信 talk ごとに ``on_new_talk(talk)`` を呼ぶ. 内部で割当戦略 (``ThreadInference``) に
問い合わせ, append-only にスレッド状態を更新する.

``new_talks_since_last_read()`` は multi-turn モードの差分送信 (新規 talk + その所属
スレッド見出しを LLM に渡す) のためのヘルパ. ``mark_read()`` で既読カーソルを進める.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from thread.keywords import load_broadcast_keywords, load_role_keywords
from thread.models import InferenceContext, Thread, ThreadAssignment

if TYPE_CHECKING:
    from aiwolf_nlp_common.packet import Role, Talk

    from thread.inference import ThreadInference

_TITLE_MAX_LEN = 20
_TITLE_DELIMS: tuple[str, ...] = ("。", "?", "!", "\n", "、", "？", "！")  # noqa: RUF001


class ThreadManager:
    """Hold thread state and assign incoming talks append-only.

    スレッド状態を保持し, 着信 talk を append-only に割り当てる.

    ``threads`` は内部的に id 昇順で保持し, ``threads()`` でその snapshot を返す.
    1 つの talk は ``(day, turn, idx)`` をキーにいずれか1スレッドに紐付き, 二度と
    変更されない. day を跨いでも保持し, デフォルトでは古いスレッドの除外は行わない
    (除外したい場合は ``filtered_threads(history_days=N)`` を使う).
    """

    def __init__(
        self,
        self_agent: str,
        self_role: Role,
        all_agents: set[str],
        inference: ThreadInference,
        lang: str,
    ) -> None:
        """Initialize the thread manager.

        ``ThreadManager`` を初期化する.

        Args:
            self_agent (str): Self agent name / 自分のエージェント名
            self_role (Role): Self agent role / 自分の役職
            all_agents (set[str]): All agent names in this game / ゲーム参加者全員の名前
            inference (ThreadInference): Inference strategy / 推定戦略
            lang (str): Language code (jp / en) for keyword dicts / キーワード辞書の言語コード
        """
        self._inference = inference
        self._self_agent = self_agent
        self._self_role = self_role
        self._lang = lang
        self._context = InferenceContext(
            self_agent=self_agent,
            self_role=self_role,
            all_agents=frozenset(all_agents),
            broadcast_keywords=load_broadcast_keywords(lang),
            role_keywords=load_role_keywords(lang, self_role),
        )
        self._threads: list[Thread] = []
        # (day, turn, idx) -> thread_id. 1 talk は1スレッドに紐付き append-only.
        self._talk_to_thread: dict[tuple[int, int, int], int] = {}
        # multi-turn の差分送信用. talk_history のうちこの位置以降が「未読」.
        self._read_cursor = 0
        # 新規スレッド ID 採番. 1 始まり.
        self._next_id = 1
        # 構造ログコールバック (P2 で外部から差し込む). None なら no-op.
        self._on_event: ThreadEventCallback | None = None

    def set_event_callback(self, callback: ThreadEventCallback | None) -> None:
        """Register a callback to receive structural log events.

        構造ログ用のイベントコールバックを登録する. None で解除.

        Args:
            callback (ThreadEventCallback | None): Event sink, or None to disable /
                イベントシンク, None で無効化
        """
        self._on_event = callback

    def on_new_talk(self, talk: Talk) -> ThreadAssignment:
        """Assign a newly received talk to a thread (append-only).

        新着 talk をスレッドに append-only で割り当てる. 既に同一キーの talk が
        登録済みの場合は再割当しない (同じ ThreadAssignment を返す).

        ``talk.over`` が True の talk (= 「Over」発話 = その日の議論離脱宣言) は
        スレッド化対象外として早期 return する. これらは内容を持たず, スレッド化
        するとノイズスレッドが乱立し Step A の判断 (特に over の選択頻度) を
        歪めるため, 構造ログにも残さず完全に無視する.

        Args:
            talk (Talk): The incoming talk / 新着 talk

        Returns:
            ThreadAssignment: Assignment result / 割当結果
        """
        if talk.over:
            return ThreadAssignment(
                thread_id=-1,
                is_new_thread=False,
                is_broadcast=False,
                reason="over=True: スレッド化対象外として無視",
            )
        key = (talk.day, talk.turn, talk.idx)
        if key in self._talk_to_thread:
            existing_id = self._talk_to_thread[key]
            return ThreadAssignment(
                thread_id=existing_id,
                is_new_thread=False,
                is_broadcast=self._thread_by_id(existing_id).is_broadcast,
                reason="既割当のためskip",
            )

        assignment = self._inference.assign(talk, list(self._threads), self._context)
        if assignment.is_new_thread:
            thread = self._create_thread(
                talk,
                is_broadcast=assignment.is_broadcast,
                title_override=assignment.suggested_title,
            )
            assignment = ThreadAssignment(
                thread_id=thread.id,
                is_new_thread=True,
                is_broadcast=thread.is_broadcast,
                reason=assignment.reason,
                suggested_title=assignment.suggested_title,
            )
        else:
            thread = self._thread_by_id(assignment.thread_id)

        self._update_thread(thread, talk)
        self._talk_to_thread[key] = thread.id

        if self._on_event is not None:
            self._on_event.on_assignment(talk, thread, assignment)
        return assignment

    def threads(self) -> list[Thread]:
        """Return a snapshot copy of current threads (id ascending).

        現在のスレッド一覧の snapshot コピーを id 昇順で返す.

        Returns:
            list[Thread]: Thread list (copies of internal state) / スレッド一覧 (内部状態のコピー)
        """
        return [self._copy_thread(t) for t in self._threads]

    def filtered_threads(
        self,
        current_day: int,
        history_days: int | None,
    ) -> list[Thread]:
        """Return threads that fall within ``history_days`` days from ``current_day``.

        ``current_day`` から見て ``history_days`` 日以内のスレッドのみ返す.
        ``history_days`` が None のとき制限なし (全スレッド返却).

        Args:
            current_day (int): Today's day number / 今日の日数
            history_days (int | None): Window in days, or None for unlimited /
                何日分まで残すか. None なら制限なし

        Returns:
            list[Thread]: Filtered thread snapshots / 絞り込み済みスナップショット
        """
        if history_days is None:
            return self.threads()
        cutoff = current_day - history_days + 1
        return [self._copy_thread(t) for t in self._threads if t.last_active_day >= cutoff]

    def thread_of(self, talk: Talk) -> Thread | None:
        """Return the thread the given talk has been assigned to (snapshot).

        指定 talk が紐付くスレッドの snapshot を返す. 未割当なら None.

        Args:
            talk (Talk): Target talk / 対象 talk

        Returns:
            Thread | None: Thread snapshot or None / スレッド snapshot, 無ければ None
        """
        key = (talk.day, talk.turn, talk.idx)
        thread_id = self._talk_to_thread.get(key)
        if thread_id is None:
            return None
        return self._copy_thread(self._thread_by_id(thread_id))

    def new_talks_since_last_read(
        self,
        talk_history: list[Talk],
    ) -> list[tuple[Talk, Thread]]:
        """Return (talk, thread) pairs since the last ``mark_read()``.

        ``mark_read()`` 以降に追加された talk と, 紐付くスレッドのペアを返す.
        multi-turn モードで「差分発話 + 見出し」を LLM に送るための補助.

        Args:
            talk_history (list[Talk]): The full talk history (Agent.talk_history) /
                全 talk 履歴

        Returns:
            list[tuple[Talk, Thread]]: New (talk, thread) pairs in order /
                新規ペア (時系列順)
        """
        result: list[tuple[Talk, Thread]] = []
        for talk in talk_history[self._read_cursor :]:
            key = (talk.day, talk.turn, talk.idx)
            thread_id = self._talk_to_thread.get(key)
            if thread_id is None:
                continue
            result.append((talk, self._copy_thread(self._thread_by_id(thread_id))))
        return result

    def mark_read(self, talk_history_len: int) -> None:
        """Advance the read cursor to ``talk_history_len``.

        既読カーソルを ``talk_history_len`` まで進める. 通常は talk() 完了直後に
        ``len(self.talk_history)`` を渡して呼ぶ.

        Args:
            talk_history_len (int): New cursor position / 新しいカーソル位置
        """
        self._read_cursor = max(self._read_cursor, talk_history_len)

    def _create_thread(
        self,
        first_talk: Talk,
        *,
        is_broadcast: bool,
        title_override: str | None = None,
    ) -> Thread:
        """Create and register a new thread starting at ``first_talk``.

        ``first_talk`` を起点に新規スレッドを作成・登録する. タイトルはここで一度だけ
        固定する. ``title_override`` が指定された場合はそれを採用 (LLM 戦略のスレッド
        タイトル生成用), None なら heuristic で生成する.
        """
        title = (title_override or "").strip() or _generate_title(first_talk.text)
        # タイトルが極端に長い場合は上限で切り詰める.
        if len(title) > _TITLE_MAX_LEN + 5:
            title = title[:_TITLE_MAX_LEN] + "…"
        thread = Thread(
            id=self._next_id,
            title=title,
            is_broadcast=is_broadcast,
            created_day=first_talk.day,
            created_turn=first_talk.turn,
            last_active_day=first_talk.day,
            last_active_turn=first_talk.turn,
        )
        self._threads.append(thread)
        self._next_id += 1
        return thread

    def _update_thread(self, thread: Thread, talk: Talk) -> None:
        """Apply the new talk's effects to ``thread`` in place.

        新着 talk の影響を ``thread`` に反映する (append-only). 参加者・最終
        アクティブ・役職関連 / 自分宛フラグを更新する.
        """
        thread.participants.add(talk.agent)
        thread.talk_keys.append((talk.day, talk.turn, talk.idx))
        thread.last_active_day = talk.day
        thread.last_active_turn = talk.turn
        if not thread.role_relevant and self._is_role_relevant(talk.text):
            thread.role_relevant = True
        if not thread.mentions_self and (
            talk.agent == self._self_agent
            or (self._self_agent and self._self_agent in (talk.text or ""))
            or thread.is_broadcast
        ):
            thread.mentions_self = True

    def _is_role_relevant(self, text: str) -> bool:
        """Return True if ``text`` contains any role-relevant keyword.

        ``text`` に役職関連キーワードが1つでも含まれていれば True.
        """
        if not text:
            return False
        return any(kw and kw in text for kw in self._context.role_keywords)

    def _thread_by_id(self, thread_id: int) -> Thread:
        """Return the internal mutable Thread for the given id.

        指定 id の内部 Thread (mutable) を返す. 不正な id は KeyError.
        """
        for t in self._threads:
            if t.id == thread_id:
                return t
        msg = f"thread_id={thread_id} not found"
        raise KeyError(msg)

    @staticmethod
    def _copy_thread(thread: Thread) -> Thread:
        """Return a defensive copy of ``thread`` so callers cannot mutate state.

        外部に渡す用の Thread 防御的コピーを返す.
        """
        return Thread(
            id=thread.id,
            title=thread.title,
            participants=set(thread.participants),
            talk_keys=list(thread.talk_keys),
            is_broadcast=thread.is_broadcast,
            role_relevant=thread.role_relevant,
            mentions_self=thread.mentions_self,
            created_day=thread.created_day,
            created_turn=thread.created_turn,
            last_active_day=thread.last_active_day,
            last_active_turn=thread.last_active_turn,
        )


class ThreadEventCallback(Protocol):
    """Sink protocol for ThreadManager structural events (impl in P2).

    ``ThreadManager`` の構造イベントシンク用プロトコル. 実装は P2 で追加する.
    P1 ではプロトコル定義のみで no-op.
    """

    def on_assignment(
        self,
        talk: Talk,
        thread: Thread,
        assignment: ThreadAssignment,
    ) -> None:
        """Receive an assignment event.

        スレッド割当イベントを受信する.
        """
        ...


def _generate_title(text: str) -> str:
    """Generate a short fixed title from a thread's first talk.

    スレッドの初出 talk からタイトル文字列を生成する (初出時 1 度だけ呼ばれ以降固定).
    句読点や改行で区切り, 上限文字数で切り詰める.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return "(無題)"
    head = cleaned
    cut_pos = -1
    for delim in _TITLE_DELIMS:
        pos = head.find(delim)
        if 0 <= pos < _TITLE_MAX_LEN:
            cut_pos = pos if cut_pos < 0 else min(cut_pos, pos)
    if cut_pos >= 0:
        head = head[:cut_pos]
    if len(head) > _TITLE_MAX_LEN:
        head = head[:_TITLE_MAX_LEN] + "…"
    return head or "(無題)"
