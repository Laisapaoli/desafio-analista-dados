"""
Gera a base SINTÉTICA do desafio (dados fictícios), já com problemas de
qualidade inseridos de propósito: duplicados, datas inválidas, nulos e
grafias inconsistentes.

Uso:  python etl/00_gerar_dados_sinteticos.py
Saída: dados/raw/*.csv
"""
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
random.seed(SEED)

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "dados" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

DATA_EXTRACAO = date(2026, 10, 31)          # "hoje" da base
INICIO = date(2024, 1, 1)
FIM_ABERTURA = date(2026, 9, 30)

# ---------------------------------------------------------------- produtos
produtos = pd.DataFrame([
    ("PRD-01", "Licença Básica",      "Licença",  1500),
    ("PRD-02", "Licença Pro",         "Licença",  3200),
    ("PRD-03", "Licença Enterprise",  "Licença",  6800),
    ("PRD-04", "Implantação",         "Serviço", 12000),
    ("PRD-05", "Treinamento",         "Serviço",  2500),
    ("PRD-06", "Hora de Consultoria", "Serviço",   350),
    ("PRD-07", "Suporte Premium",     "Suporte",  4800),
    ("PRD-08", "Integração via API",  "Serviço",  9500),
], columns=["id_externo", "nome", "familia", "preco_lista"])

# --------------------------------------------------------------- campanhas
canais_camp = ["Inbound", "Evento", "Outbound"]
camp_rows = []
nomes_camp = {
    "Inbound": ["Webinar Gestão Comercial", "E-book CRM na Prática", "SEO Blog Vendas",
                "Webinar Indicadores", "Landing Page Teste Grátis"],
    "Evento": ["Feira Varejo SP", "Summit Agro Goiânia", "Meetup Indústria 4.0"],
    "Outbound": ["Cadência SDR Indústria", "Cadência SDR Saúde",
                 "Cadência SDR Serviços", "Lista Fria LinkedIn"],
}
i = 1
for canal, nomes in nomes_camp.items():
    for n in nomes:
        ini = INICIO + timedelta(days=int(rng.integers(0, 900)))
        camp_rows.append((f"CMP-{i:02d}", n, canal, ini,
                          ini + timedelta(days=int(rng.integers(30, 120))),
                          int(rng.choice([5000, 8000, 12000, 20000, 35000]))))
        i += 1
campanhas = pd.DataFrame(camp_rows, columns=[
    "id_externo", "nome", "canal", "data_inicio", "data_fim", "orcamento"])

# investimento mensal por campanha (objeto detalhe da campanha)
inv_rows = []
for _, c in campanhas.iterrows():
    meses = pd.period_range(c["data_inicio"], c["data_fim"], freq="M")
    partes = rng.dirichlet(np.ones(len(meses)))
    for m, frac in zip(meses, partes):
        inv_rows.append((c["id_externo"], m.start_time.date(), round(c["orcamento"] * frac, 2)))
investimentos = pd.DataFrame(inv_rows, columns=["campanha_id", "mes", "valor_investido"])
investimentos.insert(0, "id_externo", [f"INV-{i:03d}" for i in range(1, len(investimentos) + 1)])

# ------------------------------------------------------------------ contas
prefixos = ["Agro", "Construtora", "Distribuidora", "Indústria", "Clínica", "Rede",
            "Transportadora", "Metalúrgica", "Laboratório", "Escola", "Supermercados",
            "Farmácia", "Logística", "Têxtil", "Energia", "Grupo", "Hospital", "Colégio"]
nucleos = ["Vale Verde", "Horizonte", "São Jorge", "Aurora", "Pioneira", "Três Rios",
           "Boa Vista", "Atlântico", "Cerrado", "Primavera", "Santa Luzia", "Nova Era",
           "Ipê", "Araucária", "Monte Alegre", "Bandeirantes", "Itapuã", "Jequitibá",
           "Serra Azul", "Paraná", "Mantiqueira", "Guaporé", "Sol Nascente", "Ribeirão"]
sufixos = ["Ltda", "S.A.", "Ltda", "ME", "Ltda", "EIRELI"]
setor_por_prefixo = {
    "Agro": "Agronegócio", "Construtora": "Construção", "Distribuidora": "Varejo",
    "Indústria": "Indústria", "Clínica": "Saúde", "Rede": "Varejo",
    "Transportadora": "Logística", "Metalúrgica": "Indústria", "Laboratório": "Saúde",
    "Escola": "Educação", "Supermercados": "Varejo", "Farmácia": "Saúde",
    "Logística": "Logística", "Têxtil": "Indústria", "Energia": "Energia",
    "Grupo": "Serviços", "Hospital": "Saúde", "Colégio": "Educação"}
ufs = ["SP", "SP", "SP", "RJ", "MG", "MG", "PR", "RS", "SC", "GO", "DF", "BA", "PE"]

nomes_usados = set()
contas = []
n_contas = 220
while len(contas) < n_contas:
    p, n, s = random.choice(prefixos), random.choice(nucleos), random.choice(sufixos)
    nome = f"{p} {n} {s}"
    chave = f"{p} {n}"
    if chave in nomes_usados:
        continue
    nomes_usados.add(chave)
    k = len(contas) + 1
    porte = rng.choice(["Pequena", "Média", "Grande"], p=[0.5, 0.35, 0.15])
    contas.append(dict(
        id_externo=f"ACC-{k:04d}", nome=nome, setor=setor_por_prefixo[p],
        uf=random.choice(ufs), porte=porte,
        data_cadastro=INICIO + timedelta(days=int(rng.integers(0, 700)))))
contas = pd.DataFrame(contas)

# ---------------------------------------------------------------- contatos
pnomes = ["Ana", "João", "Maria", "José", "Luíza", "Carlos", "Fernanda", "Paulo",
          "Juliana", "Marcos", "Patrícia", "Rafael", "Camila", "André", "Letícia",
          "Bruno", "Aline", "Diego", "Débora", "Sérgio", "Mônica", "Thiago", "Lúcia", "Vítor"]
snomes = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Ferreira",
          "Rodrigues", "Almeida", "Nascimento", "Araújo", "Ribeiro", "Gonçalves", "Conceição"]
cargos = ["Diretor Comercial", "Gerente de TI", "CEO", "Coordenador de Vendas",
          "Analista de Compras", "Gerente Financeiro", "Sócio"]


def sem_acento(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


contatos = []
k = 1
for _, c in contas.iterrows():
    dominio = sem_acento(c["nome"].split()[1].lower()) + sem_acento(
        c["nome"].split()[0].lower())[:4] + ".com.br"
    for _ in range(int(rng.choice([1, 1, 2]))):
        pn, sn = random.choice(pnomes), random.choice(snomes)
        email = f"{sem_acento(pn).lower()}.{sem_acento(sn).lower()}{k}@{dominio}"
        contatos.append(dict(id_externo=f"CTT-{k:04d}", conta_id=c["id_externo"],
                             nome=pn, sobrenome=sn, email=email,
                             telefone=f"(11) 9{rng.integers(1000, 9999)}-{rng.integers(1000, 9999)}",
                             cargo=random.choice(cargos)))
        k += 1
contatos = pd.DataFrame(contatos)

# ----------------------------------------------------------- oportunidades
canais = ["Indicação", "Inbound", "Outbound", "Evento", "Parceiro"]
# ciclo base (dias) e prob. de ganho por canal -> sinal que o teste vai achar
ciclo_base = {"Indicação": 34, "Parceiro": 45, "Inbound": 52, "Evento": 60, "Outbound": 74}
p_ganho = {"Indicação": 0.46, "Parceiro": 0.36, "Inbound": 0.30, "Evento": 0.25, "Outbound": 0.17}
ETAPAS = ["Prospecção", "Qualificação", "Proposta", "Negociação"]

# contas com peso tipo Pareto -> concentração de receita (curva ABC)
peso_conta = rng.pareto(1.6, n_contas) + 0.2
peso_conta *= np.where(contas["porte"] == "Grande", 2.5, 1.0)
peso_conta /= peso_conta.sum()

n_opps = 540
dias_total = (FIM_ABERTURA - INICIO).days
# crescimento de volume ao longo do tempo (mais opps em 2025/2026)
u = rng.random(n_opps) ** 0.75
aberturas = sorted(INICIO + timedelta(days=int(x * dias_total)) for x in u)

opps, itens, hist = [], [], []
it_k = 1
for idx, abertura in enumerate(aberturas, start=1):
    oid = f"OPP-{idx:04d}"
    conta = contas.iloc[rng.choice(n_contas, p=peso_conta)]
    # em 2026 o Outbound ganha peso (nova equipe de SDR) -> risco no resumo
    pc = np.array([0.18, 0.30, 0.22, 0.15, 0.15])
    if abertura >= date(2026, 1, 1):
        pc = np.array([0.14, 0.24, 0.38, 0.12, 0.12])
    canal = rng.choice(canais, p=pc)
    camp = None
    if canal in canais_camp and rng.random() < 0.8:
        cand = campanhas[campanhas["canal"] == canal]
        camp = cand.sample(1, random_state=int(rng.integers(1e9)))["id_externo"].iloc[0]

    # itens
    n_it = int(rng.choice([1, 2], p=[0.45, 0.55]))
    prods = produtos.sample(n_it, random_state=int(rng.integers(1e9)))
    valor = 0
    linhas = []
    for _, p in prods.iterrows():
        if p["id_externo"] == "PRD-06":
            q = int(rng.integers(10, 81))
        elif p["familia"] == "Licença":
            q = int(rng.integers(3, 41)) * (3 if conta["porte"] == "Grande" else 1)
        else:
            q = 1
        preco = float(p["preco_lista"]) * float(rng.choice([1, 1, 0.95, 0.9]))
        valor += q * preco
        linhas.append((p["id_externo"], q, round(preco, 2)))
    valor = round(valor, 2)
    for pid, q, preco in linhas:
        itens.append(dict(id_externo=f"ITM-{it_k:05d}", oportunidade_id=oid,
                          produto_id=pid, quantidade=q, preco_unitario=preco))
        it_k += 1

    ciclo = int(ciclo_base[canal] * np.exp(rng.normal(0, 0.45)) * (valor / 40000) ** 0.18)
    ciclo = max(ciclo, 5)
    fechamento = abertura + timedelta(days=ciclo)
    ganho = rng.random() < p_ganho[canal] * (0.85 if valor > 120000 else 1)

    if fechamento > DATA_EXTRACAO:
        # ainda aberta
        frac = (DATA_EXTRACAO - abertura).days / ciclo
        etapa_idx = min(int(frac * 4), 3)
        caminho = ETAPAS[: etapa_idx + 1]
        etapa_final = caminho[-1]
        status = "Aberta"
        # algumas abertas "esquecidas": data prevista vencida
        if rng.random() < 0.25 and (DATA_EXTRACAO - abertura).days > 75:
            fechamento = DATA_EXTRACAO - timedelta(days=int(rng.integers(5, 60)))
    elif ganho:
        caminho = ETAPAS + ["Fechado Ganho"]
        etapa_final, status = "Fechado Ganho", "Ganha"
    else:
        chegou = int(rng.choice([0, 1, 2, 3], p=[0.30, 0.30, 0.25, 0.15]))
        caminho = ETAPAS[: chegou + 1] + ["Fechado Perdido"]
        etapa_final, status = "Fechado Perdido", "Perdida"

    # datas de entrada em cada etapa
    n_passos = len(caminho)
    if status == "Aberta":
        fim_ref = min(DATA_EXTRACAO, abertura + timedelta(days=ciclo))
        cortes = sorted(rng.random(n_passos - 1)) if n_passos > 1 else []
        datas = [abertura] + [abertura + timedelta(days=int(c * (fim_ref - abertura).days))
                              for c in cortes]
    else:
        cortes = sorted(rng.random(n_passos - 2)) if n_passos > 2 else []
        datas = [abertura] + [abertura + timedelta(days=int(c * ciclo)) for c in cortes] + [fechamento]
    for etapa, d in zip(caminho, datas):
        hist.append(dict(oportunidade_id=oid, etapa=etapa, data_entrada=d))

    ult = max(d for d in datas)
    opps.append(dict(etapa_maxima=[e for e in caminho if e != "Fechado Perdido"][-1],
                     data_ultima_mudanca_etapa=ult, id_externo=oid, nome=f"{conta['nome'].split(' ')[0]} {conta['nome'].split(' ')[1]} - {oid[-4:]}",
                     conta_id=conta["id_externo"], etapa=etapa_final, origem=canal,
                     campanha_id=camp, data_abertura=abertura, data_fechamento=fechamento,
                     valor=valor))

opps = pd.DataFrame(opps)
itens = pd.DataFrame(itens)
# (hist só é usado internamente para gerar as datas; não vai para a base)

# tipo: 1ª venda ganha da conta = Novo Negócio, depois Expansão
opps = opps.sort_values("data_abertura")
ganhas = opps[opps["etapa"] == "Fechado Ganho"]
primeira = ganhas.groupby("conta_id")["id_externo"].first()
opps["tipo"] = np.where(opps["id_externo"].isin(primeira.values) | ~opps["conta_id"].isin(primeira.index),
                        "Novo Negócio", "Expansão")

# =========================================================================
#                 INSERÇÃO PROPOSITAL DE PROBLEMAS DE QUALIDADE
# =========================================================================
problemas = []

# --- contas: grafia inconsistente de UF e setor nulo
variantes_uf = {"SP": ["São Paulo", "sao paulo", "S.Paulo", " sp"], "MG": ["Minas Gerais", "mg"],
                "RJ": ["Rio de Janeiro", "rj "], "PR": ["Paraná", "Parana"]}
idx = contas.sample(35, random_state=1).index
for i in idx:
    uf = contas.at[i, "uf"]
    if uf in variantes_uf:
        contas.at[i, "uf"] = random.choice(variantes_uf[uf])
problemas.append(("contas", "UF com grafia inconsistente", len(idx)))
idx = contas.sample(14, random_state=2).index
contas.loc[idx, "setor"] = None
problemas.append(("contas", "setor nulo", 14))

# --- contas duplicadas (variação de grafia) + oportunidades apontando p/ elas
dups = contas.sample(22, random_state=3).copy()
def variar(nome):
    op = random.choice(["upper", "sem_acento", "espaco", "sufixo"])
    if op == "upper":
        return nome.upper()
    if op == "sem_acento":
        return sem_acento(nome) if sem_acento(nome) != nome else nome.lower()
    if op == "espaco":
        return "  " + nome.replace(" ", "  ") + " "
    return nome.replace("Ltda", "LTDA.").replace("S.A.", "SA").replace("ME", "M.E.")
dups["nome"] = dups["nome"].map(variar)
mapa_dup = {}
for j, (i, r) in enumerate(dups.iterrows(), start=1):
    novo = f"ACC-9{j:03d}"
    mapa_dup[novo] = r["id_externo"]
    dups.at[i, "id_externo"] = novo
    dups.at[i, "data_cadastro"] = r["data_cadastro"] + timedelta(days=int(rng.integers(30, 300)))
contas = pd.concat([contas, dups], ignore_index=True)
problemas.append(("contas", "contas duplicadas (nome com variação)", 22))
# parte das opps dessas contas foi registrada na conta duplicada
inv = {v: k for k, v in mapa_dup.items()}
alvo = opps[opps["conta_id"].isin(inv.keys())].sample(frac=0.4, random_state=4).index
opps.loc[alvo, "conta_id"] = opps.loc[alvo, "conta_id"].map(inv)

# --- contatos: duplicados, e-mail inválido e nulo
cd = contatos.sample(20, random_state=5).copy()
cd["email"] = cd["email"].str.upper()
cd["nome"] = cd["nome"].map(sem_acento)
cd["id_externo"] = [f"CTT-9{j:03d}" for j in range(1, 21)]
contatos = pd.concat([contatos, cd], ignore_index=True)
problemas.append(("contatos", "contatos duplicados (e-mail em maiúscula / nome sem acento)", 20))
idx = contatos.sample(15, random_state=6).index
contatos.loc[idx, "email"] = None
problemas.append(("contatos", "e-mail nulo", 15))
idx = contatos.drop(idx).sample(8, random_state=7).index
contatos.loc[idx, "email"] = contatos.loc[idx, "email"].str.replace("@", ".", regex=False)
problemas.append(("contatos", "e-mail inválido (sem @)", 8))

# --- oportunidades: grafia de etapa/origem, nulos, valores, datas
def fmt_data(d):
    return d.strftime("%d/%m/%Y") if rng.random() < 0.3 else d.isoformat()
opps["data_abertura"] = opps["data_abertura"].map(fmt_data)
opps["data_fechamento"] = opps["data_fechamento"].map(fmt_data)
problemas.append(("oportunidades", "datas em dois formatos (ISO e dd/mm/aaaa)", None))

var_etapa = {"Fechado Ganho": ["fechado ganho", "Ganho", "Closed Won", "FECHADO GANHO"],
             "Fechado Perdido": ["Perdido", "Closed Lost", "fechado perdido"],
             "Proposta": ["proposta", "Proposta "], "Negociação": ["Negociacao", "negociação"]}
idx = opps[opps["etapa"].isin(var_etapa)].sample(40, random_state=8).index
for i in idx:
    opps.at[i, "etapa"] = random.choice(var_etapa[opps.at[i, "etapa"]])
problemas.append(("oportunidades", "etapa com grafia inconsistente", 40))

var_origem = {"Indicação": ["Indicacao", "indicação", "INDICAÇÃO"], "Inbound": ["inbound", "INBOUND"],
              "Outbound": ["outbound", "Out-bound"], "Evento": ["evento", "Eventos"], "Parceiro": ["parceiro"]}
idx = opps.sample(45, random_state=9).index
for i in idx:
    opps.at[i, "origem"] = random.choice(var_origem[opps.at[i, "origem"]])
problemas.append(("oportunidades", "origem com grafia inconsistente", 45))
idx = opps.drop(idx).sample(18, random_state=10).index
opps.loc[idx, "origem"] = None
problemas.append(("oportunidades", "origem nula", 18))

idx_nulo = opps.sample(24, random_state=11).index
opps.loc[idx_nulo, "valor"] = None
problemas.append(("oportunidades", "valor nulo", 24))
idx_neg = opps.drop(idx_nulo).sample(4, random_state=12).index
opps.loc[idx_neg, "valor"] = -opps.loc[idx_neg, "valor"]
problemas.append(("oportunidades", "valor negativo", 4))

fechadas = opps[opps["etapa"].str.lower().str.contains("fechado|ganho|perdido|closed")]
idx_inv = fechadas.sample(7, random_state=13).index
invalidas = ["31/02/2025", "2025-13-05", "00/00/0000", "2024-02-30", "32/01/2026", "abc", "2025-11-31"]
opps.loc[idx_inv, "data_fechamento"] = invalidas
problemas.append(("oportunidades", "data de fechamento inválida", 7))
idx_inv2 = fechadas.drop(idx_inv).sample(5, random_state=14).index
for i in idx_inv2:   # fechamento antes da abertura (dia/mês trocados no sistema de origem)
    opps.at[i, "data_fechamento"] = "2023-12-15"
problemas.append(("oportunidades", "fechamento anterior à abertura", 5))
# 3 sem chance de recuperação (nem histórico) -> serão descartadas
sem_hist = list(idx_inv[:3])
opps.loc[sem_hist, "data_ultima_mudanca_etapa"] = None

dup_opps = opps.sample(18, random_state=15)
opps = pd.concat([opps, dup_opps], ignore_index=True).sample(frac=1, random_state=16)
problemas.append(("oportunidades", "linhas duplicadas exatas", 18))

# --- itens: órfãos e quantidade zero
orf = itens.sample(4, random_state=17).copy()
orf["oportunidade_id"] = ["OPP-7001", "OPP-7002", "OPP-7003", "OPP-7004"]
orf["id_externo"] = [f"ITM-9{j:04d}" for j in range(1, 5)]
itens = pd.concat([itens, orf], ignore_index=True)
problemas.append(("itens", "itens órfãos (oportunidade inexistente)", 4))
idx = itens.sample(3, random_state=18).index
itens.loc[idx, "quantidade"] = 0
problemas.append(("itens", "quantidade zero", 3))

# ------------------------------------------------------------------ salvar
contas.sample(frac=1, random_state=19).to_csv(RAW / "contas.csv", index=False)
contatos.to_csv(RAW / "contatos.csv", index=False)
opps.to_csv(RAW / "oportunidades.csv", index=False)
itens.to_csv(RAW / "itens_oportunidade.csv", index=False)
produtos.to_csv(RAW / "produtos.csv", index=False)
campanhas.to_csv(RAW / "campanhas_captacao.csv", index=False)
investimentos.to_csv(RAW / "investimentos_campanha.csv", index=False)
pd.DataFrame(problemas, columns=["tabela", "problema_inserido", "qtd"]).to_csv(
    RAW / "_gabarito_problemas_inseridos.csv", index=False)

for f in sorted(RAW.glob("*.csv")):
    print(f"{f.name:40s} {len(pd.read_csv(f)):>5} linhas")
