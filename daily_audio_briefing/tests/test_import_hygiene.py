"""Import hygiene guard — turns the CI dependency contract into a check.

The Tests workflow installs only pytest + requirements.txt (the light web set) + mcp.
Every module the test suite imports, and every local module those pull in at load
time, must therefore only import the standard library, other local modules, or a
package from that light set at top level. Heavy deps (TTS, GUI, YouTube, Google)
stay lazy inside functions. This test fails the moment someone adds a top-level
import that the CI job would not have installed — instead of CI failing at
collection with a ModuleNotFoundError four pushes later.
"""
import ast
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent
STDLIB = set(sys.stdlib_module_names)
LOCAL = {p.stem for p in PKG.glob("*.py")}

# import-name -> distribution, for what the CI job installs (requirements.txt + mcp)
IMPORT_TO_DIST = {"bs4": "beautifulsoup4", "lxml": "lxml", "requests": "requests",
                  "flask": "flask", "gunicorn": "gunicorn", "mcp": "mcp"}


def _ci_installed():
    req = (PKG / "requirements.txt").read_text().splitlines()
    dists = {re.split(r"[<>=\[; ]", l.strip())[0].lower() for l in req if l.strip() and not l.startswith("#")}
    dists.add("mcp")
    return {imp for imp, dist in IMPORT_TO_DIST.items() if dist in dists}


def _top_level_imports(path):
    tree = ast.parse(path.read_text(errors="ignore"))
    names = set()
    for node in tree.body:  # top level only — imports inside functions are lazy by design
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def _modules_reached_by_tests():
    """Local modules imported by any test file, plus everything they import locally (transitive)."""
    seen, todo = set(), []
    for t in HERE.glob("test_*.py"):
        if t.name == pathlib.Path(__file__).name:
            continue
        todo += [n for n in _top_level_imports(t) if n in LOCAL]
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        todo += [n for n in _top_level_imports(PKG / f"{m}.py") if n in LOCAL]
    return sorted(seen)


def test_tested_modules_only_import_what_ci_installs():
    allowed = STDLIB | LOCAL | _ci_installed()
    offenders = {}
    for m in _modules_reached_by_tests():
        bad = sorted(n for n in _top_level_imports(PKG / f"{m}.py") if n not in allowed)
        if bad:
            offenders[m] = bad
    assert not offenders, (
        "Top-level imports the CI job does not install (make them lazy, or add the "
        f"package to requirements.txt and the Tests workflow): {offenders}"
    )
