"""Conexão com o direct do Instagram (instagrapi, API privada): sessão, conversas, mensagens e envio.

Lê o JSON cru do Instagram em vez dos modelos pydantic da lib: quando o Instagram muda um formato,
só aquela mensagem vira "[tipo]" em vez de a conversa inteira falhar na validação.
"""

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword, ChallengeRequired, ClientError, FeedbackRequired, LoginRequired, PleaseWaitFewMinutes,
    RateLimitError, TwoFactorRequired,
)

BASE = Path(__file__).parent
SESSAO = BASE / "sessao" / "instagram.json"  # cookies + ids do aparelho (privado)
PAUSA_REQ = [1, 3]  # s: pausa aleatória antes de cada requisição feita em segundo plano
PAUSA_RAPIDA = [0.2, 0.6]  # s: pausa quando você está esperando na tela (abrir conversa, enviar)
MSGS_INBOX = 20  # msgs de cada conversa que já vêm junto com a caixa de entrada (abre conversa sem requisição)
ESPERA_CODIGO = 300  # s: quanto o login espera o código de verificação digitado no painel
MSGS_POR_CONVERSA = 40
PAGINA = 50  # msgs pedidas por requisição; se o Instagram mandar menos, pagina
LIMITE_TEXTO = 1000  # caracteres por mensagem enviada

# o Instagram pedindo calma: quem chama deve parar um tempo
CALMA = (PleaseWaitFewMinutes, RateLimitError, FeedbackRequired)


class PrecisaCodigo(Exception):
    """Login parado esperando código (2FA ou verificação por e-mail/SMS)."""


class Insta:
    """Uma conta logada; seguro para uso por várias threads (uma requisição por vez)."""

    def __init__(self):
        self.cl = None
        self.usuario = None
        self.trava = threading.RLock()
        self.pede = None  # None | "2fa" | "codigo"
        self._codigo = None
        self._chegou_codigo = threading.Event()
        self._login = None  # (usuario, senha) só em memória, enquanto espera o 2FA

    # ---- sessão ----

    def _cliente(self, reaproveitar=True):
        """Cliente novo; reaproveita aparelho/cookies salvos para o Instagram ver sempre o mesmo celular."""
        cl = Client(delay_range=PAUSA_REQ)
        cl.challenge_code_handler = self._esperar_codigo
        if reaproveitar and SESSAO.exists():
            cl.load_settings(SESSAO)
        return cl

    def _salvar(self):
        SESSAO.parent.mkdir(exist_ok=True)
        self.cl.dump_settings(SESSAO)

    def retomar(self):
        """Tenta usar a sessão salva; True se ela ainda vale."""
        if not SESSAO.exists():
            return False
        with self.trava:
            cl = self._cliente()
            if not cl.user_id:
                return False
            try:
                conta = cl.account_info()
            except LoginRequired:
                return False
            self.cl, self.usuario = cl, conta.username
            self._salvar()
            return True

    def entrar(self, usuario, senha, codigo=""):
        """Login por senha. Levanta PrecisaCodigo se o Instagram pedir 2FA."""
        with self.trava:
            cl = self._cliente()
            cl.relogin_attempt = 0
            try:
                cl.login(usuario, senha, relogin=bool(cl.user_id), verification_code=codigo)
            except TwoFactorRequired:
                self._login, self.pede = (usuario, senha), "2fa"
                raise PrecisaCodigo("2fa")
            finally:
                if self.pede == "codigo":
                    self.pede = None
            self._login, self.pede = None, None
            self.cl, self.usuario = cl, cl.username or usuario
            self._salvar()

    def entrar_2fa(self, codigo):
        """Segunda etapa do login com o código do app autenticador/SMS."""
        if not self._login:
            raise ValueError("nenhum login esperando código")
        self.entrar(*self._login, codigo=codigo.strip())

    def entrar_cookie(self, sessionid):
        """Login com o cookie sessionid copiado do navegador (não pede senha nem 2FA)."""
        with self.trava:
            cl = self._cliente(reaproveitar=False)
            antigo = json.loads(SESSAO.read_text(encoding="utf-8")) if SESSAO.exists() else {}
            if antigo.get("uuids"):
                cl.set_uuids(antigo["uuids"])
            if antigo.get("device_settings"):
                cl.set_device(antigo["device_settings"])
            cl.login_by_sessionid(sessionid.strip())
            self.cl, self.usuario = cl, cl.username
            self._salvar()

    def _esperar_codigo(self, usuario, escolha):
        """challenge_code_handler da lib: bloqueia até o painel mandar o código (e-mail/SMS)."""
        self._codigo, self.pede = None, "codigo"
        self._chegou_codigo.clear()
        self._chegou_codigo.wait(ESPERA_CODIGO)
        self.pede = None
        return self._codigo or ""

    def dar_codigo(self, codigo):
        """Entrega o código de verificação para o login que está esperando."""
        self._codigo = codigo.strip()
        self._chegou_codigo.set()

    def sair(self):
        """Esquece a sessão (apaga o arquivo; a conta continua logada nos outros aparelhos)."""
        with self.trava:
            self.cl, self.usuario = None, None
            if SESSAO.exists():
                SESSAO.unlink()

    @property
    def logado(self):
        return self.cl is not None

    @property
    def meu_id(self):
        return str(self.cl.user_id)

    # ---- direct ----

    def _req(self, endpoint, params, rapido=False):
        with self.trava:
            if not self.cl:
                raise LoginRequired("sem sessão")
            antes = self.cl.delay_range
            if rapido:
                self.cl.delay_range = PAUSA_RAPIDA
            try:
                return self.cl.private_request(endpoint, params=params)
            finally:
                self.cl.delay_range = antes

    def conversas(self, qtd=20):
        """Caixa de entrada: id, titulo, usuarios, ultima msg, não lida e as últimas msgs de cada conversa."""
        if not self.cl:
            raise LoginRequired("sem sessão")
        params = {
            **self.cl._direct_request_tracking_params(),
            "visual_message_return_type": "unseen", "thread_message_limit": str(MSGS_INBOX), "persistentBadging": "true",
            "limit": str(qtd), "is_prefetching": "false", "fetch_reason": "initial_snapshot",
        }
        caixa = self._req("direct_v2/inbox/", params).get("inbox", {})
        return [self._conversa(t) for t in caixa.get("threads", [])]

    def _conversa(self, t):
        usuarios = {_uid(u): u.get("username", "?") for u in t.get("users", [])}
        msgs = [self.normalizar(i, usuarios) for i in reversed(t.get("items") or [])]
        ultima = msgs[-1] if msgs else None
        visto = (t.get("last_seen_at") or {}).get(self.meu_id, {}).get("item_id")
        return {
            "id": str(t.get("thread_id")),
            "titulo": t.get("thread_title") or ", ".join(usuarios.values()) or "?",
            "grupo": bool(t.get("is_group")),
            "usuarios": list(usuarios.values()),
            "perfis": [{"usuario": u.get("username", "?"), "nome": u.get("full_name") or ""} for u in t.get("users", [])],
            "atividade": int(t.get("last_activity_at", 0)) / 1e6,
            "ultima": ultima,
            "nao_lida": bool(ultima and not ultima["de_mim"] and visto != ultima["id"]),
            "msgs": msgs,
        }

    def mensagens(self, thread_id, qtd=MSGS_POR_CONVERSA, rapido=False):
        """Últimas mensagens da conversa, da mais antiga para a mais nova."""
        thread_id = _so_digitos(thread_id)
        params = {"visual_message_return_type": "unseen", "direction": "older", "limit": str(min(qtd, PAGINA))}
        itens, usuarios = [], {}
        while len(itens) < qtd:
            t = self._req(f"direct_v2/threads/{thread_id}/", params, rapido).get("thread", {})
            usuarios.update({_uid(u): u.get("username", "?") for u in t.get("users", [])})
            itens += t.get("items", [])
            if not t.get("has_older") or not t.get("oldest_cursor") or not t.get("items"):
                break
            params["cursor"] = t["oldest_cursor"]
        return [self.normalizar(i, usuarios) for i in reversed(itens[:qtd])]

    def enviar(self, thread_id, texto, responder_a=None, rapido=False):
        """Manda texto; responder_a = {"id", "ctx"} de uma msg normalizada marca a resposta."""
        texto = texto.strip()
        if not texto or len(texto) > LIMITE_TEXTO:
            raise ValueError(f"texto vazio ou com mais de {LIMITE_TEXTO} caracteres")
        alvo = None
        if responder_a:
            alvo = SimpleNamespace(id=str(responder_a["id"]), client_context=responder_a.get("ctx") or "")
        with self.trava:
            antes = self.cl.delay_range
            if rapido:
                self.cl.delay_range = PAUSA_RAPIDA
            try:
                self.cl.direct_send(texto, thread_ids=[int(_so_digitos(thread_id))], reply_to_message=alvo)
            except (KeyError, TypeError, ValueError):
                # a msg já foi; o que falhou foi a lib montar o objeto de retorno
                if (self.cl.last_json or {}).get("status") != "ok":
                    raise
            finally:
                self.cl.delay_range = antes

    def marcar_visto(self, thread_id, item_id):
        with self.trava:
            self.cl.direct_message_seen(int(_so_digitos(thread_id)), item_id)

    # ---- normalização ----

    def normalizar(self, item, usuarios=None, _aninhada=False):
        """Item cru do direct -> dict estável: texto, anexo (reels, post, foto...), resposta_a e para_llm."""
        usuarios = usuarios or {}
        tipo = item.get("item_type", "?")
        autor_id = str(item.get("user_id", ""))
        de_mim = bool(item.get("is_sent_by_viewer")) or (self.cl is not None and autor_id == self.meu_id)
        texto, anexo = _conteudo(item, tipo)
        msg = {
            "id": str(item.get("item_id", "")),
            "ctx": item.get("client_context") or "",
            "tipo": tipo,
            "de_mim": de_mim,
            "autor": "voce" if de_mim else usuarios.get(autor_id, autor_id or "?"),
            "hora": int(item.get("timestamp", 0)) / 1e6,
            "texto": texto,
            "anexo": anexo,
            "resposta_a": None,
            "reacoes": [r.get("emoji", "") for r in (item.get("reactions") or {}).get("emojis", [])],
        }
        orig = item.get("replied_to_message")
        if orig and not _aninhada:
            r = self.normalizar(orig, usuarios, _aninhada=True)
            msg["resposta_a"] = {"id": r["id"], "autor": r["autor"], "texto": r["texto"], "anexo": r["anexo"]}
        msg["para_llm"] = para_llm(msg)
        return msg


def _uid(u):
    return str(u.get("pk") or u.get("pk_id") or u.get("id") or "")


def _so_digitos(x):
    x = str(x)
    if not x.isdigit():
        raise ValueError("id inválido")
    return x


def _thumb(m):
    """Maior imagem de um objeto de mídia do Instagram (post, reels, story, foto do direct)."""
    if not m:
        return ""
    if m.get("carousel_media"):
        m = m["carousel_media"][0]
    cands = (m.get("image_versions2") or {}).get("candidates") or []
    return cands[0].get("url", "") if cands else ""


def _midia(m, tipo):
    """Post/reels/story (media_v1) -> anexo."""
    m = m or {}
    if m.get("product_type") == "clips" and tipo == "post":
        tipo = "reels"
    code = m.get("code")
    rota = "reel" if tipo == "reels" else "p"
    return {
        "tipo": tipo,
        "autor": (m.get("user") or {}).get("username", ""),
        "legenda": ((m.get("caption") or {}).get("text") or "")[:300],
        "thumb": _thumb(m),
        "url": f"https://www.instagram.com/{rota}/{code}/" if code and tipo != "story" else "",
    }


def _xma(lista, padrao):
    """Formato novo (xma_*): cartão com target_url, title_text, preview_url."""
    x = (lista or [{}])[0]
    url = x.get("target_url") or ""
    tipo = padrao
    if "/reel/" in url or "/reels/" in url:
        tipo = "reels"
    elif "/p/" in url:
        tipo = "post"
    elif "/stories/" in url and padrao == "link":
        tipo = "story"
    return {
        "tipo": tipo,
        "autor": (x.get("header_title_text") or x.get("title_text") or "").lstrip("@"),
        "legenda": (x.get("caption_body_text") or x.get("subtitle_text") or "")[:300],
        "thumb": x.get("preview_url") or "",
        "url": url,
    }


def _conteudo(item, tipo):
    """(texto, anexo) de cada tipo de item conhecido; desconhecido vira texto "[tipo]"."""
    texto = item.get("text") or ""
    if tipo == "text":
        return texto, None
    if tipo == "link":
        link = item.get("link") or {}
        ctx = link.get("link_context") or {}
        return link.get("text") or texto, {"tipo": "link", "autor": "", "legenda": ctx.get("link_title") or "",
                                           "thumb": ctx.get("link_image_url") or "", "url": ctx.get("link_url") or ""}
    if tipo == "clip":
        clip = item.get("clip") or {}
        return texto, _midia(clip.get("clip", clip), "reels")
    if tipo == "media_share":
        return texto, _midia(item.get("media_share"), "post")
    if tipo in ("xma_clip", "xma_media_share", "generic_xma", "xma_link"):
        return texto, _xma(item.get(tipo), "reels" if tipo == "xma_clip" else "post" if tipo == "xma_media_share"
                           else "link")
    if tipo in ("reel_share", "xma_reel_share", "xma_story_share", "story_share"):
        return _story(item, tipo, texto)
    if tipo in ("media", "raw_media", "visual_media"):
        m = item.get("media") or (item.get("visual_media") or {}).get("media") or {}
        video = m.get("media_type") == 2
        temp = tipo != "media"
        return texto, {"tipo": "video" if video else "foto", "autor": "", "legenda": "temporaria" if temp else "",
                       "thumb": _thumb(m), "url": ""}
    if tipo == "voice_media":
        audio = ((item.get("voice_media") or {}).get("media") or {}).get("audio") or {}
        seg = round((audio.get("duration") or 0) / 1000)
        return texto, {"tipo": "audio", "autor": "", "legenda": f"{seg}s", "thumb": "",
                       "url": audio.get("audio_src") or ""}
    if tipo == "animated_media":
        a = item.get("animated_media") or {}
        url = ((a.get("images") or {}).get("fixed_height") or {}).get("url", "")
        return texto, {"tipo": "figurinha" if a.get("is_sticker") else "gif", "autor": "", "legenda": "",
                       "thumb": url, "url": ""}
    if tipo == "like":
        return item.get("like") or "❤️", None
    if tipo == "profile":
        p = item.get("profile") or {}
        return texto, {"tipo": "perfil", "autor": p.get("username", ""), "legenda": p.get("full_name", ""),
                       "thumb": "", "url": f"https://www.instagram.com/{p.get('username', '')}/"}
    if tipo == "action_log":
        return (item.get("action_log") or {}).get("description") or "", {"tipo": "sistema", "autor": "",
                                                                         "legenda": "", "thumb": "", "url": ""}
    if tipo == "placeholder":
        ph = item.get("placeholder") or {}
        return texto, {"tipo": "indisponivel", "autor": "", "legenda": ph.get("message") or ph.get("title") or "",
                       "thumb": "", "url": ""}
    return texto or f"[{tipo}]", None


def _story(item, tipo, texto):
    """Resposta/menção/reação a story, ou story compartilhado. (Tratamento completo fica para depois.)"""
    if tipo.startswith("xma_"):
        anexo = _xma(item.get(tipo), "story")
        anexo["tipo"] = "story"
    else:
        dado = item.get(tipo) or {}
        anexo = _midia(dado.get("media"), "story")
        if not dado.get("media"):
            anexo["legenda"] = dado.get("message") or dado.get("title") or "story indisponivel"
        texto = dado.get("text") or texto
        acao = dado.get("type")
        if acao:
            anexo["acao"] = {"reply": "respondeu", "mention": "mencionou", "reaction": "reagiu"}.get(acao, acao)
    return texto, anexo


NOMES_ANEXO = {"reels": "reels", "post": "post", "story": "story", "foto": "foto", "video": "video", "audio": "audio",
               "gif": "gif", "figurinha": "figurinha", "link": "link", "perfil": "perfil"}


def descrever(anexo):
    """Anexo -> texto curto entre colchetes, do jeito que um LLM entende."""
    if not anexo or anexo["tipo"] in ("sistema",):
        return ""
    if anexo["tipo"] == "indisponivel":
        return "[conteudo indisponivel]"
    if anexo["tipo"] in ("audio", "foto", "video"):
        return f"[mandou {anexo['tipo']} {anexo.get('legenda', '')}]".replace(" ]", "]")
    partes = [NOMES_ANEXO.get(anexo["tipo"], anexo["tipo"])]
    if anexo.get("autor"):
        partes.append(f"de @{anexo['autor']}")
    if anexo.get("legenda"):
        partes.append(f'"{anexo["legenda"][:150]}"')
    acao = anexo.get("acao")
    return f"[{acao} ao {' '.join(partes)}]" if acao else f"[mandou {' '.join(partes)}]"


def para_llm(msg):
    """Uma linha com tudo que o modelo precisa saber da mensagem (resposta marcada + anexo + texto)."""
    partes = []
    r = msg.get("resposta_a")
    if r:
        alvo = r["texto"] or descrever(r["anexo"]) or "uma mensagem"
        partes.append(f'[respondendo a {r["autor"]}: "{alvo[:150]}"]')
    if msg["anexo"]:
        partes.append(descrever(msg["anexo"]))
    if msg["texto"]:
        partes.append(msg["texto"])
    return " ".join(p for p in partes if p)
