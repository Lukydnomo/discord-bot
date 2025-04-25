import asyncio
import json
import random
import re
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone

import discord
import requests

from core.config import *

# Database System
_cached_data = None  # Cache em memória
_cached_sha = None  # SHA do arquivo no GitHub


async def safe_request(coroutine_func, *args, max_retries=3, **kwargs):
    """
    Executa uma coroutine com tentativas seguras em caso de falhas.

    Args:
        coroutine_func: A coroutine a ser executada.
        *args: Argumentos posicionais para a coroutine.
        max_retries: Número máximo de tentativas (padrão: 3).
        **kwargs: Argumentos nomeados para a coroutine.

    Returns:
        O resultado da coroutine, se bem-sucedido.

    Raises:
        Exception: Repassa a exceção após exceder o número de tentativas.
    """
    for tentativa in range(1, max_retries + 1):
        try:
            return await coroutine_func(*args, **kwargs)
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limit
                retry_after = getattr(e, "retry_after", 10)
                logger.warning(
                    f"[Rate Limit] Tentativa {tentativa}/{max_retries}: Esperando {retry_after:.1f}s..."
                )
                await asyncio.sleep(retry_after)
            else:
                logger.error(
                    f"[HTTPException] Tentativa {tentativa}/{max_retries}: {e}"
                )
                raise
        except Exception as e:
            logger.error(f"[Erro] Tentativa {tentativa}/{max_retries}: {e}")
            if tentativa < max_retries:
                await asyncio.sleep(5)
            else:
                raise

def get_file_content():
    global _cached_data, _cached_sha
    if _cached_data is None:
        url = f"https://api.github.com/repos/{github_repo}/contents/{json_file_path}"
        headers = {"Authorization": f"token {GITHUBTOKEN}"}
        response = requests.get(url, headers=headers).json()

        if "content" in response:
            try:
                _cached_data = json.loads(b64decode(response["content"]).decode())
                _cached_sha = response.get(
                    "sha"
                )  # Armazena o SHA para atualizações futuras
            except json.JSONDecodeError:
                _cached_data = {}
                _cached_sha = None
        else:
            print(f"❌ Erro ao obter conteúdo do arquivo: {response}")
            _cached_data = {}
            _cached_sha = None

    return _cached_data

def update_file_content(data):
    global _cached_data, _cached_sha
    if data == _cached_data:
        print("🔄 Nenhuma alteração detectada, não será feita atualização.")
        return  # Evita atualização desnecessária

    url = f"https://api.github.com/repos/{github_repo}/contents/{json_file_path}"
    headers = {"Authorization": f"token {GITHUBTOKEN}"}
    new_content = b64encode(json.dumps(data, indent=4).encode()).decode()
    commit_message = "Atualizando banco de dados"
    payload = {
        "message": commit_message,
        "content": new_content,
        "sha": _cached_sha,  # Inclui o SHA para evitar conflitos
    }

    response = requests.put(url, headers=headers, json=payload)
    if response.status_code == 200 or response.status_code == 201:
        print("✅ Banco de dados atualizado com sucesso!")
        _cached_data = data  # Atualiza o cache local
        _cached_sha = response.json().get("content", {}).get("sha")  # Atualiza o SHA
    else:
        print(
            f"❌ Erro ao atualizar o banco de dados: {response.status_code} {response.text}"
        )

async def save(name, value):
    data = get_file_content()
    if name in data:
        if isinstance(data[name], list):
            data[name].append(value)
        else:
            data[name] = [data[name], value]
    else:
        data[name] = value
    update_file_content(data)

def load(name):
    data = get_file_content()
    return data.get(name, None)

# Utilitários
def carregar_missoes():
    with open("assets/resources/missoes.txt", "r", encoding="utf-8") as f:
        return [linha.strip() for linha in f.readlines()]
missoes = carregar_missoes()

def carregar_dicionario():
    with open("assets/resources/palavras.txt", "r", encoding="utf-8") as f:
        return [linha.strip() for linha in f.readlines()]
dicionario = carregar_dicionario()

def obter_palavra_do_dia():
    data_atual = datetime.now(timezone.utc).strftime("%m/%d/%y")
    data = get_file_content()

    # Verifica se a palavra do dia já foi definida para a data atual
    if "palavra_do_dia" in data and data["palavra_do_dia"].get("dia") == data_atual:
        return data["palavra_do_dia"]["palavra"]

    # Escolhe uma nova palavra e atualiza apenas a entrada correspondente
    nova_palavra = random.choice(dicionario)
    if "palavra_do_dia" not in data:
        data["palavra_do_dia"] = {}
    data["palavra_do_dia"]["palavra"] = nova_palavra
    data["palavra_do_dia"]["dia"] = data_atual

    # Atualiza o banco de dados
    update_file_content(data)
    return nova_palavra
palavra_do_dia = obter_palavra_do_dia()

def carregar_piada():
    with open("assets/resources/piadas.txt", "r", encoding="utf-8") as f:
        return [linha.strip() for linha in f.readlines()]
piadas = carregar_piada()

def carregar_sarcasmResponses():
    with open("assets/resources/sarcasmResponses.txt", "r", encoding="utf-8") as f:
        return [linha.strip() for linha in f.readlines()]
SARCASM_RESPONSES = carregar_sarcasmResponses()

def is_spam(text):
    # Remove espaços e ignora letras maiúsculas/minúsculas
    normalized = text.replace(" ", "").lower()

    # Se for só um caractere repetido várias vezes, é spam
    if len(set(normalized)) == 1:
        return True

    # Se for só um pequeno grupo de caracteres repetindo várias vezes (ex: "lolololol", "haha haha")
    match = re.fullmatch(r"(.+?)\1+", normalized)
    if match:
        return True

    return False

def rolar_dado(expressao, detalhado=True):
    if not detalhado:
        detalhes = []

        def substituir(match):
            qtd_str, faces_str = match.groups()
            qtd = int(qtd_str) if qtd_str else 1
            faces = int(faces_str)

            # ─── validação de limites ───
            if qtd > MAX_DICE_GROUP or faces > MAX_FACES:
                raise ValueError(
                    f"Máximo permitido: {MAX_DICE_GROUP} dados de até d{MAX_FACES}"
                )
            # ─────────────────────────────

            rolagens = [random.randint(1, faces) for _ in range(qtd)]
            detalhes.append(sorted(rolagens, reverse=True))
            return str(sum(rolagens))

        expr_mod = re.sub(r"(\d*)d(\d+)", substituir, expressao)
        try:
            resultado = eval(expr_mod)
        except:
            return None

        return {
            "resultado": resultado,
            "resultadoWOutEval": expr_mod,
            "detalhado": False,
        }

    else:
        detalhes = []

        def substituir(match):
            qtd_str, faces_str = match.groups()
            qtd = int(qtd_str) if qtd_str else 1
            faces = int(faces_str)

            # ─── validação de limites ───
            if qtd > MAX_DICE_GROUP or faces > MAX_FACES:
                raise ValueError(
                    f"Máximo permitido: {MAX_DICE_GROUP} dados de até d{MAX_FACES}"
                )
            # ─────────────────────────────

            rolagens = [random.randint(1, faces) for _ in range(qtd)]
            detalhes.append(sorted(rolagens, reverse=True))
            return str(sum(rolagens))

        expr_mod = re.sub(r"(\d*)d(\d+)", substituir, expressao)
        try:
            resultado = eval(expr_mod)
        except:
            return None

        # montagem do breakdown
        if len(detalhes) == 1:
            breakdown = str(detalhes[0])
            m = re.search(r"(\d*d\d+)", expressao)
            dice_group = m.group(1) if m else expressao
        else:
            breakdown = " + ".join(str(lst) for lst in detalhes)
            dice_group = expressao

        return {
            "resultado": resultado,
            "resultadoWOutEval": breakdown,
            "dice_group": dice_group,
            "detalhado": True,
        }

def determinar_vencedor(jogada1, jogada2):
    if jogada1 == jogada2:
        return "🤝 **Empate!**"
    elif (
        (jogada1 == "Pedra" and jogada2 == "Tesoura")
        or (jogada1 == "Papel" and jogada2 == "Pedra")
        or (jogada1 == "Tesoura" and jogada2 == "Papel")
    ):
        return "🎉 **O primeiro jogador venceu!**"
    else:
        return "🎉 **O segundo jogador venceu!**"

def calcular_compatibilidade(nome1inp, nome2inp):
    # 1. Juntar os nomes e remover espaços
    combinado = (nome1inp + nome2inp).replace(" ", "").lower()

    # 2. Contar as letras na ordem de aparição (sem repetir letra na contagem)
    contagem = []
    letras_vistas = []
    for letra in combinado:
        if letra not in letras_vistas:
            letras_vistas.append(letra)
            contagem.append(combinado.count(letra))

    # 3. Função para fazer as somas dos extremos e gerar nova sequência
    def reduzir(sequencia):
        while len(sequencia) > 2:
            nova_seq = []
            i, j = 0, len(sequencia) - 1
            while i < j:
                soma = sequencia[i] + sequencia[j]
                nova_seq.append(soma)
                i += 1
                j -= 1
            if i == j:
                nova_seq.append(sequencia[i])
            # Concatenar todos os números como string e quebrar em dígitos novamente
            sequencia = [int(d) for d in "".join(str(num) for num in nova_seq)]
        return int("".join(str(d) for d in sequencia))

    # 4. Calcular e retornar o resultado final
    resultado = reduzir(contagem)
    return f"{resultado}% de compatibilidade"

async def castigar_automatico(member: discord.Member, tempo: int):
    """
    Temporarily mutes a Discord member for a specified duration.

    Args:
        member (discord.Member): The member to be muted.
        tempo (int): Duration of the mute in seconds.
    """
    try:
        duration = timedelta(seconds=tempo)
        until_time = datetime.now(timezone.utc) + duration
        await member.timeout(until_time, reason="puta")
    except discord.DiscordException as e:
        print(f"Erro ao castigar {member.mention}: {e}")
