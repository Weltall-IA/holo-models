from __future__ import annotations

import random
from typing import Any

from .work_catalog import (
    SCHEMA_VERSION,
    CORPUS_VERSION,
    SEED,
    TITLES,
    SETTINGS,
    OBJECTS,
    NAMES,
    WORK_PRESSURES,
    LOCAL_DETAILS,
)
from .scene_base import (
    OPENERS,
    CLOSERS,
    SCENES,
    RELATED_NEGATIVES,
    slugify,
    _choice,
)
from .scene_templates import _scene_body


def build_work_specs() -> list[dict[str, Any]]:
    works = []
    for i in range(30):
        chars = NAMES[i * 4:(i + 1) * 4]
        works.append({
            "work_id": f"work-{i + 1:03d}",
            "title": TITLES[i],
            "setting": SETTINGS[i],
            "object": OBJECTS[i],
            "characters": chars,
        })
    return works


def build_corpus(seed: int = SEED) -> tuple[list[dict[str, Any]], dict[tuple[int, str], str], dict[tuple[int, str], str]]:
    rng = random.Random(seed)
    chunks: list[dict[str, Any]] = []
    id_map: dict[tuple[int, str], str] = {}
    quote_map: dict[tuple[int, str], str] = {}
    for wi, work in enumerate(build_work_specs()):
        current_ms = rng.randint(1000, 7000)
        p, q, r, s = work["characters"]
        char_objs = [
            {"character_id": f"char-{slugify(name)}", "name": name, "role": "speaker" if j < 2 else "participant"}
            for j, name in enumerate(work["characters"])
        ]
        for sequence, spec in enumerate(SCENES, start=1):
            gap = rng.randint(3000, 9000)
            duration = rng.randint(85000, 132000)
            start_ms = current_ms + gap
            end_ms = start_ms + duration
            current_ms = end_ms
            body, exact = _scene_body(spec.key, p, q, r, s, work["setting"], work["object"], wi + sequence)
            opener = _choice(OPENERS, wi, sequence)
            closer = _choice(CLOSERS, wi, sequence)
            work_context = [
                f"Naquela fase da história, {p} {WORK_PRESSURES[wi]}, enquanto {q} tentava manter o grupo unido sem revelar o que sabia.",
                LOCAL_DETAILS[wi],
                f"{r} conhecia uma parte do passado de {p}, mas {s} tinha acesso aos detalhes práticos ligados a {work['object']}; por isso, as duas testemunhas interpretavam os mesmos gestos de maneiras incompatíveis.",
            ]
            text = " ".join([opener, *work_context, *body, closer])
            chunk_id = f"{work['work_id']}-ep-001-scene-{sequence:03d}-chunk-001"
            chunk = {
                "schema_version": SCHEMA_VERSION,
                "chunk_id": chunk_id,
                "work_id": work["work_id"],
                "episode_id": f"{work['work_id']}-ep-001",
                "sequence": sequence,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": duration,
                "title": work["title"],
                "text": text,
                "characters": char_objs,
                "themes": list(spec.themes),
                "scene_type": spec.scene_type,
                "emotion": list(spec.emotions),
                "event": spec.event,
                "requires_previous_context": spec.requires_context,
            }
            chunks.append(chunk)
            id_map[(wi, spec.key)] = chunk_id
            quote_map[(wi, spec.key)] = exact
    return chunks, id_map, quote_map


def _query_text(category: str, wi: int, spec: Any, work: dict[str, Any], quote: str, ordinal: int) -> tuple[str, str, bool, str]:
    p, q, r, s = work["characters"]
    obj = work["object"]
    setting = work["setting"]
    if category == "semantic_event":
        mapping = {
            "hidden_messages": (f"Encontre a cena em que {q} percebe, por notificações apagadas e horários de encontro, que {p} escondia uma relação importante.", "A consulta descreve a descoberta por mensagens sem depender de uma confissão."),
            "contradiction": (f"Localize quando a versão de {q} desmorona porque o horário informado por {r} não combina com os comprovantes reunidos por {p}.", "A mentira é descoberta pelo conflito entre horários e provas."),
            "parallel_relationship": (f"Em que trecho {p} conclui, comparando reservas e promessas repetidas, que {q} mantinha outra vida afetiva?", "A consulta evita a palavra traição e exige reconhecer promessas duplicadas."),
            "family_argument": (f"Qual cena transforma a decisão sobre {obj} numa discussão familiar de {p}, {q}, {r} e {s} sobre cuidado e ressentimentos antigos?", "O objeto é apenas o gatilho para um conflito familiar acumulado."),
            "implicit_threat": (f"Localize a conversa em que {q} ameaça {p} de modo educado ao mencionar a rotina de uma pessoa próxima.", "A intenção ameaçadora está implícita em um conselho aparentemente cordial."),
            "secret_revealed": (f"Encontre quando documentos ligados a {obj} revelam a {p} que a versão familiar sobre uma decisão antiga era falsa.", "A verdade surge por documentos e reorganiza fatos anteriores."),
            "twist": (f"Qual passagem revela que {s}, até então o aliado mais prestativo, conduzia a busca para esconder a própria participação?", "A reviravolta exige reinterpretar a ajuda como distração."),
            "chase": (f"Encontre a perseguição em que {p} e {r} tentam alcançar {s} depois que ele foge com {obj}.", "A consulta identifica uma perseguição específica por personagens e objeto."),
            "escape": (f"Localize a fuga de {p} e {q} por uma saída secundária depois de um apagão combinado.", "A cena é de fuga planejada, não apenas de perseguição."),
            "misunderstanding": (f"Em que cena {p} e {q} conversam por vários minutos acreditando que o outro exerce uma função diferente, causando decisões cômicas?", "O humor nasce de identidades e tarefas confundidas."),
        }
        query, rationale = mapping.get(spec.key, (
            f"Encontre o acontecimento envolvendo {p}, {q} e {obj} em {setting}, quando uma informação escondida altera a decisão do grupo.",
            "A consulta descreve o acontecimento por consequência e elementos narrativos.",
        ))
        return query, rationale, spec.requires_context, "hard" if ordinal % 3 == 0 else "medium"
    if category == "context_dependency":
        query = f"Depois do conflito anterior, qual cena de {work['title']} mostra {p} reagindo à consequência de uma decisão que não é nomeada diretamente?"
        rationale = "A resposta depende de conectar pronomes, consequências e acontecimentos anteriores."
        if spec.key == "pronoun_reference":
            query = f"Localize a conversa em que {p} diz apenas “aquilo” e {s} entende que se trata do acordo secreto feito depois da discussão familiar."
        elif spec.key == "distant_consequence":
            query = f"Qual cena mostra {p} e {q} descobrindo que uma assinatura feita meses antes bloqueou uma transferência atual?"
        elif spec.key == "sadness_guilt":
            query = f"Considerando o ritual já mostrado antes, onde o silêncio de {p} é confundido com culpa quando na verdade expressa saudade?"
        return query, rationale, True, "hard"
    if category == "emotion_intention":
        mapping = {
            "silent_cry": f"Encontre o trecho em que {p} chora sem discursar, tentando esconder a lágrima enquanto organiza {obj}.",
            "contained_anger": f"Localize quando {p} demonstra raiva contida ao alinhar {obj}, falar baixo e exigir que {q} repita a frase.",
            "implicit_threat": f"Em qual cena o tom cordial de {q} encobre a intenção de assustar {p}?",
            "fear_surprise": f"Qual passagem deixa ambíguo se {p} recua por surpresa ou por medo do que {q} trouxe?",
            "sadness_guilt": f"Encontre onde a tristeza de {p} é interpretada pelos outros como culpa.",
        }
        return mapping.get(spec.key, f"Localize a cena em que a intenção de {p} é percebida mais pelos gestos do que pelas palavras."), "A consulta exige distinguir emoção observável de interpretação equivocada.", spec.requires_context, "hard"
    if category == "indirect_dialogue":
        mapping = {
            "indirect_apology": f"Encontre a conversa em que {p} pede perdão sem dizer “desculpa”, reparando o dano e deixando tudo preparado para {q}.",
            "indirect_confrontation": f"Localize quando {p} pergunta há quanto tempo algo é chamado de coincidência, sem nomear diretamente a acusação contra {q}.",
            "implicit_threat": f"Qual diálogo parece um conselho de segurança, mas funciona como ameaça contra alguém próximo de {p}?",
            "parallel_relationship": f"Em que trecho {p} fala de promessas feitas a duas pessoas em vez de usar uma acusação direta?",
        }
        return mapping.get(spec.key, f"Qual diálogo de {p} e {q} comunica o conflito por implicação, sem declarar o fato principal?"), "O diálogo precisa ser interpretado pragmaticamente, não apenas por palavras exatas.", spec.requires_context, "hard"
    if category == "character_name":
        return f"Encontre a cena de {p} em {setting} em que {q} participa e {obj} muda o rumo da conversa.", "A consulta exige recuperar nomes próprios e contexto específico da obra.", spec.requires_context, "medium"
    if category == "exact_phrase":
        return f"Localize a frase exata: {quote}", "A consulta deve recuperar uma sequência textual literal.", spec.requires_context, "easy"
    if category == "similar_scene":
        if spec.key == "hidden_messages":
            query = f"Encontre a cena em que {q} realmente vê mensagens apagadas de {p}, não a cena posterior em que apenas reúne contradições."
        elif spec.key == "silent_cry":
            query = f"Localize o choro silencioso de {p}, não o momento em que seu silêncio é confundido com culpa."
        elif spec.key == "chase":
            query = f"Qual cena mostra {p} perseguindo {s}, e não a fuga posterior de {p} e {q} por uma saída secundária?"
        else:
            query = f"Entre cenas parecidas de {work['title']}, encontre a que corresponde a {spec.event.replace('_', ' ')}, não ao acontecimento relacionado."
        return query, "A consulta contrasta explicitamente duas cenas semanticamente próximas.", spec.requires_context, "hard"
    raise KeyError(category)


def build_queries(id_map: dict[tuple[int, str], str], quote_map: dict[tuple[int, str], str]) -> list[dict[str, Any]]:
    works = build_work_specs()
    scene_by_key = {s.key: s for s in SCENES}
    plan: list[tuple[str, int, str]] = []
    semantic_keys = ["hidden_messages", "contradiction", "parallel_relationship", "family_argument", "implicit_threat", "secret_revealed", "twist", "chase", "escape", "misunderstanding"]
    for i in range(40):
        plan.append(("semantic_event", i % 30, semantic_keys[(i * 3 + i // 30) % len(semantic_keys)]))
    context_keys = ["pronoun_reference", "distant_consequence", "sadness_guilt", "contradiction", "parallel_relationship"]
    for i in range(30):
        plan.append(("context_dependency", i % 30, context_keys[i % len(context_keys)]))
    emotion_keys = ["silent_cry", "contained_anger", "implicit_threat", "fear_surprise", "sadness_guilt"]
    for i in range(25):
        plan.append(("emotion_intention", i, emotion_keys[i % len(emotion_keys)]))
    dialogue_keys = ["indirect_apology", "indirect_confrontation", "implicit_threat", "parallel_relationship"]
    for i in range(20):
        plan.append(("indirect_dialogue", i, dialogue_keys[i % len(dialogue_keys)]))
    name_keys = ["arrival_secret", "reconciliation", "secret_revealed", "twist", "distant_consequence"]
    for i in range(15):
        plan.append(("character_name", i * 2, name_keys[i % len(name_keys)]))
    exact_keys = ["hidden_messages", "implicit_threat", "contained_anger", "reconciliation", "indirect_apology", "twist", "chase", "escape", "pronoun_reference", "distant_consequence"]
    for i in range(10):
        plan.append(("exact_phrase", (i * 13) % 30, exact_keys[i]))
    similar_keys = ["hidden_messages", "silent_cry", "chase", "parallel_relationship", "contradiction", "escape", "fear_surprise", "indirect_apology", "pronoun_reference", "family_argument"]
    for i in range(10):
        plan.append(("similar_scene", (i * 17) % 30, similar_keys[i]))
    assert len(plan) == 150

    queries = []
    for qi, (category, wi, key) in enumerate(plan, start=1):
        spec = scene_by_key[key]
        work = works[wi]
        query, rationale, requires_context, difficulty = _query_text(category, wi, spec, work, quote_map[(wi, key)], qi)
        neg_keys = RELATED_NEGATIVES[key]
        negatives = [
            id_map[(wi, neg_keys[0])],
            id_map[(wi, neg_keys[1])],
            id_map[((wi + 7) % 30, neg_keys[0])],
        ]
        relevant = [id_map[(wi, key)]]
        if category == "context_dependency" and key == "distant_consequence" and qi % 2 == 0:
            relevant.append(id_map[(wi, "pronoun_reference")])
            negatives = [n for n in negatives if n not in relevant]
        queries.append({
            "query_id": f"query-{qi:04d}",
            "query": query,
            "relevant_chunk_ids": relevant,
            "hard_negative_chunk_ids": negatives,
            "query_type": category,
            "difficulty": difficulty,
            "requires_context": requires_context,
            "expected_rationale": rationale,
        })
    return queries
