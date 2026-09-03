import sys
import tempfile
import subprocess
from pathlib import Path


def run_py02_tests(code_str: str) -> dict:
    test_script = f"""
import sys
import functools
from functools import wraps

{code_str}

def run_public():
    # Public 1: Success after failure
    attempts = 0
    @retry(max_attempts=3, exceptions=(ValueError,))
    def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("fail")
        return "ok"

    assert flaky() == "ok"
    assert attempts == 2

    # Public 2: Non-matching exception propagates immediately
    attempts2 = 0
    @retry(max_attempts=3, exceptions=(ValueError,))
    def bad_type():
        nonlocal attempts2
        attempts2 += 1
        raise TypeError("wrong type")

    try:
        bad_type()
        assert False, "TypeError should have propagated"
    except TypeError:
        pass
    assert attempts2 == 1
    return True

def run_hidden():
    # Hidden 1: max_attempts <= 0 raises ValueError
    for bad_n in [0, -1, -5]:
        try:
            retry(max_attempts=bad_n)
            assert False, f"Expected ValueError for max_attempts={{bad_n}}"
        except ValueError:
            pass

    # Hidden 2: Call counts and exception exhaustion
    count = 0
    @retry(max_attempts=4, exceptions=(RuntimeError,))
    def always_fail(x):
        nonlocal count
        count += 1
        raise RuntimeError(f"error_{{x}}_{{count}}")

    try:
        always_fail(10)
        assert False
    except RuntimeError as e:
        assert str(e) == "error_10_4"
    assert count == 4

    # Hidden 3: Per-invocation state isolation (counter resets on new call)
    count = 0
    try:
        always_fail(20)
        assert False
    except RuntimeError as e:
        assert str(e) == "error_20_4"
    assert count == 4 # Ran 4 times again

    # Hidden 4: Metadata preservation
    @retry(max_attempts=2, exceptions=(Exception,))
    def sample_func(a: int, b: str = "x") -> str:
        \"\"\"Docstring test.\"\"\"
        return f"{{a}}_{{b}}"

    assert sample_func.__name__ == "sample_func"
    assert sample_func.__doc__ == "Docstring test."

    # Hidden 5: Single exception class (not in tuple)
    calls = 0
    @retry(max_attempts=3, exceptions=KeyError)
    def single_exc():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise KeyError("transient")
        return "done"

    assert single_exc() == "done"
    assert calls == 3

    # Hidden 6: max_attempts=1
    c1 = 0
    @retry(max_attempts=1, exceptions=(Exception,))
    def one_shot():
        nonlocal c1
        c1 += 1
        raise ValueError("instant")

    try:
        one_shot()
        assert False
    except ValueError:
        pass
    assert c1 == 1

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
