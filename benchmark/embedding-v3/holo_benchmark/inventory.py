from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PACKAGES = [
    "torch",
    "transformers",
    "sentence-transformers",
    "accelerate",
    "safetensors",
    "huggingface-hub",
    "FlagEmbedding",
    "voyageai",
    "numpy",
    "scipy",
    "pandas",
    "pyarrow",
    "psutil",
    "pydantic",
    "orjson",
    "tqdm",
    "rich",
    "pynvml",
]
EXPECTED_REPOSITORY = "weltall-ia/holo-models"


def run_command(args: list[str], timeout: int = 20) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "args": args,
            "returncode": proc.returncode,
            "duration_seconds": round(time.monotonic() - started, 4),
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except FileNotFoundError:
        return {
            "args": args,
            "returncode": 127,
            "duration_seconds": round(time.monotonic() - started, 4),
            "stdout": "",
            "stderr": "executable_not_found",
        }
    except subprocess.TimeoutExpired:
        return {
            "args": args,
            "returncode": 124,
            "duration_seconds": round(time.monotonic() - started, 4),
            "stdout": "",
            "stderr": "timeout",
        }


def _remote_repository_slug(remote_url: str) -> str:
    value = remote_url.strip()
    if not value:
        return ""

    if "://" in value:
        path = urlsplit(value).path
    elif ":" in value:
        # Sintaxe SCP usada pelo Git: git@github.com:owner/repo.git
        path = value.split(":", 1)[1]
    else:
        path = value

    normalized = path.strip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized.lower()


def _origin_matches_holo_models(remote_url: str) -> bool:
    return _remote_repository_slug(remote_url) == EXPECTED_REPOSITORY


def _os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    data: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key] = value.strip().strip('"')
    return data


def _cpu_info() -> dict[str, Any]:
    model = platform.processor() or "unknown"
    physical = None
    logical = os.cpu_count()
    try:
        import psutil  # type: ignore

        physical = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)
    except Exception:
        pass
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                model = line.split(":", 1)[1].strip()
                break
    return {"model": model, "physical_cores": physical, "logical_cores": logical}


def _memory_info() -> dict[str, Any]:
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        return {"total_bytes": vm.total, "available_bytes": vm.available}
    except Exception as exc:
        meminfo = Path("/proc/meminfo")
        total = None
        if meminfo.exists():
            for line in meminfo.read_text().splitlines():
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1]) * 1024
                    break
        return {
            "total_bytes": total,
            "available_bytes": None,
            "collector_error": type(exc).__name__,
        }


def _filesystem_info(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    stat = run_command(["findmnt", "-no", "FSTYPE,SOURCE,TARGET", "--target", str(path)])
    return {
        "path": str(path),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "findmnt": stat,
    }


def _nvidia_info() -> dict[str, Any]:
    query = run_command(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.total,driver_version,compute_cap",
            "--format=csv,noheader,nounits",
        ]
    )
    gpus = []
    if query["returncode"] == 0:
        for line in query["stdout"].splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 5:
                gpus.append(
                    {
                        "index": int(parts[0]),
                        "name": parts[1],
                        "memory_total_mib": int(float(parts[2])),
                        "driver_version": parts[3],
                        "compute_capability": parts[4],
                    }
                )
    return {
        "available": query["returncode"] == 0 and bool(gpus),
        "gpus": gpus,
        "nvidia_smi": query,
        "nvcc": run_command(["nvcc", "--version"]),
    }


def _torch_cuda_test(perform_allocation: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "imported": False,
        "cuda_available": False,
        "allocation_tested": False,
        "allocation_passed": False,
    }
    try:
        import torch  # type: ignore

        result.update(
            {
                "imported": True,
                "torch_version": torch.__version__,
                "torch_cuda_version": torch.version.cuda,
                "cuda_available": bool(torch.cuda.is_available()),
                "device_count": int(torch.cuda.device_count())
                if torch.cuda.is_available()
                else 0,
            }
        )
        if torch.cuda.is_available():
            devices = []
            for index in range(torch.cuda.device_count()):
                properties = torch.cuda.get_device_properties(index)
                devices.append(
                    {
                        "index": index,
                        "name": torch.cuda.get_device_name(index),
                        "total_memory_bytes": int(properties.total_memory),
                        "major": int(properties.major),
                        "minor": int(properties.minor),
                    }
                )
            result["devices"] = devices
            if perform_allocation:
                result["allocation_tested"] = True
                tensor = torch.empty((1024, 1024), device="cuda", dtype=torch.float32)
                tensor.fill_(1.0)
                value = float(tensor.sum().item())
                del tensor
                torch.cuda.synchronize()
                result["allocation_passed"] = value == 1048576.0
                result["allocated_value"] = value
        return result
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error_message"] = str(exc)
        return result


def installed_packages() -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    for package in PACKAGES:
        try:
            resolved[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            resolved[package] = None
    return resolved


def _read_task_status(repo_root: Path) -> dict[str, str]:
    path = repo_root / ".ai" / "tasks" / "EMBED-BENCH-V3-1.1" / "STATUS.yml"
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        if (
            not raw
            or raw[0].isspace()
            or raw.lstrip().startswith("#")
            or ":" not in raw
        ):
            continue
        key, value = raw.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def collect(
    project_root: Path,
    repo_root: Path,
    perform_cuda_allocation: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    system_info = {
        "schema_version": "1.0",
        "created_at": now,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "kernel": platform.version(),
            "machine": platform.machine(),
            "os_release": _os_release(),
        },
        "cpu": _cpu_info(),
        "memory": _memory_info(),
        "filesystem_project": _filesystem_info(project_root),
        "filesystem_repo": _filesystem_info(repo_root),
        "nvidia": _nvidia_info(),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        "torch_cuda": _torch_cuda_test(perform_cuda_allocation),
    }
    environment = {
        "schema_version": "1.0",
        "created_at": now,
        "repo_root": str(repo_root),
        "project_root": str(project_root),
        "voyage_api_key_present": bool(os.environ.get("VOYAGE_API_KEY")),
        "huggingface_token_present": bool(
            os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        ),
        "packages": installed_packages(),
        "task_status": _read_task_status(repo_root),
        "commands": {
            # Somente alterações em arquivos rastreados bloqueiam o Gate 0.
            "git_status": run_command(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "status",
                    "--short",
                    "--untracked-files=no",
                ]
            ),
            # Arquivos não rastreados são inventariados separadamente e não são apagados.
            "git_untracked": run_command(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                ]
            ),
            "git_branch": run_command(
                ["git", "-C", str(repo_root), "branch", "--show-current"]
            ),
            "git_head": run_command(
                ["git", "-C", str(repo_root), "rev-parse", "HEAD"]
            ),
            "git_origin_master": run_command(
                ["git", "-C", str(repo_root), "rev-parse", "origin/master"]
            ),
            "git_origin_url": run_command(
                ["git", "-C", str(repo_root), "remote", "get-url", "origin"]
            ),
        },
    }
    return system_info, environment


def write_outputs(
    project_root: Path,
    system_info: dict[str, Any],
    environment: dict[str, Any],
) -> None:
    (project_root / "system_info.json").write_text(
        json.dumps(system_info, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "environment.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = []
    for name, version in environment["packages"].items():
        if version is not None:
            lines.append(f"{name}=={version}")
    (project_root / "requirements-resolved.txt").write_text(
        "\n".join(sorted(lines)) + "\n",
        encoding="utf-8",
    )


def gate0_passes(
    system_info: dict[str, Any],
    environment: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors = []
    commands = environment["commands"]
    branch = commands["git_branch"]
    head = commands["git_head"]
    origin_master = commands["git_origin_master"]
    origin_url = commands["git_origin_url"]
    task = environment.get("task_status", {})

    if origin_url["returncode"] != 0:
        errors.append("não foi possível identificar o remote origin")
    elif not _origin_matches_holo_models(origin_url["stdout"]):
        errors.append(
            "remote origin não corresponde a Weltall-IA/holo-models: "
            f"{origin_url['stdout']}"
        )

    if branch["returncode"] != 0:
        errors.append("não foi possível identificar a branch")
    elif branch["stdout"] == "master":
        errors.append("execução em master é proibida")
    elif task.get("branch") and branch["stdout"] != task["branch"]:
        errors.append(
            f"branch divergente: atual={branch['stdout']} esperada={task['branch']}"
        )

    if head["returncode"] != 0:
        errors.append("não foi possível identificar HEAD")
    expected_head = task.get("expected_head")
    if (
        expected_head
        and not expected_head.startswith("PENDING")
        and head["stdout"] != expected_head
    ):
        errors.append(
            f"HEAD divergente: atual={head['stdout']} esperado={expected_head}"
        )

    if origin_master["returncode"] != 0:
        errors.append("origin/master indisponível; execute git fetch origin")

    git_status = commands["git_status"]
    gate0_outputs = {
        "benchmark/embedding-v3/GATE_0_REPORT.md",
        "benchmark/embedding-v3/environment.json",
        "benchmark/embedding-v3/system_info.json",
        "benchmark/embedding-v3/gate_status.json",
        "benchmark/embedding-v3/requirements-resolved.txt",
    }
    real_changes = [
        line
        for line in git_status["stdout"].splitlines()
        if line.strip()
        and not any(
            output == line.split()[-1] if len(line.split()) >= 2 else False
            for output in gate0_outputs
        )
    ]
    if git_status["returncode"] != 0:
        errors.append("git status falhou")
    elif real_changes:
        errors.append("working tree possui alterações em arquivos rastreados")

    if system_info["filesystem_project"]["free_bytes"] < 2 * 1024**3:
        errors.append("menos de 2 GiB livres para Gates 0 e 1")

    nvidia = system_info["nvidia"]
    torch_cuda = system_info["torch_cuda"]
    if (
        nvidia["available"]
        and torch_cuda.get("imported")
        and not torch_cuda.get("cuda_available")
    ):
        errors.append("GPU detectada pelo nvidia-smi, mas CUDA indisponível no PyTorch")
    if (
        torch_cuda.get("cuda_available")
        and torch_cuda.get("allocation_tested")
        and not torch_cuda.get("allocation_passed")
    ):
        errors.append("alocação CUDA mínima falhou")

    return not errors, errors


def render_report(
    system_info: dict[str, Any],
    environment: dict[str, Any],
    dry_run: bool,
) -> str:
    ok, errors = gate0_passes(system_info, environment)
    commands = environment["commands"]
    gpu_names = ", ".join(gpu["name"] for gpu in system_info["nvidia"]["gpus"])
    if not gpu_names:
        gpu_names = "não detectada"
    packages_missing = [
        package for package, version in environment["packages"].items() if version is None
    ]
    untracked_command = commands.get("git_untracked", {})
    untracked_files = [
        line
        for line in untracked_command.get("stdout", "").splitlines()
        if line.strip()
    ]
    warnings = []
    if untracked_command.get("returncode") not in (None, 0):
        warnings.append("não foi possível inventariar arquivos não rastreados")
    elif untracked_files:
        warnings.append(
            f"{len(untracked_files)} arquivo(s) ou diretório(s) não rastreado(s) "
            "foram preservados e não bloqueiam o Gate 0"
        )

    return "\n".join(
        [
            "# GATE 0 REPORT",
            "",
            f"- modo: {'dry-run' if dry_run else 'execução'}",
            f"- resultado: {'PASS' if ok else 'BLOCKED'}",
            f"- branch: `{commands['git_branch']['stdout']}`",
            f"- HEAD: `{commands['git_head']['stdout']}`",
            f"- origin/master: `{commands['git_origin_master']['stdout']}`",
            f"- origin URL: `{commands['git_origin_url']['stdout']}`",
            f"- CPU: {system_info['cpu']['model']}",
            "- núcleos físicos/lógicos: "
            f"{system_info['cpu']['physical_cores']}/"
            f"{system_info['cpu']['logical_cores']}",
            f"- RAM total: {system_info['memory']['total_bytes']}",
            f"- GPU: {gpu_names}",
            "- CUDA PyTorch disponível: "
            f"{system_info['torch_cuda'].get('cuda_available')}",
            "- alocação CUDA testada/aprovada: "
            f"{system_info['torch_cuda'].get('allocation_tested')}/"
            f"{system_info['torch_cuda'].get('allocation_passed')}",
            "- filesystem: "
            f"{system_info['filesystem_project']['findmnt']['stdout']}",
            "- espaço livre: "
            f"{system_info['filesystem_project']['free_bytes']} bytes",
            f"- VOYAGE_API_KEY presente: {environment['voyage_api_key_present']}",
            "- dependências ausentes: "
            f"{', '.join(packages_missing) if packages_missing else 'nenhuma'}",
            "",
            "## Erros",
            *(f"- {error}" for error in errors),
            "" if errors else "- nenhum",
            "",
            "## Avisos",
            *(f"- {warning}" for warning in warnings),
            "" if warnings else "- nenhum",
            "",
            "Nenhum checkpoint foi baixado e nenhuma chamada à Voyage foi realizada.",
            "",
        ]
    )
