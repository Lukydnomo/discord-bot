import os
import json

# Lê o valor da variável de ambiente
sessaoclosedopen = int(os.getenv("sessaoclosedopen"))

# Salva no arquivo JSON
with open('sessaoclosedopen.json', 'w') as file:
    json.dump({'sessaoclosedopen': sessaoclosedopen}, file)

print(f"Valor de sessaoclosedopen salvo: {sessaoclosedopen}")
