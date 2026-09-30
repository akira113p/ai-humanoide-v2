"""Chat com IA via OpenRouter, só modelos gratuitos, com fallback automático.

Ordem = maior contexto primeiro. Se um modelo falhar (limite de requisições/tokens, indisponível,
contexto estourado, resposta vazia), o histórico COMPLETO é reenviado ao próximo da lista.

Modo persona: se existir a pasta persona/ (gerada por `python persona.py`), a IA responde como a
persona extraída das DMs: system prompt montado a cada turno com exemplos parecidos com o momento,
resposta quebrada em várias mensagens e enviadas com o ritmo de digitação dela.
"""
import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

import persona
from llm import CHAIN, chat_stream, estimate_tokens

SYSTEM_PROMPT = persona._CFG["CHAT_SYSTEM_PROMPT"]
PERSONA = persona.Persona.carregar()
DEBOUNCE_MS = 2500  # modo persona: espera você parar de mandar msgs antes de ela responder
HISTORY_FILE = Path(__file__).with_name("historico.json")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Chat com {PERSONA.nome} (persona)" if PERSONA else "Chat — modelos gratuitos com fallback")
        self.geometry("760x680")
        self.q = queue.Queue()
        self.busy = False
        self.reply = ""
        self.timer = None  # debounce do modo persona
        self.again = False  # chegou msg nova enquanto ela respondia
        self.messages = self.load_history()

        self.log = scrolledtext.ScrolledText(self, wrap="word", state="disabled", font=("Segoe UI", 11))
        self.log.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self.log.tag_config("user", foreground="#1a5fb4", font=("Segoe UI", 11, "bold"))
        self.log.tag_config("bot", foreground="#26a269", font=("Segoe UI", 11, "bold"))
        self.log.tag_config("sys", foreground="#888888", font=("Segoe UI", 9, "italic"))
        self.log.tag_config("err", foreground="#c01c28")

        self.status = tk.Label(self, anchor="w", fg="#555555", font=("Segoe UI", 9))
        self.status.pack(fill="x", padx=8)

        bar = tk.Frame(self)
        bar.pack(fill="x", padx=8, pady=(2, 8))
        self.entry = tk.Text(bar, height=3, wrap="word", font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.focus()
        side = tk.Frame(bar)
        side.pack(side="right", padx=(6, 0))
        self.send_btn = tk.Button(side, text="Enviar", width=12, command=self.send)
        self.send_btn.pack(fill="x")
        tk.Button(side, text="Nova conversa", width=12, command=self.reset).pack(fill="x", pady=(4, 0))

        for m in self.messages[1:]:
            self.show(m)
        self.update_status()
        self.after(30, self.poll)

    # --- histórico ---
    def load_history(self):
        try:
            msgs = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if msgs and msgs[0]["role"] == "system":
                msgs[0]["content"] = SYSTEM_PROMPT
                return msgs
        except (OSError, ValueError, KeyError):
            pass
        return [{"role": "system", "content": SYSTEM_PROMPT}]

    def save_history(self):
        HISTORY_FILE.write_text(json.dumps(self.messages, ensure_ascii=False, indent=1), encoding="utf-8")

    def reset(self):
        if self.busy:
            return
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.save_history()
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.update_status()

    # --- UI ---
    def write(self, text, tag=None):
        self.log.config(state="normal")
        self.log.insert("end", text, tag)
        self.log.config(state="disabled")
        self.log.see("end")

    def show(self, m):
        if m["role"] == "user":
            self.write("Você: ", "user")
        elif PERSONA:
            for linha in m["content"].split("\n"):
                self.bubble(linha)
            return
        else:
            self.write(f"IA [{m.get('model', '?')}]: ", "bot")
        self.write(m["content"] + ("\n" if PERSONA else "\n\n"))

    def bubble(self, texto):
        self.write(f"{PERSONA.nome}: ", "bot")
        self.write(texto + "\n")

    def update_status(self, model=None, ctx=None):
        used = estimate_tokens(self.messages)
        txt = f"Histórico: {len(self.messages) - 1} msgs, ~{used:,} tokens"
        if model:
            txt += f" | modelo: {model} (contexto {ctx:,}, {used / ctx:.1%} usado)"
        self.status.config(text=txt)

    def on_enter(self, event):
        if event.state & 0x1:  # Shift+Enter = quebra de linha
            return None
        self.send()
        return "break"

    def send(self):
        text = self.entry.get("1.0", "end").strip()
        if not text or (self.busy and not PERSONA):
            return
        self.entry.delete("1.0", "end")
        user = {"role": "user", "content": text}
        self.messages.append(user)
        self.show(user)
        if not PERSONA:
            self.dispatch()
            return
        # várias msgs curtas seguidas viram um turno só: ela responde quando você para de digitar
        if self.timer:
            self.after_cancel(self.timer)
        self.timer = self.after(DEBOUNCE_MS, self.dispatch)

    def dispatch(self):
        self.timer = None
        if self.busy:
            self.again = True
            return
        self.busy = True
        self.again = False
        self.reply = ""
        self.cut = len(self.messages)  # a resposta entra aqui, antes de msgs mandadas enquanto ela digita
        if not PERSONA:
            self.send_btn.config(state="disabled")
        # API só aceita role/content; msgs seguidas do mesmo lado são unidas (uma por linha)
        payload = []
        for m in self.messages:
            if payload and payload[-1]["role"] == m["role"] and m["role"] != "system":
                payload[-1]["content"] += "\n" + m["content"]
            else:
                payload.append({"role": m["role"], "content": m["content"]})
        if PERSONA:
            payload[0]["content"] = PERSONA.system_prompt(self.messages)
            self.status.config(text=f"{PERSONA.nome} está digitando...")
        threading.Thread(target=self.worker, args=(payload,), daemon=True).start()

    def worker(self, payload):
        emit = lambda kind, val: self.q.put((kind, val))
        try:
            emit("done", chat_stream(payload, emit))
        except Exception as e:
            emit("error", str(e))

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.write(f"  · {val}\n", "sys")
                elif PERSONA and kind in ("model", "chunk", "reset"):
                    # resposta é acumulada em silêncio e só aparece depois de humanizada
                    if kind == "model":
                        self.model = val[0]
                    self.reply = "" if kind != "chunk" else self.reply + val
                elif PERSONA and kind == "done":
                    self.type_out(PERSONA.humanizar(self.reply), val)
                elif kind == "model":
                    self.model, ctx, _ = val
                    self.reply = ""
                    self.log.config(state="normal")
                    self.log.mark_set("ai_start", "end-1c")
                    self.log.mark_gravity("ai_start", "left")
                    self.log.config(state="disabled")
                    self.write(f"IA [{self.model}]: ", "bot")
                    self.update_status(self.model, ctx)
                elif kind == "chunk":
                    self.reply += val
                    self.write(val)
                elif kind == "reset":
                    self.reply = ""
                    self.log.config(state="normal")
                    self.log.delete("ai_start", "end-1c")
                    self.log.config(state="disabled")
                elif kind == "error":
                    self.write(f"[erro] {val}\n\n", "err")
                    if not PERSONA:
                        self.messages.pop()  # descarta o turno falho para poder reenviar
                    self.finish()
                elif kind == "done":
                    self.messages.append({"role": "assistant", "content": self.reply, "model": val})
                    self.write("\n\n")
                    self.save_history()
                    self.update_status(val, dict(CHAIN)[val])
                    self.finish()
        except queue.Empty:
            pass
        self.after(30, self.poll)

    def type_out(self, msgs, model):
        """Mostra as msgs uma a uma, com a pausa de digitação medida da persona."""
        def step(i):
            if i == len(msgs):
                self.messages.insert(self.cut, {"role": "assistant", "content": "\n".join(msgs), "model": model})
                self.save_history()
                self.update_status(model, dict(CHAIN)[model])
                self.finish()
                return
            self.bubble(msgs[i])
            self.after(int(PERSONA.atraso(msgs[i + 1]) * 1000) if i + 1 < len(msgs) else 0, step, i + 1)

        self.after(int(max(PERSONA.espera_inicial(), PERSONA.atraso(msgs[0])) * 1000), step, 0)

    def finish(self):
        self.busy = False
        self.send_btn.config(state="normal")
        if self.again and PERSONA:  # você mandou msg enquanto ela respondia
            self.dispatch()


if __name__ == "__main__":
    App().mainloop()
