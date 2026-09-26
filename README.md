# 🔎 VisualizadorMapa

Aplicação web desenvolvida em **Python + Streamlit** para consulta, tratamento e acompanhamento de dados relacionados ao cadastro e lançamento de produtos.

O projeto implementa um pipeline completo de ingestão e tratamento de dados, partindo de arquivos disponibilizados no SharePoint até sua disponibilização em uma interface de consulta.

## 🎯 Objetivo

Centralizar e facilitar a consulta de informações de produtos, permitindo que usuários filtrem registros por identificadores, solicitantes, períodos e status, além de exportarem os resultados encontrados.

O projeto também automatiza etapas de preparação dos dados, reduzindo a necessidade de manipulação manual de planilhas.

## 🏗️ Arquitetura

```text
SharePoint
    │
    ▼
Arquivo XLSB
    │
    ▼
Ingestão
    │
    ▼
Tratamento e padronização
    │
    ├── Consolidação de abas
    ├── Normalização de campos
    ├── Tratamento de datas
    ├── Identificação de inconsistências
    └── Enriquecimento de produtos
    │
    ▼
SQLite
    │
    ▼
Streamlit
    │
    ├── Consulta
    ├── Filtros
    ├── Indicadores
    └── Exportação
```

## 🛠️ Tecnologias

* Python
* Pandas
* Streamlit
* SQLite
* OpenPyXL
* PyXLSB
* python-dotenv
* Office365 REST Python Client

## 📂 Estrutura

```text
VisualizadorMapa/
├── app/
├── data/
├── scripts/
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## ⚙️ Funcionalidades

### Consulta

Permite localizar registros utilizando:

* PLU
* EAN
* Solicitante
* Período
* Status

### Indicadores

A aplicação apresenta indicadores de:

* Produtos aprovados
* Produtos rejeitados
* Produtos aguardando validação

### Exportação

Os resultados filtrados podem ser exportados para Excel.

## 🔄 Pipeline de dados

O processo de atualização realiza:

1. Download do arquivo de origem.
2. Leitura das abas relevantes.
3. Padronização das colunas.
4. Tratamento de identificadores.
5. Conversão de datas.
6. Consolidação dos registros.
7. Enriquecimento com informações de produtos.
8. Associação de inconsistências.
9. Persistência dos dados.
10. Disponibilização para consulta através do Streamlit.

## 🔐 Configuração

Crie um arquivo `.env` baseado em `.env.example`:

```env
SHAREPOINT_USERNAME=
SHAREPOINT_PASSWORD=
SHAREPOINT_SITE_URL=
SHAREPOINT_FILE_PATH=
```

As credenciais não devem ser versionadas.

## ▶️ Execução

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute o processo de atualização:

```bash
python scripts/update_database.py
```

Depois execute a aplicação:

```bash
streamlit run app/main.py
```

## 📌 Boas práticas futuras

* Adicionar testes automatizados.
* Remover caminhos absolutos.
* Separar configuração de código.
* Adicionar logging estruturado.
* Implementar validações de schema.
* Utilizar banco de dados externo em ambientes de produção.
* Criar pipeline automatizado de atualização.

## 👤 Autor

**Danilo Guarnieri**

Projeto desenvolvido como estudo aplicado de engenharia de dados, automação e desenvolvimento de aplicações Python.
