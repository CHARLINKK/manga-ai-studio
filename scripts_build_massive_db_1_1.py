#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador e Expansor Ultra-Massivo dos Bancos de Dados de Localização de Mangá (v1.1.0)
====================================================================================
Gera bases de dados JSON verdadeiramente monumentais para:
1. manga_dialogue_localization.json (v1.1.0) - Centenas de regras coloquiais PT-BR
2. false_cognates_en_pt.json (v1.1.0) - Centenas de falsos cognatos e armadilhas
3. sfx_database.json (v1.1.0) - Mais de 1.000 entradas exatas de SFX e onomatopeias
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build_dialogue_localization_1_1():
    return {
        "description": "Banco de Dados Ultra-Massivo de Localização de Diálogo de Mangá (EN -> PT-BR Coloquial)",
        "version": "1.1.0",
        "vocatives_and_titles": {
            "tell me kid": {
                "wrong_pt": ["Fala comigo garoto", "Me fala kid", "Diga-me garoto"],
                "correct_pt": ["Diz aí, garoto", "Me fala, moleque", "Me diz uma coisa, moleque"],
                "note": "Interpelação informal a um jovem"
            },
            "tell me, kid": {
                "wrong_pt": ["Fala comigo, garoto", "Diga-me, garoto"],
                "correct_pt": ["Diz aí, garoto", "Me fala, moleque"],
                "note": "Interpelação informal a um jovem"
            },
            "hey kid": {
                "wrong_pt": ["Ei kid", "Olá garoto"],
                "correct_pt": ["Ei, moleque!", "E aí, garoto!", "Opa, moleque!"],
                "note": "Chamada informal"
            },
            "listen kid": {
                "wrong_pt": ["Ouça kid", "Escute garoto"],
                "correct_pt": ["Se liga, garoto!", "Escuta aqui, moleque!", "Presta atenção, moleque!"],
                "note": "Atenção informal/desafio"
            },
            "old man": {
                "wrong_pt": ["homem velho"],
                "correct_pt": ["coroa", "velho", "tiozão"],
                "note": "Tratamento informal para alguém mais velho"
            },
            "coach": {
                "wrong_pt": ["treinador (em contexto formal excessivo)"],
                "correct_pt": ["treinador", "mestre"],
                "note": "Tratamento esportivo/boxe"
            },
            "boss": {
                "wrong_pt": ["chefe (literal burocrático)"],
                "correct_pt": ["chefe", "patrão"],
                "note": "Tratamento respeitoso ou irônico"
            },
            "big guy": {
                "wrong_pt": ["cara grande"],
                "correct_pt": ["grandão"],
                "note": "Tratamento para homem alto/forte"
            },
            "tough guy": {
                "wrong_pt": ["cara durão"],
                "correct_pt": ["valentão", "brabão", "durão"],
                "note": "Provocação"
            },
            "little guy": {
                "wrong_pt": ["cara pequeno"],
                "correct_pt": ["nanico", "baixinho"],
                "note": "Provocação por estatura"
            },
            "bastard": {
                "wrong_pt": ["bastardo (em contexto de xingamento)"],
                "correct_pt": ["desgraçado", "maldito", "filho da mãe", "canalha"],
                "note": "Xingamento comum em mangá"
            },
            "son of a bitch": {
                "wrong_pt": ["filho de uma cadela"],
                "correct_pt": ["filho da puta", "desgraçado"],
                "note": "Xingamento pesado"
            },
            "punk": {
                "wrong_pt": ["punk (estilo musical)"],
                "correct_pt": ["pirralho", "moleque", "otário", "merdinha"],
                "note": "Provocação de rua"
            },
            "brat": {
                "wrong_pt": ["brat"],
                "correct_pt": ["pirralho", "pestinha", "mimado"],
                "note": "Criança ou jovem imaturo"
            },
            "rookie": {
                "wrong_pt": ["recruta"],
                "correct_pt": ["novato", "iniciante", "cabaço"],
                "note": "Alguém sem experiência"
            },
            "champion": {
                "wrong_pt": ["campeão (se formal demais)"],
                "correct_pt": ["campeão"],
                "note": "Título esportivo"
            },
            "champ": {
                "wrong_pt": ["champ"],
                "correct_pt": ["campeão"],
                "note": "Tratamento informal no boxe"
            },
            "pal": {
                "wrong_pt": ["pal"],
                "correct_pt": ["parceiro", "camarada", "amigão"],
                "note": "Pode ser provocação sarcástica"
            },
            "buddy": {
                "wrong_pt": ["buddy"],
                "correct_pt": ["parceiro", "chapa", "amigão"],
                "note": "Comum em ameaças disfarçadas"
            },
            "dude": {
                "wrong_pt": ["dude"],
                "correct_pt": ["cara", "mano", "velho"],
                "note": "Gíria de camaradagem"
            },
            "bro": {
                "wrong_pt": ["bro"],
                "correct_pt": ["mano", "irmão", "parceiro"],
                "note": "Gíria informal"
            },
            "chief": {
                "wrong_pt": ["cacique"],
                "correct_pt": ["chefe", "comandante"],
                "note": "Tratamento informal"
            },
            "master": {
                "wrong_pt": ["senhor dono"],
                "correct_pt": ["mestre"],
                "note": "Tratamento a mentor marcial"
            },
            "kiddo": {
                "wrong_pt": ["kiddo"],
                "correct_pt": ["garotão", "moleque", "menino"],
                "note": "Tratamento afetuoso ou condescendente"
            },
            "coward": {
                "wrong_pt": ["covarde formal"],
                "correct_pt": ["covarde", "medroso", "frouxo"],
                "note": "Insulto de combate"
            },
            "scum": {
                "wrong_pt": ["escória formal"],
                "correct_pt": ["lixo", "escória", "verme"],
                "note": "Insulto pesado"
            },
            "trash": {
                "wrong_pt": ["lixo de rua"],
                "correct_pt": ["lixo", "escória"],
                "note": "Insulto a lutador fraco"
            },
            "monster": {
                "wrong_pt": ["monstro de fantasia se for lutador"],
                "correct_pt": ["monstro", "aberração", "fera"],
                "note": "Lutador de força sobre-humana"
            },
            "freak": {
                "wrong_pt": ["freak"],
                "correct_pt": ["aberração", "esquisitão", "monstro"],
                "note": "Insulto ou espanto"
            },
            "young master": {
                "wrong_pt": ["jovem mestre literal"],
                "correct_pt": ["jovem mestre", "patrozinho"],
                "note": "Herdeiro de clã ou família rica"
            },
            "senior": {
                "wrong_pt": ["sênior"],
                "correct_pt": ["veterano", "senpai"],
                "note": "Mais experiente"
            },
            "junior": {
                "wrong_pt": ["júnior"],
                "correct_pt": ["calouro", "novato"],
                "note": "Menos experiente"
            }
        },
        "imperatives_and_interpellations": {
            "tell me": {
                "wrong_pt": ["Diga-me", "Fala comigo"],
                "correct_pt": ["Diz aí", "Me fala", "Me diz uma coisa"],
                "note": "Pedido de informação coloquial"
            },
            "listen up": {
                "wrong_pt": ["Ouçam", "Escutem acima"],
                "correct_pt": ["Se liga", "Escuta aqui", "Prestem atenção"],
                "note": "Chamada de atenção"
            },
            "listen to me": {
                "wrong_pt": ["Ouça para mim"],
                "correct_pt": ["Me escuta", "Escuta aqui", "Se liga no que tô falando"],
                "note": "Atenção urgente"
            },
            "look here": {
                "wrong_pt": ["Olhe aqui"],
                "correct_pt": ["Olha só", "Vê bem", "Se liga"],
                "note": "Introdução de argumento ou ameaça"
            },
            "look": {
                "wrong_pt": ["Olhe"],
                "correct_pt": ["Olha só", "Vê bem", "Se liga"],
                "note": "Interjeição explicativa"
            },
            "shut up": {
                "wrong_pt": ["Cale a boca", "Feche-se"],
                "correct_pt": ["Cala a boca!", "Cala essa boca!", "Quieto!"],
                "note": "Imperativo informal"
            },
            "shut your trap": {
                "wrong_pt": ["feche sua armadilha"],
                "correct_pt": ["Cala a boca!", "Cala essa matraca!"],
                "note": "Gíria agressiva"
            },
            "come on": {
                "wrong_pt": ["Vamos lá (em contexto de desafio)"],
                "correct_pt": ["Pode vir!", "Bora!", "Vem logo!", "Cai dentro!"],
                "note": "Provocação de combate"
            },
            "bring it on": {
                "wrong_pt": ["Traga isso"],
                "correct_pt": ["Pode vir!", "Cai dentro!", "Manda ver!"],
                "note": "Desafio de luta"
            },
            "bring it": {
                "wrong_pt": ["Traga"],
                "correct_pt": ["Pode vir!", "Cai dentro!"],
                "note": "Desafio curto"
            },
            "get out of here": {
                "wrong_pt": ["Saia daqui (formal)"],
                "correct_pt": ["Cai fora!", "Dá no pé!", "Soma daqui!", "Rala!"],
                "note": "Expulsão informal"
            },
            "get lost": {
                "wrong_pt": ["Perca-se"],
                "correct_pt": ["Cai fora!", "Soma daqui!", "Desaparece!"],
                "note": "Mandando embora com raiva"
            },
            "back off": {
                "wrong_pt": ["costas fora"],
                "correct_pt": ["Recua!", "Para trás!", "Se afasta!"],
                "note": "Aviso de distância"
            },
            "stay down": {
                "wrong_pt": ["fique baixo"],
                "correct_pt": ["Fica no chão!", "Não levanta!"],
                "note": "Lutador no chão"
            },
            "hold on": {
                "wrong_pt": ["Segure em cima"],
                "correct_pt": ["Peraí!", "Espera aí!", "Calma aí!"],
                "note": "Pedido de pausa interjeitivo"
            },
            "wait up": {
                "wrong_pt": ["Espere acima"],
                "correct_pt": ["Peraí!", "Espera aí!"],
                "note": "Pedindo para esperar"
            },
            "don't mess with me": {
                "wrong_pt": ["Não bagunce comigo"],
                "correct_pt": ["Não mexe comigo!", "Não tira onda comigo!", "Nem tenta a sorte!"],
                "note": "Aviso/Ameaça"
            },
            "watch out": {
                "wrong_pt": ["Assista fora"],
                "correct_pt": ["Cuidado!", "Se liga!", "Olha lá!"],
                "note": "Alerta de perigo"
            },
            "look out": {
                "wrong_pt": ["olhe fora"],
                "correct_pt": ["Cuidado!", "Olha lá!"],
                "note": "Alerta imediato"
            },
            "get up": {
                "wrong_pt": ["Levante-se (formal)"],
                "correct_pt": ["Levanta!", "Fica de pé!", "Bora, levanta!"],
                "note": "Em luta ou queda"
            },
            "give me a break": {
                "wrong_pt": ["Me dê uma quebra"],
                "correct_pt": ["Dá um tempo!", "Me poupe!", "Fala sério!"],
                "note": "Incredulidade/irritação"
            },
            "show me what you got": {
                "wrong_pt": ["mostre-me o que você tem"],
                "correct_pt": ["Mostra do que você é capaz!", "Mostra o que sabe fazer!"],
                "note": "Provocação pré-luta"
            },
            "take this": {
                "wrong_pt": ["tome isto"],
                "correct_pt": ["Toma essa!", "Receba isso!"],
                "note": "Grito de ataque"
            },
            "eat this": {
                "wrong_pt": ["coma isto"],
                "correct_pt": ["Engole essa!", "Toma essa!"],
                "note": "Grito ao desferir golpe"
            },
            "step aside": {
                "wrong_pt": ["passo ao lado"],
                "correct_pt": ["Sai da frente!", "Abre caminho!"],
                "note": "Exigindo passagem"
            },
            "calm down": {
                "wrong_pt": ["acalme-se formal"],
                "correct_pt": ["Calma aí!", "Fica frio!", "Se acalma!"],
                "note": "Pedindo calma"
            },
            "hurry up": {
                "wrong_pt": ["apresse-se"],
                "correct_pt": ["Anda logo!", "Bora logo!", "Acelera!"],
                "note": "Apressando"
            },
            "leave me alone": {
                "wrong_pt": ["deixe-me sozinho"],
                "correct_pt": ["Me deixa em paz!", "Me erra!", "Sai do meu pé!"],
                "note": "Pedindo distância"
            }
        },
        "exclamations_and_cursing": {
            "what the hell": {
                "wrong_pt": ["O que diabos"],
                "correct_pt": ["Que merda é essa?", "Que porra é essa?", "Mas o quê?!"],
                "note": "Reação de choque/revolta"
            },
            "what the fuck": {
                "wrong_pt": ["O que diabos"],
                "correct_pt": ["Que porra é essa?", "Puta que pariu, o que é isso?", "Mas que caralho?!"],
                "note": "Choque extremo/adulto"
            },
            "are you kidding me": {
                "wrong_pt": ["Você está brincando comigo"],
                "correct_pt": ["Tá de sacanagem?", "Tá brincando?", "Tá zoando com a minha cara?"],
                "note": "Indignação informal"
            },
            "you gotta be kidding me": {
                "wrong_pt": ["Você tem que estar brincando comigo"],
                "correct_pt": ["Só pode tá de sacanagem!", "Tá de brincadeira comigo!"],
                "note": "Indignação"
            },
            "damn it": {
                "wrong_pt": ["Maldição"],
                "correct_pt": ["Merda!", "Porra!", "Droga!"],
                "note": "Frustração"
            },
            "goddamn it": {
                "wrong_pt": ["Maldito seja"],
                "correct_pt": ["Puta merda!", "Porra!", "Que merda!"],
                "note": "Frustração intensa"
            },
            "for god's sake": {
                "wrong_pt": ["Pelo bem de Deus"],
                "correct_pt": ["Pelo amor de Deus!", "Fala sério!"],
                "note": "Exasperação"
            },
            "holy shit": {
                "wrong_pt": ["Santa merda"],
                "correct_pt": ["Puta merda!", "Caralho!", "Nossa!"],
                "note": "Espanto"
            },
            "holy crap": {
                "wrong_pt": ["Santa porcaria"],
                "correct_pt": ["Caramba!", "Puta merda!", "Nossa senhora!"],
                "note": "Espanto"
            },
            "no way": {
                "wrong_pt": ["Sem caminho"],
                "correct_pt": ["Nem fodendo!", "De jeito nenhum!", "Mentira!", "Sem chance!"],
                "note": "Incredulidade ou recusa"
            },
            "who the hell": {
                "wrong_pt": ["Quem diabos"],
                "correct_pt": ["Quem caralhos...", "Quem é que...", "Que porra de pessoa..."],
                "note": "Pergunta indignada"
            },
            "why the hell": {
                "wrong_pt": ["por que diabos"],
                "correct_pt": ["Por que caralhos...", "Por que cargas d'água..."],
                "note": "Pergunta revoltada"
            },
            "where the hell": {
                "wrong_pt": ["onde diabos"],
                "correct_pt": ["Onde caralhos...", "Onde é que..."],
                "note": "Pergunta revoltada"
            },
            "son of a gun": {
                "wrong_pt": ["filho de uma arma"],
                "correct_pt": ["Filho da mãe!", "Maldito!"],
                "note": "Exclamação de espanto ou raiva leve"
            },
            "what on earth": {
                "wrong_pt": ["o que na terra"],
                "correct_pt": ["Mas o que é isso?!", "Que raios é isso?!"],
                "note": "Espanto"
            },
            "screw you": {
                "wrong_pt": ["parafuse você"],
                "correct_pt": ["Vá se ferrar!", "Vai se foder!", "Danou-se!"],
                "note": "Xingamento direto"
            },
            "fuck you": {
                "wrong_pt": ["dane-se"],
                "correct_pt": ["Vai se foder!", "Vai tomar no cu!"],
                "note": "Xingamento adulto"
            },
            "bullshit": {
                "wrong_pt": ["merda de touro"],
                "correct_pt": ["Mentira!", "Conversa fiada!", "Que besteira!"],
                "note": "Rejeitando mentira"
            }
        },
        "combat_and_boxing_slang": {
            "purse money": {
                "wrong_pt": ["dinheiro da bolsa de mulher"],
                "correct_pt": ["bolsa da luta", "prêmio da luta", "grana da bolsa"],
                "note": "Remuneração de boxe/luta"
            },
            "fight purse": {
                "wrong_pt": ["bolsa de luta"],
                "correct_pt": ["bolsa da luta", "prêmio da luta"],
                "note": "Prêmio financeiro do lutador"
            },
            "slugfest": {
                "wrong_pt": ["festa de lesmas"],
                "correct_pt": ["trocação franca", "quebra-pau", "porrada pura", "pancadaria insana"],
                "note": "Luta intensa sem guarda"
            },
            "fired up": {
                "wrong_pt": ["pegando fogo (literal)"],
                "correct_pt": ["com sangue nos olhos", "pilhado", "empolgado pra caramba"],
                "note": "Lutador animado/determinado"
            },
            "knocked out cold": {
                "wrong_pt": ["nocauteado frio"],
                "correct_pt": ["apagado", "nocauteado na hora", "dormiu no ringue"],
                "note": "Nocaute instantâneo"
            },
            "out cold": {
                "wrong_pt": ["fora frio"],
                "correct_pt": ["apagado", "desmaiado na hora"],
                "note": "Inconsciente"
            },
            "glass jaw": {
                "wrong_pt": ["mandíbula de vidro"],
                "correct_pt": ["queixo de vidro"],
                "note": "Lutador sensível a golpes no queixo"
            },
            "glass chin": {
                "wrong_pt": ["queixo de vidro literal"],
                "correct_pt": ["queixo de vidro"],
                "note": "Fragilidade no queixo"
            },
            "throw the towel": {
                "wrong_pt": ["atirar a toalha"],
                "correct_pt": ["jogar a toalha"],
                "note": "Desistir/parar a luta"
            },
            "on the ropes": {
                "wrong_pt": ["sobre as cordas"],
                "correct_pt": ["contra as cordas", "no sufoco", "em perigo"],
                "note": "Situação desfavorável no ringue"
            },
            "sucker punch": {
                "wrong_pt": ["soco de trouxa"],
                "correct_pt": ["golpe traiçoeiro", "porrada na covardia", "golpe surpresa"],
                "note": "Ataque sem aviso"
            },
            "beat the crap out of": {
                "wrong_pt": ["bater a porcaria fora"],
                "correct_pt": ["encher de porrada", "quebrar na porrada", "dar uma surra em"],
                "note": "Agressão intensa"
            },
            "beat the shit out of": {
                "wrong_pt": ["bater a merda fora"],
                "correct_pt": ["arrebentar na porrada", "encher de porrada", "moer na pancada"],
                "note": "Surra violenta"
            },
            "kick your ass": {
                "wrong_pt": ["chutar sua bunda"],
                "correct_pt": ["quebrar sua cara", "te encher de porrada", "acabar com você"],
                "note": "Ameaça comum em lutas"
            },
            "pay up": {
                "wrong_pt": ["pague acima"],
                "correct_pt": ["paga logo", "passa a grana", "paga o que deve"],
                "note": "Cobrança financeira"
            },
            "haymaker": {
                "wrong_pt": ["fazedor de feno"],
                "correct_pt": ["cruzado violentíssimo", "mata-cobra", "pancada devastadora"],
                "note": "Soco amplo e poderoso"
            },
            "upper": {
                "wrong_pt": ["superior"],
                "correct_pt": ["uppercut", "gancho de baixo pra cima"],
                "note": "Golpe de boxe"
            },
            "jab": {
                "wrong_pt": ["cutucada"],
                "correct_pt": ["jab"],
                "note": "Golpe reto rápido"
            },
            "hook": {
                "wrong_pt": ["gancho literal de pendurar"],
                "correct_pt": ["cruzado", "gancho"],
                "note": "Golpe lateral no boxe"
            },
            "southpaw": {
                "wrong_pt": ["pata do sul"],
                "correct_pt": ["canhoto"],
                "note": "Postura de lutador canhoto"
            },
            "orthodox": {
                "wrong_pt": ["ortodoxo religioso"],
                "correct_pt": ["destro (postura de boxe)"],
                "note": "Postura padrão no boxe"
            },
            "clinch": {
                "wrong_pt": ["abraço"],
                "correct_pt": ["clinch", "agarração"],
                "note": "Travamento no ringue"
            },
            "footwork": {
                "wrong_pt": ["trabalho de pés"],
                "correct_pt": ["jogo de pernas", "movimentação"],
                "note": "Agilidade nos pés"
            },
            "down for the count": {
                "wrong_pt": ["abaixo para a contagem"],
                "correct_pt": ["nocauteado", "no chão esperando a contagem"],
                "note": "Queda no ringue"
            },
            "saved by the bell": {
                "wrong_pt": ["salvo pelo sino literal"],
                "correct_pt": ["salvo pelo gongo"],
                "note": "Fim do round no momento crítico"
            },
            "in the zone": {
                "wrong_pt": ["na zona"],
                "correct_pt": ["no fluxo", "extremamente concentrado"],
                "note": "Estado de foco absoluto"
            },
            "corner": {
                "wrong_pt": ["canto qualquer"],
                "correct_pt": ["corner", "canto do ringue"],
                "note": "Equipe do lutador"
            },
            "sparring": {
                "wrong_pt": ["esparramando"],
                "correct_pt": ["sparring", "treino de luta"],
                "note": "Luta de treino"
            }
        },
        "conversational_fillers_and_questions": {
            "didja": {
                "wrong_pt": ["ouviste", "fizeste"],
                "correct_pt": ["não foi?", "né?", "ouviu?"],
                "note": "Tag question informal em PT-BR"
            },
            "didn'tcha": {
                "wrong_pt": ["não fizeste"],
                "correct_pt": ["não foi?", "né?"],
                "note": "Pergunta de confirmação informal"
            },
            "got it?": {
                "wrong_pt": ["Obtido?"],
                "correct_pt": ["Entendeu?", "Sacou?", "Pegou a visão?"],
                "note": "Verificando compreensão"
            },
            "understand?": {
                "wrong_pt": ["Entendido? (formal)"],
                "correct_pt": ["Entendeu?", "Sacou?"],
                "note": "Coloquial"
            },
            "what's up": {
                "wrong_pt": ["o que está acima"],
                "correct_pt": ["E aí?", "Beleza?", "Qual é?"],
                "note": "Saudação coloquial"
            },
            "who cares": {
                "wrong_pt": ["quem se importa (formal)"],
                "correct_pt": ["Quem se importa?", "E daí?", "Que se foda"],
                "note": "Desdém"
            },
            "so what": {
                "wrong_pt": ["então o que"],
                "correct_pt": ["E daí?", "E o que que tem?"],
                "note": "Desafio retórico"
            },
            "my bad": {
                "wrong_pt": ["meu mau"],
                "correct_pt": ["Foi mal", "Erro meu", "Vacilo meu"],
                "note": "Pedido de desculpa informal"
            },
            "big deal": {
                "wrong_pt": ["grande acordo"],
                "correct_pt": ["Grande coisa", "E daí?"],
                "note": "Ironia/desprezo"
            },
            "piece of cake": {
                "wrong_pt": ["pedaço de bolo"],
                "correct_pt": ["Moleza", "Mamão com açúcar", "Fácil demais"],
                "note": "Algo muito fácil"
            },
            "no problem": {
                "wrong_pt": ["nenhum problema formal"],
                "correct_pt": ["Sem problema", "Tranquilo", "De boa"],
                "note": "Aceitação informal"
            },
            "fair enough": {
                "wrong_pt": ["justo o suficiente"],
                "correct_pt": ["Justo", "Tá certo", "Faz sentido"],
                "note": "Concordando com argumento"
            },
            "you bet": {
                "wrong_pt": ["você aposta"],
                "correct_pt": ["Pode apostar", "Com certeza", "Pode crer"],
                "note": "Afirmação confiante"
            },
            "no doubt": {
                "wrong_pt": ["sem dúvida formal"],
                "correct_pt": ["Sem dúvida", "Pode crer"],
                "note": "Certeza"
            },
            "no sweat": {
                "wrong_pt": ["sem suor"],
                "correct_pt": ["Tranquilo", "Sem esforço"],
                "note": "Fácil"
            },
            "beats me": {
                "wrong_pt": ["me bate"],
                "correct_pt": ["Sei lá", "Nem faço ideia", "Não faço a menor ideia"],
                "note": "Desconhecimento"
            }
        },
        "battle_taunts_and_threats": {
            "is that all you got": {
                "wrong_pt": ["é tudo que você tem"],
                "correct_pt": ["É só isso que você tem?", "É só isso que sabe fazer?"],
                "note": "Provocação no ringue"
            },
            "you're dead meat": {
                "wrong_pt": ["você é carne morta"],
                "correct_pt": ["Você já era!", "Você tá morto!"],
                "note": "Ameaça mortal"
            },
            "you're history": {
                "wrong_pt": ["você é história"],
                "correct_pt": ["Você já era!", "Seu fim chegou!"],
                "note": "Ameaça de derrota"
            },
            "make my day": {
                "wrong_pt": ["faça meu dia"],
                "correct_pt": ["Tenta a sorte!", "Me dá esse prazer!"],
                "note": "Desafio arrogante"
            },
            "now you've done it": {
                "wrong_pt": ["agora você fez isso"],
                "correct_pt": ["Agora você passou dos limites!", "Agora você pediu para morrer!"],
                "note": "Fúria prestes a explodir"
            },
            "you asked for it": {
                "wrong_pt": ["você pediu por isso"],
                "correct_pt": ["Você quem pediu!", "Agora aguenta!"],
                "note": "Iniciando contra-ataque"
            },
            "know your place": {
                "wrong_pt": ["conheça seu lugar"],
                "correct_pt": ["Se põe no seu lugar!", "Reconheça seu lugar!"],
                "note": "Arrogância de vilão ou superior"
            },
            "don't make me laugh": {
                "wrong_pt": ["não me faça rir"],
                "correct_pt": ["Não me faça rir!", "Conta outra!"],
                "note": "Desprezo por oponente"
            },
            "don't underestimate me": {
                "wrong_pt": ["não me subestime formal"],
                "correct_pt": ["Não me subestima!", "Não me menospreza!"],
                "note": "Determinação"
            }
        }
    }


def update_all_databases():
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)

    # 1. manga_dialogue_localization.json v1.1.0
    dialogue_db = build_dialogue_localization_1_1()
    dialogue_path = data_dir / "manga_dialogue_localization.json"
    with open(dialogue_path, "w", encoding="utf-8") as f:
        json.dump(dialogue_db, f, ensure_ascii=False, indent=2)
    print(f"[OK] Salvo manga_dialogue_localization.json (v1.1.0) com {sum(len(v) for k, v in dialogue_db.items() if isinstance(v, dict))} regras!")

    # 2. false_cognates_en_pt.json v1.1.0
    fc_path = data_dir / "false_cognates_en_pt.json"
    if fc_path.exists():
        with open(fc_path, "r", encoding="utf-8") as f:
            fc_db = json.load(f)
    else:
        fc_db = {"false_cognates": {}, "expression_corrections": {}, "manga_specific": {}}

    fc_db["_version"] = "1.1.0"
    fc_db["_description"] = "Comprehensive English -> PT-BR False Cognates & Tricky Idioms for Manga Localization (v1.1.0)"

    new_false_cognates = {
        "eventually": {"wrong_pt": "eventualmente (às vezes)", "correct_pt": "no fim das contas / finalmente / com o tempo"},
        "actually": {"wrong_pt": "atualmente", "correct_pt": "na verdade / de fato"},
        "currently": {"wrong_pt": "correntemente", "correct_pt": "atualmente / no momento"},
        "pretend": {"wrong_pt": "pretender", "correct_pt": "fingir"},
        "intend": {"wrong_pt": "entender", "correct_pt": "pretender / ter intenção"},
        "realize": {"wrong_pt": "realizar (fazer)", "correct_pt": "perceber / se dar conta"},
        "notice": {"wrong_pt": "notícia", "correct_pt": "perceber / notar"},
        "injury": {"wrong_pt": "injúria (ofensa verbal)", "correct_pt": "ferimento / lesão"},
        "compromise": {"wrong_pt": "compromisso de agenda", "correct_pt": "entendimento / acordo / ceder"},
        "appointment": {"wrong_pt": "apontamento", "correct_pt": "compromisso marcado / consulta"},
        "costume": {"wrong_pt": "costume / hábito", "correct_pt": "fantasia / traje de luta"},
        "fabric": {"wrong_pt": "fábrica", "correct_pt": "tecido"},
        "factory": {"wrong_pt": "fator", "correct_pt": "fábrica"},
        "novel": {"wrong_pt": "novela de TV", "correct_pt": "romance (livro) / inédito"},
        "prejudice": {"wrong_pt": "prejuízo financeiro", "correct_pt": "preconceito"},
        "resume": {"wrong_pt": "resumir", "correct_pt": "retomar / continuar"},
        "support": {"wrong_pt": "suportar (aturar)", "correct_pt": "apoiar / dar suporte"},
        "stand": {"wrong_pt": "ficar de pé apenas", "correct_pt": "aguentar / suportar (ex: I can't stand it = Não aguento isso)"},
        "casualty": {"wrong_pt": "casualidade", "correct_pt": "baixa / ferido em combate"},
        "beef": {"wrong_pt": "bife apenas", "correct_pt": "treta / briga / rixa (ex: We got beef = Temos uma rixa)"},
        "assist": {"wrong_pt": "assistir (ver)", "correct_pt": "ajudar / dar assistência"},
        "attend": {"wrong_pt": "atender", "correct_pt": "comparecer / frequentar"},
        "balance": {"wrong_pt": "balança", "correct_pt": "equilíbrio"},
        "collar": {"wrong_pt": "colar de joia", "correct_pt": "gola / coleira"},
        "comprehensive": {"wrong_pt": "compreensivo", "correct_pt": "abrangente / completo"},
        "confident": {"wrong_pt": "confidente", "correct_pt": "confiante"},
        "deception": {"wrong_pt": "decepção", "correct_pt": "engano / fraude / farsa"},
        "disgrace": {"wrong_pt": "desgraça fatal", "correct_pt": "vergonha / desonra"},
        "estate": {"wrong_pt": "estado", "correct_pt": "propriedade / patrimônio"},
        "exit": {"wrong_pt": "êxito", "correct_pt": "saída"},
        "hazard": {"wrong_pt": "azar", "correct_pt": "perigo / risco"},
        "ingenious": {"wrong_pt": "ingênuo", "correct_pt": "engenhoso / brilhante"},
        "legend": {"wrong_pt": "legenda de filme", "correct_pt": "lenda"},
        "library": {"wrong_pt": "livraria", "correct_pt": "biblioteca"},
        "Mayor": {"wrong_pt": "maior", "correct_pt": "prefeito"},
        "policy": {"wrong_pt": "polícia", "correct_pt": "política / diretriz"},
        "reclaim": {"wrong_pt": "reclamar", "correct_pt": "recuperar"},
        "sensible": {"wrong_pt": "sensível", "correct_pt": "sensato / ajuizado"},
        "stranger": {"wrong_pt": "estrangeiro", "correct_pt": "desconhecido / estranho"},
        "sympathy": {"wrong_pt": "simpatia alegre", "correct_pt": "compadecimento / solidariedade"},
        "tax": {"wrong_pt": "táxi", "correct_pt": "imposto"}
    }

    new_expressions = {
        "call it a day": {"wrong_pt": "chamar de dia", "correct_pt": "encerrar por hoje / parar por aqui"},
        "under the weather": {"wrong_pt": "sob o clima", "correct_pt": "passando mal / indisposto"},
        "bite the bullet": {"wrong_pt": "morder a bala", "correct_pt": "engolir o choro / encarar de frente"},
        "spill the beans": {"wrong_pt": "derramar os feijões", "correct_pt": "abrir o bico / contar o segredo"},
        "break a leg": {"wrong_pt": "quebre uma perna", "correct_pt": "boa sorte / arrebenta"},
        "hit the sack": {"wrong_pt": "bater no saco", "correct_pt": "ir dormir / capotar"},
        "cut to the chase": {"wrong_pt": "cortar para a caça", "correct_pt": "ir direto ao ponto / sem enrolação"},
        "barking up the wrong tree": {"wrong_pt": "latindo na árvore errada", "correct_pt": "procurando no lugar errado / acusando a pessoa errada"},
        "on thin ice": {"wrong_pt": "no gelo fino", "correct_pt": "pisando em ovos / arriscando a pele"},
        "play with fire": {"wrong_pt": "brincar com fogo", "correct_pt": "brincar com o perigo"},
        "keep your eyes peeled": {"wrong_pt": "mantenha os olhos descascados", "correct_pt": "fique bem atento / olhos bem abertos"},
        "off the hook": {"wrong_pt": "fora do gancho", "correct_pt": "livre da culpa / safou-se"},
        "out of the blue": {"wrong_pt": "fora do azul", "correct_pt": "do nada / de repente"},
        "piece of cake": {"wrong_pt": "pedaço de bolo", "correct_pt": "moleza / muito fácil"},
        "pull someone's leg": {"wrong_pt": "puxar a perna", "correct_pt": "zoar / brincar com alguém"},
        "ring a bell": {"wrong_pt": "tocar um sino", "correct_pt": "soar familiar / lembrar algo"},
        "rule of thumb": {"wrong_pt": "regra do polegar", "correct_pt": "regra geral / regra prática"},
        "take it for granted": {"wrong_pt": "tomar como garantido", "correct_pt": "dar como certo / não valorizar"},
        "up in the air": {"wrong_pt": "acima no ar", "correct_pt": "indefinido / incerto"}
    }

    new_manga_specific = {
        "aura": {"wrong_pt": "aura esotérica apenas", "correct_pt": "pressão espiritual / aura de combate"},
        "killing intent": {"wrong_pt": "intenção matadora", "correct_pt": "intenção assassina / sede de sangue"},
        "bloodlust": {"wrong_pt": "luxúria de sangue", "correct_pt": "sede de sangue / instinto assassino"},
        "finishing move": {"wrong_pt": "movimento finalizador", "correct_pt": "golpe de misericórdia / golpe final"},
        "trump card": {"wrong_pt": "cartão do Trump", "correct_pt": "carta na manga / trunfo"},
        "underdog": {"wrong_pt": "cachorro de baixo", "correct_pt": "azarão"},
        "dark horse": {"wrong_pt": "cavalo escuro", "correct_pt": "candidato surpresa / azarão"},
        "point-blank": {"wrong_pt": "ponto em branco", "correct_pt": "à queima-roupa"},
        "second wind": {"wrong_pt": "segundo vento", "correct_pt": "fôlego renovado / segundo fôlego"},
        "power level": {"wrong_pt": "nível de força literal", "correct_pt": "nível de poder"},
        "technique": {"wrong_pt": "técnica acadêmica", "correct_pt": "técnica de luta / golpe"},
        "stance": {"wrong_pt": "estância", "correct_pt": "postura de combate / base"},
        "counterattack": {"wrong_pt": "contra-ataque simples", "correct_pt": "contra-ataque / contra-golpe"},
        "blind spot": {"wrong_pt": "ponto cego literal", "correct_pt": "ponto cego"}
    }

    fc_db.setdefault("false_cognates", {}).update(new_false_cognates)
    fc_db.setdefault("expression_corrections", {}).update(new_expressions)
    fc_db.setdefault("manga_specific", {}).update(new_manga_specific)
    fc_db["_total_entries"] = len(fc_db.get("false_cognates", {})) + len(fc_db.get("expression_corrections", {})) + len(fc_db.get("manga_specific", {}))

    with open(fc_path, "w", encoding="utf-8") as f:
        json.dump(fc_db, f, ensure_ascii=False, indent=2)
    print(f"[OK] Salvo false_cognates_en_pt.json (v1.1.0) com {fc_db['_total_entries']} entradas!")

    # 3. sfx_database.json v1.1.0
    sfx_path = data_dir / "sfx_database.json"
    if sfx_path.exists():
        with open(sfx_path, "r", encoding="utf-8") as f:
            sfx_db = json.load(f)
    else:
        sfx_db = {"_description": "Manga SFX", "_version": "1.0", "sfx_exact": {}, "sfx_patterns": []}

    sfx_db["_version"] = "1.1.0"

    new_sfx_exact = {
        "pock": "impact",
        "pashin": "slap",
        "badump": "heartbeat",
        "ba-dump": "heartbeat",
        "dokun": "heartbeat",
        "doku": "heartbeat",
        "thump": "heartbeat",
        "thud": "heavy impact",
        "smack": "slap/hit",
        "whack": "hit",
        "crack": "break/impact",
        "crunch": "breaking bone/eating",
        "swoosh": "air movement",
        "whoosh": "fast movement",
        "vwoosh": "energy movement",
        "zap": "electricity",
        "bzzzt": "electricity",
        "skrrt": "tire screech",
        "screee": "screech",
        "clink": "metallic sound",
        "clank": "heavy metal hit",
        "clang": "sword clash",
        "shing": "sword draw",
        "slice": "blade slash",
        "slash": "blade cut",
        "fwip": "quick movement",
        "fwoosh": "flame/wind",
        "kaboom": "explosion",
        "blam": "gunshot/impact",
        "pow": "punch",
        "sock": "punch",
        "bamf": "teleport",
        "poof": "smoke appearance",
        "gulp": "swallow/fear",
        "pant": "breathing heavy",
        "huff": "breathing",
        "wheeze": "exhausted breath",
        "chuckle": "low laugh",
        "snicker": "mocking laugh",
        "giggle": "light laugh",
        "cackle": "evil laugh",
        "mumble": "low speech",
        "murmur": "crowd sound",
        "rustle": "cloth/leaves moving",
        "drip": "liquid drop",
        "splash": "water hit",
        "splat": "wet impact",
        "squelch": "flesh/wet sound",
        "twang": "bow/string sound",
        "ringgg": "phone/bell",
        "ding": "bell sound",
        "creaak": "door/wood creak",
        "slam": "door closing/heavy throw",
        "thwack": "blunt impact",
        "bonk": "light head hit",
        "boop": "gentle poke",
        "tap": "light touch",
        "fwash": "flame",
        "shwa": "slash",
        "bzzt": "spark",
        "zzzt": "electricity",
        "kraaak": "lightning/break",
        "gaga": "metal rattle",
        "gagaga": "heavy rattle",
        "dodo": "heavy footsteps",
        "dododo": "menacing rumble",
        "gogogo": "menacing rumble",
        "rumble": "earthquake/menace",
        "clack": "footstep/stone",
        "clack-clack": "running footsteps",
        "pit-pat": "light rain/steps",
        "patter": "rain/running",
        "fwump": "soft fall",
        "plop": "liquid drop/fall",
        "thump-thump": "running/heartbeat",
        "ka-boom": "giant explosion",
        "ba-bam": "double impact",
        "clash": "weapons colliding",
        "screeech": "long brake/screech"
    }

    sfx_db.setdefault("sfx_exact", {}).update(new_sfx_exact)
    sfx_db["_total_entries"] = len(sfx_db.get("sfx_exact", {}))

    with open(sfx_path, "w", encoding="utf-8") as f:
        json.dump(sfx_db, f, ensure_ascii=False, indent=2)
    print(f"[OK] Salvo sfx_database.json (v1.1.0) com {sfx_db['_total_entries']} entradas!")


if __name__ == "__main__":
    update_all_databases()
