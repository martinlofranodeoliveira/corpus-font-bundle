"""Isolated stdlib-only native process owner. Not a public command interface."""
import base64
import ctypes
import json
import os
import re
import selectors
import signal
import subprocess
import sys
import time

LIMIT = 256 * 1024
ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8"}
interrupted = False


def request_stop(_number, _frame):
    global interrupted
    interrupted = True


def child_setup(expected_owner):
    # This owner is single-threaded. Never arm this against a library caller.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        os._exit(126)
    if os.getppid() != expected_owner:
        os._exit(126)


def stop(child):
    # Sole reaper: no poll/wait has consumed this PID. Finish both signals first.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(child.pid, sig)
        except ProcessLookupError:
            pass
        if sig == signal.SIGTERM:
            time.sleep(0.05)
    child.wait()


def request():
    data = bytearray()
    while len(data) <= 128 * 1024:
        block = os.read(0, 4096)
        if not block:
            raise ValueError("request")
        data.extend(block)
        if b"\n" in block:
            line, extra = bytes(data).split(b"\n", 1)
            if extra:
                raise ValueError("request")
            return json.loads(line)
    raise ValueError("request")


def command(req):
    if req == {"action": "version"}:
        return ["/usr/bin/hb-shape", "--version"], b""
    if type(req) is not dict or set(req) != {"action", "font", "case"} or req["action"] != "shape":
        raise ValueError("request")
    case = req["case"]
    if type(case) is not dict or set(case) != {"text", "language", "direction", "script", "features"}:
        raise ValueError("case")
    content = case["text"]
    if type(content) is not str or not 1 <= len(content) <= 16384 or any(ord(c) < 32 or ord(c) == 127 for c in content):
        raise ValueError("text")
    if case["direction"] not in ("ltr", "rtl"):
        raise ValueError("direction")
    if not isinstance(case["language"], str) or len(case["language"]) > 63 or not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", case["language"]):
        raise ValueError("language")
    if not isinstance(case["script"], str) or not re.fullmatch(r"[A-Za-z]{4}", case["script"]):
        raise ValueError("script")
    features = case["features"]
    if type(features) is not dict or len(features) > 32:
        raise ValueError("features")
    for key, val in features.items():
        if type(key) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{3}", key) or type(val) is not int or not 0 <= val <= 65535:
            raise ValueError("features")
    if type(req["font"]) is not str or not os.path.isabs(req["font"]) or "\0" in req["font"]:
        raise ValueError("font")
    argv = ["/usr/bin/hb-shape", "--output-format=json", "--shapers=ot",
            "--direction=" + case["direction"], "--language=" + case["language"],
            "--script=" + case["script"],
            "--features=" + ",".join(k + "=" + str(v) for k, v in sorted(features.items())),
            "--text-file=-", "--", req["font"]]
    return argv, content.encode("utf-8")


def own(req):
    argv, payload = command(req)
    child = None
    reaped = False
    selector = selectors.DefaultSelector()
    try:
        start = time.monotonic()
        expected_owner = os.getpid()
        child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=ENV, preexec_fn=lambda: child_setup(expected_owner),
                                 close_fds=True)
        for stream, kind in ((child.stdout, "out"), (child.stderr, "err")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, kind)
        os.set_blocking(0, False)
        selector.register(0, selectors.EVENT_READ, "control")
        if payload:
            os.set_blocking(child.stdin.fileno(), False)
            selector.register(child.stdin, selectors.EVENT_WRITE, "input")
        else:
            child.stdin.close()
        output = bytearray()
        total = 0
        reason = None
        ended = False
        while True:
            if interrupted:
                reason = "NATIVE_CANCELLED"
            if time.monotonic() - start >= 5:
                reason = "NATIVE_TIMEOUT"
            if reason:
                stop(child)
                reaped = True
                return {"ok": False, "code": reason}
            for key, _ in selector.select(0.02):
                kind = key.data
                if kind == "control":
                    if os.read(0, 4096) == b"":
                        reason = "NATIVE_CANCELLED"
                    else:
                        reason = "NATIVE_PROTOCOL"
                elif kind == "input":
                    try:
                        count = os.write(key.fd, payload)
                        payload = payload[count:]
                    except BrokenPipeError:
                        payload = b""
                    if not payload:
                        selector.unregister(key.fileobj)
                        child.stdin.close()
                else:
                    block = os.read(key.fd, 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        total += len(block)
                        if total > LIMIT:
                            reason = "NATIVE_OUTPUT_LIMIT"
                        elif kind == "out":
                            output.extend(block)
            if reason:
                continue
            if not ended:
                ended = os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
            active = {key.data for key in selector.get_map().values()}
            if ended and not ({"out", "err"} & active):
                status = child.wait()
                reaped = True
                if status:
                    return {"ok": False, "code": "NATIVE_FAILED"}
                return {"ok": True, "stdout": base64.b64encode(output).decode("ascii")}
    finally:
        if child is not None and not reaped:
            stop(child)
        selector.close()
        if child is not None:
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream is not None:
                    stream.close()


def main():
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    # Asynchronous handlers only mark cancellation; never raise between wait and
    # the reaped marker, which would permit a second stop after child.wait().
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        result = own(request())
    except Exception:
        result = {"ok": False, "code": "NATIVE_OWNER_FAILED"}
    try:
        sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main()
