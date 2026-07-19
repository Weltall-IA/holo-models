from __future__ import annotations

import unittest

from holo_benchmark.inventory import (
    _origin_matches_holo_models,
    _remote_repository_slug,
    gate0_passes,
)


def command(stdout: str = "", returncode: int = 0) -> dict[str, object]:
    return {
        "args": [],
        "returncode": returncode,
        "duration_seconds": 0.0,
        "stdout": stdout,
        "stderr": "",
    }


def valid_system_info() -> dict[str, object]:
    return {
        "filesystem_project": {"free_bytes": 10 * 1024**3},
        "nvidia": {"available": False},
        "torch_cuda": {
            "imported": False,
            "cuda_available": False,
            "allocation_tested": False,
            "allocation_passed": False,
        },
    }


def valid_environment() -> dict[str, object]:
    return {
        "repo_root": "/home/alpha/Playstoria/models",
        "task_status": {
            "branch": "ai/embedding-benchmark-v3",
            "expected_head": "PENDING_STATUS_COMMIT",
        },
        "commands": {
            "git_status": command(),
            "git_untracked": command("runtime/vane-native-ops/README.md"),
            "git_branch": command("ai/embedding-benchmark-v3"),
            "git_head": command("abc123"),
            "git_origin_master": command("def456"),
            "git_origin_url": command(
                "https://github.com/Weltall-IA/holo-models.git"
            ),
        },
    }


class InventoryRepositoryTests(unittest.TestCase):
    def test_normalizes_https_and_ssh_origins(self) -> None:
        self.assertEqual(
            _remote_repository_slug(
                "https://github.com/Weltall-IA/holo-models.git"
            ),
            "weltall-ia/holo-models",
        )
        self.assertEqual(
            _remote_repository_slug("git@github.com:Weltall-IA/holo-models.git"),
            "weltall-ia/holo-models",
        )
        self.assertTrue(
            _origin_matches_holo_models(
                "ssh://git@github.com/Weltall-IA/holo-models.git"
            )
        )

    def test_local_directory_name_does_not_define_repository_identity(self) -> None:
        ok, errors = gate0_passes(valid_system_info(), valid_environment())
        self.assertTrue(ok, errors)
        self.assertEqual(errors, [])

    def test_untracked_residue_is_informational(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_untracked"] = command(
            "runtime/vane-native-ops/README.md"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertTrue(ok, errors)

    def test_tracked_changes_still_block_gate(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_status"] = command(" M AGENTS.md")
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertFalse(ok)
        self.assertIn(
            "working tree possui alterações em arquivos rastreados",
            errors,
        )

    def test_wrong_origin_blocks_gate(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_origin_url"] = command(
            "https://github.com/Weltall-IA/infra-holoplay.git"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertFalse(ok)
        self.assertTrue(
            any("remote origin não corresponde" in error for error in errors)
        )

    def test_gate0_outputs_do_not_block(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_status"] = command(
            " M benchmark/embedding-v3/GATE_0_REPORT.md"
            "\n M benchmark/embedding-v3/environment.json"
            "\n M benchmark/embedding-v3/system_info.json"
            "\n M benchmark/embedding-v3/gate_status.json"
            "\n M benchmark/embedding-v3/requirements-resolved.txt"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertTrue(ok, errors)
        self.assertNotIn(
            "working tree possui alterações em arquivos rastreados",
            errors,
        )

    def test_non_gate0_change_still_blocks(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_status"] = command(
            " M benchmark/embedding-v3/GATE_0_REPORT.md"
            "\n M benchmark/embedding-v3/environment.json"
            "\n M AGENTS.md"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertFalse(ok)
        self.assertIn(
            "working tree possui alterações em arquivos rastreados",
            errors,
        )

    def test_gate0_only_blocked_by_real_changes(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_status"] = command(
            " M benchmark/embedding-v3/GATE_0_REPORT.md"
            "\n M benchmark/embedding-v3/environment.json"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertTrue(ok, errors)
        # Agora adiciona uma alteração real fora dos outputs
        environment["commands"]["git_status"] = command(
            " M benchmark/embedding-v3/GATE_0_REPORT.md"
            "\n M benchmark/embedding-v3/holo_benchmark/inventory.py"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertFalse(ok)

    def test_bak_suffix_still_blocks(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_status"] = command(
            " M benchmark/embedding-v3/GATE_0_REPORT.md.bak"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertFalse(ok)
        self.assertIn(
            "working tree possui alterações em arquivos rastreados",
            errors,
        )

    def test_prefixed_path_still_blocks(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_status"] = command(
            " M xbenchmark/embedding-v3/GATE_0_REPORT.md"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertFalse(ok)

    def test_substring_name_still_blocks(self) -> None:
        environment = valid_environment()
        environment["commands"]["git_status"] = command(
            " M benchmark/embedding-v3/GATE_0_REPORT_extra.md"
        )
        ok, errors = gate0_passes(valid_system_info(), environment)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
