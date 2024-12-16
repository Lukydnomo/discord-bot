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

# Inicializa o bot com comandos prefixados
bot = commands.Bot(command_prefix=prefix, intents=intents)

# Cria um cliente para os comandos de barra
tree = app_commands.CommandTree(bot)

# Evento que confirma que o bot está online e sincroniza os comandos de barra
@bot.event
async def on_ready():
    await tree.sync()  # Sincroniza os comandos de barra com a API do Discord
    print(f'Bot conectado como {bot.user}, command prefix: {prefix}')
    print("Slash commands sincronizados!")

# Comando prefixado "punir" (foa!punir)
@bot.command()
async def punir(ctx, member: discord.Member, punishChannel: discord.VoiceChannel):
    await punir_logic(ctx, member, punishChannel)

# Comando de barra "/punir"
@tree.command(name="punir", description="Pune um membro movendo-o para um canal de voz específico.")
@app_commands.describe(
    member="Membro a ser punido",
    punish_channel="Canal de voz onde o membro será movido"
)
async def slash_punir(interaction: discord.Interaction, member: discord.Member, punish_channel: discord.VoiceChannel):
    # Converte o Interaction em um formato semelhante ao ctx do comando prefixado
    fake_ctx = await commands.Context.from_interaction(interaction)
    await punir_logic(fake_ctx, member, punish_channel)

# Função compartilhada pela lógica dos comandos
async def punir_logic(ctx, member: discord.Member, punishChannel: discord.VoiceChannel):
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
        await member.move_to(punishChannel)
        await ctx.send(f'✅ **{member.mention} foi punido e movido para {punishChannel.name}**')

        # Desativa a permissão de conectar a outros canais
        for channel in ctx.guild.voice_channels:
            if channel != punishChannel:
                await channel.set_permissions(member, connect=False)

        # Espera 60 segundos
        await asyncio.sleep(60)

        # Restaura as permissões de conexão
        for channel in ctx.guild.voice_channels:
            if channel != punishChannel:
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

# Inicia o bot
bot.run(TOKEN)
