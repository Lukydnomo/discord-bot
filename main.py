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

# Sistema de moedas
moedas = {
    'dragao_ouro': 100000,
    'moeda_sagrada': 10000,
    'ouro': 1000,
    'pratas': 100,
    'penas': 10,
    'cobre': 1,
    'cobre_menor': 0.1
}

# Banco de dados de moedas (pode ser uma base de dados real, mas para simplificação usamos um dicionário)
saldo_moedas = {}

# Função para converter moedas automaticamente
def converter_moeda(quantidade):
    valores = list(moedas.items())
    resultado = {}
    
    for i in range(len(valores) - 1, -1, -1):
        tipo, valor = valores[i]
        if quantidade >= valor:
            quantidade -= valor
            if tipo not in resultado:
                resultado[tipo] = 1
            else:
                resultado[tipo] += 1
    return resultado

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
            print(f"❌ Falha ao sincronizar comandos no servidor {guild.name}: {e}")

    # Certifique-se de sincronizar também o comando de barra /moeda
    await bot.tree.sync()

    print("✔️ Sincronização concluída.")


# Comando de barra "/moeda" para ver o saldo
@bot.tree.command(name="moeda", description="Veja seu saldo de moedas e a conversão automática.")
async def slash_moeda(interaction: discord.Interaction):
    usuario = interaction.user
    saldo = saldo_moedas.get(usuario.id, 0)

    # Converte a quantidade de moedas para as várias denominações possíveis
    saldo_convertido = converter_moeda(saldo)

    # Formata a resposta
    resposta = f"Saldo de {usuario.name}:\n"
    for tipo, qtd in saldo_convertido.items():
        moeda_nome = tipo.replace('_', ' ').title()
        resposta += f"**{moeda_nome}:** {qtd} ({moedas[tipo] * qtd} cada)\n"

    await interaction.response.send_message(resposta)


# Comando prefixado "adicionar_moeda"
@bot.command(name="adicionar_moeda")
async def adicionar_moeda(ctx, valor: float):
    # Adiciona moedas ao saldo do usuário
    usuario = ctx.author
    if usuario.id not in saldo_moedas:
        saldo_moedas[usuario.id] = 0
    saldo_moedas[usuario.id] += valor
    await ctx.send(f"Você recebeu {valor} moedas. Saldo atual: {saldo_moedas[usuario.id]} moedas.")


# Comando prefixado "punir"
@bot.command(name="punir")
async def punir(ctx, member: discord.Member, punish_channel: discord.VoiceChannel):
    await punir_logic(ctx, member, punish_channel)


# Função de lógica para o comando "punir" (reutilizável para prefixado e slash command)
async def punir_logic(ctx, member: discord.Member, punish_channel: discord.VoiceChannel):
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
        await ctx.send(f'✅ **{member.mention} foi punido e movido para {punish_channel.name}**')

        # Desativa a permissão de conectar a outros canais
        for channel in ctx.guild.voice_channels:
            if channel != punish_channel:
                await channel.set_permissions(member, connect=False)

        # Espera 60 segundos
        await asyncio.sleep(60)

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


# Comando de barra "/punir"
@bot.tree.command(name="punir", description="Pune um membro movendo-o para um canal de voz específico.")
@app_commands.describe(
    member="Membro a ser punido",
    punish_channel="Canal de voz onde o membro será movido"
)
async def slash_punir(interaction: discord.Interaction, member: discord.Member, punish_channel: discord.VoiceChannel):
    fake_ctx = await commands.Context.from_interaction(interaction)  # Converte interaction para ctx
    await punir_logic(fake_ctx, member, punish_channel)


# Inicia o bot
bot.run(TOKEN)
