# Task 3: Small bugfix

Fix the fixture bug described by the failing test: a retry helper incorrectly retries exceptions that are not listed in `retry_on`, and its attempt count is off by one. Read the implementation and tests, make the smallest fix, run the provided test command, and repair the patch if the first attempt fails.
