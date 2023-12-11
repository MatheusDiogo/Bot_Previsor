import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import zscore

# URL da planilha Google Sheets
google_sheets_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRdR3hcg5AsZ3tKUf6lm0JrM6ReupK-I0SYi_iwi7YwP1s_TOZ5eYRTgmkV7tk5sE8yTNtCN7R_1aKV/pub?gid=1830936369&single=true&output=csv"

# Carregar os dados usando pandas
data = pd.read_csv(google_sheets_url)

# Converte a coluna 'date' para datetime
data['date'] = pd.to_datetime(data['date'], format='%Y-%m-%d %H:%M:%S')

# Converte a coluna 'price' para float
data['price'] = data['price'].str.replace('.', '').str.replace(',', '.').astype(float)

# Converte a coluna 'normalized price' para float
data['normalized price'] = data['normalized price'].str.replace('.', '').str.replace(',', '.').astype(float)

# Agrupa os dados por SKU
grouped_data = data.groupby('prodId')

# Calcula o Z-Score para cada grupo
def remove_outliers(group):
    z_scores = zscore(group['normalized price'])
    abs_z_scores = abs(z_scores)
    outliers = (abs_z_scores < 3)
    return group.loc[outliers]  # Use ~outliers para manter os não-outliers

# Remove outliers de cada grupo
data_no_outliers = grouped_data.apply(remove_outliers).reset_index(drop=True)

# Plota o gráfico de linha sem outliers
plt.figure(figsize=(10, 6))
plt.xlabel('Data')
plt.ylabel('Preço Normalizado (0-100)')
plt.title('Preços Normalizados por SKU (Sem Outliers)')

for sku, group in data_no_outliers.groupby('prodId'):
    plt.plot(group['date'], group['normalized price'].interpolate(), label=sku)

plt.legend()
plt.show()