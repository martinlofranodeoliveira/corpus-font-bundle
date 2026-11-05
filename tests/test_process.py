import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from corpus_font_bundle import _owner
from corpus_font_bundle.shaping import native
from support import Workspace


class ProcessTests(Workspace):
    def test_inherited_ignored_sigchld_in_real_separate_caller(self):
        script = """
import signal
signal.signal(signal.SIGCHLD, signal.SIG_IGN)
from corpus_font_bundle.shaping import native
assert native({'action':'version'}).startswith(b'hb-shape (HarfBuzz) 6.0.0')
assert signal.getsignal(signal.SIGCHLD) == signal.SIG_IGN
"""
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_timeout_and_output_limit_with_real_owned_children(self):
        # Test-only substitution at the owner's command boundary; public API has
        # no executable override. These are real subprocesses, not fake PIDs.
        for script, expected in [("import time; time.sleep(30)", "NATIVE_TIMEOUT"),
                                 ("import os; os.write(1,b'x'*300000)", "NATIVE_OUTPUT_LIMIT"),
                                 ("import os; os.write(2,b'x'*300000)", "NATIVE_OUTPUT_LIMIT")]:
            caller = self.root / "probe.py"
            caller.write_text("""
import importlib.util, os, signal
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('owner', %r)
o=importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
signal.signal(signal.SIGCHLD, signal.SIG_DFL)
r,w=os.pipe()
os.dup2(r,0)
with patch.object(o, 'command', return_value=([%r, '-I', '-c', %r], b'')):
    result=o.own({})
assert result == {'ok':False,'code':%r}, result
os.close(w)
""" % (str(Path(_owner.__file__)), sys.executable, script, expected), encoding="utf-8")
            start = time.monotonic()
            result = subprocess.run([sys.executable, str(caller)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertLess(time.monotonic() - start, 9)

    def test_eof_cancels_and_signal_order_precedes_reap(self):
        caller = self.root / "cancel.py"
        caller.write_text("""
import importlib.util, os, signal, sys
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('owner', %r)
o=importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
signal.signal(signal.SIGCHLD, signal.SIG_DFL)
r,w=os.pipe(); os.dup2(r,0); os.close(w)
with patch.object(o,'command',return_value=([sys.executable,'-I','-c','import time; time.sleep(30)'],b'')):
    assert o.own({}) == {'ok':False,'code':'NATIVE_CANCELLED'}
""" % str(Path(_owner.__file__)), encoding="utf-8")
        result = subprocess.run([sys.executable, str(caller)], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        events = []

        class Child:
            pid = 123

            def wait(self):
                events.append("reap")

        with patch.object(_owner.os, "kill", side_effect=lambda pid, sig: events.append(sig)), patch.object(_owner.time, "sleep"):
            _owner.stop(Child())
        self.assertEqual(events, [signal.SIGTERM, signal.SIGKILL, "reap"])

    def test_no_raw_native_diagnostics(self):
        with self.assertRaises(Exception) as caught:
            native({"action": "not-allowed", "text": "PRIVATE-SYNTHETIC-TEXT"})
        self.assertNotIn("PRIVATE", str(caught.exception))

    def test_sigint_requests_cleanup_without_interrupting_reap(self):
        marker = self.root / "child-started"
        script = self.root / "signal-owner.py"
        script.write_text("""
import importlib.util, sys
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('owner', %r)
o=importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
with patch.object(o,'command',return_value=([sys.executable,'-I','-c',%r],b'')):
    o.main()
""" % (str(Path(_owner.__file__)), "from pathlib import Path; import time; Path(" + repr(str(marker)) + ").write_text('ready'); time.sleep(30)"), encoding="utf-8")
        process = subprocess.Popen([sys.executable, str(script)], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            process.stdin.write(b'{"action":"version"}\n')
            process.stdin.flush()
            deadline = time.monotonic() + 2
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(marker.exists(), "real child did not initialize")
            # This test alone owns/reaps the owner. WNOWAIT preserves its identity.
            self.assertIsNone(os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT))
            os.kill(process.pid, signal.SIGINT)
            response = json.loads(process.stdout.readline())
            self.assertEqual(response, {"ok": False, "code": "NATIVE_CANCELLED"})
        finally:
            process.stdin.close()
            process.wait(timeout=8)
            process.stdout.close()

    def test_child_setup_rejects_divergent_expected_owner_without_signalling_pid(self):
        # Only our own child arms PDEATHSIG; -1 is an impossible parent ID.
        # No signal is sent to any PID obtained from process inspection.
        with subprocess.Popen([sys.executable, "-I", "-c", "raise SystemExit(0)"],
                              preexec_fn=lambda: _owner.child_setup(-1),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as child:
            self.assertEqual(child.wait(timeout=2), 126)
