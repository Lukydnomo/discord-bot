import discord
from discord.ext import commands
import asyncio
import os

# Configuração do bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
prefix = 'foa!'
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

bot = commands.Bot(command_prefix=prefix, intents=intents)

# Evento que confirma que o bot está online
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}, command prefix: {prefix}')

# Comando de punição
@bot.command()
async def punir(ctx, member: discord.Member, punishChannel: discord.VoiceChannel):
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
