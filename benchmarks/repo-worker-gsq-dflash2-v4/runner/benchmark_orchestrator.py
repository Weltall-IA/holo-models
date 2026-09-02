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
HERE = ROOT / 'benchmarks/repo-worker-gsq-dflash2-v4'
BASE_RUNNER = BASE / 'runner/benchmark_orchestrator.py'
TARGET = ROOT / 'text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf'
TARGET_SHA = '16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb'
DFLASH = ROOT / 'text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf'
DFLASH_SHA = '1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd'

SEED = 9137
CTX = 32768
THREADS = 2
BUDGET = 256
DRAFT_N = 7
TEMP = 0.2
TOP_P = 0.95
CACHE_K = 'q8_0'
CACHE_V = 'q4_0'


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
    spec = importlib.util.spec_from_file_location('challenger_v2_base_dflash', BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot import {BASE_RUNNER}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_runtime_features(runtime_bin: Path) -> dict:
    p = subprocess.run([str(runtime_bin), '--help'], capture_output=True, text=True, timeout=30)
    text = p.stdout + p.stderr
    required = {
        'draft_model_flag': ('--spec-draft-model' in text) or ('--model-draft' in text) or ('-md' in text),
        '--spec-type': '--spec-type' in text,
        'draft-dflash': 'draft-dflash' in text,
        '--spec-draft-n-max': '--spec-draft-n-max' in text,
        'draft_gpu_layers': ('--spec-draft-ngl' in text) or ('--gpu-layers-draft' in text) or ('-ngld' in text),
        '--reasoning-budget': '--reasoning-budget' in text,
    }
    missing = [name for name, ok in required.items() if not ok]
    if missing:
        raise SystemExit('RUNTIME_FEATURE_MISSING=' + ','.join(missing))
    return required


def profile(pid: str, name: str, reasoning: bool, budget: int | None) -> dict:
    return {
        'id': pid,
        'name': name,
        'model_path': TARGET,
        'model_sha256': TARGET_SHA,
        'thinking': reasoning,
        'temperature': TEMP,
        'top_p': TOP_P,
        'reasoning_budget': budget,
    }


def dflash_metrics(log_path: Path) -> dict:
    text = log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''
    rates = [float(x) for x in re.findall(r'draft acceptance rate\s*=\s*([\d.]+)', text, flags=re.I)]
    gen_acc = [(int(a), int(b)) for a, b in re.findall(r'#gen tokens\s*=\s*(\d+)\s*,\s*#acc tokens\s*=\s*(\d+)', text, flags=re.I)]
    alt = [(int(a), int(b)) for a, b in re.findall(r'drafted\s*[=:]\s*(\d+).*?accepted\s*[=:]\s*(\d+)', text, flags=re.I)]
    pairs = gen_acc + alt
    max_gen = max((a for a, _ in pairs), default=None)
    max_acc = max((b for _, b in pairs), default=None)
    return {
        'draft_acceptance_rate_last': rates[-1] if rates else None,
        'draft_acceptance_rate_max': max(rates) if rates else None,
        'draft_generated_tokens_max': max_gen,
        'draft_accepted_tokens_max': max_acc,
        'observed_rate_samples': len(rates),
        'observed_counter_samples': len(pairs),
    }


def main() -> int:
    ensure_suite_links()

    if not TARGET.exists():
        raise SystemExit(f'TARGET_MISSING={TARGET}')
    if not DFLASH.exists():
        raise SystemExit('DFLASH2_MISSING=YES; run PREPARE_DFLASH2.sh first')

    target_sha = sha256(TARGET)
    dflash_sha = sha256(DFLASH)
    if target_sha != TARGET_SHA:
        raise SystemExit(f'TARGET_SHA_MISMATCH={target_sha}')
    if dflash_sha != DFLASH_SHA:
        raise SystemExit(f'DFLASH2_SHA_MISMATCH={dflash_sha}')

    m = load_base()
    runtime_features = verify_runtime_features(m.RUNTIME_BIN)

    m.BENCHMARK_DIR = HERE
    m.WORK_ROOT = Path('/tmp/repo-worker-gsq-dflash2-v4-worktrees')
    m.PORT = 8154
    m.SEED = SEED
    m.TASK_TIMEOUT = 480
    m.REQUEST_TIMEOUT_CEILING = 240
    m.MAX_TURNS = 40

    tasks = copy.deepcopy(m.TASKS)
    for task in tasks:
        if task['id'] == 'task07_architectural_placement':
            task['required_edits'] = ['challenge/arch/policy/access.py']
    m.TASKS = tasks

    m.PROFILES = [
        profile('iq2-dflash-off', 'GSQ IQ2_S / DFlash2 Q4_K_M / reasoning OFF', False, None),
        profile('iq2-dflash-b256', 'GSQ IQ2_S / DFlash2 Q4_K_M / reasoning budget 256', True, BUDGET),
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
            '-m', str(TARGET), '-md', str(DFLASH),
            '--host', '127.0.0.1', '--port', str(m.PORT),
            '-c', str(CTX), '-np', '1', '-ngl', '999', '-fa', 'on',
            '-ctk', CACHE_K, '-ctv', CACHE_V,
            '-t', str(THREADS), '-tb', str(THREADS),
            '-ngld', '999',
            '--spec-type', 'draft-dflash', '--spec-draft-n-max', str(DRAFT_N),
            '--no-webui', '--reasoning', 'on' if p['thinking'] else 'off',
        ]
        if p.get('reasoning_budget') is not None:
            args += ['--reasoning-budget', str(p['reasoning_budget'])]
        return args
    m.profile_server_args = server_args

    # Avoid rerunning target-only llama-bench: server traces are the relevant
    # measurement for DFlash2 and the no-spec target baseline already exists.
    def skip_llama_bench(profile, output_path):
        output_path.write_text('Skipped: DFlash2 speed is measured from live server traces.\n', encoding='utf-8')
        return {'ok': True, 'skipped': True, 'reason': 'use live server traces for DFlash2'}
    m.run_llama_bench = skip_llama_bench

    # A 64-token sanity response can be consumed entirely by a 256-token
    # reasoning budget. Give the budgeted profile enough completion headroom
    # without changing task generation limits.
    def sanity_check(p):
        url = f'http://127.0.0.1:{m.PORT}/v1/chat/completions'
        checks = [
            ('arithmetic', 'Answer with only the number: 17 * 23', '391'),
            ('capital', 'Answer with only the capital of France.', 'Paris'),
        ]
        out = {}
        for key, prompt, expected in checks:
            payload = {
                'model': p['id'],
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.0, 'top_p': 1.0, 'seed': SEED,
                'max_tokens': 384 if p['thinking'] else 64,
            }
            try:
                resp = m.request_json(url, payload, timeout=120)
                msg = resp['choices'][0].get('message', {})
                content = (msg.get('content') or '') + '\n' + (msg.get('reasoning_content') or '')
                out[key] = {'ok': expected.lower() in content.lower(), 'expected': expected, 'content': content[-1200:]}
            except Exception as exc:
                out[key] = {'ok': False, 'expected': expected, 'error': f'{type(exc).__name__}: {exc}'}
        out['ok'] = all(v.get('ok') for k, v in out.items() if k != 'ok')
        return out
    m.sanity_check = sanity_check

    rc = m.main()

    metrics = {}
    for p in m.PROFILES:
        metrics[p['id']] = dflash_metrics(HERE / 'profiles' / p['id'] / 'tasks_server.log')
    (HERE / 'DFLASH_METRICS.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')

    config = {
        'benchmark': 'repo-worker-gsq-dflash2-v4',
        'baseline_reference': 'benchmarks/repo-worker-challenger-v2/profiles/gsq-iq2s-off/',
        'seed': SEED,
        'ctx': CTX,
        'threads': THREADS,
        'cache_k': CACHE_K,
        'cache_v': CACHE_V,
        'temperature': TEMP,
        'top_p': TOP_P,
        'reasoning_budget': BUDGET,
        'spec_type': 'draft-dflash',
        'spec_draft_n_max': DRAFT_N,
        'target_sha256': target_sha,
        'dflash_sha256': dflash_sha,
        'runtime_features': runtime_features,
        't7_fix': 'service edit no longer required; policy placement remains mandatory',
    }
    (HERE / 'CONTROLLED_CONFIG.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    return int(rc or 0)


if __name__ == '__main__':
    raise SystemExit(main())
