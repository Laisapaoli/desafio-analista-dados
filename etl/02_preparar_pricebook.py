"""
Prepara o arquivo de precos (PricebookEntry) para o Data Loader.

Le o arquivo "success" gerado pelo Data Loader na carga dos Produtos
(pasta resultados_carga) e cria dados/salesforce/3b_PricebookEntry.csv
com as colunas: Pricebook2Id, Product2Id, UnitPrice, IsActive.

Uso (no terminal, dentro da pasta desafio):
    python etl/02_preparar_pricebook.py 01sXXXXXXXXXXXXXXX
"""
import csv
import glob
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_RESULTADOS = os.path.join(RAIZ, "resultados_carga")
SAIDA = os.path.join(RAIZ, "dados", "salesforce", "3b_PricebookEntry.csv")

if len(sys.argv) < 2 or not sys.argv[1].startswith("01s"):
    sys.exit("Informe o Id do Standard Price Book (comeca com 01s).\n"
             "Exemplo: python etl/02_preparar_pricebook.py 01sXXXXXXXXXXXXXXX")
pricebook_id = sys.argv[1].strip()

# pega o arquivo success mais recente que tenha ProductCode (carga de produtos)
candidatos = sorted(glob.glob(os.path.join(PASTA_RESULTADOS, "success*.csv")),
                    key=os.path.getmtime, reverse=True)
arquivo = None
for c in candidatos:
    with open(c, encoding="utf-8-sig") as f:
        cabecalho = f.readline().upper()
    if "PRODUCTCODE" in cabecalho and "UNITPRICE" in cabecalho:
        arquivo = c
        break
if arquivo is None:
    sys.exit(f"Nao achei o arquivo success dos produtos em {PASTA_RESULTADOS}")

with open(arquivo, encoding="utf-8-sig", newline="") as f:
    linhas = list(csv.DictReader(f))

# nomes de coluna sem diferenciar maiusculas/minusculas
def col(linha, nome):
    for k, v in linha.items():
        if k and k.strip().upper() == nome.upper():
            return v
    return ""

with open(SAIDA, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Pricebook2Id", "Product2Id", "UnitPrice", "IsActive"])
    for l in linhas:
        w.writerow([pricebook_id, col(l, "ID"), col(l, "UnitPrice"), "true"])

print(f"Lido: {os.path.basename(arquivo)}")
print(f"{len(linhas)} produtos -> {SAIDA}")
