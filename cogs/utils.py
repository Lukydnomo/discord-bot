import discord
from discord import app_commands
from discord.ext import commands
import re
import ast
import operator as op

# IDs fixos
BOARD_CHANNEL_ID = 1472670458993446922
DEST_CHANNEL_ID = 1472671366183649462
PING_USER_ID = 767015394648915978

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
            dest = interaction.client.get_channel(DEST_CHANNEL_ID)
            if dest is None:
                dest = await interaction.client.fetch_channel(DEST_CHANNEL_ID)

            await dest.send(f"<@{PING_USER_ID}> Música {self.number}")

            # responde o clique
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

    @app_commands.command(name="calcular_dt_ritual", description="Calcula os dados de teste (DT) para um ritual.")
    @app_commands.describe(atributo="Valor do atributo a ser calculado.", ocultismo="Valor do ocultismo a ser calculado.")
    async def calcular_dt_ritual(self, interaction: discord.Interaction, atributo: int, ocultismo: int):
        dt = 10 + atributo + ocultismo
        await interaction.response.send_message(f"Sua DT de ritual é {dt}.")

    @app_commands.command(name="hexatombe_musics", description="Posta um embed com 48 botões numerados de 1 a 48.")
    async def postar_botoes(self, interaction: discord.Interaction):
        BOARD_CHANNEL_ID = 1472670458993446922

        await interaction.response.defer(thinking=True, ephemeral=True)

        board = self.bot.get_channel(BOARD_CHANNEL_ID)
        if board is None:
            board = await self.bot.fetch_channel(BOARD_CHANNEL_ID)

        batches = [(1, 24), (25, 48)]
        for batch_idx, (start, end) in enumerate(batches, start=1):
            batch_embed = discord.Embed(
                title=f"Escolha um número (parte {batch_idx}/{len(batches)})",
                description="Clique em um número abaixo.",
                color=discord.Color.blurple(),
            )
            await board.send(embed=batch_embed, view=HexaMusicView(start, end))

        await interaction.followup.send("Embed(s) com botões enviado(s) com sucesso.", ephemeral=True)
    
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


async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))

    if not getattr(bot, "_hexatombe_views_registered", False):
        bot.add_view(HexaMusicView(1, 24))
        bot.add_view(HexaMusicView(25, 48))
        bot._hexatombe_views_registered = True