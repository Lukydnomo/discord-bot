import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import json
import random
import re
import requests
from base64 import b64decode, b64encode
import aiohttp
import unidecode
from datetime import datetime, timezone, timedelta

# Configuração do bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
prefix = 'foa!'
DISCORDTOKEN = os.getenv("DISCORD_BOT_TOKEN")
GITHUBTOKEN = os.getenv("DATABASE_TOKEN")
luky = 767015394648915978
usuarios_autorizados = [luky]
updateyn = 0
github_repo = "Lukydnomo/discord-bot"
json_file_path = "database.json"
NOME_ORIGINAL = "FranBOT"
CAMINHO_AVATAR_ORIGINAL = "assets/images/FranBOT-Logo.png"

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=prefix, intents=intents)

    # Sincroniza comandos quando o bot inicia
    async def setup_hook(self):
        await self.tree.sync()  # Sincroniza comandos globalmente
        print("✅ Comandos sincronizados globalmente!")

bot = MyBot()

# Nome do arquivo Markdown
arquivo_md = "changelog.md"

# Abrir o arquivo em modo leitura
with open(arquivo_md, "r", encoding="utf-8") as arquivo:
    conteudo = arquivo.read()  # Lê todo o conteúdo do arquivo e coloca na variável

# Escolhe usuário aleatório
def randomuser():
    for guild in bot.guilds:  # Itera sobre os servidores onde o bot está
        members = [member for member in guild.members if not member.bot]  # Filtra membros não-bots
        
        if members:
            return random.choice(members)  # Retorna um membro aleatório
    
    return "fudeu nego"  # Retorno caso não haja membros válidos
# Função para salvar a mensagem deletada no arquivo JSON
async def save_deleted_message(message):
    data = get_file_content()

    deleted_message_data = {
        "author": message.author.name,
        "content": message.content,
        "timestamp": str(message.created_at),
        "channel_id": message.channel.id
    }

    # Garante que "deleted_messages" é uma lista
    if "deleted_messages" not in data or not isinstance(data["deleted_messages"], list):
        data["deleted_messages"] = []

    # Adicionando a mensagem deletada ao banco de dados
    data["deleted_messages"].append(deleted_message_data)

    # Atualizando o arquivo com a nova mensagem deletada
    await save("deleted_messages", data)
# Função para verificar se passaram 5 minutos e reenviar a mensagem
async def check_and_resend_loop():
    # Canal de logs onde erros serão reportados
    error_log_channel_id = 1317580138262695967  # Substitua pelo ID do canal de log de erros
    error_log_channel = bot.get_channel(error_log_channel_id)

    while True:
        data = get_file_content()

        if not data or "deleted_messages" not in data or "deleted_messages" not in data["deleted_messages"]:
            if error_log_channel:
                await error_log_channel.send("🔍 Nenhuma mensagem deletada encontrada.")
            await asyncio.sleep(10)

        deleted_messages = data["deleted_messages"]["deleted_messages"]
        now = datetime.now(timezone.utc)

        for deleted_message_data in deleted_messages:
            if not deleted_message_data:
                continue

            if isinstance(deleted_message_data, str):
                try:
                    deleted_message_data = json.loads(deleted_message_data)
                except json.JSONDecodeError:
                    if error_log_channel:
                        await error_log_channel.send(f"⚠️ Erro ao decodificar JSON da mensagem deletada: {deleted_message_data}")
                    continue

            if "timestamp" not in deleted_message_data or "channel_id" not in deleted_message_data:
                if error_log_channel:
                    await error_log_channel.send(f"⚠️ Mensagem deletada sem timestamp ou channel_id: {deleted_message_data}")
                continue

            # Debug: printar o timestamp
            print(f"⏳ Timestamp da mensagem: {deleted_message_data['timestamp']}")

            # Ajustar o timestamp removendo o sufixo se presente
            timestamp_str = deleted_message_data["timestamp"]
            if timestamp_str.endswith("+00:00"):
                timestamp_str = timestamp_str.replace("+00:00", "").strip()

            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    if error_log_channel:
                        await error_log_channel.send(f"❌ Erro ao converter timestamp para a mensagem: {deleted_message_data}")
                    continue

            time_diff = (now - timestamp).total_seconds() / 60
            print(f"⏳ Tempo decorrido: {time_diff} minutos")

            if 5 <= time_diff < 7:
                channel_id = deleted_message_data["channel_id"]
                channel = bot.get_channel(channel_id)
                if channel is None:
                    if error_log_channel:
                        await error_log_channel.send(f"❌ Erro: Canal {channel_id} não encontrado.")
                    continue

                print(f"📩 Enviando mensagem deletada no canal {channel_id}...")
                try:
                    await channel.send(f"Ah, vocês lembram quando {deleted_message_data['author']} mandou isso? '{deleted_message_data['content']}'")
                except Exception as e:
                    if error_log_channel:
                        await error_log_channel.send(f"❌ Erro ao tentar enviar mensagem no canal {channel_id}: {e}")
                    continue

                # Remove a mensagem do JSON
                data["deleted_messages"]["deleted_messages"] = [msg for msg in deleted_messages if msg != deleted_message_data]
                print(f"✅ Mensagem removida do banco de dados.")
                await save("deleted_messages", data)

        await asyncio.sleep(10)

# Database System
async def stop_github_actions():
    run_id = os.getenv('RUN_ID')
    
    if not run_id:
        print("Erro: run_id não encontrado.")
        return
    
    url = f"https://api.github.com/repos/{github_repo}/actions/runs/{run_id}/cancel"
    headers = {"Authorization": f"token {GITHUBTOKEN}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as response:
            if response.status == 202:
                print("Instância do GitHub Actions finalizada com sucesso.")
            else:
                print(f"Falha ao finalizar instância: {response.status}, {await response.text()}")
def get_file_content():
    url = f"https://api.github.com/repos/{github_repo}/contents/{json_file_path}"
    headers = {"Authorization": f"token {GITHUBTOKEN}"}
    response = requests.get(url, headers=headers).json()

    if "content" in response:
        try:
            return json.loads(b64decode(response["content"]).decode())
        except json.JSONDecodeError:
            return {}  # Retorna um dicionário vazio se houver erro na decodificação
    elif response.get("message") == "Not Found":
        return {}  # Retorna um dicionário vazio se o arquivo não existir ainda
    else:
        print(f"Erro ao buscar o arquivo: {response}")  # Para depuração
        return {}
def update_file_content(data):
    url = f"https://api.github.com/repos/{github_repo}/contents/{json_file_path}"
    headers = {"Authorization": f"token {GITHUBTOKEN}"}
    current_data = requests.get(url, headers=headers).json()
    
    sha = current_data.get("sha", "") if "sha" in current_data else None
    new_content = b64encode(json.dumps(data, indent=4).encode()).decode()
    commit_message = "Atualizando banco de dados"

    payload = {"message": commit_message, "content": new_content}
    if sha:
        payload["sha"] = sha  # Apenas se o arquivo já existir

    requests.put(url, headers=headers, json=payload)
async def save(name, value):
    data = get_file_content()
    if name in data:
        if isinstance(data[name], list):
            data[name].append(value)
        else:
            data[name] = [data[name], value]
    else:
        data[name] = value
    update_file_content(data)

    # Aguardar 35 segundos antes de parar o bot
    await asyncio.sleep(35)
    
    # Finalizar a instância do bot no GitHub Actions
    await stop_github_actions()
def load(name):
    data = get_file_content()
    return data.get(name, None)

# Castigo
async def castigar_automatico(member: discord.Member, tempo: int):
    # Função para aplicar Time-Out automaticamente sem usar comandos.
    try:
        # Usando datetime.timedelta para definir a duração do Time-Out
        duration = timedelta(seconds=tempo)
        until_time = datetime.now() + duration  # Calcula o tempo futuro do Time-Out

        # Aplica o Time-Out até o momento calculado
        await member.timeout(until=until_time, reason="Castigo automático")
        print(f'{member.mention} foi colocado em Time-Out por {tempo} segundos devido a uma condição.')
    except discord.DiscordException as e:
        print(f'Ocorreu um erro ao tentar colocar {member.mention} em Time-Out: {e}')

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
    await asyncio.sleep(3)
    updatechannel = bot.get_channel(1319356880627171448)
    
    #bot.loop.create_task(check_and_resend_loop())

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

# Função para processar a rolagem de dados
def rolar_dado(expressao, detalhado=True):
    if not detalhado:
        # Comportamento antigo: apenas substitui e avalia a expressão
        def substituir(match):
            qtd, faces = match.groups()
            qtd = int(qtd) if qtd else 1
            faces = int(faces)
            return str(sum(random.randint(1, faces) for _ in range(qtd)))
        expr_mod = re.sub(r'(\d*)d(\d+)', substituir, expressao)
        try:
            resultado = eval(expr_mod)
        except:
            return None
        return {"resultado": resultado, "resultadoWOutEval": expr_mod, "detalhado": False}
    else:
        # Novo comportamento: captura os resultados individuais de cada grupo de dados
        detalhes = []  # Armazena os resultados individuais de cada grupo
        def substituir(match):
            qtd_str, faces_str = match.groups()
            qtd = int(qtd_str) if qtd_str else 1
            faces = int(faces_str)
            # Rola cada dado individualmente
            rolagens = [random.randint(1, faces) for _ in range(qtd)]
            # Armazena a lista ordenada do maior para o menor
            detalhes.append(sorted(rolagens, reverse=True))
            # Retorna a soma para a avaliação matemática
            return str(sum(rolagens))
        expr_mod = re.sub(r'(\d*)d(\d+)', substituir, expressao)
        try:
            resultado = eval(expr_mod)
        except:
            return None
        # Se houver apenas um grupo de dados, usamos o resultado dele; caso contrário, juntamos os resultados
        if len(detalhes) == 1:
            breakdown = str(detalhes[0])
            # Extrai o grupo de dados original (por exemplo, "5d5")
            m = re.search(r'(\d*d\d+)', expressao)
            dice_group = m.group(1) if m else expressao
        else:
            breakdown = " + ".join(str(lst) for lst in detalhes)
            dice_group = expressao
        return {
            "resultado": resultado,
            "resultadoWOutEval": breakdown,
            "dice_group": dice_group,
            "detalhado": True
        }
# Comando de rolagem de dado (/rolar)
@bot.tree.command(name="rolar", description="Rola dados no formato XdY com operações matemáticas")
@app_commands.describe(expressao="Exemplo: 2d6+2, 4d10/2, 5#d5+5")
async def rolar(interaction: discord.Interaction, expressao: str):
    if "#" in expressao:
        # Se for múltiplo (5#d5+5): usa o comportamento não detalhado
        qtd, dado = expressao.split("#", 1)
        qtd = int(qtd)
        resultados = [rolar_dado(dado, detalhado=False) for _ in range(qtd)]
        msg = "\n".join(
            f"``{r['resultado']}`` ⟵ [{r['resultadoWOutEval']}] {expressao}"
            for r in resultados
        )
        return await interaction.response.send_message(msg)
    else:
        # Para rolagens simples, usa o comportamento detalhado
        res = rolar_dado(expressao, detalhado=True)
        if res is None:
            return await interaction.response.send_message("❌ Expressão inválida!", ephemeral=True)
        # Aqui não encapsulamos em colchetes, pois o breakdown já vem formatado (ex.: "[5, 4, 3, 2, 1]")
        msg = f"``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', expressao)}"
        return await interaction.response.send_message(msg)

# Respostas de on_message
REACTIONS = {
    "bem-vindo": ["👋", "🎉"],    # Reage com 👋 e 🎉 a mensagens contendo "bem-vindo"
    "importante": ["⚠️", "📢"],   # Reage com ⚠️ e 📢 a mensagens contendo "importante"
    "parabéns": ["🥳", "🎊"],      # Reage com 🥳 e 🎊 a mensagens contendo "parabéns"
    "obrigado": ["🙏"],           # Reage com 🙏 a mensagens contendo "obrigado"
}
SARCASM_RESPONSES = [
    "Escreveu a bíblia carai",
    "Ningúem perguntou",
    "E o fodasse?",
    "Meu tico que eu vou ler isso",
    "Minhas bola",
    "Seloko tá escrevendo mais que o Ozamu Tezuka",
    f"Redação do enem nota {random.randrange(0,300)}",
    "Esse aí passa em medicina",
    "Redação do krl tmnc",
    "Bora escrever um livro cria?",
    "Esse texto aí vai virar curso de faculdade",
    "Parece que você leu o manual do lil penis",
    "Escreveu mais que a lista de clientes de um editor de vídeo",
    "Meu Deus, não sabia que você era escritor (naipe ichiro oda)",
    "Vai lançar uma série de 20 temporadas com esse texto? Pq se for a netflix enfia no cu",
    "Parece um episódio de anime cheio de filler, não, pior, PARECE UM AD DA TWITCH ESSA PORRA",
    "Texto mais longo que meu pau",
    "Você não cansa de se ouvir?",
    "Parece que escreveu a versão expandida do Senhor dos Anais",
    "Vai lançar um audiobook?"
]
def is_spam(text):
    # Remove espaços e ignora letras maiúsculas/minúsculas
    normalized = text.replace(" ", "").lower()

    # Se for só um caractere repetido várias vezes, é spam
    if len(set(normalized)) == 1:
        return True

    # Se for só um pequeno grupo de caracteres repetindo várias vezes (ex: "lolololol", "haha haha")
    match = re.fullmatch(r"(.+?)\1+", normalized)
    if match:
        return True

    return False

# Evento on_message com suporte para rolagem via "$"
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignora mensagens de bots

    # Adiciona reações pré-definidas
    for keyword, emojis in REACTIONS.items():
        if keyword in message.content.lower():
            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except discord.Forbidden:
                    print(f"❌ Não tenho permissão para reagir a mensagens em {message.channel}")

    # Detecta expressões de rolagem no formato "$..."
    matches = re.findall(r'\$(\d*#?\d*d\d+[\+\-\*/\(\)\d]*)', message.content)
    resultados = []
    if matches:
        for m in matches:
            if '#' in m:
                # Se houver "#" na expressão, dividimos em quantidade e o dado base
                qtd_str, dado = m.split("#", 1)
                try:
                    qtd = int(qtd_str)
                except ValueError:
                    qtd = 1  # Caso não consiga converter, assume 1
                # Rola a expressão "dado" a quantidade especificada
                for _ in range(qtd):
                    res = rolar_dado(dado, detalhado=False)
                    resultados.append(
                        f"``{res['resultado']}`` ⟵ [{res['resultadoWOutEval']}] {m}"
                    )
            else:
                res = rolar_dado(m, detalhado=True)
                resultados.append(
                    f"``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', m)}"
                )
        await message.channel.send("\n".join(resultados))
        
    # Respostas sarcasticas
    if len(message.content) > 300 and not is_spam(message.content):
        await asyncio.sleep(2)
        async with message.channel.typing():  # Usa o contexto assíncrono para simular digitação
            await asyncio.sleep(3)  # Aguarda 3 segundos (opcional)
            await message.channel.send(random.choice(SARCASM_RESPONSES))  # Envia a resposta

    # Palavras proíbidas (memes poggers heinn)
    if "banana" in message.content.lower():
        await message.channel.send(f'BANANA DETECTADA!!!! INICIANDO PROTOCOLO DE SEGURANÇA!!!!!')
        await castigar_automatico(message.author, 60)

    await bot.process_commands(message)
#@bot.event
#async def on_message_delete(message):
    #print(f"Mensagem deletada: {message.content}")
    #await save_deleted_message(message)

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

JOKENPO_OPCOES = {
    "🪨": "Pedra",
    "📜": "Papel",
    "✂️": "Tesoura"
}
@bot.tree.command(name="jokenpo", description="Desafie alguém para uma partida de Jokenpô!")
async def jokenpo(interaction: discord.Interaction):
    await interaction.response.send_message("🎮 **Jokenpô Iniciado!** Aguardando outro jogador... Reaja com 🎮 para entrar!", ephemeral=False)

    msg = await interaction.original_response()
    await msg.add_reaction("🎮")

    def check_jogador2(reaction, user):
        return reaction.message.id == msg.id and str(reaction.emoji) == "🎮" and user != interaction.user and not user.bot

    try:
        reaction, jogador2 = await bot.wait_for("reaction_add", timeout=30.0, check=check_jogador2)
    except asyncio.TimeoutError:
        try:
            await msg.clear_reaction("🎮")  # Remove a reação para evitar confusão
            await msg.edit(content="⏳ **Tempo esgotado!** Nenhum jogador entrou.")
        except discord.errors.NotFound:
            print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")
        return

    await msg.clear_reactions()
    await msg.edit(content=f"🆚 {interaction.user.mention} **vs** {jogador2.mention}!\n\nEscolham Pedra (🪨), Papel (📜) ou Tesoura (✂️) reagindo abaixo!")

    for emoji in JOKENPO_OPCOES.keys():
        await msg.add_reaction(emoji)

    escolhas = {interaction.user: None, jogador2: None}

    def check_escolha(reaction, user):
        return reaction.message.id == msg.id and user in escolhas and str(reaction.emoji) in JOKENPO_OPCOES and escolhas[user] is None

    while None in escolhas.values():
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check_escolha)
            escolhas[user] = JOKENPO_OPCOES[str(reaction.emoji)]
        except asyncio.TimeoutError:
            try:
                await msg.clear_reactions()
                await msg.edit(content="⏳ **Tempo esgotado!** Um dos jogadores não escolheu a tempo.")
            except discord.errors.NotFound:
                print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")
            return

    # Determinar vencedor
    resultado = determinar_vencedor(escolhas[interaction.user], escolhas[jogador2])
    try:
        await msg.clear_reactions()
        await msg.edit(content=f"🆚 {interaction.user.mention} **vs** {jogador2.mention}!\n\n"
                               f"🎭 **Escolhas:**\n"
                               f"🔹 {interaction.user.mention} escolheu **{escolhas[interaction.user]}**\n"
                               f"🔹 {jogador2.mention} escolheu **{escolhas[jogador2]}**\n\n"
                               f"{resultado}")
    except discord.errors.NotFound:
        print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")
def determinar_vencedor(jogada1, jogada2):
    if jogada1 == jogada2:
        return "🤝 **Empate!**"
    elif (jogada1 == "Pedra" and jogada2 == "Tesoura") or \
         (jogada1 == "Papel" and jogada2 == "Pedra") or \
         (jogada1 == "Tesoura" and jogada2 == "Papel"):
        return "🎉 **O primeiro jogador venceu!**"
    else:
        return "🎉 **O segundo jogador venceu!**"

@bot.tree.command(name="db_test", description="Testa o banco de dados")
@app_commands.describe(action="Escolha entre save ou load", name="Nome da chave", value="Valor a ser salvo (apenas para save)")
async def db_test(interaction: discord.Interaction, action: str, name: str, value: str = None):
    # Defer a resposta para garantir mais tempo para processamento
    await interaction.response.defer()

    if action == "save":
        if value is None:
            await interaction.followup.send("Você precisa fornecer um valor para salvar!", ephemeral=True)
            return
        await save(name, value)
        await interaction.followup.send(f"Salvo: `{name}` = `{value}`")
    elif action == "load":
        result = load(name)
        if result is None:
            await interaction.followup.send(f"Nenhum dado encontrado para `{name}`.", ephemeral=True)
        else:
            await interaction.followup.send(f"Valor de `{name}`: `{result}`")
    else:
        await interaction.followup.send("Ação inválida! Use 'save' ou 'load'.", ephemeral=True)

# Tocador
voice_clients = {}
queues = {}
def check_auto_disconnect(guild_id):
    async def task():
        await asyncio.sleep(60)  # Aguarda 1 minuto
        vc = voice_clients.get(guild_id)
        if vc and not vc.is_playing() and not queues.get(guild_id):
            await vc.disconnect()
            del voice_clients[guild_id]
            del queues[guild_id]  # Limpa também a fila

    # Certifica-se de que o loop de eventos correto está sendo utilizado
    loop = bot.loop # Obtém o loop de eventos do discord client
    asyncio.run_coroutine_threadsafe(task(), loop)  # Executa a tarefa de forma segura no loop principal
def play_next(guild_id):
    if guild_id in queues and queues[guild_id]:  # Verifica se a chave existe antes de acessar
        audio_file = queues[guild_id].pop(0)
        vc = voice_clients[guild_id]
        
        def after_playback(error):
            if error:
                print(f"Erro ao tocar áudio: {error}")
            if not queues[guild_id]:  # Verifica se a fila ficou vazia após tocar
                check_auto_disconnect(guild_id)  # Chama a função para desconectar se não houver mais áudios

            play_next(guild_id)  # Toca o próximo áudio da fila

        vc.play(discord.FFmpegPCMAudio(audio_file), after=after_playback)
    else:
        check_auto_disconnect(guild_id)  # Se a fila estiver vazia, desconectar
def buscar_arquivo(nome):
    nome_normalizado = unidecode.unidecode(nome).lower()
    for root, _, files in os.walk("assets/audios"):
        for file in files:
            if unidecode.unidecode(file).lower().startswith(nome_normalizado):
                return os.path.join(root, file)
    return None
@bot.tree.command(name="entrar", description="Faz o bot entrar no canal de voz e permanecer lá")
@app_commands.describe(canal="Canal de voz onde o bot entrará")
async def entrar(interaction: discord.Interaction, canal: discord.VoiceChannel):
    if not interaction.user.guild_permissions.connect:
        return await interaction.response.send_message("🚫 Você não tem permissão para usar este comando!", ephemeral=True)
    
    if interaction.guild.id in voice_clients:
        return await interaction.response.send_message("⚠️ Já estou em um canal de voz!", ephemeral=True)
    
    vc = await canal.connect()
    voice_clients[interaction.guild.id] = vc
    await interaction.response.send_message(f"🔊 Entrei no canal {canal.mention}!")
@bot.tree.command(name="tocar", description="Toca um áudio no canal de voz sem sair")
@app_commands.describe(arquivo="Nome do arquivo de áudio (deve estar no repositório do bot)")
async def tocar(interaction: discord.Interaction, arquivo: str):
    guild_id = interaction.guild.id
    vc = voice_clients.get(guild_id)
    
    if not vc:
        canal = interaction.user.voice.channel if interaction.user.voice else None
        if not canal:
            return await interaction.response.send_message("❌ Você não está em um canal de voz e o bot também não está!", ephemeral=True)
        vc = await canal.connect()
        voice_clients[guild_id] = vc

    audio_file = buscar_arquivo(arquivo)
    if not audio_file:
        return await interaction.response.send_message("❌ Arquivo de áudio não encontrado!", ephemeral=True)

    if guild_id not in queues:
        queues[guild_id] = []
    
    queues[guild_id].append(audio_file)
    
    if not vc.is_playing():
        play_next(guild_id)
        await interaction.response.send_message(f"🎵 Tocando `{arquivo}`!")
    else:
        await interaction.response.send_message(f"🎶 `{arquivo}` adicionado à fila!")
@bot.tree.command(name="listar", description="Lista todos os áudios")
async def listar(interaction: discord.Interaction):
    diretorio = "assets/audios"
    if not os.path.exists(diretorio):
        return await interaction.response.send_message("❌ Diretório não encontrado!", ephemeral=True)

    def build_tree(path, prefix):
        itens = os.listdir(path)
        dirs = [item for item in itens if os.path.isdir(os.path.join(path, item))]
        files = [item for item in itens if os.path.isfile(os.path.join(path, item))]
        combinados = dirs + files

        linhas = []
        for idx, item in enumerate(combinados):
            is_last = (idx == len(combinados) - 1)
            branch = "└──" if is_last else "├──"
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                linhas.append(f"{prefix}{branch} 📁 {item}/")
                novo_prefix = prefix + ("    " if is_last else "│   ")
                linhas.extend(build_tree(item_path, novo_prefix))
            else:
                linhas.append(f"{prefix}{branch} 📄 {item}")
        return linhas

    tree_lines = build_tree(diretorio, "│   ")
    lista_arquivos = f"📂 {os.path.basename(diretorio)}/\n" + "\n".join(tree_lines) if tree_lines else "📂 Diretório vazio."

    if len(lista_arquivos) > 2000:
        with open("lista_arquivos.txt", "w", encoding="utf-8") as f:
            f.write(lista_arquivos)
        await interaction.response.send_message("📜 Lista de arquivos:", file=discord.File("lista_arquivos.txt"))
        os.remove("lista_arquivos.txt")
    else:
        await interaction.response.send_message(f"**Arquivos e pastas em `{diretorio}`:**\n```\n{lista_arquivos}\n```")
@bot.tree.command(name="parar", description="Para a reprodução e limpa a fila")
async def parar(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = voice_clients.get(guild_id)
    
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("❌ Não há áudio tocando!", ephemeral=True)
    
    queues[guild_id] = []  # Limpa a fila
    vc.stop()
    await interaction.response.send_message("⏹️ Reprodução interrompida e fila limpa!")
@bot.tree.command(name="sair", description="Faz o bot sair do canal de voz e limpa a fila de reprodução")
async def sair(interaction: discord.Interaction):
    vc = voice_clients.pop(interaction.guild.id, None)
    if not vc:
        return await interaction.response.send_message("❌ Não estou em um canal de voz!", ephemeral=True)
    
    queues.pop(interaction.guild.id, None)  # Limpa a fila de reprodução
    await vc.disconnect()
    await interaction.response.send_message("👋 Saí do canal de voz e limpei a fila de reprodução!")
@bot.tree.command(name="pular", description="Pula para o próximo áudio na fila")
async def pular(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = voice_clients.get(guild_id)
    
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("❌ Nenhum áudio está tocando!", ephemeral=True)
    
    vc.stop()
    await interaction.response.send_message("⏭️ Pulando para o próximo áudio...")
    
    play_next(guild_id)
@bot.tree.command(name="fila", description="Mostra a fila de áudios")
async def fila(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    queue = queues.get(guild_id, [])
    
    if not queue:
        return await interaction.response.send_message("🎶 A fila está vazia!", ephemeral=True)
    
    lista = "\n".join([f"{idx+1}. {os.path.basename(track)}" for idx, track in enumerate(queue)])
    await interaction.response.send_message(f"📜 **Fila de reprodução:**\n```\n{lista}\n```")

@bot.tree.command(name="roletarussa", description="Vida ou morte.")
async def roletarussa(interaction: discord.Interaction):
    result = random.randrange(0,100)
    if result <= 14:
        await interaction.response.send_message(f"Você **morreu**")
    else:
        await interaction.response.send_message("Você *sobrevive*")

@bot.tree.command(name="missao", description="Receba uma missão")
async def missao(interaction: discord.Interaction):
    missoes = [
    "No meio de uma conversa séria, olha pra alguém e diz: 'Mano, eu tava pensando aqui... Tu deixaria eu te dar uma mamada?' com a cara mais séria possível.",
    "Sempre que alguém falar contigo por 10 minutos, responde só com gestos, olhares intensos e mordendo os lábios.",
    "Liga pra um número aleatório da tua lista de contatos e fala 'Você sabe por que eu liguei...' e fica em silêncio esperando a reação.",
    "Entra no chat da pessoa mais improvável e manda: 'Mano, não sei como te contar isso, mas eu sonhei que a gente se pegava. E foi bom.'",
    "Finge que acabou de encontrar Jesus/Buda/um Alien e tenta converter um amigo do grupo de maneira fanática.",
    "Escreve uma resenha absurda no status do WhatsApp, tipo: 'Recomendo a experiência de levar uma dedada no cu. Profundo e emocionante.'",
    "Pede pra alguém abrir o Google na tua frente e digita: 'É normal sentir prazer em...' e deixa o autocorretor terminar.",
    "Manda um áudio gemendo no grupo da família e depois responde: 'Foi sem querer, meu cachorro pisou no microfone.'",
    "Chama um desconhecido no Instagram e conta uma história totalmente falsa sobre como vocês já foram melhores amigos na infância.",
    "No meio de uma call, começa a discursar como se fosse um coach ultra motivacional sobre o 'poder da mamada' para o sucesso.",
    f"Manda uma mensagem pro {randomuser()} dizendo: 'Sonhei que a gente se pegava na força do ódio, mas no final gostei. O que isso significa?' e espera a resposta.",
    f"Chega no {randomuser()} e fala bem sério: 'Eu vendi tua cueca/calcinha usada na deep web por R$350, foi mal.' e vê a reação.",
    f"Faz um gemido bem convincente no ouvido do {randomuser()} e diz: 'Desculpa, não consegui me segurar.'",
    f"Liga pro {randomuser()} e começa a respirar fundo no telefone, depois solta: 'Tu tem ideia do que tu fez comigo naquela noite?' e desliga.",
    f"Manda pro {randomuser()}: 'Preciso ser honesto... Minha mãe me pegou vendo tuas fotos e perguntou se tu era meu crush.'",
    f"Olha pro {randomuser()} no meio de um papo aleatório e diz: 'Tu já experimentou chupar um dedão do pé? Porque eu sonhei que fazia isso contigo.'",
    f"Chega no {randomuser()} e fala: 'Preciso te contar... Eu tatuei teu nome numa área íntima, mas só te mostro se tu pedir com carinho.'",
    f"Manda um áudio pro {randomuser()} gemendo e depois explica: 'Foi sem querer, tava testando meu novo microfone ASMR.'",
    f"Vai no PV do {randomuser()} e manda: 'Ei... Quanto tu cobraria pra pisar em mim de coturno?' e mantém a conversa séria.",
    f"Faz uma aposta com {randomuser()}, perde de propósito e depois fala: 'Aposta é aposta, agora tu tem que me deixar morder tua orelha.'"
]
    await interaction.response.send_message(random.choice(missoes))

@bot.tree.command(name="piada", description="Piadocas pesadonas")
async def piada(interaction: discord.Interaction):
    piadas = [
    "Se eu fosse teu espelho, eu me quebrava pra não ter que te ver.",
    "Teu cérebro é tipo uma caixa de fósforos: quando acende, não dura muito.",
    "Tu é tipo um Wi-Fi, porque está sempre sem sinal de relevância.",
    "Eu não sou psicólogo, mas te diria que teu único problema é ser você.",
    "Eu te daria um conselho, mas tua vida já tá bagunçada demais.",
    "Tu é tão inútil quanto um arroz sem feijão.",
    "O único lugar que você deve estar é dentro de uma cápsula do tempo, pra nunca mais sair.",
    "Teu corpo é uma obra de arte... e o museu está em chamas.",
    "Tu já pensou em fazer uma cirurgia plástica no cérebro?",
    "Teu futuro é tão brilhante quanto uma lâmpada queimada.",
    "O que você faz de bom é se esconder bem.",
    "Se tua inteligência fosse combustível, não dava pra ligar uma lâmpada.",
    "Eu faria uma piada sobre tua vida, mas ela é trágica demais para piadas.",
    "Sua voz é tão agradável quanto um gato sendo atropelado.",
    "Se você fosse uma peça de Lego, estaria perdida no fundo da caixa.",
    "Tu não é feio, só é uma prova de que o Photoshop não salva tudo.",
    "Se eu te seguisse em redes sociais, eu bloqueava todo mundo em volta.",
    "Eu te chamaria de inútil, mas nem isso tu consegue ser.",
    "Seu cérebro é tipo uma cebola: quanto mais você mexe, mais causa dor.",
    "Você é tão importante quanto um pedaço de papel higiênico usado.",
    "Eu te consideraria uma pessoa incrível, se não fosse tão patético.",
    "Tu não é feio, tu é mais uma homenagem a todos os erros genéticos.",
    "Teu corpo é um parque de diversões… mas ninguém quer entrar.",
    "Se tua vida fosse uma série, seria um drama sem audiência.",
    "Tu é a prova viva de que a evolução não aconteceu em todas as espécies.",
    "Se eu fosse um gato, teria medo de passar perto de você.",
    "Tu é tão sem graça quanto um powerpoint sem animações.",
    "Tu parece aquele personagem que morreu no episódio 1 da série, mas ainda aparece pra dar dó.",
    "Se teu rosto fosse um título de filme, seria 'Como Arruinar Uma Carreira Em Uma Imagem'.",
    "Tu deve ser uma edição limitada de 'desastre de design'.",
    "Se tu fosse uma série, seria cancelada depois do primeiro episódio.",
    "Teu sorriso é tão acolhedor quanto uma faca.",
    "Eu não sou de julgar, mas tu é basicamente um teste de paciência.",
    "Tu tem o carisma de uma mesa de escritório.",
    "Você não é gordo, só tem mais personalidade.",
    "Tu é o tipo de pessoa que faz um espelho quebrar só de se olhar nele.",
    "Seu cérebro é como um celular sem internet: não funciona direito.",
    "Eu não te chamei de feio, mas eu falei da sua foto no seu perfil.",
    "Se seu rosto fosse uma arte moderna, ninguém entenderia.",
    "Eu te amo como eu amo uma sopa sem tempero.",
    "Tu é a mistura de um dia de chuva com uma sexta-feira 13.",
    "Eu não te julgo, mas teu karma está em greve.",
    "Você é tão insuportável quanto um fone de ouvido embaraçado.",
    "Seu corpo é como um software desatualizado, não serve pra nada.",
    "Tu tem a graça de um pato tentando andar de patins.",
    "Se tua vida fosse um jogo, seria a versão demo.",
    "Tu não é feio, mas é um dos melhores exemplos de teoria da evolução.",
    "Teu coração é como um servidor cheio de erros 404.",
    "Você tem o charme de uma rachadura na parede.",
    "Tu é a versão beta do ser humano.",
    "Você não é um problema, mas definitivamente é uma distração.",
    "Teu sentido de humor é igual a uma piada sem punchline.",
    "Você é como o efeito borboleta, mas no lado errado da história.",
    "Teu rosto deveria vir com uma placa de 'Aviso: pode causar insônia'.",
    "Tu é a pessoa que faz o wifi cair só com a presença.",
    "Se tu fosse uma música, seria aquela em loop que ninguém aguenta mais.",
    "Tu deve ser o motivo pelo qual os espelhos se trincam.",
    "Você deve ser um filme de terror, porque ninguém quer olhar pra você.",
    "Tu é a prova de que algumas ideias não deveriam sair da cabeça.",
    "Seu estilo é tão único quanto um par de crocs com meias.",
    "Você tem a elegância de um hipster tentando usar terno.",
    "Tu não é de assustar, mas com certeza é de incomodar.",
    "Se tu fosse um livro, seria um daqueles que ninguém compra.",
    "Tu tem a graça de uma pedra no meio do caminho.",
    "Seu cérebro está mais travado do que uma atualização do Windows.",
    "Tu tem o charme de um produto genérico.",
    "Se você fosse uma flor, seria aquela que morreu na floricultura.",
    "Tu é a resposta errada da equação da vida.",
    "Teu corpo é tão esquelético quanto um esqueleto de brinquedo.",
    "Você tem a profundidade emocional de uma piscina rasa.",
    "Tu não é gordo, só está indo além dos limites do normal.",
    "Se sua vida fosse um jogo de tabuleiro, você já teria perdido.",
    "Tu tem a simpatia de uma parede de concreto.",
    "Seu cérebro funciona como uma geladeira velha: faz barulho, mas não resolve nada.",
    "Tu é mais inútil que um controle remoto sem pilha.",
    "Você deve ser a razão pela qual as palavras se tornam obsoletas.",
    "Teu cheiro é tão agradável quanto um chulé de meia.",
    "Se tu fosse uma comida, seria miojo sem tempero.",
    "Teu cérebro é igual a uma faca cega: não serve pra nada.",
    "Eu te chamaria de estrela, mas tu brilha mais do que um apagador de quadro.",
    "Tu é a pessoa que até o Google te evita.",
    "Teu futuro é tão incerto quanto a internet de uma zona rural.",
    "Tu deve ser a pior decisão que teus pais tomaram.",
    "Tu é como uma música ruim: ninguém quer ouvir.",
    "Teu nível de carisma é menor que a energia de uma bateria descarregada.",
    "Se eu fosse teu chefe, te mandava embora só pela cara.",
    "Tu é como um carro velho: ninguém quer pegar.",
    "Tu deve ser aquele erro que todos os programadores tentam esconder.",
    "Seu cérebro é tipo um Wi-Fi ruim: todo mundo tenta, mas ninguém conecta.",
    "Tu não tem chance no amor, mas tem no ódio.",
    "Tu é o tipo de pessoa que até os fantasmas fogem.",
    "Você não é chato, só é uma falha de sistema.",
    "Tu é como um teste de matemática que todo mundo erra.",
    "Teu rosto é como uma obra de arte... uma obra mal feita.",
    "Você tem o talento de uma planta sem raízes.",
    "Tu tem a inteligência de um aspirador de pó, mas com menos utilidade.",
    "Eu te chamaria de otário, mas nem isso tu conseguiria ser.",
    "Tu não é feio, mas também não é bonito, é apenas... um erro.",
    "Você é o tipo de pessoa que nem um cachorro gostaria de ter como dono.",
    "Tu é tipo um espelho rachado: não reflete nada de bom.",
    "Teu rosto é como uma febre: não passa, mas também não serve pra nada.",
    "Se tua vida fosse uma peça de teatro, seria cancelada na primeira temporada.",
    "Você é como um jogo de videogame de 8 bits: velho, feio, mas ainda tenta.",
    "Tu não é estúpido, mas tá chegando lá.",
    "Teu cérebro deve ser uma planilha do Excel: cheio de fórmulas que ninguém entende.",
    "Tu tem o charme de um chinelo velho.",
    "Se eu tivesse que fazer uma comparação, diria que você é o erro 404 da vida.",
    "Você é tipo um caminhão sem carga: só ocupa espaço.",
    "Tu é o oposto da felicidade, é como um buraco no meio da praça.",
    "Tu é como uma mosca em uma festa de casamento: sempre no momento errado.",
    "Teu coração é tão quente quanto uma xícara de café esquecido.",
    "Você é como um meme velho: ninguém mais ri.",
    "Tu é mais chato que uma mariposa batendo na luz.",
    "Seu sorriso é tão acolhedor quanto uma lâmpada queimada.",
    "Você é como uma piada sem punchline: ninguém ri, mas ninguém reclama.",
    "Teu charme é como a política: ninguém acredita."
]
    await interaction.response.send_message(random.choice(piadas))

# Inicia o bot
bot.run(DISCORDTOKEN)