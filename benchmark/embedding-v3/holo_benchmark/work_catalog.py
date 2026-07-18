from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

SCHEMA_VERSION = "1.0"
CORPUS_VERSION = "holo_fake_scenes_v3"
SEED = 20260718

TITLES = [
    "A Rua dos Guarda-Chuvas", "Depois da Última Balsa", "O Quarto de Azulejos",
    "Cartas para o Cerrado", "A Janela do Observatório", "A Padaria das Seis",
    "O Som do Elevador", "Linha de Costura", "A Ponte das Mangueiras",
    "Retratos de Domingo", "A Casa do Relógio Azul", "Entre Duas Estações",
    "O Arquivo de Vidro", "A Praça sem Coreto", "A Oficina do Vento",
    "Noite no Mercado Velho", "A Chave do Apartamento 12", "O Jardim de Concreto",
    "A Última Sessão", "Caderno de Marés", "O Prédio das Persianas", "Vozes da Rodoviária",
    "A Cidade Depois da Chuva", "Um Café Antes do Norte", "O Mapa na Gaveta",
    "As Luzes do Viaduto", "A Varanda de Outubro", "O Sino da Escola Antiga",
    "Bilhetes no Parapeito", "A Estrada das Goiabeiras",
]

SETTINGS = [
    "uma galeria comercial antiga no centro de Goiânia",
    "o pequeno terminal de balsas de uma cidade ribeirinha",
    "uma pensão reformada com corredores de azulejos verdes",
    "uma fazenda de pesquisa cercada pelo cerrado",
    "um observatório municipal quase sempre vazio",
    "uma padaria de bairro que abre antes do amanhecer",
    "um edifício comercial com elevadores barulhentos",
    "um ateliê de costura instalado nos fundos de uma loja",
    "uma ponte estreita cercada por mangueiras antigas",
    "uma casa de família usada para almoços de domingo",
    "um casarão cujo relógio da sala atrasa sete minutos",
    "uma estação ferroviária desativada e uma rodoviária nova",
    "um arquivo municipal com divisórias de vidro",
    "uma praça reformada onde o coreto foi removido",
    "uma oficina mecânica aberta para a rua",
    "um mercado coberto que funciona até tarde",
    "um condomínio antigo com corredores muito iguais",
    "um jardim interno entre torres de concreto",
    "um cinema de rua prestes a fechar",
    "uma vila costeira marcada por mudanças de maré",
    "um prédio administrativo com persianas sempre fechadas",
    "uma rodoviária interestadual em horário de pico",
    "um bairro baixo que alaga depois de temporais",
    "um café ao lado de uma estrada para o norte",
    "uma biblioteca comunitária com mapas guardados em gavetas",
    "um viaduto iluminado por letreiros de lojas",
    "uma casa com varanda voltada para um pomar",
    "uma escola pública construída no início do século passado",
    "um conjunto de apartamentos com parapeitos baixos",
    "uma estrada rural cercada por goiabeiras",
]

OBJECTS = [
    "um guarda-chuva amarelo", "um bilhete de embarque", "uma caixa de fotografias",
    "um caderno de campo", "uma lente rachada", "um saco de pão ainda quente",
    "um cartão magnético", "uma fita métrica azul", "uma chave enferrujada",
    "um porta-retrato de madeira", "um relógio de bolso", "uma passagem sem data",
    "uma pasta transparente", "uma placa retirada do coreto", "uma nota fiscal amassada",
    "uma sacola de temperos", "um chaveiro com o número 12", "uma muda de jabuticaba",
    "um rolo de filme", "uma bússola de latão", "um envelope pardo", "uma etiqueta de bagagem",
    "uma lanterna recarregável", "uma xícara lascada", "um mapa dobrado",
    "um crachá vencido", "uma manta bordada", "um sino pequeno", "um vaso de manjericão",
    "uma caixa de goiabada",
]

NAMES = [
    "Lívia","Renato","Marta","Caio","Miguel","Rosa","Davi","Nina","Camila","Breno","Yara","Otávio",
    "Teresa","Gustavo","Íris","Leandro","Helena","Rafael","Joana","Samuel","Bianca","Heitor","Célia","Murilo",
    "Alice","Tomás","Vera","Noel","Sofia","Vicente","Lara","André","Marina","Fábio","Clarice","Jonas",
    "Elisa","Rogério","Mônica","Artur","Beatriz","Hugo","Lorena","César","Isadora","Nélio","Paula","Raul",
    "Daniela","Márcio","Sueli","Gael","Carolina","Elias","Denise","Bruno","Talita","Augusto","Rita","Pedro",
    "Aline","Cauê","Glória","Edson","Mirela","Danilo","Neide","Thiago","Valéria","Ivo","Natália","Marcos",
    "Amanda","Sílvio","Letícia","Ramon","Júlia","Vítor","Noemi","Álvaro","Luana","Ernesto","Pietra","Gilberto",
    "Débora","Cristiano","Madalena","Enzo","Priscila","Lúcio","Ester","Roberto","Maíra","Fernando","Selma","Ítalo",
    "Rebeca","Nelson","Cíntia","Alex","Malu","Adriano","Kátia","Wesley","Olívia","Sérgio","Jandira","Mateus",
    "Flávia","Celso","Raquel","Douglas","Tainá","Beto","Luzia","Renan","Patrícia","Afonso","Simone","Kleber",
]

WORK_PRESSURES = [
    "precisava decidir se renovaria o aluguel da loja sem consultar a família",
    "aguardava uma resposta sobre a venda de uma embarcação herdada",
    "tentava provar que uma reforma havia sido paga com recursos próprios",
    "disputava a autoria de uma pesquisa que seria apresentada na capital",
    "escondia que perdera acesso ao equipamento principal do trabalho",
    "cobria turnos extras depois do afastamento inesperado de uma colega",
    "investigava cobranças feitas com um cartão que deveria estar bloqueado",
    "tentava concluir uma encomenda importante antes de uma fiscalização",
    "negociava a divisão de uma propriedade que ninguém queria abandonar",
    "organizava documentos para um inventário familiar atrasado",
    "procurava a origem de depósitos feitos em nome de uma pessoa falecida",
    "avaliava uma proposta de mudança que separaria o grupo por meses",
    "respondia a uma sindicância baseada em papéis que pareciam incompletos",
    "tentava impedir que a reforma apagasse marcas importantes da comunidade",
    "precisava explicar por que peças novas apareciam em ordens antigas",
    "administrava dívidas de fornecedores sem revelar a extensão do problema",
    "tentava descobrir quem usara sua chave durante uma madrugada",
    "defendia um projeto coletivo ameaçado por uma decisão do condomínio",
    "buscava preservar o acervo antes do fechamento definitivo do espaço",
    "avaliava se deixaria a vila depois de uma temporada de trabalho ruim",
    "reunia provas de que relatórios haviam sido alterados depois de assinados",
    "tentava localizar uma bagagem que continha documentos de outra pessoa",
    "coordenava reparos após uma enchente e desconfiava das notas apresentadas",
    "planejava uma viagem longa sem contar que não pretendia voltar",
    "organizava uma exposição baseada em mapas encontrados sem identificação",
    "negociava um contrato cuja última página fora substituída",
    "decidia se venderia o pomar para pagar um tratamento",
    "tentava preservar registros escolares que desapareceriam numa mudança",
    "acompanhava uma disputa entre vizinhos sobre objetos lançados das janelas",
    "procurava a origem de uma encomenda entregue no quilômetro errado",
]

LOCAL_DETAILS = [
    "As vitrines refletiam pessoas de corredores diferentes, criando a impressão de que alguém sempre observava de longe.",
    "O motor da balsa era ouvido antes de cada chegada, marcando intervalos que todos usavam para conferir horários.",
    "A umidade dos corredores deixava pegadas visíveis e dificultava negar quem passara por determinada porta.",
    "O vento carregava poeira vermelha para dentro das salas e cobria rapidamente objetos deixados sem proteção.",
    "A cúpula rangia quando mudava de posição, interrompendo conversas sempre no ponto mais delicado.",
    "O cheiro de fermento e o som das assadeiras faziam clientes entrar e sair sem perceber o conflito no balcão.",
    "Cada parada do elevador acendia uma luz diferente, permitindo reconstruir deslocamentos pelo painel antigo.",
    "Retalhos presos à roupa denunciavam quem havia passado pelo ateliê mesmo depois de sair pela porta dos fundos.",
    "Frutas maduras caíam sobre o asfalto e obrigavam os carros a reduzir, tornando qualquer perseguição irregular.",
    "Fotografias de décadas diferentes ocupavam a mesma parede e contradiziam lembranças repetidas como certezas.",
    "O tique-taque atrasado confundia quem tentava usar o relógio da sala para confirmar uma versão.",
    "Anúncios da rodoviária atravessavam o prédio vazio da estação e embaralhavam nomes de destinos.",
    "As divisórias transparentes permitiam ver movimentos sem ouvir as conversas que os explicavam.",
    "O espaço onde existira o coreto permanecia marcado no piso, embora todos discutissem quem autorizara a retirada.",
    "Ferramentas penduradas lançavam sombras parecidas e faziam pequenos objetos desaparecerem à primeira vista.",
    "Feirantes fechavam as bancas em horários distintos, oferecendo testemunhas parciais para o mesmo acontecimento.",
    "As portas numeradas repetiam o mesmo desenho, e visitantes frequentemente seguiam para o apartamento errado.",
    "O sistema de irrigação ligava sem aviso e obrigava o grupo a mudar de lugar no meio das conversas.",
    "A luz do projetor falhava em intervalos regulares, escondendo movimentos por poucos segundos.",
    "As tábuas do cais indicavam pela umidade até onde a água chegara na noite anterior.",
    "As persianas impediam ver o interior, mas suas posições revelavam quais salas haviam sido usadas.",
    "Etiquetas arrancadas acumulavam-se perto dos guichês e permitiam associar malas a horários específicos.",
    "Marcas de lama secavam em tons diferentes, ajudando a distinguir passagens feitas antes e depois da chuva.",
    "Caminhões diminuíam a velocidade na curva e abafavam frases curtas pronunciadas junto à janela.",
    "Os mapas tinham anotações de mãos diferentes, algumas recentes e outras quase apagadas.",
    "Letreiros piscavam em sequências irregulares e alteravam a visibilidade sob o viaduto.",
    "O vento movia a manta sobre a cadeira e revelava objetos que alguém tentara cobrir às pressas.",
    "O sino podia ser ouvido de todos os corredores, servindo como referência comum para os horários.",
    "Vasos alinhados nos parapeitos mostravam quais apartamentos estavam ocupados apesar das luzes apagadas.",
    "O cheiro das frutas maduras permanecia nas caixas e denunciava de onde uma encomenda havia saído.",
]

