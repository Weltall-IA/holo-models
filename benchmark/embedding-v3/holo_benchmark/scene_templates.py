from __future__ import annotations

from .scene_base import OPENERS, CLOSERS, SCENES, RELATED_NEGATIVES, slugify, regex_tokens, _choice
from .scene_group_1 import scene_group_1
from .scene_group_2 import scene_group_2
from .scene_group_3 import scene_group_3
from .scene_group_4 import scene_group_4


def _scene_body(key: str, p: str, q: str, r: str, s: str, setting: str, obj: str, idx: int) -> tuple[list[str], str]:
    for handler in (scene_group_1, scene_group_2, scene_group_3, scene_group_4):
        result = handler(key, p, q, r, s, setting, obj, idx)
        if result is not None:
            lines, exact = result
            extra_variants = [
                f"O som ao redor obrigou {p} a repetir uma pergunta, dando a {q} tempo suficiente para escolher uma resposta menos espontânea.",
                f"{r} observou a distância entre os dois e mudou de lugar quando percebeu que o conflito poderia envolver {s}.",
                "Uma pessoa passou pelo ambiente e interrompeu a conversa por poucos segundos; depois disso, ninguém retomou exatamente a mesma versão.",
                f"{obj.capitalize()} mudou de mãos duas vezes durante a cena, acompanhando a mudança de controle entre os personagens.",
            ]
            lines.insert(4, extra_variants[idx % 4])
            return lines, exact
    raise KeyError(key)
