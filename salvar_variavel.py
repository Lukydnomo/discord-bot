import json
import sys

def salvar_variavel(valor):
    with open("sessaoclosedopen.json", "w") as file:
        json.dump({"sessaoclosedopen": valor}, file)

if __name__ == "__main__":
    # Captura o valor da variável a partir do argumento do comando
    if len(sys.argv) > 1:
        try:
            valor = int(sys.argv[1])
            salvar_variavel(valor)
            print(f"Variável sessaoclosedopen salva com valor: {valor}")
        except ValueError:
            print("Erro: O valor fornecido não é um número válido.")
    else:
        print("Erro: Nenhum valor fornecido para salvar a variável.")
