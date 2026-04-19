"""Data resolvers that load ``data/prompts/*.yml`` for Jinja rendering.

``data/prompts/*.yml`` を読み込んで Jinja 側から参照するためのヘルパ群.

- ``profile``: data/prompts/profiles.<lang>.yml からキャラクタープロフィールを解決.
- ``daily_objective``: data/prompts/daily_objectives.<lang>.yml から役職別・日別目標を解決.
- ``rules``: data/prompts/rules.<lang>.yml から日別フェーズと人数別役職編成を解決.
"""

from utils.resolvers import daily_objective, profile, rules

__all__ = ["daily_objective", "profile", "rules"]
