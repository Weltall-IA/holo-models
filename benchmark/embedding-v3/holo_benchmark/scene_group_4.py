from __future__ import annotations


def scene_group_4(key: str, p: str, q: str, r: str, s: str, setting: str, obj: str, idx: int):
    v = idx % 4
    exact = ""
    if key == "misunderstanding":
        exact = f"{r} perguntou: “Então ninguém aqui é o fotógrafo contratado?”"
        lines = [
            f"{p} chegou a {setting} procurando uma pessoa descrita apenas por carregar {obj}.",
            f"{q}, que segurava um objeto parecido, acreditou que {p} fosse o técnico chamado para resolver outro problema.",
            f"Os dois conversaram por vários minutos, cada um respondendo a perguntas sobre tarefas diferentes.",
            exact,
            f"{s} apareceu com o verdadeiro profissional e percebeu que os enganos se encaixavam de modo quase perfeito.",
            f"{p} havia autorizado mudanças numa sala que nem sequer pertencia ao evento correto.",
            f"{q} entregara instruções confidenciais a alguém que apenas buscava uma encomenda.",
            f"O mal-entendido terminou em riso constrangido, seguido por uma corrida para desfazer as decisões tomadas.",
        ]
    elif key == "fear_surprise":
        exact = f"{q} perguntou: “Você está com medo de mim ou só não esperava me ver?”"
        lines = [
            f"{q} surgiu sem aviso em {setting}, segurando {obj} que todos julgavam perdido.",
            f"{p} recuou, derrubou uma cadeira e levou a mão ao bolso antes de reconhecer o rosto.",
            exact,
            f"{p} disse que fora apenas surpresa, mas continuou observando as saídas do ambiente.",
            f"{r} interpretou a reação como culpa e fez uma pergunta sobre a noite anterior.",
            f"{s} lembrou que {p} já vinha recebendo mensagens ameaçadoras, oferecendo outra explicação para o susto.",
            f"A chegada de {q} era inesperada, porém o medo de {p} parecia dirigido a algo que viera junto com ele.",
            f"A cena preservou a ambiguidade entre surpresa legítima e receio de uma consequência conhecida.",
        ]
    elif key == "sadness_guilt":
        exact = f"{p} disse: “Eu não estou escondendo culpa; estou tentando não transformar saudade em espetáculo.”"
        lines = [
            f"{p} evitou a homenagem realizada em {setting} e ficou sozinho com {obj}.",
            f"{q} interpretou a ausência como sinal de responsabilidade pelo acontecimento recente.",
            f"{r} mencionou uma decisão antiga de {p}, ligando silêncio e culpa sem apresentar prova.",
            exact,
            f"{s} contou que {p} repetia o mesmo ritual desde antes do conflito, sempre que sentia falta de alguém.",
            f"{q} percebeu que havia confundido incapacidade de falar com tentativa de esconder participação.",
            f"A tristeza de {p} não eliminava todas as dúvidas, mas mudava o sentido dos gestos observados.",
            f"O grupo deixou de tratar o silêncio como confissão automática.",
        ]
    elif key == "pronoun_reference":
        exact = f"{p} disse apenas: “Foi por causa daquilo, e você sabe.”"
        lines = [
            f"{p} e {q} retomaram uma conversa interrompida semanas antes, diante de {obj} em {setting}.",
            f"Nenhum dos dois nomeou a decisão central; usaram pronomes e referências a horários já conhecidos.",
            exact,
            f"{r}, que não presenciara o episódio anterior, acreditou que falavam de uma viagem.",
            f"{s} entendeu que “aquilo” se referia ao acordo secreto feito depois da discussão familiar.",
            f"{q} respondeu que a consequência não poderia ser atribuída a uma única escolha.",
            f"O sentido da conversa dependia de conectar a expressão vaga a uma cena anterior do episódio.",
            f"Sem esse contexto, as frases pareciam neutras; com ele, tornavam-se uma acusação precisa.",
        ]
    elif key == "distant_consequence":
        exact = f"{q} concluiu: “A decisão de meses atrás chegou aqui antes de nós.”"
        lines = [
            f"Uma mudança inesperada em {setting} obrigou {p} e {q} a rever um acordo feito muito antes.",
            f"{obj} apareceu registrado em nome de outra pessoa, consequência de um formulário assinado na primeira semana.",
            f"{r} lembrou que todos haviam tratado aquela assinatura como formalidade sem efeito.",
            exact,
            f"{s} mostrou que o registro impedira uma transferência recente e alterara o destino de recursos.",
            f"{p} tentou corrigir o documento imediatamente, mas o prazo administrativo já havia terminado.",
            f"A pergunta principal deixou de ser quem assinara e passou a ser quem alertara sobre o risco e fora ignorado.",
            f"A cena localizou uma consequência distante, conectando uma escolha antiga ao problema atual.",
        ]
    else:
        return None
    return lines, exact
