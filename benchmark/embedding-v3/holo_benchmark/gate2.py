from __future__ import annotations

# Camada pública mantida para compatibilidade com benchmark.py e testes.
# A implementação resiliente vive em gate2_runtime.py; cada modelo é executado
# por gate2_worker.py em processo separado para não propagar falhas CUDA.
from .gate2_runtime import *  # noqa: F401,F403
