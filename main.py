import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import json
import random
import re

# Configuração do bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
prefix = 'foa!'
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
luky = 767015394648915978
usuarios_autorizados = [luky]
updateyn = 0

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

# Reações automáticas pré-definidas
REACTIONS = {
    "bem-vindo": ["👋", "🎉"],    # Reage com 👋 e 🎉 a mensagens contendo "bem-vindo"
    "importante": ["⚠️", "📢"],   # Reage com ⚠️ e 📢 a mensagens contendo "importante"
    "parabéns": ["🥳", "🎊"],      # Reage com 🥳 e 🎊 a mensagens contendo "parabéns"
    "obrigado": ["🙏"],           # Reage com 🙏 a mensagens contendo "obrigado"
}

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
                # Se houver "#", usa comportamento não detalhado
                res = rolar_dado(m, detalhado=False)
                resultados.append(f"``{res['resultado']}`` ⟵ [{res['resultadoWOutEval']}] {m}")
            else:
                res = rolar_dado(m, detalhado=True)
                resultados.append(f"``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', m)}")
        await message.channel.send("\n".join(resultados))
        
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

# Inicia o bot
bot.run(TOKEN)