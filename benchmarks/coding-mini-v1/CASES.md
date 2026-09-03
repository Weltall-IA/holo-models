# coding-mini-v1 — Canonical Cases

Status: case specification only. The local executor must pull this file and implement the harness around these exact tasks. Do not replace, broaden, or rewrite the cases.

Benchmark scope: 5 models × 6 cases × 1 seed = 30 measured generations. Pure coding only. No repo navigation, tool-use protocol, agent loop, DFlash2, GRUG, or subjective LLM judging.

Models:
- `fable_heretic_q3km`
- `rvn_iq3m_mtp`
- `ymq_s_pro`
- `gsq_iq2s_base`
- `qwen38_9b_heretic_q4km`

Generation baseline: seed 9137, temperature 0.2, top_p 0.95, reasoning off, native GGUF chat template, 8 threads, full GPU offload, Flash Attention on, KV K=q8_0, V=q4_0. Same per-case max_tokens for every model.

## PY01 — TTL cache with injected clock

Language: Python 3.
Difficulty: medium.
Task type: implementation.

The model must return only Python code defining this public API:

```python
class TTLCache:
    def __init__(self, clock): ...
    def set(self, key, value, ttl): ...
    def get(self, key): ...
    def delete(self, key): ...
```

Contract:
- `clock` is a zero-argument callable returning the current numeric timestamp.
- `set(key, value, ttl)` stores or replaces a key. `ttl` must be strictly positive; otherwise raise `ValueError` and do not modify the cache.
- Expiration time is `clock_at_set + ttl`.
- A key is expired when `clock() >= expires_at`.
- `get(key)` returns the value for a live key and raises `KeyError` for a missing or expired key. An expired key must be removed when observed.
- `delete(key)` removes a live or expired stored key if present and returns `True`; if the key is not stored, return `False`.
- Updating an existing key replaces both value and expiry.
- The implementation must use the injected `clock`; it must not call `time.time()`, `time.monotonic()`, sleep, or inspect real time.

Public examples:
```python
now = [10.0]
c = TTLCache(lambda: now[0])
c.set("a", 7, 5)
assert c.get("a") == 7
now[0] = 14.999
assert c.get("a") == 7
now[0] = 15.0
try:
    c.get("a")
    assert False
except KeyError:
    pass

c.set("x", 1, 10)
c.set("x", 2, 1)
assert c.get("x") == 2
```

Hidden-test requirements for the harness:
- exact expiry boundary;
- replacement resets expiry;
- invalid TTL leaves old value untouched;
- fake clocks returning ints and floats;
- repeated observation of expired keys;
- delete semantics for expired-but-still-stored entries;
- source-level guard against real-time calls.

## PY02 — Repair a retry decorator

Language: Python 3.
Difficulty: medium.
Task type: debugging.

The prompt must provide this buggy starter and ask the model to return a corrected complete version of the file:

```python
from functools import wraps


def retry(max_attempts, exceptions=(Exception,)):
    attempts = 0

    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            nonlocal attempts
            while attempts <= max_attempts:
                attempts += 1
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempts >= max_attempts:
                        raise
            return None
        return wrapped
    return decorate
```

Correct contract:
- `max_attempts` means total calls to the wrapped function, not retries after the first call.
- `max_attempts <= 0` raises `ValueError` when `retry(...)` is constructed.
- Catch only exception classes supplied by `exceptions`.
- Non-matching exceptions propagate immediately.
- Attempt state is per invocation of the wrapped function; separate calls must not share counters.
- Successful return values are returned unchanged.
- On exhaustion, re-raise the last eligible exception.
- Preserve wrapped metadata via `functools.wraps`.
- No sleeping/backoff and no global mutable state.

Public examples must verify one success-after-failures case and one non-matching exception case. Hidden tests must verify exact call counts, repeated invocation isolation, metadata, tuple/single exception handling, and `max_attempts=1`.

## PY03 — Deterministic dependency order

Language: Python 3.
Difficulty: hard.
Task type: algorithm / logic.

Return only Python code defining:

```python
def resolve_order(graph): ...
```

Input contract:
- `graph` is a mapping `node -> iterable of dependencies`.
- Nodes are strings.
- A dependency must appear before the node that depends on it.
- Nodes that appear only inside dependency lists are still part of the graph.
- Duplicate dependencies do not change semantics.
- If several nodes are currently eligible, choose the lexicographically smallest node. This rule applies at every step, producing one deterministic order.
- A self-cycle or any directed cycle raises `ValueError`.
- Do not mutate `graph` or any dependency container supplied by the caller.

Public examples:
```python
assert resolve_order({"app": ["db", "api"], "api": ["db"], "db": []}) == ["db", "api", "app"]
assert resolve_order({"b": [], "a": []}) == ["a", "b"]
```

Hidden tests must include dependency-only nodes, duplicate edges, disconnected components, self-cycle, multi-node cycle, large DAGs, and a case where a one-time initial sort is insufficient because lexicographic choice must be maintained dynamically.

## CPP01 — Normalize inclusive int64 ranges safely

Language: C++20.
Difficulty: medium.
Task type: implementation.

The model must return a complete compilable C++20 program. Input/output protocol:

Input:
- first line: integer `n` (`0 <= n <= 200000`)
- next `n` lines: signed 64-bit integers `l r`

Each range is inclusive. If any input range has `l > r`, print exactly `INVALID` followed by newline and exit successfully.

Otherwise normalize all ranges by sorting and merging ranges that overlap OR are immediately adjacent. Output:
- first line: number of normalized ranges `m`
- then `m` lines `l r` in ascending order.

Critical requirement: adjacency logic must be correct at `INT64_MIN` and `INT64_MAX`; no signed overflow or undefined behavior is allowed. In particular, do not blindly evaluate `current_r + 1` when `current_r == INT64_MAX`.

Public example:
Input:
```text
5
5 7
1 2
3 4
10 10
12 14
```
Output:
```text
3
1 7
10 10
12 14
```

Hidden tests must include empty input, singleton ranges, duplicates, nested ranges, chains of adjacency, negative ranges, `INT64_MIN`, `INT64_MAX`, full-span ranges, and invalid ranges.

Compile with:
`g++ -std=c++20 -O2 -Wall -Wextra`

## CPP02 — Repair sliding-window statistics

Language: C++20.
Difficulty: medium.
Task type: debugging.

The prompt must provide a complete buggy starter program that reads:
- `n k`
- `n` signed 32-bit values

For every contiguous window of length `k`, it must print one line:
`sum min max`

Correct contract:
- sums must be exact in signed 64-bit range for the declared input bounds;
- if `k <= 0` or `k > n`, print exactly `INVALID` and exit successfully;
- negative values must work;
- complexity target: O(n log k) or O(n); an O(n*k) implementation must fail the large hidden performance case;
- output exactly `n-k+1` lines for valid input.

Canonical buggy starter for the prompt:

```cpp
#include <algorithm>
#include <iostream>
#include <vector>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;
    vector<int> a(n);
    for (int &x : a) cin >> x;

    if (k < 0 || k >= n) {
        cout << "INVALID\n";
        return 0;
    }

    int sum = 0;
    for (int i = 0; i < k; ++i) sum += a[i];

    for (int left = 0; left + k < n; ++left) {
        int mn = a[left], mx = a[left];
        for (int j = left; j <= left + k; ++j) {
            mn = min(mn, a[j]);
            mx = max(mx, a[j]);
        }
        cout << sum << ' ' << mn << ' ' << mx << '\n';
        sum -= a[left];
        sum += a[left + k];
    }
}
```

Hidden tests must independently catch:
- `k == n`;
- `k == 1`;
- invalid k values;
- missing final window;
- off-by-one access in min/max;
- 32-bit sum overflow;
- all-negative data;
- large input enforcing the complexity target.

Compile with:
`g++ -std=c++20 -O2 -Wall -Wextra`

## CPP03 — Lazy segment tree: ADD, MUL, SUM

Language: C++20.
Difficulty: hard.
Task type: algorithm / logic.

The model must return a complete C++20 program implementing range updates and range-sum queries modulo `1000000007`.

Input:
- first line: `n q`, with `1 <= n,q <= 200000`
- second line: `n` signed 64-bit initial values
- next `q` lines, each one of:
  - `ADD l r x`
  - `MUL l r x`
  - `SUM l r`

Indices are 0-based and ranges are inclusive. Inputs satisfy `0 <= l <= r < n`. Values and update operands may be negative or larger than the modulus; normalize modulo `1000000007`.

Semantics:
- `ADD l r x`: for every `i` in `[l,r]`, `a[i] = a[i] + x`
- `MUL l r x`: for every `i` in `[l,r]`, `a[i] = a[i] * x`
- `SUM l r`: print the normalized modular sum over `[l,r]`

Performance requirement: O((n+q) log n) or equivalent. Per-element range updates must fail the large hidden case.

The implementation must compose affine lazy tags correctly. If a pending transform is represented as:
`v -> v * mul + add`,
then order matters. `ADD` followed by `MUL` is not equivalent to `MUL` followed by `ADD`.

Public example:
Input:
```text
3 6
1 2 3
SUM 0 2
ADD 0 1 5
SUM 0 2
MUL 1 2 2
SUM 0 2
SUM 1 1
```
Output:
```text
6
16
28
14
```

Hidden validation requirements:
- hand-written cases for ADD→MUL and MUL→ADD;
- multiply by zero;
- negative updates;
- single-element and full-range operations;
- values well above the modulus;
- repeated affine compositions;
- deterministic randomized differential testing against a brute-force vector for at least 200 small scenarios;
- one large deterministic performance case.

Compile with:
`g++ -std=c++20 -O2 -Wall -Wextra`

## Evaluation policy

For each measured generation:
- extract only the requested code artifact;
- Python executes in a fresh temporary directory with `python -I` and a hard timeout;
- C++ compiles in a fresh temporary directory with `g++ -std=c++20 -O2 -Wall -Wextra`, then runs with a hard timeout;
- public tests and hidden tests are separate;
- PASS requires syntax/compile success + all public tests + all hidden tests;
- no subjective quality judge;
- do not repair model output before evaluation;
- preserve stdout/stderr for failures;
- report median generation tok/s and peak VRAM separately from functional PASS count.

Before any model run, the local executor must create independent reference solutions and prove that every reference passes all public and hidden tests. `CPP03` must additionally pass >=200 deterministic differential scenarios against brute force.
