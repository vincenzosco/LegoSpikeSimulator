"""Fixture condivise: eseguire un programma SPIKE scritto al volo."""

from __future__ import annotations

import textwrap

import pytest

from spikesim.config import Config, default_config
from spikesim.runner import run_in_process


@pytest.fixture
def run_source(tmp_path):
    """Scrive ``source`` in un file .py e lo esegue nel simulatore.

    Restituisce un callable ``(source, config=None, name="programma.py")`` che
    ritorna il `RunResult` del runner.
    """
    counter = {"n": 0}

    def _run(source: str, config: Config | None = None, name: str | None = None):
        counter["n"] += 1
        path = tmp_path / (name or f"programma_{counter['n']}.py")
        path.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        return run_in_process(str(path), config or default_config())

    return _run
