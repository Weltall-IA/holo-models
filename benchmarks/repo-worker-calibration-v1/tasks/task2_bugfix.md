# Task 2: Bugfix

Fix the bug in the fixture retry helper: `retry_call` in `fixture/retry.py` incorrectly executes an extra attempt and retries unselected exception types.
Read the failing test `fixture/test_retry.py` and the implementation in `fixture/retry.py`, fix the implementation, run `pytest fixture/test_retry.py`, and emit `done` once all tests pass.
