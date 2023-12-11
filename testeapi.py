import requests
import pandas as pd
import json

def request_zoom_api():
    api_url = 'https://api-v1.zoom.com.br/restql/run-query/sherlock/zoom_expert_reviews/1?tenant=DEFAULT'

    try:
        response = requests.get(api_url)

        if response.status_code == 200:
            print('Requisição feita!')
            data = response.json()

            with open('Resultado_api.txt', 'w') as arquivo_txt:
                json.dump(data, arquivo_txt, indent=2)
                
            print('Resultado salvo em Resultado_api.txt')
        
    except requests.RequestException as e:
        print(f'Erro na requisição: {e}')
        exit()

if __name__ == '__main__':
    request_zoom_api()