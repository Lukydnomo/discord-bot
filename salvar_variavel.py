import os
import json

# Lê o valor da variável de ambiente
sessaoclosedopen = os.getenv("sessaoclosedopen")

if sessaoclosedopen is None or sessaoclosedopen == '':
    print("Erro: sessaoclosedopen não foi definido corretamente!")
    exit(1)

try:
    sessaoclosedopen = int(sessaoclosedopen)  # Converte para inteiro
except ValueError:
    print(f"Erro: não foi possível converter o valor '{sessaoclosedopen}' para inteiro.")
    exit(1)

# Salva no arquivo JSON
with open('sessaoclosedopen.json', 'w') as file:
    json.dump({'sessaoclosedopen': sessaoclosedopen}, file)

print(f"Valor de sessaoclosedopen salvo: {sessaoclosedopen}")
