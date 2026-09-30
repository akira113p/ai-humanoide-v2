"""Extrai o jeito de escrever (e a história de vida) de uma pessoa a partir do export de DMs do Instagram
e gera uma persona anonimizada para o chat.py.

Construir:  python persona.py              (estatística + análise por IA)
            python persona.py --sem-llm    (só estatística, sem biografia)
Saída em persona/:
  perfil.json         medidas de digitação (ritmo, tamanho, pontuação, risadas, gírias...)
  analise.json        biografia, relações, personalidade e reações (IA, sobre o texto já anonimizado)
  pares.jsonl         exemplos reais contexto -> resposta dela, anonimizados (usados como few-shot)
  conversa.txt        conversa inteira anonimizada, para conferência
  mapa_nomes.json     nome real -> pseudônimo (PRIVADO; edite à mão para corrigir e rode de novo)
"""
import argparse
import hashlib
import json
import math
import random
import re
import statistics
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
INBOX = ROOT / "meta dados" / "your_instagram_activity" / "messages" / "inbox"
OUT = ROOT / "persona"

# ---------------- configuração ----------------
def _env_persona() -> dict:
    """Lê persona.env (privado, fora do git): identidade do alvo, conversas, listas de nomes e prompt do modo sem persona."""
    arq = ROOT / "persona.env"
    if not arq.exists():
        raise RuntimeError("persona.env não encontrado: copie persona.env.example e preencha")
    cfg = {}
    for linha in arq.read_text(encoding="utf-8").splitlines():
        if linha.strip() and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            cfg[chave.strip()] = json.loads(valor)
    return cfg


_CFG = _env_persona()
ALVO = _CFG["PERSONA_ALVO"]  # sender_name de quem vai ser imitado
THREADS = _CFG["PERSONA_THREADS"]
NOMES_EXTRA = _CFG["PERSONA_NOMES_EXTRA"]  # apelidos que os detectores não pegam
NAO_SAO_NOMES = set(_CFG["PERSONA_NAO_SAO_NOMES"])  # palavras capitalizadas que não são pessoas (lugares, marcas)
GENERO = _CFG["PERSONA_GENERO"]  # força gênero quando o palpite erraria

BURST_GAP = 180  # s: msgs seguidas do mesmo autor dentro disso formam um turno
SESSION_GAP = 3 * 3600  # s: silêncio maior que isso abre nova sessão (contexto não atravessa)
CONTEXTO_TURNOS = 6  # turnos anteriores guardados em cada par
LONGA = 80  # caracteres a partir dos quais a msg conta como "texto grande"

# ---------------- dicionários ----------------
STOP = set("""a o e é de da do das dos em no na nos nas um uma uns umas eu tu ele ela nós eles elas você vc
me te se lhe meu minha teu tua seu sua que q quem qual quando onde como porque pq por pra para com sem mas mais
menos muito pouco já ja não nao n sim só so também tb tbm isso isto esse essa este esta aquele aquela ai aí la lá
aqui ali então ent tipo nossa oi oie olá ola bom boa dia noite tarde tudo td nada ok sério serio ata oxi mds nss
pse pprt kkk vezes as os ao tem ter foi era vai vou tá ta está estou sou ser fazer fez faz eae opa pronto pera
ah hum sim meu editada lgl lgll hoje amanhã ontem vamos bora mano mana cara véi vei gente povo""".split())

NOMES_M = """Adriano Alexandre Anderson André Antônio Arthur Bernardo Breno Bruno Caio Carlos Cauã Daniel Davi Diego
Douglas Eduardo Enzo Erick Fábio Felipe Fernando Gabriel Guilherme Gustavo Heitor Henrique Hugo Igor Isaac João
Joaquim Jonas José Juan Júlio Kaique Kauã Leandro Leonardo Lorenzo Lucas Luan Luiz Luís Marcelo Marcos Mateus
Matheus Miguel Murilo Nicolas Otávio Paulo Pedro Rafael Renan Renato Ricardo Rodrigo Rogério Samuel Sérgio Thiago
Tiago Theo Vinícius Vitor Victor Wesley Yuri Manoel Manuel Ademir Emanuel Pietro Benício Cauê Ruan Kevin""".split()
NOMES_F = """Alice Amanda Ana Beatriz Bia Bianca Bruna Camila Carla Carol Carolina Cecília Débora Duda Eduarda
Fernanda Gabriela Gabi Giovana Helena Heloísa Isabela Isabel Isadora Iza Júlia Juliana Kamila Karol Lara Larissa
Laura Letícia Lívia Lorena Luana Luísa Maitê Manuela Mariana Marina Maria Melissa Natália Nicole Paula Pietra
Rafaela Raquel Rebeca Sabrina Sara Sofia Sophia Tainá Valentina Yasmin Lais Melina Lavínia Helô""".split()
# fora da lista por serem palavras comuns: Clara, Vitória, Rosa, Luz, Graça
POOL_M = ["Téo", "Caetano", "Ravi", "Otto", "Benjamin", "Joel", "Bento", "Vicente", "Iuri", "Noah", "Ian", "Levi",
          "Dante", "Raul", "Tomás", "Elias", "Gael", "Ulisses", "Martim", "Ícaro"]
POOL_F = ["Lívia", "Aurora", "Cora", "Íris", "Olívia", "Jade", "Maya", "Ágatha", "Stella", "Nina", "Liz",
          "Mirela", "Yara", "Elisa", "Tereza", "Aline", "Dália", "Luna", "Celina", "Noemi"]
POOL_SOBRENOME = ["Prado", "Moura", "Queiroz", "Siqueira", "Barros", "Toledo", "Rangel", "Paiva", "Leal", "Assis"]

ACENTOS = {"nao": "não", "voce": "você", "tambem": "também", "entao": "então", "ja": "já", "ate": "até",
           "la": "lá", "ta": "tá", "so": "só", "voces": "vocês", "sera": "será", "serio": "sério"}
GIRIAS = set("""vc vcs tb tbm q pq n nn ss sss nss mds pprt tlgd slk sla blz ent pse oxi ata ok okay mt mto msm
td tds cmg ctg vdd fds plmdds pdc tmj vlw flw mn mna mano mana vei véi mlk mlks mlk lgl lgll dms kd hj amg
migo miga bff crush aff affs eita ual nossa oie oii nop ss hum hmm aham uhum tipo cringe paia sacanagem ksks""".split())

RE_URL = re.compile(r"https?://\S+")
RE_RISADA = re.compile(r"\b(?=[ak]*k[ak]*k)[ak]{2,}\b|\b(?:ha){2,}h?\b|\b(?:rs){2,}\b|\bhe(?:he)+\b", re.I)
RE_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐❤]")
RE_ALONG = re.compile(r"([a-jl-z])\1{2,}", re.I)  # letra repetida 3x+ (fora o k da risada)
RE_TOKEN = re.compile(r"[\wÀ-ÿ]+")


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def fix(s):
    """O export da Meta grava UTF-8 como latin1."""
    try:
        return s.encode("latin1").decode("utf8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def pct(parte, total):
    return round(parte / total, 3) if total else 0.0


def quantis(xs):
    if not xs:
        return {"media": 0, "mediana": 0, "p90": 0, "max": 0}
    xs = sorted(xs)
    return {"media": round(statistics.mean(xs), 2), "mediana": statistics.median(xs),
            "p90": xs[min(len(xs) - 1, int(len(xs) * 0.9))], "max": xs[-1]}


# ================= 1. carregar e limpar =================
def carregar(threads):
    msgs = []
    for t in threads:
        d = json.loads((INBOX / t / "message_1.json").read_text(encoding="utf-8"))
        for m in d["messages"]:
            texto = fix(m.get("content", ""))
            editada = texto.endswith(" (edited)")
            texto = texto.removesuffix(" (edited)")
            midia = []
            if "photos" in m: midia.append("foto")
            if "videos" in m: midia.append("vídeo")
            if "audio_files" in m: midia.append("áudio")
            if "share" in m or texto == "You sent an attachment." or RE_URL.fullmatch(texto.strip()):
                midia.append("post/reel")
                texto = ""
            if "sticker" in m: midia.append("figurinha")
            if re.fullmatch(r"(Liked a message|Reacted .* to your message|.* reacted .*)", texto):
                continue
            msgs.append({"autor": fix(m["sender_name"]), "ts": m["timestamp_ms"] / 1000, "texto": texto.strip(),
                         "midia": midia, "editada": editada})
    msgs.sort(key=lambda m: m["ts"])
    return msgs


def agrupar(msgs):
    """Turno = rajada de msgs do mesmo autor sem pausa > BURST_GAP. Sessão = bloco sem silêncio > SESSION_GAP."""
    turnos, sessao = [], 0
    for m in msgs:
        ant = turnos[-1] if turnos else None
        if ant and m["ts"] - ant["fim"] > SESSION_GAP:
            sessao += 1
        if ant and ant["autor"] == m["autor"] and ant["sessao"] == sessao and m["ts"] - ant["fim"] <= BURST_GAP:
            ant["msgs"].append(m)
            ant["fim"] = m["ts"]
        else:
            turnos.append({"autor": m["autor"], "sessao": sessao, "inicio": m["ts"], "fim": m["ts"], "msgs": [m]})
    return turnos


# ================= 2. anonimização =================
def palpite_genero(nome, textos):
    n = sem_acento(nome.lower())
    if n in GENERO:
        return GENERO[n]
    for lista, g in ((NOMES_M, "m"), (NOMES_F, "f")):
        if n in {sem_acento(x.lower()) for x in lista}:
            return g
    # artigo antes do nome: "o gomes", "a bia"
    m = f = 0
    for t in textos:
        tl = sem_acento(t.lower())
        m += len(re.findall(rf"\b(?:o|do|no|pelo|ao|pro)\s+{re.escape(n)}\b", tl))
        f += len(re.findall(rf"\b(?:da|na|pela|pra a)\s+{re.escape(n)}\b", tl))
    if m != f:
        return "m" if m > f else "f"
    return "f" if n.endswith("a") else "m"


def detectar_nomes(msgs):
    textos = [m["texto"] for m in msgs if m["texto"]]
    achados = {}
    # participantes (nome e sobrenome separados)
    for autor in {m["autor"] for m in msgs}:
        partes = autor.split()
        achados[partes[0].lower()] = "pessoa"
        for p in partes[1:]:
            achados[p.lower()] = "sobrenome"
    # palavra capitalizada no meio da frase que não é stopword nem lugar
    for t in textos:
        for w in RE_TOKEN.findall(t)[1:]:
            wl = w.lower()
            if w[0].isupper() and len(w) > 2 and wl not in STOP and sem_acento(wl) not in NAO_SAO_NOMES \
                    and not RE_RISADA.fullmatch(w):
                achados.setdefault(wl, "pessoa")
    # nomes comuns em qualquer posição/caixa
    conhecidos = {sem_acento(n.lower()) for n in NOMES_M + NOMES_F}
    for t in textos:
        for w in RE_TOKEN.findall(t):
            if sem_acento(w.lower()) in conhecidos:
                achados.setdefault(w.lower(), "pessoa")
    for n in NOMES_EXTRA:
        achados.setdefault(n.lower(), "pessoa")
    return achados, textos


def montar_mapa(msgs, extras=()):
    arq = OUT / "mapa_nomes.json"
    mapa = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    achados, textos = detectar_nomes(msgs)
    for e in extras:
        achados.setdefault(e.lower(), "pessoa")
    reais = {sem_acento(k) for k in achados}
    usados = set(mapa.values())
    for nome in sorted(achados):
        if nome in mapa:
            continue
        if achados[nome] == "sobrenome":
            pool = POOL_SOBRENOME
        else:
            pool = POOL_M if palpite_genero(nome, textos) == "m" else POOL_F
        livres = [p for p in pool if p not in usados and sem_acento(p.lower()) not in reais]
        # hash estável: o mesmo nome real sempre recebe o mesmo pseudônimo
        h = int(hashlib.sha1(nome.encode()).hexdigest(), 16)
        escolha = livres[h % len(livres)] if livres else f"Pessoa{len(mapa) + 1}"
        mapa[nome] = escolha
        usados.add(escolha)
    OUT.mkdir(exist_ok=True)
    arq.write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")
    return mapa


def compilar_anonimizador(mapa):
    variantes = {sem_acento(k.lower()): v for k, v in mapa.items()}
    formas = sorted(set(mapa) | set(variantes), key=len, reverse=True)  # com e sem acento
    padrao = re.compile(r"(?<![\w@])(" + "|".join(re.escape(k) for k in formas) + r")(?!\w)", re.I)

    def trocar(m):
        real = m.group(0)
        novo = variantes[sem_acento(real.lower())]
        if real.isupper() and len(real) > 1:
            return novo.upper()
        if real[0].islower():
            return novo.lower()  # ela escreve "igor" minúsculo -> mantém minúsculo
        return novo

    def anon(texto):
        texto = RE_URL.sub("[link]", texto)
        texto = re.sub(r"@[\w.]+", "@usuario", texto)
        return padrao.sub(trocar, texto) if variantes else texto

    return anon


# ================= 3. medidas de estilo =================
def medir(msgs, turnos, alvo):
    dela = [m for m in msgs if m["autor"] == alvo and m["texto"]]
    outro = [m for m in msgs if m["autor"] != alvo and m["texto"]]
    textos = [m["texto"] for m in dela]
    n = len(textos)
    t_dela = [t for t in turnos if t["autor"] == alvo]

    tamanhos = [len(t) for t in textos]
    palavras = [len(t.split()) for t in textos]
    finais = Counter()
    for t in textos:
        c = t.rstrip()[-1]
        finais["..." if t.rstrip().endswith("...") else c if c in "?!." else "nenhum"] += 1

    # acentos omitidos, por palavra
    acento = {}
    for sem, com in ACENTOS.items():
        a = sum(len(re.findall(rf"(?<!\w){sem}(?!\w)", t.lower())) for t in textos)
        b = sum(len(re.findall(rf"(?<!\w){com}(?!\w)", t.lower())) for t in textos)
        if a + b:
            acento[sem] = {"sem_acento": a, "com_acento": b, "taxa_omite": pct(a, a + b)}
    omit_total = pct(sum(v["sem_acento"] for v in acento.values()), sum(v["sem_acento"] + v["com_acento"] for v in acento.values()))

    risadas = [r.lower() for t in textos for r in RE_RISADA.findall(t)]
    so_risada = sum(1 for t in textos if RE_RISADA.sub("", t).strip(" ?!.") == "")
    emojis = [e for t in textos for e in RE_EMOJI.findall(t)]

    # vocabulário distintivo: log-odds dela vs o outro lado (quem ela É, não do que falam)
    cd = Counter(w.lower() for t in textos for w in RE_TOKEN.findall(t))
    co = Counter(w.lower() for m in outro for w in RE_TOKEN.findall(m["texto"]))
    vd, vo, V = sum(cd.values()), sum(co.values()), len(set(cd) | set(co))
    distintivo = sorted(
        ((w, round(math.log((c + 1) / (vd + V)) - math.log((co[w] + 1) / (vo + V)), 2), c) for w, c in cd.items() if c >= 3),
        key=lambda x: -x[1])[:30]

    todas = Counter(w.lower() for t in textos for w in RE_TOKEN.findall(t))
    # gíria conhecida, ou abreviação sem vogal repetida (vc, mds, pq...), fora lugares/marcas
    girias = Counter({w: c for w, c in todas.items() if w not in NAO_SAO_NOMES and not w.isdigit() and (
        w in GIRIAS or (2 <= len(w) <= 4 and c >= 2 and not re.search(r"[aeiouáéíóúãõâêôà]", w)))})

    aberturas = Counter(RE_TOKEN.findall(t["msgs"][0]["texto"].lower())[0] for t in t_dela
                        if t["msgs"][0]["texto"] and RE_TOKEN.findall(t["msgs"][0]["texto"]))

    # velocidade de digitação: caracteres da msg seguinte / pausa dentro da mesma rajada
    cps = []
    for t in t_dela:
        for a, b in zip(t["msgs"], t["msgs"][1:]):
            gap = b["ts"] - a["ts"]
            if 1 <= gap <= 90 and b["texto"]:
                cps.append(len(b["texto"]) / gap)

    # latência de resposta e quem puxa conversa
    lat, iniciou, sessoes = [], Counter(), {}
    for a, b in zip(turnos, turnos[1:]):
        if b["autor"] == alvo and a["autor"] != alvo and a["sessao"] == b["sessao"]:
            lat.append(b["inicio"] - a["fim"])
    for t in turnos:
        sessoes.setdefault(t["sessao"], t["autor"])
    iniciou.update(sessoes.values())
    horas = Counter(datetime.fromtimestamp(m["ts"]).hour for m in dela)

    return {
        "alvo": alvo,
        "n_msgs": n, "n_turnos": len(t_dela),
        "msgs_por_turno": quantis([len(t["msgs"]) for t in t_dela]),
        "dist_msgs_por_turno": dict(sorted(Counter(min(len(t["msgs"]), 8) for t in t_dela).items())),
        "chars_por_msg": quantis(tamanhos),
        "palavras_por_msg": quantis(palavras),
        "pct_msgs_longas": pct(sum(x >= LONGA for x in tamanhos), n),
        "pct_msgs_1_palavra": pct(sum(x == 1 for x in palavras), n),
        "pct_inicia_maiuscula": pct(sum(t[0].isupper() for t in textos if t[0].isalpha()), sum(t[0].isalpha() for t in textos)),
        "pct_tudo_minusculo": pct(sum(t == t.lower() for t in textos), n),
        "pct_com_caps_lock": pct(sum(bool(re.search(r"\b[A-ZÀ-Ý]{3,}\b", t)) for t in textos), n),
        "final_da_msg": {k: pct(v, n) for k, v in finais.most_common()},
        "pct_interrogacao_dupla": pct(sum("??" in t for t in textos), n),
        "virgulas_por_msg": round(sum(t.count(",") for t in textos) / max(n, 1), 3),
        "omissao_acento": {"geral": omit_total, "por_palavra": acento},
        "risada": {"pct_msgs_com": pct(sum(bool(RE_RISADA.search(t)) for t in textos), n),
                   "pct_msgs_so_risada": pct(so_risada, n),
                   "formas": Counter(risadas).most_common(8),
                   "tamanho_tipico": statistics.median([len(r) for r in risadas]) if risadas else 0},
        "emoji": {"por_msg": round(len(emojis) / max(n, 1), 3), "top": Counter(emojis).most_common(8)},
        "pct_alongamento": pct(sum(bool(RE_ALONG.search(t)) for t in textos), n),
        "exemplos_alongamento": list({mm.group(0) for t in textos for mm in RE_ALONG.finditer(t)})[:8],
        "pct_espaco_duplo": pct(sum("  " in t for t in textos), n),
        "pct_editadas": pct(sum(m["editada"] for m in dela), n),
        "pct_turnos_com_pergunta": pct(sum(any("?" in m["texto"] for m in t["msgs"]) for t in t_dela), len(t_dela)),
        "girias_abreviacoes": girias.most_common(30),
        "vocabulario_distintivo": distintivo,
        "aberturas_de_turno": aberturas.most_common(15),
        "digitacao_cps": round(statistics.median(cps), 2) if cps else 4.0,
        "latencia_resposta_s": quantis([round(x) for x in lat]),
        "pct_sessoes_iniciadas_por_ela": pct(iniciou[alvo], len(sessoes)),
        "horarios_mais_ativos": [h for h, _ in horas.most_common(5)],
    }


# ================= 4. pares de exemplo =================
def rotulo(t, alvo):
    return "ela" if t["autor"] == alvo else "outro"


def linhas_turno(t, anon):
    out = []
    for m in t["msgs"]:
        if m["texto"]:
            out.append(anon(m["texto"]))
        for x in m["midia"]:
            out.append(f"[mandou {x}]")
    return out


def montar_pares(turnos, alvo, anon):
    pares = []
    for i, t in enumerate(turnos):
        if t["autor"] != alvo:
            continue
        resp = [anon(m["texto"]) for m in t["msgs"] if m["texto"]]
        if not resp:
            continue
        ctx = [c for c in turnos[max(0, i - CONTEXTO_TURNOS):i] if c["sessao"] == t["sessao"]]
        pares.append({"contexto": [{"quem": rotulo(c, alvo), "msgs": linhas_turno(c, anon)} for c in ctx],
                      "resposta": resp})
    return pares


# ================= 5. análise por IA (biografia + nuances) =================
PROMPT_ANALISE = """Abaixo está uma conversa real de DM . A pessoa analisada é "{nome}".
Extraia TUDO que ajude uma IA a falar exatamente como ela e a conhecer a história dela. Use só o que está no texto.
Responda APENAS com JSON válido neste formato:
{{
 "biografia": "texto corrido em 3ª pessoa com todos os fatos que ela conta sobre si: idade, estudo, família, religião, rotina, lugares, hobbies, planos, gostos, histórias marcantes",
 "relacoes": [{{"nome": "pseudônimo", "quem_e": "...", "como_ela_fala_dessa_pessoa": "..."}}],
 "personalidade": "como ela é (humor, confiança, timidez, sarcasmo, afeto , provocacao)",
 "estilo_qualitativo": ["observação concreta sobre o jeito de escrever + exemplo citado entre aspas"],
 "como_reage": {{"piada": "", "pergunta_pessoal": "", "elogio_ou_flerte": "", "assunto_desconfortavel": "", "quando_ocupada_ou_sem_interesse": "", "fofoca": ""}},
 "expressoes_marcantes": ["frases e bordões típicos dela"],
 "assuntos_favoritos": ["..."],
 "nomes_nao_anonimizados": ["nomes próprios de PESSOAS que ainda aparecem sem troca (não inclua os pseudônimos {pseudos})"]
}}

CONVERSA:
{conversa}"""

PROMPT_MESCLAR = """Junte estas análises parciais da mesma pessoa em um único JSON no mesmo formato, sem perder fatos
e sem repetir itens. Responda APENAS com o JSON.\n\n{partes}"""


def chamar_llm(prompt):
    from chat import chat_stream  # import tardio: chat.py importa este módulo

    for _ in range(3):
        partes = []
        chat_stream([{"role": "user", "content": prompt}],
                    lambda kind, v: partes.append(v) if kind == "chunk" else (partes.clear() if kind == "reset" else print("  ", v) if kind == "log" else None))
        txt = "".join(partes)
        m = re.search(r"\{.*\}", txt, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                pass
        print("   resposta não era JSON válido, tentando de novo")
    raise RuntimeError("a IA não devolveu JSON válido")


def analisar(linhas, nome, pseudos, max_chars=45_000):
    blocos, atual = [], []
    for l in linhas:
        if sum(map(len, atual)) + len(l) > max_chars:
            blocos.append(atual)
            atual = []
        atual.append(l)
    blocos.append(atual)
    resultados = []
    for i, b in enumerate(blocos, 1):
        print(f"análise por IA: bloco {i}/{len(blocos)}")
        resultados.append(chamar_llm(PROMPT_ANALISE.format(nome=nome, pseudos=", ".join(pseudos), conversa="\n".join(b))))
    if len(resultados) == 1:
        return resultados[0]
    print("análise por IA: mesclando blocos")
    return chamar_llm(PROMPT_MESCLAR.format(partes=json.dumps(resultados, ensure_ascii=False)))


def anon_profundo(obj, anon):
    if isinstance(obj, str):
        return anon(obj)
    if isinstance(obj, list):
        return [anon_profundo(x, anon) for x in obj]
    if isinstance(obj, dict):
        return {k: anon_profundo(v, anon) for k, v in obj.items()}
    return obj


# ================= construção =================
def construir(usar_llm=True):
    msgs = carregar(THREADS)
    turnos = agrupar(msgs)
    mapa = montar_mapa(msgs)
    anon = compilar_anonimizador(mapa)
    autor = lambda a: " ".join(w.capitalize() for w in anon(a).split())
    nome_alvo = autor(ALVO)
    outro = next((autor(m["autor"]) for m in msgs if m["autor"] != ALVO), "Outro")

    perfil = medir(msgs, turnos, ALVO)
    perfil["alvo"] = nome_alvo
    perfil["outro"] = outro
    # listas de palavras podem conter nomes reais
    for k in ("girias_abreviacoes", "vocabulario_distintivo", "aberturas_de_turno"):
        perfil[k] = [x for x in perfil[k] if x[0] not in mapa]

    conversa = []
    for t in turnos:
        for l in linhas_turno(t, anon):
            conversa.append(f"{autor(t['autor'])}: {l}")

    analise = {}
    if usar_llm:
        analise = analisar(conversa, nome_alvo, sorted(set(mapa.values())))
        sobras = [n for n in analise.pop("nomes_nao_anonimizados", []) if n and n.lower() not in {v.lower() for v in mapa.values()}]
        if sobras:  # nomes que escaparam: entram no mapa e tudo é re-anonimizado
            print("nomes extras detectados pela IA:", sobras)
            mapa = montar_mapa(msgs, extras=[s.split()[0] for s in sobras])
            anon = compilar_anonimizador(mapa)
            conversa = [f"{autor(t['autor'])}: {l}" for t in turnos for l in linhas_turno(t, anon)]
        analise = anon_profundo(analise, anon)

    pares = montar_pares(turnos, ALVO, anon)
    OUT.mkdir(exist_ok=True)
    (OUT / "perfil.json").write_text(json.dumps(perfil, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "conversa.txt").write_text("\n".join(conversa), encoding="utf-8")
    with open(OUT / "pares.jsonl", "w", encoding="utf-8") as f:
        for p in pares:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    if analise:
        (OUT / "analise.json").write_text(json.dumps(analise, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"persona '{nome_alvo}': {perfil['n_msgs']} msgs, {perfil['n_turnos']} turnos, {len(pares)} pares")
    print("mapa de nomes:", json.dumps(mapa, ensure_ascii=False))


# ================= uso em tempo real (chat.py) =================
def _tok(s):
    return RE_TOKEN.findall(sem_acento(s.lower()))


class Persona:
    def __init__(self, perfil, analise, pares):
        self.perfil, self.analise, self.pares = perfil, analise, pares
        self.nome = perfil["alvo"]
        docs = [_tok(" ".join(sum((c["msgs"] for c in p["contexto"][-2:]), [])) + " " + " ".join(p["resposta"]))
                for p in pares]
        df = Counter(w for d in docs for w in set(d))
        self.idf = {w: math.log((1 + len(docs)) / (1 + c)) + 1 for w, c in df.items()}
        self.vetores = [self._vetor(d) for d in docs]

    @classmethod
    def carregar(cls, pasta=OUT):
        if not (pasta / "perfil.json").exists():
            return None
        analise = json.loads((pasta / "analise.json").read_text(encoding="utf-8")) if (pasta / "analise.json").exists() else {}
        pares = [json.loads(l) for l in (pasta / "pares.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        return cls(json.loads((pasta / "perfil.json").read_text(encoding="utf-8")), analise, pares)

    def _vetor(self, toks):
        tf = Counter(toks)
        v = {w: c * self.idf.get(w, 1.0) for w, c in tf.items()}
        norma = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norma for w, x in v.items()}

    def exemplos(self, consulta, k_sim=8, k_aleat=4):
        """Os pares mais parecidos com o momento atual + alguns aleatórios (variedade de tom)."""
        q = self._vetor(_tok(consulta))
        notas = sorted(((sum(q.get(w, 0) * x for w, x in v.items()), i) for i, v in enumerate(self.vetores)), reverse=True)
        escolhidos = [i for s, i in notas[:k_sim] if s > 0]
        resto = [i for i in range(len(self.pares)) if i not in escolhidos]
        escolhidos += random.sample(resto, min(k_aleat, len(resto)))
        return [self.pares[i] for i in escolhidos]

    def regras(self):
        """Transforma as medidas em instruções concretas."""
        p = self.perfil
        r = p["risada"]
        finais = p["final_da_msg"]
        formas = ", ".join(f'"{f}"' for f, _ in r["formas"][:5]) or "quase não ri por escrito"
        girias = ", ".join(w for w, _ in p["girias_abreviacoes"][:20])
        vocab = ", ".join(w for w, _, _ in p["vocabulario_distintivo"][:20])
        abre = ", ".join(w for w, _ in p["aberturas_de_turno"][:10])
        acento = ", ".join(f'{w} ({v["taxa_omite"]:.0%} sem acento)' for w, v in p["omissao_acento"]["por_palavra"].items() if v["sem_acento"] + v["com_acento"] >= 3)
        emo = "praticamente nunca usa emoji" if p["emoji"]["por_msg"] < 0.02 else "emojis que usa: " + " ".join(e for e, _ in p["emoji"]["top"])
        return f"""- Manda o que pensa em RAJADAS de mensagens curtas: em média {p['msgs_por_turno']['media']} msgs seguidas (às vezes {p['msgs_por_turno']['p90']}+). Distribuição real de msgs por vez: {p['dist_msgs_por_turno']}.
- Cada mensagem tem mediana de {p['chars_por_msg']['mediana']} caracteres / {p['palavras_por_msg']['mediana']} palavras; {p['pct_msgs_1_palavra']:.0%} são de uma palavra só. {f"Só {p['pct_msgs_longas']:.0%} passam de {LONGA} caracteres (texto grande é raro)" if p['pct_msgs_longas'] else f"NUNCA manda mensagem com mais de {p['chars_por_msg']['max']} caracteres: até história longa ela conta picotada em várias msgs (já mandou {p['msgs_por_turno']['max']} seguidas)"}.
- Começa com letra maiúscula em {p['pct_inicia_maiuscula']:.0%} das msgs (o teclado do celular capitaliza); {p['pct_com_caps_lock']:.0%} têm palavra em CAPS pra dar ênfase.
- Fim da mensagem: {', '.join(f'{k} {v:.0%}' for k, v in finais.items())}. Ou seja: quase nunca ponto final; pergunta com "?" {'e às vezes "??"' if p['pct_interrogacao_dupla'] > 0.01 else ''}.
- Vírgulas: {p['virgulas_por_msg']} por msg (quebra em outra mensagem em vez de usar vírgula).
- Acentos: omite em {p['omissao_acento']['geral']:.0%} dos casos medidos. {acento}.
- Risada: aparece em {r['pct_msgs_com']:.0%} das msgs, {r['pct_msgs_so_risada']:.0%} são só risada. Formas: {formas}.
- {emo}.
- Gírias/abreviações que ela usa: {girias}.
- Palavras mais características dela: {vocab}.
- Como costuma começar a falar: {abre}.
- Erros de digitação e espaço duplo acontecem ({p['pct_espaco_duplo']:.0%} das msgs com espaço duplo); não corrija tudo.
- Faz pergunta em {p['pct_turnos_com_pergunta']:.0%} das vezes que fala."""

    def system_prompt(self, historico, n_msgs=None):
        a = self.analise
        consulta = " ".join(m["content"] for m in historico[-3:] if m["role"] != "system")
        blocos = []
        for ex in self.exemplos(consulta):
            linhas = [f"{self.perfil['outro'] if c['quem'] == 'outro' else self.nome}: " + " / ".join(c["msgs"]) for c in ex["contexto"][-4:]]
            linhas.append(f"{self.nome} respondeu:\n" + "\n".join(ex["resposta"]))
            blocos.append("\n".join(linhas))
        if n_msgs is None:  # sorteia o tamanho da rajada pela distribuição real dela
            dist = self.perfil["dist_msgs_por_turno"]
            n_msgs = int(random.choices(list(dist), weights=list(dist.values()))[0])
        rel = "\n".join(f"- {r.get('nome')}: {r.get('quem_e')} ({r.get('como_ela_fala_dessa_pessoa', '')})" for r in a.get("relacoes", []))
        reage = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in a.get("como_reage", {}).items() if v)
        estilo = "\n".join(f"- {x}" for x in a.get("estilo_qualitativo", []))
        return f"""Você está numa conversa de DM do Instagram vc é {self.nome}, . Escreva exatamente como ela digita e pensa. A outra pessoa da conversa é quem está te escrevendo agora.

# Quem ela é
{a.get('biografia', '(sem biografia gerada)')}
Personalidade: {a.get('personalidade', '')}
Assuntos que ela gosta: {', '.join(a.get('assuntos_favoritos', []))}
Pessoas da vida dela:
{rel}

# Como ela digita (medido em {self.perfil['n_msgs']} mensagens reais)
{self.regras()}

# Jeito de conversar
{estilo}
Expressões marcantes: {' | '.join(a.get('expressoes_marcantes', []))}
Como ela reage:
{reage}

# Exemplos reais (o contexto e como ela respondeu de verdade)
""" + "\n\n---\n".join(blocos) + f"""

# Formato da sua resposta
- Escreva só as mensagens dela, UMA POR LINHA. Cada linha é enviada como uma mensagem separada no direct.
- Desta vez mande cerca de {n_msgs} mensagem(ns) (mais, se estiver contando uma história).
- Nada de aspas, "{self.nome}:", markdown, listas ou descrição de ações. Nada de linguagem de assistente.
- Não copie os exemplos: reaja ao que acabaram de dizer, com o mesmo tom, gírias e ritmo.
- Fatos sobre ela vêm só da seção "Quem ela é". Se perguntarem algo que não está lá, responda vago ou desconverse como ela faria.
- Ela é adolescente de 18 anos"""

    # --------- pós-processamento: força as estatísticas que o modelo ignora ---------
    def humanizar(self, texto):
        p = self.perfil
        linhas = []
        for l in texto.replace("\r", "").split("\n"):
            l = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", l)  # listas
            l = re.sub(rf"^\s*{re.escape(self.nome)}\s*:\s*", "", l, flags=re.I)  # "Nome: "
            l = re.sub(r"[*_`#]+", "", l).strip().strip('"“”')
            if l:
                linhas.append(l)
        out = []
        for l in linhas:
            if p["emoji"]["por_msg"] < 0.02:
                l = RE_EMOJI.sub("", l).strip()
            forma = p["risada"]["formas"][0][0] if p["risada"]["formas"] else None
            if forma:
                l = re.sub(r"\b(?:ha){2,}h?\b|\b(?:rs){2,}\b|\bhe(?:he)+\b", forma, l, flags=re.I)
            # ponto final: tira na proporção em que ela não usa
            if l.endswith(".") and not l.endswith("...") and random.random() > p["final_da_msg"].get(".", 0):
                l = l[:-1]
            # acentos: tira nas palavras que ela costuma escrever sem
            for sem, v in p["omissao_acento"]["por_palavra"].items():
                if v["sem_acento"] + v["com_acento"] >= 3 and random.random() < v["taxa_omite"]:
                    com = ACENTOS[sem]
                    l = re.sub(rf"(?<!\w){com}(?!\w)", sem, l)
                    l = re.sub(rf"(?<!\w){com.capitalize()}(?!\w)", sem.capitalize(), l)
            # maiúscula inicial na proporção dela
            if l and l[0].isalpha():
                l = (l[0].upper() if random.random() < p["pct_inicia_maiuscula"] else l[0].lower()) + l[1:]
            if l:
                out.append(l)
        # quebra msgs longas demais para o padrão dela
        limite = max(p["chars_por_msg"]["p90"] * 2, LONGA * 1.5)
        partes = []
        for l in out:
            while len(l) > limite and re.search(r"[,.;]\s|\s(?:mas|e|porque|pq)\s", l[20:]):
                m = re.search(r"[,.;]\s|\s(?:mas|e|porque|pq)\s", l[int(limite * 0.4):])
                if not m:
                    break
                corte = int(limite * 0.4) + m.start()
                partes.append(l[:corte].rstrip(",.; "))
                l = l[corte:].lstrip(",.; ")
            partes.append(l)
        maximo = max(3, int(p["msgs_por_turno"]["p90"]) * 3)
        if len(partes) > maximo:  # junta o excesso na última
            partes = partes[:maximo - 1] + [" ".join(partes[maximo - 1:])]
        return partes or ["?"]

    def atraso(self, msg):
        """Segundos para 'digitar' a msg na velocidade medida dela (limitado para não travar o teste)."""
        return min(max(len(msg) / max(self.perfil["digitacao_cps"], 1.0), 0.6), 6.0)

    def espera_inicial(self):
        """Pausa antes da primeira msg: latência mediana real dela, limitada a 8 s."""
        return min(self.perfil["latencia_resposta_s"]["mediana"], 8)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-llm", action="store_true", help="não chama a IA para biografia/nuances")
    construir(usar_llm=not ap.parse_args().sem_llm)
