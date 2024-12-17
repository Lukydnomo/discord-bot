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

# Criação do bot com intents
bot = commands.Bot(command_prefix=prefix, intents=intents)

# Banco de dados simples para armazenar o saldo de moedas dos jogadores (armazena como dicionário)
moedas_db = {}

# Taxa de conversão entre as moedas
conversao = {
    "dragao_ouro": 100000,  # Cada Dragão de Ouro vale 10 moedas sagradas (100000 cobre menor)
    "moeda_sagrada": 10000,
    "ouro": 1000,
    "prata": 100,
    "pena": 10,
    "cobre": 1,
    "cobre_menor": 0.1  # Supondo que cobre menor seja a menor unidade de moeda
}

# Função para converter entre as moedas
def converter_moeda(valor, moeda_origem, moeda_destino):
    # Convertendo para cobre menor (a unidade mais baixa)
    valor_em_cobre_menor = valor * conversao[moeda_origem]
    
    # Convertendo para a moeda de destino
    valor_convertido = valor_em_cobre_menor / conversao[moeda_destino]
    
    return valor_convertido

# Função para adicionar moedas ao jogador
async def adicionar_moeda(ctx, jogador: discord.Member, quantidade: float, tipo: str):
    if jogador.id not in moedas_db:
        moedas_db[jogador.id] = {
            "dragao_ouro": 0,
            "moeda_sagrada": 0,
            "ouro": 0,
            "prata": 0,
            "pena": 0,
            "cobre": 0,
            "cobre_menor": 0
        }

    moedas_db[jogador.id][tipo] += quantidade
    await ctx.send(f"✅ **{jogador.mention}** agora tem **{quantidade} {tipo.replace('_', ' ')}**!")

# Função para consultar o saldo de moedas do jogador
async def consultar_moeda(ctx, jogador: discord.Member):
    if jogador.id not in moedas_db:
        moedas_db[jogador.id] = {
            "dragao_ouro": 0,
            "moeda_sagrada": 0,
            "ouro": 0,
            "prata": 0,
            "pena": 0,
            "cobre": 0,
            "cobre_menor": 0
        }

    saldo = moedas_db[jogador.id]
    saldo_msg = f"**{jogador.name}'s Saldo de Moedas:**\n"
    for moeda, quantidade in saldo.items():
        saldo_msg += f"{moeda.replace('_', ' ').title()}: {quantidade}\n"
    
    await ctx.send(saldo_msg)

# Função para remover moedas do jogador
async def remover_moeda(ctx, jogador: discord.Member, quantidade: float, tipo: str):
    if jogador.id not in moedas_db or moedas_db[jogador.id][tipo] < quantidade:
        await ctx.send(f"❌ **{jogador.mention}** não tem moedas suficientes!")
        return
    
    moedas_db[jogador.id][tipo] -= quantidade
    await ctx.send(f"✅ **{jogador.mention}** perdeu **{quantidade} {tipo.replace('_', ' ')}**!")

# Evento on_ready que sincroniza os comandos de barra
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

# Comando prefixado "moeda" para adicionar moedas
@bot.command(name="moeda")
async def moeda(ctx, jogador: discord.Member, quantidade: float, tipo: str):
    if tipo not in conversao:
        await ctx.send("❌ **Tipo de moeda inválido!** Use 'dragao_ouro', 'moeda_sagrada', 'ouro', 'prata', 'pena', 'cobre' ou 'cobre_menor'.")
        return
    await adicionar_moeda(ctx, jogador, quantidade, tipo)

# Comando prefixado "consultar" para ver saldo de moedas
@bot.command(name="consultar")
async def consultar(ctx, jogador: discord.Member):
    await consultar_moeda(ctx, jogador)

# Comando prefixado "converter" para converter moedas
@bot.command(name="converter")
async def converter(ctx, jogador: discord.Member, valor: float, moeda_origem: str, moeda_destino: str):
    if moeda_origem not in conversao or moeda_destino not in conversao:
        await ctx.send("❌ **Tipo de moeda inválido!** Use 'dragao_ouro', 'moeda_sagrada', 'ouro', 'prata', 'pena', 'cobre' ou 'cobre_menor'.")
        return

    valor_convertido = converter_moeda(valor, moeda_origem, moeda_destino)
    await ctx.send(f"✅ **{jogador.mention}** converteu **{valor} {moeda_origem.replace('_', ' ')}** para **{valor_convertido:.2f} {moeda_destino.replace('_', ' ')}**.")

# Inicia o bot
bot.run(TOKEN)
