#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path('/home/alpha/Playstoria/models')
BASE = ROOT / 'benchmarks/repo-worker-challenger-v2'
HERE = ROOT / 'benchmarks/repo-worker-gsq-controlled-v3'
BASE_RUNNER = BASE / 'runner/benchmark_orchestrator.py'
MODEL_DIR = ROOT / 'text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-MTP'
IQ2 = MODEL_DIR / 'Qwen3.8-27B-GSQ-RCO-IQ2_S-mtp.gguf'
IQ3 = MODEL_DIR / 'Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf'
IQ2_SHA = 'e6406238a5cc0043775cd1963b6f9e5b8707400276e38d9fde742304906b1330'
SEED = 27183
CTX = 32768
THREADS = 4
BUDGET = 256
DRAFT_N = 3
TEMP = 0.2
TOP_P = 0.95


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ensure_suite_links() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    for name in ('fixtures', 'hidden', 'evaluator'):
        dst = HERE / name
        if dst.exists() or dst.is_symlink():
            continue
        os.symlink(os.path.relpath(BASE / name, HERE), dst)


def load_base():
    spec = importlib.util.spec_from_file_location('challenger_v2_base', BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot import {BASE_RUNNER}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_runtime_features(runtime_bin: Path) -> None:
    p = subprocess.run([str(runtime_bin), '--help'], capture_output=True, text=True, timeout=30)
    text = p.stdout + p.stderr
    required = {
        '--reasoning-budget': '--reasoning-budget' in text,
        '--spec-type': '--spec-type' in text,
        'draft-mtp': 'draft-mtp' in text,
        '--spec-draft-n-max': '--spec-draft-n-max' in text,
    }
    missing = [name for name, ok in required.items() if not ok]
    if missing:
        raise SystemExit('RUNTIME_FEATURE_MISSING=' + ','.join(missing))


def profile(pid: str, name: str, path: Path, model_sha: str, reasoning: bool, mtp: bool, budget: int | None):
    return {
        'id': pid,
        'name': name,
        'model_path': path,
        'model_sha256': model_sha,
        'thinking': reasoning,
        'temperature': TEMP,
        'top_p': TOP_P,
        'mtp': mtp,
        'reasoning_budget': budget,
    }


def mtp_metrics(log_path: Path) -> dict:
    text = log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''
    rates = [float(x) for x in re.findall(r'draft acceptance rate\s*=\s*([\d.]+)', text)]
    pairs = [(int(a), int(b)) for a, b in re.findall(r'#gen tokens\s*=\s*(\d+),\s*#acc tokens\s*=\s*(\d+)', text)]
    return {
        'draft_acceptance_rate_last': rates[-1] if rates else None,
        'draft_acceptance_rate_max': max(rates) if rates else None,
        'draft_generated_tokens_max': max((a for a, _ in pairs), default=None),
        'draft_accepted_tokens_max': max((b for _, b in pairs), default=None),
    }


def main() -> int:
    ensure_suite_links()
    if not IQ2.exists() or not IQ3.exists():
        raise SystemExit('MTP models missing. Run PREPARE_MODELS.sh first.')
    iq2_sha = sha256(IQ2)
    iq3_sha = sha256(IQ3)
    if iq2_sha != IQ2_SHA:
        raise SystemExit(f'IQ2 SHA mismatch: {iq2_sha}')

    m = load_base()
    verify_runtime_features(m.RUNTIME_BIN)
    m.BENCHMARK_DIR = HERE
    m.WORK_ROOT = Path('/tmp/repo-worker-gsq-controlled-v3-worktrees')
    m.PORT = 8153
    m.SEED = SEED
    m.TASK_TIMEOUT = 480
    m.REQUEST_TIMEOUT_CEILING = 180
    m.MAX_TURNS = 40

    tasks = copy.deepcopy(m.TASKS)
    for task in tasks:
        if task['id'] == 'task07_architectural_placement':
            task['required_edits'] = ['challenge/arch/policy/access.py']
    m.TASKS = tasks

    m.PROFILES = [
        profile('iq2-off-nospec', 'GSQ IQ2_S MTP-build / reasoning OFF / MTP OFF', IQ2, iq2_sha, False, False, None),
        profile('iq2-off-mtp', 'GSQ IQ2_S MTP-build / reasoning OFF / MTP ON', IQ2, iq2_sha, False, True, None),
        profile('iq2-budget256-mtp', 'GSQ IQ2_S MTP-build / reasoning budget 256 / MTP ON', IQ2, iq2_sha, True, True, BUDGET),
        profile('iq3-off-nospec', 'GSQ IQ3_XXS MTP-build / reasoning OFF / MTP OFF', IQ3, iq3_sha, False, False, None),
        profile('iq3-off-mtp', 'GSQ IQ3_XXS MTP-build / reasoning OFF / MTP ON', IQ3, iq3_sha, False, True, None),
        profile('iq3-budget256-mtp', 'GSQ IQ3_XXS MTP-build / reasoning budget 256 / MTP ON', IQ3, iq3_sha, True, True, BUDGET),
    ]

    original_eval = m.evaluate_task
    def fixed_eval(task, *args, **kwargs):
        if task.get('id') == 'task07_architectural_placement':
            task = copy.deepcopy(task)
            task['required_edits'] = ['challenge/arch/policy/access.py']
        return original_eval(task, *args, **kwargs)
    m.evaluate_task = fixed_eval

    def server_args(p):
        args = [
            '-m', str(p['model_path']), '--host', '127.0.0.1', '--port', str(m.PORT),
            '-c', str(CTX), '-np', '1', '-ngl', '999', '-fa', 'on',
            '-ctk', 'q4_0', '-ctv', 'q4_0', '-t', str(THREADS), '-tb', str(THREADS),
            '--no-webui', '--reasoning', 'on' if p['thinking'] else 'off',
        ]
        if p.get('reasoning_budget') is not None:
            args += ['--reasoning-budget', str(p['reasoning_budget'])]
        if p.get('mtp'):
            args += ['--spec-type', 'draft-mtp', '--spec-draft-n-max', str(DRAFT_N)]
        return args
    m.profile_server_args = server_args

    for p in m.PROFILES:
        p['temperature'] = TEMP
        p['top_p'] = TOP_P

    rc = m.main()

    metrics = {}
    for p in m.PROFILES:
        metrics[p['id']] = mtp_metrics(HERE / 'profiles' / p['id'] / 'tasks_server.log')
    (HERE / 'MTP_METRICS.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    manifest = {
        'seed': SEED, 'ctx': CTX, 'threads': THREADS, 'cache_k': 'q4_0', 'cache_v': 'q4_0',
        'temperature': TEMP, 'top_p': TOP_P, 'reasoning_budget': BUDGET,
        'spec_type': 'draft-mtp', 'spec_draft_n_max': DRAFT_N,
        'iq2_sha256': iq2_sha, 'iq3_sha256': iq3_sha,
        't7_fix': 'service edit no longer required; policy placement remains mandatory',
    }
    (HERE / 'CONTROLLED_CONFIG.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return int(rc or 0)


if __name__ == '__main__':
    raise SystemExit(main())
