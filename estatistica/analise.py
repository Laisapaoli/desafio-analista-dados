# %% [markdown]
# # Desafio Analista de Dados — Estatística e indicadores de negócio
# Base: export limpo do Salesforce (`dados/limpo`). Data de referência: 31/10/2026.
#
# Roteiro:
# 1. Correlação entre **valor da oportunidade** e **ciclo de venda**
# 2. Teste de hipótese: o ciclo de venda difere entre **Indicação** e **Outbound**?
# 3. Indicadores de apoio ao resumo executivo (receita YTD, conversão por canal, ROI de campanha, pipeline parado)

# %%
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path.cwd() if (Path.cwd() / "dados").exists() else Path.cwd().parent
L = BASE / "dados" / "limpo"
opps = pd.read_csv(L / "oportunidades.csv", parse_dates=["data_abertura", "data_fechamento",
                                                         "data_ultima_mudanca_etapa"])
contas = pd.read_csv(L / "contas.csv")
inv = pd.read_csv(L / "investimentos_campanha.csv")
camp = pd.read_csv(L / "campanhas_captacao.csv")
REF = pd.Timestamp("2026-10-31")
AZUL, CINZA, TEXTO = "#2a78d6", "#8a8984", "#52514e"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": CINZA, "axes.labelcolor": TEXTO,
                     "xtick.color": TEXTO, "ytick.color": TEXTO, "font.size": 10})

fechadas = opps[opps["status"] != "Aberta"].copy()
print(f"Oportunidades: {len(opps)} | fechadas: {len(fechadas)} | ganhas: {(opps.status=='Ganha').sum()}")

# %% [markdown]
# ## 1. Correlação: valor × ciclo de venda
# Ciclo = dias entre abertura e decisão (ganho ou perda). As duas variáveis são assimétricas
# (poucos negócios muito grandes), então a medida principal é a **correlação de Spearman**
# (baseada em postos, robusta a outliers). Pearson entra como comparação, com valor em log.

# %%
x, y = fechadas["valor"], fechadas["ciclo_dias"]
rho, p_s = stats.spearmanr(x, y)
r_log, p_p = stats.pearsonr(np.log(x), y)
r_raw, _ = stats.pearsonr(x, y)
print(f"Spearman rho = {rho:.3f} (p = {p_s:.2e})")
print(f"Pearson log(valor) x ciclo r = {r_log:.3f} (p = {p_p:.2e})")
print(f"Pearson valor bruto x ciclo r = {r_raw:.3f}  <- distorcido pelos negócios gigantes")
print(f"R² aproximado (Pearson log): {r_log**2:.1%} da variação do ciclo é explicada pelo valor")

fig, ax = plt.subplots(figsize=(7, 4))
ax.scatter(x, y, s=14, color=AZUL, alpha=0.55, edgecolors="none")
ax.set_xscale("log")
ax.set_xlabel("Valor da oportunidade (R$, escala log)")
ax.set_ylabel("Ciclo (dias)")
ax.set_title(f"Negócios maiores demoram mais (Spearman ρ = {rho:.2f})", loc="left", fontsize=11)
ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
fig.tight_layout(); fig.savefig(BASE / "estatistica" / "fig_valor_x_ciclo.png", dpi=150)
plt.show()

# %% [markdown]
# ## 2. Teste de hipótese — o ciclo difere entre Indicação e Outbound?
# - **H0:** a distribuição do ciclo é a mesma nos dois canais.
# - **H1:** as distribuições são diferentes (bicaudal). Nível de significância α = 5%.
#
# Primeiro verificamos normalidade (Shapiro-Wilk). Se os dados não forem normais, o teste t
# perde confiabilidade e usamos **Mann-Whitney U** (não paramétrico). O tamanho de efeito é a
# **correlação rank-biserial** e a diferença de medianas ganha intervalo de confiança por bootstrap.

# %%
ind = fechadas.loc[fechadas.origem == "Indicação", "ciclo_dias"].values
out = fechadas.loc[fechadas.origem == "Outbound", "ciclo_dias"].values
print(f"n Indicação = {len(ind)} | n Outbound = {len(out)}")
print(f"Mediana Indicação = {np.median(ind):.0f} dias | Mediana Outbound = {np.median(out):.0f} dias")
print(f"Média   Indicação = {ind.mean():.1f} dias | Média   Outbound = {out.mean():.1f} dias")
for nome, a in [("Indicação", ind), ("Outbound", out)]:
    print(f"Shapiro-Wilk {nome}: p = {stats.shapiro(a).pvalue:.4f}")

u, p_mw = stats.mannwhitneyu(ind, out, alternative="two-sided")
rbc = 1 - 2 * u / (len(ind) * len(out))      # rank-biserial (negativo = Indicação menor)
print(f"\nMann-Whitney U = {u:.0f} | p-valor = {p_mw:.2e} | rank-biserial = {rbc:.2f}")

rng = np.random.default_rng(0)
boot = [np.median(rng.choice(out, len(out))) - np.median(rng.choice(ind, len(ind))) for _ in range(5000)]
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"Diferença de medianas (Outbound − Indicação): {np.median(out)-np.median(ind):.0f} dias "
      f"[IC 95% bootstrap: {lo:.0f} a {hi:.0f}]")

t, p_t = stats.ttest_ind(np.log(ind), np.log(out), equal_var=False)
print(f"Robustez — Welch t em log(ciclo): p = {p_t:.2e}")

# %% [markdown]
# ### Controle de confusão: o canal importa mesmo descontando o valor do negócio?
# Outbound pode ter ciclo maior só porque vende negócios maiores. Regressão linear
# `log(ciclo) ~ canal + log(valor)` (mínimos quadrados) separa os dois efeitos.

# %%
d = fechadas[fechadas.origem.isin(["Indicação", "Outbound"])].copy()
X = np.column_stack([np.ones(len(d)), (d.origem == "Outbound").astype(float), np.log(d.valor)])
yv = np.log(d.ciclo_dias.values)
beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
res = yv - X @ beta
sigma2 = res @ res / (len(d) - X.shape[1])
se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
tval = beta / se
pval = 2 * stats.t.sf(np.abs(tval), len(d) - X.shape[1])
for nome, b, s, p in zip(["intercepto", "Outbound (vs Indicação)", "log(valor)"], beta, se, pval):
    print(f"{nome:25s} coef = {b:6.3f}  ep = {s:.3f}  p = {p:.2e}")
print(f"\nMantido o valor constante, Outbound leva ~{(np.exp(beta[1])-1):.0%} mais dias que Indicação.")

ordem = (fechadas.groupby("origem")["ciclo_dias"].median().sort_values().index.tolist())
fig, ax = plt.subplots(figsize=(7, 4))
bp = ax.boxplot([fechadas.loc[fechadas.origem == o, "ciclo_dias"] for o in ordem],
                tick_labels=ordem, patch_artist=True, widths=0.5,
                medianprops=dict(color="white", linewidth=2),
                flierprops=dict(marker="o", markersize=4, markerfacecolor=CINZA, markeredgecolor="none"))
for patch, o in zip(bp["boxes"], ordem):
    patch.set_facecolor(AZUL if o in ("Indicação", "Outbound") else "#c9c8c2")
    patch.set_edgecolor("none")
ax.set_ylabel("Ciclo (dias)")
ax.set_title("Ciclo de venda por canal (Indicação e Outbound em destaque)", loc="left", fontsize=11)
ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
fig.tight_layout(); fig.savefig(BASE / "estatistica" / "fig_ciclo_por_canal.png", dpi=150)
plt.show()

# %% [markdown]
# ### Conclusão em linguagem de negócio
# Negócios que vêm por **Indicação** fecham bem mais rápido do que os de **Outbound**, e a
# diferença não é acaso (p-valor muito abaixo de 5%). Mesmo comparando negócios do mesmo
# tamanho, o Outbound continua mais lento. Na prática: cada real investido em programa de
# indicação gira mais rápido no caixa, e a previsão de receita do Outbound precisa considerar
# um prazo maior.
#
# **Limitações**
# - Dados sintéticos e amostra pequena por canal; o resultado mostra o método, não um fato de mercado.
# - Estudo observacional: mostra associação, não causa (o tipo de cliente que chega por
#   indicação pode ser diferente).
# - Oportunidades ainda abertas ficam de fora (viés de sobrevivência: os ciclos mais longos
#   do período recente ainda não terminaram).
# - Ciclo inclui ganhas e perdidas; restringir a ganhas reduz n (ver célula abaixo).
# - "Origem" depende do preenchimento do vendedor; 18 registros vieram sem origem.

# %%
g = fechadas[fechadas.status == "Ganha"]
a, b = g.loc[g.origem == "Indicação", "ciclo_dias"], g.loc[g.origem == "Outbound", "ciclo_dias"]
print(f"Só ganhas -> n={len(a)} vs {len(b)}, medianas {a.median():.0f} vs {b.median():.0f} dias, "
      f"Mann-Whitney p = {stats.mannwhitneyu(a, b).pvalue:.2e}")

# %% [markdown]
# ## 3. Indicadores para o resumo executivo

# %%
ganhas = opps[opps.status == "Ganha"].copy()
ganhas["ano"] = ganhas.data_fechamento.dt.year
ytd = lambda ano: ganhas[(ganhas.ano == ano) & (ganhas.data_fechamento.dt.month <= 10)].valor.sum()
r26, r25 = ytd(2026), ytd(2025)
print("Receita ganha por ano (R$ mil):", (ganhas.groupby("ano").valor.sum() / 1e3).round(0).to_dict())
print(f"YTD jan-out 2026: R$ {r26/1e3:,.0f} mil | jan-out 2025: R$ {r25/1e3:,.0f} mil | var: {r26/r25-1:+.1%}")

fechadas["ano_ab"] = fechadas.data_abertura.dt.year
win = (fechadas.assign(ganha=fechadas.status == "Ganha")
       .groupby("origem").agg(fechadas=("ganha", "size"), win_rate=("ganha", "mean"),
                              ticket=("valor", "median")))
win["win_rate"] = (win.win_rate * 100).round(1)
print("\nTaxa de ganho por canal (oportunidades fechadas):\n", win.sort_values("win_rate", ascending=False))

mix = (opps.assign(ano=opps.data_abertura.dt.year).groupby(["ano", "origem"]).size()
       .unstack(fill_value=0))
print("\nParticipação do Outbound nas aberturas: ",
      (mix["Outbound"] / mix.sum(axis=1) * 100).round(1).to_dict())
wr_ano = (fechadas.assign(g=fechadas.status == "Ganha").groupby("ano_ab").g.mean() * 100).round(1)
print("Taxa de ganho geral por ano de abertura:", wr_ano.to_dict())

# qui-quadrado: a taxa de ganho do Outbound é diferente dos demais canais?
tab = pd.crosstab(fechadas.origem == "Outbound", fechadas.status == "Ganha")
chi2, p_chi, *_ = stats.chi2_contingency(tab)
print(f"Qui-quadrado taxa de ganho Outbound vs demais: p = {p_chi:.2e}")

# ROI de campanha por canal = receita ganha atribuída / investimento
rec_camp = ganhas.dropna(subset=["campanha_id"]).groupby("campanha_id").valor.sum()
roi = (inv.groupby("campanha_id").valor_investido.sum().to_frame("investido")
       .join(rec_camp.rename("receita")).fillna(0).join(camp.set_index("id_externo")[["canal"]])
       .groupby("canal").sum())
roi["roi_x"] = (roi.receita / roi.investido).round(1)
print("\nRetorno por canal de campanha (receita ganha / investimento):\n", roi)

# concentração
rc = ganhas.groupby("conta_id").valor.sum().sort_values(ascending=False)
print(f"\nMaior cliente = {rc.iloc[0]/rc.sum():.1%} da receita; top 10 = {rc.iloc[:10].sum()/rc.sum():.1%}")

# pipeline aberto e parado (> 30 dias sem mudar de etapa)
ab = opps[opps.status == "Aberta"].copy()
ab["dias_parada"] = (REF - ab.data_ultima_mudanca_etapa).dt.days
parada = ab[ab.dias_parada > 30]
venc = ab[ab.data_fechamento < REF]
print(f"\nPipeline aberto: {len(ab)} opps, R$ {ab.valor.sum()/1e3:,.0f} mil")
print(f"Parado > 30 dias: {len(parada)} opps, R$ {parada.valor.sum()/1e3:,.0f} mil")
print(f"Com data prevista de fechamento vencida: {len(venc)} opps, R$ {venc.valor.sum()/1e3:,.0f} mil")

# %% [markdown]
# ## 4. Estimativa de impacto da recomendação
# Cenário: um programa de indicação para a carteira atual (foco nos clientes classe A) faz
# **25% das oportunidades que hoje entrariam por Outbound** entrarem por Indicação.
# Premissas: volume anual de 2026 anualizado, taxas de ganho e ticket médio históricos por canal.

# %%
ab26 = opps[opps.data_abertura.dt.year == 2026]
meses = ab26.data_abertura.dt.month.max()
vol_out_ano = (ab26.origem == "Outbound").sum() / meses * 12
tk = ganhas.groupby("origem").valor.mean()
wr = fechadas.assign(g=fechadas.status == "Ganha").groupby("origem").g.mean()
migra = 0.25 * vol_out_ano
ganho_extra = migra * (wr["Indicação"] * tk["Indicação"] - wr["Outbound"] * tk["Outbound"])
print(f"Outbound/ano (2026 anualizado): {vol_out_ano:.0f} opps | migração de 25%: {migra:.0f} opps")
print(f"Ticket médio ganho: Indicação R$ {tk['Indicação']:,.0f} | Outbound R$ {tk['Outbound']:,.0f}")
print(f"Receita esperada por opp: Indicação R$ {wr['Indicação']*tk['Indicação']:,.0f} | "
      f"Outbound R$ {wr['Outbound']*tk['Outbound']:,.0f}")
print(f"Impacto anual estimado: + R$ {ganho_extra/1e3:,.0f} mil "
      f"({ganho_extra/ganhas[ganhas.ano==2025].valor.sum():.1%} da receita de 2025), "
      f"com ciclo ~{np.median(out)-np.median(ind):.0f} dias mais curto nesses negócios")
