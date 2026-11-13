# 2. Processo de ETL

## Origem
Extração simulada de um CRM legado em CSV (`dados/raw/`), gerada pelo script `etl/00_gerar_dados_sinteticos.py` (semente fixa = resultado reproduzível). A base é **fictícia** e recebeu problemas de qualidade de propósito, como pede o desafio. O arquivo `_gabarito_problemas_inseridos.csv` lista o que foi inserido — serve para conferir se o ETL pegou tudo.

| Arquivo bruto | Linhas | Conteúdo |
|---|---|---|
| contas.csv | 242 | empresas clientes e prospects |
| contatos.csv | 304 | pessoas de contato |
| oportunidades.csv | 558 | negócios, jan/2024 a out/2026 |
| itens_oportunidade.csv | 835 | produtos de cada negócio |
| produtos.csv | 8 | catálogo |
| campanhas_captacao.csv | 12 | campanhas de marketing/vendas |
| investimentos_campanha.csv | 43 | gasto mensal por campanha |

## Fluxo
```
dados/raw  ──►  etl/01_etl_limpeza.py  ──►  dados/limpo       (análise: SQL, Python, Power BI)
                                       ├─►  dados/salesforce  (carga, já com API names)
                                       └─►  dados/limpo/_log_etl.csv (contagem por regra)
```
Ordem: contas → contatos → oportunidades → itens. A ordem importa: a deduplicação de contas gera um "de-para" (id duplicado → id mestre) usado para corrigir contatos e oportunidades, e os itens são limpos antes do recálculo do valor das oportunidades.

## Regras de limpeza e registros afetados

| Tabela | Problema | Regra aplicada | Ação | Registros |
|---|---|---|---|---|
| Contas | Espaços extras no nome | `trim` + espaço único | corrigido | 5 |
| Contas | UF escrita de vários jeitos ("São Paulo", "sao paulo", " sp") | Mapa para sigla de 2 letras | corrigido | 21 |
| Contas | Setor nulo | "Não informado" (não descarta a conta) | corrigido | 14 |
| Contas | Mesma empresa cadastrada 2× com grafia diferente | Chave = nome sem acento, minúsculo, sem pontuação e sem sufixo (Ltda, S.A., ME, EIRELI); fica o cadastro **mais antigo** | descartado | 22 |
| Contatos | E-mail sem "@" | Validação por expressão regular → e-mail vira nulo, contato é mantido | corrigido | 8 |
| Contatos | E-mail nulo | Mantido e marcado `Email_Pendente__c = true` para o time completar | sinalizado | 23 |
| Contatos | Contato duplicado | Mesmo e-mail (minúsculo) **ou** mesmo nome normalizado na mesma conta | descartado | 21 |
| Oportunidades | Linha repetida inteira | `drop_duplicates` | descartado | 18 |
| Oportunidades | Ligada a conta duplicada | Repontada para a conta mestre (de-para) | corrigido | 12 |
| Oportunidades | Etapa com grafia diferente ("Closed Won", "Ganho", "negociação") | Mapa para as 6 etapas oficiais | corrigido | 40 |
| Oportunidades | Origem com grafia diferente ("Indicacao", "Out-bound") | Mapa para os 5 canais oficiais | corrigido | 45 |
| Oportunidades | Origem nula | "Não informado" | corrigido | 18 |
| Oportunidades | Datas em dois formatos | Leitura de AAAA-MM-DD e DD/MM/AAAA → ISO | corrigido | 162 |
| Oportunidades | Fechamento inválido (31/02, mês 13) ou antes da abertura | Em negócio fechado, usa a data da última mudança de etapa (= dia em que virou Ganho/Perdido) | corrigido | 9 |
| Oportunidades | Data inválida sem fonte alternativa | Não dá para calcular ciclo nem mês → descarte | descartado | 3 |
| Itens | Item de oportunidade inexistente (órfão) | Descarte | descartado | 4 |
| Itens | Itens das 3 oportunidades descartadas | Descarte em cascata | descartado | 6 |
| Itens | Quantidade 0 | Descarte | descartado | 3 |
| Oportunidades | Valor nulo | Valor = soma (quantidade × preço) dos itens | corrigido | 24 |
| Oportunidades | Valor negativo | Valor = soma dos itens | corrigido | 4 |
| Oportunidades | Valor diferente da soma dos itens | Itens são a fonte de verdade (no Salesforce o Amount também vira a soma dos itens) | corrigido | 2 |
| Oportunidades | Sem itens válidos | Mantém o valor original positivo e sinaliza | sinalizado | 1 |

## Resultado

| Tabela | Entrada | Saída | Descartados |
|---|---|---|---|
| Contas | 242 | 220 | 22 (9,1%) |
| Contatos | 304 | 283 | 21 (6,9%) |
| Oportunidades | 558 | 537 | 21 (3,8%) |
| Itens | 835 | 822 | 13 (1,6%) |

Atende ao mínimo do desafio: **537 oportunidades** (≥ 500) e **220 contas** (≥ 200).

## Decisões que valem explicar na defesa
- **Corrigir antes de descartar.** Só descartei o que não tinha como recuperar (3 oportunidades). Setor e origem nulos viraram "Não informado" para não perder receita na análise.
- **Contato sem e-mail não é apagado.** Ele ainda tem valor comercial; vira pendência sinalizada.
- **Itens como fonte de verdade do valor.** O valor digitado à mão erra mais do que a soma dos produtos — e o Salesforce já faz isso sozinho quando há produtos na oportunidade.
- **Sobrevivente da deduplicação = cadastro mais antigo**, porque costuma ter mais histórico ligado a ele.
- **Tudo é reexecutável**: rodar os dois scripts de novo gera exatamente os mesmos números.
