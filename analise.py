import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import zscore
from prophet import Prophet
import holidays

# URL da planilha Google Sheets
google_sheets_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRdR3hcg5AsZ3tKUf6lm0JrM6ReupK-I0SYi_iwi7YwP1s_TOZ5eYRTgmkV7tk5sE8yTNtCN7R_1aKV/pub?gid=1830936369&single=true&output=csv"

# Carregar os dados usando pandas
data = pd.read_csv(google_sheets_url)

# Converte a coluna 'date' para datetime
data['date'] = pd.to_datetime(data['date'], format='%Y-%m-%d %H:%M:%S')

# Converte a coluna 'price' para float
data['price'] = data['price'].str.replace('.', '').str.replace(',', '.').astype(float)

# Agrupa os dados por SKU
grouped_data = data.groupby('prodId')

# Calcula a média e o desvio padrão para cada grupo
mean_prices = grouped_data['price'].transform('mean')
std_prices = grouped_data['price'].transform('std')

# Normaliza os preços por SKU usando Z-Score
#data['normalized price'] = (data['price'] - mean_prices) / std_prices

# Calcula o Z-Score para cada grupo
def remove_outliers(group):
    z_scores = zscore(group['price'])
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
    plt.plot(group['date'], group['price'].interpolate(), label=sku)

plt.legend()
plt.show()

# Adicione feriados brasileiros ao modelo
feriados_brasil = holidays.Brazil()
feriados_df = pd.DataFrame(list(feriados_brasil.items()), columns=['ds', 'holiday'])

with open('previsoes.txt', 'w') as file:
    for sku, group in data_no_outliers.groupby('prodId'):
        prophet_data = group.rename(columns={'date': 'ds', 'price': 'y'})

        # Interpolação dos dados faltantes
        prophet_data['y'] = prophet_data['y'].interpolate()

        model = Prophet(mcmc_samples=300, holidays=feriados_df)

        # Ajusta o modelo aos dados
        model.fit(prophet_data)

        # Cria um DataFrame com datas futuras para fazer previsões
        future = model.make_future_dataframe(periods=20)  # 365 dias no futuro

        # Faz as previsões
        forecast = model.predict(future)

        # group_sku = group['prodId'].iloc[0]
        # forecast['yhat'] = forecast['yhat'] * std_prices[data['prodId'] == group_sku].iloc[0] + mean_prices[data['prodId'] == group_sku].iloc[0]
        
        # Plota as previsões sem normalização
        fig = model.plot(forecast, figsize=(10, 6))
        plt.xlabel('Data')
        plt.ylabel('Preço')
        plt.title('Previsões de Preço com Prophet para SKU {}'.format(sku))
        plt.show()

        # Escreve as previsões no arquivo de texto
        file.write(f"Previsões para SKU {sku}:\n")
        file.write(f"{forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(20)}\n\n")