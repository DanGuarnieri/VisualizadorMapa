import pandas as pd
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

# Exemplo de uso
if __name__ == "__main__":
    importar_planilha("planilha_tratada.xlsx")  # ← substitua pelo nome real do arquivo
