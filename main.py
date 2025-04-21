# Core Python
import os
import io
import re
import json
import random
import asyncio
from datetime import datetime, timezone, timedelta
from base64 import b64decode, b64encode, urlsafe_b64decode, urlsafe_b64encode

# Discord
import discord
from discord import app_commands
from discord.ext import commands

# Terceiros
import requests
from PIL import Image, ImageEnhance, ImageDraw, ImageFont, ImageChops
from deep_translator import GoogleTranslator
import unidecode
import logging
import pyfiglet

# Instâncias iniciais
translate = GoogleTranslator

# Configuração do bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
from config import *

# Configuração do logger
logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

def cancel_previous_github_runs():
    """
    Cancela execuções anteriores no GitHub Actions, exceto a execução atual.
    """
    run_id = os.getenv("RUN_ID")
    token = os.getenv("GITHUB_TOKEN")

    if not run_id or not token:
        logger.warning("⚠️ Faltando RUN_ID ou GITHUB_TOKEN — pulando cancelamento de runs antigas.")
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
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
            cancel_url = f"https://api.github.com/repos/{github_repo}/actions/runs/{rid}/cancel"
            try:
                cancel_resp = requests.post(cancel_url, headers=headers)
                if cancel_resp.status_code == 202:
                    logger.info(f"✅ Run antiga cancelada: {rid}")
                else:
                    logger.warning(f"⚠️ Falha ao cancelar run {rid}: {cancel_resp.status_code}")
            except requests.RequestException as e:
                logger.error(f"❌ Erro ao cancelar run {rid}: {e}")

# chama antes de inicializar o bot
cancel_previous_github_runs()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commandPrefix, intents=intents)

    # Sincroniza comandos quando o bot inicia
    async def setup_hook(self):
        await self.tree.sync()  # Sincroniza comandos globalmente
        print("✅ Comandos sincronizados globalmente!")

bot = MyBot()

# Nome do arquivo Markdown
arquivo_md = "changelog.md"

# Abrir o arquivo em modo leitura
with open(arquivo_md, "r", encoding="utf-8") as arquivo:
    linhas = arquivo.readlines()

# Filtrar o conteúdo ignorando só as linhas com <!-- prettier-ignore -->
conteudo_filtrado = [
    linha for linha in linhas if "<!-- prettier-ignore -->" not in linha
]

# Junta tudo em uma única string
conteudo = "".join(conteudo_filtrado)

# Escolhe usuário aleatório
def randomuser():
    for guild in bot.guilds:  # Itera sobre os servidores onde o bot está
        members = [member for member in guild.members if not member.bot]  # Filtra membros não-bots
        
        if members:
            return random.choice(members)  # Retorna um membro aleatório
    
    return "No valid members found"  # Retorno caso não haja membros válidos

# Configuração do logger
logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

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
                logger.warning(f"[Rate Limit] Tentativa {tentativa}/{max_retries}: Esperando {retry_after:.1f}s...")
                await asyncio.sleep(retry_after)
            else:
                logger.error(f"[HTTPException] Tentativa {tentativa}/{max_retries}: {e}")
                raise
        except Exception as e:
            logger.error(f"[Erro] Tentativa {tentativa}/{max_retries}: {e}")
            if tentativa < max_retries:
                await asyncio.sleep(5)
            else:
                raise
# Database System
_cached_data = None  # Cache em memória
_cached_sha = None   # SHA do arquivo no GitHub

def get_file_content():
    global _cached_data, _cached_sha
    if _cached_data is None:
        url = f"https://api.github.com/repos/{github_repo}/contents/{json_file_path}"
        headers = {"Authorization": f"token {GITHUBTOKEN}"}
        response = requests.get(url, headers=headers).json()

        if "content" in response:
            try:
                _cached_data = json.loads(b64decode(response["content"]).decode())
                _cached_sha = response.get("sha")  # Armazena o SHA para atualizações futuras
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
        "sha": _cached_sha  # Inclui o SHA para evitar conflitos
    }

    response = requests.put(url, headers=headers, json=payload)
    if response.status_code == 200 or response.status_code == 201:
        print("✅ Banco de dados atualizado com sucesso!")
        _cached_data = data  # Atualiza o cache local
        _cached_sha = response.json().get("content", {}).get("sha")  # Atualiza o SHA
    else:
        print(f"❌ Erro ao atualizar o banco de dados: {response.status_code} {response.text}")

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

# Função para carregar o dicionário de palavras
def carregar_dicionario():
    with open("resources/palavras.txt", "r", encoding="utf-8") as f:
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

# Castigo
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
        print(f'Erro ao castigar {member.mention}: {e}')

# Evento de quando o bot estiver pronto
@bot.event
async def on_ready():
    get_file_content()

    await asyncio.sleep(3)

    print(f'Bot conectado como {bot.user}')
    for guild in bot.guilds:
        try:
            print(f"Sincronizando comandos para o servidor: {guild.name}")
            await bot.tree.sync(guild=guild)
            print(f"✅ Comandos sincronizados com sucesso para o servidor: {guild.name}")
        except Exception as e:
            print(f"❌ Falha ao sincronizar comandos no servidor {guild.name}: {e}")

    updatechannel = bot.get_channel(1319356880627171448)
    mention_message = "<@&1319355628195549247>"
    full_message = f"{conteudo}"
    message_chunks = [full_message[i:i+2000] for i in range(0, len(full_message), 2000)]

    # Pega todas as mensagens do canal, mais antigas primeiro
    existing_messages = []
    async for msg in updatechannel.history(oldest_first=True):
        existing_messages.append(msg)

    # Compara o conteúdo atual com as mensagens existentes
    is_same = len(existing_messages) == len(message_chunks) + 1 and all(
        existing_messages[i].content.strip() == message_chunks[i].strip()
        for i in range(len(message_chunks))
    ) and existing_messages[-1].content.strip() == mention_message.strip()

    if is_same:
        print("✅ Changelog já está no canal, nenhuma mensagem enviada.")
    else:
        await updatechannel.purge()
        for chunk in message_chunks:
            await updatechannel.send(chunk)
        await updatechannel.send(mention_message)
        print("✅ Changelog atualizado no canal.")


    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="Franciele tem robô agr? oloko",
        details="Tenso",
        large_image="punish",
        large_text="Moderando",
        small_image="punish",
        small_text="Feito por Luky",
    )
    await bot.change_presence(activity=activity)

# Respostas de on_message
REACTIONS = {
    "bem-vindo": ["👋", "🎉"],    # Reage com 👋 e 🎉 a mensagens contendo "bem-vindo"
    "importante": ["⚠️", "📢"],   # Reage com ⚠️ e 📢 a mensagens contendo "importante"
    "parabéns": ["🥳", "🎊"],      # Reage com 🥳 e 🎊 a mensagens contendo "parabéns"
    "obrigado": ["🙏"],           # Reage com 🙏 a mensagens contendo "obrigado"
}
def carregar_sarcasmResponses():
        with open("resources/sarcasmResponses.txt", "r", encoding="utf-8") as f:
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

# Evento on_message com suporte para rolagem via "$"
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignora mensagens de bots

    # Adiciona reações pré-definidas
    for keyword, emojis in REACTIONS.items():
        if keyword in message.content.lower():
            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except discord.Forbidden:
                    print(f"❌ Não tenho permissão para reagir a mensagens em {message.channel}")

    # Detecta expressões de rolagem no formato "$..."
    matches = re.findall(r'\$(\d*#?\d*d\d+[\+\-\*/\(\)\d]*)', message.content)
    resultados = []
    if matches:
        loop = asyncio.get_running_loop()
        resultados = []
        for m in matches:
            # this will run rolar_dado in a separate thread
            res = await asyncio.to_thread(rolar_dado, m, True)
            resultados.append(
                f"``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', m)}"
            )
        await message.channel.send("\n".join(resultados))
        
    # Respostas sarcasticas
    if len(message.content) > 300 and not is_spam(message.content):
        await asyncio.sleep(2)
        async with message.channel.typing():  # Usa o contexto assíncrono para simular digitação
            await asyncio.sleep(3)  # Aguarda 3 segundos (opcional)
            await safe_request(message.channel.send, random.choice(SARCASM_RESPONSES))

    # Normaliza a mensagem e a palavra do dia (remove acentos e transforma ç -> c)
    mensagem_normalizada = unidecode.unidecode(message.content.lower())
    palavra_normalizada = unidecode.unidecode(palavra_do_dia.lower())

    if palavra_normalizada in mensagem_normalizada:
        await message.channel.send(f'{palavra_do_dia.upper()} DETECTAD!!!! INICIANDO PROTOCOLO DE SEGURANÇA!!!!!')
        await castigar_automatico(message.author, 60)

    await bot.process_commands(message)

@bot.tree.command(name="punir", description="Pune um membro movendo-o para um canal de voz específico por um tempo determinado.")
@app_commands.describe(
    member="Membro a ser punido",
    punish_channel="Canal de voz onde o membro será movido",
    duration="Duração da punição em minutos (opcional, padrão: 1 minuto)"
)
async def punir(interaction: discord.Interaction, member: discord.Member, punish_channel: discord.VoiceChannel, duration: int = 1):
    try:
        # Verifica permissões do autor
        if interaction.user.top_role <= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ **Você precisa ter um cargo superior ao meu para usar este comando!**", ephemeral=True)
            return

        # Verifica se o autor está em um canal de voz
        if not interaction.user.voice:
            await interaction.response.send_message("❌ **Você precisa estar em um canal de voz para usar este comando!**", ephemeral=True)
            return

        # Salva o canal original e move o membro para o canal de punição
        original_channel = member.voice.channel if member.voice else None
        await member.move_to(punish_channel)
        await interaction.response.send_message(f'✅ **{member.mention} foi punido e movido para {punish_channel.name} por {duration} minutos**')

        # Desabilita a permissão de conectar aos outros canais
        for channel in interaction.guild.voice_channels:
            if channel != punish_channel:
                await channel.set_permissions(member, connect=False)

        # Aguarda a duração da punição
        await asyncio.sleep(duration * 60)

        # Restaura as permissões de conexão
        for channel in interaction.guild.voice_channels:
            if channel != punish_channel:
                await channel.set_permissions(member, overwrite=None)

        # Move o membro de volta para o canal original
        if original_channel:
            await member.move_to(original_channel)
            await interaction.followup.send(f'✅ **{member.mention} foi movido de volta para {original_channel.name}**')
        else:
            await interaction.followup.send(f'✅ **{member.mention} foi liberado, mas não havia um canal original para movê-lo.**')

    except discord.Forbidden:
        await interaction.followup.send("❌ **Eu não tenho permissão suficiente para executar essa ação!**", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ **Ocorreu um erro ao mover o membro: {e}**", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ **Algo deu errado: {e}**", ephemeral=True)

@bot.tree.command(name="mover", description="Move todos os membros de um canal de voz para outro")
@app_commands.describe(origem="Canal de onde os usuários serão movidos",
                        destino="Canal para onde os usuários serão movidos",
                        cargo="(Opcional) Apenas move membros com um cargo específico")
async def mover(interaction: discord.Interaction, origem: discord.VoiceChannel, destino: discord.VoiceChannel, cargo: discord.Role = None):
    if not interaction.user.guild_permissions.move_members:
        return await interaction.response.send_message("🚫 Você não tem permissão para mover membros!", ephemeral=True)

    membros_movidos = 0

    for membro in origem.members:
        if cargo and cargo not in membro.roles:
            continue  # Se um cargo foi especificado, ignora membros que não o possuem
        try:
            await membro.move_to(destino)
            membros_movidos += 1
        except discord.Forbidden:
            await interaction.response.send_message(f"🚨 Não tenho permissão para mover {membro.mention}!", ephemeral=True)

    await interaction.response.send_message(f"✅ **{membros_movidos}** membros movidos de {origem.mention} para {destino.mention}!")

@bot.tree.command(name="mutar", description="Muta todos em um canal de voz, um usuário ou um cargo específico")
@app_commands.describe(
    canal="Canal de voz onde os membros serão mutados",
    excecao_usuario="(Opcional) Usuário que NÃO será mutado",
    excecao_cargo="(Opcional) Cargo cujos membros NÃO serão mutados",
    apenas_usuario="(Opcional) Mutar SOMENTE este usuário",
    apenas_cargo="(Opcional) Mutar SOMENTE este cargo"
)
async def mutar(
    interaction: discord.Interaction,
    canal: discord.VoiceChannel,
    excecao_usuario: discord.Member = None,
    excecao_cargo: discord.Role = None,
    apenas_usuario: discord.Member = None,
    apenas_cargo: discord.Role = None
):
    if not interaction.user.guild_permissions.mute_members:
        return await interaction.response.send_message("🚫 Você não tem permissão para mutar membros!", ephemeral=True)

    # Mutar apenas um usuário
    if apenas_usuario:
        try:
            await apenas_usuario.edit(mute=True)
            return await interaction.response.send_message(f"🔇 {apenas_usuario.mention} foi mutado em {canal.mention}!")
        except discord.Forbidden:
            return await interaction.response.send_message(f"🚨 Não tenho permissão para mutar {apenas_usuario.mention}!", ephemeral=True)

    # Mutar apenas um cargo
    if apenas_cargo:
        membros_mutados = 0
        for membro in canal.members:
            if apenas_cargo in membro.roles:
                try:
                    await membro.edit(mute=True)
                    membros_mutados += 1
                except discord.Forbidden:
                    await interaction.response.send_message(f"🚨 Não tenho permissão para mutar {membro.mention}!", ephemeral=True)
        return await interaction.response.send_message(f"🔇 **{membros_mutados}** membros do cargo {apenas_cargo.mention} foram mutados em {canal.mention}!")

    # Mutar todo mundo (exceto quem for exceção)
    membros_mutados = 0
    for membro in canal.members:
        if membro == excecao_usuario or (excecao_cargo and excecao_cargo in membro.roles):
            continue  # Pula quem deve ser ignorado

        try:
            await membro.edit(mute=True)
            membros_mutados += 1
        except discord.Forbidden:
            await interaction.response.send_message(f"🚨 Não tenho permissão para mutar {membro.mention}!", ephemeral=True)

    await interaction.response.send_message(f"🔇 **{membros_mutados}** membros foram mutados em {canal.mention}!")
@bot.tree.command(name="desmutar", description="Desmuta todos em um canal de voz ou apenas um membro específico")
@app_commands.describe(
    canal="Canal de voz onde os membros serão desmutados",
    apenas_usuario="(Opcional) Desmutar SOMENTE este usuário",
    apenas_cargo="(Opcional) Desmutar SOMENTE membros desse cargo"
)
async def desmutar(
    interaction: discord.Interaction,
    canal: discord.VoiceChannel,
    apenas_usuario: discord.Member = None,
    apenas_cargo: discord.Role = None
):
    if not interaction.user.guild_permissions.mute_members:
        return await interaction.response.send_message("🚫 Você não tem permissão para desmutar membros!", ephemeral=True)

    if apenas_usuario:
        try:
            await apenas_usuario.edit(mute=False)
            return await interaction.response.send_message(f"🔊 {apenas_usuario.mention} foi desmutado em {canal.mention}!")
        except discord.Forbidden:
            return await interaction.response.send_message(f"🚨 Não tenho permissão para desmutar {apenas_usuario.mention}!", ephemeral=True)

    membros_desmutados = 0

    for membro in canal.members:
        if apenas_cargo and apenas_cargo not in membro.roles:
            continue  # Pula quem não faz parte do cargo especificado

        try:
            await membro.edit(mute=False)
            membros_desmutados += 1
        except discord.Forbidden:
            await interaction.response.send_message(f"🚨 Não tenho permissão para desmutar {membro.mention}!", ephemeral=True)

    if apenas_cargo:
        await interaction.response.send_message(f"🔊 **{membros_desmutados}** membros com o cargo {apenas_cargo.mention} foram desmutados em {canal.mention}!")
    else:
        await interaction.response.send_message(f"🔊 **{membros_desmutados}** membros foram desmutados em {canal.mention}!")

JOKENPO_OPCOES = {
    "🪨": "Pedra",
    "📜": "Papel",
    "✂️": "Tesoura"
}
@bot.tree.command(name="jokenpo", description="Desafie alguém para uma partida de Jokenpô!")
async def jokenpo(interaction: discord.Interaction):
    await interaction.response.send_message("🎮 **Jokenpô Iniciado!** Aguardando outro jogador... Reaja com 🎮 para entrar!", ephemeral=False)

    msg = await interaction.original_response()
    await msg.add_reaction("🎮")

    def check_jogador2(reaction, user):
        return reaction.message.id == msg.id and str(reaction.emoji) == "🎮" and user != interaction.user and not user.bot

    try:
        reaction, jogador2 = await bot.wait_for("reaction_add", timeout=30.0, check=check_jogador2)
    except asyncio.TimeoutError:
        try:
            await msg.clear_reaction("🎮")  # Remove a reação para evitar confusão
            await msg.edit(content="⏳ **Tempo esgotado!** Nenhum jogador entrou.")
        except discord.errors.NotFound:
            print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")
        return

    await msg.clear_reactions()
    await msg.edit(content=f"🆚 {interaction.user.mention} **vs** {jogador2.mention}!\n\nEscolham Pedra (🪨), Papel (📜) ou Tesoura (✂️) reagindo abaixo!")

    for emoji in JOKENPO_OPCOES.keys():
        await msg.add_reaction(emoji)

    escolhas = {interaction.user: None, jogador2: None}

    def check_escolha(reaction, user):
        return reaction.message.id == msg.id and user in escolhas and str(reaction.emoji) in JOKENPO_OPCOES and escolhas[user] is None

    while None in escolhas.values():
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check_escolha)
            escolhas[user] = JOKENPO_OPCOES[str(reaction.emoji)]
        except asyncio.TimeoutError:
            try:
                await msg.clear_reactions()
                await msg.edit(content="⏳ **Tempo esgotado!** Um dos jogadores não escolheu a tempo.")
            except discord.errors.NotFound:
                print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")
            return

    # Determinar vencedor
    resultado = determinar_vencedor(escolhas[interaction.user], escolhas[jogador2])
    try:
        await msg.clear_reactions()
        await msg.edit(content=f"🆚 {interaction.user.mention} **vs** {jogador2.mention}!\n\n"
                               f"🎭 **Escolhas:**\n"
                               f"🔹 {interaction.user.mention} escolheu **{escolhas[interaction.user]}**\n"
                               f"🔹 {jogador2.mention} escolheu **{escolhas[jogador2]}**\n\n"
                               f"{resultado}")
    except discord.errors.NotFound:
        print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")
def determinar_vencedor(jogada1, jogada2):
    if jogada1 == jogada2:
        return "🤝 **Empate!**"
    elif (jogada1 == "Pedra" and jogada2 == "Tesoura") or \
         (jogada1 == "Papel" and jogada2 == "Pedra") or \
         (jogada1 == "Tesoura" and jogada2 == "Papel"):
        return "🎉 **O primeiro jogador venceu!**"
    else:
        return "🎉 **O segundo jogador venceu!**"

@bot.tree.command(name="db_test", description="Testa o banco de dados")
@app_commands.describe(action="Escolha entre save ou load", name="Nome da chave", value="Valor a ser salvo (apenas para save)")
async def db_test(interaction: discord.Interaction, action: str, name: str, value: str = None):
    # Defer a resposta para garantir mais tempo para processamento
    await interaction.response.defer()

    if action == "save":
        if value is None:
            await interaction.followup.send("Você precisa fornecer um valor para salvar!", ephemeral=True)
            return
        await save(name, value)
        await interaction.followup.send(f"Salvo: `{name}` = `{value}`")
    elif action == "load":
        result = load(name)
        if result is None:
            await interaction.followup.send(f"Nenhum dado encontrado para `{name}`.", ephemeral=True)
        else:
            await interaction.followup.send(f"Valor de `{name}`: `{result}`")
    else:
        await interaction.followup.send("Ação inválida! Use 'save' ou 'load'.", ephemeral=True)

# Tocador
voice_clients = {}
queues = {}
loop_status = {}  # 0 = off, 1 = loop música atual, 2 = loop fila
def check_auto_disconnect(guild_id):
    async def task():
        await asyncio.sleep(60)  # Aguarda 1 minuto
        vc = voice_clients.get(guild_id)
        if vc and not vc.is_playing() and not queues.get(guild_id):
            await vc.disconnect()
            del voice_clients[guild_id]
            del queues[guild_id]  # Limpa também a fila

    # Certifica-se de que o loop de eventos correto está sendo utilizado
    loop = bot.loop # Obtém o loop de eventos do discord client
    asyncio.run_coroutine_threadsafe(task(), loop)  # Executa a tarefa de forma segura no loop principal
def play_next(guild_id):
    if guild_id not in queues or not queues[guild_id]:
        check_auto_disconnect(guild_id)
        return

    vc = voice_clients[guild_id]
    current_track = queues[guild_id][0]

    def after_playback(error):
        if error:
            print(f"Erro ao tocar áudio: {error}")

        # Se estiver em loop da música, repete o mesmo
        if loop_status.get(guild_id, 0) == 1:
            play_next(guild_id)
        # Se estiver em loop da fila, move o atual para o final e toca o próximo
        elif loop_status.get(guild_id, 0) == 2:
            queues[guild_id].append(queues[guild_id].pop(0))
            play_next(guild_id)
        else:
            # Loop desativado: remove a música da fila
            queues[guild_id].pop(0)
            if queues[guild_id]:
                play_next(guild_id)
            else:
                check_auto_disconnect(guild_id)

    vc.play(discord.FFmpegPCMAudio(current_track), after=after_playback)
def buscar_arquivo(nome):
    nome_normalizado = unidecode.unidecode(nome).lower()
    for root, _, files in os.walk("assets/audios"):
        for file in files:
            if unidecode.unidecode(file).lower().startswith(nome_normalizado):
                return os.path.join(root, file)
    return None
@bot.tree.command(name="entrar", description="Faz o bot entrar no canal de voz e permanecer lá")
@app_commands.describe(canal="Canal de voz onde o bot entrará")
async def entrar(interaction: discord.Interaction, canal: discord.VoiceChannel):
    if not interaction.user.guild_permissions.connect:
        return await interaction.response.send_message("🚫 Você não tem permissão para usar este comando!", ephemeral=True)
    
    if interaction.guild.id in voice_clients:
        return await interaction.response.send_message("⚠️ Já estou em um canal de voz!", ephemeral=True)
    
    vc = await canal.connect()
    voice_clients[interaction.guild.id] = vc
    await interaction.response.send_message(f"🔊 Entrei no canal {canal.mention}!")
@bot.tree.command(name="tocar", description="Toca um ou mais áudios no canal de voz")
@app_commands.describe(arquivo="Nome(s) do(s) arquivo(s) de áudio ou pasta, separados por vírgula")
async def tocar(interaction: discord.Interaction, arquivo: str):
    guild_id = interaction.guild.id
    vc = voice_clients.get(guild_id)

    if not vc:
        canal = interaction.user.voice.channel if interaction.user.voice else None
        if not canal:
            return await interaction.response.send_message("❌ Você não está em um canal de voz e o bot também não está!", ephemeral=True)
        vc = await canal.connect()
        voice_clients[guild_id] = vc

    nomes = [nome.strip() for nome in arquivo.split(",")]
    encontrados = []

    if guild_id not in queues:
        queues[guild_id] = []

    for nome in nomes:
        if nome.startswith("*"):
            pasta = nome[1:]
            caminho_pasta = os.path.join("assets/audios", pasta)
            if os.path.exists(caminho_pasta) and os.path.isdir(caminho_pasta):
                arquivos = sorted([
                    os.path.join(caminho_pasta, f)
                    for f in os.listdir(caminho_pasta)
                    if os.path.isfile(os.path.join(caminho_pasta, f))
                ])
                if arquivos:
                    queues[guild_id].extend(arquivos)
                    encontrados.append(f"[{len(arquivos)} de {pasta}]")
                else:
                    await interaction.channel.send(f"⚠️ A pasta `{pasta}` está vazia!")
            else:
                await interaction.channel.send(f"❌ Pasta `{pasta}` não encontrada!")
        else:
            audio_file = buscar_arquivo(nome)
            if audio_file:
                queues[guild_id].append(audio_file)
                encontrados.append(nome)
            else:
                await interaction.channel.send(f"⚠️ Arquivo `{nome}` não encontrado!")

    if not encontrados:
        return await interaction.response.send_message("❌ Nenhum dos áudios ou pastas foi encontrado!", ephemeral=True)

    if not vc.is_playing():
        play_next(guild_id)
        await interaction.response.send_message(f"🎵 Tocando `{encontrados[0]}` e adicionando o resto à fila!")
    else:
        await interaction.response.send_message(f"🎶 Adicionado(s) à fila: {', '.join(encontrados)}")
@bot.tree.command(name="listar", description="Lista todos os áudios")
async def listar(interaction: discord.Interaction):
    diretorio = "assets/audios"
    if not os.path.exists(diretorio):
        return await interaction.response.send_message("❌ Diretório não encontrado!", ephemeral=True)

    def build_tree(path, prefix):
        itens = os.listdir(path)
        dirs = [item for item in itens if os.path.isdir(os.path.join(path, item))]
        files = [item for item in itens if os.path.isfile(os.path.join(path, item))]
        combinados = dirs + files

        linhas = []
        for idx, item in enumerate(combinados):
            is_last = (idx == len(combinados) - 1)
            branch = "└──" if is_last else "├──"
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                linhas.append(f"{prefix}{branch} 📁 {item}/")
                novo_prefix = prefix + ("    " if is_last else "│   ")
                linhas.extend(build_tree(item_path, novo_prefix))
            else:
                linhas.append(f"{prefix}{branch} 📄 {item}")
        return linhas

    tree_lines = build_tree(diretorio, "│   ")
    lista_arquivos = f"📂 {os.path.basename(diretorio)}/\n" + "\n".join(tree_lines) if tree_lines else "📂 Diretório vazio."

    if len(lista_arquivos) > 2000:
        with open("lista_arquivos.txt", "w", encoding="utf-8") as f:
            f.write(lista_arquivos)
        await interaction.response.send_message("📜 Lista de arquivos:", file=discord.File("lista_arquivos.txt"))
        os.remove("lista_arquivos.txt")
    else:
        await interaction.response.send_message(f"**Arquivos e pastas em `{diretorio}`:**\n```\n{lista_arquivos}\n```")
@bot.tree.command(name="parar", description="Para a reprodução e limpa a fila")
async def parar(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = voice_clients.get(guild_id)
    
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("❌ Não há áudio tocando!", ephemeral=True)
    
    queues[guild_id] = []  # Limpa a fila
    vc.stop()
    await interaction.response.send_message("⏹️ Reprodução interrompida e fila limpa!")
@bot.tree.command(name="sair", description="Faz o bot sair do canal de voz e limpa a fila de reprodução")
async def sair(interaction: discord.Interaction):
    vc = voice_clients.pop(interaction.guild.id, None)
    if not vc:
        return await interaction.response.send_message("❌ Não estou em um canal de voz!", ephemeral=True)
    
    queues.pop(interaction.guild.id, None)  # Limpa a fila de reprodução
    await vc.disconnect()
    await interaction.response.send_message("👋 Saí do canal de voz e limpei a fila de reprodução!")
@bot.tree.command(name="pular", description="Pula para o próximo áudio na fila")
async def pular(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = voice_clients.get(guild_id)
    
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("❌ Nenhum áudio está tocando!", ephemeral=True)
    
    vc.stop()
    await interaction.response.send_message("⏭️ Pulando para o próximo áudio...")
    
    play_next(guild_id)
@bot.tree.command(name="fila", description="Mostra a fila de áudios")
async def fila(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    queue = queues.get(guild_id, [])
    
    if not queue:
        return await interaction.response.send_message("🎶 A fila está vazia!", ephemeral=True)
    
    lista = "\n".join([f"{idx+1}. {os.path.basename(track)}" for idx, track in enumerate(queue)])
    await interaction.response.send_message(f"📜 **Fila de reprodução:**\n```\n{lista}\n```")
@bot.tree.command(name="loop")
@app_commands.describe(modo="0: Desativado, 1: Música Atual, 2: Fila Inteira (opcional)")
async def loop(interaction: discord.Interaction, modo: int = None):
    # Alterna o loop entre 0 (desativado), 1 (música atual) e 2 (fila inteira), ou define um modo específico
    guild_id = interaction.guild.id
    estado_atual = loop_status.get(guild_id, 0)

    if modo is None:
        # Alterna entre 0 → 1 → 2 → 0...
        novo_estado = (estado_atual + 1) % 3
    else:
        # Se um valor for fornecido, define diretamente (garantindo que esteja entre 0 e 2)
        novo_estado = max(0, min(2, modo))

    loop_status[guild_id] = novo_estado

    mensagens = {
        0: "🔁 Loop desativado!",
        1: "🔂 Loop da música atual ativado!",
        2: "🔁 Loop da fila inteira ativado!",
    }

    await interaction.response.send_message(mensagens[novo_estado])
@bot.tree.command(name="shuffle", description="Embaralha a fila de áudios")
async def shuffle(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    fila = queues.get(guild_id)

    if not fila or len(fila) <= 1:
        return await interaction.response.send_message("🎶 A fila está vazia ou tem apenas um item!", ephemeral=True)

    # Se a música atual tá tocando, deixa ela no topo e embaralha o resto
    tocando_agora = fila[0]
    restante = fila[1:]
    random.shuffle(restante)
    queues[guild_id] = [tocando_agora] + restante

    await interaction.response.send_message("🔀 Fila embaralhada com sucesso!")
@bot.tree.command(name="salvar_fila", description="Salva a fila atual em um ID único")
async def salvar_fila(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    queue = queues.get(guild_id, [])

    if not queue:
        return await interaction.response.send_message("❌ A fila está vazia, nada para salvar!", ephemeral=True)

    # Gera um ID único baseado nos nomes dos arquivos na fila
    nomes_arquivos = [os.path.basename(track) for track in queue]
    fila_serializada = ",".join(nomes_arquivos)
    fila_codificada = urlsafe_b64encode(fila_serializada.encode()).decode()

    await interaction.response.send_message(f"✅ Fila salva com sucesso! Use este ID para carregar: `{fila_codificada}`", ephemeral=True)
@bot.tree.command(name="carregar_fila", description="Carrega uma fila salva usando um ID")
@app_commands.describe(fila_id="ID da fila a ser carregada")
async def carregar_fila(interaction: discord.Interaction, fila_id: str):
    try:
        # Decodifica o ID para obter os nomes dos arquivos
        fila_decodificada = urlsafe_b64decode(fila_id.encode()).decode()
        nomes_arquivos = fila_decodificada.split(",")

        guild_id = interaction.guild.id
        if guild_id not in queues:
            queues[guild_id] = []

        encontrados = []
        for nome in nomes_arquivos:
            audio_file = buscar_arquivo(nome)
            if audio_file:
                queues[guild_id].append(audio_file)
                encontrados.append(nome)
            else:
                await interaction.channel.send(f"⚠️ Arquivo `{nome}` não encontrado!")

        if not encontrados:
            return await interaction.response.send_message("❌ Nenhum dos áudios foi encontrado!", ephemeral=True)

        vc = voice_clients.get(guild_id)
        if not vc or not vc.is_playing():
            play_next(guild_id)
            await interaction.response.send_message(f"🎵 Fila carregada e tocando `{encontrados[0]}`!")
        else:
            await interaction.response.send_message(f"🎶 Fila carregada! Adicionado(s) à fila: {', '.join(encontrados)}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao carregar a fila: {e}", ephemeral=True)

@bot.tree.command(name="roletarussa", description="Vida ou morte.")
async def roletarussa(interaction: discord.Interaction):
    result = random.randrange(0,100)
    if result <= 14:
        await interaction.response.send_message(f"Você **morreu**")
    else:
        await interaction.response.send_message("Você *sobrevive*")

@bot.tree.command(name="missao", description="Receba uma missão")
async def missao(interaction: discord.Interaction):
    missoes = [
    "No meio de uma conversa séria, olha pra alguém e diz: 'Mano, eu tava pensando aqui... Tu deixaria eu te dar uma mamada?' com a cara mais séria possível.",
    "Sempre que alguém falar contigo por 10 minutos, responde só com gestos, olhares intensos e mordendo os lábios.",
    "Liga pra um número aleatório da tua lista de contatos e fala 'Você sabe por que eu liguei...' e fica em silêncio esperando a reação.",
    "Entra no chat da pessoa mais improvável e manda: 'Mano, não sei como te contar isso, mas eu sonhei que a gente se pegava. E foi bom.'",
    "Finge que acabou de encontrar Jesus/Buda/um Alien e tenta converter um amigo do grupo de maneira fanática.",
    "Escreve uma resenha absurda no status do WhatsApp, tipo: 'Recomendo a experiência de levar uma dedada no cu. Profundo e emocionante.'",
    "Pede pra alguém abrir o Google na tua frente e digita: 'É normal sentir prazer em...' e deixa o autocorretor terminar.",
    "Manda um áudio gemendo no grupo da família e depois responde: 'Foi sem querer, meu cachorro pisou no microfone.'",
    "Chama um desconhecido no Instagram e conta uma história totalmente falsa sobre como vocês já foram melhores amigos na infância.",
    "No meio de uma call, começa a discursar como se fosse um coach ultra motivacional sobre o 'poder da mamada' para o sucesso.",
    f"Manda uma mensagem pro {randomuser()} dizendo: 'Sonhei que a gente se pegava na força do ódio, mas no final gostei. O que isso significa?' e espera a resposta.",
    f"Chega no {randomuser()} e fala bem sério: 'Eu vendi tua cueca/calcinha usada na deep web por R$350, foi mal.' e vê a reação.",
    f"Faz um gemido bem convincente no ouvido do {randomuser()} e diz: 'Desculpa, não consegui me segurar.'",
    f"Liga pro {randomuser()} e começa a respirar fundo no telefone, depois solta: 'Tu tem ideia do que tu fez comigo naquela noite?' e desliga.",
    f"Manda pro {randomuser()}: 'Preciso ser honesto... Minha mãe me pegou vendo tuas fotos e perguntou se tu era meu crush.'",
    f"Olha pro {randomuser()} no meio de um papo aleatório e diz: 'Tu já experimentou chupar um dedão do pé? Porque eu sonhei que fazia isso contigo.'",
    f"Chega no {randomuser()} e fala: 'Preciso te contar... Eu tatuei teu nome numa área íntima, mas só te mostro se tu pedir com carinho.'",
    f"Manda um áudio pro {randomuser()} gemendo e depois explica: 'Foi sem querer, tava testando meu novo microfone ASMR.'",
    f"Vai no PV do {randomuser()} e manda: 'Ei... Quanto tu cobraria pra pisar em mim de coturno?' e mantém a conversa séria.",
    f"Faz uma aposta com {randomuser()}, perde de propósito e depois fala: 'Aposta é aposta, agora tu tem que me deixar morder tua orelha.'"
]
    await interaction.response.send_message(random.choice(missoes))

@bot.tree.command(name="piada", description="Piadocas pesadonas")
async def piada(interaction: discord.Interaction):
    def carregar_piada():
        with open("resources/piadas.txt", "r", encoding="utf-8") as f:
            return [linha.strip() for linha in f.readlines()]
    
    piadas = carregar_piada()

    await interaction.response.send_message(random.choice(piadas))

@bot.tree.command(name="roleta", description="Escolhe uma opção aleatóriamente")
async def roleta(interaction: discord.Interaction, opcoes: str):
    opcoesNaRoleta = {}
    opcoesNaRoleta = opcoes.split(", ")
    await interaction.response.send_message(f"O escolhido foi: *{random.choice(opcoesNaRoleta)}*!")

@bot.tree.command(name="pdd", description="pdd")
@app_commands.default_permissions(administrator=True)  # Permite apenas para admins
async def pdd(interaction: discord.Interaction):
    await interaction.response.send_message(f"{palavra_do_dia}", ephemeral=True)

# Função para processar a rolagem de dados
def rolar_dado(expressao, detalhado=True):
    if not detalhado:
        detalhes = []
        def substituir(match):
            qtd_str, faces_str = match.groups()
            qtd   = int(qtd_str)  if qtd_str  else 1
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

        expr_mod = re.sub(r'(\d*)d(\d+)', substituir, expressao)
        try:
            resultado = eval(expr_mod)
        except:
            return None

        return {
            "resultado": resultado,
            "resultadoWOutEval": expr_mod,
            "detalhado": False
        }

    else:
        detalhes = []
        def substituir(match):
            qtd_str, faces_str = match.groups()
            qtd   = int(qtd_str)  if qtd_str  else 1
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

        expr_mod = re.sub(r'(\d*)d(\d+)', substituir, expressao)
        try:
            resultado = eval(expr_mod)
        except:
            return None

        # montagem do breakdown
        if len(detalhes) == 1:
            breakdown  = str(detalhes[0])
            m          = re.search(r'(\d*d\d+)', expressao)
            dice_group = m.group(1) if m else expressao
        else:
            breakdown  = " + ".join(str(lst) for lst in detalhes)
            dice_group = expressao

        return {
            "resultado": resultado,
            "resultadoWOutEval": breakdown,
            "dice_group": dice_group,
            "detalhado": True
        }
# Comando de rolagem de dado (/rolar)
@bot.tree.command(name="rolar", description="Rola dados no formato XdY com operações matemáticas")
@app_commands.describe(expressao="Exemplo: 2d6+2, 4d10/2, 5#d5+5")
async def rolar(interaction: discord.Interaction, expressao: str):
    if "#" in expressao:
        # Se for múltiplo (5#d5+5): usa o comportamento não detalhado
        qtd, dado = expressao.split("#", 1)
        qtd = int(qtd)
        resultados = [rolar_dado(dado, detalhado=False) for _ in range(qtd)]
        msg = "\n".join(
            f"``{r['resultado']}`` ⟵ [{r['resultadoWOutEval']}] {expressao}"
            for r in resultados
        )
        return await interaction.response.send_message(msg)
    else:
        # Para rolagens simples, usa o comportamento detalhado
        res = await asyncio.to_thread(rolar_dado, expressao, True)
        if res is None:
            return await interaction.response.send_message("❌ Expressão inválida!", ephemeral=True)
        # Aqui não encapsulamos em colchetes, pois o breakdown já vem formatado (ex.: "[5, 4, 3, 2, 1]")
        msg = f"``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', expressao)}"
        return await interaction.response.send_message(msg)

@bot.tree.command(name="shippar", description="Calcula a chance de 2 usuários ficarem juntos")
async def shippar(interaction: discord.Interaction, nome1: str, nome2: str):
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
                sequencia = [int(d) for d in ''.join(str(num) for num in nova_seq)]
            return int(''.join(str(d) for d in sequencia))

        # 4. Calcular e retornar o resultado final
        resultado = reduzir(contagem)
        return f"{resultado}% de compatibilidade"
    await interaction.response.send_message(f"{nome1.capitalize()} e {nome2.capitalize()} tem {calcular_compatibilidade(nome1, nome2)}")

@bot.tree.command(name="deepfry", description="Aplica o efeito deep fry em uma imagem.")
@app_commands.describe(imagem="Imagem para aplicar o efeito deep fry")
async def deepfry(interaction: discord.Interaction, imagem: discord.Attachment):
    await interaction.response.defer()  # Pra dar tempo de processar a imagem

    try:
        # Baixa a imagem
        img_bytes = await imagem.read()
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        img = ImageEnhance.Contrast(img).enhance(4.0)
        img = ImageEnhance.Sharpness(img).enhance(12.0)
        img = ImageEnhance.Color(img).enhance(8.0)
        img = ImageEnhance.Brightness(img).enhance(1.5)

        # Adiciona um overlay vermelho
        overlay = Image.new('RGB', img.size, (255, 0, 0))
        img = Image.blend(img, overlay, alpha=0.2)

        # Faz compressão zoada JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=10)
        buffer.seek(0)

        await interaction.followup.send("🧨 **Imagem deep fried com sucesso!**", file=discord.File(buffer, filename="deepfried.jpg"))

    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao aplicar o efeito: {e}", ephemeral=True)

POPULAR_LANGUAGES = {
    "English": "en",
    "Português": "pt",
    "Español": "es",
    "Français": "fr",
    "Deutsch": "de",
    "Italiano": "it",
    "Русский": "ru",
    "中文": "zh",
    "日本語": "ja",
    "한국어": "ko",
    "العربية": "ar",
    "हिन्दी": "hi",
    "বাংলা": "bn",
    "Türkçe": "tr",
    "Việt": "vi",
    "Polski": "pl",
    "Nederlands": "nl",
    "Ελληνικά": "el",
    "Čeština": "cs",
    "Svenska": "sv",
    "Dansk": "da",
    "Suomi": "fi",
    "עברית": "he",
    "Bahasa Indonesia": "id",
    "Norsk": "no"
}
@bot.tree.command(name="hypertranslate", description="Traduz um texto por várias línguas aleatórias e retorna o resultado final.")
@app_commands.describe(
    texto="Texto original para traduzir",
    vezes="Quantidade de vezes a traduzir (máximo 50)",
    idioma_entrada="Idioma original do texto (ou auto para detectar)",
    idioma_saida="Idioma final do texto traduzido"
)
@app_commands.choices(
    idioma_entrada=[
        app_commands.Choice(name=nome, value=cod)
        for nome, cod in POPULAR_LANGUAGES.items()
    ],
    idioma_saida=[
        app_commands.Choice(name=nome, value=cod)
        for nome, cod in POPULAR_LANGUAGES.items()
    ]
)
async def hypertranslate(
    interaction: discord.Interaction,
    texto: str,
    vezes: int = 10,
    idioma_entrada: app_commands.Choice[str] = None,
    idioma_saida: app_commands.Choice[str] = None
):
    await interaction.response.defer()

    if vezes < 1 or vezes > 50:
        return await interaction.followup.send("❌ Escolha entre 1 e 50 traduções.", ephemeral=True)

    # Define o idioma de entrada; se não informado, usa "auto"
    entrada = idioma_entrada.value if idioma_entrada else "auto"
    # Se o idioma de saída não for informado, retorna para o idioma de entrada
    saida = idioma_saida.value if idioma_saida else entrada

    langs = GoogleTranslator().get_supported_languages(as_dict=True)
    lang_codes = list(langs.values())

    atual = texto
    usado = []

    try:
        for _ in range(vezes):
            destino = random.choice(lang_codes)
            # Garante que não escolha o idioma de entrada ou repetido
            while destino in usado or destino == entrada or destino == "auto":
                destino = random.choice(lang_codes)
            usado.append(destino)

            try:
                atual = GoogleTranslator(source="auto", target=destino).translate(atual)
                if not atual:  # Handle empty or unexpected results
                    raise ValueError(f"Tradução falhou para o idioma {destino}.")
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao traduzir para o idioma {destino}: {e}", ephemeral=True)
                return
            await asyncio.sleep(0.3)

        # Traduz de volta para o idioma de saída escolhido
        final = GoogleTranslator(source="auto", target=saida).translate(atual)

        await interaction.followup.send(
            f"🌐 **Tradução de {texto} iniciada!**\n"
            f"**Idioma de entrada:** `{entrada}`\n"
            f"**Idioma final:** `{saida}`\n"
            f"**Rodadas:** {vezes}\n"
            f"🔁 **Texto final:**\n```{final}```"
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Ocorreu um erro durante as traduções: {e}", ephemeral=True)

@bot.tree.command(name="lapide", description="Cria uma lápide com o nome de alguém ou texto personalizado.")
@app_commands.describe(
    usuario="(Opcional) Alvo da lápide",
    texto="(Opcional) Texto a ser escrito na lápide"
)
async def lapide(interaction: discord.Interaction, usuario: discord.Member = None, texto: str = None):
    await interaction.response.defer()

    try:
        # Decide o que será escrito
        nome_final = texto or (usuario.display_name if usuario else interaction.user.display_name)
        nome_final = nome_final.upper()

        # Caminhos
        caminho_imagem = "assets/images/grave.png"
        caminho_fonte = "assets/fonts/PTSerif-Bold.ttf"

        # 1) Carrega imagem base
        img = Image.open(caminho_imagem).convert("RGBA")

        # 2) Fonte
        fonte = ImageFont.truetype(caminho_fonte, 50)

        # 3) Camada de texto
        text_layer = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        bbox = fonte.getbbox(nome_final)
        w_text = bbox[2] - bbox[0]
        h_text = bbox[3] - bbox[1]
        x_center = (600 - w_text) // 2
        y_center = (200 - h_text) // 2

        draw.text((x_center, y_center), nome_final, font=fonte, fill=(50, 50, 50, 180))

        # 4) Inclinação e blending
        rotated = text_layer.rotate(3.5, expand=True, resample=Image.BICUBIC)

        pos_x, pos_y = 160, 400
        w_rot, h_rot = rotated.size
        area_crop = img.crop((pos_x, pos_y, pos_x + w_rot, pos_y + h_rot))
        blended = ImageChops.multiply(area_crop, rotated)
        img.paste(blended, (pos_x, pos_y), rotated)

        # 5) Buffer e envio
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        await interaction.followup.send(
            content=f"🪦 Aqui jaz **{nome_final}**...",
            file=discord.File(fp=buffer, filename="lapide.png")
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao gerar a lápide: {e}", ephemeral=True)

# Lista de fontes famosas e melhores
FONTES_DISPONIVEIS = [
    "5lineoblique", "standard", "slant", "3-d", "alphabet", "doh", "isometric1", "block", "bubble", "digital"
]

@bot.tree.command(name="ascii", description="Gera uma arte ASCII com o texto e fonte escolhidos.")
@app_commands.describe(
    texto="Texto para converter em arte ASCII",
    fonte="Fonte para a arte ASCII (opcional, padrão: standard)"
)
@app_commands.choices(
    fonte=[app_commands.Choice(name=fonte, value=fonte) for fonte in FONTES_DISPONIVEIS]
)
async def ascii(interaction: discord.Interaction, texto: str, fonte: app_commands.Choice[str] = None):
    try:
        # Define a fonte padrão se nenhuma for escolhida
        fonte_escolhida = fonte.value if fonte else "standard"

        # Gera a arte ASCII
        arte = pyfiglet.figlet_format(texto, font=fonte_escolhida, width=50)
        if len(arte) > 2000:  # Limite de caracteres do Discord
            return await interaction.response.send_message(
                "❌ O resultado é muito grande para ser enviado no Discord!",
                ephemeral=True
            )

        await interaction.response.send_message(f"```\n{arte}\n```")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao gerar a arte ASCII: {e}", ephemeral=True)

# Inicia o bot
bot.run(DISCORDTOKEN)