import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
import json
import yt_dlp
import tempfile

# Configuração do bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
prefix = 'foa!'
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
COOKIE = os.getenv("YTDL_COOKIE")
luky = 767015394648915978
usuarios_autorizados = [luky]
updateyn = 0

def json_to_netscape(cookies_json_str):
    """
    Converte uma string JSON contendo cookies (lista de dicionários)
    para o formato Netscape, que o yt-dlp espera.
    """
    import json
    cookies = json.loads(cookies_json_str)
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in cookies:
        domain = cookie.get("domain", "")
        # Se hostOnly for False, queremos permitir subdomínios (TRUE); caso contrário, FALSE.
        flag = "TRUE" if not cookie.get("hostOnly", False) else "FALSE"
        path = cookie.get("path", "/")
        secure = "TRUE" if cookie.get("secure", False) else "FALSE"
        # expirationDate deve ser um número inteiro (em epoch). Se não existir, usamos 0.
        expiration = str(int(cookie.get("expirationDate", 0)))
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        # Formato: domain, flag, path, secure, expiration, name, value
        line = f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}"
        lines.append(line)
    return "\n".join(lines)
def baixar_audio(url):
    # Converte o JSON (do secret) para o formato Netscape
    netscape_cookie_str = json_to_netscape(COOKIE)
    
    # Cria um arquivo temporário para os cookies convertidos
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as temp_file:
        temp_file.write(netscape_cookie_str)
        temp_cookie_path = temp_file.name

    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'cookiefile': temp_cookie_path,  # arquivo temporário com cookies
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            arquivo = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
    finally:
        # Remove o arquivo temporário após o download
        os.remove(temp_cookie_path)
    
    return arquivo, info.get('title', 'Desconhecido')

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

REACTIONS = {
    "bem-vindo": ["👋", "🎉"],  # Reage com 👋 e 🎉 a mensagens contendo "bem-vindo"
    "importante": ["⚠️", "📢"],  # Reage com ⚠️ e 📢 a mensagens contendo "importante"
    "parabéns": ["🥳", "🎊"],  # Reage com 🥳 e 🎊 a mensagens contendo "parabéns"
    "obrigado": ["🙏"],  # Reage com 🙏 a mensagens contendo "obrigado"
}
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignora mensagens de bots

    for keyword, emojis in REACTIONS.items():
        if keyword in message.content.lower():
            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except discord.Forbidden:
                    print(f"❌ Não tenho permissão para reagir a mensagens em {message.channel}")

    await bot.process_commands(message)  # Permite que outros comandos ainda funcionem

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

# Executar comandos através de DMs
@bot.tree.command(name="executar_comando", description="Executa comandos específicos em DMs, com escolha do servidor")
@app_commands.describe(
    comando="Comando que deseja executar",
    servidor="(Opcional) ID do servidor onde o comando será executado",
    parametros="(Opcional) Parâmetros do comando, separados por vírgula (ex: mesa=Mesa Principal, user=123456789)"
)
async def executar_comando(
    interaction: discord.Interaction,
    comando: str,
    servidor: str = None,
    parametros: str = None  # Parâmetros opcionais
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
            guild = bot.get_guild(int(servidor))  # Obtém o servidor pelo ID
            if not guild:
                return await interaction.response.send_message(f"🚫 O servidor com ID {servidor} não foi encontrado.", ephemeral=True)

            # Buscando o comando correspondente
            comando_obj = bot.get_command(comando.lower())  # O nome do comando é convertido para minúsculo

            if comando_obj:
                try:
                    # Criando o contexto para invocar o comando
                    context = await bot.get_context(interaction)  # Criando contexto corretamente
                    context.guild = guild  # Definindo o servidor

                    # Convertendo os parâmetros para uma lista de argumentos
                    args = []
                    kwargs = {}

                    if parametros:
                        parametros_lista = parametros.split(",")  # Divide os parâmetros por vírgula
                        for param in parametros_lista:
                            chave_valor = param.strip().split("=")  # Divide chave=valor
                            if len(chave_valor) == 2:
                                chave, valor = chave_valor
                                kwargs[chave.strip()] = valor.strip()
                            else:
                                # Adiciona o parâmetro como um argumento posicional se não for chave=valor
                                args.append(param.strip())

                    # Invoca o comando com os parâmetros passados corretamente
                    await comando_obj(context, *args, **kwargs)

                    return await interaction.response.send_message(f"✅ O comando `{comando}` foi executado no servidor {guild.name}.")
                
                except Exception as e:
                    return await interaction.response.send_message(f"🚫 Ocorreu um erro ao tentar executar o comando: {e}", ephemeral=True)
            else:
                return await interaction.response.send_message(f"🚫 Comando `{comando}` não encontrado.", ephemeral=True)

        else:
            return await interaction.response.send_message("🚫 Nenhum servidor foi especificado para executar o comando.", ephemeral=True)
    
    else:
        return await interaction.response.send_message("🚫 Este comando só pode ser executado em DMs.", ephemeral=True)

@bot.tree.command(name="tocar", description="Toca uma música do YouTube no canal de voz.")
@app_commands.describe(musica="Nome ou link da música do YouTube")
async def tocar(interaction: discord.Interaction, musica: str):
    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.response.send_message("🚫 Você precisa estar em um canal de voz para usar este comando!", ephemeral=True)

    canal = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if not voice_client:
        voice_client = await canal.connect()

    await interaction.response.send_message(f"🔍 Buscando: **{musica}**...")

    # Se for um link, usa direto, senão faz uma busca no YouTube
    if "youtube.com" in musica or "youtu.be" in musica:
        url = musica
    else:
        with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True}) as ydl:
            info = ydl.extract_info(f"ytsearch:{musica}", download=False)['entries'][0]
            url = info['url']

    # Baixar e tocar a música
    arquivo, titulo = baixar_audio(url)
    voice_client.stop()
    voice_client.play(discord.FFmpegPCMAudio(arquivo), after=lambda e: print(f"Música terminada: {e}"))

    await interaction.edit_original_response(content=f"🎶 Tocando agora: **{titulo}**!")
@bot.tree.command(name="pausar", description="Pausa a música atual.")
async def pausar(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("⏸️ Música pausada!")
    else:
        await interaction.response.send_message("🚫 Não há nenhuma música tocando!", ephemeral=True)
@bot.tree.command(name="retomar", description="Retoma a música pausada.")
async def retomar(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("▶️ Música retomada!")
    else:
        await interaction.response.send_message("🚫 Não há nenhuma música pausada!", ephemeral=True)
@bot.tree.command(name="parar", description="Para a música e limpa a fila.")
async def parar(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client:
        voice_client.stop()
        await interaction.response.send_message("⏹️ Música parada!")
    else:
        await interaction.response.send_message("🚫 Não há nada tocando!", ephemeral=True)
@bot.tree.command(name="sair", description="Faz o bot sair do canal de voz.")
async def sair(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("👋 Saindo do canal de voz!")
    else:
        await interaction.response.send_message("🚫 Não estou em um canal de voz!", ephemeral=True)

# Inicia o bot
bot.run(TOKEN)