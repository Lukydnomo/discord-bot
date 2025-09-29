# Core Python
import asyncio
import io

# Terceiros
import os
import random

# Discord
import discord
import pyfiglet
from deep_translator import GoogleTranslator
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFont

# Instâncias iniciais
cached_supported_languages = None  # Cache for supported languages
translate = GoogleTranslator

# Configuração do bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
from core.config import *
from core.events import *
from core.modules import *
from discord.ui import View, Button

# chama antes de inicializar o bot
cancel_previous_github_runs()

# ... após as importações ...

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="foa!",
            intents=intents    # <<< use o intents que você configurou em cima
        )

    async def setup_hook(self):
        # Carrega cada arquivo .py dentro de cogs/
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        # Sincroniza seus slash commands
        await self.tree.sync()

bot = MyBot()

# Nome do arquivo Markdown
arquivo_md = "changelog.md"

# Abrir o arquivo em modo leitura
with open(arquivo_md, "r", encoding="utf-8") as arquivo:
    linhas = arquivo.readlines()

# Filtrar o conteúdo ignorando só as linhas com <!-- prettier-ignore -->
conteudo_filtrado = [
    linha for linha in linhas if "<!-- prettier-ignore -->" not in linha
]

# Junta tudo em uma única string
conteudo = "".join(conteudo_filtrado)

# Escolhe usuário aleatório
async def randomuser():
    for guild in bot.guilds:  # Itera sobre os servidores onde o bot está
        members = [member for member in guild.members if not member.bot]  # Filtra membros não-bots
        
        if members:
            return random.choice(members)  # Retorna um membro aleatório
    
    return "No valid members found"  # Retorno caso não haja membros válidos

# Evento de quando o bot estiver pronto
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await on_ready_custom(bot, conteudo)  # Chama a função personalizada

@bot.event
async def on_message(message):
    await on_message_custom(bot, message)

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

@bot.tree.command(name="roletarussa", description="Vida ou morte.")
async def roletarussa(interaction: discord.Interaction):
    result = random.randrange(0,100)
    if result <= 14:
        await interaction.response.send_message(f"Você **morreu**")
    else:
        await interaction.response.send_message("Você *sobrevive*")

@bot.tree.command(name="missao", description="Receba uma missão")
async def missao(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(missoes))

@bot.tree.command(name="piada", description="Piadocas pesadonas")
async def piada(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(piadas))

@bot.tree.command(name="roleta", description="Escolhe uma opção aleatóriamente")
async def roleta(interaction: discord.Interaction, opcoes: str):
    opcoesNaRoleta = {}
    opcoesNaRoleta = opcoes.split(", ")
    await interaction.response.send_message(f"O escolhido foi: *{random.choice(opcoesNaRoleta)}*!")

@bot.tree.command(name="pdd", description="pdd")
@app_commands.default_permissions(administrator=True)  # Permite apenas para admins
async def pdd(interaction: discord.Interaction):
    await interaction.response.send_message(f"{palavra_do_dia}", ephemeral=True)

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
        res = await asyncio.to_thread(rolar_dado, expressao, True)
        if res is None:
            return await interaction.response.send_message("❌ Expressão inválida!", ephemeral=True)
        # Aqui não encapsulamos em colchetes, pois o breakdown já vem formatado (ex.: "[5, 4, 3, 2, 1]")
        msg = f"``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', expressao)}"
        return await interaction.response.send_message(msg)

@bot.tree.command(name="shippar", description="Calcula a chance de 2 usuários ficarem juntos")
async def shippar(interaction: discord.Interaction, nome1: str, nome2: str):
    await interaction.response.send_message(f"{nome1.capitalize()} e {nome2.capitalize()} tem {calcular_compatibilidade(nome1, nome2)}")

@bot.tree.command(name="deepfry", description="Aplica o efeito deep fry em uma imagem.")
@app_commands.describe(imagem="Imagem para aplicar o efeito deep fry")
async def deepfry(interaction: discord.Interaction, imagem: discord.Attachment):
    await interaction.response.defer()  # Pra dar tempo de processar a imagem

    try:
        # Baixa a imagem
        img_bytes = await imagem.read()
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        img = ImageEnhance.Contrast(img).enhance(4.0)
        img = ImageEnhance.Sharpness(img).enhance(12.0)
        img = ImageEnhance.Color(img).enhance(8.0)
        img = ImageEnhance.Brightness(img).enhance(1.5)

        # Adiciona um overlay vermelho
        overlay = Image.new('RGB', img.size, (255, 0, 0))
        img = Image.blend(img, overlay, alpha=0.2)

        # Faz compressão zoada JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=10)
        buffer.seek(0)

        await interaction.followup.send("🧨 **Imagem deep fried com sucesso!**", file=discord.File(buffer, filename="deepfried.jpg"))

    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao aplicar o efeito: {e}", ephemeral=True)

POPULAR_LANGUAGES = {
    "English": "en",
    "Português": "pt",
    "Español": "es",
    "Français": "fr",
    "Deutsch": "de",
    "Italiano": "it",
    "Русский": "ru",
    "中文": "zh",
    "日本語": "ja",
    "한국어": "ko",
    "العربية": "ar",
    "हिन्दी": "hi",
    "বাংলা": "bn",
    "Türkçe": "tr",
    "Việt": "vi",
    "Polski": "pl",
    "Nederlands": "nl",
    "Ελληνικά": "el",
    "Čeština": "cs",
    "Svenska": "sv",
    "Dansk": "da",
    "Suomi": "fi",
    "עברית": "he",
    "Bahasa Indonesia": "id",
    "Norsk": "no"
}
@bot.tree.command(name="hypertranslate", description="Traduz um texto por várias línguas aleatórias e retorna o resultado final.")
@app_commands.describe(
    texto="Texto original para traduzir",
    vezes="Quantidade de vezes a traduzir (máximo 50)",
    idioma_entrada="Idioma original do texto (ou auto para detectar)",
    idioma_saida="Idioma final do texto traduzido"
)
@app_commands.choices(
    idioma_entrada=[
        app_commands.Choice(name=nome, value=cod)
        for nome, cod in POPULAR_LANGUAGES.items()
    ],
    idioma_saida=[
        app_commands.Choice(name=nome, value=cod)
        for nome, cod in POPULAR_LANGUAGES.items()
    ]
)
async def hypertranslate(
    interaction: discord.Interaction,
    texto: str,
    vezes: app_commands.Range[int, 1, 50] = 10,
    idioma_entrada: app_commands.Choice[str] = None,
    idioma_saida: app_commands.Choice[str] = None
):
    await interaction.response.defer()

    if vezes < 1 or vezes > 50:
        return await interaction.followup.send("❌ Escolha entre 1 e 50 traduções.", ephemeral=True)

    # Define o idioma de entrada; se não informado, usa "auto"
    entrada = idioma_entrada.value if idioma_entrada else "auto"
    # Se o idioma de saída não for informado, retorna para o idioma de entrada
    saida = idioma_saida.value if idioma_saida else entrada

    global cached_supported_languages
    if cached_supported_languages is None:
        cached_supported_languages = GoogleTranslator().get_supported_languages(as_dict=True)
    langs = cached_supported_languages
    lang_codes = list(langs.values())

    atual = texto
    usado = []

    try:
        for _ in range(vezes):
            destino = random.choice(lang_codes)
            # Garante que não escolha o idioma de entrada ou repetido
            while destino in usado or destino == entrada or destino == "auto":
                destino = random.choice(lang_codes)
            usado.append(destino)

            try:
                atual = GoogleTranslator(source="auto", target=destino).translate(atual)
                if not atual:  # Handle empty or unexpected results
                    raise ValueError(f"Tradução falhou para o idioma {destino}.")
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao traduzir para o idioma {destino}: {e}", ephemeral=True)
                return
            await asyncio.sleep(0.3)

        # Traduz de volta para o idioma de saída escolhido
        final = GoogleTranslator(source="auto", target=saida).translate(atual)

        await interaction.followup.send(
            f"🌐 **Tradução concluída!**\n"
            f"🔤 **Texto original:** {texto}\n"
            f"🔁 **Texto traduzido:** {final}\n"
            f"📊 **Rodadas:** {vezes}\n"
            f"**Idioma de entrada:** `{entrada}`\n"
            f"**Idioma final:** `{saida}`\n"
            f"🔁 **Texto final:**\n```{final}```"
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Ocorreu um erro durante as traduções: {e}", ephemeral=True)

@bot.tree.command(name="lapide", description="Cria uma lápide com o nome de alguém ou texto personalizado.")
@app_commands.describe(
    usuario="(Opcional) Alvo da lápide",
    texto="(Opcional) Texto a ser escrito na lápide"
)
async def lapide(interaction: discord.Interaction, usuario: discord.Member = None, texto: str = None):
    nome_final = texto if texto else (usuario.display_name if usuario else "Desconhecido")
    await interaction.response.defer()

    try:
        # Decide o que será escrito
        # Nome final já definido acima
        # Caminhos

        # Caminhos
        caminho_imagem = "assets/images/grave.png"
        caminho_fonte = "assets/fonts/PTSerif-Bold.ttf"

        # Verifica se os arquivos necessários existem
        if not os.path.exists(caminho_imagem):
            return await interaction.followup.send("❌ O arquivo de imagem `grave.png` não foi encontrado!", ephemeral=True)
        if not os.path.exists(caminho_fonte):
            return await interaction.followup.send("❌ O arquivo de fonte `PTSerif-Bold.ttf` não foi encontrado!", ephemeral=True)

        # 1) Carrega imagem base
        img = Image.open(caminho_imagem).convert("RGBA")

        # 2) Fonte
        fonte = ImageFont.truetype(caminho_fonte, 50)

        # 3) Camada de texto
        text_layer = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        bbox = fonte.getbbox(nome_final)
        w_text = bbox[2] - bbox[0]
        h_text = bbox[3] - bbox[1]
        x_center = (600 - w_text) // 2
        y_center = (200 - h_text) // 2

        draw.text((x_center, y_center), nome_final, font=fonte, fill=(50, 50, 50, 180))

        # 4) Inclinação e blending
        rotated = text_layer.rotate(3.5, expand=True, resample=Image.BICUBIC)

        pos_x, pos_y = 160, 400
        w_rot, h_rot = rotated.size
        area_crop = img.crop((pos_x, pos_y, pos_x + w_rot, pos_y + h_rot))
        blended = ImageChops.multiply(area_crop, rotated)
        img.paste(blended, (pos_x, pos_y), rotated)

        # 5) Buffer e envio
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        await interaction.followup.send(
            content=f"🪦 Aqui jaz **{nome_final}**...",
            file=discord.File(fp=buffer, filename="lapide.png")
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao gerar a lápide: {e}", ephemeral=True)

# Lista de fontes famosas e melhores
FONTES_DISPONIVEIS = [
    "5lineoblique", "standard", "slant", "3-d", "alphabet", "doh", "isometric1", "block", "bubble", "digital"
]
@bot.tree.command(name="ascii", description="Gera uma arte ASCII com o texto e fonte escolhidos.")
@app_commands.describe(
    texto="Texto para converter em arte ASCII",
    fonte="Fonte para a arte ASCII (opcional, padrão: standard)"
)
@app_commands.choices(
    fonte=[app_commands.Choice(name=fonte, value=fonte) for fonte in FONTES_DISPONIVEIS]
)
async def ascii(interaction: discord.Interaction, texto: str, fonte: app_commands.Choice[str] = None):
    try:
        # Define a fonte padrão se nenhuma for escolhida
        fonte_escolhida = fonte.value if fonte else "standard"

        # Gera a arte ASCII
        if fonte_escolhida not in FONTES_DISPONIVEIS:
            fonte_escolhida = "standard"  # Fallback to default font if invalid
        arte = pyfiglet.figlet_format(texto, font=fonte_escolhida, width=50)
        if len(arte) > 2000:  # Limite de caracteres do Discord
            return await interaction.response.send_message(
                "❌ O resultado é muito grande para ser enviado no Discord!",
                ephemeral=True
            )

        await interaction.response.send_message(f"```\n{arte}\n```")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao gerar a arte ASCII: {e}", ephemeral=True)

class MuteUnmuteView(View):
    def __init__(self, channel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(label="Mutar Todos", style=discord.ButtonStyle.danger, custom_id="mute_all")
    async def mute_all(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message("❌ Você não tem permissão para mutar membros.", ephemeral=True)
            return
        count = 0
        for member in self.channel.members:
            if not member.bot and not member.voice.mute:
                try:
                    await member.edit(mute=True)
                    count += 1
                except Exception:
                    pass
        await interaction.response.send_message(f"🔇 Mutados: {count} membros.", ephemeral=True)

    @discord.ui.button(label="Desmutar Todos", style=discord.ButtonStyle.success, custom_id="unmute_all")
    async def unmute_all(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message("❌ Você não tem permissão para desmutar membros.", ephemeral=True)
            return
        count = 0
        for member in self.channel.members:
            if not member.bot and member.voice.mute:
                try:
                    await member.edit(mute=False)
                    count += 1
                except Exception:
                    pass
        await interaction.response.send_message(f"🔊 Desmutados: {count} membros.", ephemeral=True)
@bot.tree.command(name="mutecall", description="Cria botões para mutar/desmutar todos na call atual.")
async def mutecall(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ Você precisa estar em um canal de voz.", ephemeral=True)
        return
    channel = interaction.user.voice.channel
    embed = discord.Embed(
        title="Controle de Mute da Call",
        description=f"Canal: **{channel.name}**\nUse os botões abaixo para mutar ou desmutar todos na call.",
        color=discord.Color.blue()
    )
    view = MuteUnmuteView(channel)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Inicia o bot
bot.run(DISCORDTOKEN)