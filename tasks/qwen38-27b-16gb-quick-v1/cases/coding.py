import os
import re
import subprocess
import sys
import tempfile

CODING_CASES = [
    {
        "id": "C01",
        "name": "duration_parser",
        "prompt": """Write a Python function `parse_duration(text: str) -> int` that parses a duration string and returns the total number of seconds as an integer.

Rules:
- Valid units are 'h' (hours), 'm' (minutes), and 's' (seconds), appearing at most once, in strict order: hours first, then minutes, then seconds. Example valid inputs: "1h30m", "45m", "2h5m10s", "0s", "100s", "1h".
- Each unit must be preceded by a non-negative integer.
- Reject empty strings, negative numbers, decimals, repeated units (e.g. "1h2h"), invalid units, wrong unit ordering (e.g. "30m1h", "10s5m"), whitespace, or any extraneous characters by raising `ValueError`.

Provide only the complete Python code for `parse_duration` inside a ```python ``` block. Do not include test code or explanations.""",
        "test_code": """import pytest
from solution import parse_duration

def test_valid_durations():
    assert parse_duration("1h30m") == 5400
    assert parse_duration("2h5m10s") == 7510
    assert parse_duration("45m") == 2700
    assert parse_duration("0s") == 0
    assert parse_duration("100s") == 100
    assert parse_duration("1h") == 3600
    assert parse_duration("2h30s") == 7230
    assert parse_duration("0h0m0s") == 0

def test_invalid_durations():
    invalid_cases = [
        "", " ", "abc", "-1s", "1.5h", "1h1h", "30m1h", "10s5m",
        "1h 30m", "100", "h", "m", "s", "1d", "1h2m3s4", "++1s"
    ]
    for text in invalid_cases:
        with pytest.raises(ValueError):
            parse_duration(text)
"""
    },
    {
        "id": "C02",
        "name": "stable_dedupe_bug",
        "prompt": """Fix and implement `dedupe_keep_order(items, key=None)` in Python:

Requirements:
- Deduplicate items while preserving the exact order of their first occurrence.
- If `key` is provided (a callable), use `key(item)` to determine equivalence. If `key` is None, use the item itself.
- If `key` is provided, items themselves may be unhashable (e.g. dicts, lists) as long as `key(item)` returns a hashable value.
- `key` must be called exactly once per item in `items`.
- Must not mutate the input `items`.
- Return a new list.

Provide only the complete Python code for `dedupe_keep_order` inside a ```python ``` block.""",
        "test_code": """import pytest
from solution import dedupe_keep_order

def test_basic_dedupe():
    assert dedupe_keep_order([3, 1, 2, 1, 3, 4]) == [3, 1, 2, 4]
    assert dedupe_keep_order([]) == []
    assert dedupe_keep_order(["a", "b", "a", "c"]) == ["a", "b", "c"]

def test_key_function_and_unhashable():
    data = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}, {"id": 1, "v": "c"}]
    res = dedupe_keep_order(data, key=lambda x: x["id"])
    assert res == [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]

def test_key_called_exactly_once():
    calls = []
    def my_key(x):
        calls.append(x)
        return x % 2
    items = [1, 3, 2, 4, 5]
    res = dedupe_keep_order(items, key=my_key)
    assert res == [1, 2]
    assert calls == items  # exactly once per item

def test_no_mutation():
    orig = [4, 2, 4, 1]
    copy = list(orig)
    dedupe_keep_order(orig)
    assert orig == copy
"""
    },
    {
        "id": "C03",
        "name": "ttl_cache_boundary",
        "prompt": """Implement a `TTLCache` class in Python with an injectable clock:

Requirements:
- `__init__(self, clock=None)`: accepts an optional parameterless callable `clock` that returns current time in float/int seconds. Defaults to `time.time`.
- `set(self, key, value, ttl: float)`: stores `value` for `key` which expires at `current_time + ttl`. If `key` already exists, overwrite value and update expiry.
- `get(self, key, default=None)`: returns stored value if present and not expired; otherwise returns `default`.
- Boundary condition: exact `now == expires_at` counts as EXPIRED (must return `default`).
- `delete(self, key)`: removes key if present.

Provide only the complete Python code for `TTLCache` inside a ```python ``` block.""",
        "test_code": """import pytest
from solution import TTLCache

def test_ttl_cache_injected_clock():
    current_time = 100.0
    def clock():
        return current_time

    cache = TTLCache(clock=clock)
    cache.set("a", 1, ttl=10.0) # expires at 110.0
    
    assert cache.get("a") == 1
    
    current_time = 105.0
    assert cache.get("a") == 1
    
    # Boundary: exactly at expiry time, must be expired
    current_time = 110.0
    assert cache.get("a") is None
    assert cache.get("a", "def") == "def"
    
    # After expiry
    current_time = 115.0
    assert cache.get("a") is None

def test_overwrite_and_delete():
    current_time = 50.0
    cache = TTLCache(clock=lambda: current_time)
    cache.set("k", "v1", ttl=5.0) # exp 55.0
    
    current_time = 52.0
    cache.set("k", "v2", ttl=10.0) # exp 62.0
    
    current_time = 56.0
    assert cache.get("k") == "v2"
    
    cache.delete("k")
    assert cache.get("k") is None
"""
    },
    {
        "id": "C04",
        "name": "recursive_config_merge",
        "prompt": """Implement `merge_config(base: dict, override: dict) -> dict` in Python:

Requirements:
- Return a new dictionary that merges `override` into `base`.
- If a key exists in both and both values are `dict`, recursively merge them.
- If a key exists in both and either value is NOT a `dict` (e.g. int, str, list, bool), replace the value with the one from `override`. Note: Lists are replaced, not concatenated.
- Keys present only in `base` or only in `override` are preserved.
- Neither `base` nor `override` (nor their nested dicts) must be mutated.
- The returned dict must be an independent copy (modifying it does not affect inputs).

Provide only the complete Python code for `merge_config` inside a ```python ``` block.""",
        "test_code": """import pytest
from solution import merge_config

def test_recursive_merge():
    base = {
        "app": {"name": "TestApp", "port": 8080, "tags": ["a", "b"]},
        "db": {"host": "localhost", "pool": 5},
        "debug": True
    }
    override = {
        "app": {"port": 9000, "tags": ["c"]},
        "db": {"pool": 10, "timeout": 30},
        "env": "prod"
    }
    
    merged = merge_config(base, override)
    
    assert merged == {
        "app": {"name": "TestApp", "port": 9000, "tags": ["c"]},
        "db": {"host": "localhost", "pool": 10, "timeout": 30},
        "debug": True,
        "env": "prod"
    }

def test_immutability():
    base = {"nested": {"k": "v"}, "list": [1]}
    override = {"nested": {"k2": "v2"}}
    merged = merge_config(base, override)
    
    merged["nested"]["k"] = "changed"
    assert base["nested"]["k"] == "v"
"""
    },
    {
        "id": "C05",
        "name": "retry_decorator",
        "prompt": """Implement a retry decorator `retry(max_attempts: int, exceptions: tuple)` in Python for synchronous functions:

Requirements:
- `max_attempts`: total attempts allowed (including the first attempt). If `max_attempts <= 0`, raise `ValueError`.
- `exceptions`: a tuple of exception classes (or a single exception class) that trigger a retry.
- If a decorated function raises an exception in `exceptions`, retry up to `max_attempts` total attempts.
- If the final attempt also raises an exception in `exceptions`, that exception is re-raised.
- If an exception NOT in `exceptions` is raised, it propagates immediately without further retries.
- If a call succeeds, return the result immediately.
- Preserve the decorated function's name, docstring, and signature using `functools.wraps`.

Provide only the complete Python code for `retry` inside a ```python ``` block.""",
        "test_code": """import pytest
from solution import retry

def test_successful_retry():
    attempts = 0
    @retry(max_attempts=3, exceptions=(ValueError, KeyError))
    def flaky(x):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("transient")
        return x * 2

    assert flaky(5) == 10
    assert attempts == 3

def test_unhandled_exception_no_retry():
    attempts = 0
    @retry(max_attempts=3, exceptions=(ValueError,))
    def fail_type():
        nonlocal attempts
        attempts += 1
        raise TypeError("unexpected")

    with pytest.raises(TypeError):
        fail_type()
    assert attempts == 1

def test_exceed_max_attempts():
    attempts = 0
    @retry(max_attempts=2, exceptions=(RuntimeError,))
    def always_fail():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        always_fail()
    assert attempts == 2

def test_preserves_metadata():
    @retry(max_attempts=2, exceptions=(Exception,))
    def sample_fn(a, b=1):
        \"\"\"Sample doc.\"\"\"
        return a + b

    assert sample_fn.__name__ == "sample_fn"
    assert sample_fn.__doc__ == "Sample doc."
"""
    },
    {
        "id": "C06",
        "name": "bounded_chunk_iterator",
        "prompt": """Implement `chunked(iterable, size: int)` in Python as a lazy generator/iterator of lists:

Requirements:
- `size`: maximum number of items in each chunk. Raise `ValueError("size must be > 0")` if `size <= 0`.
- Return an iterator yielding chunks (each chunk is a Python `list`).
- Must work with one-shot generators and infinite/lazy iterables (do NOT pre-materialize the full input into memory with `list(iterable)` or `len(iterable)`).
- The last chunk may have fewer than `size` items if the total number of items is not evenly divisible by `size`.
- If `iterable` is empty, yield nothing.

Provide only the complete Python code for `chunked` inside a ```python ``` block.""",
        "test_code": """import pytest
from solution import chunked

def test_chunked_list():
    assert list(chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert list(chunked([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]]
    assert list(chunked([], 3)) == []

def test_one_shot_generator():
    def gen():
        for i in range(5):
            yield i
    g = gen()
    chunks = list(chunked(g, 2))
    assert chunks == [[0, 1], [2, 3], [4]]

def test_invalid_size():
    with pytest.raises(ValueError):
        list(chunked([1, 2], 0))
    with pytest.raises(ValueError):
        list(chunked([1, 2], -1))
"""
    }
]

def extract_python_code(text: str) -> str:
    # Try finding markdown python code block
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # If no code block, strip leading/trailing whitespace
    return text.strip()

def run_coding_eval(case: dict, model_response: str) -> dict:
    code = extract_python_code(model_response)
    with tempfile.TemporaryDirectory() as tmpdir:
        sol_path = os.path.join(tmpdir, "solution.py")
        test_path = os.path.join(tmpdir, "run_tests.py")
        
        with open(sol_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        test_script = f"""
import sys

class _RaisesContext:
    def __init__(self, expected_exc):
        self.expected_exc = expected_exc
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(f"Expected exception {{self.expected_exc}} was not raised")
        return issubclass(exc_type, self.expected_exc)

class _PytestShim:
    @staticmethod
    def raises(expected_exc):
        return _RaisesContext(expected_exc)

sys.modules['pytest'] = _PytestShim()

# Test Code
{case['test_code']}

# Execute all test functions
test_funcs = [v for k, v in list(locals().items()) if k.startswith('test_') and callable(v)]
for fn in test_funcs:
    fn()

print("ALL_TESTS_PASSED")
"""
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(test_script)
            
        res = subprocess.run(
            [sys.executable, test_path],
            cwd=tmpdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        passed = (res.returncode == 0 and "ALL_TESTS_PASSED" in res.stdout)
        return {
            "success": 1 if passed else 0,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "extracted_code": code
        }
