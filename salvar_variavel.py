import os
import json

# Carregar o valor da variável de ambiente
sessaoclosedopen = int(os.getenv("sessaoclosedopen"))  # Lê o valor do ambiente

# Salvar no arquivo JSON
with open('sessaoclosedopen.json', 'w') as file:
    json.dump({'sessaoclosedopen': sessaoclosedopen}, file)

print(f"Valor de sessaoclosedopen salvo: {sessaoclosedopen}")
