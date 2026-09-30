"""Cliente OpenRouter (só modelos gratuitos) com fallback automático entre modelos.

Ordem = maior contexto primeiro. Se um modelo falhar (limite de requisições/tokens, indisponível,
contexto estourado, resposta vazia), o histórico COMPLETO é reenviado ao próximo da lista.
"""
import json
import time
from functools import cache
from pathlib import Path

import requests

ENV = Path(__file__).with_name("env.env")
URL = "https://openrouter.ai/api/v1/chat/completions"
# (id, contexto em tokens) — ordenado do maior para o menor contexto.
# Fora da lista: thinkingmachines/inkling(-small):free (1M, mas só aceita "agentic harness", erro 403),
# nemotron-3.5-content-safety (classificador, não conversa).
CHAIN = [
    ("stealth/space-bunny-alpha", 1_000_000),
    ("nvidia/nemotron-3-ultra-550b-a55b:free", 1_000_000),
    ("nvidia/nemotron-3.5-lightning:free", 1_000_000),
    ("dots-studio/dots-3-note-preview:free", 512_000),
    ("nvidia/nemotron-3-super-120b-a12b:free", 262_144),
    ("qwen/qwen3.8-27b:free", 262_144),
    ("google/gemma-4-31b-it:free", 262_144),
    ("google/gemma-4-26b-a4b-it:free", 262_144),
    ("poolside/laguna-s-2.1:free", 262_144),
    ("poolside/laguna-xs-2.1:free", 262_144),
    ("inclusionai/ling-3.0-flash-sante:free", 262_144),
    ("cohere/north-mini-code:free", 256_000),
    ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", 256_000),
    ("openrouter/free", 200_000),  # roteador: escolhe qualquer modelo grátis disponível
    ("liquid/lfm-2.5-2.6b:free", 65_536),
]
COOLDOWN = 120  # segundos que um modelo com erro fica fora da fila (403/404: sessão inteira)
CHARS_PER_TOKEN = 3  # estimativa conservadora para pular modelos cujo contexto não cabe
OUTPUT_MARGIN = 8_000  # espaço reservado para a resposta ao checar se o histórico cabe


def load_key() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            name, value = line.split("=", 1)
            if name.strip().lower() in ("openrouter", "openrouter_api_key"):
                return value.strip().strip("\"'")
    raise RuntimeError("chave 'openrouter' não encontrada em env.env")


blocked_until: dict[str, float] = {}


@cache
def chave():
    """Chave lida uma vez, só quando a primeira chamada acontece (o painel abre mesmo sem env.env)."""
    return load_key()


def estimate_tokens(messages) -> int:
    return sum(len(m["content"]) for m in messages) // CHARS_PER_TOKEN + 4 * len(messages)


class ModelError(Exception):
    def __init__(self, msg, permanent=False):
        super().__init__(msg)
        self.permanent = permanent


def stream_one(model, messages):
    """Gera pedaços de texto de um modelo; levanta ModelError se falhar ou vier vazio."""
    try:
        r = requests.post(
            URL,
            headers={"Authorization": f"Bearer {chave()}"},
            json={"model": model, "messages": messages, "stream": True},
            stream=True,
            timeout=(10, 120),
        )
    except requests.RequestException as e:
        raise ModelError(str(e)) from e
    if r.status_code != 200:
        raise ModelError(f"{r.status_code}: {r.text[:200]}", permanent=r.status_code in (403, 404))
    got = False
    try:
        for line in r.iter_lines():
            raw = line.decode("utf-8")
            if not raw.startswith("data: "):
                continue  # linhas vazias e comentários ": OPENROUTER PROCESSING"
            data = raw[6:]
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            if "error" in chunk:
                raise ModelError(str(chunk["error"]))
            if not chunk.get("choices"):
                continue
            delta = chunk["choices"][0]["delta"].get("content")
            if delta:
                got = True
                yield delta
    except requests.RequestException as e:
        raise ModelError(str(e)) from e
    if not got:
        raise ModelError("resposta vazia (tokens gastos só em raciocínio?)")


def chat_stream(messages, emit):
    """Tenta cada modelo da cadeia em ordem. emit(kind, valor): 'model', 'chunk', 'reset', 'log'."""
    need = estimate_tokens(messages) + OUTPUT_MARGIN
    for model, ctx in CHAIN:
        if blocked_until.get(model, 0) > time.time():
            continue
        if need > ctx:
            emit("log", f"pulando {model}: histórico (~{need:,} tokens) não cabe em {ctx:,}")
            continue
        emit("model", (model, ctx, need))
        try:
            for piece in stream_one(model, messages):
                emit("chunk", piece)
            return model
        except ModelError as e:
            blocked_until[model] = time.time() + (10**9 if e.permanent else COOLDOWN)
            emit("reset", None)  # apaga resposta parcial
            emit("log", f"{model} falhou ({e}); indo para o próximo")
    raise RuntimeError("todos os modelos gratuitos falharam ou não comportam o histórico")


def completar(messages):
    """Resposta inteira (sem streaming) + modelo usado."""
    partes = []

    def emit(tipo, valor):
        if tipo == "chunk":
            partes.append(valor)
        elif tipo == "reset":
            partes.clear()

    modelo = chat_stream(messages, emit)
    return "".join(partes), modelo
