#!/usr/bin/env python3
"""
Master Orchestrator for repo-worker-final-short-v1.
Runs 6 tasks across 4 candidates with 1 seed:
- O1: Ornith 1.5 9B Q5_K_M (Thinking OFF, ctx 32768)
- B4: Ternary Bonsai 27B (Thinking ON + DSpark ON, ctx 8192)
- M1: Qwen3.8-20B-Minitron IQ3_M (Thinking OFF, ctx 16384)
- V1: Vireqo-27B-Plus (Thinking OFF, ctx 2048, corrected config)
"""

import argparse
import json
import multiprocessing
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path('/home/alpha/Playstoria/models')
BENCHMARK_DIR = ROOT / 'benchmarks/repo-worker-final-short-v1'
SOURCE_REPO = Path('/home/alpha/Playstoria/holo-agent-tooling')
WORK_ROOT = Path('/tmp/repo-worker-short-v1-worktrees')
PYTEST_BIN = Path('/home/alpha/Playstoria/models/.venv/bin/pytest')

PORT = 8135

PROFILES = [
    {
        'key': 'O1',
        'id': 'ornith-off',
        'name': 'Ornith 1.5 9B (Thinking OFF)',
        'runtime_type': 'deepgrove',
        'runtime_bin': ROOT / 'engines/deepgrove-llama.cpp/build/bin/llama-server',
        'runtime_libs': str(ROOT / 'engines/deepgrove-llama.cpp/build/bin'),
        'runtime_sha': '8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1',
        'model_path': ROOT / 'text/bartowski-Ornith-1.5-9B-Q5_K_M/Ornith-1.5-9B-Q5_K_M.gguf',
        'model_sha256': 'b50e44fd4e4dc2a14e5b864cbc296885d111e772c07286efbac9a20c1f1c63ab',
        'thinking': False,
        'context': 32768,
        'server_args': ['-m', str(ROOT / 'text/bartowski-Ornith-1.5-9B-Q5_K_M/Ornith-1.5-9B-Q5_K_M.gguf'), '--host', '127.0.0.1', '--port', str(PORT), '-c', '32768', '-np', '1', '-ngl', '999', '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q4_0', '-t', '4', '-tb', '4', '--no-webui', '--reasoning', 'off'],
        'sampling': {'temperature': 0.2, 'top_p': 0.95}
    },
    {
        'key': 'B4',
        'id': 'bonsai-thinking-on-dspark',
        'name': 'Ternary Bonsai 27B (Thinking ON + DSpark ON)',
        'runtime_type': 'prism',
        'runtime_bin': ROOT / 'engines/prism-llama/llama-prism-b9599-9ca265a/llama-server',
        'runtime_libs': f"/home/alpha/.lmstudio/extensions/backends/vendor/linux-llama-cuda12-vendor-v1:{ROOT / 'engines/prism-llama/llama-prism-b9599-9ca265a'}",
        'runtime_sha': '9ca265a57f85f2117942490f421f64a226dd9847',
        'model_path': ROOT / 'text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf',
        'model_sha256': '527f276ddf047b3494de964985b5529b9fc3ecf739ea64d8fab3a6ef8403e81d',
        'thinking': True,
        'context': 8192,
        'server_args': ['-m', str(ROOT / 'text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf'), '-md', str(ROOT / 'text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-dspark-Q4_1.gguf'), '--host', '127.0.0.1', '--port', str(PORT), '-c', '8192', '-np', '1', '-ngl', '999', '-ngld', '999', '--spec-type', 'draft-dspark', '--spec-draft-n-max', '4', '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q4_0', '-t', '4', '-tb', '4', '--no-webui', '--reasoning', 'on'],
        'sampling': {'temperature': 0.7, 'top_p': 0.95, 'top_k': 20}
    },
    {
        'key': 'M1',
        'id': 'minitron-20b-iq3m',
        'name': 'Qwen3.8-20B-Minitron IQ3_M (Thinking OFF)',
        'runtime_type': 'deepgrove',
        'runtime_bin': ROOT / 'engines/deepgrove-llama.cpp/build/bin/llama-server',
        'runtime_libs': str(ROOT / 'engines/deepgrove-llama.cpp/build/bin'),
        'runtime_sha': '8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1',
        'model_path': ROOT / 'text/mradermacher-Qwen3.8-20B-Minitron-i1-IQ3_M/Qwen3.8-20B-Minitron.i1-IQ3_M.gguf',
        'model_sha256': '253f542604f42433cf9fad806b30c0d1243418c5b543eca56ad62c0761b12bbd',
        'thinking': False,
        'context': 16384,
        'server_args': ['-m', str(ROOT / 'text/mradermacher-Qwen3.8-20B-Minitron-i1-IQ3_M/Qwen3.8-20B-Minitron.i1-IQ3_M.gguf'), '--host', '127.0.0.1', '--port', str(PORT), '-c', '16384', '-np', '1', '-ngl', '999', '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q4_0', '-t', '4', '-tb', '4', '--no-webui', '--reasoning', 'off'],
        'sampling': {'temperature': 0.2, 'top_p': 0.95}
    },
    {
        'key': 'M1-ON',
        'id': 'minitron-20b-iq3m-on',
        'name': 'Qwen3.8-20B-Minitron IQ3_M (Thinking ON)',
        'runtime_type': 'deepgrove',
        'runtime_bin': ROOT / 'engines/deepgrove-llama.cpp/build/bin/llama-server',
        'runtime_libs': str(ROOT / 'engines/deepgrove-llama.cpp/build/bin'),
        'runtime_sha': '8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1',
        'model_path': ROOT / 'text/mradermacher-Qwen3.8-20B-Minitron-i1-IQ3_M/Qwen3.8-20B-Minitron.i1-IQ3_M.gguf',
        'model_sha256': '253f542604f42433cf9fad806b30c0d1243418c5b543eca56ad62c0761b12bbd',
        'thinking': True,
        'context': 16384,
        'server_args': ['-m', str(ROOT / 'text/mradermacher-Qwen3.8-20B-Minitron-i1-IQ3_M/Qwen3.8-20B-Minitron.i1-IQ3_M.gguf'), '--host', '127.0.0.1', '--port', str(PORT), '-c', '16384', '-np', '1', '-ngl', '999', '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q4_0', '-t', '4', '-tb', '4', '--no-webui', '--reasoning', 'on'],
        'sampling': {'temperature': 0.6, 'top_p': 0.95}
    },
    {
        'key': 'V1',
        'id': 'vireqo-corrected',
        'name': 'Vireqo-27B-Plus (Corrected Reference Profile)',
        'runtime_type': 'deepgrove',
        'runtime_bin': ROOT / 'engines/deepgrove-llama.cpp/build/bin/llama-server',
        'runtime_libs': str(ROOT / 'engines/deepgrove-llama.cpp/build/bin'),
        'runtime_sha': '8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1',
        'model_path': ROOT / 'text/Vireqo-27B-Plus-260816/Vireqo-27B-Plus-260816.gguf',
        'model_sha256': 'a32a8ec286a11c6534bf29d1ee20bd4c02064032b51ae8310bb1216e2de17e03',
        'thinking': False,
        'context': 2048,
        'server_args': ['-m', str(ROOT / 'text/Vireqo-27B-Plus-260816/Vireqo-27B-Plus-260816.gguf'), '--host', '127.0.0.1', '--port', str(PORT), '-c', '2048', '-np', '1', '-ngl', '999', '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q8_0', '-t', '4', '-tb', '4', '--no-webui', '--reasoning', 'off'],
        'sampling': {'temperature': 0.7, 'top_k': 20, 'top_p': 0.95, 'min_p': 0, 'repeat_penalty': 1.08, 'repeat_last_n': 64}
    }
]

SEED = 3407

BASE_FIXTURES = {
    'fixture/settings.py': '''DEFAULTS = {"tool_timeout_seconds": 30, "retries": 2}\n\ndef load_settings(env):\n    return {**DEFAULTS, "tool_timeout_seconds": int(env.get("TOOL_TIMEOUT_SECONDS", DEFAULTS["tool_timeout_seconds"]))}\n''',
    'fixture/settings.pyi': '''from typing import Mapping\n\ndef load_settings(env: Mapping[str, str]) -> dict[str, int]: ...\n''',
    'fixture/README.md': '''# Fixture settings\n\nThe `tool_timeout_seconds` setting controls the maximum wait for a tool.\n\nEnvironment: `TOOL_TIMEOUT_SECONDS`.\n''',
    'fixture/config.json': '''{"tool_timeout_seconds": 30, "retries": 2}\n''',
    'fixture/test_settings.py': '''from settings import load_settings\n\ndef test_default_timeout():\n    assert load_settings({"tool_timeout_seconds": "99"})["tool_timeout_seconds"] == 30\n\ndef test_environment_timeout():\n    assert load_settings({"TOOL_TIMEOUT_SECONDS": "7"})["tool_timeout_seconds"] == 7\n''',
    
    'fixture/retry.py': '''def retry_call(fn, retry_on=(Exception,), attempts=3):\n    last = None\n    for _ in range(attempts + 1):\n        try:\n            return fn()\n        except retry_on as exc:\n            last = exc\n    raise last\n''',
    'fixture/test_retry.py': '''import pytest\nfrom retry import retry_call\n\ndef test_retries_only_selected_exception_and_attempt_count():\n    calls = []\n    def work():\n        calls.append(1)\n        raise ValueError("retry")\n    with pytest.raises(ValueError):\n        retry_call(work, retry_on=(ValueError,), attempts=3)\n    assert len(calls) == 3\n\ndef test_unselected_exception_is_not_retried():\n    calls = []\n    def work():\n        calls.append(1)\n        raise TypeError("stop")\n    with pytest.raises(TypeError):\n        retry_call(work, retry_on=(ValueError,), attempts=3)\n    assert len(calls) == 1\n''',
    
    'fixture/ratelimit.py': '''import time\n\nclass TokenBucket:\n    def __init__(self, capacity: int, fill_rate: float):\n        self.capacity = capacity\n        self.fill_rate = fill_rate\n        self.tokens = capacity\n        self.last_update = time.time()\n\n    def consume(self, amount: int = 1) -> bool:\n        now = time.time()\n        delta = now - self.last_update\n        self.last_update = now\n        self.tokens = min(self.capacity, self.tokens + delta * self.fill_rate)\n        if self.tokens >= amount:\n            self.tokens += amount  # BUG: should subtract amount\n            return True\n        return False\n''',
    'fixture/test_ratelimit.py': '''from ratelimit import TokenBucket\n\ndef test_token_bucket_consume():\n    bucket = TokenBucket(capacity=10, fill_rate=0.0)\n    assert bucket.consume(3) is True\n    assert bucket.tokens == 7\n    assert bucket.consume(8) is False\n''',

    'fixture/cache.py': '''class LRUCache:\n    def __init__(self, max_items: int = 3):\n        self.max_items = max_items\n        self.items = {}\n\n    def get(self, key):\n        if key not in self.items:\n            return None\n        val = self.items.pop(key)\n        self.items[key] = val\n        return val\n\n    def set(self, key, val):\n        if key in self.items:\n            self.items.pop(key)\n        elif len(self.items) >= self.max_items:\n            first_key = list(self.items.keys())[0]\n            del self.items[first_key]\n        self.items[key] = val\n''',
    'fixture/test_cache.py': '''from cache import LRUCache\n\ndef test_cache_eviction():\n    c = LRUCache(2)\n    c.set("a", 1)\n    c.set("b", 2)\n    assert c.get("a") == 1\n    c.set("c", 3)\n    assert c.get("b") is None\n    assert c.get("a") == 1\n    assert c.get("c") == 3\n''',

    'fixture/router.py': '''class EndpointRouter:\n    def __init__(self):\n        self.routes = {}\n    def register(self, path: str, handler):\n        self.routes[path] = handler\n    def resolve(self, path: str):\n        return self.routes.get(path)\n''',
    'fixture/test_router.py': '''from router import EndpointRouter\n\ndef test_router():\n    r = EndpointRouter()\n    r.register("/health", lambda: "ok")\n    assert r.resolve("/health")() == "ok"\n    assert r.resolve("/missing") is None\n'''
}

TASKS = [
    {
        'id': 'task01_nav_role_chain',
        'type': 'navigation',
        'instruction': 'Determine how a request for the `project-rw` role is routed from top-level model bindings to its agent instructions and its effective contract specification. Inspect repository files and emit `done` with the chain of paths.',
        'eval_type': 'oracle_strings',
        'expected': ['model-bindings.yaml', 'project-rw', 'instructions.md']
    },
    {
        'id': 'task02_fix_retry_loop',
        'type': 'bugfix_small',
        'instruction': 'Fix the bug in `fixture/retry.py`: `retry_call` runs one attempt too many and does not properly respect attempt bounds. Run `pytest fixture/test_retry.py` and emit `done` when all tests pass.',
        'eval_type': 'pytest',
        'test_target': 'fixture/test_retry.py'
    },
    {
        'id': 'task03_fix_ratelimit_math',
        'type': 'bugfix_hard',
        'instruction': 'Fix the logic bug in `fixture/ratelimit.py` where consuming tokens adds to the bucket instead of deducting. Run `pytest fixture/test_ratelimit.py` and emit `done` when all tests pass.',
        'eval_type': 'pytest',
        'test_target': 'fixture/test_ratelimit.py'
    },
    {
        'id': 'task04_multifile_timeout_rename',
        'type': 'multifile',
        'instruction': 'Rename `tool_timeout_seconds` to `tool_timeout_s` across all files in `fixture/` (code, stubs, tests, docs, config). Run `pytest fixture/test_settings.py` and emit `done`.',
        'eval_type': 'multifile_check',
        'test_target': 'fixture/test_settings.py',
        'old_key': 'tool_timeout_seconds',
        'new_key': 'tool_timeout_s'
    },
    {
        'id': 'task05_recovery_missing_path',
        'type': 'recovery',
        'instruction': 'Read `fixture/non_existent_config.py`, handle the error, find the real settings file in `fixture/`, verify default timeout is 30, and emit `done` with the confirmed value.',
        'eval_type': 'oracle_strings',
        'expected': ['30']
    },
    {
        'id': 'task06_feature_router_prefix',
        'type': 'feature',
        'instruction': 'In `fixture/router.py`, add support for a method `register_prefix(prefix, handler)` that routes any path starting with `prefix`. Update `fixture/test_router.py` to test it, run `pytest fixture/test_router.py`, and emit `done`.',
        'eval_type': 'pytest',
        'test_target': 'fixture/test_router.py'
    }
]

TOOLS_DESCRIPTION = '''Available tools. Emit exactly one JSON object per turn, with no markdown formatting:
{"action":"list","path":"."}
{"action":"search","query":"literal or regex","path":"."}
{"action":"read","path":"relative/path","start":1,"end":200}
{"action":"edit","path":"relative/path","old":"exact old string","new":"new replacement string"}
{"action":"patch","diff":"unified diff text"}
{"action":"run","command":"safe shell command"}
{"action":"done","answer":"final answer"}
Rules: Use relative paths. Run tests after editing. When finished, emit done.\n'''


def sample_vram():
    try:
        res = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
        used, total = res.stdout.strip().split(',')[:2]
        return int(used.strip()), int(total.strip())
    except Exception:
        return 0, 0


def safe_path(worktree: Path, rel_path: str) -> Path:
    p = (worktree / rel_path).resolve()
    w = worktree.resolve()
    if p != w and w not in p.parents:
        raise ValueError(f"Path outside worktree: {rel_path}")
    return p


def apply_patch(worktree: Path, diff: str):
    res = subprocess.run(['git', 'apply', '--whitespace=nowarn', '-'], cwd=worktree, input=diff, text=True, capture_output=True, timeout=30)
    return res.returncode, res.stdout + res.stderr


def tool_call(worktree: Path, action: dict) -> dict:
    name = action.get('action')
    try:
        if name == 'list':
            path = safe_path(worktree, action.get('path', '.'))
            entries = []
            if path.exists() and path.is_dir():
                for item in sorted(path.iterdir()):
                    if item.name.startswith('.git'):
                        continue
                    entries.append({'name': str(item.relative_to(worktree)), 'type': 'dir' if item.is_dir() else 'file'})
            return {'ok': True, 'entries': entries[:500]}

        elif name == 'search':
            query = action.get('query', '')
            path = safe_path(worktree, action.get('path', '.'))
            res = subprocess.run(['rg', '-n', '--hidden', '--glob', '!.git', query, str(path)], cwd=worktree, text=True, capture_output=True, timeout=60)
            return {'ok': True, 'matches': res.stdout[-30000:], 'exit_code': res.returncode}

        elif name == 'read':
            path = safe_path(worktree, action['path'])
            if not path.exists():
                return {'ok': False, 'error': f"File not found: {action['path']}"}
            lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
            start = max(1, int(action.get('start', 1)))
            end = min(len(lines), int(action.get('end', start + 199)))
            content = '\n'.join(f'{n}: {lines[n-1]}' for n in range(start, end + 1))
            return {'ok': True, 'path': action['path'], 'start': start, 'end': end, 'content': content}

        elif name == 'edit':
            path = safe_path(worktree, action['path'])
            if not path.exists():
                return {'ok': False, 'error': f"File not found: {action['path']}"}
            content = path.read_text(encoding='utf-8', errors='replace')
            old_str = action.get('old', '')
            new_str = action.get('new', '')
            if not old_str:
                return {'ok': False, 'error': "Missing 'old' field in edit"}
            if old_str not in content:
                return {'ok': False, 'error': f"Target string 'old' not found in {action['path']}"}
            new_content = content.replace(old_str, new_str, 1)
            path.write_text(new_content, encoding='utf-8')
            return {'ok': True, 'path': action['path'], 'message': 'Successfully edited file'}

        elif name == 'patch':
            code, output = apply_patch(worktree, action.get('diff', ''))
            return {'ok': code == 0, 'output': output, 'patch_exit_code': code}

        elif name == 'run':
            command = action.get('command', '')
            forbidden = re.search(r'(^|[;&|])\s*(rm|git\s+(reset|checkout|clean)|curl|wget|ssh)\b|\.\./', command)
            if forbidden:
                return {'ok': False, 'error': 'Command rejected by harness security policy'}
            env = os.environ.copy()
            if PYTEST_BIN.exists():
                env['PATH'] = f"{PYTEST_BIN.parent}:{env.get('PATH', '')}"
            res = subprocess.run(command, cwd=worktree, env=env, shell=True, text=True, capture_output=True, timeout=120)
            return {'ok': res.returncode == 0, 'exit_code': res.returncode, 'stdout': res.stdout[-20000:], 'stderr': res.stderr[-20000:]}

        elif name == 'done':
            return {'ok': True, 'done': True, 'answer': action.get('answer', '')}

        return {'ok': False, 'error': f'Unknown action: {name}'}
    except Exception as exc:
        return {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}


def _request_json_worker(conn, url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=400) as response:
            conn.send({'ok': True, 'response': json.loads(response.read().decode())})
    except Exception as exc:
        conn.send({'ok': False, 'error': f'{type(exc).__name__}: {exc}'})
    finally:
        conn.close()


def request_json(url, payload, timeout=360):
    parent, child = multiprocessing.Pipe(duplex=False)
    worker = multiprocessing.Process(target=_request_json_worker, args=(child, url, payload))
    worker.start()
    child.close()
    deadline = time.monotonic() + max(0.01, timeout)
    res = None
    while worker.is_alive() and time.monotonic() < deadline:
        if parent.poll(0.05):
            res = parent.recv()
            worker.join(5)
            break
    if res is None and worker.is_alive():
        worker.terminate()
        worker.join(5)
        parent.close()
        raise TimeoutError(f'Request exceeded timeout ({timeout:.2f}s)')
    try:
        if res is None and not parent.poll():
            raise RuntimeError(f'Worker exited with code {worker.exitcode}')
        if res is None:
            res = parent.recv()
    finally:
        parent.close()
    if not res['ok']:
        raise urllib.error.URLError(res['error'])
    return res['response']


def start_server_for_profile(profile: dict, log_path: Path):
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = f"{profile['runtime_libs']}:{env.get('LD_LIBRARY_PATH', '')}"
    cmd = [str(profile['runtime_bin'])] + profile['server_args']
    log_file = log_path.open('w', encoding='utf-8')
    process = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    return process, log_file


def wait_for_server(port=PORT, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1) as resp:
                data = json.loads(resp.read().decode())
                if data.get('status') == 'ok':
                    return True
        except Exception:
            time.sleep(1)
    return False


def stop_server(process, log_file):
    if process:
        try:
            process.terminate()
            process.wait(timeout=10)
        except Exception:
            process.kill()
            process.wait()
    if log_file and not log_file.closed:
        log_file.close()
    subprocess.run(['pkill', '-9', '-f', 'llama-server'], capture_output=True)
    time.sleep(2)


def setup_clean_worktree(worktree_dir: Path):
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir)
    worktree_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'clone', '--depth', '1', f'file://{SOURCE_REPO}', str(worktree_dir)], capture_output=True, check=True)
    for rel_path, content in BASE_FIXTURES.items():
        p = worktree_dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')


def run_agent_task(profile: dict, task_def: dict, seed: int, worktree: Path, output_dir: Path) -> dict:
    prompt = f"You are a precise repository-worker agent. Complete the assigned task below.\n\n# {task_def['id']}\n{task_def['instruction']}\n\n{TOOLS_DESCRIPTION}\nEmit exactly one valid JSON action per turn. Begin by exploring context or reading files."

    messages = [
        {'role': 'system', 'content': 'You are a precise repository-worker agent. Follow the tool protocol strictly. Output ONLY a valid JSON object per turn.'},
        {'role': 'user', 'content': prompt}
    ]

    events = []
    final_answer = ''
    files_read = set()
    files_edited = set()
    successful_edits = 0
    failed_edits = 0
    patch_attempts = 0
    tool_errors = 0
    test_commands = []
    test_results = []
    recovered_errors = 0
    last_action_error = False

    t_start = time.perf_counter()
    time_to_first_useful = None
    time_to_first_edit = None
    peak_vram = 0

    total_prompt_tokens = 0
    total_reasoning_tokens = 0
    total_output_tokens = 0

    url = f'http://127.0.0.1:{PORT}/v1/chat/completions'
    max_turns = 40
    task_timeout = 360

    for turn in range(1, max_turns + 1):
        elapsed = time.perf_counter() - t_start
        if elapsed > task_timeout:
            events.append({'turn': turn, 'type': 'timeout', 'elapsed': elapsed})
            break

        vram_used, _ = sample_vram()
        if vram_used > peak_vram:
            peak_vram = vram_used

        sampling_params = dict(profile['sampling'])
        sampling_params['seed'] = seed
        sampling_params['max_tokens'] = 1536 if profile['context'] >= 8192 else 512

        payload = {
            'model': profile['id'],
            'messages': messages,
            **sampling_params
        }

        try:
            resp = request_json(url, payload, timeout=min(120, task_timeout - elapsed))
        except Exception as exc:
            events.append({'turn': turn, 'type': 'request_error', 'error': str(exc)})
            tool_errors += 1
            break

        choice = resp['choices'][0]
        message = choice['message']
        content = message.get('content', '') or ''
        reasoning = message.get('reasoning_content', '') or ''
        usage = resp.get('usage', {})

        total_prompt_tokens += usage.get('prompt_tokens', 0)
        total_output_tokens += usage.get('completion_tokens', 0)
        if usage.get('completion_tokens_details', {}).get('reasoning_tokens'):
            total_reasoning_tokens += usage['completion_tokens_details']['reasoning_tokens']

        # Parse action from content
        action = None
        clean_text = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        clean_text = re.sub(r'^```json\s*', '', clean_text)
        clean_text = re.sub(r'\s*```$', '', clean_text)

        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            try:
                action = json.loads(match.group(0))
            except Exception:
                pass

        turn_record = {
            'turn': turn,
            'content': content,
            'reasoning': reasoning,
            'action': action,
            'finish_reason': choice.get('finish_reason')
        }

        if not action or 'action' not in action:
            turn_record['tool_res'] = {'ok': False, 'error': 'Invalid JSON format or missing action property'}
            tool_errors += 1
            last_action_error = True
            messages.append({'role': 'assistant', 'content': content})
            messages.append({'role': 'user', 'content': 'Error: Output must be a valid JSON tool call object. Try again.'})
            events.append(turn_record)
            continue

        act_name = action['action']

        if time_to_first_useful is None and act_name in ['list', 'search', 'read']:
            time_to_first_useful = time.perf_counter() - t_start

        if act_name == 'read' and 'path' in action:
            files_read.add(action['path'])
        elif act_name == 'edit' and 'path' in action:
            files_edited.add(action['path'])
            if time_to_first_edit is None:
                time_to_first_edit = time.perf_counter() - t_start
        elif act_name == 'patch':
            patch_attempts += 1
            if time_to_first_edit is None:
                time_to_first_edit = time.perf_counter() - t_start

        res = tool_call(worktree, action)
        turn_record['tool_res'] = res

        if res.get('ok'):
            if last_action_error:
                recovered_errors += 1
                last_action_error = False
            if act_name == 'edit':
                successful_edits += 1
            elif act_name == 'patch':
                successful_edits += 1
        else:
            tool_errors += 1
            last_action_error = True
            if act_name in ['edit', 'patch']:
                failed_edits += 1

        if act_name == 'run':
            test_commands.append(action.get('command', ''))
            test_results.append(res.get('ok', False))

        events.append(turn_record)

        if act_name == 'done':
            final_answer = action.get('answer', '')
            break

        messages.append({'role': 'assistant', 'content': content})
        messages.append({'role': 'user', 'content': f"Tool Result: {json.dumps(res)}"})

    t_total = time.perf_counter() - t_start

    # Evaluate task success
    passed = False
    eval_detail = {}
    eval_type = task_def.get('eval_type')

    if eval_type == 'oracle_strings':
        expected = task_def.get('expected', [])
        ans = (final_answer + ' ' + ' '.join(e.get('content', '') for e in events)).lower()
        passed = all(exp.lower() in ans for exp in expected)
        eval_detail = {'type': 'oracle_strings', 'expected': expected, 'found': passed}

    elif eval_type in ['pytest', 'bugfix_small', 'bugfix_hard', 'feature']:
        target = task_def.get('test_target', '')
        env = os.environ.copy()
        if PYTEST_BIN.exists():
            env['PATH'] = f"{PYTEST_BIN.parent}:{env.get('PATH', '')}"
        p = subprocess.run(['pytest', target], cwd=worktree, env=env, capture_output=True, text=True, timeout=60)
        passed = (p.returncode == 0)
        eval_detail = {'type': 'pytest', 'target': target, 'exit_code': p.returncode, 'stdout': p.stdout[-2000:], 'stderr': p.stderr[-2000:]}

    elif eval_type == 'multifile_check':
        target = task_def.get('test_target', '')
        env = os.environ.copy()
        if PYTEST_BIN.exists():
            env['PATH'] = f"{PYTEST_BIN.parent}:{env.get('PATH', '')}"
        p = subprocess.run(['pytest', target], cwd=worktree, env=env, capture_output=True, text=True, timeout=60)
        
        # Check files for old string
        old_found = False
        for f in (worktree / 'fixture').rglob('*'):
            if f.is_file() and not f.name.endswith('.pyc') and '__pycache__' not in str(f):
                txt = f.read_text(encoding='utf-8', errors='replace')
                if task_def['old_key'] in txt:
                    old_found = True
                    break
        passed = (p.returncode == 0) and not old_found
        eval_detail = {'type': 'multifile_check', 'pytest_passed': p.returncode == 0, 'old_key_absent': not old_found}

    return {
        'task_id': task_def['id'],
        'profile_id': profile['id'],
        'seed': seed,
        'passed': passed,
        'total_time_s': t_total,
        'time_to_first_useful_s': time_to_first_useful,
        'time_to_first_edit_s': time_to_first_edit,
        'peak_vram_mib': peak_vram,
        'total_turns': len(events),
        'tool_errors': tool_errors,
        'recovered_errors': recovered_errors,
        'files_read': list(files_read),
        'files_edited': list(files_edited),
        'successful_edits': successful_edits,
        'failed_edits': failed_edits,
        'prompt_tokens': total_prompt_tokens,
        'reasoning_tokens': total_reasoning_tokens,
        'output_tokens': total_output_tokens,
        'eval_detail': eval_detail,
        'events': events
    }


def parse_server_log_for_tps(log_path: Path):
    if not log_path.exists():
        return {'decode_tps': 0.0, 'prompt_tps': 0.0}
    
    text = log_path.read_text(encoding='utf-8', errors='replace')
    prompt_tps_list = [float(m) for m in re.findall(r'prompt eval time.*?\(\s*([\d\.]+)\s*tokens per second\)', text)]
    eval_tps_list = [float(m) for m in re.findall(r'\beval time.*?\(\s*([\d\.]+)\s*tokens per second\)', text)]

    avg_prompt = sum(prompt_tps_list) / len(prompt_tps_list) if prompt_tps_list else 0.0
    avg_decode = sum(eval_tps_list) / len(eval_tps_list) if eval_tps_list else 0.0

    return {'decode_tps': avg_decode, 'prompt_tps': avg_prompt}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profiles', nargs='*', help='Specific profiles to run')
    args = parser.parse_args()

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    WORK_ROOT.mkdir(parents=True, exist_ok=True)

    profiles_to_run = PROFILES
    if args.profiles:
        profiles_to_run = [p for p in PROFILES if p['id'] in args.profiles or p['key'] in args.profiles]

    print(f"=== REPO-WORKER SHORT FINAL BENCHMARK ({len(profiles_to_run)} PROFILES x {len(TASKS)} TASKS) ===")

    all_results = {}

    for profile in profiles_to_run:
        p_id = profile['id']
        p_dir = BENCHMARK_DIR / 'profiles' / p_id
        p_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = p_dir / 'tasks_server.log'

        print(f"\n=======================================================")
        print(f"STARTING PROFILE: {profile['name']} ({p_id})")
        print(f"=======================================================")

        proc, log_f = start_server_for_profile(profile, log_file_path)
        if not wait_for_server(PORT, timeout=120):
            print(f"FAILED TO START SERVER FOR {p_id}")
            stop_server(proc, log_f)
            continue

        profile_task_results = []

        for task in TASKS:
            t_id = task['id']
            res_file = p_dir / f"{t_id}.json"
            if res_file.exists():
                print(f"  [{p_id}] {t_id}: ALREADY COMPLETED (Skipping)")
                with open(res_file, 'r', encoding='utf-8') as f:
                    profile_task_results.append(json.load(f))
                continue

            print(f"  [{p_id}] Running {t_id} (Seed {SEED})...", flush=True)
            wt_dir = WORK_ROOT / f"{p_id}_{t_id}"
            setup_clean_worktree(wt_dir)

            res = run_agent_task(profile, task, SEED, wt_dir, p_dir)
            with open(res_file, 'w', encoding='utf-8') as f:
                json.dump(res, f, indent=2)

            status = "PASS" if res['passed'] else "FAIL"
            print(f"  [{p_id}] {t_id} -> {status} in {res['total_time_s']:.1f}s (Turns: {res['total_turns']}, Edits: {res['successful_edits']}, Errors: {res['tool_errors']})")
            profile_task_results.append(res)

        stop_server(proc, log_f)

        tps = parse_server_log_for_tps(log_file_path)
        all_results[p_id] = {
            'profile': profile,
            'tasks': profile_task_results,
            'server_tps': tps
        }

    # Save summary results
    summary_path = BENCHMARK_DIR / 'RESULTS.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, default=str)

    print("\nBenchmark completed successfully!")


if __name__ == '__main__':
    main()
