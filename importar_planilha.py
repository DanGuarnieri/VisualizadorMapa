import pandas as pd
import requests
from io import BytesIO
from pandas.api.types import is_numeric_dtype
import sqlite3

def importar_planilha(caminho_arquivo: str, caminho_db: str = "dados.db"):
    # Lê todas as abas da planilha
    xls = pd.ExcelFile(caminho_arquivo)
    df_total = pd.concat([xls.parse(sheet) for sheet in xls.sheet_names], ignore_index=True)

    # Conecta ao banco de dados SQLite e salva os dados
    conn = sqlite3.connect(caminho_db)
    df_total.to_sql("dados", conn, if_exists="replace", index=False)
    conn.close()

    print(f"[✓] Base importada com sucesso! {len(df_total)} linhas salvas em {caminho_db}")

# === CONFIGURAÇÕES ===
sharepoint_url = 'COLE_AQUI_A_URL_DIRETA_DA_PLANILHA.xlsx'
abas_interesse = ['NAL', 'PAS', 'DPH e Perfumaria', 'Liquida', 'Mercearia Complementar', 'Merc Basica']
cabecalho_padrao = ['Solicitante','Data da Inclusão','EAN',
                    'PLU','	Descrição do produto','Tipo','Nº Fornecedor',
                    'Nº Produto','Categoria','Subcategoria','Cod Grupo',
                    'Grupo Solução', 'Cod Subgrupo','Subgrupo Solução', 'Item de ME',
                    'Item Substituto',	'Previsão de Lançamento','Observação Comercial','Sugestão Bandeira',
                    'Sugestão Região', 'Sugestão Perfil',	'Sugestão Tamanho',	'Lojas Especificas Nº LOJA',
                    'Planejamento Comercial', 'STATUS', 'Decisão Validada - Bandeira',	'Decisão Validada - Região',
                    'Decisão Validada - Perfil','Decisão Validada - Tamanho','Lojas Definidas Nº LOJA',
                    'Responsável pela aprovação ("GCAT" + "COMERCIAL")','Observação','Status de cluster','Data de Validação',	
                    'Tempo de Retorno']
Produtos_postados = r'C:\Users\3878422\OneDrive\Onedrive - GPA\Área de Trabalho\Projetos Python\Visualizador\ProdutosPostados.xlsx'
saida_arquivo = 'planilha_tratada.xlsx'


# === DOWNLOAD DO SHAREPOINT ===
def baixar_arquivo_sharepoint(url):
    response = requests.get(url)
    response.raise_for_status()
    return BytesIO(response.content)

# === TRATAMENTO DAS ABAS E CONSOLIDAÇÃO ===
def tratar_planilha(arquivo):
    xls = pd.ExcelFile(arquivo)
    df_final = pd.DataFrame()

    for aba in abas_interesse:
        if aba in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=aba, skiprows=2, header=None)  # Ignora as duas primeiras linhas
            df.columns = cabecalho_padrao[:df.shape[1]]  # Ajusta o número de colunas conforme o DataFrame
            # Remove apenas se as três colunas estiverem vazias
            df = df[~df[['Solicitante', 'EAN', 'PLU']].isna().all(axis=1)]
            df['Solicitante'] = df['Solicitante'].fillna('Não Informado')
            df['Solicitante'] = df['Solicitante'].astype(str).str.strip().str.upper()
            # Converte colunas de data para datetime
            colunas_data = ['Data da Inclusão', 'Previsão de Lançamento', 'Data de Validação']
                        
            for col in colunas_data:
                if col in df.columns:
                    if is_numeric_dtype(df[col]):
                        # Limita os valores válidos para datas
                        df[col] = df[col].where(df[col].between(1, 60000), pd.NA)
                        df[col] = (pd.to_datetime('1899-12-30') + pd.to_timedelta(df[col], unit='D')).dt.date
                    else:
                        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True).dt.date

            df['Origem'] = aba  # Opcional: adicionar coluna com nome da aba
            df_final = pd.concat([df_final, df], ignore_index=True)

    return df_final

# === SALVAR EM NOVA ABA ===
def salvar_planilha(df, nome_saida, aba_saida='Mapa Gcat'):
    with pd.ExcelWriter(nome_saida, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=aba_saida, index=False)

# === EXECUÇÃO ===
arquivo_baixado = r'C:\Users\3878422\OneDrive\Onedrive - GPA\Área de Trabalho\Projetos Python\Visualizador\Mapa de Lançamentos e Oportunidades - Definitivo.xlsb'
df_consolidado = tratar_planilha(arquivo_baixado)

# === CARREGAR PRODUTOS POSTADOS ===
df_postados = pd.read_excel(Produtos_postados, engine='openpyxl', dtype={'Cód Chave do Produto': str})

# === FORMATAR E PADRONIZAR CAMPOS PARA COMPARAÇÃO ===
df_consolidado['EAN'] = df_consolidado['EAN'].fillna('').astype(str).str.replace(r'\D', '', regex=True)
df_postados['Cód Chave do Produto'] = df_postados['Cód Chave do Produto'].fillna('').astype(str).str.replace(r'\D', '', regex=True)
df_postados['Nome Provedor'] = df_postados['Nome Provedor'].astype(str).str.strip()

# === FILTRAR SOMENTE PROVEDORES VÁLIDOS ===
provedores_validos = ['Simplus', 'Portal de Produtos']
df_filtrado = df_postados[df_postados['Nome Provedor'].isin(provedores_validos)].copy()

# === REMOVER DUPLICATAS MANTENDO PRIMEIRO OCORRIDO ===
df_filtrado = df_filtrado.drop_duplicates(subset='Cód Chave do Produto', keep='first')

# === REALIZAR JUNÇÃO COM A BASE ===
df_resultado = df_consolidado.merge(
    df_filtrado[['Cód Chave do Produto', 'Nome Provedor']],
    left_on='EAN',
    right_on='Cód Chave do Produto',
    how='left'
)

# === APLICAR REGRAS DE CLASSIFICAÇÃO DO PROVEDOR ===
def classificar_provedor(ean, provedor):
    if not ean or ean.lower() == 'nan':
        return 'EAN não informado'
    if provedor in provedores_validos:
        return provedor
    return 'Provedor não identificado'

df_resultado['Nome Provedor'] = df_resultado.apply(
    lambda x: classificar_provedor(x['EAN'], x['Nome Provedor']), axis=1
)

df_resultado.drop(columns=['Cód Chave do Produto'], inplace=True)
df_consolidado = df_resultado

# === CARREGAR PLANILHA DE INCONSISTÊNCIAS ===
caminho_inconsistencias = r'C:\Users\3878422\OneDrive\Onedrive - GPA\Área de Trabalho\Projetos Python\Visualizador\Inconsistencias.xlsx'
df_incons = pd.read_excel(caminho_inconsistencias, engine='openpyxl', dtype={'Cód Chave do Produto': str})

# === FORMATAR EAN PARA COMPARAÇÃO ===
df_incons['Cód Chave do Produto'] = df_incons['Cód Chave do Produto'].fillna('').astype(str).str.replace(r'\D', '', regex=True)
df_incons['Erro'] = df_incons['Erro'].astype(str).str.strip()

# === AGRUPAR INCONSISTÊNCIAS POR EAN EM TEXTO ÚNICO ===
df_agrupado = df_incons.groupby('Cód Chave do Produto')['Erro'] \
    .apply(lambda x: '; '.join(x.unique())).reset_index()
df_agrupado.rename(columns={'Cód Chave do Produto': 'EAN', 'Erro': 'Inconsistência'}, inplace=True)

# === GARANTE QUE A BASE PRINCIPAL ESTÁ FORMATADA IGUAL ===
df_consolidado['EAN'] = df_consolidado['EAN'].fillna('').astype(str).str.replace(r'\D', '', regex=True)

# === JUNÇÃO COM A PLANILHA BASE ===
df_com_incons = df_consolidado.merge(df_agrupado, on='EAN', how='left')

# === APLICAÇÃO DAS REGRAS DE EXIBIÇÃO ===
def classificar_inconsistencia(ean, inconsistencias):
    if not ean or ean.lower() == 'nan':
        return 'EAN não informado'
    if pd.isna(inconsistencias) or inconsistencias.strip() == '':
        return 'Sem inconsistências'
    return inconsistencias

df_com_incons['Inconsistências'] = df_com_incons.apply(
    lambda x: classificar_inconsistencia(x['EAN'], x['Inconsistência']), axis=1
)

# === REMOVE COLUNA AUXILIAR ===
df_com_incons.drop(columns=['Inconsistência'], inplace=True)

# Atualiza o DataFrame principal
df_consolidado = df_com_incons

salvar_planilha(df_consolidado, saida_arquivo)
print(f"Planilha consolidada salva como '{saida_arquivo}'.")

importar_planilha('planilha_tratada.xlsx')  # ← substitua pelo nome real do arquivo

