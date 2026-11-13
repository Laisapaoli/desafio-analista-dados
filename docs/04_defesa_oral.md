# 4. Preparação para a defesa oral (30 min)

## Roteiro sugerido de apresentação (10 min)
1. **Problema e base** (1 min) — base fictícia de uma empresa B2B de software; 537 oportunidades, 220 contas, jan/2024 a out/2026.
2. **Modelo e ETL** (3 min) — mostrar o Schema Builder; explicar Master-Detail × Lookup; mostrar a tabela de regras do ETL e o print do erro da regra de validação.
3. **Achados** (4 min) — dashboard; as 3 conclusões do resumo executivo.
4. **Recomendação** (2 min) — programa de indicação, impacto estimado e como mediria.

## Perguntas do desafio — respostas-base (fale com suas palavras)

**"Se a base crescesse 100 vezes, o que mudaria?"**
- 100× = ~54 mil oportunidades e ~80 mil itens: ainda é pequeno para PostgreSQL. O que muda é a forma de trabalhar, não o banco.
- **Carga:** sair do Data Import Wizard para **Bulk API** (Data Loader em modo Bulk) e carga **incremental** por data de modificação (`SystemModstamp`), em vez de recarregar tudo.
- **Armazenamento:** um *staging* + camada analítica (modelo estrela: fato oportunidade, dimensões conta, tempo, canal, produto) em um data warehouse (BigQuery, Snowflake ou Postgres particionado por mês de fechamento).
- **Consultas:** índices nas colunas de filtro/junção (já criei `etapa, data_fechamento` e `conta_id`); a deduplicação por similaridade é a mais cara — comparar "todos com todos" cresce ao quadrado, então eu usaria *blocking* (só comparar dentro da mesma conta ou do mesmo domínio de e-mail) e índice trigram (GIN), que já está no script.
- **Power BI:** modo Importação com atualização incremental, ou tabelas agregadas por mês.
- **Salesforce:** no limite de armazenamento, arquivar histórico antigo (Big Objects ou fora da plataforma).

**"Como garantir qualidade de dados de forma contínua?"**
- **Prevenir na entrada:** regras de validação (já criadas), picklists em vez de texto livre para etapa/origem, campos obrigatórios por etapa, **regras de duplicidade** nativas do Salesforce (*Matching Rules + Duplicate Rules*) para Conta e Contato.
- **Automatizar:** os Flows mantêm `Etapa_Maxima__c` e `Data_Ultima_Mudanca_Etapa__c` sem depender do vendedor.
- **Monitorar:** um relatório/painel de qualidade (contatos com e-mail pendente, oportunidades sem origem, abertas com data vencida) revisado toda semana; o script de ETL vira um teste que roda a cada export e alerta se uma contagem fugir do normal.
- **Dono do dado:** cada indicador tem um responsável; métrica de % de registros completos por vendedor.

**"Qual decisão de modelagem você tomaria diferente?"**
- Usaria o histórico nativo de etapas (*Field History Tracking* / `OpportunityHistory`) desde o início, em vez de guardar só a etapa máxima — com ele dá para medir **tempo em cada etapa**, não só o ciclo total. Não fiz por causa do limite de 5 MB da Developer Edition.
- Ligaria Oportunidade à Campanha por um objeto de junção (vários toques de campanha por negócio) para atribuição multitoque; com Lookup simples, todo o crédito vai para uma campanha só.

## Perguntas prováveis que vale treinar
- *Por que Spearman e não Pearson?* Os valores são muito assimétricos (um negócio de R$ 714 mil); Spearman usa a ordem, não o valor, e não é distorcido por extremos. Pearson bruto deu 0,29 e Spearman 0,39.
- *Por que Mann-Whitney e não teste t?* O Shapiro-Wilk rejeitou normalidade nos dois grupos. Mesmo assim conferi com teste t de Welch no log do ciclo: mesma conclusão.
- *Correlação de 0,39 é forte?* É moderada: o valor explica cerca de 14% da variação do ciclo. Há outros fatores (canal, setor, vendedor).
- *O canal causa o ciclo mais curto?* Não dá para afirmar causa: é dado observacional. Controlei pelo valor do negócio na regressão e o efeito continuou, mas pode haver outros fatores (perfil do cliente indicado).
- *Por que a taxa de conversão de meses recentes cai?* Coortes recentes ainda têm oportunidades abertas — por isso mostro `pct_abertas` e o funil consolidado usa só negócios já decididos.
- *O retorno do Outbound nas campanhas é o maior (27×). Isso não contradiz a recomendação?* O investimento de campanha não inclui o custo do time de SDR, que é o principal custo do Outbound. Com esse custo, o retorno cai muito. É uma limitação que eu declararia.
- *Por que a curva ABC usa "acumulado anterior < 80%"?* Para que o cliente que cruza a linha dos 80% fique na classe A — é a convenção mais comum.
