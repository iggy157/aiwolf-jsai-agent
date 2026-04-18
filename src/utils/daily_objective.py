"""Load and resolve per-role per-day objectives from data/daily_objectives.<lang>.yml.

data/daily_objectives.<lang>.yml から役職別・日別の目標を読み込み, 役職と日数で解決する.

各役職は day_0 / day_1 / day_2 / default の4区分を持つ. 与えられた day が
day_0-2 に該当すればその値, それ以外 (3日目以降) は default を返す.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_DATA_ROOT = Path(__file__).parent.joinpath("./../../data").resolve()

# lang 単位でキャッシュ. 値は role -> (day_key -> 目標文字列) のネスト辞書.
_OBJECTIVES_CACHE: dict[str, dict[str, dict[str, str]]] = {}


def load_objectives(lang: str) -> dict[str, dict[str, str]]:
    """Return the parsed daily-objectives mapping for the given language.

    指定言語の役職別目標マップを返す. 一度読んだ結果はプロセス内でキャッシュする.
    ファイルが無ければ空辞書を返す (呼び出し側は None フォールバックで扱う).

    Args:
        lang (str): 言語コード (jp / en).

    Returns:
        dict[str, dict[str, str]]:
            role (例: "VILLAGER") -> { "day_0": "...", "day_1": "...", ..., "default": "..." }.
    """
    if lang in _OBJECTIVES_CACHE:
        return _OBJECTIVES_CACHE[lang]

    path = _DATA_ROOT / f"daily_objectives.{lang}.yml"
    if not path.exists():
        _OBJECTIVES_CACHE[lang] = {}
        return _OBJECTIVES_CACHE[lang]

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    result: dict[str, dict[str, str]] = {}
    for role, days in raw.items():
        if not isinstance(days, dict):
            continue
        result[str(role)] = {str(k): str(v) for k, v in days.items()}

    _OBJECTIVES_CACHE[lang] = result
    return result


def resolve_objective(lang: str, role: str | None, day: int | None) -> str | None:
    """Look up the objective for a given role and day.

    役職と日数から該当する目標文字列を返す. day が 0-2 のうち対応するキーが
    見つからないか, day が 3 以上の場合は "default" を返す. 役職自体が未登録
    あるいは引数欠落のときは None を返す.

    Args:
        lang (str): 言語コード (jp / en).
        role (str | None): 役職名 (サーバ Role enum と一致する英語名).
        day (int | None): 現在の日数.

    Returns:
        str | None: 該当する目標文字列. 解決できなければ None.
    """
    if not role or day is None:
        return None
    data = load_objectives(lang)
    role_data = data.get(role)
    if not role_data:
        return None
    day_key = f"day_{day}"
    return role_data.get(day_key) or role_data.get("default")


def _reset_cache() -> None:
    """Clear the in-process cache (for tests).

    テスト用に全キャッシュをクリアする.
    """
    _OBJECTIVES_CACHE.clear()


__all__: list[str] = ["load_objectives", "resolve_objective"]
