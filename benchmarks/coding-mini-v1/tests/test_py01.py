import ast
import inspect
import sys
import tempfile
import subprocess
from pathlib import Path


def run_py01_tests(code_str: str) -> dict:
    # 1. AST Static Guard: Ensure time.time, time.monotonic, time.sleep are not used
    tree = ast.parse(code_str)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr in ("time", "monotonic", "sleep", "perf_counter"):
                if isinstance(node.value, ast.Name) and node.value.id == "time":
                    return {
                        "public_pass": False,
                        "hidden_pass": False,
                        "error": f"AST Guard: forbidden real-time call 'time.{node.attr}' detected"
                    }

    test_script = f"""
import sys

{code_str}

def run_public():
    now = [10.0]
    c = TTLCache(lambda: now[0])
    c.set("a", 7, 5)
    assert c.get("a") == 7
    now[0] = 14.999
    assert c.get("a") == 7
    now[0] = 15.0
    try:
        c.get("a")
        assert False, "KeyError expected at exact expiry boundary"
    except KeyError:
        pass

    c.set("x", 1, 10)
    c.set("x", 2, 1)
    assert c.get("x") == 2
    return True

def run_hidden():
    # Test 1: Exact expiry boundary and invalid TTL
    t = [100.0]
    c = TTLCache(lambda: t[0])
    c.set("k1", "v1", 10.0) # exp 110.0
    
    # Invalid TTL must raise ValueError and leave old value intact
    for bad_ttl in [0, -1, -0.001]:
        try:
            c.set("k1", "bad", bad_ttl)
            assert False, f"Expected ValueError for ttl={{bad_ttl}}"
        except ValueError:
            pass
            
    assert c.get("k1") == "v1"

    # Test 2: Clock int vs float
    t[0] = 109
    assert c.get("k1") == "v1"
    t[0] = 110
    try:
        c.get("k1")
        assert False
    except KeyError:
        pass

    # Test 3: Repeated observation of expired keys
    try:
        c.get("k1")
        assert False
    except KeyError:
        pass

    # Test 4: Delete semantics for live and expired stored entries
    t[0] = 200
    c.set("k2", "v2", 5) # exp 205
    t[0] = 210 # expired
    assert c.delete("k2") is True
    assert c.delete("k2") is False
    assert c.delete("nonexistent") is False

    # Test 5: Replacement resets expiry
    t[0] = 300
    c.set("k3", 10, 5) # exp 305
    t[0] = 304
    assert c.get("k3") == 10
    c.set("k3", 20, 10) # exp 314
    t[0] = 308
    assert c.get("k3") == 20
    t[0] = 313.99
    assert c.get("k3") == 20
    t[0] = 314.0
    try:
        c.get("k3")
        assert False
    except KeyError:
        pass

    return True

if __name__ == "__main__":
    assert run_public(), "Public tests failed"
    print("__PUBLIC_PASS__")
    assert run_hidden(), "Hidden tests failed"
    print("__HIDDEN_PASS__")
"""

    with tempfile.TemporaryDirectory() as td:
        script_file = Path(td) / "test_case.py"
        script_file.write_text(test_script, encoding="utf-8")
        try:
            p = subprocess.run(
                [sys.executable, "-I", str(script_file)],
                capture_output=True,
                text=True,
                timeout=5
            )
            pub_ok = "__PUBLIC_PASS__" in p.stdout
            hid_ok = "__HIDDEN_PASS__" in p.stdout and p.returncode == 0
            err = (p.stdout + "\n" + p.stderr).strip() if (not pub_ok or not hid_ok) else None
            return {"public_pass": pub_ok, "hidden_pass": hid_ok, "error": err}
        except subprocess.TimeoutExpired:
            return {"public_pass": False, "hidden_pass": False, "error": "Timeout after 5s"}
        except Exception as exc:
            return {"public_pass": False, "hidden_pass": False, "error": f"{type(exc).__name__}: {exc}"}
