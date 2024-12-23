import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
import json

# Configuração do bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
prefix = 'foa!'
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
updateyn = 0

# Nome do arquivo Markdown
arquivo_md = "changelog.md"

# Abrir o arquivo em modo leitura
with open(arquivo_md, "r", encoding="utf-8") as arquivo:
    conteudo = arquivo.read()  # Lê todo o conteúdo do arquivo e coloca na variável
with open('avisos_sessao.json', 'r') as file:
    avisos = json.load(file)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=prefix, intents=intents)

    # Sincroniza comandos quando o bot inicia
    async def setup_hook(self):
        await self.tree.sync()  # Sincroniza comandos globalmente
        print("✅ Comandos sincronizados globalmente!")

bot = MyBot()

# Lógicas
sessaoclosedopen = 0
# Função para punir um membro
async def punir_logic(ctx, member: discord.Member, punish_channel: discord.VoiceChannel, duration: int = 1):
    try:
        # Verifica permissões do autor
        if ctx.author.top_role <= ctx.guild.me.top_role:
            await ctx.send("❌ **Você precisa ter um cargo superior ao meu para usar este comando!**")
            return

        # Verifica se o autor está em um canal de voz
        if not ctx.author.voice:
            await ctx.send("❌ **Você precisa estar em um canal de voz para usar este comando!**")
            return

        # Salva o canal original e move o membro para o canal de punição
        original_channel = member.voice.channel if member.voice else None
        await member.move_to(punish_channel)
        await ctx.send(f'✅ **{member.mention} foi punido e movido para {punish_channel.name} por {duration} minutos**')

        # Desabilita a permissão de conectar aos outros canais
        for channel in ctx.guild.voice_channels:
            if channel != punish_channel:
                await channel.set_permissions(member, connect=False)

        # Aguarda a duração da punição
        await asyncio.sleep(duration * 60)

        # Restaura as permissões de conexão
        for channel in ctx.guild.voice_channels:
            if channel != punish_channel:
                await channel.set_permissions(member, overwrite=None)

        # Move o membro de volta para o canal original
        if original_channel:
            await member.move_to(original_channel)
            await ctx.send(f'✅ **{member.mention} foi movido de volta para {original_channel.name}**')
        else:
            await ctx.send(f'✅ **{member.mention} foi liberado, mas não havia um canal original para movê-lo.**')

    except discord.Forbidden:
        await ctx.send("❌ **Eu não tenho permissão suficiente para executar essa ação!**")
    except discord.HTTPException as e:
        await ctx.send(f"❌ **Ocorreu um erro ao mover o membro: {e}**")
    except Exception as e:
        await ctx.send(f"❌ **Algo deu errado: {e}**")

# Lógica para iniciar a sessão
async def togglesessao_logic(ctx, mesa: str, interaction: discord.Interaction = None):
    global sessaoclosedopen
    canalAviso = bot.get_channel(1319306482470228020)

    mesa_principal_cargo = 1319301421216301179
    mesa_desordem_cargo = 1320516709089673237

    if sessaoclosedopen == 0:
        try:
            if canalAviso:
                if mesa == "mesa-principal":
                    avisoOpen = random.choice(avisos["avisos_sessaoOpen"]).format(mesa=mesa_principal_cargo)
                    await canalAviso.send(avisoOpen)
                elif mesa == "mesa-desordem":
                    avisoOpen = random.choice(avisos["avisos_sessaoOpen"]).format(mesa=mesa_desordem_cargo)
                    await canalAviso.send(avisoOpen)
                else:
                    await ctx.send("Mesa não encontrada")  # Isso é para comandos prefixados
            if interaction:  # Se for uma interação de slash command
                await interaction.response.send_message(f"Sessão iniciada na {mesa}!")  # Responde a interação
            else:
                await ctx.send(f"Sessão iniciada na {mesa}!")  # Para comandos prefixados
            sessaoclosedopen = 1
        except Exception as e:
            if interaction:
                await interaction.response.send_message(f"**Algo deu errado: {e}**")  # Responde a interação de erro
            else:
                await ctx.send(f"**Algo deu errado: {e}**")
    elif sessaoclosedopen == 1:
        try:
            if canalAviso:
                if mesa == "mesa-principal":
                    avisoClosed = random.choice(avisos["avisos_sessaoClose"]).format(mesa=mesa_principal_cargo)
                    await canalAviso.send(avisoClosed)
                elif mesa == "mesa-desordem":
                    avisoClosed = random.choice(avisos["avisos_sessaoClose"]).format(mesa=mesa_desordem_cargo)
                    await canalAviso.send(avisoClosed)
                else:
                    await ctx.send("Mesa não encontrada")  # Isso é para comandos prefixados
            if interaction:  # Se for uma interação de slash command
                await interaction.response.send_message(f"Sessão encerrada na {mesa}!")  # Responde a interação
            else:
                await ctx.send(f"Sessão encerrada na {mesa}!")  # Para comandos prefixados
            sessaoclosedopen = 0
        except Exception as e:
            if interaction:
                await interaction.response.send_message(f"**Algo deu errado: {e}**")  # Responde a interação de erro
            else:
                await ctx.send(f"**Algo deu errado: {e}**")


# Evento de quando o bot estiver pronto
@bot.event
async def on_ready():
    updatechannel = bot.get_channel(1319356880627171448)

    print(f'Bot conectado como {bot.user}')
    for guild in bot.guilds:
        try:
            print(f"Sincronizando comandos para o servidor: {guild.name}")
            await bot.tree.sync(guild=guild)
            print(f"✅ Comandos sincronizados com sucesso para o servidor: {guild.name}")
        except Exception as e:
            print(f"❌ Falha ao sincronizar comandos no servidor {guild.name}: {e}")

    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="Trabalhando pro Myuki",
        details="(E pro Luky)",
        large_image="punish",
        large_text="Moderando",
        small_image="punish",
        small_text="Feito por Luky",
    )
    await bot.change_presence(activity=activity)

    if updateyn == 1:
        if updatechannel:
            await updatechannel.send(f"{conteudo}\n\n<@&1319355628195549247>")
        else:
            print("❌ Canal de atualização não encontrado.")
    else:
        print("❌ Atualização não habilitada.")

# Comando prefixado "punir"
@bot.command(name="punir")
async def punir(ctx, member: discord.Member, punish_channel: discord.VoiceChannel, duration: int = 1):
    await punir_logic(ctx, member, punish_channel, duration)

@bot.command(name="togglesessao")
async def togglesessao(ctx, mesa: str):
    await togglesessao_logic(ctx, mesa)

# Comando de barra "/punir"
@bot.tree.command(name="punir", description="Pune um membro movendo-o para um canal de voz específico por um tempo determinado.")
@app_commands.describe(
    member="Membro a ser punido",
    punish_channel="Canal de voz onde o membro será movido",
    duration="Duração da punição em minutos (opcional, padrão: 1 minuto)"
)
async def punir(interaction: discord.Interaction, member: discord.Member, punish_channel: discord.VoiceChannel, duration: int = 1):
    fake_ctx = await commands.Context.from_interaction(interaction)
    await punir_logic(fake_ctx, member, punish_channel, duration)

@bot.tree.command(name="togglesessao", description="Iniciar a sessão")
@app_commands.describe(
    mesa="Mesa a ser marcada"
)
@app_commands.choices(
    mesa=[
        app_commands.Choice(name="Mesa Principal", value="mesa-principal"),
        app_commands.Choice(name="Mesa Desordem", value="mesa-desordem")
    ]
)
async def togglesessao(interaction: discord.Interaction, mesa: str):
    fake_ctx = await commands.Context.from_interaction(interaction)
    await togglesessao_logic(fake_ctx, mesa)

# Inicia o bot
bot.run(TOKEN)
