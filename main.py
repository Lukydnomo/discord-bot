# Terceiros
import os
import random

# Discord
import discord
from deep_translator import GoogleTranslator
from discord.ext import commands

# Instâncias iniciais
cached_supported_languages = None  # Cache for supported languages
translate = GoogleTranslator

# Configuração do bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
from core.config import *
from core.events import *
from core.modules import *
from discord.ui import View, Button

# chama antes de inicializar o bot
cancel_previous_github_runs()

# ... após as importações ...

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commandPrefix,
            intents=intents    # <<< use o intents que você configurou em cima
        )

    async def setup_hook(self):
        # Carrega cada arquivo .py dentro de cogs/
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        # Sincroniza seus slash commands
        await self.tree.sync()

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
async def randomuser():
    for guild in bot.guilds:  # Itera sobre os servidores onde o bot está
        members = [member for member in guild.members if not member.bot]  # Filtra membros não-bots
        
        if members:
            return random.choice(members)  # Retorna um membro aleatório
    
    return "No valid members found"  # Retorno caso não haja membros válidos

# Evento de quando o bot estiver pronto
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await on_ready_custom(bot, conteudo)  # Chama a função personalizada

@bot.event
async def on_message(message):
    await on_message_custom(bot, message)

# Inicia o bot
bot.run(DISCORDTOKEN)