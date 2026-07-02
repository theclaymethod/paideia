"""Shared gate conftest template (paideia gated-tutor machinery).

check_gates.py copies this file to <course>/exercises/<id>/conftest.py for every
gated chunk (it regenerates a missing copy, and refuses to run if an existing
copy has drifted from this template). pytest imports the conftest before
collecting test_gate.py; this code loads `impl` from the directory named by
$TUTOR_IMPL_DIR and registers it in sys.modules, so a bare `import impl` in
test_gate.py always resolves there — regardless of how pytest orders sys.path:

  * TUTOR_IMPL_DIR=<course>/exercises/<id>  -> learner implementation (holes)
  * TUTOR_IMPL_DIR=<course>/solutions/<id>  -> reference implementation

The directory is also placed at sys.path[0] so impl-adjacent helper modules
resolve consistently. Only check_gates.py ever points TUTOR_IMPL_DIR at a
solutions/ path.
"""

import importlib.util
import os
import sys

_impl_dir = os.environ.get("TUTOR_IMPL_DIR")
if _impl_dir:
    _impl_dir = os.path.abspath(_impl_dir)
    while _impl_dir in sys.path:
        sys.path.remove(_impl_dir)
    sys.path.insert(0, _impl_dir)

    _impl_path = os.path.join(_impl_dir, "impl.py")
    if os.path.isfile(_impl_path):
        _spec = importlib.util.spec_from_file_location("impl", _impl_path)
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["impl"] = _mod
        _spec.loader.exec_module(_mod)
