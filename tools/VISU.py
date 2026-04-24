# Flake8: noqa
import json
import os

# Caminho para o arquivo JSON
json_path = r'result_json\result.json'


def process_json(json_path):
    # Verifica se o arquivo existe
    if not os.path.isfile(json_path):
        print(f"O arquivo {json_path} não foi encontrado.")
        return

    # Lê o conteúdo do arquivo JSON
    with open(json_path, 'r') as file:
        data = json.load(file)

    num_values = []
    # Itera sobre os valores no JSON
    for key, value in data.items():
        try:
            # Tenta converter o valor para float (para tratar números inteiros e decimais)
            numeric_value = float(value["Valor"])
            num_values.append(numeric_value)
        except (ValueError, TypeError):
            # Se o valor não pode ser convertido para float, ignora
            continue

    # Contar o número de valores numéricos
    count = len(num_values)

    # Encontrar o maior valor numérico
    max_value = max(num_values) if num_values else None

    # Imprimir os resultados
    print(f"Total de valores numéricos: {count}")
    print(f"Maior valor numérico: {max_value}")
    input("Pressione Enter para sair.")


# Chama a função para processar o arquivo JSON
process_json(json_path)
