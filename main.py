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
usuarios_autorizados = [123456789012345678, 987654321098765432]
updateyn = 0

# Caminho do arquivo para salvar o estado
state_file = "bot_state.json"

if not os.path.exists(state_file):
    # Se não existir, cria com o estado inicial
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump({'sessaoclosedopen': 0}, f, ensure_ascii=False, indent=4)

# Função para salvar o estado no arquivo
def save_state(state):
    try:
        with open('bot_state.json', 'w') as file:
            json.dump(state, file)
    except FileNotFoundError:
        return {"sessaoclosedopen": 0}  # Retorna o estado padrão se o arquivo não existir

# Função para carregar o estado do arquivo
# Função para carregar o estado do arquivo
def load_state():
    try:
        with open(state_file, 'r') as f:
            bot_state = json.load(f)
            # Carregar o estado para a variável
            return bot_state  # Agora retorna o estado carregado
    except FileNotFoundError:
        # Se o arquivo não for encontrado, inicializa o estado com valores default
        return {'sessaoclosedopen': 0}  # Retorna um estado padrão, caso o arquivo não exista

# Carregar o estado inicial
state = load_state()
sessaoclosedopen = state["sessaoclosedopen"]

# Nome do arquivo Markdown
arquivo_md = "changelog.md"

# Abrir o arquivo em modo leitura
with open(arquivo_md, "r", encoding="utf-8") as arquivo:
    conteudo = arquivo.read()  # Lê todo o conteúdo do arquivo e coloca na variável
with open('data/avisos_sessao.json', 'r', encoding='utf-8') as file:
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

sessaoclosedopen = 0

# Lógica para iniciar a sessão
async def togglesessao_logic(ctx, mesa: str, interaction: discord.Interaction = None):
    global sessaoclosedopen
    canalAviso = bot.get_channel(1319306482470228020)

    mesa_principal_cargo = 1319301421216301179
    mesa_desordem_cargo = 1320516709089673237
    dev = 1316481758056808558

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
                await interaction.response.send_message(f"<@&{dev}> Sessão iniciada na {mesa}!")  # Responde a interação
            else:
                await ctx.send(f"<@&{dev}> Sessão iniciada na {mesa}!")  # Para comandos prefixados
            sessaoclosedopen = 1
            save_state({"sessaoclosedopen": sessaoclosedopen})
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
                await interaction.response.send_message(f"<@&{dev}> Sessão encerrada na {mesa}!")  # Responde a interação
            else:
                await ctx.send(f"<@&{dev}> Sessão encerrada na {mesa}!")  # Para comandos prefixados
            sessaoclosedopen = 0
            save_state({"sessaoclosedopen": sessaoclosedopen})
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

# 🔊 Comando para desmutar membros
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

@bot.tree.command(name="executar_comando", description="Executa comandos específicos em DMs, com escolha do servidor")
@app_commands.describe(
    comando="Comando que deseja executar",
    servidor="(Opcional) ID do servidor onde o comando será executado"
)
async def executar_comando(
    interaction: discord.Interaction,
    comando: str,
    servidor: str = None
):
    # Verifica se a interação foi realizada via DM
    if isinstance(interaction.channel, discord.DMChannel):
        # Verifica se o usuário é autorizado
        if interaction.user.id not in usuarios_autorizados:
            return await interaction.response.send_message("🚫 Você não tem permissão para usar esse comando!", ephemeral=True)
        
        # Se o parâmetro de servidor não for especificado, tenta obter o servidor padrão do usuário
        if not servidor:
            servidor = interaction.guild.id if interaction.guild else None
        
        if servidor:
            guild = bot.get_guild(int(servidor))  # Obtemos o servidor pelo ID
            if not guild:
                return await interaction.response.send_message(f"🚫 O servidor com ID {servidor} não foi encontrado.", ephemeral=True)

            # Verifica se o comando solicitado existe
            if comando.lower() == "mutar":
                # Realiza a ação de mutar em um canal do servidor
                canal = guild.voice_channels[0]  # Exemplo de escolha do canal de voz, você pode personalizar
                await canal.edit(mute=True)
                return await interaction.response.send_message(f"🔇 O comando `mutar` foi executado no servidor {guild.name}.")
            # Adicione mais comandos aqui conforme necessário
            else:
                return await interaction.response.send_message(f"🚫 O comando '{comando}' não é reconhecido ou não está implementado.", ephemeral=True)

        else:
            return await interaction.response.send_message("🚫 Nenhum servidor foi especificado para executar o comando.", ephemeral=True)
    
    else:
        return await interaction.response.send_message("🚫 Este comando só pode ser executado em DMs.", ephemeral=True)

# Inicia o bot
bot.run(TOKEN)
print(sessaoclosedopen)