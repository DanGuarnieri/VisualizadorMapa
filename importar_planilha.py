import os
import pandas as pd
import requests
from io import BytesIO
from pandas.api.types import is_numeric_dtype
import sqlite3
from dotenv import load_dotenv
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext

# === CONFIGURAÇÕES SHAREPOINT ===
ENV_PATH = r"C:\Users\3878422\OneDrive\Onedrive - GPA\Área de Trabalho\Projetos Python\pytestes\env\.env"
SITE_URL = "https://gpabr.sharepoint.com/sites/CatalogodeProdutos/"
SERVER_RELATIVE_PATH = (
    "/sites/CatalogodeProdutos/"
    "Documentos Compartilhados/Mapa Gcat/"
    "Mapa de Lançamentos e Oportunidades - Definitivo.xlsb"
)

load_dotenv(ENV_PATH)
username = os.getenv("SHAREPOINT_USERNAME")
password = os.getenv("SHAREPOINT_PASSWORD")

def get_sharepoint_context():
    return ClientContext(SITE_URL).with_credentials(
        UserCredential(username, password)
    )

def baixar_planilha_sharepoint() -> BytesIO:
    """Baixa o .xlsb do SharePoint e retorna um BytesIO."""
    ctx = get_sharepoint_context()
    file = ctx.web.get_file_by_server_relative_url(SERVER_RELATIVE_PATH)
    stream = BytesIO()
    file.download(stream).execute_query()
    stream.seek(0)
    return stream

# === CONFIGURAÇÕES DE TRATAMENTO ===
abas_interesse = [
    'NAL', 'PAS', 'DPH e Perfumaria', 'Liquida',
    'Mercearia Complementar', 'Merc Basica'
]
cabecalho_padrao = [
    'Solicitante','Data da Inclusão','EAN','PLU','Descrição do produto',
    'Tipo','Nº Fornecedor','Nº Produto','Categoria','Subcategoria',
    'Cod Grupo','Grupo Solução','Cod Subgrupo','Subgrupo Solução',
    'Item de ME','Item Substituto','Previsão de Lançamento',
    'Observação Comercial','Sugestão Bandeira','Sugestão Região',
    'Sugestão Perfil','Sugestão Tamanho','Lojas Especificas Nº LOJA',
    'Planejamento Comercial','STATUS','Decisão Validada - Bandeira',
    'Decisão Validada - Região','Decisão Validada - Perfil',
    'Decisão Validada - Tamanho','Lojas Definidas Nº LOJA',
    'Responsável pela aprovação ("GCAT" + "COMERCIAL")',
    'Observação','Status de cluster','Data de Validação',
    'Tempo de Retorno'
]
Produtos_postados = r'C:\Users\3878422\OneDrive\Onedrive - GPA\Área de Trabalho\Projetos Python\Visualizador\CatalogoProdutos.xlsx'
saida_arquivo = 'planilha_tratada.xlsx'
caminho_inconsistencias = r'C:\Users\3878422\OneDrive\Onedrive - GPA\Área de Trabalho\Projetos Python\Visualizador\Inconsistencias.xlsx'

# === FUNÇÕES ===

def tratar_planilha(arquivo):
    """
    Recebe um caminho (str) ou BytesIO e consolida as abas de interesse.
    Retorna um DataFrame único.
    """
    xls = pd.ExcelFile(arquivo, engine='pyxlsb')
    df_final = pd.DataFrame()

    for aba in abas_interesse:
        if aba in xls.sheet_names:
            df = pd.read_excel(
                xls, sheet_name=aba,
                skiprows=2, header=None
            )
            df.columns = cabecalho_padrao[:df.shape[1]]
            df = df[~df[['Solicitante','EAN','PLU']].isna().all(axis=1)]
            df['Solicitante'] = (
                df['Solicitante']
                .fillna('Não Informado')
                .astype(str).str.strip().str.upper()
            )

            for col in ['Data da Inclusão','Previsão de Lançamento','Data de Validação']:
                if col in df.columns:
                    if is_numeric_dtype(df[col]):
                        df[col] = df[col].where(df[col].between(1,60000), pd.NA)
                        df[col] = (
                            pd.to_datetime('1899-12-30')
                            + pd.to_timedelta(df[col], unit='D')
                        ).dt.date
                    else:
                        df[col] = (
                            pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                            .dt.date
                        )

            df['Origem'] = aba
            df_final = pd.concat([df_final, df], ignore_index=True)

    return df_final

def salvar_planilha(df, nome_saida, aba_saida='Mapa Gcat'):
    with pd.ExcelWriter(nome_saida, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=aba_saida, index=False)

def importar_planilha(caminho_arquivo: str, caminho_db: str = "dados.db"):
    xls = pd.ExcelFile(caminho_arquivo)
    df_total = pd.concat([
        xls.parse(s) for s in xls.sheet_names
    ], ignore_index=True)
    conn = sqlite3.connect(caminho_db)
    df_total.to_sql("dados", conn, if_exists="replace", index=False)
    conn.close()
    print(f"[✓] {len(df_total)} linhas salvas em {caminho_db}")

# === EXECUÇÃO PRINCIPAL ===

# 1) Baixa do SharePoint
arquivo_share = baixar_planilha_sharepoint()

# 2) Consolida e trata
df_consolidado = tratar_planilha(arquivo_share)

# 3) Carrega produtos já postados e faz merge
df_postados = pd.read_excel(
    Produtos_postados, engine='openpyxl',
    dtype={'Cód Chave do Produto': str}
)
df_consolidado['EAN'] = (
    df_consolidado['EAN']
    .fillna('').astype(str).str.replace(r'\D', '', regex=True)
)
df_postados['Cód Chave do Produto'] = (
    df_postados['Cód Chave do Produto']
    .fillna('').astype(str).str.replace(r'\D', '', regex=True)
)
df_postados['Nome Provedor'] = (
    df_postados['Nome Provedor']
    .astype(str).str.strip()
)
validos = ['Simplus','Portal de Produtos']
df_filtrado = df_postados[
    df_postados['Nome Provedor'].isin(validos)
].drop_duplicates('Cód Chave do Produto')

df_resultado = df_consolidado.merge(
    df_filtrado[['Cód Chave do Produto','Nome Provedor']],
    left_on='EAN', right_on='Cód Chave do Produto', how='left'
)
df_resultado['Nome Provedor'] = df_resultado.apply(
    lambda x: x['Nome Provedor'] if x['Nome Provedor'] in validos
    else ('EAN não informado' if not x['EAN'] else 'Provedor não identificado'),
    axis=1
)
df_resultado.drop(columns=['Cód Chave do Produto'], inplace=True)
df_consolidado = df_resultado

# 4) Junta inconsistências
df_incons = pd.read_excel(
    caminho_inconsistencias, engine='openpyxl',
    dtype={'Cód Chave do Produto': str}
)
df_agrupado = (
    df_incons
    .assign(**{
        'Cód Chave do Produto': lambda d: (
            d['Cód Chave do Produto']
            .fillna('').astype(str).str.replace(r'\D','',regex=True)
        )
    })
    .groupby('Cód Chave do Produto')['Erro']
    .apply(lambda x: '; '.join(x.unique()))
    .reset_index()
    .rename(columns={
        'Cód Chave do Produto':'EAN','Erro':'Inconsistência'
    })
)
df_consolidado['Inconsistências'] = df_consolidado.apply(
    lambda x: (
        'EAN não informado' if not x['EAN']
        else ('Sem inconsistências' if pd.isna(df_agrupado.loc[
            df_agrupado['EAN']==x['EAN'],'Inconsistência'
        ]).all() else df_agrupado.loc[
            df_agrupado['EAN']==x['EAN'],'Inconsistência'
        ].values[0])
    ),
    axis=1
)

# 5) Salva e importa no SQLite
salvar_planilha(df_consolidado, saida_arquivo)
print(f"Planilha tratada salva em '{saida_arquivo}'.")
importar_planilha(saida_arquivo)
