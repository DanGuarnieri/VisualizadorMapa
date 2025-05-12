import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os

# === CARREGA A SENHA A PARTIR DO .env ===
load_dotenv()
SENHA_CORRETA = os.getenv("SENHA_CORRETA")
SENHA_CORRETA1 = st.secrets['SENHA_CORRETA1']
# === AUTENTICAÇÃO SIMPLES ===
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acesso restrito")
    senha = st.text_input("Digite a senha para acessar:", type="password")
    if senha == SENHA_CORRETA or senha == SENHA_CORRETA1:
        st.session_state.autenticado = True
        st.rerun()
    elif senha:
        st.error("Senha incorreta. Tente novamente.")
    st.stop()


# === APP PRINCIPAL ===

# Configurações da página
st.set_page_config(page_title="Consulta Mapa", layout="wide")
st.title("🔎 Consulta de Cadastro de Produtos")

# Conexão com o banco
try:
    conn = sqlite3.connect("dados.db")
except Exception as e:
    st.error(f"Erro ao conectar no banco de dados: {e}")
    st.stop()


# Lê todos os dados
df_completo = pd.read_sql_query("SELECT * FROM dados", conn)

# Normaliza nomes: uppercase e strip
if 'Solicitante' in df_completo.columns:
    df_completo['Solicitante_limpo'] = (
        df_completo['Solicitante'].astype(str)
            .str.upper()
            .str.strip()
    )
else:
    df_completo['Solicitante_limpo'] = ''

# Converte e formata datas (trata overflow)
colunas_data = ["Data da Inclusão", "Previsão de Lançamento", "Data de Validação"]

for col in colunas_data:
    if col in df_completo.columns:
        try:
            df_completo[col] = pd.to_datetime(df_completo[col], errors='coerce')\
                                    .dt.strftime('%d/%m/%Y')\
                                    .fillna("")
        except Exception as e:
            st.warning(f"Erro ao converter coluna {col}: {e}")
            df_completo[col] = ""


# Layout de busca
col_a, col_b = st.columns(2)
busca = col_a.text_input("Digite o PLU ou EAN:")
nome_input = col_b.text_input("Filtrar por solicitante (insensitive):")
nome = nome_input.strip().upper()

# Função de badge
def render_status_badge(status):
    # Define texto padrão para status vazio
    if not status or pd.isna(status):
        display = "Aguardando validação"
        color, icon = '#888', '⏳'
    else:
        s = str(status).strip().lower()
        if 'aguardando' in s:
            display = status
            color, icon = '#888', '⏳'
        elif 'aprovado' in s:
            display = status
            color, icon = '#28a745', '✅'
        elif 'rejeitado' in s:
            display = status
            color, icon = '#dc3545', '❌'
        else:
            display = status
            color, icon = '#6c757d', 'ℹ️'
    return (
        f"<span style='background-color:{color}; color:white;"
        f" padding:2px 10px; border-radius:12px; font-size:0.85em;'>"
        f"{icon} {display}</span>"
    )

# Filtragem
mask = pd.Series(True, index=df_completo.index)
if busca:
    mask &= (
        df_completo['PLU'].astype(str).str.contains(busca, na=False) |
        df_completo['EAN'].astype(str).str.contains(busca, na=False)
    )
if nome:
    mask &= df_completo['Solicitante_limpo'].str.contains(nome, na=False)
df_filtrado = df_completo[mask]

# Indicadores
def calcular_indicadores(df):
    if 'STATUS' not in df.columns:
        return 0, 0, 0
    sc = df['STATUS'].astype(str).str.strip().str.lower()
    aprov = (sc == 'aprovado').sum()
    rej = (sc == 'rejeitado').sum()
    agu = sc.isin(['aguardando', 'aguardando atendimento', '', 'none', 'aguardando validação']).sum()
    return aprov, rej, agu

base_ind = df_filtrado if nome else df_completo
aprovados, rejeitados, aguardando = calcular_indicadores(base_ind)

# Exibição indicadores
c1, c2, c3 = st.columns(3)
c1.metric("✅ Aprovados", aprovados)
c2.metric("❌ Rejeitados", rejeitados)
c3.metric("🕒 Aguardando", aguardando)

# Resultados
if not busca and not nome:
    st.info("Digite um PLU/EAN ou informe um solicitante para iniciar a consulta.")
else:
    st.success(f"{len(df_filtrado)} produto(s) encontrado(s). ")
    if df_filtrado.empty:
        st.warning("Nenhum resultado encontrado.")
    else:
        for _, row in df_filtrado.iterrows():
            badge = render_status_badge(row.get('STATUS'))
            with st.container():
                st.markdown("---")
                html = f"""
                <div style='background-color:#fff; padding:20px; border-radius:12px;
                            box-shadow:0 2px 8px rgba(0,0,0,0.1); margin-bottom:20px;'>
                    <h4 style='margin-bottom:10px;'>{row.get('Descrição do produto','Sem descrição')} {badge}</h4>
                    <table>
                        <tr>
                            <td><strong>Sugestão Região:</strong> {row.get("Sugestão Região", "-")}</td>
                            <td><strong>Decisão Validada - Região:</strong> {row.get("Decisão Validada - Região", "-")}</td>
                        </tr>
                    </table>
                    <table style='width:100%; font-size:14px; border-collapse:collapse;'>
                        <tr>
                            <td><strong>Solicitante:</strong> {row.get('Solicitante','-')}</td>
                            <td><strong>Data da Inclusão:</strong> {row.get('Data da Inclusão','-')}</td>
                            <td><strong>EAN:</strong> {row.get('EAN','-')}</td>
                            <td><strong>PLU:</strong> {row.get('PLU','-')}</td>
                        </tr>
                        <tr>
                            <td><strong>Tipo:</strong> {row.get("Tipo", "-")}</td>
                            <td><strong>Nº Fornecedor:</strong> {row.get("Nº Fornecedor", "-")}</td>
                            <td colspan="1"><strong>Nº Produto:</strong> {row.get("Nº Produto", "-")}</td>
                        </tr>
                        <tr>
                            <td><strong>Categoria:</strong> {row.get("Categoria", "-")}</td>
                            <td><strong>Subcategoria:</strong> {row.get("Subcategoria", "-")}</td>
                            <td><strong>Cod Grupo:</strong> {row.get("Cod Grupo", "-")}</td>
                            <td><strong>Cod Subgrupo:</strong> {row.get("Cod Subgrupo", "-")}</td>
                        </tr>
                        <tr>
                            <td><strong>Grupo Solução:</strong> {row.get("Grupo Solução", "-")}</td>
                            <td><strong>Subgrupo Solução:</strong> {row.get("Subgrupo Solução", "-")}</td>
                            <td><strong>Item de ME:</strong> {row.get("Item de ME", "-")}</td>
                            <td><strong>Previsão de Lançamento:</strong> {row.get("Previsão de Lançamento", "-")}</td>
                        </tr>
                        <tr>
                            <td><strong>Sugestão Bandeira:</strong> {row.get("Sugestão Bandeira", "-")}</td>
                            <td><strong>Decisão Validada - Bandeira:</strong> {row.get("Decisão Validada - Bandeira", "-")}</td>
                            <td><strong>Sugestão Perfil:</strong> {row.get("Sugestão Perfil", "-")}</td>
                            <td><strong>Decisão Validada - Perfil:</strong> {row.get("Decisão Validada - Perfil", "-")}</td>
                        </tr>
                        <tr>
                            <td><strong>Sugestão Tamanho:</strong> {row.get("Sugestão Tamanho", "-")}</td>
                            <td><strong>Decisão Validada - Tamanho:</strong> {row.get("Decisão Validada - Tamanho", "-")}</td>
                            <td><strong>Lojas Especificas Nº LOJA:</strong> {row.get("Lojas Especificas Nº LOJA", "-")}</td>
                            <td><strong>Planejamento Comercial:</strong> {row.get("Planejamento Comercial", "-")}</td>
                        </tr>
                        <tr>
                            <td><strong>Status de cluster:</strong> {row.get("Status de cluster", "-")}</td>
                            <td><strong>Lojas Definidas Nº LOJA:</strong> {row.get("Lojas Definidas Nº LOJA", "-")}</td>
                            <td><strong>Observação Comercial:</strong> {row.get("Observação Comercial", "-")}</td>
                            <td><strong>Item Substituto:</strong> {row.get("Item Substituto", "-")}</td>
                        </tr>
                        <tr>
                            <td><strong>Responsável pela Aprovação:</strong> {row.get("Responsável pela aprovação (\"GCAT\" + \"COMERCIAL\")", "-")}</td>
                            <td><strong>Observação:</strong> {row.get("Observação", "-")}</td>
                            <td><strong>Tempo de Retorno:</strong> {row.get("Tempo de Retorno", "-")}</td>
                            <td><strong>Data de Validação:</strong> {row.get("Data de Validação", "-")}</td>
                        </tr>
                    </table>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)
