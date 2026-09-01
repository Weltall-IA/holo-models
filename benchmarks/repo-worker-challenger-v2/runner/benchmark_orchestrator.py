#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path("/home/alpha/Playstoria/models")
BENCHMARK_DIR = ROOT / "benchmarks/repo-worker-challenger-v2"
SOURCE_REPO = Path("/home/alpha/Playstoria/holo-agent-tooling")
WORK_ROOT = Path("/tmp/repo-worker-challenger-v2-worktrees")
PYTEST_BIN = ROOT / ".venv/bin/pytest"

RUNTIME_REPO = ROOT / "engines/deepgrove-llama.cpp"
RUNTIME_BIN = RUNTIME_REPO / "build/bin/llama-server"
LLAMA_BENCH = RUNTIME_REPO / "build/bin/llama-bench"
EXPECTED_RUNTIME_SHA = "8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1"

PORT = 8147
SEED = 9137
TASK_TIMEOUT = 480
REQUEST_TIMEOUT_CEILING = 240
MAX_TURNS = 40

sys.path.insert(0, str(BENCHMARK_DIR / "evaluator"))
from tasks import TASKS  # noqa: E402
from evaluator import evaluate_task  # noqa: E402


PROFILES = [
    {
        "id": "gsq-iq2s-off",
        "name": "Qwen3.8-27B GSQ-RCO IQ2_S (Thinking OFF)",
        "model_path": ROOT / "text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf",
        "model_sha256": "16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb",
        "thinking": False,
        "temperature": 0.2,
        "top_p": 0.95,
    },
    {
        "id": "gsq-iq3xxs-on",
        "name": "Qwen3.8-27B GSQ-RCO IQ3_XXS (Thinking ON)",
        "model_path": ROOT / "text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ3_XXS/Qwen3.8-27B-GSQ-RCO-IQ3_XXS.gguf",
        "model_sha256": "fdfcb6a29b11188956dfbfd904223588a6c1b77eb250c3e8a36e1bd269df91f7",
        "thinking": True,
        "temperature": 0.6,
        "top_p": 0.95,
    },
    {
        "id": "qwen38-9b-heretic-off",
        "name": "Qwen3.8-9B Distill uncensored/heretic Q4_K_M (Thinking OFF)",
        "model_path": ROOT / "text/petruhonk-Qwen3.8-9B-Distill-uncensored-heretic/Qwen3.8-9B-Distill-uncensored-heretic.i1-Q4_K_M.gguf",
        "model_sha256": "3a63c5b5c7c6af57d92437ed2610d524ea96a7ecf873ae7f8e470a024c047fa6",
        "thinking": False,
        "temperature": 0.2,
        "top_p": 0.95,
    },
    {
        "id": "ornith-15-9b-off",
        "name": "Ornith 1.5 9B Q5_K_M (Thinking OFF)",
        "model_path": ROOT / "text/bartowski-Ornith-1.5-9B-Q5_K_M/Ornith-1.5-9B-Q5_K_M.gguf",
        "model_sha256": "b50e44fd4e4dc2a14e5b864cbc296885d111e772c07286efbac9a20c1f1c63ab",
        "thinking": False,
        "temperature": 0.2,
        "top_p": 0.95,
    },
]


TOOLS_DESCRIPTION = r'''
Available tools. Emit exactly one JSON object per turn, with no markdown or surrounding prose:
{"action":"list","path":"."}
{"action":"search","query":"literal or regex","path":"."}
{"action":"read","path":"relative/path","start":1,"end":200}
{"action":"edit","path":"relative/path","old":"exact old string","new":"new replacement string"}
{"action":"patch","diff":"unified diff text"}
{"action":"run","command":"pytest relative/test_file.py"}
{"action":"done","answer":"final answer"}

Rules:
- Use only repository-relative paths.
- Run the requested public tests after editing.
- Do not assume public tests cover all acceptance criteria.
- Do not use absolute paths or parent traversal.
- When finished, emit done.
'''.strip()


def sha256_file(path: Path, chunk_size: int = 16 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def git_output(repo: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if p.returncode != 0:
        return ""
    return p.stdout.strip()


def source_repo_head() -> str:
    return git_output(SOURCE_REPO, "rev-parse", "HEAD")


def runtime_head() -> str:
    return git_output(RUNTIME_REPO, "rev-parse", "HEAD")


def atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


def sample_vram() -> tuple[int, int]:
    try:
        p = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        used, total = p.stdout.strip().split(",")[:2]
        return int(used.strip()), int(total.strip())
    except Exception:
        return 0, 0


def safe_path(worktree: Path, rel_path: str) -> Path:
    if not isinstance(rel_path, str) or not rel_path:
        raise ValueError("path must be a non-empty relative string")
    candidate = Path(rel_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe path: {rel_path}")
    p = (worktree / candidate).resolve()
    w = worktree.resolve()
    if p != w and w not in p.parents:
        raise ValueError(f"Path outside worktree: {rel_path}")
    return p


def safe_pytest_command(command: str) -> tuple[bool, str]:
    forbidden_fragments = ["..", "/home/", "/tmp/", "/mnt/", "$", "`", "&&", "||", ";", "|", ">", "<"]
    if any(fragment in command for fragment in forbidden_fragments):
        return False, "Command rejected: shell traversal/metacharacter/absolute path is not allowed"
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return False, f"Command parse error: {exc}"
    if not argv:
        return False, "Empty command"
    for token in argv:
        if token.startswith("/") or token.startswith("~"):
            return False, "Absolute/home-expanded paths are not allowed"
    allowed = False
    if argv[0] == "pytest":
        allowed = True
    elif len(argv) >= 3 and argv[0] in {"python", "python3"} and argv[1:3] == ["-m", "pytest"]:
        allowed = True
    if not allowed:
        return False, "Only pytest commands are allowed through the run tool"
    return True, ""


def patch_paths(diff: str) -> list[str]:
    paths = []
    for line in diff.splitlines():
        if not line.startswith("+++ "):
            continue
        raw = line[4:].strip().split("\t", 1)[0]
        if raw == "/dev/null":
            continue
        if raw.startswith("b/"):
            raw = raw[2:]
        candidate = Path(raw)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"Unsafe patch path: {raw}")
        paths.append(raw)
    return sorted(set(paths))


def apply_patch(worktree: Path, diff: str) -> tuple[int, str]:
    patch_paths(diff)
    p = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=worktree,
        input=diff,
        text=True,
        capture_output=True,
        timeout=30,
    )
    return p.returncode, p.stdout + p.stderr


def tool_call(worktree: Path, action: dict[str, Any]) -> dict[str, Any]:
    name = action.get("action")
    try:
        if name == "list":
            path = safe_path(worktree, action.get("path", "."))
            if not path.exists():
                return {"ok": False, "error": f"Path not found: {action.get('path', '.')}"}
            if not path.is_dir():
                return {"ok": False, "error": f"Not a directory: {action.get('path', '.')}"}
            entries = []
            for item in sorted(path.iterdir()):
                if item.name.startswith(".git"):
                    continue
                entries.append({"name": str(item.relative_to(worktree)), "type": "dir" if item.is_dir() else "file"})
            return {"ok": True, "entries": entries[:500]}

        if name == "search":
            query = str(action.get("query", ""))
            path = safe_path(worktree, action.get("path", "."))
            p = subprocess.run(
                ["rg", "-n", "--hidden", "--glob", "!.git", query, str(path)],
                cwd=worktree,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {"ok": p.returncode in {0, 1}, "matches": p.stdout[-30000:], "exit_code": p.returncode}

        if name == "read":
            rel = action["path"]
            path = safe_path(worktree, rel)
            if not path.exists() or not path.is_file():
                return {"ok": False, "error": f"File not found: {rel}"}
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            start = max(1, int(action.get("start", 1)))
            end = min(len(lines), int(action.get("end", start + 199)))
            content = "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1))
            return {"ok": True, "path": rel, "start": start, "end": end, "content": content}

        if name == "edit":
            rel = action["path"]
            path = safe_path(worktree, rel)
            if not path.exists() or not path.is_file():
                return {"ok": False, "error": f"File not found: {rel}"}
            old = action.get("old", "")
            new = action.get("new", "")
            if not isinstance(old, str) or not old:
                return {"ok": False, "error": "Missing non-empty old string"}
            content = path.read_text(encoding="utf-8", errors="replace")
            if old not in content:
                return {"ok": False, "error": f"Target old string not found in {rel}"}
            path.write_text(content.replace(old, str(new), 1), encoding="utf-8")
            return {"ok": True, "path": rel, "message": "Successfully edited file"}

        if name == "patch":
            diff = str(action.get("diff", ""))
            code, output = apply_patch(worktree, diff)
            return {"ok": code == 0, "patch_exit_code": code, "output": output[-20000:]}

        if name == "run":
            command = str(action.get("command", ""))
            allowed, reason = safe_pytest_command(command)
            if not allowed:
                return {"ok": False, "error": reason}
            env = os.environ.copy()
            if PYTEST_BIN.exists():
                env["PATH"] = f"{PYTEST_BIN.parent}:{env.get('PATH', '')}"
            p = subprocess.run(command, cwd=worktree, env=env, shell=True, capture_output=True, text=True, timeout=120)
            return {"ok": p.returncode == 0, "exit_code": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:]}

        if name == "done":
            return {"ok": True, "done": True, "answer": action.get("answer", "")}

        return {"ok": False, "error": f"Unknown action: {name}"}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _request_json_worker(conn, url: str, payload: dict[str, Any]) -> None:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_CEILING + 30) as response:
            conn.send({"ok": True, "response": json.loads(response.read().decode())})
    except Exception as exc:
        conn.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        conn.close()


def request_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    parent, child = multiprocessing.Pipe(duplex=False)
    worker = multiprocessing.Process(target=_request_json_worker, args=(child, url, payload))
    worker.start()
    child.close()
    deadline = time.monotonic() + max(0.01, timeout)
    result = None
    while worker.is_alive() and time.monotonic() < deadline:
        if parent.poll(0.05):
            result = parent.recv()
            worker.join(5)
            break
    if result is None and worker.is_alive():
        worker.terminate()
        worker.join(5)
        parent.close()
        raise TimeoutError(f"Request exceeded timeout ({timeout:.2f}s)")
    try:
        if result is None:
            if not parent.poll():
                raise RuntimeError(f"Request worker exited with code {worker.exitcode}")
            result = parent.recv()
    finally:
        parent.close()
    if not result["ok"]:
        raise urllib.error.URLError(result["error"])
    return result["response"]


def profile_server_args(profile: dict[str, Any]) -> list[str]:
    return [
        "-m", str(profile["model_path"]), "--host", "127.0.0.1", "--port", str(PORT),
        "-c", "32768", "-np", "1", "-ngl", "999", "-fa", "on", "-ctk", "q8_0", "-ctv", "q4_0",
        "-t", "4", "-tb", "4", "--no-webui", "--reasoning", "on" if profile["thinking"] else "off",
    ]


def start_server(profile: dict[str, Any], log_path: Path):
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{RUNTIME_BIN.parent}:{env.get('LD_LIBRARY_PATH', '')}"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    log_file.write(f"\n\n===== SERVER START {time.strftime('%Y-%m-%d %H:%M:%S')} profile={profile['id']} =====\n")
    log_file.flush()
    proc = subprocess.Popen([str(RUNTIME_BIN), *profile_server_args(profile)], env=env, stdout=log_file, stderr=subprocess.STDOUT)
    return proc, log_file


def wait_for_server(timeout: int = 240) -> bool:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{PORT}/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 300:
                    return True
        except Exception:
            time.sleep(1)
    return False


def stop_server(proc, log_file) -> None:
    if proc is not None:
        try:
            proc.terminate()
            proc.wait(timeout=15)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=10)
            except Exception:
                pass
    if log_file is not None and not log_file.closed:
        log_file.close()
    time.sleep(2)


def setup_worktree(task: dict[str, Any], worktree: Path) -> None:
    if worktree.exists():
        shutil.rmtree(worktree)
    worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", f"file://{SOURCE_REPO}", str(worktree)],
        capture_output=True, text=True, check=True, timeout=90,
    )
    public_bundle = json.loads((BENCHMARK_DIR / "fixtures" / "public_files.json").read_text(encoding="utf-8"))
    fixture_prefix = task["fixture"].rstrip("/") + "/"
    fixture_dst = worktree / task["dest"]
    fixture_dst.mkdir(parents=True, exist_ok=True)
    matched = 0
    for bundled_path, content in public_bundle.items():
        if not bundled_path.startswith(fixture_prefix):
            continue
        rel = bundled_path[len(fixture_prefix):]
        dst = fixture_dst / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")
        matched += 1
    if matched == 0:
        raise RuntimeError(f"No public fixture files found for {task['fixture']}")
    challenge_init = worktree / "challenge/__init__.py"
    if not challenge_init.exists():
        challenge_init.parent.mkdir(parents=True, exist_ok=True)
        challenge_init.write_text("", encoding="utf-8")


def strict_action_from_content(content: str) -> tuple[dict[str, Any] | None, str | None]:
    clean = re.sub(r"<think>.*?</think>", "", content or "", flags=re.DOTALL).strip()
    try:
        obj = json.loads(clean)
    except Exception as exc:
        return None, f"Invalid strict JSON action: {type(exc).__name__}: {exc}"
    if not isinstance(obj, dict) or "action" not in obj:
        return None, "JSON output must be an object with an action property"
    return obj, None


def run_agent_task(profile: dict[str, Any], task: dict[str, Any], worktree: Path) -> dict[str, Any]:
    prompt = (
        "You are a precise repository-worker agent. Complete the assigned task.\n\n"
        f"# {task['id']}\n{task['instruction']}\n\n"
        f"{TOOLS_DESCRIPTION}\n\n"
        "Begin by obtaining the minimum repository context needed for this task."
    )
    messages = [
        {"role": "system", "content": "You are a precise repository-worker agent. Follow the tool protocol strictly. Output ONLY one valid JSON object per turn."},
        {"role": "user", "content": prompt},
    ]

    events = []
    files_read = set()
    files_edited = set()
    successful_edits = 0
    failed_edits = 0
    tool_errors = 0
    recovered_tool_errors = 0
    protocol_errors = 0
    last_tool_error = False
    final_answer = ""
    done_seen = False
    timed_out = False
    request_error = False
    request_error_message = None
    time_to_first_useful = None
    time_to_first_edit = None
    peak_vram_mib = 0
    total_prompt_tokens = 0
    total_output_tokens = 0
    total_reasoning_tokens = 0

    started = time.perf_counter()
    url = f"http://127.0.0.1:{PORT}/v1/chat/completions"

    for turn in range(1, MAX_TURNS + 1):
        elapsed = time.perf_counter() - started
        remaining = TASK_TIMEOUT - elapsed
        if remaining <= 0:
            timed_out = True
            events.append({"turn": turn, "type": "task_timeout", "elapsed": elapsed})
            break

        used, _ = sample_vram()
        peak_vram_mib = max(peak_vram_mib, used)

        payload = {
            "model": profile["id"], "messages": messages, "temperature": profile["temperature"],
            "top_p": profile["top_p"], "seed": SEED, "max_tokens": 1536,
        }
        try:
            response_timeout = min(float(REQUEST_TIMEOUT_CEILING), max(10.0, remaining))
            resp = request_json(url, payload, timeout=response_timeout)
        except Exception as exc:
            request_error = True
            request_error_message = f"{type(exc).__name__}: {exc}"
            events.append({"turn": turn, "type": "request_error", "error": request_error_message, "elapsed": time.perf_counter() - started})
            break

        choice = resp["choices"][0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""
        usage = resp.get("usage") or {}
        total_prompt_tokens += int(usage.get("prompt_tokens") or 0)
        total_output_tokens += int(usage.get("completion_tokens") or 0)
        details = usage.get("completion_tokens_details") or {}
        total_reasoning_tokens += int(details.get("reasoning_tokens") or 0)

        action, parse_error = strict_action_from_content(content)
        event = {
            "turn": turn,
            "elapsed_before_action_s": time.perf_counter() - started,
            "content": content,
            "reasoning": reasoning,
            "finish_reason": choice.get("finish_reason"),
            "usage": usage,
            "action": action,
        }

        if action is None:
            protocol_errors += 1
            tool_errors += 1
            last_tool_error = True
            event["tool_res"] = {"ok": False, "error": parse_error}
            events.append(event)
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": "Protocol error: output exactly one JSON tool action object and nothing else."})
            continue

        act_name = action.get("action")
        if time_to_first_useful is None and act_name in {"list", "search", "read"}:
            time_to_first_useful = time.perf_counter() - started
        if act_name == "read" and action.get("path"):
            files_read.add(str(action["path"]))
        if act_name == "edit" and action.get("path"):
            files_edited.add(str(action["path"]))
            if time_to_first_edit is None:
                time_to_first_edit = time.perf_counter() - started
        if act_name == "patch" and time_to_first_edit is None:
            time_to_first_edit = time.perf_counter() - started

        result = tool_call(worktree, action)
        event["tool_res"] = result
        event["elapsed_after_tool_s"] = time.perf_counter() - started

        if result.get("ok") and act_name == "patch":
            try:
                for patched_path in patch_paths(str(action.get("diff", ""))):
                    files_edited.add(patched_path)
            except Exception:
                pass

        if result.get("ok"):
            if last_tool_error:
                recovered_tool_errors += 1
                last_tool_error = False
            if act_name in {"edit", "patch"}:
                successful_edits += 1
        else:
            tool_errors += 1
            last_tool_error = True
            if act_name in {"edit", "patch"}:
                failed_edits += 1

        events.append(event)
        if act_name == "done":
            done_seen = True
            final_answer = str(action.get("answer", ""))
            break

        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": f"Tool Result: {json.dumps(result, ensure_ascii=False)}"})

    total_time_s = time.perf_counter() - started
    if not done_seen and not request_error and total_time_s >= TASK_TIMEOUT:
        timed_out = True

    return {
        "task_id": task["id"], "profile_id": profile["id"], "seed": SEED,
        "done_seen": done_seen, "timed_out": timed_out, "request_error": request_error,
        "request_error_message": request_error_message, "final_answer": final_answer,
        "total_time_s": total_time_s, "time_to_first_useful_s": time_to_first_useful,
        "time_to_first_edit_s": time_to_first_edit, "peak_vram_mib": peak_vram_mib,
        "total_turns": len(events), "tool_errors": tool_errors, "protocol_errors": protocol_errors,
        "recovered_tool_errors": recovered_tool_errors, "files_read": sorted(files_read),
        "files_edited": sorted(files_edited), "successful_edits": successful_edits,
        "failed_edits": failed_edits, "prompt_tokens": total_prompt_tokens,
        "output_tokens": total_output_tokens, "reasoning_tokens": total_reasoning_tokens,
        "events": events,
    }


def parse_server_log(log_path: Path) -> dict[str, Any]:
    prompt = []
    decode = []
    if not log_path.exists():
        return {"prompt_tps": None, "decode_tps": None, "prompt_samples": 0, "decode_samples": 0}
    pattern = re.compile(r"\(\s*[\d.]+\s*ms per token,\s*([\d.]+)\s*tokens per second\s*\)")
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "prompt eval time" in line:
            m = pattern.search(line)
            if m:
                prompt.append(float(m.group(1)))
        elif "eval time" in line:
            m = pattern.search(line)
            if m:
                decode.append(float(m.group(1)))
    return {
        "prompt_tps": sum(prompt) / len(prompt) if prompt else None,
        "decode_tps": sum(decode) / len(decode) if decode else None,
        "prompt_samples": len(prompt), "decode_samples": len(decode),
    }


def run_llama_bench(profile: dict[str, Any], output_path: Path) -> dict[str, Any]:
    if not LLAMA_BENCH.exists():
        return {"ok": False, "error": f"llama-bench not found: {LLAMA_BENCH}"}
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{LLAMA_BENCH.parent}:{env.get('LD_LIBRARY_PATH', '')}"
    cmd = [
        str(LLAMA_BENCH), "-m", str(profile["model_path"]), "-ngl", "999", "-fa", "1",
        "-ctk", "q8_0", "-ctv", "q4_0", "-t", "4", "-p", "512", "-n", "128", "-r", "3",
    ]
    try:
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        text = p.stdout + p.stderr
        output_path.write_text(text, encoding="utf-8")
        pp = None
        tg = None
        for line in text.splitlines():
            if "pp512" in line.lower():
                nums = re.findall(r"([\d.]+)\s*±", line)
                if nums:
                    pp = float(nums[-1])
            if "tg128" in line.lower():
                nums = re.findall(r"([\d.]+)\s*±", line)
                if nums:
                    tg = float(nums[-1])
        return {"ok": p.returncode == 0, "exit_code": p.returncode, "pp512": pp, "tg128": tg, "command": cmd}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "command": cmd}


def sanity_check(profile: dict[str, Any]) -> dict[str, Any]:
    url = f"http://127.0.0.1:{PORT}/v1/chat/completions"
    checks = [
        ("arithmetic", "Answer with only the number: 17 * 23", "391"),
        ("capital", "Answer with only the capital of France.", "Paris"),
    ]
    out = {}
    for key, prompt, expected in checks:
        payload = {
            "model": profile["id"], "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0, "top_p": 1.0, "seed": SEED, "max_tokens": 64,
        }
        try:
            resp = request_json(url, payload, timeout=120)
            msg = resp["choices"][0].get("message", {})
            content = (msg.get("content") or "") + "\n" + (msg.get("reasoning_content") or "")
            out[key] = {"ok": expected.lower() in content.lower(), "expected": expected, "content": content[-1000:]}
        except Exception as exc:
            out[key] = {"ok": False, "expected": expected, "error": f"{type(exc).__name__}: {exc}"}
    out["ok"] = all(v.get("ok") for k, v in out.items() if k != "ok")
    return out


def preflight_static() -> dict[str, Any]:
    source_head = source_repo_head()
    runtime_sha = runtime_head()
    data = {
        "source_repo": str(SOURCE_REPO), "source_repo_head": source_head,
        "source_repo_dirty": bool(git_output(SOURCE_REPO, "status", "--porcelain")),
        "runtime_repo": str(RUNTIME_REPO), "runtime_bin": str(RUNTIME_BIN),
        "runtime_sha": runtime_sha, "expected_runtime_sha": EXPECTED_RUNTIME_SHA,
        "runtime_sha_match": runtime_sha == EXPECTED_RUNTIME_SHA, "seed": SEED, "profiles": {},
    }
    for profile in PROFILES:
        path = Path(profile["model_path"])
        exists = path.exists()
        actual_sha = sha256_file(path) if exists else None
        data["profiles"][profile["id"]] = {
            "name": profile["name"], "model_path": str(path), "exists": exists,
            "size_bytes": path.stat().st_size if exists else None,
            "expected_sha256": profile["model_sha256"], "actual_sha256": actual_sha,
            "sha_match": actual_sha == profile["model_sha256"] if actual_sha else False,
            "thinking": profile["thinking"], "temperature": profile["temperature"], "top_p": profile["top_p"],
        }
    return data


def write_preflight_markdown(preflight: dict[str, Any]) -> None:
    lines = [
        "# Preflight — Repo-Worker Challenger v2", "",
        f"- Source repo HEAD: `{preflight.get('source_repo_head', '')}`",
        f"- Source repo dirty at observation: `{preflight.get('source_repo_dirty')}`",
        f"- Runtime SHA: `{preflight.get('runtime_sha', '')}`",
        f"- Expected runtime SHA: `{preflight.get('expected_runtime_sha', '')}`",
        f"- Runtime SHA match: `{preflight.get('runtime_sha_match')}`",
        f"- Seed: `{preflight.get('seed')}`", "",
        "| profile | model SHA match | size bytes | sanity | PP512 | TG128 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pid, row in preflight.get("profiles", {}).items():
        sanity = row.get("sanity", {})
        bench = row.get("llama_bench", {})
        sanity_text = "—" if not sanity else ("PASS" if sanity.get("ok") else "FAIL")
        pp = "—" if bench.get("pp512") is None else f"{bench['pp512']:.2f}"
        tg = "—" if bench.get("tg128") is None else f"{bench['tg128']:.2f}"
        lines.append(f"| {pid} | {row.get('sha_match')} | {row.get('size_bytes') or '—'} | {sanity_text} | {pp} | {tg} |")
    (BENCHMARK_DIR / "PREFLIGHT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(static_preflight: dict[str, Any]) -> None:
    manifest = {
        "benchmark": "repo-worker-challenger-v2", "created_by_runner_version": 1,
        "seed": SEED, "planned_runs": len(PROFILES) * len(TASKS),
        "source_repo_head": static_preflight["source_repo_head"], "runtime_sha": static_preflight["runtime_sha"],
        "task_timeout_s": TASK_TIMEOUT, "request_timeout_ceiling_s": REQUEST_TIMEOUT_CEILING, "max_turns": MAX_TURNS,
        "profiles": [
            {
                "id": p["id"], "name": p["name"], "model_path": str(p["model_path"]),
                "model_sha256": p["model_sha256"], "thinking": p["thinking"],
                "temperature": p["temperature"], "top_p": p["top_p"], "server_args": profile_server_args(p),
            } for p in PROFILES
        ],
        "tasks": [{"id": t["id"], "kind": t["kind"], "instruction": t["instruction"]} for t in TASKS],
    }
    atomic_json(BENCHMARK_DIR / "RUN_MANIFEST.json", manifest)


def collect_results(preflight: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    results = {}
    raw_metrics = {}
    for profile in PROFILES:
        pid = profile["id"]
        pdir = BENCHMARK_DIR / "profiles" / pid
        task_rows = []
        for task in TASKS:
            path = pdir / f"{task['id']}.json"
            if path.exists():
                task_rows.append(json.loads(path.read_text(encoding="utf-8")))
        server = parse_server_log(pdir / "tasks_server.log")
        bench = (preflight.get("profiles", {}).get(pid, {}) or {}).get("llama_bench", {})
        passed = sum(1 for row in task_rows if row.get("evaluation", {}).get("passed"))
        hidden_applicable = [row for row in task_rows if row.get("evaluation", {}).get("hidden_tests_pass") is not None]
        hidden_passes = sum(1 for row in hidden_applicable if row.get("evaluation", {}).get("hidden_tests_pass") is True)
        protocol_failures = sum(1 for row in task_rows if not row.get("evaluation", {}).get("protocol_pass", False))
        recovery_rows = [row for row in task_rows if row.get("evaluation", {}).get("recovery_required")]
        recovery_passes = sum(1 for row in recovery_rows if row.get("evaluation", {}).get("recovery_pass") is True)
        times = [float(row.get("total_time_s") or 0) for row in task_rows if row.get("total_time_s") is not None]
        total_tool_errors = sum(int(row.get("tool_errors") or 0) for row in task_rows)
        peak_vram = max([int(row.get("peak_vram_mib") or 0) for row in task_rows] or [0])
        valid_pass_time = sum(float(row.get("total_time_s") or 0) for row in task_rows if row.get("evaluation", {}).get("passed") and row.get("total_time_s") is not None)
        tasks_per_hour = passed / (valid_pass_time / 3600.0) if passed and valid_pass_time > 0 else 0.0
        results[pid] = {
            "profile": profile["name"], "runs_present": len(task_rows), "passed": passed,
            "total_tasks": len(TASKS), "hidden_passes": hidden_passes, "hidden_applicable": len(hidden_applicable),
            "protocol_failures": protocol_failures,
            "recovery": f"{recovery_passes}/{len(recovery_rows)}" if recovery_rows else "n/a",
            "median_time_s": statistics.median(times) if times else None,
            "avg_time_s": statistics.mean(times) if times else None,
            "tool_errors": total_tool_errors, "peak_vram_mib": peak_vram,
            "tasks_per_hour_valid_passes": tasks_per_hour,
            "server_prompt_tps": server["prompt_tps"], "server_decode_tps": server["decode_tps"],
            "server_prompt_samples": server["prompt_samples"], "server_decode_samples": server["decode_samples"],
            "pp512": bench.get("pp512"), "tg128": bench.get("tg128"),
        }
        raw_metrics[pid] = {"tasks": task_rows, "server_tps": server, "llama_bench": bench}
    return results, raw_metrics


def write_factual_markdown(results: dict[str, Any]) -> None:
    lines = [
        "# Objective Results — Repo-Worker Challenger v2", "",
        "No ranking or causal interpretation is produced by the runner.", "",
        "| profile | passed/8 | hidden passes | protocol failures | recovery | median time | tool errors | peak VRAM | TG128 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pid, row in results.items():
        med = "—" if row["median_time_s"] is None else f"{row['median_time_s']:.1f}s"
        tg = "—" if row["tg128"] is None else f"{row['tg128']:.2f}"
        lines.append(
            f"| {pid} | {row['passed']}/8 | {row['hidden_passes']}/{row['hidden_applicable']} | "
            f"{row['protocol_failures']} | {row['recovery']} | {med} | {row['tool_errors']} | "
            f"{row['peak_vram_mib']} MiB | {tg} |"
        )
    (BENCHMARK_DIR / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", nargs="*", help="Optional subset of profile ids")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    WORK_ROOT.mkdir(parents=True, exist_ok=True)

    static = preflight_static()
    atomic_json(BENCHMARK_DIR / "PREFLIGHT.json", static)
    write_preflight_markdown(static)
    write_manifest(static)

    fatal = []
    if not static["runtime_sha_match"]:
        fatal.append(f"Runtime SHA mismatch: expected {EXPECTED_RUNTIME_SHA}, got {static['runtime_sha']}")
    for pid, p in static["profiles"].items():
        if not p["exists"]:
            fatal.append(f"{pid}: model file missing")
        elif not p["sha_match"]:
            fatal.append(f"{pid}: model SHA mismatch")
    if fatal:
        print("PREFLIGHT FAILED")
        for item in fatal:
            print(f"- {item}")
        return 2

    selected = PROFILES
    if args.profiles:
        wanted = set(args.profiles)
        selected = [p for p in PROFILES if p["id"] in wanted]
        unknown = wanted - {p["id"] for p in selected}
        if unknown:
            print(f"Unknown profile ids: {sorted(unknown)}")
            return 2

    preflight = static

    for profile in selected:
        pid = profile["id"]
        pdir = BENCHMARK_DIR / "profiles" / pid
        pdir.mkdir(parents=True, exist_ok=True)
        llama_bench_result = run_llama_bench(profile, pdir / "llama-bench.txt")
        preflight["profiles"][pid]["llama_bench"] = llama_bench_result
        atomic_json(BENCHMARK_DIR / "PREFLIGHT.json", preflight)
        write_preflight_markdown(preflight)

        if args.preflight_only:
            continue

        remaining = [task for task in TASKS if not (pdir / f"{task['id']}.json").exists()]
        if not remaining:
            print(f"[{pid}] all task traces already exist; preserving them")
            continue

        proc = None
        log_file = None
        try:
            proc, log_file = start_server(profile, pdir / "tasks_server.log")
            if not wait_for_server(timeout=240):
                raise RuntimeError("llama-server did not become healthy within 240s")

            sanity = sanity_check(profile)
            preflight["profiles"][pid]["sanity"] = sanity
            atomic_json(BENCHMARK_DIR / "PREFLIGHT.json", preflight)
            write_preflight_markdown(preflight)
            if not sanity.get("ok"):
                raise RuntimeError(f"sanity check failed: {sanity}")

            for task in remaining:
                out_path = pdir / f"{task['id']}.json"
                worktree = WORK_ROOT / f"{pid}_{task['id']}"
                print(f"[{pid}] {task['id']} ...", flush=True)
                try:
                    setup_worktree(task, worktree)
                    trace = run_agent_task(profile, task, worktree)
                    evaluation = evaluate_task(task, trace, worktree, BENCHMARK_DIR, PYTEST_BIN)
                    trace["evaluation"] = evaluation
                    trace["infra_error"] = False
                except Exception as exc:
                    trace = {
                        "task_id": task["id"], "profile_id": pid, "seed": SEED,
                        "infra_error": True, "infra_error_message": f"{type(exc).__name__}: {exc}",
                        "evaluation": {"passed": False, "protocol_pass": False, "functional_pass": False, "infra_error": True},
                    }
                atomic_json(out_path, trace)
                status = "INFRA_ERROR" if trace.get("infra_error") else ("PASS" if trace.get("evaluation", {}).get("passed") else "FAIL")
                print(f"[{pid}] {task['id']} -> {status}", flush=True)

        except Exception as exc:
            preflight["profiles"][pid]["server_infra_error"] = f"{type(exc).__name__}: {exc}"
            atomic_json(BENCHMARK_DIR / "PREFLIGHT.json", preflight)
            write_preflight_markdown(preflight)
            print(f"[{pid}] INFRA_ERROR: {type(exc).__name__}: {exc}")
        finally:
            stop_server(proc, log_file)

    results, raw_metrics = collect_results(preflight)
    atomic_json(BENCHMARK_DIR / "RESULTS.json", results)
    atomic_json(BENCHMARK_DIR / "RAW_METRICS.json", raw_metrics)
    write_factual_markdown(results)

    runs_completed = sum(row["runs_present"] for row in results.values())
    infra_errors = sum(1 for row in preflight.get("profiles", {}).values() if row.get("server_infra_error"))
    for pid in results:
        pdir = BENCHMARK_DIR / "profiles" / pid
        for task in TASKS:
            fp = pdir / f"{task['id']}.json"
            if fp.exists():
                obj = json.loads(fp.read_text(encoding="utf-8"))
                infra_errors += int(bool(obj.get("infra_error")))

    print(f"SOURCE_REPO_HEAD={preflight['source_repo_head']}")
    print(f"SEED={SEED}")
    print(f"RUNS_COMPLETED={runs_completed}/{len(PROFILES) * len(TASKS)}")
    print(f"INFRA_ERRORS={infra_errors}")
    print("RESULTS_TABLE=benchmarks/repo-worker-challenger-v2/RESULTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
