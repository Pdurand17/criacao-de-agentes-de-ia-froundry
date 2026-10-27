import os
import sqlite3
from datetime import datetime
import streamlit as st
from openai import AzureOpenAI

# Configuração do Banco de Dados SQLite
DB_NAME = "sistema_agente.db"

def inicializar_banco():
    """Inicializa o banco de dados e cria a tabela 'produtos' se não existir."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                resposta TEXT,
                status TEXT DEFAULT 'PENDENTE',
                data_hora TEXT NOT NULL
            )
        ''')
        # Inserção de dados de teste iniciais, caso a tabela esteja vazia
        cursor.execute('SELECT COUNT(*) FROM produtos')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO produtos (prompt, resposta, status, data_hora)
                VALUES (?, ?, ?, ?)
            ''', (
                "Analisar logs de erro do sistema de pagamentos.",
                "Logs analisados. Nenhum erro crítico encontrado.",
                "CONCLUIDO",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao inicializar o banco de dados: {e}")

# 1. Ferramenta: consultar_prompt
def consultar_prompt(item_id: int) -> dict:
    """
    Consulta os detalhes completos de um registro/prompt na tabela 'produtos' com base no ID.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, prompt, resposta, status, data_hora FROM produtos WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {"erro": f"Item com ID {item_id} não encontrado."}
    except sqlite3.Error as e:
        return {"erro": f"Erro no banco de dados: {str(e)}"}

# 2. Ferramenta: verificar_prompt
def verificar_prompt(item_id: int) -> str:
    """
    Verifica o status atual e a existência de um prompt específico no banco de dados.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT status, data_hora FROM produtos WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return f"Item ID {item_id} encontrado. Status: {row[0]} | Data/Hora: {row[1]}"
        return f"Item ID {item_id} não existe na base de dados."
    except sqlite3.Error as e:
        return f"Erro ao verificar o prompt: {str(e)}"

# Configuração do Cliente Azure OpenAI (Azure Foundry)
def obter_cliente_azure():
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

# Interface Gráfica com Streamlit (Template)
def main():
    st.set_page_config(page_title="Agente de IA - Azure Foundry", page_icon="🤖", layout="wide")
    inicializar_banco()

    st.title("🤖 Agente de IA Corporativo (Azure Foundry)")
    st.markdown("Sistema integrado com banco de dados SQLite para gerenciamento de prompts e auditoria.")

    # Sidebar para Ferramentas e Configurações
    st.sidebar.header("Painel de Ferramentas (Tools)")
    escolha_ferramenta = st.sidebar.selectbox("Selecionar Ação", ["Chat com Agente", "Consultar Prompt por ID", "Verificar Status"])

    if escolha_ferramenta == "Consultar Prompt por ID":
        st.subheader("Ferramenta: consultar_prompt")
        item_id = st.sidebar.number_input("Digite o ID do item:", min_value=1, step=1, value=1)
        if st.sidebar.button("Executar Consulta"):
            resultado = consultar_prompt(item_id)
            st.json(resultado)

    elif escolha_ferramenta == "Verificar Status":
        st.subheader("Ferramenta: verificar_prompt")
        item_id = st.sidebar.number_input("Digite o ID para verificação:", min_value=1, step=1, value=1)
        if st.sidebar.button("Verificar"):
            status_res = verificar_prompt(item_id)
            st.info(status_res)

    else:
        st.subheader("Sessão do Agente de IA")
        user_input = st.text_area("Digite sua solicitação para o agente:", placeholder="Ex: Preciso registrar uma nova análise...")
        
        if st.button("Enviar para o Agente"):
            if not user_input.strip():
                st.warning("O prompt não pode estar vazio.")
                return

            with st.spinner("Processando com Azure Foundry..."):
                try:
                    # Salvando o prompt do usuário no SQLite
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    data_hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Chamada simulada/integrada ao Azure OpenAI
                    client = obter_cliente_azure()
                    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
                    
                    response = client.chat.completions.create(
                        model=deployment_name,
                        messages=[
                            {"role": "system", "content": "Você é um assistente de IA técnico e direto, especializado em operações de sistema."},
                            {"role": "user", "content": user_input}
                        ],
                        temperature=0.3
                    )
                    
                    resposta_ia = response.choices[0].message.content
                    
                    # Persistindo dados no SQLite
                    cursor.execute('''
                        INSERT INTO produtos (prompt, resposta, status, data_hora)
                        VALUES (?, ?, ?, ?)
                    ''', (user_input, resposta_ia, "CONCLUIDO", data_hora_atual))
                    conn.commit()
                    conn.close()

                    st.success("Processado e salvo com sucesso no SQLite!")
                    st.markdown(f"**Resposta da IA:**\n\n{resposta_ia}")

                except Exception as e:
                    st.error(f"Erro ao comunicar com o Azure OpenAI ou banco de dados: {e}")

if __name__ == "__main__":
    main()