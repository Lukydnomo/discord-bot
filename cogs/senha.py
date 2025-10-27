import discord
from discord import app_commands
from discord.ext import commands

class Secreto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # 🔑 Dicionário de senhas → canais
        # Formato: "senha": canal_id
        self.senhas = {
            "AL2706": 1424931563421962270,  # exemplo
            "meusecreto": 987654321098765432,
            "vip": 112233445566778899
        }

    @app_commands.command(name="secreto", description="Digite a senha para acessar um canal secreto.")
    @app_commands.describe(senha="A senha secreta para entrar no canal.")
    async def secreto(self, interaction: discord.Interaction, senha: str):
        usuario = interaction.user

        # Verifica se o usuário está em call
        if not usuario.voice or not usuario.voice.channel:
            await interaction.response.send_message("❌ Você precisa estar em um canal de voz primeiro.", ephemeral=True)
            return

        # Verifica se a senha existe
        if senha in self.senhas:
            canal_id = self.senhas[senha]
            canal_destino = interaction.guild.get_channel(canal_id)

            if not canal_destino or not isinstance(canal_destino, discord.VoiceChannel):
                await interaction.response.send_message("⚠️ Canal de destino inválido ou não encontrado.", ephemeral=True)
                return

            try:
                await usuario.move_to(canal_destino)
                await interaction.response.send_message(
                    f"✅ Senha correta! Você foi movido para **{canal_destino.name}**.",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message("🚫 Não tenho permissão para mover você.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Erro ao mover: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Senha incorreta.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Secreto(bot))