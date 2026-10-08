"""Root conftest: makes the repository root importable as ``spikesim``.

pytest's default (prepend) import mode puts the directory of the closest
conftest.py on sys.path, so this file is what lets ``import spikesim`` work
whether the suite is started with ``pytest`` or ``python -m pytest``.
"""
