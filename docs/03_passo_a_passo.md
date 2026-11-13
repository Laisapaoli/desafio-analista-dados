# 3. Passo a passo do que você faz nas plataformas

Os arquivos, o SQL, a estatística e a documentação já estão prontos. O que depende da **sua conta** (Trailhead, Salesforce, Power BI) está aqui, na ordem. Tire print de cada etapa concluída — os prints são evidência na entrega.

---

## Parte 1 — Emblemas do Trailhead (≈ 6 a 10 h)
Você já tem o **Admin Beginner**. Faltam:
1. Módulo **Reports & Dashboards for Lightning Experience**
2. Módulo **Data Modeling**
3. Módulo **Data Management** (ensina exatamente o Data Import Wizard e o Data Loader que você vai usar na Parte 2)

Faça a Parte 1 **antes** da Parte 2: os módulos ensinam o que você vai fazer. Na entrega, mande o link do seu perfil público.

---

## Parte 2 — Salesforce (Developer Edition)

### 2.1 Criar a org
1. Cadastre-se em developer.salesforce.com/signup (gratuito).
2. **Apague os dados de exemplo** que vêm na org (contas/oportunidades de demonstração): o limite é 5 MB e a nossa base usa ~3,9 MB. Confira em Configuração › *Uso de armazenamento*.

### 2.2 Criar o modelo (siga `docs/01_modelo_salesforce.md`)
1. Ajuste as picklists (Etapa, Origem, Tipo, Setor).
2. Crie os campos personalizados em Conta, Contato e Oportunidade — **marque `Id_Externo__c` como "ID externo" e "Exclusivo"**.
3. Crie o objeto **Campanha de Captação** (`Campanha_Captacao__c`) e o objeto **Investimento da Campanha** (`Investimento_Campanha__c`) com o campo **Mestre-detalhes** para a campanha.
4. Na Oportunidade, crie o campo de **Pesquisa (Lookup)** para Campanha de Captação.
5. Na Campanha, crie o **Resumo de totalização** `Investimento_Total__c`.
6. Crie os 3 campos de fórmula. **Deixe as regras de validação para depois da carga.**
7. Abra Configuração › *Schema Builder* e tire um print do modelo — vira o diagrama da entrega.

### 2.3 Carregar os dados (arquivos em `dados/salesforce/`, nesta ordem)

| # | Arquivo | Ferramenta | Observação |
|---|---|---|---|
| 1 | `1_Account.csv` | Data Import Wizard | Mapear colunas para os campos |
| 2 | `2_Contact.csv` | Data Import Wizard | Vincular à conta pelo `Id_Externo__c` da conta |
| 3 | `3_Product2_e_PricebookEntry.csv` | Data Loader | Primeiro insira os **Produtos**; depois as **Entradas de catálogo** (PricebookEntry) no *Catálogo de preços padrão* com o `UnitPrice` |
| 4 | `4_Campanha_Captacao__c.csv` | Data Import Wizard | — |
| 5 | `5_Investimento_Campanha__c.csv` | Data Loader (Upsert) | Relacionar pela campanha via `Id_Externo__c` |
| 6 | `6_Opportunity.csv` | Data Loader (Upsert) | Conta e campanha relacionadas por `Id_Externo__c`; adicione uma coluna `Pricebook2Id` com o Id do Catálogo padrão |
| 7 | `7_OpportunityLineItem.csv` | Data Loader (Insert) | Precisa do `PricebookEntryId`: exporte PricebookEntry (Id, ProductCode), faça PROCV no Excel pelo `ProductCode` e cole o Id |

- O **Data Import Wizard não importa Oportunidades nem Itens** — por isso o Data Loader (programa desktop) ou o **dataloader.io** (versão web gratuita).
- No Data Loader, ao fazer *Upsert*, ele pergunta qual campo usar para achar o registro relacionado: escolha `Id_Externo__c`.
- Guarde os arquivos `success` e `error` que o Data Loader gera — eles comprovam a carga.

### 2.4 Regras de validação e prova
Crie as 2 regras. Depois tente importar 3 linhas de `dados/raw/oportunidades.csv` que tenham data de fechamento anterior à abertura e tire print do erro.

### 2.5 Relatórios (3) e dashboard
1. **Tipo de relatório personalizado**: Configuração › Tipos de relatório › Novo. Objeto principal *Campanhas de Captação*, relacionado *Oportunidades* ("com ou sem"). Nome: "Campanhas com Oportunidades".
   - **Relatório 1 – Retorno por campanha** (usa esse tipo): agrupar por Canal e Campanha; colunas Investimento total, Soma do Valor (filtro Etapa = Fechado Ganho).
2. **Relatório 2 – Matriz origem × etapa (agrupamento duplo)**: tipo Oportunidades, formato *Matriz*: linhas = Origem, colunas = Etapa, valor = Soma do Valor e contagem.
3. **Relatório 3 – Pipeline parado**: tipo Oportunidades, filtros Fechado = Falso e `Dias_Parada__c` > 30, agrupar por Etapa.
4. **Dashboard** com: gráfico de funil por Etapa; medidor de taxa de ganho; barras de receita por Origem; tabela do pipeline parado; métrica de receita ganha no ano; barras de receita por mês.

### 2.6 Bônus — Flow de oportunidade parada
1. **Flow acionado por registro** (Oportunidade, ao atualizar, quando `StageName` mudar): atualiza `Data_Ultima_Mudanca_Etapa__c = TODAY()` e, se a nova etapa for mais avançada, `Etapa_Maxima__c`.
2. **Flow agendado** (diário, objeto Oportunidade, condição `IsClosed = Falso`): elemento *Decisão* `Dias_Parada__c > 30` → *Atualizar registro* marca uma caixa `Parada__c` e *Enviar notificação personalizada* (ou alerta de e-mail) ao proprietário.

---

## Parte 4 — Power BI

### Conexão
Obter dados › Texto/CSV: `dados/limpo/oportunidades.csv`, `contas.csv`, `campanhas_captacao.csv`, `investimentos_campanha.csv` e `dados/powerbi/funil_etapas.csv`.
(Em um ambiente real: conector *Objetos do Salesforce* direto; para a entrega, o CSV exportado basta e é o que o desafio pede.)

### Relacionamentos
- `contas[id_externo]` 1 → * `oportunidades[conta_id]`
- `campanhas_captacao[id_externo]` 1 → * `oportunidades[campanha_id]` e → * `investimentos_campanha[campanha_id]`
- `oportunidades[id_externo]` 1 → * `funil_etapas[oportunidade_id]`
- `Calendario[Data]` 1 → * `oportunidades[data_fechamento]`

### Tabela calendário (Modelagem › Nova tabela)
```DAX
Calendario =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2024, 1, 1 ), DATE ( 2026, 10, 31 ) ),   -- termina na data de corte
    "Ano", YEAR ( [Date] ),
    "Mes", FORMAT ( [Date], "MM" ),
    "AnoMes", FORMAT ( [Date], "YYYY-MM" )
)
```
Depois: *Marcar como tabela de datas*. O calendário termina na data de extração de propósito: assim o "ano anterior" compara jan–out com jan–out, e não com o ano inteiro.

### Medidas
```DAX
Receita Ganha = CALCULATE ( SUM ( oportunidades[valor] ), oportunidades[status] = "Ganha" )

Oportunidades Fechadas = CALCULATE ( COUNTROWS ( oportunidades ), oportunidades[status] <> "Aberta" )
Taxa de Ganho = DIVIDE ( CALCULATE ( COUNTROWS ( oportunidades ), oportunidades[status] = "Ganha" ), [Oportunidades Fechadas] )

Ticket Medio = DIVIDE ( [Receita Ganha], CALCULATE ( COUNTROWS ( oportunidades ), oportunidades[status] = "Ganha" ) )

Ciclo Mediano (dias) = CALCULATE ( MEDIAN ( oportunidades[ciclo_dias] ), oportunidades[status] <> "Aberta" )

Pipeline Aberto = CALCULATE ( SUM ( oportunidades[valor] ), oportunidades[status] = "Aberta" )

Retorno sobre Investimento = DIVIDE ( CALCULATE ( [Receita Ganha], NOT ISBLANK ( oportunidades[campanha_id] ) ),
                                      SUM ( investimentos_campanha[valor_investido] ) )
```

**Medida avançada documentada — Receita acumulada no ano × ano anterior**
```DAX
Receita YTD = TOTALYTD ( [Receita Ganha], Calendario[Date] )

Receita YTD Ano Anterior =
CALCULATE ( [Receita YTD], SAMEPERIODLASTYEAR ( Calendario[Date] ) )

Var YTD % =
DIVIDE ( [Receita YTD] - [Receita YTD Ano Anterior], [Receita YTD Ano Anterior] )
```
Como funciona: `TOTALYTD` soma a receita de 1º de janeiro até a última data do contexto; `SAMEPERIODLASTYEAR` desloca esse mesmo intervalo um ano para trás; `DIVIDE` evita erro quando o ano anterior é zero. Valor esperado para 2026: **R$ 4,34 mi × R$ 3,16 mi = +37,4%** (confira com o notebook).

### Página do dashboard (≥ 6 indicadores + filtros + funil)
- Cartões: Receita Ganha · Var YTD % · Taxa de Ganho · Ticket Médio · Ciclo Mediano · Pipeline Aberto · Retorno sobre Investimento
- **Funil**: visual *Funil* com `funil_etapas[etapa]` (ordenar por `ordem`) e contagem distinta de `oportunidade_id`
- Linha: Receita YTD e Receita YTD Ano Anterior por mês
- Barras: Taxa de Ganho por Origem
- **Segmentações (filtros)**: Ano, Origem, Setor, UF, Faixa de valor

Valores de conferência (base inteira, sem filtro): 537 oportunidades, 153 ganhas, taxa de ganho 29,9%, receita ganha total R$ 9,44 mi.
