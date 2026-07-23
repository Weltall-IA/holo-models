from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

OPENERS = [
    "A movimentação habitual tornou difícil perceber de imediato que algo estava fora do lugar.",
    "O encontro começou como uma tarefa simples, mas cada pessoa chegou com uma versão diferente do dia.",
    "Ninguém levantou a voz no início; o desconforto apareceu nos intervalos entre uma resposta e outra.",
    "A cena se desenvolveu em meio a ruídos cotidianos, o que obrigou os personagens a observar gestos pequenos.",
    "O assunto parecia prático até que um detalhe antigo voltou à conversa.",
    "A rotina do lugar continuou ao redor deles, indiferente ao impasse que se formava.",
    "Uma decisão aparentemente banal abriu espaço para perguntas que vinham sendo adiadas.",
    "O grupo tentou manter a conversa objetiva, embora todos soubessem que havia outra questão em jogo.",
    "A presença de outras pessoas impediu uma discussão direta e tornou cada frase mais calculada.",
    "O clima mudou antes que alguém explicasse por quê; bastou um objeto aparecer no momento errado.",
    "A conversa começou tarde, quando o cansaço já tornava mais difícil sustentar versões ensaiadas.",
    "Um compromisso comum reuniu pessoas que evitavam ficar no mesmo ambiente havia semanas.",
    "A princípio, todos trataram o encontro como coincidência, mas os olhares indicavam preparação.",
    "O silêncio do lugar fez com que passos, notificações e respirações ganhassem importância.",
    "Uma lembrança compartilhada parecia unir o grupo, até revelar que cada um guardava uma parte diferente.",
    "O ambiente oferecia poucas saídas e obrigava todos a permanecer perto do problema.",
    "O que deveria durar poucos minutos se alongou porque ninguém queria formular a pergunta principal.",
    "A conversa foi interrompida várias vezes, e cada retorno trouxe uma informação mais difícil de ignorar.",
    "O encontro ocorreu diante de testemunhas ocasionais, por isso os conflitos apareceram em códigos.",
    "A situação parecia controlada, mas pequenas contradições acumulavam pressão.",
]

CLOSERS = [
    "Quando se separaram, ninguém declarou uma decisão, mas o equilíbrio entre eles já havia mudado.",
    "O episódio terminou sem acordo, deixando uma consequência concreta para a cena seguinte.",
    "A última resposta não resolveu o conflito; apenas definiu quem passaria a desconfiar de quem.",
    "O grupo retomou a rotina, embora cada gesto posterior fosse interpretado à luz do que acabara de ocorrer.",
    "A cena encerrou com uma escolha prática que teria efeito muito além daquele ambiente.",
    "Ninguém pediu explicações adicionais, mas o silêncio passou a funcionar como uma acusação.",
    "A conversa foi encerrada por uma necessidade externa, não porque o assunto estivesse resolvido.",
    "Ao final, o objeto permaneceu sobre a mesa como prova de que a versão anterior não bastava.",
    "A saída de um dos personagens interrompeu o diálogo e tornou impossível voltar ao tom inicial.",
    "A aparente calma do encerramento contrastou com a mudança de alianças provocada pela conversa.",
]

@dataclass(frozen=True)
class SceneSpec:
    key: str
    scene_type: str
    event: str
    themes: tuple[str, ...]
    emotions: tuple[str, ...]
    requires_context: bool

SCENES = [
    SceneSpec("arrival_secret","chegada_com_segredo","chegada_suspeita",("segredo","chegada"),("mistério","cautela"),False),
    SceneSpec("hidden_messages","mensagens_escondidas","descoberta_de_mensagens",("segredo","relacionamento"),("desconfiança","choque_contido"),False),
    SceneSpec("contradiction","mentira_por_contradicao","mentira_descoberta_por_contradicao",("mentira","prova"),("tensão","desconfiança"),True),
    SceneSpec("parallel_relationship","descoberta_indireta","outro_relacionamento_descoberto",("relacionamento","segredo"),("decepção","raiva_contida"),True),
    SceneSpec("family_argument","discussao_familiar","discussao_sobre_decisao_antiga",("família","ressentimento"),("raiva","frustração"),True),
    SceneSpec("silent_cry","choro_silencioso","choro_sem_explicacao",("perda","silêncio"),("tristeza","contenção"),True),
    SceneSpec("implicit_threat","ameaca_implicita","ameaca_disfarcada_de_conselho",("poder","medo"),("ameaça","apreensão"),False),
    SceneSpec("contained_anger","raiva_contida","raiva_expressa_por_gestos",("conflito","controle"),("raiva_contida","humilhação"),False),
    SceneSpec("indirect_confrontation","confronto_indireto","acusacao_sem_nomear_o_fato",("segredo","confronto"),("desconfiança","tensão"),True),
    SceneSpec("reconciliation","reconciliacao","reaproximacao_cautelosa",("afeto","confiança"),("alívio","esperança"),True),
    SceneSpec("indirect_apology","pedido_de_perdao_indireto","desculpa_por_acao",("culpa","reparação"),("culpa","ternura"),True),
    SceneSpec("secret_revealed","segredo_revelado","verdade_antiga_revelada",("segredo","família"),("choque","alívio"),True),
    SceneSpec("twist","reviravolta","aliado_revelado_como_autor",("mistério","prova"),("surpresa","traição"),True),
    SceneSpec("chase","perseguicao","perseguicao_a_pe",("perigo","urgência"),("medo","determinação"),False),
    SceneSpec("escape","fuga","fuga_por_saida_secundaria",("perigo","liberdade"),("pânico","alívio"),True),
    SceneSpec("misunderstanding","humor_por_mal_entendido","confusao_de_identidade",("humor","equívoco"),("embaraço","diversão"),False),
    SceneSpec("fear_surprise","medo_confundido_com_surpresa","reacao_ambigua_a_chegada",("percepção","equívoco"),("medo","surpresa"),False),
    SceneSpec("sadness_guilt","tristeza_confundida_com_culpa","silencio_mal_interpretado",("perda","culpa"),("tristeza","culpa_aparente"),True),
    SceneSpec("pronoun_reference","referencia_por_pronome","decisao_referida_sem_nome",("memória","consequência"),("ansiedade","dúvida"),True),
    SceneSpec("distant_consequence","consequencia_distante","efeito_de_decisao_anterior",("consequência","tempo"),("arrependimento","aceitação"),True),
]

RELATED_NEGATIVES = {
    "arrival_secret": ("hidden_messages","contradiction"),
    "hidden_messages": ("contradiction","indirect_confrontation"),
    "contradiction": ("hidden_messages","indirect_confrontation"),
    "parallel_relationship": ("hidden_messages","reconciliation"),
    "family_argument": ("contained_anger","reconciliation"),
    "silent_cry": ("sadness_guilt","indirect_apology"),
    "implicit_threat": ("contained_anger","indirect_confrontation"),
    "contained_anger": ("family_argument","implicit_threat"),
    "indirect_confrontation": ("contradiction","parallel_relationship"),
    "reconciliation": ("indirect_apology","family_argument"),
    "indirect_apology": ("reconciliation","sadness_guilt"),
    "secret_revealed": ("twist","contradiction"),
    "twist": ("secret_revealed","parallel_relationship"),
    "chase": ("escape","fear_surprise"),
    "escape": ("chase","arrival_secret"),
    "misunderstanding": ("fear_surprise","pronoun_reference"),
    "fear_surprise": ("misunderstanding","implicit_threat"),
    "sadness_guilt": ("silent_cry","indirect_apology"),
    "pronoun_reference": ("distant_consequence","secret_revealed"),
    "distant_consequence": ("pronoun_reference","family_argument"),
}

def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")

def regex_tokens(text: str) -> list[str]:
    return re.findall(r"\b[\wÀ-ÿ'-]+\b", text, flags=re.UNICODE)

def _choice(seq: list[str] | tuple[str, ...], idx: int, salt: int = 0) -> str:
    return seq[(idx * 7 + salt * 11) % len(seq)]
