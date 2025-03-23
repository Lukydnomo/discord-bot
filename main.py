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
CAMINHO_AVATAR_ORIGINAL = "F.png"

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
with open('data/avisos_sessao.json', 'r', encoding='utf-8') as file:
    avisos = json.load(file)

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

    await bot.process_commands(message)

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
    asyncio.create_task(task())
def play_next(guild_id):
    if guild_id in queues and queues[guild_id]:  # Verifica se a chave existe antes de acessar
        audio_file = queues[guild_id].pop(0)
        vc = voice_clients[guild_id]
        
        def after_playback(error):
            if error:
                print(f"Erro ao tocar áudio: {error}")
            play_next(guild_id)  # Toca o próximo áudio da fila

        vc.play(discord.FFmpegPCMAudio(audio_file), after=lambda e: after_playback(e))
def buscar_arquivo(nome):
    nome_normalizado = unidecode.unidecode(nome).lower()
    for root, _, files in os.walk("audios"):
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
    diretorio = "audios"
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

# Inicia o bot
bot.run(DISCORDTOKEN)