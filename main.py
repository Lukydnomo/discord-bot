import discord
from discord.ext import commands
import asyncio
import os

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
prefix = 'foa!'
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

bot = commands.Bot(command_prefix=prefix, intents=intents)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}, command prefix: {prefix}')

@bot.command()
async def punir(ctx, member: discord.Member, punishChannel: discord.VoiceChannel):
    # Obtém o cargo mais alto do autor e do bot
    author_top_role = ctx.author.top_role
    bot_top_role = ctx.guild.me.top_role  # Cargo mais alto do bot
    member_top_role = member.top_role  # Cargo mais alto do membro a ser punido

    # Verifica se o autor tem um cargo superior ao do bot
    if author_top_role.position <= bot_top_role.position and member_top_role.position:
        await ctx.send("Você precisa ter um cargo superior ao meu para usar este comando!")
    else:
        author_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not author_channel:
            await ctx.send("Você não está em um canal de voz!")
        else:
            try:
                # Desabilita a permissão de conectar a outros canais de voz
                for channel in ctx.guild.voice_channels:
                    if channel != punishChannel:
                        await channel.set_permissions(member, connect=False)

                # Move o membro para o punishChannel
                await member.move_to(punishChannel)
                await ctx.send(f'{member.mention} foi punido e movido para {punishChannel.name}')

                # Espera 60 segundos
                await asyncio.sleep(60)

                # Restaura as permissões para que o membro possa conectar aos outros canais de voz
                for channel in ctx.guild.voice_channels:
                    if channel != punishChannel:
                        await channel.set_permissions(member, connect=True)

                # Move o membro de volta para o canal original
                await member.move_to(author_channel)
                await ctx.send(f'{member.mention} foi movido de volta para {author_channel.name}')

            except Exception as e:
                await ctx.send(f'Erro ao punir: {str(e)}')
bot.run(TOKEN)
