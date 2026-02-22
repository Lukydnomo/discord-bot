import logging
import os

import requests

def _env_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if not v or not v.strip():
        return default
    try:
        return int(v.strip())
    except ValueError:
        return default


def _env_int_list(name: str, default: list[int]) -> list[int]:
    v = os.getenv(name)
    if not v or not v.strip():
        return default
    parts = v.replace(";", ",").split(",")
    out: list[int] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            out.append(int(p))
        except ValueError:
            pass
    return out or default


# Prefixo de comandos (se tu ainda usa prefix command)
commandPrefix = _env_str("COMMAND_PREFIX", "foa!")

# Tokens
DISCORDTOKEN = os.getenv("DISCORD_BOT_TOKEN")
GITHUBTOKEN = os.getenv("DATABASE_TOKEN")

# IDs (com fallback pros teus atuais)
luky = _env_int("OWNER_ID", 767015394648915978)
logChannel = _env_int("LOG_CHANNEL_ID", 1317580138262695967)

# Lista de autorizados (ex: "123,456,789")
usuarios_autorizados = _env_int_list("AUTHORIZED_USER_IDS", [luky])

# DB no GitHub
github_repo = _env_str("GITHUB_REPO", "Lukydnomo/discord-bot")
json_file_path = _env_str("DB_JSON_PATH", "database.json")

# Identidade
NOME_ORIGINAL = _env_str("BOT_ORIGINAL_NAME", "FranBOT")
CAMINHO_AVATAR_ORIGINAL = _env_str("BOT_ORIGINAL_AVATAR", "assets/images/FranBOT-Logo.png")

# Limites
MAX_DICE_GROUP = _env_int("MAX_DICE_GROUP", 100)
MAX_FACES = _env_int("MAX_FACES", 10000)

logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

def cancel_previous_github_runs():
    """
    Cancela execuções anteriores no GitHub Actions, exceto a execução atual.
    """
    run_id = os.getenv("RUN_ID")
    token = os.getenv("GITHUB_TOKEN")

    if not run_id or not token:
        logger.warning(
            "⚠️ Faltando RUN_ID ou GITHUB_TOKEN — pulando cancelamento de runs antigas."
        )
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    # Lista as execuções em andamento
    list_url = f"https://api.github.com/repos/{github_repo}/actions/runs?status=in_progress&per_page=100"
    try:
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"❌ Erro ao listar runs: {e}")
        return

    runs = response.json().get("workflow_runs", [])
    if not runs:
        logger.info("✅ Nenhuma execução em andamento encontrada.")
        return

    # Cancela execuções anteriores
    for run in runs:
        rid = run.get("id")
        if str(rid) != run_id:
            cancel_url = (
                f"https://api.github.com/repos/{github_repo}/actions/runs/{rid}/cancel"
            )
            try:
                cancel_resp = requests.post(cancel_url, headers=headers)
                if cancel_resp.status_code == 202:
                    logger.info(f"✅ Run antiga cancelada: {rid}")
                else:
                    logger.warning(
                        f"⚠️ Falha ao cancelar run {rid}: {cancel_resp.status_code}"
                    )
            except requests.RequestException as e:
                logger.error(f"❌ Erro ao cancelar run {rid}: {e}")
