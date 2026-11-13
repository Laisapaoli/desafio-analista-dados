# 1. Modelo de dados no Salesforce

## Diagrama

```
                 ┌──────────────┐
                 │   Account    │ (Conta)
                 └──────┬───────┘
          Lookup padrão │ 1:N            1:N │ Lookup padrão
          ┌─────────────┘                    └──────────────┐
   ┌──────┴──────┐                                   ┌──────┴────────┐
   │   Contact   │                                   │  Opportunity  │◄──── Lookup ────┐
   └─────────────┘                                   └──────┬────────┘                 │
                                         Master-Detail      │ 1:N              ┌─────────┴───────────┐
                                         (padrão)           │                  │ Campanha_Captacao__c│
                                                     ┌──────┴──────────────┐   └─────────┬───────────┘
                                                     │ OpportunityLineItem │             │ 1:N  MASTER-DETAIL
                                                     │ (Item da Oport.)    │   ┌─────────┴─────────────────┐
                                                     └──────┬──────────────┘   │ Investimento_Campanha__c  │
                                                            │ N:1              └───────────────────────────┘
                                                     ┌──────┴──────┐
                                                     │  Product2   │ (+ PricebookEntry no Catálogo Padrão)
                                                     └─────────────┘
```

## Objetos e campos criados

| Objeto | Campo (API name) | Tipo | Para quê |
|---|---|---|---|
| Account | `Id_Externo__c` | Texto(10), **External ID**, único | Chave da carga e dos relacionamentos |
| Account | `UF__c` | Texto(2) | Estado (evita conflito com picklist de estados do endereço) |
| Account | `Porte__c` | Picklist: Pequena, Média, Grande | Segmentação |
| Account | `Data_Cadastro__c` | Data | Data de cadastro no sistema de origem |
| Contact | `Id_Externo__c` | Texto, External ID | Carga |
| Contact | `Email_Pendente__c` | Caixa de seleção | Marca contatos que ficaram sem e-mail válido no ETL |
| Opportunity | `Id_Externo__c` | Texto, External ID | Carga |
| Opportunity | `Data_Abertura__c` | Data | Data real de abertura (o `CreatedDate` vira a data da carga) |
| Opportunity | `Etapa_Maxima__c` | Picklist com as etapas | Etapa mais avançada que a oportunidade alcançou — base do funil |
| Opportunity | `Data_Ultima_Mudanca_Etapa__c` | Data | Base para detectar oportunidade parada |
| Opportunity | `Campanha_Captacao__c` | **Lookup** → Campanha_Captacao__c | Campanha que originou o negócio |
| Opportunity | `Dias_no_Funil__c` | **Fórmula** (Número) | ver abaixo |
| Opportunity | `Faixa_de_Valor__c` | **Fórmula** (Texto) | ver abaixo |
| Opportunity | `Dias_Parada__c` | **Fórmula** (Número) | ver abaixo |
| Campanha_Captacao__c (objeto novo) | `Name`, `Id_Externo__c`, `Canal__c` (picklist), `Data_Inicio__c`, `Data_Fim__c`, `Orcamento__c` (Moeda) | | Campanhas de captação de clientes |
| Campanha_Captacao__c | `Investimento_Total__c` | **Resumo de totalização** (SOMA de Valor_Investido__c) | Só existe porque a relação é Master-Detail |
| Investimento_Campanha__c (objeto novo) | `Campanha_Captacao__c` (**Master-Detail**), `Mes__c` (Data), `Valor_Investido__c` (Moeda) | | Gasto mensal de cada campanha |

Picklists que precisam ser ajustadas antes da carga:
- **Opportunity.StageName** (Configuração › Objeto Oportunidade › Etapa): Prospecção, Qualificação, Proposta, Negociação, Fechado Ganho (Fechado/Ganho), Fechado Perdido (Fechado/Perdido).
- **Opportunity.LeadSource** (Origem): Indicação, Inbound, Outbound, Evento, Parceiro, Não informado.
- **Opportunity.Type** (Tipo): Novo Negócio, Expansão.
- **Account.Industry** (Setor): Agronegócio, Construção, Varejo, Indústria, Saúde, Logística, Educação, Energia, Serviços, Não informado.

## Por que Master-Detail e por que Lookup (2 linhas cada)

**Master-Detail — Investimento_Campanha__c → Campanha_Captacao__c**
Um investimento mensal não existe sem a campanha: se a campanha for excluída, o gasto dela também deve sair, e o acesso segue o da campanha.
Além disso, o Master-Detail permite o campo de resumo `Investimento_Total__c`, que soma o gasto sem nenhum código.

**Lookup — Opportunity → Campanha_Captacao__c**
Nem toda oportunidade vem de uma campanha (indicação e parceiro, por exemplo), então o campo precisa ser opcional.
Apagar uma campanha não pode apagar negócios; e objeto padrão (Oportunidade) não pode ser "detalhe" de objeto customizado.

## Campos de fórmula

**Dias_no_Funil__c** (Número, 0 casas)
```
IF( IsClosed,
    CloseDate - Data_Abertura__c,
    TODAY() - Data_Abertura__c )
```

**Faixa_de_Valor__c** (Texto) — mesmas faixas usadas no SQL e no Power BI
```
IF( ISBLANK(Amount), "Sem valor",
  IF( Amount < 10000, "1. Pequeno (< R$ 10 mil)",
    IF( Amount < 50000, "2. Médio (R$ 10–50 mil)",
        "3. Grande (≥ R$ 50 mil)" )))
```

**Dias_Parada__c** (Número) — usado no relatório de pipeline parado e no Flow
```
IF( IsClosed, NULL, TODAY() - Data_Ultima_Mudanca_Etapa__c )
```

## Regras de validação

**Fechamento_Antes_da_Abertura** (Opportunity) — impede o problema que mais apareceu na origem
```
AND( NOT(ISBLANK(Data_Abertura__c)), CloseDate < Data_Abertura__c )
```
Mensagem: "A data de fechamento não pode ser anterior à data de abertura." (exibir no campo CloseDate)

**Valor_Negativo** (Opportunity) — opcional, segunda regra
```
Amount < 0
```
Mensagem: "O valor da oportunidade não pode ser negativo."

> Dica: crie as regras **depois** de testar a carga com os dados limpos. Para mostrar que elas funcionam, tente importar 2 ou 3 linhas da base bruta (`dados/raw/oportunidades.csv`) com data trocada — o Data Loader vai rejeitar e gerar o arquivo de erro. Tire print disso: é ótima evidência de qualidade de dados.

## Por que não usei um objeto de histórico de etapas

A Developer Edition tem só 5 MB de dados (~2.500 registros de 2 KB). Com 220 contas, 283 contatos, 537 oportunidades e 822 itens a base já usa ~3,9 MB. Um histórico com uma linha por mudança de etapa passaria de 2.000 registros e estouraria o limite. A solução foi guardar a **etapa máxima alcançada** na própria oportunidade — suficiente para o funil — e a data da última mudança de etapa para o alerta de oportunidade parada. Em produção, eu ativaria o *Field History Tracking* de Etapa (ou usaria o `OpportunityHistory` nativo).
