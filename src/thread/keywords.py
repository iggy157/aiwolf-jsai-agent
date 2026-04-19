"""Loader for broadcast / role keyword dictionaries used by HeuristicThreadInference.

``HeuristicThreadInference`` が使う broadcast / role キーワード辞書のローダー.

辞書ファイルは ``data/broadcast_keywords.<lang>.yml`` と ``data/role_keywords.<lang>.yml``
に置く. ファイルが存在しないか壊れているときは空タプルを返し, 推定は keyword 不発の
扱いになる (= broadcast / 役職関連と判定されない).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from aiwolf_nlp_common.packet import Role

_DATA_ROOT = Path(__file__).parent.joinpath("./../../data").resolve()
_BROADCAST_CACHE: dict[str, tuple[str, ...]] = {}
_ROLE_CACHE: dict[str, dict[str, tuple[str, ...]]] = {}


def load_broadcast_keywords(lang: str) -> tuple[str, ...]:
    """Return broadcast keywords for the given language.

    指定言語の broadcast キーワード一覧をタプルで返す. ファイルが無い場合は空タプル.

    Args:
        lang (str): Language code (jp / en) / 言語コード

    Returns:
        tuple[str, ...]: Broadcast keywords / broadcast キーワード一覧
    """
    if lang in _BROADCAST_CACHE:
        return _BROADCAST_CACHE[lang]
    path = _DATA_ROOT / f"broadcast_keywords.{lang}.yml"
    keywords: tuple[str, ...] = ()
    if path.exists():
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        items = raw.get("keywords") or []
        keywords = tuple(str(k) for k in items if str(k).strip())
    _BROADCAST_CACHE[lang] = keywords
    return keywords


def load_role_keywords(lang: str, role: Role) -> tuple[str, ...]:
    """Return keywords relevant to the given role for the given language.

    指定言語・役職に対応するキーワード一覧を返す. 役職エントリが無い場合は空タプル.

    Args:
        lang (str): Language code (jp / en) / 言語コード
        role (Role): Role enum / 役職

    Returns:
        tuple[str, ...]: Role-relevant keywords / 役職関連キーワード一覧
    """
    by_role = _load_role_keywords_all(lang)
    return by_role.get(role.value, ())


def _load_role_keywords_all(lang: str) -> dict[str, tuple[str, ...]]:
    """Load and cache the full role->keywords map for the given language.

    指定言語の役職→キーワードマップ全体をロードしてキャッシュする.
    """
    if lang in _ROLE_CACHE:
        return _ROLE_CACHE[lang]
    path = _DATA_ROOT / f"role_keywords.{lang}.yml"
    by_role: dict[str, tuple[str, ...]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        for role_name, items in raw.items():
            if not isinstance(items, list):
                continue
            by_role[str(role_name)] = tuple(str(k) for k in items if str(k).strip())
    _ROLE_CACHE[lang] = by_role
    return by_role
