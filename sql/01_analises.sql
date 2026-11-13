-- =====================================================================
-- 01 - Perguntas do desafio (PostgreSQL)
--   psql -d desafio -f sql/01_analises.sql
-- Data de referência da base (extração): 2026-10-31
-- =====================================================================


-- ---------------------------------------------------------------------
-- Q1. Taxa de conversão do funil por etapa e por mês (mês de ABERTURA),
--     com variação em relação ao mês anterior (funções de janela).
--
-- Lógica: cada oportunidade tem a etapa máxima que alcançou. Ela "passou"
-- por todas as etapas até essa. Conversão da etapa k = qtd que chegou em
-- k+1 / qtd que chegou em k.  Ex.: Proposta -> Negociação.
-- Variação: em pontos percentuais (p.p.) e em % relativa ao mês anterior.
-- Atenção: meses recentes têm oportunidades ainda abertas -> taxa tende a
-- ser subestimada (coluna pct_abertas ajuda a ler isso).
-- ---------------------------------------------------------------------
WITH etapas (etapa, ordem) AS (
    VALUES ('Prospecção', 1), ('Qualificação', 2), ('Proposta', 3),
           ('Negociação', 4), ('Fechado Ganho', 5)
),
opp AS (
    SELECT date_trunc('month', o.data_abertura)::date AS mes,
           e.ordem                                   AS ordem_max,
           (o.status = 'Aberta')::int                AS aberta
    FROM oportunidades o
    JOIN etapas e ON e.etapa = o.etapa_maxima
),
alcance AS (                       -- quantas opps do mês chegaram a cada etapa
    SELECT o.mes, e.ordem, e.etapa,
           COUNT(*) FILTER (WHERE o.ordem_max >= e.ordem) AS qtd,
           ROUND(100.0 * SUM(o.aberta) / COUNT(*), 0)     AS pct_abertas
    FROM opp o CROSS JOIN etapas e
    GROUP BY o.mes, e.ordem, e.etapa
),
conv AS (
    SELECT mes, ordem, pct_abertas,
           etapa                       AS etapa_origem,
           LEAD(etapa) OVER w          AS etapa_destino,
           qtd                         AS qtd_origem,
           LEAD(qtd)   OVER w          AS qtd_destino
    FROM alcance
    WINDOW w AS (PARTITION BY mes ORDER BY ordem)
),
taxa AS (
    SELECT *, 100.0 * qtd_destino / NULLIF(qtd_origem, 0) AS taxa
    FROM conv
    WHERE etapa_destino IS NOT NULL
)
SELECT to_char(mes, 'YYYY-MM')                     AS mes,
       etapa_origem || ' → ' || etapa_destino      AS transicao,
       qtd_origem,
       qtd_destino,
       ROUND(taxa, 1)                              AS taxa_conv_pct,
       ROUND(taxa - LAG(taxa) OVER m, 1)           AS var_pp_vs_mes_ant,
       ROUND(100.0 * (taxa / NULLIF(LAG(taxa) OVER m, 0) - 1), 1) AS var_pct_vs_mes_ant,
       pct_abertas
FROM taxa
WINDOW m AS (PARTITION BY etapa_origem ORDER BY mes)
ORDER BY mes, ordem;


-- Q1b. Visão consolidada do funil (todas as oportunidades) – útil no resumo
WITH etapas (etapa, ordem) AS (
    VALUES ('Prospecção', 1), ('Qualificação', 2), ('Proposta', 3),
           ('Negociação', 4), ('Fechado Ganho', 5)
),
alcance AS (
    SELECT e.ordem, e.etapa, COUNT(*) FILTER (WHERE eo.ordem >= e.ordem) AS qtd
    FROM oportunidades o
    JOIN etapas eo ON eo.etapa = o.etapa_maxima
    CROSS JOIN etapas e
    WHERE o.status <> 'Aberta'                      -- só coortes maduras
    GROUP BY e.ordem, e.etapa
)
SELECT etapa, qtd,
       ROUND(100.0 * qtd / LAG(qtd) OVER (ORDER BY ordem), 1)         AS conv_da_etapa_anterior_pct,
       ROUND(100.0 * qtd / FIRST_VALUE(qtd) OVER (ORDER BY ordem), 1) AS conv_acumulada_pct
FROM alcance
ORDER BY ordem;


-- ---------------------------------------------------------------------
-- Q2. Top 10 clientes por receita acumulada (oportunidades ganhas),
--     participação % no total e % acumulado -> curva ABC
--     Classe A: clientes que formam os primeiros 80% da receita;
--     B: de 80% a 95%; C: restante.
-- ---------------------------------------------------------------------
WITH receita AS (
    SELECT c.id_externo, c.nome, SUM(o.valor) AS receita
    FROM oportunidades o
    JOIN contas c ON c.id_externo = o.conta_id
    WHERE o.etapa = 'Fechado Ganho'
    GROUP BY c.id_externo, c.nome
),
abc AS (
    SELECT nome, receita,
           RANK() OVER (ORDER BY receita DESC)                     AS posicao,
           100.0 * receita / SUM(receita) OVER ()                  AS pct,
           100.0 * SUM(receita) OVER (ORDER BY receita DESC, id_externo
                                      ROWS UNBOUNDED PRECEDING)
                 / SUM(receita) OVER ()                            AS pct_acum
    FROM receita
)
SELECT posicao, nome,
       TO_CHAR(receita, 'FM999G999G990D00') AS receita,
       ROUND(pct, 2)      AS participacao_pct,
       ROUND(pct_acum, 2) AS acumulado_pct,
       CASE WHEN pct_acum - pct < 80 THEN 'A'
            WHEN pct_acum - pct < 95 THEN 'B'
            ELSE 'C' END  AS classe_abc
FROM abc
WHERE posicao <= 10
ORDER BY posicao;

-- Q2b. Resumo da curva ABC (quantos clientes em cada classe)
WITH receita AS (
    SELECT conta_id, SUM(valor) AS receita
    FROM oportunidades WHERE etapa = 'Fechado Ganho' GROUP BY conta_id
),
abc AS (
    SELECT receita,
           100.0 * receita / SUM(receita) OVER () AS pct,
           100.0 * SUM(receita) OVER (ORDER BY receita DESC, conta_id ROWS UNBOUNDED PRECEDING)
                 / SUM(receita) OVER () AS pct_acum
    FROM receita
)
SELECT CASE WHEN pct_acum - pct < 80 THEN 'A' WHEN pct_acum - pct < 95 THEN 'B' ELSE 'C' END AS classe,
       COUNT(*)                                       AS clientes,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_clientes,
       ROUND(SUM(pct), 1)                             AS pct_receita
FROM abc GROUP BY 1 ORDER BY 1;


-- ---------------------------------------------------------------------
-- Q3. Ciclo de venda (dias da abertura até a decisão: ganho OU perda)
--     por faixa de valor: média, mediana e outliers por 1,5 × IQR.
--     As faixas são as mesmas do campo de fórmula Faixa_de_Valor__c.
-- ---------------------------------------------------------------------
WITH base AS (
    SELECT id_externo, valor,
           (data_fechamento - data_abertura) AS ciclo,
           CASE WHEN valor < 10000 THEN '1. Pequeno (< R$ 10 mil)'
                WHEN valor < 50000 THEN '2. Médio (R$ 10–50 mil)'
                ELSE                    '3. Grande (≥ R$ 50 mil)' END AS faixa
    FROM oportunidades
    WHERE status IN ('Ganha', 'Perdida')
),
quartis AS (
    SELECT faixa,
           percentile_cont(0.25) WITHIN GROUP (ORDER BY ciclo) AS q1,
           percentile_cont(0.50) WITHIN GROUP (ORDER BY ciclo) AS mediana,
           percentile_cont(0.75) WITHIN GROUP (ORDER BY ciclo) AS q3
    FROM base GROUP BY faixa
),
limites AS (
    SELECT *, q3 - q1 AS iqr,
           q1 - 1.5 * (q3 - q1) AS lim_inf,
           q3 + 1.5 * (q3 - q1) AS lim_sup
    FROM quartis
)
SELECT l.faixa,
       COUNT(*)                         AS n,
       ROUND(AVG(b.ciclo), 1)           AS media_dias,
       l.mediana                        AS mediana_dias,
       l.q1, l.q3, l.iqr,
       GREATEST(l.lim_inf, 0)           AS lim_inf,
       l.lim_sup,
       COUNT(*) FILTER (WHERE b.ciclo < l.lim_inf OR b.ciclo > l.lim_sup) AS outliers,
       ROUND(AVG(b.ciclo) FILTER (WHERE b.ciclo BETWEEN l.lim_inf AND l.lim_sup), 1)
                                        AS media_sem_outliers
FROM base b JOIN limites l USING (faixa)
GROUP BY l.faixa, l.mediana, l.q1, l.q3, l.iqr, l.lim_inf, l.lim_sup
ORDER BY l.faixa;

-- Q3b. Lista dos outliers (para investigar caso a caso)
WITH base AS (
    SELECT id_externo, nome, origem, valor, (data_fechamento - data_abertura) AS ciclo,
           CASE WHEN valor < 10000 THEN '1. Pequeno' WHEN valor < 50000 THEN '2. Médio'
                ELSE '3. Grande' END AS faixa
    FROM oportunidades WHERE status IN ('Ganha', 'Perdida')
),
lim AS (
    SELECT faixa,
           percentile_cont(0.75) WITHIN GROUP (ORDER BY ciclo)
             + 1.5 * (percentile_cont(0.75) WITHIN GROUP (ORDER BY ciclo)
                      - percentile_cont(0.25) WITHIN GROUP (ORDER BY ciclo)) AS lim_sup
    FROM base GROUP BY faixa
)
SELECT b.faixa, b.id_externo, b.nome, b.origem, b.valor, b.ciclo, ROUND(l.lim_sup::numeric, 1) AS lim_sup
FROM base b JOIN lim l USING (faixa)
WHERE b.ciclo > l.lim_sup
ORDER BY b.faixa, b.ciclo DESC;


-- ---------------------------------------------------------------------
-- Q4. Cohort de retenção: dos clientes que compraram em um mês M,
--     quantos voltaram a comprar em M+1, M+2, M+3 e em qualquer um deles.
--     "Comprar" = oportunidade Fechado Ganho, pelo mês de fechamento.
--     Só entram meses com janela completa (M+3 <= mês da extração).
-- ---------------------------------------------------------------------
WITH compras AS (
    SELECT DISTINCT conta_id, date_trunc('month', data_fechamento)::date AS mes
    FROM oportunidades
    WHERE etapa = 'Fechado Ganho'
),
retorno AS (
    SELECT c.mes, c.conta_id,
           MAX(CASE WHEN r.mes = c.mes + INTERVAL '1 month'  THEN 1 ELSE 0 END) AS m1,
           MAX(CASE WHEN r.mes = c.mes + INTERVAL '2 months' THEN 1 ELSE 0 END) AS m2,
           MAX(CASE WHEN r.mes = c.mes + INTERVAL '3 months' THEN 1 ELSE 0 END) AS m3,
           MAX(CASE WHEN r.mes IS NOT NULL                  THEN 1 ELSE 0 END) AS algum
    FROM compras c
    LEFT JOIN compras r
           ON r.conta_id = c.conta_id
          AND r.mes >  c.mes
          AND r.mes <= c.mes + INTERVAL '3 months'
    GROUP BY c.mes, c.conta_id
)
SELECT to_char(mes, 'YYYY-MM') AS mes_compra,
       COUNT(*)                AS clientes,
       SUM(m1) AS voltou_m1, SUM(m2) AS voltou_m2, SUM(m3) AS voltou_m3,
       SUM(algum)              AS voltou_em_ate_3m,
       ROUND(100.0 * SUM(algum) / COUNT(*), 1) AS retencao_3m_pct
FROM retorno
WHERE mes + INTERVAL '3 months' <= DATE '2026-10-01'
GROUP BY mes
ORDER BY mes;

-- Q4b. Retenção média ponderada por ano
WITH compras AS (
    SELECT DISTINCT conta_id, date_trunc('month', data_fechamento)::date AS mes
    FROM oportunidades WHERE etapa = 'Fechado Ganho'
),
retorno AS (
    SELECT c.mes, c.conta_id,
           EXISTS (SELECT 1 FROM compras r
                   WHERE r.conta_id = c.conta_id
                     AND r.mes > c.mes AND r.mes <= c.mes + INTERVAL '3 months') AS voltou
    FROM compras c
    WHERE c.mes + INTERVAL '3 months' <= DATE '2026-10-01'
)
SELECT EXTRACT(YEAR FROM mes)::int AS ano, COUNT(*) AS clientes_mes,
       SUM(voltou::int) AS voltaram, ROUND(100.0 * AVG(voltou::int), 1) AS retencao_3m_pct
FROM retorno GROUP BY 1 ORDER BY 1;


-- ---------------------------------------------------------------------
-- Q5. Detecção de duplicados por similaridade de NOME e E-MAIL
--     (na base BRUTA, stg.contatos_raw — antes da limpeza)
--
--   sim_nome  = similaridade por trigramas (0 a 1) do nome completo
--               sem acento e em minúsculas
--   dist_email= distância de Levenshtein entre os e-mails normalizados
--
-- Regra de deduplicação proposta (score):
--   DUPLICADO CERTO   -> e-mail normalizado igual
--                        OU (mesma conta e sim_nome >= 0,9)
--   PROVÁVEL (revisar)-> sim_nome >= 0,6 e dist_email <= 3 (ambos com e-mail)
--   HOMÔNIMO          -> nome igual, contas diferentes, sem e-mail para
--                        comparar: NÃO mesclar (pessoas diferentes)
--   Sobrevivente: registro mais antigo (menor id); os campos vazios dele
--   são preenchidos com os do duplicado antes do merge (Merge Contacts).
-- ---------------------------------------------------------------------
WITH n AS (
    SELECT id_externo, conta_id, nome, sobrenome, email,
           lower(unaccent(trim(nome || ' ' || sobrenome))) AS nome_norm,
           lower(trim(email))                               AS email_norm
    FROM stg.contatos_raw
),
pares AS (
    SELECT a.id_externo AS id_a, b.id_externo AS id_b,
           a.nome || ' ' || a.sobrenome AS nome_a,
           b.nome || ' ' || b.sobrenome AS nome_b,
           a.email AS email_a, b.email AS email_b,
           (a.conta_id = b.conta_id) AS mesma_conta,
           ROUND(similarity(a.nome_norm, b.nome_norm)::numeric, 2) AS sim_nome,
           levenshtein(a.email_norm, b.email_norm) AS dist_email,   -- NULL se faltar e-mail
           (a.email_norm = b.email_norm) AS email_igual
    FROM n a
    JOIN n b
      ON a.id_externo < b.id_externo
     AND (a.email_norm = b.email_norm          -- candidatos: e-mail igual
          OR a.nome_norm % b.nome_norm)        -- ou nome parecido (índice trigram)
)
SELECT id_a, id_b, nome_a, nome_b, email_a, email_b, mesma_conta, sim_nome, dist_email,
       CASE WHEN email_igual OR (mesma_conta AND sim_nome >= 0.9) THEN 'DUPLICADO CERTO'
            WHEN sim_nome >= 0.6 AND dist_email <= 3               THEN 'PROVÁVEL (revisar)'
            WHEN NOT mesma_conta AND sim_nome >= 0.9 AND dist_email IS NULL
                                                                   THEN 'HOMÔNIMO (não mesclar)'
            ELSE 'diferente' END AS classificacao
FROM pares
WHERE email_igual
   OR (mesma_conta AND sim_nome >= 0.9)
   OR (sim_nome >= 0.6 AND dist_email <= 3)
   OR (sim_nome >= 0.9 AND dist_email IS NULL)
ORDER BY classificacao, sim_nome DESC;

-- Q5b. Resumo da regra aplicada
WITH n AS (
    SELECT id_externo, conta_id,
           lower(unaccent(trim(nome || ' ' || sobrenome))) AS nome_norm,
           lower(trim(email)) AS email_norm
    FROM stg.contatos_raw
),
pares AS (
    SELECT a.id_externo id_a, b.id_externo id_b,
           CASE WHEN a.email_norm = b.email_norm
                  OR (a.conta_id = b.conta_id AND similarity(a.nome_norm, b.nome_norm) >= 0.9)
                THEN 'DUPLICADO CERTO'
                WHEN similarity(a.nome_norm, b.nome_norm) >= 0.6
                 AND levenshtein(a.email_norm, b.email_norm) <= 3
                THEN 'PROVÁVEL (revisar)'
                WHEN a.conta_id <> b.conta_id AND similarity(a.nome_norm, b.nome_norm) >= 0.9
                 AND (a.email_norm IS NULL OR b.email_norm IS NULL)
                THEN 'HOMÔNIMO (não mesclar)' END AS classificacao
    FROM n a JOIN n b ON a.id_externo < b.id_externo
)
SELECT classificacao, COUNT(*) AS pares,
       COUNT(DISTINCT id_b) FILTER (WHERE classificacao <> 'HOMÔNIMO (não mesclar)') AS registros_a_remover
FROM pares WHERE classificacao IS NOT NULL GROUP BY classificacao;

-- Q5c. Mesma ideia para CONTAS (nome sem sufixo societário)
WITH n AS (
    SELECT id_externo, nome,
           trim(regexp_replace(regexp_replace(lower(unaccent(nome)), '[^a-z0-9 ]', ' ', 'g'),
                '\m(ltda|sa|s a|me|m e|eireli)\M|\s+', ' ', 'g')) AS nome_norm
    FROM stg.contas_raw
)
SELECT a.id_externo AS id_a, b.id_externo AS id_b, a.nome AS nome_a, b.nome AS nome_b,
       ROUND(similarity(a.nome_norm, b.nome_norm)::numeric, 2) AS sim_nome
FROM n a JOIN n b ON a.id_externo < b.id_externo
WHERE similarity(a.nome_norm, b.nome_norm) >= 0.8
ORDER BY sim_nome DESC, id_a;
