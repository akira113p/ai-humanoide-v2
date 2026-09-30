"""Painel local do direct: servidor só em 127.0.0.1 + leitor que acompanha a caixa de entrada.

Uso: .venv\\Scripts\\python painel.py  (abre http://127.0.0.1:8765 com o token da execução)
"""

import hmac
import json
import random
import secrets
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from instagrapi.exceptions import ChallengeRequired, ClientError, LoginRequired

import bot
import insta

PORTA = 8765
TOKEN = secrets.token_urlsafe(24)  # muda a cada execução; só a aba aberta pelo painel conhece
PAGINA = Path(__file__).parent / "painel" / "index.html"
INTERVALO = 20  # s: leitura da caixa de entrada
INTERVALO_QUENTE = 8  # s: leitura quando uma conversa com IA ligada teve atividade há pouco
QUENTE = 3 * 60  # s: quanto tempo depois da última msg a conversa com IA conta como "quente"
VARIACAO = 6  # s: +- aleatório no intervalo, para não bater no relógio
PAUSA_CALMA = 15 * 60  # s: parado quando o Instagram pede calma
MANTER = 80  # msgs por conversa no cache do painel
SALVAR_A_CADA = 30  # leituras: regrava a sessão (cookies renovados)
CORPO_MAX = 64 * 1024  # bytes de JSON aceitos num POST
MIDIA_MAX = 20 * 1024 * 1024  # bytes: maior mídia repassada pelo proxy
HOSTS_MIDIA = (".cdninstagram.com", ".fbcdn.net")
HOSTS_OK = {f"127.0.0.1:{PORTA}", f"localhost:{PORTA}"}


class Leitor(threading.Thread):
    """Mantém conversas e mensagens abertas em cache; toda conversa com o Instagram passa por aqui."""

    def __init__(self):
        super().__init__(daemon=True)
        self.ig = insta.Insta()
        self.status = "entrando"  # offline | entrando | online | pausa | erro
        self.aviso = "procurando sessao salva"
        self.pausa_ate = 0
        self.conversas = []
        self.lidas_em = 0
        self.abertas = {}  # thread_id -> {"msgs": [...], "atividade": float}
        self.acordar = threading.Event()
        self.leituras = 0
        self.completando = set()  # conversas buscando histórico maior em segundo plano
        self.bot = bot.Bot(self.ig, ao_mudar=self._recarregar, ao_erro=self._falhou,
                           online=lambda: self.status == "online")

    # ---- estado ----

    def estado(self):
        return {
            "status": self.status, "aviso": self.aviso, "usuario": self.ig.usuario, "pede": self.ig.pede,
            "pausa_ate": self.pausa_ate, "lidas_em": self.lidas_em, "intervalo": self._intervalo(),
            "bot": self.bot.estado(),
        }

    def _falhou(self, e):
        """Traduz erro do Instagram em status do painel. Devolve a mensagem para a API."""
        if isinstance(e, insta.CALMA):
            self.status, self.pausa_ate = "pausa", time.time() + PAUSA_CALMA
            self.aviso = "o Instagram pediu calma; leitura parada por 15 min"
        elif isinstance(e, LoginRequired):
            self.ig.cl = None
            self.status, self.aviso = "offline", "sessao expirou; entre de novo"
        elif isinstance(e, ChallengeRequired):
            self.status, self.aviso = "erro", "o Instagram pediu verificacao: confirme no app oficial e entre de novo"
        elif isinstance(e, ClientError):
            self.aviso = f"erro do Instagram: {str(e)[:160]}"
        else:
            traceback.print_exc()
            self.aviso = f"erro: {type(e).__name__}: {str(e)[:160]}"
        return self.aviso

    # ---- login (roda fora da thread HTTP: pode ficar esperando código) ----

    def em_fundo(self, fn, *args):
        def rodar():
            self.status, self.aviso = "entrando", "entrando..."
            try:
                fn(*args)
            except insta.PrecisaCodigo:
                self.status, self.aviso = "offline", "digite o codigo de 2 fatores"
                return
            except insta.BadPassword:
                self.status, self.aviso = "erro", "senha incorreta"
                return
            except AssertionError:
                self.status, self.aviso = "erro", "cookie sessionid invalido"
                return
            except Exception as e:
                self._falhou(e)
                if self.status == "entrando":
                    self.status = "erro"
                return
            self._online()
        threading.Thread(target=rodar, daemon=True).start()

    def _online(self):
        self.status, self.aviso, self.abertas = "online", f"conectado como @{self.ig.usuario}", {}
        self.acordar.set()

    def sair(self):
        self.ig.sair()
        self.status, self.aviso, self.conversas, self.abertas = "offline", "sessao apagada", [], {}

    # ---- leitura ----

    def run(self):
        try:
            if self.ig.retomar():
                self._online()
            else:
                self.status, self.aviso = "offline", "sem sessao salva; entre com senha ou cookie"
        except Exception as e:
            self._falhou(e)
            self.status = "offline" if self.status == "entrando" else self.status
        while True:
            espera = self._intervalo()
            self.acordar.wait(espera + random.uniform(-VARIACAO, VARIACAO) * espera / INTERVALO)
            self.acordar.clear()
            if self.status == "pausa" and time.time() >= self.pausa_ate:
                self.status, self.aviso = "online", "voltando a ler"
            if self.status == "online":
                self.ler()

    def ler(self):
        """Uma volta: caixa de entrada, que já traz as últimas msgs de cada conversa (sem requisição extra)."""
        try:
            conversas = self.ig.conversas()
            for c in conversas:
                self._guardar(c["id"], c.pop("msgs"), c["atividade"])
            self.conversas = conversas
            self.lidas_em = time.time()
            self.leituras += 1
            self.bot.verificar(self.conversas)
            if self.leituras % SALVAR_A_CADA == 0:
                self.ig._salvar()
        except Exception as e:
            self._falhou(e)

    def _intervalo(self):
        ativos = set(self.bot.estado()["ativos"])
        quente = any(c["id"] in ativos and time.time() - c["atividade"] < QUENTE for c in self.conversas)
        return INTERVALO_QUENTE if quente or self.bot.ocupadas else INTERVALO

    def conversa(self, tid):
        c = next((c for c in self.conversas if c["id"] == tid), None)
        if not c:
            raise ValueError("conversa fora das 20 mais recentes")
        return c

    def _recarregar(self, tid):
        """Depois que a IA mandou algo: atualiza a conversa se ela estiver aberta no painel."""
        if tid in self.abertas:
            try:
                self._buscar(tid)
            except Exception as e:
                self._falhou(e)

    def _guardar(self, tid, msgs, atividade, completa=False):
        """Põe msgs no cache. Da caixa de entrada (parcial) só entra se houve atividade, e junta com o que já tinha."""
        atual = self.abertas.get(tid)
        if atual and not completa:
            if atividade <= atual["atividade"]:
                return
            por_id = {m["id"]: m for m in atual["msgs"]}
            por_id.update({m["id"]: m for m in msgs})
            msgs = sorted(por_id.values(), key=lambda m: m["hora"])[-MANTER:]
        self.abertas[tid] = {"msgs": msgs, "atividade": atividade,
                             "completa": completa or bool(atual and atual.get("completa"))}

    def _buscar(self, tid, rapido=False):
        atividade = next((c["atividade"] for c in self.conversas if c["id"] == tid), 0)
        self._guardar(tid, self.ig.mensagens(tid, rapido=rapido), atividade, completa=True)

    def _completar(self, tid):
        """Em segundo plano: troca as msgs da caixa de entrada pelo histórico maior da conversa aberta."""
        try:
            self._buscar(tid, rapido=True)
        except Exception as e:
            self._falhou(e)
        finally:
            self.completando.discard(tid)

    def mensagens(self, tid):
        """Mensagens da conversa: devolve na hora o que está no cache e busca mais histórico por trás."""
        if self.status not in ("online", "pausa"):
            raise LoginRequired("offline")
        if tid not in self.abertas:  # conversa fora das 20 da caixa de entrada: tem que esperar
            if self.status == "pausa":
                raise insta.PleaseWaitFewMinutes("pausa")
            self._buscar(tid, rapido=True)
        msgs = self.abertas[tid]["msgs"]
        if not self.abertas[tid]["completa"] and self.status == "online" and tid not in self.completando:
            self.completando.add(tid)
            threading.Thread(target=self._completar, args=(tid,), daemon=True).start()
        return msgs

    def enviar(self, tid, texto, responder_a):
        if self.status != "online":
            raise RuntimeError("so da para enviar com o painel online")
        self.ig.enviar(tid, texto, responder_a, rapido=True)
        self._buscar(tid, rapido=True)


leitor = Leitor()


class Painel(BaseHTTPRequestHandler):
    server_version = "painel"

    def log_message(self, fmt, *args):
        pass  # sem log de requisição: URLs de mídia e ids de conversa não vão para o terminal

    # ---- respostas ----

    def _enviar(self, codigo, corpo, tipo="application/json; charset=utf-8", extra=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, dado, codigo=200):
        self._enviar(codigo, json.dumps(dado, ensure_ascii=False).encode("utf-8"),
                     extra={"Cache-Control": "no-store"})

    def _erro(self, msg, codigo=400):
        self._json({"ok": False, "erro": msg}, codigo)

    # ---- guarda ----

    def _permitido(self, token=None):
        """Só 127.0.0.1 com Host certo (contra DNS rebinding) e, na API, o token desta execução."""
        if self.headers.get("Host") not in HOSTS_OK:
            self._erro("host", 403)
            return False
        if self.path.startswith("/api/"):
            token = token or self.headers.get("X-Token", "")
            if not hmac.compare_digest(token.encode(), TOKEN.encode()):
                self._erro("token", 403)
                return False
        return True

    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > CORPO_MAX:
            raise ValueError("corpo grande demais")
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    # ---- rotas ----

    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        if not self._permitido(q.get("t") if url.path == "/api/midia" else None):
            return
        try:
            if url.path in ("/", "/index.html"):
                csp = ("default-src 'self'; img-src 'self' data:; media-src 'self'; style-src 'self' 'unsafe-inline'; "
                       "script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
                self._enviar(200, PAGINA.read_bytes(), "text/html; charset=utf-8",
                             {"Content-Security-Policy": csp, "Cache-Control": "no-store"})
            elif url.path == "/api/estado":
                self._json(leitor.estado())
            elif url.path == "/api/conversas":
                self._json({"conversas": leitor.conversas, "lidas_em": leitor.lidas_em})
            elif url.path == "/api/mensagens":
                tid = insta._so_digitos(q.get("id", ""))
                self._json({"mensagens": leitor.mensagens(tid)})
            elif url.path == "/api/contato":
                tid = insta._so_digitos(q.get("id", ""))
                self._json({"contato": leitor.bot.contato(tid), "memoria": leitor.bot.memoria(tid),
                            "persona": leitor.bot.estado()["persona"]})
            elif url.path == "/api/midia":
                self._midia(q.get("u", ""))
            else:
                self._erro("rota", 404)
        except ValueError as e:
            self._erro(str(e))
        except Exception as e:
            self._erro(leitor._falhou(e), 502)

    def do_POST(self):
        if not self._permitido():
            return
        try:
            d = self._corpo()
            rota = urlparse(self.path).path
            if rota == "/api/login":
                if d.get("sessionid"):
                    leitor.em_fundo(leitor.ig.entrar_cookie, str(d["sessionid"]))
                elif d.get("usuario") and d.get("senha"):
                    leitor.em_fundo(leitor.ig.entrar, str(d["usuario"]).strip().lstrip("@"), str(d["senha"]))
                else:
                    return self._erro("informe usuario e senha, ou o cookie sessionid")
            elif rota == "/api/codigo":
                cod = str(d.get("codigo", "")).strip()
                if leitor.ig.pede == "codigo":
                    leitor.ig.dar_codigo(cod)
                elif leitor.ig.pede == "2fa":
                    leitor.em_fundo(leitor.ig.entrar_2fa, cod)
                else:
                    return self._erro("nenhum login esperando codigo")
            elif rota == "/api/sair":
                leitor.sair()
            elif rota == "/api/atualizar":
                leitor.acordar.set()
            elif rota == "/api/contato":
                tid = insta._so_digitos(d.get("id", ""))
                campos = {k: d[k] for k in ("ativo", "origem") if isinstance(d.get(k), bool)}
                if d.get("velocidade") in bot.VELOCIDADES:
                    campos["velocidade"] = d["velocidade"]
                if isinstance(d.get("notas"), str):
                    campos["notas"] = d["notas"][:2000]
                c = leitor.conversa(tid)
                if c["grupo"] and campos.get("ativo"):
                    return self._erro("a IA so responde conversa de uma pessoa, nao grupo")
                return self._json({"ok": True, "contato": leitor.bot.ajustar(tid, c, **campos)})
            elif rota == "/api/puxar":
                leitor.bot.puxar(leitor.conversa(insta._so_digitos(d.get("id", ""))))
            elif rota == "/api/memoria":
                leitor.bot.refazer_memoria(leitor.conversa(insta._so_digitos(d.get("id", ""))))
            elif rota == "/api/enviar":
                tid = insta._so_digitos(d.get("id", ""))
                resp = d.get("responder_a")
                if resp:
                    resp = {"id": insta._so_digitos(resp.get("id", "")), "ctx": str(resp.get("ctx", ""))[:100]}
                leitor.enviar(tid, str(d.get("texto", "")), resp)
                return self._json({"ok": True, "mensagens": leitor.abertas[tid]["msgs"]})
            else:
                return self._erro("rota", 404)
            self._json({"ok": True})
        except (ValueError, RuntimeError) as e:
            self._erro(str(e))
        except Exception as e:
            self._erro(leitor._falhou(e), 502)

    def _midia(self, u):
        """Repassa imagem/áudio do CDN do Instagram (o CDN recusa carregar direto em outra origem)."""
        p = urlparse(u)
        if p.scheme != "https" or not (p.hostname or "").endswith(HOSTS_MIDIA):
            return self._erro("url de midia nao permitida", 403)
        r = requests.get(u, timeout=15, stream=True, allow_redirects=False)
        tipo = r.headers.get("Content-Type", "")
        if r.status_code != 200 or not tipo.startswith(("image/", "audio/", "video/")):
            return self._erro("midia indisponivel", 404)
        corpo = r.raw.read(MIDIA_MAX + 1, decode_content=True)
        if len(corpo) > MIDIA_MAX:
            return self._erro("midia grande demais", 413)
        self._enviar(200, corpo, tipo, {"Cache-Control": "private, max-age=3600"})


class Servidor(ThreadingHTTPServer):
    allow_reuse_address = False  # no Windows, True deixaria um segundo painel abrir a mesma porta em silêncio


def main():
    leitor.start()
    srv = Servidor(("127.0.0.1", PORTA), Painel)
    url = f"http://127.0.0.1:{PORTA}/#t={TOKEN}"
    print(f"painel em {url}\n(ctrl+c para parar)")
    webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if leitor.ig.logado:
            leitor.ig._salvar()


if __name__ == "__main__":
    main()
