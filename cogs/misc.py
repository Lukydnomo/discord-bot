# cogs/misc.py
from __future__ import annotations

import asyncio
import io
import os
import random
import re
import ast
import operator as op
from typing import Any, Optional, Dict, List, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from PIL import Image, ImageEnhance, ImageFont, ImageDraw, ImageChops
import pyfiglet

from core.modules import (
    carregar_missoes,
    carregar_piada,
    obter_palavra_do_dia,
)

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None


# =========================
# Config / Placeholders
# =========================

JOKENPO_OPCOES = {
    "🪨": "Pedra",
    "📜": "Papel",
    "✂️": "Tesoura",
}

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
    "Norsk": "no",
}

FONTES_DISPONIVEIS = [
    "5lineoblique", "standard", "slant", "3-d", "alphabet",
    "doh", "isometric1", "block", "bubble", "digital"
]


# =========================
# Helpers
# =========================

def calcular_compatibilidade(nome1: str, nome2: str) -> str:
    base = (nome1.strip().lower() + "|" + nome2.strip().lower()).encode("utf-8")
    val = sum(base) % 101
    return f"**{val}%** 💘"


def _jokenpo_vencedor(p1: str, p2: str) -> int:
    """Retorna: 0 empate, 1 player1 vence, 2 player2 vence."""
    if p1 == p2:
        return 0
    vence = {
        ("Pedra", "Tesoura"),
        ("Tesoura", "Papel"),
        ("Papel", "Pedra"),
    }
    return 1 if (p1, p2) in vence else 2


# ---- Dice roller seguro (sem eval direto) ----

_ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

_DICE_RE = re.compile(r"(?<!\w)(\d*)d(\d+)(?!\w)", re.IGNORECASE)


def _safe_eval(expr: str) -> float:
    """Avalia expressão matemática com AST permitido."""
    node = ast.parse(expr, mode="eval")

    def _eval(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Num):  # py<3.8
            return float(n.n)
        if isinstance(n, ast.Constant):  # py>=3.8
            if isinstance(n.value, (int, float)):
                return float(n.value)
            raise ValueError("Constante inválida.")
        if isinstance(n, ast.BinOp):
            if type(n.op) not in _ALLOWED_OPS:
                raise ValueError("Operador não permitido.")
            return _ALLOWED_OPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp):
            if type(n.op) not in _ALLOWED_OPS:
                raise ValueError("Operador não permitido.")
            return _ALLOWED_OPS[type(n.op)](_eval(n.operand))
        raise ValueError("Expressão inválida.")

    return _eval(node)


def rolar_dado(expressao: str, detalhado: bool = True) -> Optional[Dict[str, Any]]:
    """
    Suporta: 2d6+2, d20-1, 4d10/2, etc.
    Retorna dict com resultado + breakdown.
    """
    exp = (expressao or "").strip().replace(" ", "")
    if not exp:
        return None

    breakdown_parts: List[str] = []
    replaced = exp

    # Substitui grupos XdY por soma (e guarda breakdown)
    matches = list(_DICE_RE.finditer(exp))
    if not matches:
        # sem dado: tenta só matemática
        try:
            val = _safe_eval(exp)
            return {
                "resultado": int(val) if val.is_integer() else val,
                "resultadoWOutEval": exp,
                "dice_group": expressao,
            }
        except Exception:
            return None

    offset = 0
    for m in matches:
        qtd_s = m.group(1)
        faces_s = m.group(2)
        qtd = int(qtd_s) if qtd_s else 1
        faces = int(faces_s)

        if qtd < 1 or qtd > 200 or faces < 2 or faces > 100000:
            return None

        rolls = [random.randint(1, faces) for _ in range(qtd)]
        soma = sum(rolls)

        rep_str = f"({soma})"
        # troca no texto com offset (pq string muda de tamanho)
        start, end = m.start() + offset, m.end() + offset
        replaced = replaced[:start] + rep_str + replaced[end:]
        offset += len(rep_str) - (m.end() - m.start())

        if detalhado:
            breakdown_parts.append(f"{qtd}d{faces}→{rolls}={soma}")
        else:
            breakdown_parts.append(f"{qtd}d{faces}={soma}")

    # Agora avalia matemática final
    try:
        val = _safe_eval(replaced)
    except Exception:
        return None

    out = {
        "resultado": int(val) if float(val).is_integer() else val,
        "resultadoWOutEval": (" | ".join(breakdown_parts) + f" | expr={replaced}") if breakdown_parts else replaced,
        "dice_group": expressao,
    }
    return out


# =========================
# Views
# =========================

class MuteUnmuteView(View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(label="Mutar Todos", style=discord.ButtonStyle.danger, custom_id="mute_all")
    async def mute_all(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message("❌ Você não tem permissão para mutar membros.", ephemeral=True)
            return

        count = 0
        for member in self.channel.members:
            if member.bot:
                continue
            if member.voice and not member.voice.mute:
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
            if member.bot:
                continue
            if member.voice and member.voice.mute:
                try:
                    await member.edit(mute=False)
                    count += 1
                except Exception:
                    pass

        await interaction.response.send_message(f"🔊 Desmutados: {count} membros.", ephemeral=True)


# =========================
# Cog
# =========================

class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cached_supported_languages: Optional[Dict[str, str]] = None

    # ---------- JOKENPÔ ----------
    @app_commands.command(name="jokenpo", description="Desafie alguém para uma partida de Jokenpô!")
    async def jokenpo(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "🎮 **Jokenpô Iniciado!** Aguardando outro jogador... Reaja com 🎮 para entrar!",
            ephemeral=False,
        )

        msg = await interaction.original_response()
        await msg.add_reaction("🎮")

        def check_jogador2(reaction: discord.Reaction, user: discord.User):
            return (
                reaction.message.id == msg.id
                and str(reaction.emoji) == "🎮"
                and user != interaction.user
                and not getattr(user, "bot", False)
            )

        try:
            _, jogador2 = await self.bot.wait_for("reaction_add", timeout=30.0, check=check_jogador2)
        except asyncio.TimeoutError:
            try:
                await msg.clear_reaction("🎮")
                await msg.edit(content="⏳ **Tempo esgotado!** Nenhum jogador entrou.")
            except discord.NotFound:
                print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")
            return

        try:
            await msg.clear_reactions()
        except Exception:
            pass

        await msg.edit(
            content=(
                f"🆚 {interaction.user.mention} **vs** {jogador2.mention}!\n\n"
                "Escolham Pedra (🪨), Papel (📜) ou Tesoura (✂️) reagindo abaixo!"
            )
        )

        for emoji in JOKENPO_OPCOES.keys():
            await msg.add_reaction(emoji)

        escolhas: Dict[discord.abc.User, Optional[str]] = {interaction.user: None, jogador2: None}

        def check_escolha(reaction: discord.Reaction, user: discord.User):
            return (
                reaction.message.id == msg.id
                and user in escolhas
                and str(reaction.emoji) in JOKENPO_OPCOES
                and escolhas[user] is None
            )

        while None in escolhas.values():
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check_escolha)
                escolhas[user] = JOKENPO_OPCOES[str(reaction.emoji)]
            except asyncio.TimeoutError:
                try:
                    await msg.clear_reactions()
                    await msg.edit(content="⏳ **Tempo esgotado!** Um dos jogadores não escolheu a tempo.")
                except discord.NotFound:
                    print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")
                return

        p1 = escolhas[interaction.user]
        p2 = escolhas[jogador2]

        vencedor = _jokenpo_vencedor(p1, p2)
        if vencedor == 0:
            resultado_txt = "🤝 **Empate!**"
        elif vencedor == 1:
            resultado_txt = f"🏆 {interaction.user.mention} **venceu!**"
        else:
            resultado_txt = f"🏆 {jogador2.mention} **venceu!**"

        try:
            await msg.clear_reactions()
            await msg.edit(
                content=(
                    f"🆚 {interaction.user.mention} **vs** {jogador2.mention}!\n\n"
                    f"🎭 **Escolhas:**\n"
                    f"🔹 {interaction.user.mention} escolheu **{p1}**\n"
                    f"🔹 {jogador2.mention} escolheu **{p2}**\n\n"
                    f"{resultado_txt}"
                )
            )
        except discord.NotFound:
            print("⚠️ Mensagem não encontrada. Provavelmente foi deletada ou expirou.")

    # ---------- Roleta Russa ----------
    @app_commands.command(name="roletarussa", description="Vida ou morte.")
    async def roletarussa(self, interaction: discord.Interaction):
        # 1 em 6
        result = random.randint(1, 6)
        if result == 1:
            await interaction.response.send_message("Você **morreu**")
        else:
            await interaction.response.send_message("Você *sobrevive*")

    # ---------- Missão ----------
    @app_commands.command(name="missao", description="Receba uma missão")
    async def missao(self, interaction: discord.Interaction):
        missoes = carregar_missoes()
        if not missoes:
            return await interaction.response.send_message("❌ Não tem missões configuradas.")
        await interaction.response.send_message(random.choice(missoes))

    # ---------- Piada ----------
    @app_commands.command(name="piada", description="Piadocas pesadonas")
    async def piada(self, interaction: discord.Interaction):
        piadas = carregar_piada()
        if not piadas:
            return await interaction.response.send_message("❌ Não tem piadas configuradas.")
        await interaction.response.send_message(random.choice(piadas))

    # ---------- Roleta (opções) ----------
    @app_commands.command(name="roleta", description="Escolhe uma opção aleatoriamente")
    @app_commands.describe(opcoes="Separe por vírgula. Ex: a, b, c")
    async def roleta(self, interaction: discord.Interaction, opcoes: str):
        lista = [x.strip() for x in opcoes.split(",") if x.strip()]
        if not lista:
            return await interaction.response.send_message("❌ Você precisa passar pelo menos 1 opção.", ephemeral=True)
        await interaction.response.send_message(f"O escolhido foi: *{random.choice(lista)}*!")

    # ---------- PDD ----------
    @app_commands.command(name="pdd", description="pdd")
    @app_commands.default_permissions(administrator=True)
    async def pdd(self, interaction: discord.Interaction):
        palavra = obter_palavra_do_dia()
        await interaction.response.send_message(palavra, ephemeral=True)

    # ---------- Rolar ----------
    @app_commands.command(name="rolar", description="Rola dados no formato XdY com operações matemáticas")
    @app_commands.describe(expressao="Exemplo: 2d6+2, 4d10/2, 5#d5+5")
    async def rolar(self, interaction: discord.Interaction, expressao: str):
        if "#" in expressao:
            qtd_s, dado = expressao.split("#", 1)
            try:
                qtd = int(qtd_s)
            except ValueError:
                return await interaction.response.send_message("❌ Expressão inválida!", ephemeral=True)

            if qtd < 1 or qtd > 50:
                return await interaction.response.send_message("❌ Quantidade inválida (1 a 50).", ephemeral=True)

            resultados = [rolar_dado(dado, detalhado=False) for _ in range(qtd)]
            if any(r is None for r in resultados):
                return await interaction.response.send_message("❌ Expressão inválida!", ephemeral=True)

            msg = "\n".join(
                f"``{r['resultado']}`` ⟵ [{r['resultadoWOutEval']}] {expressao}"
                for r in resultados
            )
            return await interaction.response.send_message(msg)

        res = await asyncio.to_thread(rolar_dado, expressao, True)
        if res is None:
            return await interaction.response.send_message("❌ Expressão inválida!", ephemeral=True)

        msg = f"``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', expressao)}"
        return await interaction.response.send_message(msg)

    # ---------- Shippar ----------
    @app_commands.command(name="shippar", description="Calcula a chance de 2 usuários ficarem juntos")
    @app_commands.describe(nome1="Primeiro nome", nome2="Segundo nome")
    async def shippar(self, interaction: discord.Interaction, nome1: str, nome2: str):
        await interaction.response.send_message(
            f"{nome1.capitalize()} e {nome2.capitalize()} tem {calcular_compatibilidade(nome1, nome2)}"
        )

    # ---------- Deepfry ----------
    @app_commands.command(name="deepfry", description="Aplica o efeito deep fry em uma imagem.")
    @app_commands.describe(imagem="Imagem para aplicar o efeito deep fry")
    async def deepfry(self, interaction: discord.Interaction, imagem: discord.Attachment):
        await interaction.response.defer()

        try:
            img_bytes = await imagem.read()
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            img = ImageEnhance.Contrast(img).enhance(4.0)
            img = ImageEnhance.Sharpness(img).enhance(12.0)
            img = ImageEnhance.Color(img).enhance(8.0)
            img = ImageEnhance.Brightness(img).enhance(1.5)

            overlay = Image.new("RGB", img.size, (255, 0, 0))
            img = Image.blend(img, overlay, alpha=0.2)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=10)
            buffer.seek(0)

            await interaction.followup.send(
                "🧨 **Imagem deep fried com sucesso!**",
                file=discord.File(buffer, filename="deepfried.jpg"),
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao aplicar o efeito: {e}", ephemeral=True)

    # ---------- Hypertranslate ----------
    @app_commands.command(
        name="hypertranslate",
        description="Traduz um texto por várias línguas aleatórias e retorna o resultado final.",
    )
    @app_commands.describe(
        texto="Texto original para traduzir",
        vezes="Quantidade de vezes a traduzir (máximo 50)",
        idioma_entrada="Idioma original do texto (ou auto para detectar)",
        idioma_saida="Idioma final do texto traduzido",
    )
    @app_commands.choices(
        idioma_entrada=[app_commands.Choice(name=nome, value=cod) for nome, cod in POPULAR_LANGUAGES.items()],
        idioma_saida=[app_commands.Choice(name=nome, value=cod) for nome, cod in POPULAR_LANGUAGES.items()],
    )
    async def hypertranslate(
        self,
        interaction: discord.Interaction,
        texto: str,
        vezes: app_commands.Range[int, 1, 50] = 10,
        idioma_entrada: Optional[app_commands.Choice[str]] = None,
        idioma_saida: Optional[app_commands.Choice[str]] = None,
    ):
        await interaction.response.defer()

        if GoogleTranslator is None:
            return await interaction.followup.send(
                "❌ `deep-translator` não está instalado. Instale com: `pip install deep-translator`",
                ephemeral=True,
            )

        entrada = idioma_entrada.value if idioma_entrada else "auto"
        saida = idioma_saida.value if idioma_saida else entrada

        if self.cached_supported_languages is None:
            # isso pode demorar um pouco (rede)
            self.cached_supported_languages = GoogleTranslator().get_supported_languages(as_dict=True)

        lang_codes = list(self.cached_supported_languages.values())
        atual = texto
        usado: List[str] = []

        try:
            for _ in range(vezes):
                destino = random.choice(lang_codes)
                while destino in usado or destino == entrada or destino == "auto":
                    destino = random.choice(lang_codes)
                usado.append(destino)

                try:
                    atual = await asyncio.to_thread(GoogleTranslator, source="auto", target=destino).translate(atual)
                    if not atual:
                        raise ValueError(f"Tradução vazia para {destino}.")
                except Exception as e:
                    await interaction.followup.send(f"❌ Erro ao traduzir para `{destino}`: {e}", ephemeral=True)
                    return

                await asyncio.sleep(0.3)

            final = await asyncio.to_thread(GoogleTranslator, source="auto", target=saida).translate(atual)

            await interaction.followup.send(
                "🌐 **Tradução concluída!**\n"
                f"🔤 **Texto original:** {texto}\n"
                f"📊 **Rodadas:** {vezes}\n"
                f"**Idioma de entrada:** `{entrada}`\n"
                f"**Idioma final:** `{saida}`\n"
                f"🔁 **Texto final:**\n```{final}```"
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Ocorreu um erro durante as traduções: {e}", ephemeral=True)

    # ---------- Lápide ----------
    @app_commands.command(name="lapide", description="Cria uma lápide com o nome de alguém ou texto personalizado.")
    @app_commands.describe(usuario="(Opcional) Alvo da lápide", texto="(Opcional) Texto a ser escrito na lápide")
    async def lapide(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None, texto: Optional[str] = None):
        nome_final = texto if texto else (usuario.display_name if usuario else "Desconhecido")
        await interaction.response.defer()

        try:
            caminho_imagem = "assets/images/grave.png"
            caminho_fonte = "assets/fonts/PTSerif-Bold.ttf"

            if not os.path.exists(caminho_imagem):
                return await interaction.followup.send("❌ O arquivo `assets/images/grave.png` não foi encontrado!", ephemeral=True)
            if not os.path.exists(caminho_fonte):
                return await interaction.followup.send("❌ O arquivo `assets/fonts/PTSerif-Bold.ttf` não foi encontrado!", ephemeral=True)

            img = Image.open(caminho_imagem).convert("RGBA")
            fonte = ImageFont.truetype(caminho_fonte, 50)

            text_layer = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(text_layer)

            bbox = fonte.getbbox(nome_final)
            w_text = bbox[2] - bbox[0]
            h_text = bbox[3] - bbox[1]
            x_center = (600 - w_text) // 2
            y_center = (200 - h_text) // 2

            draw.text((x_center, y_center), nome_final, font=fonte, fill=(50, 50, 50, 180))

            rotated = text_layer.rotate(3.5, expand=True, resample=Image.BICUBIC)

            pos_x, pos_y = 160, 400
            w_rot, h_rot = rotated.size
            area_crop = img.crop((pos_x, pos_y, pos_x + w_rot, pos_y + h_rot))
            blended = ImageChops.multiply(area_crop, rotated)
            img.paste(blended, (pos_x, pos_y), rotated)

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            await interaction.followup.send(
                content=f"🪦 Aqui jaz **{nome_final}**...",
                file=discord.File(fp=buffer, filename="lapide.png"),
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao gerar a lápide: {e}", ephemeral=True)

    # ---------- ASCII ----------
    @app_commands.command(name="ascii", description="Gera uma arte ASCII com o texto e fonte escolhidos.")
    @app_commands.describe(texto="Texto para converter em arte ASCII", fonte="Fonte para a arte ASCII (opcional)")
    @app_commands.choices(fonte=[app_commands.Choice(name=f, value=f) for f in FONTES_DISPONIVEIS])
    async def ascii(self, interaction: discord.Interaction, texto: str, fonte: Optional[app_commands.Choice[str]] = None):
        try:
            fonte_escolhida = fonte.value if fonte else "standard"
            if fonte_escolhida not in FONTES_DISPONIVEIS:
                fonte_escolhida = "standard"

            arte = pyfiglet.figlet_format(texto, font=fonte_escolhida, width=50)
            if len(arte) > 2000:
                return await interaction.response.send_message("❌ O resultado é muito grande para enviar no Discord!", ephemeral=True)

            await interaction.response.send_message(f"```\n{arte}\n```")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao gerar a arte ASCII: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Misc(bot))