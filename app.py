import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from groq import Groq

# System Prompt Otimizado com Convenção Semântica
OPTIMIZED_SYSTEM_PROMPT = """
# [ROLE & IDENTITY]
Você é um **Professor de Música Sênior, Especialista em Violão e Guitarra**, com profundo domínio em técnica instrumental, teoria musical e história da música.

# [TONE & STYLE]
- **Didático e Explicativo:** Apresente os conceitos de forma clara, passo a passo, tornando o aprendizado acessível.
- **Exemplificação Prática:** Sempre cite exemplos práticos de músicas, riffs, solos ou artistas famosos que utilizam o conceito explicado.

# [BOUNDARIES & SCOPE]
- **Estritamente Musical:** Responda apenas a dúvidas relacionadas à música (teoria, prática, equipamentos, artistas e bandas).
- **Recusa Educada:** Caso receba perguntas fora do escopo musical, redirecione o foco educadamente para o estudo de violão e guitarra.

# [EXPERTISE]
Domínio absoluto de qualquer gênero musical, cifras, tablaturas, escalas, harmonia e improvisação.
"""


class MusicTeacherApp:

  def __init__(self, root):
    self.root = root
    self.root.title("Professor de Violão e Guitarra - Desktop AI")
    self.root.geometry("800x650")
    self.root.minsize(650, 500)

    # Cores do Tema (Estilo IDE Moderna)
    self.bg_color = "#1e1e1e"
    self.panel_bg = "#252526"
    self.fg_color = "#d4d4d4"
    self.accent_color = "#007acc"

    self.root.configure(bg=self.bg_color)

    # Histórico de conversas mantido para o contexto da API
    self.chat_history = [
        {"role": "system", "content": OPTIMIZED_SYSTEM_PROMPT}
    ]

    self.create_widgets()

  def create_widgets(self):
    # Topo: Inserção da API Key
    top_frame = tk.Frame(self.root, bg=self.panel_bg, pady=8, padx=10)
    top_frame.pack(fill="x", padx=10, pady=10)

    lbl_key = tk.Label(
        top_frame,
        text="Groq API Key:",
        font=("Segoe UI", 10, "bold"),
        bg=self.panel_bg,
        fg=self.fg_color,
    )
    lbl_key.pack(side="left", padx=5)

    self.entry_key = tk.Entry(
        top_frame,
        show="*",
        font=("Segoe UI", 10),
        width=45,
        bg="#333333",
        fg=self.fg_color,
        insertbackground="white",
    )
    self.entry_key.pack(side="left", padx=5)

    # Centro: Área de Chat
    chat_frame = tk.Frame(self.root, bg=self.bg_color)
    chat_frame.pack(fill="both", expand=True, padx=10, pady=5)

    self.chat_area = scrolledtext.ScrolledText(
        chat_frame,
        wrap=tk.WORD,
        font=("Segoe UI", 10),
        bg=self.panel_bg,
        fg=self.fg_color,
        insertbackground="white",
        state="disabled",
    )
    self.chat_area.pack(fill="both", expand=True)

    # Configuração de Cores para as Mensagens
    self.chat_area.tag_config(
        "user", foreground="#4ec9b0", font=("Segoe UI", 10, "bold")
    )
    self.chat_area.tag_config(
        "ai", foreground="#ce9178", font=("Segoe UI", 10, "bold")
    )
    self.chat_area.tag_config("text", foreground=self.fg_color)

    # Rodapé: Campo de Mensagem e Botão Enviar
    bottom_frame = tk.Frame(self.root, bg=self.bg_color, pady=10)
    bottom_frame.pack(fill="x", padx=10)

    self.entry_msg = tk.Entry(
        bottom_frame,
        font=("Segoe UI", 11),
        bg=self.panel_bg,
        fg=self.fg_color,
        insertbackground="white",
    )
    self.entry_msg.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=5)
    self.entry_msg.bind("<Return>", lambda event: self.send_message())

    btn_send = tk.Button(
        bottom_frame,
        text="Enviar Pergunta",
        font=("Segoe UI", 10, "bold"),
        bg=self.accent_color,
        fg="#ffffff",
        activebackground="#005999",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        command=self.send_message,
        padx=15,
    )
    btn_send.pack(side="right")

    # Mensagem de Boas-Vindas
    self.append_chat(
        "Professor AI",
        "Olá! Sou seu professor virtual de violão e guitarra. O que vamos"
        " estudar ou praticar hoje?\n\n",
        "ai",
    )

  def append_chat(self, sender, message, tag):
    self.chat_area.config(state="normal")
    self.chat_area.insert(tk.END, f"{sender}: ", tag)
    self.chat_area.insert(tk.END, f"{message}\n\n", "text")
    self.chat_area.config(state="disabled")
    self.chat_area.see(tk.END)

  def send_message(self):
    api_key = self.entry_key.get().strip()
    user_input = self.entry_msg.get().strip()

    if not api_key:
      messagebox.showerror(
          "Erro", "Por favor, insira sua chave da API da Groq."
      )
      return

    if not user_input:
      return

    self.entry_msg.delete(0, tk.END)
    self.append_chat("Você", user_input, "user")
    self.chat_history.append({"role": "user", "content": user_input})

    # Chamada assíncrona para evitar travamento da interface gráfica
    threading.Thread(
        target=self.fetch_ai_response, args=(api_key,), daemon=True
    ).start()

  def fetch_ai_response(self, api_key):
    try:
      client = Groq(api_key=api_key)

      response = client.chat.completions.create(
          model="openai/gpt-oss-120b",
          messages=self.chat_history,
          temperature=1.0,
      )

      answer = response.choices[0].message.content
      self.chat_history.append({"role": "assistant", "content": answer})

      # Atualiza a interface gráfica com segurança na thread principal
      self.root.after(0, lambda: self.append_chat("Professor AI", answer, "ai"))

    except Exception as e:
      self.root.after(
          0,
          lambda: messagebox.showerror(
              "Erro de Conexão", f"Falha ao comunicar com a Groq:\n{e}"
          ),
      )


if __name__ == "__main__":
  root = tk.Tk()
  app = MusicTeacherApp(root)
  root.mainloop()