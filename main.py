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

# ID do cargo que será verificado
TARGET_ROLE_ID = 1318721735264309278  # Substitua pelo ID do cargo específico

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
async def on_ready():
    print(f'Bot conectado como {bot.user}, command prefix: {prefix}')
    print("Sincronizando comandos de barra...")

    for guild in bot.guilds:
        try:
            print(f"Sincronizando comandos para o servidor: {guild.name} (ID: {guild.id})")
            await bot.tree.sync(guild=guild)
            print(f"✅ Comandos sincronizados com sucesso para o servidor: {guild.name}")
        except Exception as e:
            print(f"❌ Falha ao sincronizar comandos no servidor {guild.name}: {e}")

    print("✔️ Sincronização concluída.")

# Lógica para o comando "comendo"
async def comendo_logic(member: discord.Member):
    try:
        # Verifica se o usuário possui o cargo específico
        target_role = discord.utils.get(member.guild.roles, id=TARGET_ROLE_ID)
        if target_role not in member.roles:
            return f"❌ **{member.mention} não possui o cargo necessário!**"

        # Atualiza o nickname do usuário adicionando "[COMENDO]"
        original_name = member.display_name
        new_name = f"{original_name} [COMENDO]"

        if len(new_name) > 32:  # Discord limita os nomes a 32 caracteres
            return f"❌ **O novo nome ultrapassa o limite de 32 caracteres!**"

        await member.edit(nick=new_name)
        return f"✅ **O nome de {member.mention} foi atualizado para '{new_name}'**"

    except discord.Forbidden:
        return "❌ **Não tenho permissão para alterar o nickname deste usuário!**"
    except Exception as e:
        return f"❌ **Ocorreu um erro: {e}**"

# Comando prefixado "comendo"
@bot.command(name="comendo")
async def comendo(ctx, member: discord.Member):
    result = await comendo_logic(member)
    await ctx.send(result)

# Comando de barra "/comendo"
@bot.tree.command(name="comendo", description="Adiciona '[COMENDO]' ao nome de um usuário se ele tiver o cargo necessário.")
@app_commands.describe(member="O membro cujo nome será atualizado")
async def comendo(interaction: discord.Interaction, member: discord.Member):
    result = await comendo_logic(member)
    await interaction.response.send_message(result)

# Inicia o bot
bot.run(TOKEN)
