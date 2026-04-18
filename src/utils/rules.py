"""Load and resolve game rules from data/rules.<lang>.yml.

data/rules.<lang>.yml から日別フェーズ進行ルールと人数別役職編成を読み込み,
day と agent_count で rules.jinja 用に解決する.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DATA_ROOT = Path(__file__).parent.joinpath("./../../data").resolve()

# lang 単位でキャッシュ. 値は YAML 全体の dict (daily / compositions / role_labels).
_RULES_CACHE: dict[str, dict[str, Any]] = {}


def load_rules(lang: str) -> dict[str, Any]:
    """Return the parsed rules data for the given language.

    指定言語のルール定義を返す. 一度読んだ結果はプロセス内でキャッシュする.
    ファイルが無ければ空辞書を返す.
    """
    if lang in _RULES_CACHE:
        return _RULES_CACHE[lang]

    path = _DATA_ROOT / f"rules.{lang}.yml"
    if not path.exists():
        _RULES_CACHE[lang] = {}
        return _RULES_CACHE[lang]

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    _RULES_CACHE[lang] = raw
    return _RULES_CACHE[lang]


def resolve_rules(
    lang: str,
    day: int | None,
    agent_count: int | None,
) -> dict[str, Any] | None:
    """Resolve today's rule and the role composition for the current game.

    day と agent_count から本日のルールと役職編成を解決する.
    - day が 0/1/2 に該当すれば day_N, それ以外は default にフォールバック
    - agent_count が 5/9/13 に該当すればその composition, それ以外は None
    - いずれか片方だけが取れた場合は取れた方のみ埋めて返す
    - 両方取れない / ファイル自体が空 の場合は None を返す (呼び出し側で空出力)

    Returns:
        dict | None:
            {
              "day": int,                             # 現在日 (参照用. day が None なら含まれない)
              "morning": str,                         # 本日朝のルール
              "night": str,                           # 本日夜のフェーズ
              "agent_count": int,                     # 人数 (agent_count が解決できない場合は含まれない)
              "composition": list[{"role": str, "label": str, "count": int}],
            }
    """
    data = load_rules(lang)
    if not data:
        return None

    result: dict[str, Any] = {}

    # 本日のルール
    daily = data.get("daily") or {}
    if day is not None:
        day_key = f"day_{day}" if f"day_{day}" in daily else "default"
        today = daily.get(day_key)
        if isinstance(today, dict):
            result["day"] = day
            result["morning"] = str(today.get("morning", ""))
            result["night"] = str(today.get("night", ""))

    # 役職編成 (role_labels で enum → 表示名に変換)
    comps = data.get("compositions") or {}
    labels = data.get("role_labels") or {}
    if agent_count is not None and agent_count in comps:
        comp_raw = comps[agent_count] or {}
        composition = [
            {
                "role": str(role),
                "label": str(labels.get(role, role)),
                "count": int(count),
            }
            for role, count in comp_raw.items()
        ]
        result["agent_count"] = int(agent_count)
        result["composition"] = composition

    return result or None


def _reset_cache() -> None:
    """Clear the in-process cache (for tests).

    テスト用に全キャッシュをクリアする.
    """
    _RULES_CACHE.clear()


__all__: list[str] = ["load_rules", "resolve_rules"]
