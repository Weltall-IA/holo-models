from __future__ import annotations


def scene_group_3(key: str, p: str, q: str, r: str, s: str, setting: str, obj: str, idx: int):
    v = idx % 4
    exact = ""
    if key == "indirect_apology":
        exact = f"{p} disse: “Deixei tudo como você precisava, mesmo sem saber se vai querer voltar.”"
        lines = [
            f"{p} entrou em {setting} antes dos demais e consertou o dano causado na discussão anterior.",
            f"Ele limpou {obj}, reuniu documentos dispersos e refez uma tarefa que havia recusado por orgulho.",
            f"Quando {q} chegou, {p} não usou a palavra desculpa nem pediu resposta imediata.",
            exact,
            f"{q} observou as mudanças e perguntou por que aquilo não fora feito antes.",
            f"{p} respondeu que havia entendido tarde demais o peso de sua ausência.",
            f"{r} tentou transformar o gesto em reconciliação completa, mas {q} pediu tempo.",
            f"O pedido de perdão foi transmitido pelas ações e pela disposição de reparar sem garantia de recompensa.",
        ]
    elif key == "secret_revealed":
        exact = f"{r} afirmou: “O nome no documento é meu, mas a história não começou comigo.”"
        lines = [
            f"Uma discussão sobre {obj} levou {r} a abrir uma pasta guardada fora de vista em {setting}.",
            f"Os documentos mostravam que uma decisão atribuída a {p} fora tomada anos antes por outra pessoa.",
            f"{q} reconheceu uma assinatura e percebeu que a família construíra várias versões para proteger {s}.",
            exact,
            f"{s} pediu que a leitura parasse, confirmando sem querer a importância do material.",
            f"{p} releu as datas e entendeu por que determinadas lembranças nunca se encaixavam.",
            f"O segredo revelado explicava silêncios antigos, mas também retirava de alguns personagens a desculpa da ignorância.",
            f"Ninguém soube se a verdade aproximaria a família ou apenas mudaria o alvo do ressentimento.",
        ]
    elif key == "twist":
        exact = f"{s} confessou: “Eu ajudei vocês a procurar porque sabia onde nunca encontrariam.”"
        lines = [
            f"{p}, {q} e {r} compararam pistas sobre o desaparecimento de {obj} em {setting}.",
            f"Todas as evidências pareciam apontar para uma pessoa ausente, defendida desde o início por {s}.",
            f"Uma marca no objeto recuperado correspondia a uma ferramenta que apenas {s} utilizava.",
            exact,
            f"{q} lembrou que os melhores indícios haviam sido sugeridos pelo próprio {s}.",
            f"{s} admitiu ter conduzido a busca para locais seguros, esperando que o tempo apagasse outras provas.",
            f"A revelação transformou o aliado mais prestativo no autor da distração.",
            f"A reviravolta não dependia de uma nova personagem, mas de reinterpretar ações vistas como ajuda.",
        ]
    elif key == "chase":
        exact = f"{p} gritou: “Não deixe que ele atravesse a saída principal!”"
        lines = [
            f"{q} viu {s} recolher {obj} e correr por {setting} antes que alguém pudesse bloqueá-lo.",
            f"{p} seguiu pela passagem central, enquanto {r} tentou antecipar o caminho por uma lateral.",
            exact,
            f"O fluxo de pessoas obrigou {p} a escolher entre manter contato visual e evitar derrubar quem passava.",
            f"{s} mudou de direção duas vezes e usou uma porta de serviço que parecia trancada.",
            f"{q} acompanhou a perseguição à distância, transmitindo referências do ambiente pelo telefone.",
            f"{r} quase alcançou {s}, mas precisou parar quando um carrinho atravessou o corredor.",
            f"A perseguição terminou sem captura imediata, porém revelou qual saída seria usada na fuga seguinte.",
        ]
    elif key == "escape":
        exact = f"{p} disse: “Quando a luz apagar, conte até cinco e não olhe para trás.”"
        lines = [
            f"{p} identificou uma saída secundária de {setting} durante a confusão criada na cena anterior.",
            f"{q} guardou {obj} sob a roupa e verificou se {s} continuava perto da entrada principal.",
            exact,
            f"{r} desligou o quadro elétrico no horário combinado, mergulhando o corredor em escuridão curta.",
            f"{p} e {q} atravessaram uma passagem estreita sem falar, guiados pelo som externo.",
            f"Um ruído atrás deles sugeriu que o plano fora descoberto antes do previsto.",
            f"{q} hesitou ao perceber que {r} não os acompanhara, mas {p} lembrou que voltar colocaria todos em risco.",
            f"A fuga terminou do lado de fora, com alívio incompleto e a certeza de que alguém ficara para trás.",
        ]
    else:
        return None
    return lines, exact
