#!/usr/bin/env python3
import argparse
import difflib
import hashlib
import json
import multiprocessing
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path('/home/alpha/Playstoria/models')
SOURCE_REPO = Path('/home/alpha/Playstoria/holo-agent-tooling')
BENCHMARK = ROOT / 'benchmarks/repo-worker-mini-v1'
WORK_ROOT = Path('/tmp/repo-worker-mini-v1-worktrees')
PORTS = {'bonsai': 8121, 'ornith-1.5-9b-q5': 8122}
MAX_TOOL_CALLS = 20
MAX_GENERATED_TOKENS = 12000
MAX_TOKENS_PER_TURN = 1024
TASK_TIMEOUT_SECONDS = 180

BONSAI = ROOT / 'text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf'
ORNITH = ROOT / 'text/bartowski-Ornith-1.5-9B-Q5_K_M/Ornith-1.5-9B-Q5_K_M.gguf'
PRISM = ROOT / 'engines/prism-llama/llama-prism-b9599-9ca265a/llama-server'
MAINLINE = ROOT / 'engines/deepgrove-llama.cpp/build/bin/llama-server'
CUDA_LIBS = Path('/home/alpha/.lmstudio/extensions/backends/vendor/linux-llama-cuda12-vendor-v1')
PRISM_LIBS = PRISM.parent

FIXTURE = {
    'fixture/settings.py': '''DEFAULTS = {"tool_timeout_seconds": 30, "retries": 2}\n\n\ndef load_settings(env):\n    return {**DEFAULTS, "tool_timeout_seconds": int(env.get("TOOL_TIMEOUT_SECONDS", DEFAULTS["tool_timeout_seconds"]))}\n''',
    'fixture/settings.pyi': '''from typing import Mapping\n\ndef load_settings(env: Mapping[str, str]) -> dict[str, int]: ...\n''',
    'fixture/README.md': '''# Fixture settings\n\nThe `tool_timeout_seconds` setting controls the maximum wait for a tool.\n\nEnvironment: `TOOL_TIMEOUT_SECONDS`.\n''',
    'fixture/config.json': '''{"tool_timeout_seconds": 30, "retries": 2}\n''',
    'fixture/test_settings.py': '''from settings import load_settings\n\n\ndef test_default_timeout():\n    assert load_settings({"tool_timeout_seconds": "99"})["tool_timeout_seconds"] == 30\n\n\ndef test_environment_timeout():\n    assert load_settings({"TOOL_TIMEOUT_SECONDS": "7"})["tool_timeout_seconds"] == 7\n''',
    'fixture/retry.py': '''def retry_call(fn, retry_on=(Exception,), attempts=3):\n    last = None\n    for _ in range(attempts + 1):\n        try:\n            return fn()\n        except retry_on as exc:\n            last = exc\n    raise last\n''',
    'fixture/test_retry.py': '''import pytest\nfrom retry import retry_call\n\n\ndef test_retries_only_selected_exception_and_attempt_count():\n    calls = []\n    def work():\n        calls.append(1)\n        raise ValueError("retry")\n    with pytest.raises(ValueError):\n        retry_call(work, retry_on=(ValueError,), attempts=3)\n    assert len(calls) == 3\n\n\ndef test_unselected_exception_is_not_retried():\n    calls = []\n    def work():\n        calls.append(1)\n        raise TypeError("stop")\n    with pytest.raises(TypeError):\n        retry_call(work, retry_on=(ValueError,), attempts=3)\n    assert len(calls) == 1\n''',
    'fixture/loader.py': '''from dataclasses import dataclass\n\n\n@dataclass\nclass Settings:\n    retries: int = 2\n\n\ndef load(env: dict[str, str]) -> Settings:\n    return Settings(retries=int(env.get("HOLO_RETRIES", "2")))\n''',
    'fixture/loader.pyi': '''from typing import Mapping\nfrom loader import Settings\n\ndef load(env: Mapping[str, str]) -> Settings: ...\n''',
    'fixture/test_loader.py': '''from loader import load\n\n\ndef test_default_and_env_retries():\n    assert load({}).retries == 2\n    assert load({"HOLO_RETRIES": "5"}).retries == 5\n''',
    'fixture/loader.md': '''# Loader\n\n`load` reads `HOLO_RETRIES` and otherwise uses the default of 2.\n''',
}

TASK_EXPECTATIONS = {
    'task01': ['library/routing/model-bindings.yaml', 'project-rw', 'library/agents/project-rw/instructions.md', 'core/agents/contracts/project-rw.yaml'],
    'task02': ['tool_timeout_s'],
    'task03': ['fixture/retry.py'],
    'task04': ['reasoning_budget', 'HOLO_REASONING_BUDGET'],
    'task05': ['project-ro', 'project-rw', 'explore', 'browser'],
}

TOOLS = '''Available tools. Emit exactly one JSON object per turn, with no Markdown.
{"action":"list","path":"."}
{"action":"search","query":"literal or regex","path":"."}
{"action":"read","path":"relative/path","start":1,"end":200}
{"action":"patch","diff":"unified diff text"}
{"action":"run","command":"safe shell command"}
{"action":"done","answer":"final concise answer"}
Rules: use relative paths; no network, destructive commands, git reset/checkout, or access outside the worktree. For patch, provide a standard unified diff. You must use tools to discover context. For edit tasks, run tests after editing and repair failures. Do not claim a tool call you did not make.\n'''


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def size(path):
    return path.stat().st_size


def run(cmd, cwd=None, env=None, timeout=120, check=False):
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout, check=check)


def safe_path(worktree, value):
    path = (worktree / value).resolve()
    if path != worktree.resolve() and worktree.resolve() not in path.parents:
        raise ValueError('path outside worktree')
    return path


def materialize_fixture(worktree):
    for relative, content in FIXTURE.items():
        path = worktree / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')


def fixture_diff(worktree):
    chunks = []
    changed_files = []
    for relative, original in FIXTURE.items():
        path = worktree / relative
        current = path.read_text(encoding='utf-8') if path.exists() else ''
        if current == original:
            continue
        changed_files.append(relative)
        chunks.extend(difflib.unified_diff(
            original.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile=f'a/{relative}',
            tofile=f'b/{relative}',
            lineterm='',
        ))
    return ''.join(chunks), changed_files


def apply_patch(worktree, diff):
    result = subprocess.run(['git', 'apply', '--whitespace=nowarn', '-'], cwd=worktree, input=diff, text=True, capture_output=True, timeout=60)
    return result.returncode, result.stdout + result.stderr


def tool_call(worktree, action):
    name = action.get('action')
    try:
        if name == 'list':
            path = safe_path(worktree, action.get('path', '.'))
            entries = []
            for item in sorted(path.iterdir()):
                entries.append({'name': str(item.relative_to(worktree)), 'type': 'dir' if item.is_dir() else 'file'})
            return {'ok': True, 'entries': entries[:500]}
        if name == 'search':
            query = action.get('query', '')
            path = safe_path(worktree, action.get('path', '.'))
            result = subprocess.run(['rg', '-n', '--hidden', '--glob', '!.git', query, str(path)], cwd=worktree, text=True, capture_output=True, timeout=60)
            return {'ok': True, 'matches': result.stdout[-30000:], 'exit_code': result.returncode}
        if name == 'read':
            path = safe_path(worktree, action['path'])
            lines = path.read_text(encoding='utf-8').splitlines()
            start = max(1, int(action.get('start', 1)))
            end = min(len(lines), int(action.get('end', start + 199)))
            return {'ok': True, 'path': action['path'], 'start': start, 'end': end, 'content': '\n'.join(f'{n}: {lines[n-1]}' for n in range(start, end + 1))}
        if name == 'patch':
            code, output = apply_patch(worktree, action['diff'])
            return {'ok': code == 0, 'output': output, 'patch_exit_code': code}
        if name == 'run':
            command = action.get('command', '')
            forbidden = re.search(r'(^|[;&|])\s*(rm|git\s+(reset|checkout|clean)|curl|wget|ssh)\b|\.\./', command)
            if forbidden:
                return {'ok': False, 'error': 'command rejected by harness policy'}
            result = subprocess.run(command, cwd=worktree, shell=True, text=True, capture_output=True, timeout=180)
            return {'ok': result.returncode == 0, 'exit_code': result.returncode, 'stdout': result.stdout[-20000:], 'stderr': result.stderr[-20000:]}
        if name == 'done':
            return {'ok': True, 'done': True, 'answer': action.get('answer', '')}
        return {'ok': False, 'error': f'unknown action: {name}'}
    except Exception as exc:
        return {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}


def _request_json_worker(connection, url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=900) as response:
            connection.send({'ok': True, 'response': json.loads(response.read().decode())})
    except Exception as exc:
        connection.send({'ok': False, 'error': f'{type(exc).__name__}: {exc}'})
    finally:
        connection.close()


def request_json(url, payload, timeout=900):
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
        raise TimeoutError(f'request exceeded {timeout:.2f}s')
    try:
        if result is None and not parent.poll():
            raise RuntimeError(f'request worker exited with code {worker.exitcode}')
        if result is None:
            result = parent.recv()
    finally:
        parent.close()
    if not result['ok']:
        raise urllib.error.URLError(result['error'])
    return result['response']


def wait_server(port, timeout=240):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2) as response:
                if json.loads(response.read().decode()).get('status') == 'ok':
                    return True
        except Exception:
            time.sleep(1)
    return False


def model_config(model):
    if model == 'bonsai':
        return {'model_path': BONSAI, 'runtime': PRISM, 'runtime_name': 'PrismML llama.cpp', 'reasoning': 'off', 'lib_path': f'{CUDA_LIBS}:{PRISM_LIBS}'}
    return {'model_path': ORNITH, 'runtime': MAINLINE, 'runtime_name': 'deepgrove llama.cpp', 'reasoning': 'auto', 'lib_path': str(MAINLINE.parent)}


def start_server(model, port, log_path):
    cfg = model_config(model)
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = f"{cfg['lib_path']}:{env.get('LD_LIBRARY_PATH', '')}"
    command = [str(cfg['runtime']), '-m', str(cfg['model_path']), '--host', '127.0.0.1', '--port', str(port), '-c', '32768', '-np', '1', '-ngl', 'auto', '-fit', 'on', '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q4_0', '-t', '4', '-tb', '4', '--no-webui']
    if model == 'bonsai':
        command += ['--reasoning', 'off']
    log = log_path.open('w', encoding='utf-8')
    process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    return process, log, cfg, command


def usage_tokens(response):
    usage = response.get('usage') or {}
    return int(usage.get('completion_tokens') or 0), int(usage.get('prompt_tokens') or 0)


def prompt_for(task_id):
    task_text = (BENCHMARK / 'tasks' / f'{task_id}.md').read_text(encoding='utf-8')
    return f'''You are a repository worker. Work only on the assigned task below.\n\n{task_text}\n\n{TOOLS}\nStart by choosing the smallest useful read/search/list action. When complete, emit done with a concise answer.'''


def objective_result(task_id, worktree, answer, tool_events, initial_files):
    text = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
    checks = TASK_EXPECTATIONS[task_id]
    facts = {item: item in text for item in checks}
    tests = None
    if task_id == 'task02':
        all_files = list((worktree / 'fixture').rglob('*'))
        contents = '\n'.join(p.read_text(encoding='utf-8') for p in all_files if p.is_file())
        expected_files = [path for path, content in FIXTURE.items() if 'tool_timeout_seconds' in content]
        tests = {
            'old_absent': 'tool_timeout_seconds' not in contents,
            'new_present': all('tool_timeout_s' in (worktree / path).read_text(encoding='utf-8') for path in expected_files),
            'expected_files_changed': set(expected_files) == set(fixture_diff(worktree)[1]),
        }
    elif task_id == 'task03':
        result = run([sys.executable, '-m', 'pytest', '-q', 'test_retry.py'], cwd=worktree / 'fixture', timeout=180)
        tests = {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    elif task_id == 'task04':
        result = run([sys.executable, '-m', 'pytest', '-q', 'test_loader.py'], cwd=worktree / 'fixture', timeout=180)
        loader = (worktree / 'fixture/loader.py').read_text(encoding='utf-8')
        typed = (worktree / 'fixture/loader.pyi').read_text(encoding='utf-8')
        test_loader = (worktree / 'fixture/test_loader.py').read_text(encoding='utf-8')
        docs = (worktree / 'fixture/loader.md').read_text(encoding='utf-8')
        tests = {
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'loader_support': 'reasoning_budget' in loader and 'HOLO_REASONING_BUDGET' in loader,
            'typed_support': 'reasoning_budget' in typed,
            'test_coverage': 'HOLO_REASONING_BUDGET' in test_loader,
            'documentation': 'reasoning_budget' in docs and 'HOLO_REASONING_BUDGET' in docs,
            'expected_files_changed': set(['fixture/loader.py', 'fixture/loader.pyi', 'fixture/test_loader.py', 'fixture/loader.md']) == set(fixture_diff(worktree)[1]),
        }
    elif task_id in ('task01', 'task05'):
        tests = {'answer_markers': facts}
    diff, changed_files = fixture_diff(worktree)
    changed = '\n'.join(f'M  {path}' for path in changed_files)
    if task_id == 'task02':
        objective = bool(tests['old_absent'] and tests['new_present'] and tests['expected_files_changed'])
    elif task_id in ('task03', 'task04'):
        objective = bool(tests['exit_code'] == 0)
        if task_id == 'task04':
            objective = objective and all(tests[key] for key in ('loader_support', 'typed_support', 'test_coverage', 'documentation', 'expected_files_changed'))
    else:
        objective = bool(any(event.get('parsed_action', {}).get('action') == 'done' for event in tool_events) and all(facts.values()))
    return {'objective_pass': objective, 'checks': facts, 'tests': tests, 'diff': diff, 'status': changed, 'changed_files': changed_files, 'initial_files': initial_files}


def sample_vram():
    try:
        result = run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'], timeout=10)
        used, total = result.stdout.strip().split(',')[:2]
        return {'used_mib': int(used), 'total_mib': int(total)}
    except Exception:
        return None


def run_task(model, task_id, server, cfg, command, worktree, output_dir):
    system = 'You are a precise repository-worker agent. Follow the tool protocol exactly. Do not narrate outside JSON.'
    user = prompt_for(task_id)
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
    events = []
    answer = ''
    generated = 0
    prompt_tokens = 0
    completion_tokens = 0
    patch_attempts = 0
    files_read = set()
    files_changed_before = set()
    started = time.time()
    vram_peak = 0
    stop_reason = 'max_tool_calls'
    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = output_dir / f'{task_id}.transcript.json'
    transcript_path.write_text('[]', encoding='utf-8')
    for call_index in range(MAX_TOOL_CALLS):
        if generated >= MAX_GENERATED_TOKENS:
            stop_reason = 'max_generated_tokens'
            break
        if time.time() - started >= TASK_TIMEOUT_SECONDS:
            stop_reason = 'task_timeout'
            break
        vram = sample_vram()
        if vram:
            vram_peak = max(vram_peak, vram['used_mib'])
        remaining = TASK_TIMEOUT_SECONDS - (time.time() - started)
        if remaining <= 0:
            stop_reason = 'task_timeout'
            break
        try:
            response = request_json(f'http://127.0.0.1:{PORTS[model]}/v1/chat/completions', {'messages': messages, 'temperature': 0.2, 'top_p': 0.95, 'seed': 3407, 'max_tokens': MAX_TOKENS_PER_TURN, 'stream': False}, timeout=remaining)
        except (TimeoutError, urllib.error.URLError) as exc:
            stop_reason = 'generation_timeout' if isinstance(exc, TimeoutError) else 'request_error'
            events.append({'index': call_index + 1, 'request': messages[-1], 'error': f'{type(exc).__name__}: {exc}'})
            transcript_path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding='utf-8')
            break
        choice = (response.get('choices') or [{}])[0]
        message = choice.get('message') or {}
        content = message.get('content') or ''
        reasoning = message.get('reasoning_content') or ''
        ct, pt = usage_tokens(response)
        completion_tokens += ct
        prompt_tokens += pt
        generated += ct
        raw = {'index': call_index + 1, 'request': messages[-1], 'response': response}
        events.append(raw)
        transcript_path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding='utf-8')
        messages.append({'role': 'assistant', 'content': content})
        candidate = content.strip()
        match = re.search(r'\{.*\}', candidate, re.DOTALL)
        if not match:
            messages.append({'role': 'user', 'content': 'Invalid protocol. Emit exactly one JSON object using the available actions.'})
            continue
        try:
            action = json.loads(match.group(0))
        except json.JSONDecodeError:
            messages.append({'role': 'user', 'content': 'Invalid JSON. Emit exactly one valid JSON action.'})
            continue
        if action.get('action') == 'patch':
            patch_attempts += 1
        if action.get('action') == 'read':
            files_read.add(action.get('path', ''))
        result = tool_call(worktree, action)
        if action.get('action') == 'done':
            answer = action.get('answer', '')
            events[-1]['parsed_action'] = action
            events[-1]['tool_result'] = result
            break
        events[-1]['parsed_action'] = action
        events[-1]['tool_result'] = result
        messages.append({'role': 'user', 'content': 'TOOL RESULT:\n' + json.dumps(result, ensure_ascii=False)})
        if action.get('action') == 'patch' and result.get('ok') is False:
            messages.append({'role': 'user', 'content': 'The patch failed. Inspect the error, correct the diff, and retry.'})
        if generated >= MAX_GENERATED_TOKENS:
            stop_reason = 'max_generated_tokens'
            break
    else:
        stop_reason = 'max_tool_calls'
    elapsed = time.time() - started
    if not answer:
        answer = content
    if answer and any(event.get('parsed_action', {}).get('action') == 'done' for event in events):
        stop_reason = 'done'
    initial_files = sorted(p for p in FIXTURE if (worktree / p).exists())
    objective = objective_result(task_id, worktree, answer, events, initial_files)
    result = {'model': model, 'task': task_id, 'objective': objective, 'answer': answer, 'stop_reason': stop_reason, 'tool_calls': len(events), 'files_read': sorted(files_read), 'files_read_count': len(files_read), 'files_changed_count': len(objective['changed_files']), 'patch_attempts': patch_attempts, 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'generation_tokens': generated, 'seconds': round(elapsed, 2), 'generation_tok_s': round(completion_tokens / elapsed, 2) if elapsed else 0, 'prompt_processing_tok_s': None, 'peak_vram_mib': vram_peak, 'runtime': cfg['runtime_name'], 'runtime_command': command, 'config': {'context': 32768, 'concurrency': 1, 'flash_attention': True, 'kv_k': 'q8_0', 'kv_v': 'q4_0', 'threads': 4, 'batch_threads': 4, 'seed': 3407, 'temperature': 0.2, 'top_p': 0.95, 'speculative_decoding': False, 'max_tokens_per_turn': MAX_TOKENS_PER_TURN, 'max_generated_tokens_per_task': MAX_GENERATED_TOKENS}, 'browser': 'unavailable', 'transcript': events}
    (output_dir / f'{task_id}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (output_dir / f'{task_id}.transcript.json').write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding='utf-8')
    (output_dir / f'{task_id}.patch').write_text(objective['diff'], encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['bonsai', 'ornith-1.5-9b-q5', 'both'], default='both')
    parser.add_argument('--tasks', default='task01,task02,task03,task04,task05')
    args = parser.parse_args()
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    source_commit = run(['git', 'rev-parse', 'HEAD'], cwd=SOURCE_REPO).stdout.strip()
    models = ['bonsai', 'ornith-1.5-9b-q5'] if args.model == 'both' else [args.model]
    all_results = []
    for model in models:
        model_dir = BENCHMARK / model
        model_dir.mkdir(parents=True, exist_ok=True)
        log_path = model_dir / 'server.log'
        process, log, cfg, command = start_server(model, PORTS[model], log_path)
        try:
            if not wait_server(PORTS[model]):
                raise RuntimeError(f'{model} server did not become healthy')
            try:
                smoke = request_json(f'http://127.0.0.1:{PORTS[model]}/v1/chat/completions', {'messages': [{'role': 'user', 'content': 'Responda apenas: OK'}], 'temperature': 0.2, 'top_p': 0.95, 'seed': 3407, 'max_tokens': 4, 'stream': False}, timeout=30)
            except (TimeoutError, urllib.error.URLError) as exc:
                smoke = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
            (model_dir / 'smoke.json').write_text(json.dumps(smoke, ensure_ascii=False, indent=2), encoding='utf-8')
            model_meta = {'model': model, 'model_path': str(cfg['model_path']), 'model_size': size(cfg['model_path']), 'model_sha256': sha256(cfg['model_path']), 'runtime': cfg['runtime_name'], 'runtime_path': str(cfg['runtime']), 'source_commit': source_commit, 'command': command, 'smoke': smoke, 'browser': 'unavailable'}
            (model_dir / 'RUN_META.json').write_text(json.dumps(model_meta, ensure_ascii=False, indent=2), encoding='utf-8')
            for task_id in [x.strip() for x in args.tasks.split(',') if x.strip()]:
                name = f'{model}-{task_id}-{int(time.time() * 1000)}'
                worktree = WORK_ROOT / name
                subprocess.run(['git', 'worktree', 'add', '--detach', str(worktree), source_commit], cwd=SOURCE_REPO, check=True, text=True, capture_output=True, timeout=120)
                try:
                    materialize_fixture(worktree)
                    result = run_task(model, task_id, process, cfg, command, worktree, model_dir)
                    result['source_repository'] = str(SOURCE_REPO)
                    result['source_commit'] = source_commit
                    all_results.append(result)
                finally:
                    subprocess.run(['git', 'worktree', 'remove', '--force', str(worktree)], cwd=SOURCE_REPO, text=True, capture_output=True, timeout=120)
        finally:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            log.close()
    summary = {'benchmark': 'repo-worker-mini-v1', 'source_repository': str(SOURCE_REPO), 'source_commit': source_commit, 'limits': {'max_tool_calls_per_task': MAX_TOOL_CALLS, 'max_generated_tokens_per_task': MAX_GENERATED_TOKENS, 'max_tokens_per_turn': MAX_TOKENS_PER_TURN, 'task_timeout_seconds': TASK_TIMEOUT_SECONDS}, 'models': models, 'results': all_results}
    (BENCHMARK / 'RESULTS.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (BENCHMARK / 'raw' / 'complete.json').parent.mkdir(parents=True, exist_ok=True)
    (BENCHMARK / 'raw' / 'complete.json').write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'results': [{'model': r['model'], 'task': r['task'], 'pass': r['objective']['objective_pass'], 'tool_calls': r['tool_calls'], 'seconds': r['seconds']} for r in all_results]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
