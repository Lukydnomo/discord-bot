import discord
from discord import app_commands
from discord.ext import commands
import math

class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
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
        pd = int((sanidade / 3) * 2 + 0.5)
        await interaction.response.send_message(f"O valor convertido de {sanidade} sanidade é {pd} pontos de determinação (PD).")

    @app_commands.command(name="calcular_pd", description="Calcula os pontos de determinação (PD)")
    @app_commands.describe(classe="Indica a classe do personagem.", NEX="Indica o quanto de exposição paranormal ele tem.", atributo="Valor do atributo a ser calculado.", tem_potencial_aprimorado="Indica se o personagem tem potencial aprimorado (sim/não).", com_afinidade_com_morte="Indica se o personagem tem afinidade com Morte (sim/não).")
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
    ])
    async def calcular_pd(self, interaction: discord.Interaction, classe: str, nex: int, atributo: int, tem_potencial_aprimorado: app_commands.Choice[int], com_afinidade_com_morte: app_commands.Choice[int]):
        
        """
         Combatente. PD Iniciais: 6 + Pre. A cada novo NEX: 3 + Pre.
         
         Especialista. PD Iniciais: 8 + Pre. A cada novo NEX: 4 + Pre.

         Ocultista. PD Iniciais: 10 + Pre. A cada
         novo NEX: 5 + Pre.
        """

        nex_base = 95 if nex == 99 else nex
        nex_pos = (nex_base - 5) // 5

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

        pre_pd = base_por_classe[classe] + atributo + (nex_pos * (ganho_por_classe[classe] + atributo))

        if tem_potencial_aprimorado.value == 1:
            multiplicador = 2 if com_afinidade_com_morte == 1 else 1
            pre_pd += nex_pos * multiplicador

        pd = pre_pd

        await interaction.response.send_message(f"O valor é {pd} pontos de determinação (PD).")

    @app_commands.command(name="calcular_dt_ritual", description="Calcula os dados de teste (DT) para um ritual.")
    @app_commands.describe(atributo="Valor do atributo a ser calculado.", ocultismo="Valor do ocultismo a ser calculado.")
    async def calcular_dt_ritual(self, interaction: discord.Interaction, atributo: int, ocultismo: int):
        dt = 10 + atributo + ocultismo
        await interaction.response.send_message(f"Sua DT de ritual é {dt}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))