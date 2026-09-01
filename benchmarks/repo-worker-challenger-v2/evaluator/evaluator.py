from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


TEXT_EXTS = {".py", ".pyi", ".json", ".md", ".toml", ".yaml", ".yml"}


def ordered_contains(text: str, items: list[str]) -> bool:
    pos = -1
    low = text.lower()
    for item in items:
        idx = low.find(item.lower(), pos + 1)
        if idx < 0:
            return False
        pos = idx
    return True


def run_pytest(worktree: Path, targets: list[str], pytest_bin: Path) -> dict[str, Any]:
    env = os.environ.copy()
    if pytest_bin.exists():
        env["PATH"] = f"{pytest_bin.parent}:{env.get('PATH', '')}"
    cmd = [str(pytest_bin) if pytest_bin.exists() else "pytest", "-q", *targets]
    try:
        p = subprocess.run(
            cmd,
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        return {
            "ok": p.returncode == 0,
            "exit_code": p.returncode,
            "stdout": p.stdout[-12000:],
            "stderr": p.stderr[-12000:],
            "command": cmd,
        }
    except Exception as exc:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "command": cmd,
        }


def run_hidden_pytest(
    task: dict[str, Any],
    worktree: Path,
    benchmark_dir: Path,
    pytest_bin: Path,
) -> dict[str, Any]:
    hidden_rel = task.get("hidden")
    if not hidden_rel:
        return {"applicable": False, "ok": None}
    bundle_path = benchmark_dir / "hidden" / "hidden_files.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if hidden_rel not in bundle:
        return {"applicable": True, "ok": False, "error": f"Hidden test missing from bundle: {hidden_rel}"}
    dst = worktree / task["hidden_dest"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(bundle[hidden_rel], encoding="utf-8")
    targets = [*task.get("public_tests", []), task["hidden_dest"]]
    result = run_pytest(worktree, targets, pytest_bin)
    result["applicable"] = True
    try:
        dst.unlink()
    except FileNotFoundError:
        pass
    return result


def _files_with_old_symbol(root: Path, symbol: str) -> list[str]:
    out = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in TEXT_EXTS:
            continue
        try:
            if symbol in p.read_text(encoding="utf-8", errors="replace"):
                out.append(str(p))
        except OSError:
            pass
    return out


def _recovery_check(events: list[dict[str, Any]], required_path: str) -> dict[str, Any]:
    fail_turn = None
    success_after = None
    for event in events:
        action = event.get("action") or {}
        res = event.get("tool_res") or {}
        if (
            action.get("action") == "read"
            and action.get("path") == required_path
            and res.get("ok") is False
            and fail_turn is None
        ):
            fail_turn = event.get("turn")
            continue
        if fail_turn is not None and res.get("ok") is True and action.get("action") in {"list", "search", "read"}:
            success_after = event.get("turn")
            break
    return {
        "required_failure_seen": fail_turn is not None,
        "required_failure_turn": fail_turn,
        "successful_recovery_turn": success_after,
        "recovery_pass": fail_turn is not None and success_after is not None,
    }


def _stopping_metrics(events: list[dict[str, Any]], evidence_tokens: list[str]) -> dict[str, Any]:
    cumulative = ""
    evidence_turn = None
    for event in events:
        cumulative += "\n" + json.dumps(event.get("tool_res", {}), ensure_ascii=False)
        cumulative += "\n" + (event.get("content") or "")
        low = cumulative.lower()
        if evidence_turn is None and all(tok.lower() in low for tok in evidence_tokens):
            evidence_turn = event.get("turn")
    if evidence_turn is None:
        return {
            "evidence_turn": None,
            "turns_after_evidence": None,
            "non_done_actions_after_evidence": None,
        }
    actions_after = 0
    max_turn = 0
    for event in events:
        turn = int(event.get("turn") or 0)
        max_turn = max(max_turn, turn)
        if turn > evidence_turn:
            action = event.get("action") or {}
            if action.get("action") != "done":
                actions_after += 1
    return {
        "evidence_turn": evidence_turn,
        "turns_after_evidence": max(0, max_turn - evidence_turn),
        "non_done_actions_after_evidence": actions_after,
    }


def evaluate_task(
    task: dict[str, Any],
    trace: dict[str, Any],
    worktree: Path,
    benchmark_dir: Path,
    pytest_bin: Path,
) -> dict[str, Any]:
    done_seen = bool(trace.get("done_seen"))
    timed_out = bool(trace.get("timed_out"))
    request_error = bool(trace.get("request_error"))
    protocol_pass = done_seen and not timed_out and not request_error
    final_answer = trace.get("final_answer", "") or ""
    edited = set(trace.get("files_edited", []))

    result: dict[str, Any] = {
        "protocol_pass": protocol_pass,
        "done_seen": done_seen,
        "timed_out": timed_out,
        "request_error": request_error,
        "functional_pass": False,
        "hidden_tests_pass": None,
        "recovery_required": False,
        "recovery_pass": None,
        "architecture_pass": None,
        "test_authoring_pass": None,
    }

    kind = task["kind"]

    if kind == "ordered_oracle":
        result["functional_pass"] = ordered_contains(final_answer, task["expected_chain"])
        result["ordered_chain_expected"] = task["expected_chain"]

    elif kind in {"hidden_pytest", "feature_test_authoring", "multifile", "architecture"}:
        hidden = run_hidden_pytest(task, worktree, benchmark_dir, pytest_bin)
        result["hidden_test_result"] = hidden
        result["hidden_tests_pass"] = bool(hidden.get("ok"))
        required_edits = set(task.get("required_edits", []))
        required_edits_pass = required_edits.issubset(edited)
        result["required_edits_pass"] = required_edits_pass
        result["missing_required_edits"] = sorted(required_edits - edited)

        if kind == "hidden_pytest":
            result["functional_pass"] = bool(hidden.get("ok")) and required_edits_pass

        elif kind == "feature_test_authoring":
            test_path = worktree / "challenge/feature/test_cache.py"
            text = test_path.read_text(encoding="utf-8", errors="replace") if test_path.exists() else ""
            test_authoring = (
                "challenge/feature/test_cache.py" in edited
                and "invalidate_prefix" in text
                and len(re.findall(r"(?m)^def test_", text)) >= 2
            )
            result["test_authoring_pass"] = test_authoring
            result["functional_pass"] = bool(hidden.get("ok")) and required_edits_pass and test_authoring

        elif kind == "multifile":
            target_root = worktree / "challenge/multifile"
            old_hits = _files_with_old_symbol(target_root, "max_attempts")
            new_hits = _files_with_old_symbol(target_root, "retry_limit")
            structural = not old_hits and len(new_hits) >= 5
            result["old_symbol_hits"] = [str(Path(x).relative_to(worktree)) for x in old_hits]
            result["retry_limit_files"] = [str(Path(x).relative_to(worktree)) for x in new_hits]
            result["structural_pass"] = structural
            result["functional_pass"] = bool(hidden.get("ok")) and required_edits_pass and structural

        elif kind == "architecture":
            forbidden = set(task.get("forbidden_edits", []))
            no_forbidden_edits = not bool(forbidden & edited)
            policy_path = worktree / "challenge/arch/policy/access.py"
            service_path = worktree / "challenge/arch/service/profile_service.py"
            policy_text = policy_path.read_text(encoding="utf-8", errors="replace") if policy_path.exists() else ""
            service_text = service_path.read_text(encoding="utf-8", errors="replace") if service_path.exists() else ""
            architecture_pass = (
                required_edits_pass
                and no_forbidden_edits
                and "reserved:" in policy_text
                and "reserved:" not in service_text
                and "policy" in service_text
            )
            result["architecture_pass"] = architecture_pass
            result["forbidden_edits_seen"] = sorted(forbidden & edited)
            result["functional_pass"] = bool(hidden.get("ok")) and architecture_pass

    elif kind == "mandatory_recovery":
        result["recovery_required"] = True
        rec = _recovery_check(trace.get("events", []), task["required_failed_read"])
        result.update(rec)
        result["functional_pass"] = all(x.lower() in final_answer.lower() for x in task["expected_answer"])

    elif kind == "stopping":
        result["functional_pass"] = all(x.lower() in final_answer.lower() for x in task["expected_answer"])
        no_edits = len(edited) == 0
        result["no_edit_pass"] = no_edits
        result["functional_pass"] = result["functional_pass"] and no_edits
        result["stopping_metrics"] = _stopping_metrics(trace.get("events", []), task["evidence_tokens"])

    mandatory = [protocol_pass, bool(result["functional_pass"])]
    if result["recovery_required"]:
        mandatory.append(bool(result["recovery_pass"]))
    result["passed"] = all(mandatory)
    return result
