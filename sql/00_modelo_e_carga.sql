-- =====================================================================
-- 00 - Modelo relacional (espelho do Salesforce) e carga dos CSVs
-- PostgreSQL 14+   |   rodar a partir da pasta raiz do projeto:
--   psql -d desafio -f sql/00_modelo_e_carga.sql
-- Os CSVs de dados/limpo representam o EXPORT do Salesforce (Data Loader
-- > Export), já com os nomes de coluna simplificados.
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;        -- similaridade de texto
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;  -- levenshtein
CREATE EXTENSION IF NOT EXISTS unaccent;       -- remover acentos

DROP SCHEMA IF EXISTS stg CASCADE;
CREATE SCHEMA stg;                              -- dados brutos (antes do ETL)

DROP TABLE IF EXISTS itens_oportunidade, investimentos_campanha, oportunidades,
                     contatos, contas, produtos, campanhas_captacao CASCADE;

CREATE TABLE contas (
    id_externo     varchar(10) PRIMARY KEY,
    nome           text NOT NULL,
    setor          text,
    uf             char(2),
    porte          text,
    data_cadastro  date
);

CREATE TABLE contatos (
    id_externo     varchar(10) PRIMARY KEY,
    conta_id       varchar(10) NOT NULL REFERENCES contas,
    nome           text,
    sobrenome      text,
    email          text,
    telefone       text,
    cargo          text,
    email_pendente boolean
);

CREATE TABLE produtos (
    id_externo   varchar(10) PRIMARY KEY,
    nome         text,
    familia      text,
    preco_lista  numeric(12,2)
);

CREATE TABLE campanhas_captacao (
    id_externo   varchar(10) PRIMARY KEY,
    nome         text,
    canal        text,
    data_inicio  date,
    data_fim     date,
    orcamento    numeric(12,2)
);

CREATE TABLE investimentos_campanha (            -- detalhe (Master-Detail) da campanha
    id_externo      varchar(10) PRIMARY KEY,
    campanha_id     varchar(10) NOT NULL REFERENCES campanhas_captacao ON DELETE CASCADE,
    mes             date,
    valor_investido numeric(12,2)
);

CREATE TABLE oportunidades (
    etapa_maxima               text,
    data_ultima_mudanca_etapa  date,
    id_externo                 varchar(10) PRIMARY KEY,
    nome                       text,
    conta_id                   varchar(10) NOT NULL REFERENCES contas,
    etapa                      text NOT NULL,
    origem                     text,
    campanha_id                varchar(10) REFERENCES campanhas_captacao,  -- Lookup (opcional)
    data_abertura              date NOT NULL,
    data_fechamento            date NOT NULL,
    valor                      numeric(14,2),
    tipo                       text,
    status                     text,
    ciclo_dias                 numeric,
    CONSTRAINT ck_datas CHECK (data_fechamento >= data_abertura OR status = 'Aberta')
);

CREATE TABLE itens_oportunidade (
    id_externo      varchar(12) PRIMARY KEY,
    oportunidade_id varchar(10) NOT NULL REFERENCES oportunidades ON DELETE CASCADE,
    produto_id      varchar(10) NOT NULL REFERENCES produtos,
    quantidade      integer CHECK (quantidade > 0),
    preco_unitario  numeric(12,2)
);

-- dados brutos para a consulta de deduplicação
CREATE TABLE stg.contatos_raw (id_externo text, conta_id text, nome text, sobrenome text,
                               email text, telefone text, cargo text);
CREATE TABLE stg.contas_raw   (id_externo text, nome text, setor text, uf text, porte text,
                               data_cadastro text);

\copy contas FROM 'dados/limpo/contas.csv' CSV HEADER
\copy contatos FROM 'dados/limpo/contatos.csv' CSV HEADER
\copy produtos FROM 'dados/limpo/produtos.csv' CSV HEADER
\copy campanhas_captacao FROM 'dados/limpo/campanhas_captacao.csv' CSV HEADER
\copy investimentos_campanha FROM 'dados/limpo/investimentos_campanha.csv' CSV HEADER
\copy oportunidades FROM 'dados/limpo/oportunidades.csv' CSV HEADER
\copy itens_oportunidade FROM 'dados/limpo/itens_oportunidade.csv' CSV HEADER
\copy stg.contatos_raw FROM 'dados/raw/contatos.csv' CSV HEADER
\copy stg.contas_raw FROM 'dados/raw/contas.csv' CSV HEADER

-- índices que as consultas usam (filtros por etapa/data e joins)
CREATE INDEX ix_opp_conta   ON oportunidades (conta_id);
CREATE INDEX ix_opp_etapa   ON oportunidades (etapa, data_fechamento);
CREATE INDEX ix_item_opp    ON itens_oportunidade (oportunidade_id);
CREATE INDEX ix_ctt_nome_trgm ON stg.contatos_raw USING gin (lower(nome || ' ' || sobrenome) gin_trgm_ops);

ANALYZE;
SELECT 'contas' tabela, count(*) FROM contas UNION ALL
SELECT 'contatos', count(*) FROM contatos UNION ALL
SELECT 'oportunidades', count(*) FROM oportunidades UNION ALL
SELECT 'itens', count(*) FROM itens_oportunidade UNION ALL
SELECT 'campanhas', count(*) FROM campanhas_captacao UNION ALL
SELECT 'investimentos', count(*) FROM investimentos_campanha;
