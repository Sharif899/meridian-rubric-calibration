"""No placeholder / stub text anywhere in the repo."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN = [
    r"\bTODO\b", r"\bFIXME\b", r"\bXXX\b", r"\blorem\b", r"\bplaceholder\b",
    r"sample result", r"not implemented", r"pass  # stub",
]

# Files that legitimately mention the word (HTML input placeholders).
ALLOWED_FILES = {
    ROOT / "src" / "meridian_eval" / "web" / "index.html",
}


def _iter_files():
    skip_dirs = {".venv", "__pycache__", ".pytest_cache", ".git"}
    skip_files = {
        ROOT / "tests" / "test_no_placeholders.py",
        # Generated, gitignored run outputs; the committed sample export
        # (reports/sample-analysis.json) is scanned.
        ROOT / "reports" / "analysis.json",
        ROOT / "reports" / "analysis.md",
    }
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path in skip_files:
            continue
        if any(part in skip_dirs or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix in (".db", ".pyc"):
            continue
        if path.name in ("LICENSE",):
            continue
        yield path


def test_no_forbidden_words():
    hits = []
    for path in _iter_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # HTML placeholder="..." attributes are legitimate.
                line = text[max(0, match.start() - 60):match.end() + 60]
                if 'placeholder="' in line or "placeholder='" in line:
                    continue
                hits.append(f"{path.relative_to(ROOT)}: {pattern}: {line.strip()[:120]}")
    assert not hits, "\n".join(hits)


def test_no_empty_python_modules():
    for path in (ROOT / "src").rglob("*.py"):
        assert path.read_text(encoding="utf-8").strip(), f"{path} is empty"


def test_no_db_files_committed():
    # The working store (store.db in the repo root) is a runtime artifact
    # created by running the pipeline; it is gitignored, never committed.
    # Everything else must be absent.
    dbs = [p for p in ROOT.rglob("*.db") if p != ROOT / "store.db"]
    assert not dbs, dbs
    assert not [p for p in ROOT.rglob("*.sqlite3")]
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.db" in gitignore
