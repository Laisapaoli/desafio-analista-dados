"""
Prepara o arquivo de itens de oportunidade (OpportunityLineItem) para o Data Loader.

O Salesforce exige o Id da entrada de preco (PricebookEntryId) em cada item.
Este script cruza os arquivos "success" das cargas de Produtos e de Precos
(pasta resultados_carga) para descobrir o PricebookEntryId de cada ProductCode
e gera dados/salesforce/7b_OpportunityLineItem.csv.

Uso (no terminal, dentro da pasta do projeto):
    python etl/03_preparar_itens.py
"""
import csv
import glob
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_RESULTADOS = os.path.join(RAIZ, "resultados_carga")
ENTRADA = os.path.join(RAIZ, "dados", "salesforce", "7_OpportunityLineItem.csv")
SAIDA = os.path.join(RAIZ, "dados", "salesforce", "7b_OpportunityLineItem.csv")


def ler(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    # padroniza nomes de coluna em maiusculas
    return [{(k or "").strip().upper(): v for k, v in l.items()} for l in linhas]


def achar_success(colunas_obrigatorias):
    arquivos = sorted(glob.glob(os.path.join(PASTA_RESULTADOS, "success*.csv")),
                      key=os.path.getmtime, reverse=True)
    for a in arquivos:
        with open(a, encoding="utf-8-sig") as f:
            cab = f.readline().upper()
        if all(c in cab for c in colunas_obrigatorias):
            return a
    sys.exit(f"Nao achei success com {colunas_obrigatorias} em {PASTA_RESULTADOS}")


arq_produtos = achar_success(["PRODUCTCODE", "FAMILY"])
arq_precos = achar_success(["PRICEBOOK2ID", "PRODUCT2ID"])

# ProductCode -> Product2Id
codigo_para_produto = {l["PRODUCTCODE"]: l["ID"] for l in ler(arq_produtos)}
# Product2Id -> PricebookEntryId
produto_para_entrada = {l["PRODUCT2ID"]: l["ID"] for l in ler(arq_precos)}

with open(ENTRADA, encoding="utf-8-sig", newline="") as f:
    itens = list(csv.DictReader(f))

sem_preco = 0
with open(SAIDA, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Id_Externo__c", "Opportunity:Id_Externo__c",
                "PricebookEntryId", "Quantity", "UnitPrice"])
    for it in itens:
        entrada = produto_para_entrada.get(codigo_para_produto.get(it["ProductCode"], ""), "")
        if not entrada:
            sem_preco += 1
            continue
        w.writerow([it["Id_Externo__c"], it["Opportunity:Id_Externo__c"],
                    entrada, it["Quantity"], it["UnitPrice"]])

print(f"Produtos: {os.path.basename(arq_produtos)}")
print(f"Precos:   {os.path.basename(arq_precos)}")
print(f"{len(itens) - sem_preco} itens -> {SAIDA}")
if sem_preco:
    print(f"ATENCAO: {sem_preco} itens sem preco cadastrado foram ignorados")
