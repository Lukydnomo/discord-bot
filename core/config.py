import logging
import os

import requests

commandPrefix = "foa!"
DISCORDTOKEN = os.getenv("DISCORD_BOT_TOKEN")
GITHUBTOKEN = os.getenv("DATABASE_TOKEN")
luky = 767015394648915978
logChannel = 1317580138262695967
usuarios_autorizados = [luky]
github_repo = "Lukydnomo/discord-bot"
json_file_path = "database.json"
NOME_ORIGINAL = "FranBOT"
CAMINHO_AVATAR_ORIGINAL = "assets/images/FranBOT-Logo.png"
MAX_DICE_GROUP = 100
MAX_FACES = 10000
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
