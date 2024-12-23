import json
import sys

# Recebe o valor da variável como argumento (caso não seja passado, usa o valor padrão)
sessaoclosedopen = sys.argv[1] if len(sys.argv) > 1 else "indefinido"

# Salvar a variável no arquivo JSON
with open('sessaoclosedopen.json', 'w') as file:
    json.dump({'sessaoclosedopen': sessaoclosedopen}, file)
