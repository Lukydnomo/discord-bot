import discord
from discord import app_commands
from discord.ext import commands

class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="converter_sanidade_para_pd", description="Converte valores de Sanidade para Pontos de Determinação.")
    @app_commands.describe(sanidade="Valor de Sanidade a ser convertido.")
    async def converter_sanidade_para_pd(sanidade: int) -> int:
        """
        Converte um valor de sanidade para pontos de dano (PD) usando a fórmula:
        Para cada 3 pontos de sanidade, o usuário recebe 2 pontos de dano.

        Args:
            sanidade (int): O valor de sanidade a ser convertido.

        Returns:
            int: O valor convertido em pontos de dano (PD).
        """
        pd = (sanidade // 3) * 2
        return pd

async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))