import sys
import json

# Carregar o valor passado pelo argumento
sessaoclosedopen = int(sys.argv[1])  # O valor que o bot passa

# Salvar no arquivo JSON
with open('sessaoclosedopen.json', 'w') as file:
    json.dump({'sessaoclosedopen': sessaoclosedopen}, file)

print(f"Valor de sessaoclosedopen salvo: {sessaoclosedopen}")
