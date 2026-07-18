from __future__ import annotations


def scene_group_1(key: str, p: str, q: str, r: str, s: str, setting: str, obj: str, idx: int):
    v = idx % 4
    exact = ""
    if key == "arrival_secret":
        exact = f"{p} disse: “Eu só precisava chegar antes de vocês.”"
        lines = [
            f"{p} apareceu em {setting} carregando {obj}, embora tivesse dito que viria sem bagagem.",
            f"{q} ofereceu ajuda e percebeu que o objeto estava marcado com uma data posterior à viagem anunciada.",
            f"{r} perguntou por que {p} descera duas quadras antes, mas recebeu uma explicação vaga sobre trânsito.",
            exact,
            f"{s} reconheceu no objeto um sinal ligado a uma pessoa que {p} afirmava não conhecer.",
            f"Em vez de confrontá-la, {q} guardou a informação e mudou a conversa para o horário da chegada.",
            f"A resposta de {p} veio rápida demais e não combinou com o bilhete encontrado no bolso externo.",
            f"O segredo ainda não foi nomeado, porém a chegada deixou de parecer casual.",
        ]
    elif key == "hidden_messages":
        exact = f"{q} perguntou: “Por que essa conversa precisava desaparecer?”"
        lines = [
            f"Enquanto procurava uma fotografia no celular de {p}, {q} viu uma notificação com um apelido desconhecido.",
            f"{p} tomou o aparelho de volta e apagou a conversa antes que a tela bloqueasse.",
            f"Mais tarde, {r} mostrou uma captura enviada por engano, com horários e a promessa de um encontro em {setting}.",
            exact,
            f"{p} chamou tudo de assunto profissional, mas não explicou por que o contato estava salvo apenas com uma inicial.",
            f"{s} tentou encerrar o assunto e acabou revelando que já sabia das mensagens.",
            f"{q} não usou a palavra que todos evitavam; comparou as datas e percebeu que havia uma história paralela.",
            f"O celular permaneceu virado para baixo, como se a posição pudesse esconder o conteúdo já visto.",
        ]
    elif key == "contradiction":
        exact = f"{r} comentou: “Eu só cheguei depois das oito.”"
        lines = [
            f"{q} repetiu que passara a tarde inteira com {r}, resolvendo uma tarefa em {setting}.",
            exact,
            f"A observação contradisse o horário apresentado por {q} poucos minutos antes.",
            f"{p} pediu que ele narrasse novamente o caminho e anotou cada parada ao lado de {obj}.",
            f"Na segunda versão, surgiram um recibo e uma ligação que não existiam na primeira.",
            f"{s} atribuiu a diferença ao cansaço, mas {p} colocou sobre a mesa um comprovante do começo da tarde.",
            f"A mentira não apareceu em uma confissão; formou-se pelo acúmulo de detalhes incompatíveis.",
            f"{q} percebeu que qualquer nova explicação aumentaria o problema e deixou a frase pela metade.",
        ]
    elif key == "parallel_relationship":
        exact = f"{p} disse: “Você prometeu o mesmo futuro para duas pessoas.”"
        lines = [
            f"{p} reuniu mensagens, fotografias e reservas feitas por {q} em semanas nas quais ele dizia estar trabalhando.",
            f"Os registros mencionavam {setting} e repetiam um apelido usado apenas em conversas íntimas.",
            f"{r} confirmou que vira {q} acompanhado, mas acreditara tratar-se de uma parente.",
            exact,
            f"{q} tentou discutir a origem das provas em vez de explicar o conteúdo.",
            f"{s} percebeu que as mesmas desculpas haviam sido apresentadas a pessoas diferentes.",
            f"{p} não pediu uma confissão; organizou os horários e perguntou desde quando as duas histórias coexistiam.",
            f"A descoberta ocorreu sem a palavra mais óbvia, sustentada pelas promessas duplicadas e pelos encontros escondidos.",
        ]
    elif key == "family_argument":
        exact = f"{r} afirmou: “Não estamos discutindo a venda; estamos discutindo quem sempre decide.”"
        lines = [
            f"A família se reuniu para decidir o destino de {obj}, guardado havia anos em {setting}.",
            f"{p} propôs vender, enquanto {q} defendia que o objeto pertencia à memória de todos.",
            f"Uma conta recente transformou a conversa prática em disputa sobre responsabilidades antigas.",
            exact,
            f"{s} lembrou uma promessa feita no hospital e acusou os demais de citá-la apenas quando era conveniente.",
            f"{p} respondeu com outro episódio, de muitos anos antes, que ninguém julgava encerrado.",
            f"Os argumentos passaram do valor do objeto para a distribuição desigual de cuidado dentro da família.",
            f"A decisão foi adiada porque qualquer escolha passou a significar reconhecimento ou negação dos ressentimentos.",
        ]
    else:
        return None
    return lines, exact
