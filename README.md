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

- [x] [Link do perfil Trailhead](https://www.salesforce.com/trailblazer/hqr91pum24qfz50wg0) com os 3 emblemas (detalhes na seção Trailhead abaixo)
- [x] Documentação do modelo (`docs/01`) + print do Schema Builder (`docs/`)
- [x] Documentação do ETL (`docs/02`) + arquivos success/error do Data Loader (`resultados_carga/`)
- [x] Arquivo SQL com consultas e resultados (`sql/`)
- [x] Notebook de estatística (`estatistica/`)
- [ ] Dashboard Power BI (print ou link) — roteiro em `docs/03`
- [x] 3 relatórios + dashboard no Salesforce (prints em docs/)
- [x] Resumo executivo
- [ ] Bônus: Flow de oportunidade parada (print)
- [x] Bônus: limpeza e análises automatizadas em Python

## 🏅 Trailhead — Pré-requisitos do desafio

**Perfil público:** [salesforce.com/trailblazer/hqr91pum24qfz50wg0](https://www.salesforce.com/trailblazer/hqr91pum24qfz50wg0) — 16 emblemas

| Exigido no desafio | Concluído no Trailhead | Status |
|---|---|---|
| Admin Beginner | Trilha *Admin iniciantse* | ✅ |
| Reports & Dashboards for Lightning Experience | Trilha *Explorar Reports & Dashboards do Lightning Experience* + emblemas *Relatórios e painéis* e *Criar relatórios e painéis* | ✅ |
| Data Modeling e Data Management | Emblemas *Modelagem de dados* e *Gerenciamento de dados* + trilha *Gerenciar dados como administrador* | ✅ |

Outros emblemas relevantes: Qualidade dos dados, Administração da lista de opções, Gerenciamento de usuários, Salesforce CRM.




| 

| 