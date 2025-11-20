# cogs/fran_minecraft_server.py
import asyncio
import os
import requests
from discord.ext import commands
import discord

class Fran_Server(commands.Cog):
    """Comandos para controlar o servidor Minecraft via GitHub Actions"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.GITHUB_OWNER = "Lukydnomo"
        self.GITHUB_REPO = "fran-server"
        self.GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    
    def trigger_server_action(self, action: str) -> tuple[int, str]:
        """
        Dispara um workflow no repo fran-server via repository_dispatch
        action: 'start' ou 'stop'
        """
        if not self.GITHUB_TOKEN:
            return 400, "❌ GITHUB_TOKEN não configurado"
        
        try:
            url = f"https://api.github.com/repos/{self.GITHUB_OWNER}/{self.GITHUB_REPO}/dispatches"
            headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.GITHUB_TOKEN}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            payload = {
                "event_type": "fran-control",
                "client_payload": {"action": action}
            }
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            return r.status_code, r.text
        except Exception as e:
            return 500, str(e)
    
    @commands.command(name="fran_ligar", description="Liga o servidor Fran Minecraft + Playit")
    async def fran_ligar(self, ctx):
        """Liga o servidor Fran Minecraft + Playit na Codespace"""
        embed = discord.Embed(
            title="🟡 Iniciando servidor Fran...",
            description="Disparando workflow no GitHub Actions",
            color=discord.Color.gold()
        )
        msg = await ctx.send(embed=embed)
        
        # Dispara o workflow
        status, text = await asyncio.to_thread(self.trigger_server_action, "start")
        
        if status in (200, 202, 204):
            embed = discord.Embed(
                title="✅ Servidor iniciado!",
                description="Workflow foi disparado. O servidor está iniciando...\n\nVerifique em: https://github.com/Lukydnomo/fran-server/actions",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Erro ao iniciar servidor",
                description=f"Status: {status}\nResposta: {text[:200]}",
                color=discord.Color.red()
            )
        
        await msg.edit(embed=embed)
    
    @commands.command(name="fran_desligar", description="Desliga o servidor Fran Minecraft + Playit")
    async def fran_desligar(self, ctx):
        """Desliga o servidor Fran Minecraft + Playit"""
        embed = discord.Embed(
            title="🟡 Desligando servidor Fran...",
            description="Disparando workflow no GitHub Actions",
            color=discord.Color.gold()
        )
        msg = await ctx.send(embed=embed)
        
        # Dispara o workflow
        status, text = await asyncio.to_thread(self.trigger_server_action, "stop")
        
        if status in (200, 202, 204):
            embed = discord.Embed(
                title="✅ Servidor desligado!",
                description="Workflow foi disparado. O servidor está desligando...\n\nVerifique em: https://github.com/Lukydnomo/fran-server/actions",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Erro ao desligar servidor",
                description=f"Status: {status}\nResposta: {text[:200]}",
                color=discord.Color.red()
            )
        
        await msg.edit(embed=embed)
    
    @commands.command(name="fran_status", description="Mostra link para verificar status no GitHub")
    async def fran_status(self, ctx):
        """Mostra status dos workflows"""
        embed = discord.Embed(
            title="📊 Status do Servidor Fran",
            description="Clique no link abaixo para ver os workflows em tempo real:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🔗 GitHub Actions",
            value="https://github.com/Lukydnomo/fran-server/actions",
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fran_Server(bot))
