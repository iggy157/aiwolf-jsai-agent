"""JSONL structural logger for the thread feature (人手検証用).

スレッド機能の構造ログ (JSONL) ライタ. 後で人手による割当精度の検証ができるよう,
スレッド割当 / タイトル付与 / Step A 判断 / 日次スナップショット の各イベントを
時系列で出力する.

出力先: ``<log.output_dir>/<game_folder>/thread_structure/<agent_name>.jsonl``
``log.file_output: true`` かつ ``thread.enabled: true`` のときに有効化する.
追加 config 不要 (両者の AND).

このモジュールは ``ThreadManager`` の ``ThreadEventCallback`` を実装する
``StructureLogger`` クラスを提供する. Step A 判断の記録は P4 で
``log_decision()`` を経由して書き込む.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from aiwolf_nlp_common.packet import Talk

    from thread.models import Thread, ThreadAssignment

logger = logging.getLogger(__name__)

THREAD_STRUCTURE_SUBDIR = "thread_structure"


class StructureLogger:
    """Append thread structure events as JSON lines.

    スレッド構造イベントを JSONL で1行ずつ追記するロガー.

    1 game / 1 agent につき 1 ファイル. 書き込み失敗は握りつぶす
    (ログ書き込みでゲーム処理を止めない).
    """

    def __init__(self, log_path: Path) -> None:
        """Initialize the logger with a target JSONL path.

        ターゲット JSONL パスを指定して初期化する. 親ディレクトリが無ければ作成する.

        Args:
            log_path (Path): Output JSONL path / 出力先 JSONL パス
        """
        self._path = log_path
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch(exist_ok=True)
        except OSError:
            logger.exception("Failed to prepare structure log path: %s", self._path)

    def on_assignment(
        self,
        talk: Talk,
        thread: Thread,
        assignment: ThreadAssignment,
    ) -> None:
        """Record one assignment event (called by ThreadManager).

        スレッド割当イベントを 1 件記録する (``ThreadManager`` から呼ばれる).
        新規スレッド作成時は ``title_assigned`` イベントも続けて出力する.
        """
        event: dict[str, Any] = {
            "type": "assignment",
            "ts": _now(),
            "day": talk.day,
            "turn": talk.turn,
            "talk": _talk_dict(talk),
            "thread_id": thread.id,
            "is_new_thread": assignment.is_new_thread,
            "is_broadcast": assignment.is_broadcast,
            "reason": assignment.reason,
        }
        self._write(event)
        if assignment.is_new_thread:
            self._write(
                {
                    "type": "title_assigned",
                    "ts": _now(),
                    "thread_id": thread.id,
                    "title": thread.title,
                    "is_broadcast": thread.is_broadcast,
                    "created_day": thread.created_day,
                    "created_turn": thread.created_turn,
                },
            )

    def log_decision(
        self,
        day: int,
        turn: int,
        decision: dict[str, Any],
        threads_snapshot: list[Thread],
    ) -> None:
        """Record a Step A (ThreadDecision) event (called by Agent in P4).

        Step A (判断) イベントを記録する (P4 の Agent 側から呼ぶ).
        その時点の全スレッド snapshot も併記し, 後で「どの状態で何を選んだか」が追える形にする.

        Args:
            day (int): Current day / 現在の日数
            turn (int): Current turn / 現在の turn
            decision (dict[str, Any]): Step A output (target_thread / action / reason) /
                Step A 出力
            threads_snapshot (list[Thread]): Threads at decision time / 判断時点のスレッド一覧
        """
        self._write(
            {
                "type": "decision",
                "ts": _now(),
                "day": day,
                "turn": turn,
                "decision": decision,
                "threads_snapshot": [_thread_dict(t) for t in threads_snapshot],
            },
        )

    def log_eod_snapshot(self, day: int, threads_snapshot: list[Thread]) -> None:
        """Record an end-of-day snapshot of all threads.

        当該日の全スレッド snapshot を記録する (daily_finish タイミングで呼ぶ想定).

        Args:
            day (int): Day number / 日数
            threads_snapshot (list[Thread]): All threads / 全スレッド
        """
        self._write(
            {
                "type": "snapshot_eod",
                "ts": _now(),
                "day": day,
                "threads": [_thread_dict(t) for t in threads_snapshot],
            },
        )

    def _write(self, event: dict[str, Any]) -> None:
        """Append one JSON line. Swallow exceptions to keep the game running.

        1 行 JSON を追記する. 例外は握りつぶしてゲーム継続を優先する.
        """
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            logger.exception("Failed to write thread structure event")


def _now() -> str:
    """Return current UTC ISO timestamp (seconds resolution).

    現在時刻 (UTC, 秒精度) の ISO 文字列を返す.
    """
    return datetime.now(UTC).isoformat(timespec="seconds")


def _talk_dict(talk: Talk) -> dict[str, Any]:
    """Convert a Talk to a JSON-friendly dict.

    ``Talk`` を JSON 互換の dict に変換する.
    """
    return {
        "idx": talk.idx,
        "day": talk.day,
        "turn": talk.turn,
        "agent": talk.agent,
        "text": talk.text,
        "skip": talk.skip,
        "over": talk.over,
    }


def _thread_dict(thread: Thread) -> dict[str, Any]:
    """Convert a Thread to a JSON-friendly dict.

    ``Thread`` を JSON 互換の dict に変換する.
    """
    return {
        "id": thread.id,
        "title": thread.title,
        "participants": sorted(thread.participants),
        "is_broadcast": thread.is_broadcast,
        "role_relevant": thread.role_relevant,
        "mentions_self": thread.mentions_self,
        "created_day": thread.created_day,
        "created_turn": thread.created_turn,
        "last_active_day": thread.last_active_day,
        "last_active_turn": thread.last_active_turn,
        "talk_count": len(thread.talk_keys),
    }


def render_markdown_summary(jsonl_path: Path, md_path: Path) -> None:
    """Read the JSONL log and render a human-readable Markdown summary.

    JSONL 生ログを読み, 人間可読な Markdown サマリを生成する. ゲーム終了時に
    ``Agent.finish()`` から呼び出される想定. JSONL が無いか空なら何もしない.
    書き込み失敗は握りつぶす (ログ生成でゲーム処理を止めない).

    レイアウト:
        1. ヘッダ (生成時刻, 元 JSONL パス)
        2. 概要 (スレッド数 / 発話数 / Step A 判断数 / action 分布)
        3. スレッド別詳細 (参加者・フラグ・発話一覧)
        4. Step A 判断の時系列 (action / target / reason)
        5. 日次スナップショット (day ごとのスレッド一覧)

    Args:
        jsonl_path (Path): Source JSONL path / 元 JSONL パス
        md_path (Path): Destination MD path / 出力 MD パス
    """
    if not jsonl_path.exists():
        return
    try:
        events = _load_jsonl(jsonl_path)
    except OSError:
        logger.exception("Failed to read %s", jsonl_path)
        return
    if not events:
        return
    threads = _aggregate_threads(events)
    decisions = [e for e in events if e.get("type") == "decision"]
    snapshots = [e for e in events if e.get("type") == "snapshot_eod"]

    lines: list[str] = [
        f"# Thread Structure Summary — `{md_path.stem}`",
        "",
        f"- Generated: {_now()}",
        f"- Source: `{jsonl_path.name}`",
        f"- Threads: **{len(threads)}**  / "
        f"Assignments: **{sum(len(t['talks']) for t in threads.values())}**  / "
        f"Step A decisions: **{len(decisions)}**",
        "",
    ]
    lines += _render_decision_summary(decisions)
    lines += _render_threads_section(threads)
    lines += _render_decisions_timeline(decisions)
    lines += _render_eod_snapshots(snapshots)

    try:
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        logger.exception("Failed to write %s", md_path)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL file, skipping unparseable lines.

    JSONL を読み込む. パース不能な行は警告して skip.
    """
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skip unparseable line %d in %s", lineno, path)
                continue
            if isinstance(obj, dict):
                events.append(obj)
    return events


def _aggregate_threads(events: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Build per-thread record with title, participants, and talk list.

    thread_id ごとにタイトル / 参加者 / 発話一覧を集計して返す.
    ``assignment`` から talk 情報, ``title_assigned`` からタイトル, ``snapshot_eod`` から
    最終フラグ (role_relevant / mentions_self など) を吸収する.
    """
    threads: dict[int, dict[str, Any]] = {}
    for ev in events:
        t = ev.get("type")
        if t == "assignment":
            tid = int(ev.get("thread_id", -1))
            if tid < 0:
                continue
            rec = threads.setdefault(
                tid,
                {
                    "id": tid,
                    "title": "",
                    "is_broadcast": bool(ev.get("is_broadcast", False)),
                    "role_relevant": False,
                    "mentions_self": False,
                    "participants": set(),
                    "talks": [],
                },
            )
            talk = ev.get("talk") or {}
            rec["participants"].add(str(talk.get("agent", "")))
            rec["talks"].append(
                {
                    "day": talk.get("day"),
                    "turn": talk.get("turn"),
                    "idx": talk.get("idx"),
                    "agent": talk.get("agent"),
                    "text": talk.get("text", ""),
                    "reason": ev.get("reason", ""),
                    "is_new_thread": bool(ev.get("is_new_thread", False)),
                },
            )
        elif t == "title_assigned":
            tid = int(ev.get("thread_id", -1))
            if tid < 0:
                continue
            rec = threads.setdefault(tid, {"id": tid, "title": "", "talks": [], "participants": set()})
            rec["title"] = str(ev.get("title", ""))
            rec["is_broadcast"] = bool(ev.get("is_broadcast", False))
        elif t == "snapshot_eod":
            for snap in ev.get("threads", []) or []:
                tid = int(snap.get("id", -1))
                if tid in threads:
                    threads[tid]["role_relevant"] = bool(snap.get("role_relevant", False))
                    threads[tid]["mentions_self"] = bool(snap.get("mentions_self", False))
                    threads[tid]["title"] = threads[tid].get("title") or str(snap.get("title", ""))
    return threads


def _render_decision_summary(decisions: list[dict[str, Any]]) -> list[str]:
    """Render the "decision action breakdown" section.

    Step A 判断の action 分布 (reply/skip/over/new_thread) を集計表示する.
    """
    counts: dict[str, int] = {"reply": 0, "skip": 0, "over": 0, "new_thread": 0}
    for ev in decisions:
        action = str((ev.get("decision") or {}).get("action", ""))
        if action in counts:
            counts[action] += 1
    if not decisions:
        return []
    total = max(len(decisions), 1)
    lines: list[str] = ["## Step A Action Breakdown", ""]
    for action in ("reply", "new_thread", "skip", "over"):
        n = counts[action]
        pct = 100 * n / total
        lines.append(f"- `{action}`: **{n}** ({pct:.1f}%)")
    lines.append("")
    return lines


def _render_threads_section(threads: dict[int, dict[str, Any]]) -> list[str]:
    """Render the per-thread detail section.

    スレッド別の詳細セクションを描画する. 各スレッドの参加者・フラグ・発話一覧
    (表形式) を出力する.
    """
    if not threads:
        return ["## Threads", "", "_(まだスレッドが作成されていません)_", ""]
    lines: list[str] = ["## Threads", ""]
    for tid in sorted(threads.keys()):
        rec = threads[tid]
        tag = f"T{tid}{'*' if rec.get('is_broadcast') else ''}"
        title = str(rec.get("title") or "(無題)")
        participants = sorted(rec.get("participants") or set())
        flag_role = "yes" if rec.get("role_relevant") else "-"
        flag_self = "yes" if rec.get("mentions_self") else "-"
        lines.append(f"### [{tag}] 「{title}」")
        lines.append("")
        lines.append(f"- 参加: {', '.join(participants) if participants else '(なし)'}")
        lines.append(f"- 役職関連: {flag_role}")
        lines.append(f"- 自分宛: {flag_self}")
        lines.append(f"- 発話数: {len(rec.get('talks') or [])}")
        lines.append("")
        talks = rec.get("talks") or []
        if talks:
            lines.append("| day/turn/idx | agent | text | assigned by |")
            lines.append("|---|---|---|---|")
            for t in talks:
                text = str(t.get("text") or "").replace("|", "\\|").replace("\n", " ")
                if len(text) > 80:  # noqa: PLR2004
                    text = text[:80] + "…"
                reason = str(t.get("reason") or "").replace("|", "\\|").replace("\n", " ")
                if len(reason) > 40:  # noqa: PLR2004
                    reason = reason[:40] + "…"
                dti = f"{t.get('day')}/{t.get('turn')}/{t.get('idx')}"
                lines.append(f"| {dti} | {t.get('agent')} | {text} | {reason} |")
            lines.append("")
    return lines


def _render_decisions_timeline(decisions: list[dict[str, Any]]) -> list[str]:
    """Render the Step A decisions timeline table.

    Step A 判断の時系列を表で描画する.
    """
    if not decisions:
        return []
    lines: list[str] = [
        "## Step A Decisions (chronological)",
        "",
        "| ts | day/turn | action | target_thread | reason |",
        "|---|---|---|---|---|",
    ]
    for ev in decisions:
        d = ev.get("decision") or {}
        action = str(d.get("action", ""))
        target = d.get("target_thread")
        target_str = f"T{target}" if target is not None else "-"
        reason = str(d.get("reason") or "").replace("|", "\\|").replace("\n", " ")
        if len(reason) > 60:  # noqa: PLR2004
            reason = reason[:60] + "…"
        ts = str(ev.get("ts", ""))
        dt = f"{ev.get('day')}/{ev.get('turn')}"
        lines.append(f"| {ts} | {dt} | `{action}` | {target_str} | {reason} |")
    lines.append("")
    return lines


def _render_eod_snapshots(snapshots: list[dict[str, Any]]) -> list[str]:
    """Render per-day end-of-day snapshot section.

    日次 EOD スナップショットを day ごとに表で描画する.
    """
    if not snapshots:
        return []
    lines: list[str] = ["## End-of-Day Snapshots", ""]
    for ev in snapshots:
        day = ev.get("day")
        threads = ev.get("threads") or []
        lines.append(f"### day {day} ({len(threads)} threads)")
        lines.append("")
        lines.append("| thread | title | participants | role | self | talks |")
        lines.append("|---|---|---|---|---|---|")
        for t in threads:
            tag = f"T{t.get('id')}{'*' if t.get('is_broadcast') else ''}"
            title = str(t.get("title") or "").replace("|", "\\|")
            participants = ", ".join(t.get("participants") or [])
            role_flag = "yes" if t.get("role_relevant") else "-"
            self_flag = "yes" if t.get("mentions_self") else "-"
            count = t.get("talk_count") or 0
            lines.append(f"| {tag} | {title} | {participants} | {role_flag} | {self_flag} | {count} |")
        lines.append("")
    return lines
