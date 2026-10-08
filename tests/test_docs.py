"""I README e i loro screenshot: i file citati devono esistere davvero."""

from __future__ import annotations

import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Riferimenti a file locali dentro il markdown: `![...](percorso)` e `[...](percorso)`.
_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def _read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return handle.read()


def _local_links(text: str) -> list[str]:
    links = []
    for target in _LINK.findall(text):
        target = target.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        links.append(target)
    return links


#: Le sezioni che ogni guida deve avere, nella lingua in cui è scritta.
REQUIRED_SECTIONS = {
    "README.md": ("## Installation", "## Quick start", "## Step by step", "## Licence"),
    "README.it.md": ("## Installazione", "## Avvio rapido", "## Passo per passo", "## Licenza"),
}


@pytest.mark.parametrize("name", ["README.md", "README.it.md"])
def test_the_readme_exists_and_is_substantial(name):
    text = _read(name)
    assert len(text) > 3000, f"{name} è troppo scarno per essere una guida"
    for section in REQUIRED_SECTIONS[name]:
        assert section in text, f"{name}: manca la sezione «{section}»"


@pytest.mark.parametrize("name", ["README.md", "README.it.md"])
def test_every_local_link_in_the_readme_exists(name):
    missing = [
        link for link in _local_links(_read(name)) if not os.path.exists(os.path.join(ROOT, link))
    ]
    assert not missing, f"{name} rimanda a file che non esistono: {missing}"


@pytest.mark.parametrize("name", ["README.md", "README.it.md"])
def test_the_readme_shows_the_screenshots(name):
    shots = [link for link in _local_links(_read(name)) if link.startswith("docs/screenshots/")]
    assert len(shots) >= 4, f"{name} deve mostrare alcuni screenshot, ne ha {len(shots)}"
    for shot in shots:
        path = os.path.join(ROOT, shot)
        with open(path, "rb") as handle:
            assert handle.read(8) == b"\x89PNG\r\n\x1a\n", f"{shot} non è un PNG"
        assert os.path.getsize(path) > 5000, f"{shot} sembra vuoto"


def test_the_two_readmes_point_at_each_other():
    assert "README.it.md" in _read("README.md")
    assert "README.md" in _read("README.it.md")


def test_the_readme_documents_the_templates_and_the_light():
    english = _read("README.md")
    for needle in ("Seguilinea", "Luce", "green", "90°", "LICENSE"):
        assert needle in english, f"il README inglese non parla di «{needle}»"


def test_the_readme_documents_how_to_run_the_tests():
    for name in ("README.md", "README.it.md"):
        assert "python3 -m pytest -q" in _read(name)
