import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os

# Configuração do bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
prefix = 'foa!'
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=prefix, intents=intents)

    # Método para sincronizar os comandos
    async def setup_hook(self):
        await self.tree.sync()  # Sincroniza comandos globalmente
        print("✅ Comandos sincronizados globalmente!")

bot = MyBot()

# Evento: Bot pronto
@bot.event
# Função de lógica para o comando "punir" (reutilizável para prefixado e slash command)
async def punir_logic(ctx, member: discord.Member, punish_channel: discord.VoiceChannel, duration: int = 1):
    try:
        # Obtém o cargo mais alto do autor, do bot e do membro
        author_top_role = ctx.author.top_role
        bot_top_role = ctx.guild.me.top_role
        member_top_role = member.top_role

        # Verifica se o autor tem um cargo superior ao bot
        if author_top_role <= bot_top_role:
            await ctx.send("❌ **Você precisa ter um cargo superior ao meu para usar este comando!**")
            return

        # Verifica se o autor está em um canal de voz
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ **Você precisa estar em um canal de voz para usar este comando!**")
            return

        # Salva o canal original do membro
        original_channel = member.voice.channel if member.voice else None

        # Move o membro para o canal de punição
        await member.move_to(punish_channel)
        await ctx.send(f'✅ **{member.mention} foi punido e movido para {punish_channel.name} por {duration} minutos**')

        # Desativa a permissão de conectar a outros canais
        for channel in ctx.guild.voice_channels:
            if channel != punish_channel:
                await channel.set_permissions(member, connect=False)

        # Espera 60 segundos
        await asyncio.sleep(duration * 60)

        # Restaura as permissões de conexão
        for channel in ctx.guild.voice_channels:
            if channel != punish_channel:
                await channel.set_permissions(member, overwrite=None)

        # Move o membro de volta para o canal original (se possível)
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


# Evento on_ready que sincroniza os comandos de barra
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}, command prefix: {prefix}')
    print("Sincronizando comandos de barra...")

    # Pega automaticamente todos os servidores onde o bot está presente
    for guild in bot.guilds:
        try:
            print(f"Sincronizando comandos para o servidor: {guild.name} (ID: {guild.id})")
            await bot.tree.sync(guild=guild)
            print(f"✅ Comandos sincronizados com sucesso para o servidor: {guild.name}")
        except Exception as e:
            print(f"❌ Falha ao sincronizar comandos no servidor {guild.name}: {e}<>")

    print("✔️ Sincronização concluída.")

    activity = discord.Activity(
        type=discord.ActivityType.playing,  # Pode ser "playing", "streaming", "listening", "watching"
        name="Punindo membros",  # Nome do que o bot está fazendo
        details="Punindo jogadores no servidor",  # Descrição adicional
        large_image="punish",  # Nome do asset do image (uploadado no Developer Portal)
        large_text="Punindo membros",  # Texto que aparece ao passar o mouse sobre a imagem
        small_image="punish",  # Nome do asset do image (uploadado no Developer Portal)
        small_text="Comando ativo",  # Texto que aparece ao passar o mouse sobre a pequena imagem
    )

    await bot.change_presence(activity=activity)


# Comando prefixado "punir"
@bot.command(name="punir")
async def punir(ctx, member: discord.Member, punish_channel: discord.VoiceChannel, duration: int = 1):
    await punir_logic(ctx, member, punish_channel, duration)


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

# Inicia o bot
bot.run(TOKEN)
