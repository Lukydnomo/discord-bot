import sys
import json

# Verifica se o valor foi passado como argumento
if len(sys.argv) < 2:
    print("Erro: Nenhum valor fornecido para salvar a variável.")
    sys.exit(1)

# Carregar o valor passado pelo argumento
sessaoclosedopen = int(sys.argv[1])  # O valor que o bot passa

# Salvar no arquivo JSON
with open('sessaoclosedopen.json', 'w') as file:
    json.dump({'sessaoclosedopen': sessaoclosedopen}, file)

print(f"Valor de sessaoclosedopen salvo: {sessaoclosedopen}")
