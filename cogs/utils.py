import discord
from discord import app_commands
from discord.ext import commands
import re
import ast
import operator as op
import asyncio
import unicodedata
from typing import Dict, Tuple, List, Optional

from core.modules import get_file_content, update_file_content, rolar_dado


# =========================
# REFERÊNCIAS (DB)
# =========================

REF_TERM_RE = re.compile(r"^[a-zA-ZÀ-ÿ0-9 _\-]{1,40}$")
MAX_REF_NOTES = 2000
MAX_REF_FONTE = 40
MAX_REF_TAGS = 8
MAX_REF_ALIASES = 8

def _norm_term(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _term_id(s: str) -> str:
    """Generate a normalized identifier from a term.

    The result is lowercase, ASCII (diacritics removed), and uses
    underscores instead of spaces. This is used as the key in the
    reference buckets so that terms like "Conjuração Complexa" and
    "conjuracao complexa" collide correctly and avoid duplicates.
    """
    norm = _norm_term(s)
    # remove accents/diacritics
    norm = ''.join(ch for ch in unicodedata.normalize('NFD', norm)
                   if unicodedata.category(ch) != 'Mn')
    # spaces become underscores
    norm = re.sub(r"\s+", "_", norm)
    return norm

def _parse_tags(tags: str) -> List[str]:
    if not tags:
        return []
    # aceita "#tag #outra" ou "tag, outra"
    raw = re.split(r"[,\s]+", tags.strip())
    out = []
    for t in raw:
        t = t.strip().lower()
        if not t:
            continue
        if t.startswith("#"):
            t = t[1:]
        t = re.sub(r"[^a-z0-9_\-à-ÿ]", "", t)
        if t and t not in out:
            out.append(t)
        if len(out) >= MAX_REF_TAGS:
            break
    return out

def _parse_aliases(aliases: str) -> List[str]:
    # store aliases in id form so lookups behave uniformly
    if not aliases:
        return []
    raw = re.split(r"[,\n;]+", aliases.strip())
    out = []
    for a in raw:
        aid = _term_id(a)
        if not aid:
            continue
        if aid not in out:
            out.append(aid)
        if len(out) >= MAX_REF_ALIASES:
            break
    return out

def _ensure_ref_root(data: dict) -> dict:
    refs = data.get("refs")
    if not isinstance(refs, dict):
        refs = {}
        data["refs"] = refs
    if not isinstance(refs.get("user"), dict):
        refs["user"] = {}
    if not isinstance(refs.get("guild"), dict):
        refs["guild"] = {}
    return refs

def _get_ref_bucket(refs: dict, scope: str, scope_id: int) -> Dict[str, dict]:
    bucket = refs[scope].get(str(scope_id))
    if not isinstance(bucket, dict):
        bucket = {}
        refs[scope][str(scope_id)] = bucket
    return bucket

def _find_ref(bucket: Dict[str, dict], term: str) -> Optional[Tuple[str, dict]]:
    """Procura por um *id* dentro do bucket.

    "term" **must** already be converted with :func:`_term_id`.  The
    bucket keys are stored in that format and aliases are saved the same
    way, so this function is a simple lookup.
    """
    if term in bucket:
        return term, bucket[term]

    # busca por alias (já estão no formato id)
    for k, obj in bucket.items():
        if not isinstance(obj, dict):
            continue
        aliases = obj.get("aliases", [])
        if isinstance(aliases, list) and term in aliases:
            return k, obj

    return None

####################################################
####################################################
####################################################

# nomes: atk, dano-espada, rifle_01 etc
MACRO_NAME_RE = re.compile(r"^[a-z0-9_-]{1,24}$", re.I)

# expressão bem restrita pra não deixar coisa perigosa passar pro eval do rolar_dado
SAFE_EXPR_RE = re.compile(r"^[0-9dD#+\-*/().\s:;=_\n]+$")

MAX_MACRO_LEN = 400
MAX_PARTS = 10

def _normalize_name(name: str) -> str:
    return name.strip().lower()


def _expand_template(template: str, args: List[str]) -> str:
    # $1..$9 e $* (tudo)
    out = template
    for i in range(1, 10):
        token = f"${i}"
        if token in out:
            out = out.replace(token, args[i - 1] if i - 1 < len(args) else "")
    out = out.replace("$*", " ".join(args))
    return out


def _ensure_macro_root(data: dict) -> dict:
    macros = data.get("macros")
    if not isinstance(macros, dict):
        macros = {}
        data["macros"] = macros
    if not isinstance(macros.get("user"), dict):
        macros["user"] = {}
    if not isinstance(macros.get("guild"), dict):
        macros["guild"] = {}
    return macros


def _get_scope_bucket(macros: dict, scope: str, scope_id: int) -> Dict[str, str]:
    # scope: "user" ou "guild"
    bucket = macros[scope].get(str(scope_id))
    if not isinstance(bucket, dict):
        bucket = {}
        macros[scope][str(scope_id)] = bucket
    return bucket


def _split_parts(expanded: str) -> List[str]:
    # separa por ; ou \n
    raw = re.split(r"[;\n]+", expanded)
    parts = [p.strip() for p in raw if p.strip()]
    return parts[:MAX_PARTS]


def _parse_labeled_expr(part: str) -> Tuple[Optional[str], str]:
    # aceita "label: expr" ou "label=expr"
    m = re.match(r"^([a-zA-ZÀ-ÿ0-9 _-]{1,20})\s*[:=]\s*(.+)$", part.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, part.strip()

####################################################
####################################################
####################################################

# helpers para ler configurações de guild (sincrono/async)
def _get_guild_cfg_sync(guild_id: int) -> dict:
    data = get_file_content()
    if not isinstance(data, dict):
        return {}
    gc = data.get("guild_config", {})
    if not isinstance(gc, dict):
        return {}
    b = gc.get(str(guild_id), {})
    return b if isinstance(b, dict) else {}


async def _get_guild_cfg(guild_id: int) -> dict:
    return await asyncio.to_thread(_get_guild_cfg_sync)


async def _fetch_text_channel(client: discord.Client, channel_id: int) -> Optional[discord.TextChannel]:
    ch = client.get_channel(channel_id)
    if ch is None:
        try:
            ch = await client.fetch_channel(channel_id)
        except Exception:
            return None
    return ch if isinstance(ch, discord.TextChannel) else None

class HexaMusicButton(discord.ui.Button):
    def __init__(self, number: int, row: int):
        super().__init__(
            label=str(number),
            style=discord.ButtonStyle.primary,
            custom_id=f"num_button_{number}",  # <- IGUAL ao que você já usava
            row=row,
        )
        self.number = number

    async def callback(self, interaction: discord.Interaction):
        try:
            if interaction.guild is None:
                return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

            cfg = await _get_guild_cfg(interaction.guild.id)

            dest_id = cfg.get("hexatombe_dest_channel_id")
            if not dest_id:
                return await interaction.response.send_message(
                    "❌ Hexatombê não configurado.\nUse: `/config hexatombe painel:#canal destino:#canal pingar:@alguem(opcional)`",
                    ephemeral=True
                )

            dest = await _fetch_text_channel(interaction.client, int(dest_id))
            if dest is None:
                return await interaction.response.send_message("❌ Canal de destino inválido/sem acesso.", ephemeral=True)

            ping_id = cfg.get("hexatombe_ping_user_id")
            mention = f"<@{int(ping_id)}> " if ping_id else ""

            await dest.send(f"{mention}Música {self.number}")

            if interaction.response.is_done():
                await interaction.followup.send(f"Número {self.number} enviado.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Número {self.number} enviado.", ephemeral=True)

        except Exception:
            msg = "Falha ao enviar o número. Verifique permissões."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)


class HexaMusicView(discord.ui.View):
    def __init__(self, start: int, end: int):
        super().__init__(timeout=None)  # <- obrigatório pra persistir
        for idx, n in enumerate(range(start, end + 1)):
            self.add_item(HexaMusicButton(n, row=idx // 5))



############################################
# __   __  _______  ___   ___      _______ #
#|  | |  ||       ||   | |   |    |       |#
#|  | |  ||_     _||   | |   |    |  _____|#
#|  |_|  |  |   |  |   | |   |    | |_____ #
#|       |  |   |  |   | |   |___ |_____  |#
#|       |  |   |  |   | |       | _____| |#
#|_______|  |___|  |___| |_______||_______|#
############################################
############################################

class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    # Operadores permitidos (calculadora segura)
    allowed_operators = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.USub: op.neg,
        ast.UAdd: op.pos,
    }

    def eval_expr(self, expr: str):
        def _eval(node):
            # Python 3.8+: números vêm como ast.Constant
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value

            # Compat com versões antigas
            if isinstance(node, ast.Num):
                return node.n

            if isinstance(node, ast.BinOp):
                op_type = type(node.op)
                if op_type not in self.allowed_operators:
                    raise TypeError("Operador inválido.")
                return self.allowed_operators[op_type](_eval(node.left), _eval(node.right))

            if isinstance(node, ast.UnaryOp):
                op_type = type(node.op)
                if op_type not in self.allowed_operators:
                    raise TypeError("Operador inválido.")
                return self.allowed_operators[op_type](_eval(node.operand))

            raise TypeError("Expressão inválida.")

        return _eval(ast.parse(expr, mode="eval").body)



#######################################################################


#######################################################################



    @app_commands.command(name="converter_sanidade_para_pd", description="Converte valores de Sanidade para Pontos de Determinação.")
    @app_commands.describe(sanidade="Valor de Sanidade a ser convertido.")
    async def converter_sanidade_para_pd(self, interaction: discord.Interaction, sanidade: int):
        """
        Converte um valor de sanidade para pontos de dano (PD) usando a fórmula:
        Para cada 3 pontos de sanidade, o usuário recebe 2 pontos de dano.

        Args:
            interaction (discord.Interaction): A interação do comando.
            sanidade (int): O valor de sanidade a ser convertido.

        Returns:
            None
        """
        pd = int((sanidade * 0.43) + 0.5)
        await interaction.response.send_message(f"O valor convertido de {sanidade} sanidade é {pd} pontos de determinação (PD).")


#######################################################################


#######################################################################


    @app_commands.command(name="calcular_pd", description="Calcula os pontos de determinação (PD)")
    @app_commands.describe(classe="Indica a classe do personagem.",
                           nex="Indica o quanto de exposição paranormal ele tem.",
                           atributo="Valor do atributo a ser calculado.",
                           tem_potencial_aprimorado="Indica se o personagem tem potencial aprimorado (sim/não).",
                           com_afinidade_com_morte="Indica se o personagem tem afinidade com Morte (sim/não).",
                           com_cicatrizes_psicológicas="Indica se o personagem tem cicatrizes psicológicas (sim/não).")
    @app_commands.choices(classe=[
        app_commands.Choice(name="Combatente", value="Combatente"),
        app_commands.Choice(name="Especialista", value="Especialista"),
        app_commands.Choice(name="Ocultista", value="Ocultista")
    ],tem_potencial_aprimorado=[
        app_commands.Choice(name="Sim", value=1),
        app_commands.Choice(name="Não", value=0)
    ], com_afinidade_com_morte=[
        app_commands.Choice(name="Sim", value=1),
        app_commands.Choice(name="Não", value=0)
    ], com_cicatrizes_psicológicas=[
        app_commands.Choice(name="Sim", value=1),
        app_commands.Choice(name="Não", value=0)
    ])
    async def calcular_pd(self, interaction: discord.Interaction,
                          classe: str,
                          nex: int,
                          atributo: int,
                          tem_potencial_aprimorado: app_commands.Choice[int],
                          com_afinidade_com_morte: app_commands.Choice[int],
                          com_cicatrizes_psicológicas: app_commands.Choice[int]):
        
        """
         Combatente. PD Iniciais: 6 + Pre. A cada novo NEX: 3 + Pre.
         
         Especialista. PD Iniciais: 8 + Pre. A cada novo NEX: 4 + Pre.

         Ocultista. PD Iniciais: 10 + Pre. A cada
         novo NEX: 5 + Pre.
        """

        nex_base = 100 if nex == 99 else nex
        nex_pos = nex_base // 5

        base_por_classe = {
            "Combatente": 6,
            "Especialista": 8,
            "Ocultista": 10
        }

        ganho_por_classe ={
            "Combatente": 3,
            "Especialista": 4,
            "Ocultista": 5
        }

        pre_pd = base_por_classe[classe] + atributo + ((nex_pos - 1) * (ganho_por_classe[classe] + atributo))

        if tem_potencial_aprimorado.value == 1:
            multiplicador = 2 if com_afinidade_com_morte.value == 1 else 1
            pre_pd += nex_pos * multiplicador

        if com_cicatrizes_psicológicas.value == 1:
            pre_pd += int((nex_pos*0.43)+0.5)

        pd = pre_pd

        await interaction.response.send_message(f"O valor é {pd} pontos de determinação (PD).")


#######################################################################


#######################################################################


    @app_commands.command(name="calcular_dt_ritual", description="Calcula os dados de teste (DT) para um ritual.")
    @app_commands.describe(atributo="Valor do atributo a ser calculado.", ocultismo="Valor do ocultismo a ser calculado.")
    async def calcular_dt_ritual(self, interaction: discord.Interaction, atributo: int, ocultismo: int):
        dt = 10 + atributo + ocultismo
        await interaction.response.send_message(f"Sua DT de ritual é {dt}.")

    @app_commands.command(name="hexatombe_musics", description="Posta um embed com 48 botões numerados de 1 a 48.")
    async def postar_botoes(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        # (recomendo) trava pra Manage Guild
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                "❌ Pra postar o painel, precisa permissão **Gerenciar Servidor**.",
                ephemeral=True
            )

        await interaction.response.defer(thinking=True, ephemeral=True)

        cfg = await _get_guild_cfg(interaction.guild.id)
        board_id = cfg.get("hexatombe_board_channel_id")
        if not board_id:
            return await interaction.followup.send(
                "❌ Hexatombê não configurado.\nUse: `/config hexatombe painel:#canal destino:#canal pingar:@alguem(opcional)`",
                ephemeral=True
            )

        board = await _fetch_text_channel(self.bot, int(board_id))
        if board is None:
            return await interaction.followup.send("❌ Canal do painel inválido/sem acesso.", ephemeral=True)

        

        batches = [(1, 24), (25, 48)]
        for batch_idx, (start, end) in enumerate(batches, start=1):
            batch_embed = discord.Embed(
                title=f"Escolha um número (parte {batch_idx}/{len(batches)})",
                description="Clique em um número abaixo.",
                color=discord.Color.blurple(),
            )
            await board.send(embed=batch_embed, view=HexaMusicView(start, end))

        await interaction.followup.send("Embed(s) com botões enviado(s) com sucesso.", ephemeral=True)
    

#######################################################################


#######################################################################


    @app_commands.command(
        name="calcular_dano_medio",
        description="Calcula o dano médio com base em uma expressão de dados."
    )
    @app_commands.describe(
        expressao="Ex: 3d8+10, 10d8+4d6, 5d20+(3d10*2)"
    )
    async def calcular_dano_medio(self, interaction: discord.Interaction, expressao: str):
        try:
            expr = expressao.lower().replace(" ", "")
    
            # Substitui XdY pelo dano médio matemático
            def substituir_dados(match):
                x = int(match.group(1))
                y = int(match.group(2))
                if x <= 0 or y <= 0:
                    raise ValueError("Número de dados e faces deve ser positivo.")
                return f"({x}*({y}+1)/2)"
    
            expr_convertida = re.sub(r'(\d+)d(\d+)', substituir_dados, expr)
    
            resultado = self.eval_expr(expr_convertida)

            await interaction.response.send_message(
                f"🎲 Dano médio para `{expressao}`:\n**{resultado:.2f}**"
            )

        except Exception as e:
            await interaction.response.send_message(
                f"Erro ao calcular dano médio: {e}"
            )


#######################################################################


#######################################################################


    macro = app_commands.Group(name="macro", description="Macros de rolagem (atalhos)")

    @macro.command(name="set", description="Salva uma macro (atalho de rolagem).")
    @app_commands.describe(
        nome="Ex: atk, dano, furtividade",
        template="Ex: atk: 3d20+$1; dano: 2d8+$2  | Use $1..$9 e $*",
        escopo="Pessoal (só você) ou Servidor (pra mesa)"
    )
    @app_commands.choices(escopo=[
        app_commands.Choice(name="Pessoal", value="user"),
        app_commands.Choice(name="Servidor", value="guild"),
    ])
    async def macro_set(
        self,
        interaction: discord.Interaction,
        nome: str,
        template: str,
        escopo: app_commands.Choice[str],
    ):
        nome_n = _normalize_name(nome)

        if not MACRO_NAME_RE.fullmatch(nome_n):
            return await interaction.response.send_message(
                "❌ Nome inválido. Use só letras/números/_/- (até 24 chars).",
                ephemeral=True
            )

        if len(template) > MAX_MACRO_LEN:
            return await interaction.response.send_message(
                f"❌ Macro grande demais (máx {MAX_MACRO_LEN} chars).",
                ephemeral=True
            )

        if not SAFE_EXPR_RE.fullmatch(template):
            return await interaction.response.send_message(
                "❌ Template contém caracteres não permitidos (por segurança).",
                ephemeral=True
            )

        scope = escopo.value
        if scope == "guild":
            if interaction.guild is None:
                return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)
            # trava "escopo servidor" pra quem tem Manage Guild (evita bagunça)
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message(
                    "❌ Pra salvar macro no servidor, precisa permissão **Gerenciar Servidor**.",
                    ephemeral=True
                )
            scope_id = interaction.guild.id
        else:
            scope_id = interaction.user.id

        def _write():
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}
            macros = _ensure_macro_root(data)
            bucket = _get_scope_bucket(macros, scope, scope_id)
            bucket[nome_n] = template.strip()
            update_file_content(data)

        await asyncio.to_thread(_write)

        await interaction.response.send_message(
            f"✅ Macro `{nome_n}` salva no escopo **{escopo.name}**.",
            ephemeral=True
        )


    @macro.command(name="usar", description="Usa uma macro salva.")
    @app_commands.describe(
        nome="Nome da macro",
        args="Argumentos (separados por espaço). Ex: 5 3",
        oculto="Se True, responde só pra você (ephemeral)."
    )
    async def macro_usar(
        self,
        interaction: discord.Interaction,
        nome: str,
        args: str = "",
        oculto: bool = False,
    ):
        nome_n = _normalize_name(nome)
        arglist = [a for a in args.split(" ") if a.strip()]

        def _read_template() -> Optional[str]:
            data = get_file_content()
            if not isinstance(data, dict):
                return None
            macros = data.get("macros", {})
            if not isinstance(macros, dict):
                return None

            # prioridade: pessoal > servidor
            user_bucket = (((macros.get("user") or {}).get(str(interaction.user.id))) or {})
            if isinstance(user_bucket, dict) and nome_n in user_bucket:
                return user_bucket[nome_n]

            if interaction.guild is not None:
                guild_bucket = (((macros.get("guild") or {}).get(str(interaction.guild.id))) or {})
                if isinstance(guild_bucket, dict) and nome_n in guild_bucket:
                    return guild_bucket[nome_n]

            return None

        template = _read_template()
        if not template:
            return await interaction.response.send_message(
                f"❌ Macro `{nome_n}` não encontrada (nem pessoal nem do servidor).",
                ephemeral=True
            )

        expanded = _expand_template(template, arglist)
        parts = _split_parts(expanded)

        # valida cada parte antes de rolar
        for p in parts:
            _, expr = _parse_labeled_expr(p)
            if not SAFE_EXPR_RE.fullmatch(expr):
                return await interaction.response.send_message(
                    "❌ A macro expandiu para algo com caracteres inválidos (bloqueado por segurança).",
                    ephemeral=True
                )

        # rola tudo
        resultados = []
        for p in parts:
            label, expr = _parse_labeled_expr(p)
            res = await asyncio.to_thread(rolar_dado, expr, True)
            if res is None:
                resultados.append(f"❌ Falha ao rolar: `{expr}`")
                continue

            prefix = f"**{label}**: " if label else ""
            resultados.append(
                f"{prefix}``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', expr)}"
            )

        await interaction.response.send_message("\n".join(resultados), ephemeral=oculto)


    @macro.command(name="list", description="Lista suas macros (e/ou as do servidor).")
    @app_commands.describe(escopo="Pessoal / Servidor / Ambos")
    @app_commands.choices(escopo=[
        app_commands.Choice(name="Pessoal", value="user"),
        app_commands.Choice(name="Servidor", value="guild"),
        app_commands.Choice(name="Ambos", value="both"),
    ])
    async def macro_list(self, interaction: discord.Interaction, escopo: app_commands.Choice[str]):
        data = get_file_content()
        macros = (data or {}).get("macros", {}) if isinstance(data, dict) else {}
        if not isinstance(macros, dict):
            macros = {}

        lines = []

        if escopo.value in ("user", "both"):
            user_bucket = (((macros.get("user") or {}).get(str(interaction.user.id))) or {})
            if isinstance(user_bucket, dict) and user_bucket:
                lines.append("**Pessoal:** " + ", ".join(f"`{k}`" for k in sorted(user_bucket.keys())))
            else:
                lines.append("**Pessoal:** (vazio)")

        if escopo.value in ("guild", "both"):
            if interaction.guild is None:
                lines.append("**Servidor:** (fora de servidor)")
            else:
                guild_bucket = (((macros.get("guild") or {}).get(str(interaction.guild.id))) or {})
                if isinstance(guild_bucket, dict) and guild_bucket:
                    lines.append("**Servidor:** " + ", ".join(f"`{k}`" for k in sorted(guild_bucket.keys())))
                else:
                    lines.append("**Servidor:** (vazio)")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


    @macro.command(name="show", description="Mostra o template salvo de uma macro.")
    @app_commands.describe(nome="Nome da macro")
    async def macro_show(self, interaction: discord.Interaction, nome: str):
        nome_n = _normalize_name(nome)

        data = get_file_content()
        macros = (data or {}).get("macros", {}) if isinstance(data, dict) else {}
        if not isinstance(macros, dict):
            macros = {}

        user_bucket = (((macros.get("user") or {}).get(str(interaction.user.id))) or {})
        if isinstance(user_bucket, dict) and nome_n in user_bucket:
            return await interaction.response.send_message(
                f"**{nome_n}** (Pessoal):\n```{user_bucket[nome_n]}```",
                ephemeral=True
            )

        if interaction.guild is not None:
            guild_bucket = (((macros.get("guild") or {}).get(str(interaction.guild.id))) or {})
            if isinstance(guild_bucket, dict) and nome_n in guild_bucket:
                return await interaction.response.send_message(
                    f"**{nome_n}** (Servidor):\n```{guild_bucket[nome_n]}```",
                    ephemeral=True
                )

        await interaction.response.send_message(f"❌ Macro `{nome_n}` não encontrada.", ephemeral=True)


    @macro.command(name="del", description="Apaga uma macro.")
    @app_commands.describe(
        nome="Nome da macro",
        escopo="Se não passar, tenta apagar pessoal e depois servidor."
    )
    @app_commands.choices(escopo=[
        app_commands.Choice(name="Auto", value="auto"),
        app_commands.Choice(name="Pessoal", value="user"),
        app_commands.Choice(name="Servidor", value="guild"),
    ])
    async def macro_del(
        self,
        interaction: discord.Interaction,
        nome: str,
        escopo: app_commands.Choice[str],
    ):
        nome_n = _normalize_name(nome)

        if escopo.value == "guild":
            if interaction.guild is None:
                return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message(
                    "❌ Pra apagar macro do servidor, precisa **Gerenciar Servidor**.",
                    ephemeral=True
                )

        def _delete() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                return False
            macros = _ensure_macro_root(data)

            deleted = False

            def del_from(scope: str, sid: int):
                nonlocal deleted
                bucket = macros.get(scope, {}).get(str(sid))
                if isinstance(bucket, dict) and nome_n in bucket:
                    del bucket[nome_n]
                    deleted = True

            if escopo.value in ("auto", "user"):
                del_from("user", interaction.user.id)

            if escopo.value in ("auto", "guild") and interaction.guild is not None:
                del_from("guild", interaction.guild.id)

            if deleted:
                update_file_content(data)
            return deleted

        ok = await asyncio.to_thread(_delete)
        if ok:
            await interaction.response.send_message(f"🗑️ Macro `{nome_n}` apagada.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Não achei `{nome_n}` pra apagar.", ephemeral=True)


#######################################################################


#######################################################################


    # =========================
    # /ref (Referências)
    # =========================
    ref = app_commands.Group(name="ref", description="Referências rápidas (apelidos → fonte/página/notas)")

    @ref.command(name="add", description="Salva uma referência (apelido → fonte/página/notas).")
    @app_commands.describe(
        termo="Ex: debilitado, perseguição, ritual retido",
        fonte="Ex: Ordem, SaH, Arquivos Secretos",
        pagina="Página do PDF/livro (número)",
        notas="Resumo curtinho (evita colar texto longo do livro)",
        tags="Ex: #condicao #ritual (opcional)",
        aliases="Sinônimos separados por vírgula (opcional). Ex: debil, deb"
    )
    @app_commands.choices(escopo=[
        app_commands.Choice(name="Servidor", value="guild"),
        app_commands.Choice(name="Pessoal", value="user"),
    ])
    async def ref_add(
        self,
        interaction: discord.Interaction,
        termo: str,
        fonte: str,
        pagina: int,
        notas: str,
        escopo: app_commands.Choice[str],
        tags: str = "",
        aliases: str = "",
    ):
        # prepare both a canonical id and keep the original display name
        termo_id = _term_id(termo)
        display = termo.strip()

        # validate id
        if not termo_id or len(termo_id) > 40 or not re.fullmatch(r"[a-z0-9_\-]+", termo_id):
            return await interaction.response.send_message(
                "❌ Termo inválido. Usa até 40 chars e só letras/números/_/- (acento será removido).",
                ephemeral=True
            )

        fonte_n = (fonte or "").strip()
        if not fonte_n or len(fonte_n) > MAX_REF_FONTE:
            return await interaction.response.send_message(
                f"❌ Fonte inválida (1–{MAX_REF_FONTE} chars).",
                ephemeral=True
            )

        if pagina < 1 or pagina > 5000:
            return await interaction.response.send_message("❌ Página inválida.", ephemeral=True)

        notas_n = (notas or "").strip()
        if not notas_n:
            return await interaction.response.send_message("❌ Notas não podem ficar vazias.", ephemeral=True)
        if len(notas_n) > MAX_REF_NOTES:
            return await interaction.response.send_message(
                f"❌ Notas muito longas (máx {MAX_REF_NOTES} chars).",
                ephemeral=True
            )

        scope = escopo.value
        if scope == "guild":
            if interaction.guild is None:
                return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message(
                    "❌ Pra salvar no servidor, precisa permissão **Gerenciar Servidor**.",
                    ephemeral=True
                )
            scope_id = interaction.guild.id
        else:
            scope_id = interaction.user.id

        tags_list = _parse_tags(tags)
        aliases_list = _parse_aliases(aliases)
        # don't let alias equal the main id (redundant)
        if termo_id in aliases_list:
            aliases_list.remove(termo_id)

        def _write():
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}
            refs = _ensure_ref_root(data)
            bucket = _get_ref_bucket(refs, scope, scope_id)

            # duplicate check: same id or same as someone's alias
            if termo_id in bucket:
                return False
            for k,obj in bucket.items():
                if isinstance(obj, dict):
                    aliases = obj.get("aliases", [])
                    if isinstance(aliases, list) and termo_id in aliases:
                        return False

            bucket[termo_id] = {
                "nome": display,
                "fonte": fonte_n,
                "pagina": int(pagina),
                "notas": notas_n,
                "tags": tags_list,
                "aliases": aliases_list,
                "by": int(interaction.user.id),
            }
            update_file_content(data)
            return True

        ok = await asyncio.to_thread(_write)
        if not ok:
            return await interaction.response.send_message(
                f"❌ Já existe referência `{display}`.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"✅ Referência `{display}` salva em **{escopo.name}**.",
            ephemeral=True
        )


    @ref.command(name="get", description="Mostra uma referência salva.")
    @app_commands.describe(termo="Termo/alias", oculto="Se True, só você vê (ephemeral).")
    async def ref_get(self, interaction: discord.Interaction, termo: str, oculto: bool = False):
        termo_id = _term_id(termo)

        def _read() -> Optional[Tuple[str, dict, str]]:
            data = get_file_content()
            if not isinstance(data, dict):
                return None
            refs = data.get("refs", {})
            if not isinstance(refs, dict):
                return None

            # prioridade: pessoal > servidor
            user_bucket = (((refs.get("user") or {}).get(str(interaction.user.id))) or {})
            if isinstance(user_bucket, dict):
                found = _find_ref(user_bucket, termo_id)
                if found:
                    key, obj = found
                    return key, obj, "Pessoal"

            if interaction.guild is not None:
                guild_bucket = (((refs.get("guild") or {}).get(str(interaction.guild.id))) or {})
                if isinstance(guild_bucket, dict):
                    found = _find_ref(guild_bucket, termo_id)
                    if found:
                        key, obj = found
                        return key, obj, "Servidor"

            return None

        got = await asyncio.to_thread(_read)
        if not got:
            return await interaction.response.send_message(
                f"❌ Não achei referência pra `{termo.strip()}`.",
                ephemeral=True
            )

        key, obj, scope_name = got
        fonte = obj.get("fonte", "—")
        display = obj.get("nome", key)
        pagina = obj.get("pagina", "—")
        notas = obj.get("notas", "—")
        tags = obj.get("tags", [])
        aliases = obj.get("aliases", [])

        emb = discord.Embed(
            title=f"📌 {display}",
            description=notas,
            color=discord.Color.blurple()
        )
        emb.add_field(name="Fonte", value=str(fonte), inline=True)
        emb.add_field(name="Página", value=str(pagina), inline=True)
        emb.add_field(name="Escopo", value=scope_name, inline=True)

        if isinstance(tags, list) and tags:
            emb.add_field(name="Tags", value=" ".join(f"`#{t}`" for t in tags[:MAX_REF_TAGS]), inline=False)

        if isinstance(aliases, list) and aliases:
            emb.add_field(name="Aliases", value=", ".join(f"`{a}`" for a in aliases[:MAX_REF_ALIASES]), inline=False)

        await interaction.response.send_message(embed=emb, ephemeral=oculto)


    @ref.command(name="search", description="Procura referências por termo/tag/fonte.")
    @app_commands.describe(query="Ex: debil, #condicao, sah, perseg")
    async def ref_search(self, interaction: discord.Interaction, query: str):
        q_norm = _norm_term(query)
        if not q_norm:
            return await interaction.response.send_message("❌ Query vazia.", ephemeral=True)
        q_id = _term_id(query)

        def _search() -> List[str]:
            data = get_file_content()
            if not isinstance(data, dict):
                return []
            refs = data.get("refs", {})
            if not isinstance(refs, dict):
                return []

            results = []
            qtag = q_norm[1:] if q_norm.startswith("#") else None

            def scan_bucket(bucket: Dict[str, dict], prefix: str):
                nonlocal results
                for term_key, obj in bucket.items():
                    if not isinstance(obj, dict):
                        continue
                    fonte = str(obj.get("fonte", "")).lower()
                    notas = str(obj.get("notas", "")).lower()
                    tags = obj.get("tags", [])
                    aliases = obj.get("aliases", [])

                    hit = False
                    if qtag:
                        if isinstance(tags, list) and qtag in tags:
                            hit = True
                    else:
                        # try both normalized forms against id/aliases and
                        # also match against display name, fonte and notas
                        if q_id in term_key or q_norm in term_key:
                            hit = True
                        elif isinstance(aliases, list) and (q_id in aliases or q_norm in aliases):
                            hit = True
                        elif q_norm in fonte or q_norm in notas or q_norm in str(obj.get("nome","")).lower():
                            hit = True
                        elif q_id in fonte or q_id in notas or q_id in str(obj.get("nome","")).lower():
                            hit = True

                    if hit:
                        display = obj.get("nome", term_key)
                        results.append(f"{prefix}`{display}` — {obj.get('fonte','—')} p.{obj.get('pagina','—')}")
                        if len(results) >= 10:
                            return

            # pessoal
            user_bucket = (((refs.get("user") or {}).get(str(interaction.user.id))) or {})
            if isinstance(user_bucket, dict):
                scan_bucket(user_bucket, "👤 ")

            # servidor
            if interaction.guild is not None and len(results) < 10:
                guild_bucket = (((refs.get("guild") or {}).get(str(interaction.guild.id))) or {})
                if isinstance(guild_bucket, dict):
                    scan_bucket(guild_bucket, "🏠 ")

            return results

        results = await asyncio.to_thread(_search)
        if not results:
            return await interaction.response.send_message("🔎 Nada encontrado.", ephemeral=True)

        await interaction.response.send_message("\n".join(results), ephemeral=True)


    @ref.command(name="list", description="Lista referências (pessoal/servidor).")
    @app_commands.choices(escopo=[
        app_commands.Choice(name="Pessoal", value="user"),
        app_commands.Choice(name="Servidor", value="guild"),
        app_commands.Choice(name="Ambos", value="both"),
    ])
    @app_commands.describe(escopo="Onde listar", fonte="Filtrar por fonte (opcional)", tag="Filtrar por tag (opcional, sem #)")
    async def ref_list(self, interaction: discord.Interaction, escopo: app_commands.Choice[str], fonte: str = "", tag: str = ""):
        fonte_q = (fonte or "").strip().lower()
        tag_q = (tag or "").strip().lower().lstrip("#")

        def _list() -> List[str]:
            data = get_file_content()
            if not isinstance(data, dict):
                return []
            refs = data.get("refs", {})
            if not isinstance(refs, dict):
                return []

            lines = []

            def add_terms(bucket: Dict[str, dict], header: str):
                nonlocal lines
                terms = []
                for k, obj in bucket.items():
                    if not isinstance(obj, dict):
                        continue
                    if fonte_q and fonte_q not in str(obj.get("fonte", "")).lower():
                        continue
                    if tag_q:
                        tags = obj.get("tags", [])
                        if not (isinstance(tags, list) and tag_q in tags):
                            continue
                    disp = obj.get("nome", k)
                    terms.append(disp)

                # append a line summarizing this bucket
                if terms:
                    lines.append(f"**{header}:** " + ", ".join(f"`{t}`" for t in sorted(terms)))
                else:
                    lines.append(f"**{header}:** (vazio)")

            if escopo.value in ("user", "both"):
                user_bucket = (((refs.get("user") or {}).get(str(interaction.user.id))) or {})
                if isinstance(user_bucket, dict):
                    add_terms(user_bucket, "Pessoal")

            if escopo.value in ("guild", "both"):
                if interaction.guild is None:
                    lines.append("**Servidor:** (fora de servidor)")
                else:
                    guild_bucket = (((refs.get("guild") or {}).get(str(interaction.guild.id))) or {})
                    if isinstance(guild_bucket, dict):
                        add_terms(guild_bucket, "Servidor")

            return lines

        lines = await asyncio.to_thread(_list)
        await interaction.response.send_message("\n".join(lines) if lines else "—", ephemeral=True)


    @ref.command(name="del", description="Apaga uma referência.")
    @app_commands.choices(escopo=[
        app_commands.Choice(name="Auto", value="auto"),
        app_commands.Choice(name="Pessoal", value="user"),
        app_commands.Choice(name="Servidor", value="guild"),
    ])
    @app_commands.describe(termo="Termo/alias", escopo="Auto tenta pessoal e depois servidor")
    async def ref_del(self, interaction: discord.Interaction, termo: str, escopo: app_commands.Choice[str]):
        termo_id = _term_id(termo)

        if escopo.value == "guild":
            if interaction.guild is None:
                return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message(
                    "❌ Pra apagar do servidor, precisa **Gerenciar Servidor**.",
                    ephemeral=True
                )

        def _delete() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                return False
            refs = _ensure_ref_root(data)

            deleted = False

            def del_from(scope: str, sid: int):
                nonlocal deleted
                bucket = refs.get(scope, {}).get(str(sid))
                if not isinstance(bucket, dict):
                    return

                # pode ser termo real ou alias
                found = _find_ref(bucket, termo_id)
                if found:
                    key, _obj = found
                    if key in bucket:
                        del bucket[key]
                        deleted = True

            if escopo.value in ("auto", "user"):
                del_from("user", interaction.user.id)

            if escopo.value in ("auto", "guild") and interaction.guild is not None:
                del_from("guild", interaction.guild.id)

            if deleted:
                update_file_content(data)

            return deleted

        ok = await asyncio.to_thread(_delete)
        if ok:
            await interaction.response.send_message(f"🗑️ Referência apagada: `{termo.strip()}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Não achei `{termo.strip()}` pra apagar.", ephemeral=True)


#######################################################################


#######################################################################


async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))

    if not getattr(bot, "_hexatombe_views_registered", False):
        bot.add_view(HexaMusicView(1, 24))
        bot.add_view(HexaMusicView(25, 48))
        bot._hexatombe_views_registered = True