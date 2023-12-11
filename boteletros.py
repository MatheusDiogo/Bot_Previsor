import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1pJ-WmcxwLLJ1ylURvWMrKZNmA2VQFyr6Q2UQXQEKicA"

def update_data_history(service, data_history):
    sheet = service.spreadsheets()
    
    data_history = data_history.fillna('')

    # Obtém os valores atuais da página "Data History"
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range='Data History').execute()
    values = result.get("values", [])

    if not values:
        data_history_sheet = pd.DataFrame(data_history, columns=['prodId', 'date', 'price'])
    else:
        # Cria um DataFrame pandas dos valores existentes
        data_history_sheet = pd.DataFrame(values[1:], columns=values[0])

        # Adiciona os dados do SKU atual ao DataFrame
        new_row = pd.DataFrame(data_history[['prodId', 'date', 'price']], columns=['prodId', 'date', 'price'])
        
        data_history_sheet = pd.concat([data_history_sheet, new_row], ignore_index=True)

    data_history_sheet['prodId'] = data_history_sheet['prodId'].astype(str)
    data_history_sheet['date'] = pd.to_datetime(data_history_sheet['date'])
    data_history_sheet['date'] = data_history_sheet['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    data_history_sheet.drop_duplicates(subset=['prodId', 'date'], keep='last', inplace=True)

    # Atualiza a página "Data History" na planilha
    body = {'values': [data_history_sheet.columns.tolist()] + data_history_sheet.values.tolist()}
    
    result = sheet.values().update(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range='Data History',
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

def request_zoom_api(product_id):
    api_url = 'https://api-v1.zoom.com.br/restql/run-query/sherlock/product_price_history/1'

    query_params = {
        'tenant': 'DEFAULT',
        'product_id': product_id,
        'period': 'months',
        'amount': '12',
    }

    try:
        response = requests.get(api_url, params=query_params)

        if response.status_code == 200:
            print('Requisição feita!')
            price_data = response.json()['product_price_history']['result']

            # Criar um DataFrame do pandas para facilitar a manipulação
            df = pd.DataFrame(price_data)

            # Extrair as datas e os preços
            df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
            
            return df
        
    except requests.RequestException as e:
        print(f'Erro na requisição: {e}')
        exit()

def get_product_price_zoom(url):
    user_agent = {'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 OPR/104.0.0.0'}

    if url.lower() == 'não encontrado':
        return "URL não encontrada"
    
    # Enviar uma solicitação GET para a página da web
    response = requests.get(url, headers=user_agent)

    # Verificar se a solicitação foi bem-sucedida (código de status 200)
    if response.status_code == 200:
        # Parsear o conteúdo HTML da página
        soup = BeautifulSoup(response.content, 'html.parser')

        # Encontrar a primeira ocorrência da classe 'Text_Text_h_AF6 Text_DesktopHeadingM_C_e4f'
        price_element = soup.find(class_='Text_Text__h_AF6 Text_DesktopHeadingM__C_e4f')
        loja_element = soup.find(class_='Text_Text__h_AF6 Text_MobileLabelS___fuke Price_Merchant__EUdHA')
        
        # Extrair o texto do elemento encontrado
        price = price_element.text.strip() if price_element else "Preço não encontrado"
        loja = loja_element.text.strip() if loja_element else "Loja não encontrada"
        
        # Encontre o elemento div com data-testid="save-product"
        save_product_div = soup.find('div', {'data-testid': 'save-product'})
        
        # Extraia o número do SKU do atributo id
        if save_product_div:
            sku_id = save_product_div.get('id')
            # Remova o prefixo "save-product-" para obter apenas o número do SKU
            sku_number = sku_id.replace('save-product-', '')
        else:
            sku_number = "SKU não encontrado"

        return price, loja, sku_number
    else:
        return "Erro ao obter a página"

def main():
    try:
        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "Credenciais.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        service = build("sheets", "v4", credentials=creds)
        
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range='A:I')
            .execute()
        )

        values = result.get("values", [])
        
        dados = pd.DataFrame(values[1:], columns=values[0])

        # Iterar sobre as linhas da planilha
        for index, row in dados.iterrows():
            zoom_url = row['Zoom']
            
            if zoom_url:
                preco_str, loja_menor_preco, sku = get_product_price_zoom(zoom_url)

                if preco_str and preco_str not in ['URL não encontrada', 'Preço não encontrado']:
                    # Remover pontos de milhar e extrair o valor numérico da string de preço
                    menor_preco = float(preco_str.replace('R$ ', '').replace('.','').replace(',','.'))
                else:
                    continue

                data_history = request_zoom_api(sku)
                update_data_history(service, data_history)

            # Atualizar 'Menor Preço' e 'Loja' na planilha
            if menor_preco:
                loja = loja_menor_preco.split()[-1]
                media_preco = data_history['price'].tail(90).mean()
                mediana_preco = data_history['price'].tail(90).median()
                minimo_preco = data_history['price'].tail(90).min()

                if menor_preco < media_preco:
                    alerta = 'Preço Baixo!'
                elif media_preco < menor_preco < mediana_preco:
                    alerta = 'Preço Bom!'
                elif menor_preco == minimo_preco:
                    alerta = 'Menor em 90 dias!'
                else:
                    alerta = 'Preço Alto!'

                print(menor_preco, loja, alerta, media_preco, mediana_preco)

                result = (
                    sheet.values()
                    .update(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                            range=f'C{index + 2}:G{index + 2}',
                            valueInputOption="USER_ENTERED",
                            body={'values': [[menor_preco, loja, alerta, media_preco, mediana_preco]]})
                    .execute()
                )
            else:
                continue
        
    except Exception as erro:
        print(erro)

if __name__ == '__main__':
    main()