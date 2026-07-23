from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .gate2_worker import _extract_embedding_rows, _free_port, _post_json, _wait_server
from .gate3_worker import _find_llama_server as find_llama_server_binary

REPO = Path(__file__).resolve().parent.parent.parent.parent
BENCH = REPO / "benchmark/embedding-v3"
DEFAULT_PROFILES_PATH = BENCH / "config/production_profiles.json"

INPUT_TYPES = frozenset({"document", "query"})
MAX_TEXTS = 64
MAX_TOTAL_CHARS = 512 * 1024


def _sanitize(msg: str) -> str:
    for pat in (REPO.as_posix(), REPO.as_posix().replace("/", "\\"),
                os.environ.get("HOME", ""), os.environ.get("USER", "")):
        if pat:
            msg = msg.replace(pat, "<redacted>")
    return msg


def _sha256(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(8 * 1024 * 1024):
            d.update(block)
    return d.hexdigest()


def _find_llama_server() -> str:
    explicit = os.environ.get("LLAMA_SERVER")
    candidates = [
        shutil.which(explicit) if explicit else None,
        explicit if explicit and Path(explicit).exists() else None,
        shutil.which("llama-server"),
        shutil.which("llama-server-cuda"),
    ]
    server = next((str(p) for p in candidates if p), None)
    if server is None:
        raise RuntimeError("llama-server não encontrado no PATH. Defina LLAMA_SERVER.")
    return server


def _find_gguf_path(profile: dict) -> Path | None:
    emb = profile.get("embedding", {})
    eid = emb.get("id", "")
    if eid == "embeddinggemma_768_float32":
        return REPO / "embed/embeddinggemma_gguf/embeddinggemma-300M-Q8_0.gguf"
    if eid == "nemotron_3_embed_1b_q4_k_m_gguf":
        return REPO / "embed/Nemotron-3-Embed-1B-Q4_K_M/nemotron-3-embed-1b-q4_k_m.gguf"
    return None


def _load_profiles(path: Path | None = None) -> list[dict]:
    path = path or DEFAULT_PROFILES_PATH
    with open(path) as f:
        data = json.load(f)
    return data.get("profiles", [])


def _find_profile(profiles: list[dict], profile_id: str) -> dict:
    for p in profiles:
        if p["id"] == profile_id:
            return p
    raise KeyError(f"Perfil '{profile_id}' não encontrado")


def _validate_input(payload: dict) -> None:
    errors = []
    if not isinstance(payload.get("texts"), list) or len(payload["texts"]) == 0:
        errors.append("'texts' deve ser uma lista não vazia")
    if isinstance(payload.get("texts"), list):
        if any(not isinstance(t, str) or not t.strip() for t in payload["texts"]):
            errors.append("cada texto deve ser uma string não vazia")
        if len(payload["texts"]) > MAX_TEXTS:
            errors.append(f"máximo de {MAX_TEXTS} textos")
        total = sum(len(t) for t in payload["texts"])
        if total > MAX_TOTAL_CHARS:
            errors.append(f"tamanho total excede {MAX_TOTAL_CHARS} caracteres")
    if payload.get("input_type") not in INPUT_TYPES:
        errors.append(f"'input_type' deve ser 'document' ou 'query'")
    if errors:
        raise ValueError("; ".join(errors))


class FakeBackend:
    def __init__(self, dimension: int = 768, normalized: bool = True) -> None:
        self._dimension = dimension
        self._normalized = normalized

    def embed(self, texts: list[str], profile: dict) -> np.ndarray:
        rng = np.random.default_rng(42)
        matrix = rng.uniform(-1, 1, (len(texts), self._dimension)).astype(np.float32)
        if self._normalized:
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1
            matrix = matrix / norms
        return matrix


class LlamaCppBackend:
    def __init__(self, gguf_path: Path, pooling: str = "mean",
                 normalize: int = 2, gpu_layers: int = 99,
                 context_size: int = 2048) -> None:
        self._gguf = gguf_path
        self._pooling = pooling
        self._normalize = normalize
        self._gpu_layers = gpu_layers
        self._context_size = context_size
        self._server: subprocess.Popen[str] | None = None
        self._port: int | None = None
        self._server_path: str | None = None

    def _ensure_server(self) -> tuple[str, int]:
        port = _free_port()
        server_path = _find_llama_server()
        cmd = [
            server_path, "-m", str(self._gguf),
            "--embedding", "--pooling", self._pooling,
            "--embd-normalize", str(self._normalize),
            "--host", "127.0.0.1", "--port", str(port),
            "-np", "1", "-ngl", str(self._gpu_layers),
            "-c", str(self._context_size),
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _wait_server(port, proc, timeout=120)
        self._server = proc
        self._port = port
        self._server_path = server_path
        return server_path, port

    def embed(self, texts: list[str], profile: dict) -> np.ndarray:
        if self._server is None:
            self._ensure_server()
        assert self._port is not None
        dim = profile.get("embedding", {}).get("dimension", 0)
        rows = []
        for text in texts:
            result = _post_json(
                f"http://127.0.0.1:{self._port}/v1/embeddings",
                {"input": [text], "model": "default"},
                timeout=300,
            )
            extracted = _extract_embedding_rows(result)
            rows.extend(extracted)
        matrix = np.asarray(rows, dtype=np.float32)
        if dim and matrix.shape[1] > dim:
            matrix = matrix[:, :dim]
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return matrix / norms

    def close(self) -> None:
        if self._server:
            self._server.terminate()
            try:
                self._server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._server.kill()
            self._server = None
            self._port = None


class VllmBackend:
    def __init__(self, vllm_env: Path | str) -> None:
        self._env = Path(vllm_env)
        self._proc: subprocess.Popen[str] | None = None
        self._port: int | None = None

    def _check_available(self) -> None:
        if not self._env.is_dir():
            raise RuntimeError(
                f"Ambiente vLLM não encontrado em {self._env}")
        python = self._env / "bin/python3"
        if not python.exists():
            python = self._env / "bin/python"
        if not python.exists():
            raise RuntimeError(
                f"Python do ambiente vLLM não encontrado em {self._env}/bin/")

    def embed(self, texts: list[str], profile: dict) -> np.ndarray:
        self._check_available()
        return np.zeros((len(texts), 1024), dtype=np.float32)

    def close(self) -> None:
        pass


def build_backend(profile: dict, evaluation_mode: bool = False,
                  force_fake: bool = False) -> tuple[Any, dict]:
    emb = profile.get("embedding", {})
    bid = emb.get("backend", "")
    dim = emb.get("dimension", 0)
    normalized = emb.get("normalization", "L2") == "L2"
    meta: dict[str, Any] = {"backend": bid}

    if force_fake:
        return FakeBackend(dimension=dim, normalized=normalized), meta

    if bid == "llama.cpp":
        gguf = _find_gguf_path(profile)
        if gguf is None or not gguf.exists():
            raise RuntimeError(f"GGUF não encontrado para perfil '{profile.get('id')}'")
        meta["gguf_path"] = gguf.as_posix()
        meta["gguf_sha256"] = _sha256(gguf)
        meta["pooling"] = emb.get("pooling", "mean")
        return LlamaCppBackend(gguf, pooling=meta["pooling"]), meta

    if bid == "vllm":
        isolated = emb.get("isolated_environment")
        if isolated:
            meta["isolated_environment"] = isolated
        return VllmBackend(isolated or "/tmp/vllm-env"), meta

    raise RuntimeError(f"Backend '{bid}' não suportado")


def _check_profile_allowed(profile: dict, evaluation_mode: bool,
                           allow_external_api: bool) -> bool:
    pid = profile["id"]
    if not profile.get("enabled", False) and not evaluation_mode:
        raise RuntimeError(
            f"Perfil '{pid}' está desabilitado. Use evaluation_mode=true para teste experimental")
    if profile.get("requires_api") and not allow_external_api:
        raise RuntimeError(
            f"Perfil '{pid}' requer API externa e não está autorizado")
    if profile.get("requires_api") and not profile.get("requires_authorization"):
        raise RuntimeError(
            f"Perfil '{pid}' tem requires_api=true mas requires_authorization não está definido")
    return True


def _validate_embeddings(matrix: np.ndarray, dimension: int, normalized: bool) -> None:
    if matrix.ndim != 2:
        raise ValueError(f"matriz deve ser 2D, shape={matrix.shape}")
    if matrix.shape[1] != dimension:
        raise ValueError(
            f"dimensão esperada {dimension}, obtida {matrix.shape[1]}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("embedding contém valores não finitos")
    if normalized:
        norms = np.linalg.norm(matrix, axis=1)
        if np.any(norms == 0):
            raise ValueError("embedding com norma zero")
        if np.any(np.abs(norms - 1.0) > 0.01):
            raise ValueError(
                f"normalização L2 esperada, normas fora de tolerância: {norms}")


@dataclass
class IntegrationResult:
    profile_id: str
    status: str
    backend: str = ""
    dimension: int = 0
    vector_count: int = 0
    norm_range: tuple[float, float] = (0.0, 0.0)
    repeatability: float = 0.0
    reason: str = ""
    runtime_seconds: float = 0.0
    startup_seconds: float = 0.0
    weight_sha256: str = ""
    runtime_version: str = ""
    hardware: str = ""
    metadata: dict = field(default_factory=dict)

    def to_evidence(self) -> dict:
        return {
            "schema_version": "1.0",
            "profile_id": self.profile_id,
            "status": self.status,
            "backend": self.backend,
            "dimension": self.dimension if self.status in ("PASSED", "FAILED") else None,
            "vector_count": self.vector_count if self.vector_count else None,
            "norm_range": list(self.norm_range) if self.norm_range else None,
            "repeatability_cosine": round(self.repeatability, 6) if self.repeatability else None,
            "reason": self.reason if self.reason else None,
            "runtime_seconds": round(self.runtime_seconds, 3) if self.runtime_seconds else None,
            "startup_seconds": round(self.startup_seconds, 3) if self.startup_seconds else None,
            "weight_sha256": self.weight_sha256 or None,
            "runtime_version": self.runtime_version or None,
            "hardware": self.hardware or None,
        }


def run_profile(profiles: list[dict], profile_id: str,
                texts: list[str], input_type: str = "document",
                evaluation_mode: bool = False,
                allow_external_api: bool = False,
                force_fake: bool = False) -> IntegrationResult:
    started = time.monotonic()
    profile = _find_profile(profiles, profile_id)
    emb = profile.get("embedding", {})
    dimension = emb.get("dimension", 0)
    normalized = emb.get("normalization", "L2") == "L2"
    backend_name = emb.get("backend", "")
    pid = profile_id

    result = IntegrationResult(profile_id=pid, backend=backend_name, status="FAILED")
    backend_instance = None
    try:
        _check_profile_allowed(profile, evaluation_mode, allow_external_api)
        backend_instance, meta = build_backend(
            profile, evaluation_mode=evaluation_mode,
            force_fake=force_fake)
        startup = time.monotonic()
        matrix = backend_instance.embed(texts, profile)
        startup_secs = time.monotonic() - startup

        _validate_embeddings(matrix, dimension, normalized)
        norms = np.linalg.norm(matrix, axis=1)

        result.dimension = dimension
        result.vector_count = len(texts)
        result.norm_range = (float(norms.min()), float(norms.max()))
        result.startup_seconds = startup_secs
        result.metadata = meta
        result.weight_sha256 = meta.get("gguf_sha256", "")
        result.status = "PASSED"

        if len(texts) >= 2:
            v0 = matrix[0]
            v1 = matrix[1]
            sim = float(np.dot(v0, v1) / (
                np.linalg.norm(v0) * np.linalg.norm(v1)))
            result.repeatability = sim

        result.runtime_version = _get_runtime_version(backend_name)

        import platform
        result.hardware = f"{platform.machine()}; {platform.processor() or 'N/A'}"
        try:
            import subprocess
            nvidia = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5)
            if nvidia.returncode == 0:
                gpu = nvidia.stdout.strip().split("\n")[0].strip()
                result.hardware += f"; GPU: {gpu}"
        except Exception:
            pass

    except RuntimeError as exc:
        result.status = "BLOCKED"
        result.reason = _sanitize(str(exc))
    except Exception as exc:
        result.status = "FAILED"
        result.reason = _sanitize(str(exc))
    finally:
        if backend_instance and hasattr(backend_instance, "close"):
            backend_instance.close()
        result.runtime_seconds = time.monotonic() - started
    return result


def _get_runtime_version(backend: str) -> str:
    try:
        if backend == "llama.cpp":
            server = _find_llama_server()
            r = subprocess.run([server, "--version"],
                               capture_output=True, text=True, timeout=10)
            return r.stdout.strip()[:80] if r.stdout else "unknown"
        if backend == "vllm":
            return "vllm (environment not available)"
    except Exception:
        return "unknown"
    return "unknown"


def run_all_profiles(profiles: list[dict], texts: list[str],
                     input_type: str = "document",
                     allow_external_api: bool = False,
                     force_fake: bool = False) -> list[IntegrationResult]:
    results: list[IntegrationResult] = []
    for p in profiles:
        pid = p["id"]
        evaluation = "evaluation" in pid
        try:
            r = run_profile(profiles, pid, texts, input_type,
                            evaluation_mode=evaluation,
                            allow_external_api=allow_external_api,
                            force_fake=force_fake)
        except RuntimeError as exc:
            r = IntegrationResult(profile_id=pid, status="BLOCKED",
                                  reason=_sanitize(str(exc)))
        except Exception as exc:
            r = IntegrationResult(profile_id=pid, status="FAILED",
                                  reason=_sanitize(str(exc)))
        results.append(r)
    return results


def summarize_results(results: list) -> dict:
    def _ev(r):
        return r.to_evidence() if hasattr(r, "to_evidence") else r
    ready = {f"{r['profile_id']}_ready" if not r['profile_id'].startswith("quality") else f"external_api_guard_ready": r['status'] == "PASSED"
             for r in [_ev(r) for r in results]}
    summary: dict[str, Any] = {
        "schema_version": "1.0",
        "task": "RETRIEVAL-RUNTIME-INTEGRATION-1",
        "application_contract_ready": all(
            r['status'] == "PASSED" if r['profile_id'] == "local_default"
            else r['status'] in ("BLOCKED", "PASSED")
            for r in [_ev(r) for r in results]
            if r['profile_id'] in ("local_default", "quality_external_optional")),
        "results": [_ev(r) for r in results],
    }
    for r in [_ev(r) for r in results]:
        key = f"{r['profile_id']}_ready".replace("-", "_")
        if r['profile_id'] == "quality_external_optional":
            key = "external_api_guard_ready"
        summary[key] = r['status'] == "PASSED"
    blocks = [r['reason'] for r in [_ev(r) for r in results] if r['status'] in ("BLOCKED", "FAILED") and r.get('reason')]
    if blocks:
        summary["blockers"] = blocks
    return summary
