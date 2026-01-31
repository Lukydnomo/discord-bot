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

async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))