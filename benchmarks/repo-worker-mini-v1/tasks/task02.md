# Task 2: Multi-file mechanical edit

Rename the fixture configuration key `tool_timeout_seconds` to `tool_timeout_s` everywhere in the repository fixture. Update all references, tests, and documentation. Do not change behavior or introduce aliases. Run the provided check command and stop when it passes.

The evaluator checks that no tracked fixture file contains the old key and all expected files contain the new key.
