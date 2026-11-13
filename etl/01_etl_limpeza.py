"""
ETL de limpeza: dados/raw  ->  dados/limpo  (+ dados/salesforce para carga)

Cada regra registra quantos registros afetou em dados/limpo/_log_etl.csv,
que é a base da documentação do ETL.

Uso:  python etl/01_etl_limpeza.py
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW, LIMPO, SF = BASE / "dados/raw", BASE / "dados/limpo", BASE / "dados/salesforce"
LIMPO.mkdir(parents=True, exist_ok=True)
SF.mkdir(parents=True, exist_ok=True)

log = []


def registrar(tabela, regra, acao, n):
    log.append(dict(tabela=tabela, regra=regra, acao=acao, registros_afetados=int(n)))
    print(f"[{tabela:13s}] {regra:55s} {acao:10s} {int(n):>4}")


def sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def chave_nome(nome):
    """Chave de comparação de empresa: minúsculas, sem acento, sem pontuação,
    sem sufixo societário e sem espaços repetidos."""
    t = sem_acento(str(nome)).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\b(ltda|sa|s a|me|m e|eireli)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_data(s):
    """Aceita AAAA-MM-DD e DD/MM/AAAA. Inválida -> NaT."""
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip()
    fmt = "%d/%m/%Y" if "/" in s else "%Y-%m-%d"
    return pd.to_datetime(s, format=fmt, errors="coerce")


contas = pd.read_csv(RAW / "contas.csv")
contatos = pd.read_csv(RAW / "contatos.csv")
opps = pd.read_csv(RAW / "oportunidades.csv")
itens = pd.read_csv(RAW / "itens_oportunidade.csv")
produtos = pd.read_csv(RAW / "produtos.csv")
campanhas = pd.read_csv(RAW / "campanhas_captacao.csv")
investimentos = pd.read_csv(RAW / "investimentos_campanha.csv")

entrada = {"contas": len(contas), "contatos": len(contatos), "oportunidades": len(opps),
           "itens": len(itens)}

# ============================================================== CONTAS
antes = contas["nome"].copy()
contas["nome"] = contas["nome"].str.strip().str.replace(r"\s+", " ", regex=True)
registrar("contas", "espaços extras no nome", "corrigido", (antes != contas["nome"]).sum())

mapa_uf = {"sao paulo": "SP", "s.paulo": "SP", "sp": "SP", "minas gerais": "MG", "mg": "MG",
           "rio de janeiro": "RJ", "rj": "RJ", "parana": "PR", "pr": "PR"}
uf_norm = contas["uf"].map(lambda x: sem_acento(str(x)).strip().lower())
nova_uf = uf_norm.map(mapa_uf).fillna(contas["uf"].str.strip().str.upper())
registrar("contas", "UF padronizada para sigla", "corrigido", (nova_uf != contas["uf"]).sum())
contas["uf"] = nova_uf

registrar("contas", "setor nulo -> 'Não informado'", "corrigido", contas["setor"].isna().sum())
contas["setor"] = contas["setor"].fillna("Não informado")

# deduplicação: mesma chave de nome -> mantém o cadastro mais antigo
contas["data_cadastro"] = pd.to_datetime(contas["data_cadastro"])
contas["chave"] = contas["nome"].map(chave_nome)
contas = contas.sort_values(["chave", "data_cadastro"])
mestre = contas.groupby("chave")["id_externo"].transform("first")
mapa_contas = dict(zip(contas["id_externo"], mestre))          # id -> id mestre
n_dup = (contas["id_externo"] != mestre).sum()
contas = contas[contas["id_externo"] == mestre].drop(columns="chave")
registrar("contas", "conta duplicada (mesmo nome normalizado)", "descartado", n_dup)

# ============================================================ CONTATOS
n_remap = (contatos["conta_id"].map(mapa_contas) != contatos["conta_id"]).sum()
contatos["conta_id"] = contatos["conta_id"].map(mapa_contas)
registrar("contatos", "conta apontando p/ duplicada -> conta mestre", "corrigido", n_remap)

contatos["email"] = contatos["email"].str.strip().str.lower()
valido = contatos["email"].str.match(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$", na=False)
n_inv = (~valido & contatos["email"].notna()).sum()
contatos.loc[~valido, "email"] = None
registrar("contatos", "e-mail inválido -> nulo (manter contato)", "corrigido", n_inv)
registrar("contatos", "e-mail nulo (mantido, sinalizado)", "sinalizado", contatos["email"].isna().sum())
contatos["email_pendente"] = contatos["email"].isna()

# duplicado = mesmo e-mail OU mesmo nome normalizado na mesma conta
contatos["chave_nome"] = (contatos["nome"] + " " + contatos["sobrenome"]).map(chave_nome)
contatos = contatos.sort_values("id_externo")
d1 = contatos["email"].notna() & contatos.duplicated("email")
d2 = contatos.duplicated(["conta_id", "chave_nome"])
n_dup = (d1 | d2).sum()
contatos = contatos[~(d1 | d2)].drop(columns="chave_nome")
registrar("contatos", "contato duplicado (e-mail ou nome+conta)", "descartado", n_dup)

# ======================================================= OPORTUNIDADES
n = opps.duplicated().sum()
opps = opps.drop_duplicates()
registrar("oportunidades", "linha duplicada exata", "descartado", n)

n_remap = (opps["conta_id"].map(mapa_contas) != opps["conta_id"]).sum()
opps["conta_id"] = opps["conta_id"].map(mapa_contas)
registrar("oportunidades", "conta duplicada -> conta mestre", "corrigido", n_remap)

mapa_etapa = {"fechado ganho": "Fechado Ganho", "ganho": "Fechado Ganho", "closed won": "Fechado Ganho",
              "fechado perdido": "Fechado Perdido", "perdido": "Fechado Perdido",
              "closed lost": "Fechado Perdido", "proposta": "Proposta", "negociacao": "Negociação",
              "prospeccao": "Prospecção", "qualificacao": "Qualificação"}
nova = opps["etapa"].map(lambda x: mapa_etapa.get(sem_acento(str(x)).strip().lower()))
registrar("oportunidades", "etapa padronizada", "corrigido", (nova != opps["etapa"]).sum())
opps["etapa"] = nova

mapa_origem = {"indicacao": "Indicação", "inbound": "Inbound", "outbound": "Outbound",
               "out-bound": "Outbound", "evento": "Evento", "eventos": "Evento", "parceiro": "Parceiro"}
nova = opps["origem"].map(lambda x: mapa_origem.get(sem_acento(str(x)).strip().lower()))
registrar("oportunidades", "origem padronizada",
          "corrigido", ((nova != opps["origem"]) & opps["origem"].notna()).sum())
registrar("oportunidades", "origem nula -> 'Não informado'", "corrigido", opps["origem"].isna().sum())
opps["origem"] = nova.fillna("Não informado")

# datas
opps["data_abertura"] = opps["data_abertura"].map(parse_data)
fech_txt = opps["data_fechamento"].copy()
opps["data_fechamento"] = opps["data_fechamento"].map(parse_data)
registrar("oportunidades", "datas convertidas de dd/mm/aaaa p/ ISO", "corrigido",
          fech_txt.astype(str).str.contains("/").sum())

# fechamento inválido ou < abertura: em oportunidade FECHADA, a data da última
# mudança de etapa é a data em que ela foi para Ganho/Perdido -> usamos como fonte
opps["data_ultima_mudanca_etapa"] = pd.to_datetime(opps["data_ultima_mudanca_etapa"])
ruim = opps["data_fechamento"].isna() | (opps["data_fechamento"] < opps["data_abertura"])
fechada = opps["etapa"].isin(["Fechado Ganho", "Fechado Perdido"])
recuperavel = ruim & fechada & opps["data_ultima_mudanca_etapa"].notna()
opps.loc[recuperavel, "data_fechamento"] = opps.loc[recuperavel, "data_ultima_mudanca_etapa"]
registrar("oportunidades", "fechamento inválido/antes da abertura -> últ. mudança", "corrigido",
          recuperavel.sum())
n = (ruim & ~recuperavel).sum()
descartadas_ids = set(opps.loc[ruim & ~recuperavel, "id_externo"])
opps = opps[~(ruim & ~recuperavel)]
registrar("oportunidades", "data irrecuperável (sem data alternativa)", "descartado", n)

# itens primeiro (são a fonte de verdade do valor)
n = (~itens["oportunidade_id"].isin(opps["id_externo"]) &
     ~itens["oportunidade_id"].isin(descartadas_ids)).sum()
itens = itens[itens["oportunidade_id"].isin(opps["id_externo"]) |
              itens["oportunidade_id"].isin(descartadas_ids)]
registrar("itens", "item órfão (oportunidade inexistente)", "descartado", n)
n = itens["oportunidade_id"].isin(descartadas_ids).sum()
itens = itens[~itens["oportunidade_id"].isin(descartadas_ids)]
registrar("itens", "item de oportunidade descartada", "descartado", n)
n = (itens["quantidade"] <= 0).sum()
itens = itens[itens["quantidade"] > 0]
registrar("itens", "quantidade <= 0", "descartado", n)

soma_itens = (itens["quantidade"] * itens["preco_unitario"]).groupby(itens["oportunidade_id"]).sum().round(2)
calc = opps["id_externo"].map(soma_itens)
nulo = opps["valor"].isna()
neg = opps["valor"] < 0
registrar("oportunidades", "valor nulo -> soma dos itens", "corrigido", nulo.sum())
registrar("oportunidades", "valor negativo -> soma dos itens", "corrigido", neg.sum())
divergente = ~nulo & ~neg & ((opps["valor"] - calc).abs() > 0.01)
registrar("oportunidades", "valor diferente da soma dos itens -> soma", "corrigido", divergente.sum())
sem_itens = calc.isna()
ok_original = sem_itens & opps["valor"].gt(0)
registrar("oportunidades", "sem itens válidos -> mantém valor original", "sinalizado", ok_original.sum())
n = (sem_itens & ~ok_original).sum()
opps["valor"] = calc.where(~sem_itens, opps["valor"])
opps = opps[~(sem_itens & ~ok_original)]
registrar("oportunidades", "sem itens e sem valor válido", "descartado", n)


# derivados úteis para a análise (no Salesforce viram fórmulas)
opps["status"] = opps["etapa"].map({"Fechado Ganho": "Ganha", "Fechado Perdido": "Perdida"}).fillna("Aberta")
opps["ciclo_dias"] = (opps["data_fechamento"] - opps["data_abertura"]).dt.days.where(opps["status"] != "Aberta")

# ================================================================ SALVAR
for df, nome in [(contas, "contas"), (contatos, "contatos"), (opps, "oportunidades"),
                 (itens, "itens_oportunidade"), (produtos, "produtos"),
                 (campanhas, "campanhas_captacao"), (investimentos, "investimentos_campanha")]:
    df.to_csv(LIMPO / f"{nome}.csv", index=False, date_format="%Y-%m-%d")

pd.DataFrame(log).to_csv(LIMPO / "_log_etl.csv", index=False)
resumo = pd.DataFrame([
    ("contas", entrada["contas"], len(contas)), ("contatos", entrada["contatos"], len(contatos)),
    ("oportunidades", entrada["oportunidades"], len(opps)), ("itens", entrada["itens"], len(itens))],
    columns=["tabela", "linhas_entrada", "linhas_saida"])
resumo.to_csv(LIMPO / "_resumo_etl.csv", index=False)
print("\n", resumo.to_string(index=False))

# ======================== ARQUIVOS PRONTOS PARA O SALESFORCE (API names)
# Relacionamentos são resolvidos por ID externo (campo Id_Externo__c, External ID).
contas.rename(columns={"id_externo": "Id_Externo__c", "nome": "Name", "setor": "Industry",
                       "uf": "UF__c", "porte": "Porte__c",
                       "data_cadastro": "Data_Cadastro__c"}).to_csv(
    SF / "1_Account.csv", index=False, date_format="%Y-%m-%d")
contatos.rename(columns={"id_externo": "Id_Externo__c", "conta_id": "Account:Id_Externo__c",
                         "nome": "FirstName", "sobrenome": "LastName", "email": "Email",
                         "telefone": "Phone", "cargo": "Title",
                         "email_pendente": "Email_Pendente__c"}).to_csv(SF / "2_Contact.csv", index=False)
produtos.rename(columns={"id_externo": "ProductCode", "nome": "Name", "familia": "Family",
                         "preco_lista": "UnitPrice"}).assign(IsActive=True).to_csv(
    SF / "3_Product2_e_PricebookEntry.csv", index=False)
campanhas.rename(columns={"id_externo": "Id_Externo__c", "nome": "Name", "canal": "Canal__c",
                          "data_inicio": "Data_Inicio__c", "data_fim": "Data_Fim__c",
                          "orcamento": "Orcamento__c"}).to_csv(SF / "4_Campanha_Captacao__c.csv", index=False)
investimentos.rename(columns={"id_externo": "Id_Externo__c", "campanha_id": "Campanha_Captacao__r:Id_Externo__c",
                              "mes": "Mes__c", "valor_investido": "Valor_Investido__c"}).to_csv(
    SF / "5_Investimento_Campanha__c.csv", index=False)
opps.drop(columns=["status", "ciclo_dias"]).rename(columns={
    "id_externo": "Id_Externo__c", "nome": "Name", "conta_id": "Account:Id_Externo__c",
    "etapa": "StageName", "origem": "LeadSource", "campanha_id": "Campanha_Captacao__r:Id_Externo__c",
    "data_abertura": "Data_Abertura__c", "data_fechamento": "CloseDate", "valor": "Amount",
    "tipo": "Type", "etapa_maxima": "Etapa_Maxima__c",
    "data_ultima_mudanca_etapa": "Data_Ultima_Mudanca_Etapa__c"}).to_csv(SF / "6_Opportunity.csv", index=False, date_format="%Y-%m-%d")
itens.rename(columns={"id_externo": "Id_Externo__c", "oportunidade_id": "Opportunity:Id_Externo__c",
                      "produto_id": "ProductCode", "quantidade": "Quantity",
                      "preco_unitario": "UnitPrice"}).to_csv(SF / "7_OpportunityLineItem.csv", index=False)

# ============== APOIO AO POWER BI: funil em formato longo (1 linha por etapa alcançada)
ORDEM = {"Prospecção": 1, "Qualificação": 2, "Proposta": 3, "Negociação": 4, "Fechado Ganho": 5}
PBI = BASE / "dados" / "powerbi"
PBI.mkdir(exist_ok=True)
linhas = [(r.id_externo, e, o) for r in opps.itertuples()
          for e, o in ORDEM.items() if o <= ORDEM[r.etapa_maxima]]
pd.DataFrame(linhas, columns=["oportunidade_id", "etapa", "ordem"]).to_csv(PBI / "funil_etapas.csv", index=False)
