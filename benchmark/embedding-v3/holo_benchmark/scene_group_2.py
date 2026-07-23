from __future__ import annotations


def scene_group_2(key: str, p: str, q: str, r: str, s: str, setting: str, obj: str, idx: int):
    v = idx % 4
    exact = ""
    if key == "silent_cry":
        exact = f"{q} sussurrou: “Você não precisa explicar agora.”"
        lines = [
            f"{p} permaneceu perto de uma janela de {setting}, organizando {obj} várias vezes sem necessidade.",
            f"Quando {q} mencionou uma ausência recente, {p} continuou a tarefa e apenas diminuiu o ritmo.",
            f"Uma lágrima caiu sobre a superfície do objeto; {p} limpou a marca antes que {r} se aproximasse.",
            exact,
            f"{p} confirmou com a cabeça, incapaz de responder sem alterar a respiração.",
            f"{s} entrou falando de outro assunto e percebeu tarde demais que o grupo estava em silêncio.",
            f"Ninguém abraçou {p} imediatamente; a proximidade foi construída aos poucos, respeitando a recusa em falar.",
            f"O choro não virou discurso e, justamente por isso, deixou claro o tamanho da perda.",
        ]
    elif key == "implicit_threat":
        exact = f"{q} disse: “Seria uma pena se alguém confundisse o caminho que sua irmã faz todos os dias.”"
        lines = [
            f"{q} encontrou {p} em {setting} e iniciou a conversa como se oferecesse um conselho.",
            f"Ele colocou {obj} entre os dois e citou detalhes da rotina de uma pessoa próxima a {p}.",
            exact,
            f"O tom permaneceu cordial, mas a informação não tinha relação com o assunto aparente.",
            f"{p} perguntou se aquilo era uma ameaça; {q} sorriu e disse que apenas se preocupava com segurança.",
            f"{r} ouviu parte da frase e tentou atribuí-la a um mal-entendido.",
            f"{s} percebeu que {q} escolhera um lugar público justamente para poder negar a intenção.",
            f"{p} saiu sem responder, entendendo que a mensagem dependia menos das palavras do que do conhecimento demonstrado.",
        ]
    elif key == "contained_anger":
        exact = f"{p} falou baixo: “Repita isso olhando para mim.”"
        lines = [
            f"{q} apresentou uma decisão já tomada e pediu que {p} apenas confirmasse diante dos demais.",
            f"{p} alinhou {obj} com a borda da mesa, corrigindo a posição toda vez que {q} falava.",
            f"Em {setting}, o barulho ao redor permitia esconder a mudança na respiração.",
            exact,
            f"{q} tentou rir, mas {p} apertou os dedos até as juntas perderem a cor.",
            f"{r} propôs uma pausa e recebeu de {p} um gesto curto, sem qualquer aumento de voz.",
            f"{s} percebeu que a calma era deliberada e afastou os objetos frágeis do alcance.",
            f"A raiva apareceu no controle excessivo, não em gritos, e tornou a resposta seguinte ainda mais incisiva.",
        ]
    elif key == "indirect_confrontation":
        exact = f"{p} perguntou: “Há quanto tempo você chama isso de coincidência?”"
        lines = [
            f"{p} espalhou sobre a mesa três registros ligados a {q}, sem explicar como os obtivera.",
            f"Cada registro isolado poderia ser casual, mas todos apontavam para o mesmo horário em {setting}.",
            f"{q} comentou que muita gente usava {obj} e tentou deslocar a conversa para outra pessoa.",
            exact,
            f"{r} percebeu que a pergunta continha uma acusação, embora nenhum comportamento fosse nomeado.",
            f"{s} pediu que {p} fosse direto; ela respondeu que preferia ouvir a versão de {q} antes de completar a frase.",
            f"{q} negou apenas os detalhes menores e deixou sem resposta a relação entre os registros.",
            f"O confronto permaneceu indireto, obrigando cada pessoa a reconhecer por conta própria o fato evitado.",
        ]
    elif key == "reconciliation":
        exact = f"{q} disse: “Podemos começar pelo que ainda conseguimos fazer direito.”"
        lines = [
            f"{p} chegou primeiro a {setting} e deixou {obj} em um lugar visível, como sinal de que não pretendia fugir.",
            f"{q} manteve distância e perguntou se a conversa teria novas acusações.",
            f"{p} reconheceu uma parte concreta do dano sem pedir que tudo fosse esquecido.",
            exact,
            f"{r} sugeriu um acordo pequeno: uma tarefa compartilhada durante a semana seguinte.",
            f"{s} lembrou que confiança não voltaria por promessa e pediu formas de verificar o combinado.",
            f"{p} aceitou as condições sem negociar o prazo, o que surpreendeu {q}.",
            f"A reconciliação não apagou o conflito; criou apenas um primeiro procedimento para que a relação pudesse continuar.",
        ]
    else:
        return None
    return lines, exact
