# Desafio Analista de Dados — Funil comercial no Salesforce

Projeto completo do desafio: modelagem e carga no Salesforce, ETL com tratamento de qualidade de dados, análises em SQL (PostgreSQL), estatística em Python e dashboards. **Todos os dados são fictícios**, gerados por script com problemas de qualidade inseridos de propósito.

## Estrutura
```
dados/
  raw/          base bruta (com duplicados, datas inválidas, nulos, grafias diferentes)
  limpo/        base tratada + _log_etl.csv (registros afetados por regra)
  salesforce/   arquivos prontos para carga, na ordem (1_ a 7_), com API names
  powerbi/      funil_etapas.csv (apoio ao visual de funil)
etl/
  00_gerar_dados_sinteticos.py   gera a base bruta (semente fixa)
  01_etl_limpeza.py              limpeza, deduplicação, log
sql/
  00_modelo_e_carga.sql          tabelas, chaves, índices, carga
  01_analises.sql                as 5 perguntas do desafio
  01_analises_resultados.txt     saída das consultas
estatistica/
  analise_estatistica.ipynb      correlação, teste de hipótese, indicadores, impacto
  analise.py                     mesmo conteúdo em script
docs/
  01_modelo_salesforce.md        objetos, campos, fórmulas, validação, justificativas
  02_etl.md                      origem, regras, contagens
  03_passo_a_passo.md            Trailhead, Salesforce, Power BI (DAX)
  04_defesa_oral.md              roteiro e respostas
```

## Como reproduzir
```bash
pip install pandas numpy scipy matplotlib
python etl/00_gerar_dados_sinteticos.py
python etl/01_etl_limpeza.py
createdb desafio
psql -d desafio -f sql/00_modelo_e_carga.sql
psql -d desafio -f sql/01_analises.sql
jupyter notebook estatistica/analise_estatistica.ipynb
```

## Checklist de entregáveis
- [ ] Link do perfil Trailhead com os 3 emblemas
- [x] Documentação do modelo (`docs/01`) + [ ] print do Schema Builder
- [x] Documentação do ETL (`docs/02`) + [ ] arquivos success/error do Data Loader
- [x] Arquivo SQL com consultas e resultados (`sql/`)
- [x] Notebook de estatística (`estatistica/`)
- [ ] Dashboard Power BI (print ou link) — roteiro em `docs/03`
- [ ] 3 relatórios + dashboard no Salesforce (prints)
- [x] Resumo executivo
- [ ] Bônus: Flow de oportunidade parada (print)
- [x] Bônus: limpeza e análises automatizadas em Python
