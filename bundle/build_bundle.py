#!/usr/bin/env python3
"""Bundle STEPIR (stepir_geom/cand, several modules) into ONE file, because a cad-code workspace copies a fixed list
of single tool files (src/workspace.mjs TOOL_FILES) and stepir.py is one of them.

  python3 build_bundle.py --out <path>/stepir.py

The bundle keeps the old interface (`import stepir; stepir.build_ir(path)`, `python stepir.py part.step`) and adds:
  python stepir.py part.step                full v6.2 IR: base records + derived lines (what target.ir.jsonl holds)
  python stepir.py part.step --base         base records only
  python stepir.py query part.step face <id> | evidence <id> | axis | neighbours <id>
"""
import argparse
import hashlib
import subprocess
from pathlib import Path

CAND = Path(__file__).resolve().parents[1] / "cand"
VERSION = "v6.3"
ORDER = ["cadthreads", "sdk_ocp", "geomnorm", "_stepir_core", "construct", "blends", "cadfit", "stepir_ops", "stepir_query"]
FILES = {"cadthreads": "cadthreads.py", "sdk_ocp": "sdk_ocp.py", "geomnorm": "geomnorm.py", "_stepir_core": "stepir.py", "construct": "construct.py",
         "blends": "blends.py", "cadfit": "cadfit.py", "stepir_ops": "stepir_ops.py", "stepir_query": "stepir_query.py"}

HEAD = '''#!/usr/bin/env python3
"""STEPIR {version} - STEP -> compact B-rep description for writing SimpleCADAPI code (single-file bundle).

  python stepir.py part.step                full IR: one JSON object per line - header, face records, derived lines
  python stepir.py part.step --base         face records only (no derived lines)
  python stepir.py query part.step face <id> | evidence <id> | axis | neighbours <id>   on-demand detail

Bundled from stepir_geom/cand @ {commit} ({n} modules). Format reference: docs/STEPIR_VERSIONS.md of step-tools (references/inspect/stepir.md of the simplecadapi skill).
"""
import os as _os
import sys as _sys
import types as _types

_os.environ.setdefault("STEPIR_NDIG", "4")
_SOURCES = {sources}


def _install():
    for _name in {order!r}:
        if _name in _sys.modules:
            continue
        _m = _types.ModuleType(_name)
        _m.__file__ = __file__
        _sys.modules[_name] = _m
        exec(compile(_SOURCES[_name], "<stepir-bundle:" + _name + ">", "exec"), _m.__dict__)


_install()
from _stepir_core import *            # noqa: E402,F401,F403  (old interface: build_ir, canon_axes, add_cut_flags, ...)
from _stepir_core import build_ir, canon_axes, add_cut_flags, canon_frame   # noqa: E402,F401


def full_ir(path):
    import stepir_ops
    lines = build_ir(str(path))
    facts = stepir_ops.analyse(str(path), with_fit=True, lines=lines)
    return stepir_ops.augment(lines, facts)


def main(argv=None):
    argv = list(_sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "query":
        import stepir_query
        _sys.argv = ["stepir_query.py"] + argv[1:]
        return stepir_query.main()
    import argparse
    ap = argparse.ArgumentParser(description="STEPIR {version}")
    ap.add_argument("step")
    ap.add_argument("--base", action="store_true", help="face records only, no derived lines")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    lines = build_ir(a.step) if a.base else full_ir(a.step)
    text = "\\n".join(lines) + "\\n"
    if a.out:
        open(a.out, "w").write(text)
    else:
        _sys.stdout.write(text)


if __name__ == "__main__":
    main()
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--version", default=VERSION)
    a = ap.parse_args()
    srcs = {}
    for name in ORDER:
        s = (CAND / FILES[name]).read_text()
        s = s.replace("import stepir  # noqa: E402", "import _stepir_core as stepir  # noqa: E402")
        s = s.replace("    import stepir\n", "    import _stepir_core as stepir\n")
        s = s.replace("import stepir\n", "import _stepir_core as stepir\n")
        srcs[name] = s
    commit = subprocess.run(["git", "-C", str(CAND.parent), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    body = "{\n" + "".join(f"    {k!r}: {v!r},\n" for k, v in srcs.items()) + "}"
    out = HEAD.format(commit=commit, n=len(ORDER), sources=body, order=ORDER, version=a.version)
    Path(a.out).write_text(out)
    print(a.out, len(out), "bytes, sha256", hashlib.sha256(out.encode()).hexdigest()[:12], "from", commit)


if __name__ == "__main__":
    main()
