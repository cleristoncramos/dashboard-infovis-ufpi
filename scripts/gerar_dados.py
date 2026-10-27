"""Gera a base simulada data/vendas.csv (24 meses × 27 UFs × 5 áreas).

Uso:  python scripts/gerar_dados.py
"""

from pathlib import Path

import pandas as pd
import numpy as np

np.random.seed(42)

# Todos os 26 estados + DF
estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", 
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", 
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

categorias = [
    "Tecnologia",
    "Saúde",
    "Educação",
    "Infraestrutura",
    "Segurança"
]

datas = pd.date_range(start="2024-01-01", end="2025-12-01", freq="MS")

registros = []

for data in datas:
    for estado in estados:
        for categoria in categorias:
            base = np.random.randint(50, 500)
            fator_estado = np.random.uniform(0.6, 1.6)
            fator_categoria = np.random.uniform(0.7, 1.5)

            registros.append({
                "data": data,
                "ano": data.year,
                "mes": data.strftime("%Y-%m"),
                "estado": estado,
                "categoria": categoria,
                "atendimentos": int(base * fator_estado * fator_categoria),
                "valor": round(float(base * fator_estado * fator_categoria * np.random.uniform(80, 220)), 2)
            })

df = pd.DataFrame(registros)
df.to_csv(Path(__file__).resolve().parent.parent / "data" / "vendas.csv", index=False)

print(df.head())
print("Arquivo gerado: data/vendas.csv")