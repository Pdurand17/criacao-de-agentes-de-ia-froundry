import os
import sqlite3
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import streamlit as st
from dotenv import load_dotenv
from openai import AzureOpenAI, APIError, APITimeoutError, RateLimitError

load_dotenv(override=True)

# Configuração obrigatória mantida rigorosamente
client = AzureOpenAI(
    azure_endpoint=os.getenv("ENDPOINT"),
    api_key=os.getenv("API_KEY"),
    api_version=os.getenv("API_VERSION", "2025-04-01-preview")
)
deployment_name = os.getenv("GPT5_MODEL")

# --- GERENCIAMENTO DE MEMÓRIA (BANCO DE DADOS DE HISTÓRICO) ---
def inicializar_banco_historico():
    try:
        con = sqlite3.connect('chat_history.db')
        cursor = con.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT
            )
        ''')
        con.commit()
    except Exception as e:
        st.error(f"Erro ao inicializar banco de histórico: {e}")
    finally:
        con.close()

def salvar_mensagem(role, content):
    try:
        con = sqlite3.connect('chat_history.db')
        cursor = con.cursor()
        cursor.execute('INSERT INTO historico (role, content) VALUES (?, ?)', (role, content))
        con.commit()
    except Exception as e:
        print(f"Erro ao salvar mensagem no histórico: {e}")
    finally:
        con.close()

def carregar_historico():
    try:
        con = sqlite3.connect('chat_history.db')
        cursor = con.cursor()
        cursor.execute('SELECT role, content FROM historico')
        mensagens = cursor.fetchall()
        return [{"role": r, "content": c} for r, c in mensagens]
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        return []
    finally:
        con.close()

# --- FUNÇÕES DE RETRIEVAL COM FALLBACKS ROBUSTOS ---

@st.cache_data
def raspar_site():
    url = "https://gratuitos.netlify.app/"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        texto = soup.get_text(separator="\n", strip=True)
        if not texto:
            raise ValueError("O conteúdo extraído do site está vazio.")
        return texto[:3000]
    except requests.exceptions.Timeout:
        return "[Fallback] Aviso: O site demorou muito para responder (Timeout). Utilizando informações em cache ou base alternativa."
    except Exception as e:
        return f"[Fallback] Aviso: Não foi possível acessar o site no momento ({e})."

@st.cache_data
def ler_pdf():
    caminho_pdf = "arquivo.pdf"
    if not os.path.exists(caminho_pdf):
        return "[Fallback] Arquivo PDF institucional não encontrado no servidor."
    try:
        reader = PdfReader(caminho_pdf)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() or ""
        if not texto.strip():
            return "[Fallback] O PDF está vazio ou corrompido."
        return texto[:3000]
    except Exception as e:
        return f"[Fallback] Erro ao ler o PDF: {e}"

def carregar_dados_locais():
    # CSV 1
    try:
        dados_csv = pd.read_csv('dados.csv').head(50).to_string()
    except Exception:
        dados_csv = "[Fallback] dados.csv indisponível."

    # CSV 2
    try:
        t_csv = pd.read_csv('tic.csv').head(50).to_string()
    except Exception:
        t_csv = "[Fallback] tic.csv indisponível."

    # Banco de Dados SQLite Local (Vendas)
    try:
        con = sqlite3.connect('banco.db')
        cursor = con.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vendas(
                            venda REAL,
                            vendedor TEXT,
                            id TEXT)''')
        con.commit()
        cursor.execute('SELECT * FROM vendas')
        resultados = cursor.fetchall()
        dados_db = str(resultados) if resultados else "Banco de dados de vendas vazio."
        con.close()
    except Exception as e:
        dados_db = f"[Fallback] Erro ao acessar o banco de dados local de vendas: {e}"

    return dados_csv, t_csv, dados_db

# --- ORQUESTRAÇÃO DE FLUXOS (ROTEAMENTO INTELIGENTE) ---
def orquestrar_fontes(pergunta: str):
    """
    Analisa a pergunta do usuário para decidir quais bases de conhecimento
    devem ser acionadas (Fluxos Combinados e Direcionados).
    """
    p = pergunta.lower()
    fontes_ativadas = []
    
    # Heurísticas de Roteamento baseadas em intenção
    pergunta_sobre_vendas = any(k in p for k in ["venda", "vendedor", "faturamento", "comissão", "lucro", "meta", "id"])
    pergunta_sobre_cursos_site = any(k in p for k in ["curso", "site", "gratuito", "plataforma", "aula", "inscrição"])
    pergunta_sobre_documentos = any(k in p for k in ["documento", "regra", "termo", "pdf", "política", "manual"])
    
    # Se nenhuma palavra-chave específica for forte o suficiente, aciona o fluxo padrão combinado (todas as fontes principais)
    if not (pergunta_sobre_vendas or pergunta_sobre_cursos_site or pergunta_sobre_documentos):
        pergunta_sobre_vendas = pergunta_sobre_cursos_site = pergunta_sobre_documentos = True

    dados_csv, t_csv, dados_db = "", "", ""
    conteudo_site = ""
    conteudo_pdf = ""

    # Execução seletiva ou paralela controlada de fontes
    if pergunta_sobre_vendas:
        d_csv, t_c, d_db = carregar_dados_locais()
        dados_csv, t_csv, dados_db = d_csv, t_c, d_db
        fontes_ativadas.append("Banco/CSVs de Vendas")

    if pergunta_sobre_cursos_site:
        conteudo_site = raspar_site()
        fontes_ativadas.append("Web Scraping")

    if pergunta_sobre_documentos:
        conteudo_pdf = ler_pdf()
        fontes_ativadas.append("Documento PDF")

    # Montagem dinâmica do prompt do sistema com base no roteamento
    prompt_sistema = f"""
Você é um assistente de atendimento inteligente e especialista. Responda à dúvida do usuário utilizando EXCLUSIVAMENTE os contextos obtidos abaixo pelas fontes ativas ({', '.join(fontes_ativadas)}):

----[DADOS DO SITE]----
{conteudo_site if conteudo_site else "Não consultado para esta pergunta."}

----[CONTEÚDO DO PDF]----
{conteudo_pdf if conteudo_pdf else "Não consultado para esta pergunta."}

----[DADOS DO CSV 1]----
{dados_csv if dados_csv else "Não consultado."}

----[DADOS DO CSV 2]----
{t_csv if t_csv else "Não consultado."}

----[BANCO DE DADOS DE VENDAS]----
{dados_db if dados_db else "Não consultado."}
"""
    return prompt_sistema, fontes_ativadas

# --- APLICAÇÃO STREAMLIT ---

def main():
    st.set_page_config(page_title="Agente IA - Atendimento", page_icon="🤖", layout="centered")

    st.title("🤖 Agente Virtual Inteligente (Com Orquestração & Fallbacks)")
    st.write("Faça suas perguntas. O agente roteará automaticamente para a base correta.")

    # Inicializa o banco de memória de chat
    inicializar_banco_historico()

    # Recupera o histórico salvo no banco de dados SQLite
    historico = carregar_historico()

    # Exibe as mensagens anteriores
    for mensagem in historico:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

    # Campo de entrada de chat do Streamlit
    if pergunta := st.chat_input("Digite sua dúvida..."):
        if not os.getenv("ENDPOINT") or not os.getenv("API_KEY") or not deployment_name:
            st.error("Erro de configuração: Variáveis de ambiente da Azure ausentes.")
            return

        # Adiciona a mensagem do usuário na tela e salva no banco
        with st.chat_message("user"):
            st.markdown(pergunta)
        salvar_mensagem("user", pergunta)

        # 1. Orquestração e Seleção de Contextos
        with st.spinner("Analisando intenção e roteando para fontes de conhecimento..."):
            prompt_sistema, fontes_usadas = orquestrar_fontes(pergunta)

        # Prepara o payload de mensagens com memória conversacional (últimas 6 interações)
        mensagens_api = [{"role": "system", "content": prompt_sistema}]
        for m in historico[-6:]:
            mensagens_api.append({"role": m["role"], "content": m["content"]})
        mensagens_api.append({"role": "user", "content": pergunta})

        max_tentativas = 3
        resposta_texto = ""

        # 3. Fallbacks Robustos para a Chamada da API Azure OpenAI
        for tentativa in range(max_tentativas):
            try:
                with st.spinner(f"Consultando fontes ({', '.join(fontes_usadas)}) e gerando resposta..."):
                    response = client.chat.completions.create(
                        model=deployment_name,
                        messages=mensagens_api,
                        temperature=1.0
                    )
                    resposta_texto = response.choices[0].message.content
                    break
            except RateLimitError:
                if tentativa < max_tentativas - 1:
                    time.sleep(5)
                else:
                    resposta_texto = "⚠️ O limite de requisições/tokens da API foi atingido (Rate Limit 429). Por favor, tente novamente em instantes."
            except APITimeoutError:
                if tentativa < max_tentativas - 1:
                    time.sleep(3)
                else:
                    resposta_texto = "⚠️ A conexão com a Azure OpenAI expirou (Timeout). Nossa equipe técnica já foi notificada."
            except APIError as e:
                resposta_texto = f"⚠️ Erro na API Azure: {e}. Direcionando para atendimento humano se o problema persistir."
                break
            except Exception as e:
                resposta_texto = f"⚠️ Ocorreu um erro inesperado no fluxo do agente: {e}. Por favor, tente reformular sua pergunta."
                break

        # Exibe a resposta do assistente e salva na memória persistente
        with st.chat_message("assistant"):
            st.markdown(resposta_texto)
            if fontes_usadas:
                st.caption(f"*(Fontes consultadas: {', '.join(fontes_usadas)})*")
                
        salvar_mensagem("assistant", resposta_texto)

if __name__ == "__main__":
    main()