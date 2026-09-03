import sys
import tempfile
import subprocess
from pathlib import Path


def run_py03_tests(code_str: str) -> dict:
    test_script = f"""
import sys
import heapq
import collections

{code_str}

def run_public():
    assert resolve_order({{"app": ["db", "api"], "api": ["db"], "db": []}}) == ["db", "api", "app"]
    assert resolve_order({{"b": [], "a": []}}) == ["a", "b"]
    return True

def run_hidden():
    # Hidden 1: Nodes appearing only inside dependency lists
    g1 = {{"web": ["auth", "db"]}}
    assert resolve_order(g1) == ["auth", "db", "web"]

    # Hidden 2: Duplicate dependencies in list
    g2 = {{"x": ["y", "y", "y"], "y": []}}
    assert resolve_order(g2) == ["y", "x"]

    # Hidden 3: Dynamic lexicographic tie-breaking at each step
    # Free initially: b, d. (Choose b).
    # Releasing from b: a is freed!
    # Now available: a, d. (Lexicographically, 'a' < 'd', so 'a' must be chosen next, even though 'd' was free first!)
    g3 = {{"c": ["a", "d"], "a": ["b"], "b": [], "d": []}}
    assert resolve_order(g3) == ["b", "a", "d", "c"]

    # Hidden 4: Self cycle
    try:
        resolve_order({{"loop": ["loop"]}})
        assert False, "Expected ValueError for self-cycle"
    except ValueError:
        pass

    # Hidden 5: Multi-node cycle
    try:
        resolve_order({{"a": ["b"], "b": ["c"], "c": ["a"]}})
        assert False, "Expected ValueError for cycle"
    except ValueError:
        pass

    # Hidden 6: Input immutability
    orig = {{"x": ["a", "b"], "y": ["x"]}}
    copy_orig = {{"x": ["a", "b"], "y": ["x"]}}
    res = resolve_order(orig)
    assert orig == copy_orig
    assert res == ["a", "b", "x", "y"]

    # Hidden 7: Scaled DAG (100 nodes chain + branches)
    deep_g = {{f"node_{{i}}": [f"node_{{i-1}}"] for i in range(1, 100)}}
    deep_g["node_0"] = []
    deep_res = resolve_order(deep_g)
    assert deep_res[0] == "node_0"
    assert deep_res[-1] == "node_99"
    assert len(deep_res) == 100

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
