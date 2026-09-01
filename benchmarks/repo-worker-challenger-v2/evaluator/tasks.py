TASKS = [
    {
        "id": "task01_deep_repo_navigation",
        "slug": "nav",
        "fixture": "task01_nav",
        "dest": "challenge/nav",
        "kind": "ordered_oracle",
        "instruction": (
            "A synthetic role-routing subsystem exists under `challenge/nav`. Determine the complete active routing chain "
            "from the user-facing role request through alias resolution, binding resolution, canonical role instructions, "
            "formal contract, and final write-scope policy. Several plausible legacy/decoy files exist. Do not edit anything. "
            "Emit `done` with the ordered chain of repository-relative paths and a short explanation of why that chain is active."
        ),
        "expected_chain": [
            "challenge/nav/config/entrypoint.yaml",
            "challenge/nav/registry/role_aliases.yaml",
            "challenge/nav/routing/role_bindings.yaml",
            "challenge/nav/roles/writer/guide.md",
            "challenge/nav/contracts/scoped-writer.yaml",
            "challenge/nav/policies/write-scope.yaml",
        ],
    },
    {
        "id": "task02_diagnostic_bugfix",
        "slug": "diag",
        "fixture": "task02_diag",
        "dest": "challenge/diag",
        "kind": "hidden_pytest",
        "instruction": (
            "The pagination tests in `challenge/diag/test_pager.py` are failing. Diagnose the underlying implementation bug "
            "without being told its location, make the smallest correct fix, run `pytest challenge/diag/test_pager.py`, "
            "and emit `done` when the behavior is correct. Preserve valid cursor behavior for empty/final pages and arbitrary limits."
        ),
        "public_tests": ["challenge/diag/test_pager.py"],
        "hidden": "task02/test_pager_hidden.py",
        "hidden_dest": "challenge/diag/test_pager_hidden.py",
        "required_edits": ["challenge/diag/pager.py"],
    },
    {
        "id": "task03_semantic_regression_trap",
        "slug": "semantic",
        "fixture": "task03_semantic",
        "dest": "challenge/semantic",
        "kind": "hidden_pytest",
        "instruction": (
            "Extend the rule table under `challenge/semantic` with namespace-prefix rules via "
            "`add_namespace(prefix, action)`. Exact rules registered with `add_exact` must remain exact-only and take precedence. "
            "When multiple namespace rules match, the longest prefix must win. Update the implementation as needed, run the public "
            "tests, and emit `done`. Preserve all existing exact-rule semantics."
        ),
        "public_tests": ["challenge/semantic/test_rules.py"],
        "hidden": "task03/test_rules_hidden.py",
        "hidden_dest": "challenge/semantic/test_rules_hidden.py",
        "required_edits": ["challenge/semantic/rules.py"],
    },
    {
        "id": "task04_feature_and_test_authoring",
        "slug": "feature",
        "fixture": "task04_feature",
        "dest": "challenge/feature",
        "kind": "feature_test_authoring",
        "instruction": (
            "In `challenge/feature`, add `LRUCache.invalidate_prefix(prefix)`. It must remove every entry whose key is a string "
            "starting with `prefix`, leave non-string keys untouched, preserve the remaining LRU order, and return the number removed. "
            "Add meaningful public tests for the new behavior, run `pytest challenge/feature/test_cache.py`, and emit `done`."
        ),
        "public_tests": ["challenge/feature/test_cache.py"],
        "hidden": "task04/test_cache_hidden.py",
        "hidden_dest": "challenge/feature/test_cache_hidden.py",
        "required_edits": ["challenge/feature/cache.py", "challenge/feature/test_cache.py"],
    },
    {
        "id": "task05_real_multifile_change",
        "slug": "multifile",
        "fixture": "task05_multifile",
        "dest": "challenge/multifile",
        "kind": "multifile",
        "instruction": (
            "Within `challenge/multifile`, replace the public setting `max_attempts` with `retry_limit` throughout the implementation "
            "and all consumers. Preserve the default value 3, change the environment override to `RETRY_LIMIT`, keep code/stub/config/docs/tests "
            "consistent, discover all affected files yourself, run `pytest challenge/multifile/test_client.py`, and emit `done`."
        ),
        "public_tests": ["challenge/multifile/test_client.py"],
        "hidden": "task05/test_multifile_hidden.py",
        "hidden_dest": "challenge/multifile/test_multifile_hidden.py",
        "required_edits": [
            "challenge/multifile/settings.py",
            "challenge/multifile/client.py",
            "challenge/multifile/schema.pyi",
            "challenge/multifile/config.json",
            "challenge/multifile/README.md",
            "challenge/multifile/test_client.py",
        ],
    },
    {
        "id": "task06_mandatory_recovery",
        "slug": "recovery",
        "fixture": "task06_recovery",
        "dest": "challenge/recovery",
        "kind": "mandatory_recovery",
        "instruction": (
            "Start by reading `challenge/recovery/runtime_effective.py`. If it does not exist, handle that tool error, locate the actual "
            "effective runtime settings under `challenge/recovery`, determine the configured default worker timeout, and emit `done` with "
            "the confirmed value and the repository-relative path of the authoritative settings file. Do not edit anything."
        ),
        "required_failed_read": "challenge/recovery/runtime_effective.py",
        "expected_answer": ["45", "challenge/recovery/runtime/settings.py"],
    },
    {
        "id": "task07_architectural_placement",
        "slug": "arch",
        "fixture": "task07_arch",
        "dest": "challenge/arch",
        "kind": "architecture",
        "instruction": (
            "The mini application under `challenge/arch` follows transport -> service -> policy/repository boundaries. "
            "Add the rule that any target user id beginning with `reserved:` is denied before the repository is queried. "
            "Access-decision logic belongs in the policy layer; the service should consume that policy rather than duplicating the rule. "
            "Preserve normal/admin behavior, run `pytest challenge/arch/test_profile.py`, and emit `done`."
        ),
        "public_tests": ["challenge/arch/test_profile.py"],
        "hidden": "task07/test_arch_hidden.py",
        "hidden_dest": "challenge/arch/test_arch_hidden.py",
        "required_edits": [
            "challenge/arch/policy/access.py",
            "challenge/arch/service/profile_service.py",
        ],
        "forbidden_edits": [
            "challenge/arch/transport/api.py",
            "challenge/arch/repository/profiles.py",
        ],
    },
    {
        "id": "task08_stopping_control",
        "slug": "stopping",
        "fixture": "task08_stopping",
        "dest": "challenge/stopping",
        "kind": "stopping",
        "instruction": (
            "Investigate the audit-export configuration under `challenge/stopping`. Determine which backend is actually active and "
            "the exact enabling condition that makes it active. Legacy and documentation files may contain stale alternatives. "
            "Do not edit anything. Once the authoritative evidence is sufficient, emit `done` with the backend and enabling condition."
        ),
        "expected_answer": ["ledger-v2", "export_audit", "true"],
        "evidence_tokens": ["ledger-v2", "export_audit = true"],
    },
]
