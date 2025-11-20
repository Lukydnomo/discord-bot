# cogs/server.py
import subprocess
import asyncio
from discord.ext import commands
import discord

class Server(commands.Cog):
    """Comandos para controlar o servidor Minecraft na Codespace"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Substitua com o nome da sua Codespace
        self.CODESPACE = "didactic-goggles-v6qjj4gvq954f667w"
    
    def run_ssh_command(self, cmd: str) -> tuple[str, str]:
        """Executa comando via SSH na Codespace"""
        try:
            full_cmd = [
                "gh", "codespace", "ssh",
                "-c", self.CODESPACE,
                "--",
                cmd
            ]
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
            return result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return "", "❌ Timeout ao conectar à Codespace"
        except Exception as e:
            return "", f"❌ Erro ao executar comando: {e}"
    
    @commands.command(name="fran_ligar", description="Liga o servidor Fran Minecraft + Playit")
    async def fran_ligar(self, ctx):
        """Liga o servidor Fran Minecraft + Playit na Codespace"""
        embed = discord.Embed(
            title="🟡 Iniciando servidor Fran...",
            description="Aguarde enquanto o servidor está sendo iniciado",
            color=discord.Color.gold()
        )
        msg = await ctx.send(embed=embed)
        
        # Executa script de inicialização
        stdout, stderr = await asyncio.to_thread(
            self.run_ssh_command,
            "bash /workspaces/fran-server/start.sh"
        )
        
        # Pega logs
        logs_stdout, _ = await asyncio.to_thread(
            self.run_ssh_command,
            "tail -20 /tmp/fran-server.log"
        )
        
        if stderr and "já está rodando" not in stderr:
            embed = discord.Embed(
                title="❌ Erro ao iniciar servidor",
                description=f"```\n{stderr[:1024]}\n```",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="✅ Servidor iniciado!",
                description="Minecraft + Playit estão rodando",
                color=discord.Color.green()
            )
            if logs_stdout:
                embed.add_field(
                    name="📋 Logs recentes",
                    value=f"```\n{logs_stdout[-512:]}\n```",
                    inline=False
                )
        
        await msg.edit(embed=embed)
    
    @commands.command(name="fran_desligar", description="Desliga o servidor Fran Minecraft + Playit")
    async def fran_desligar(self, ctx):
        """Desliga o servidor Fran Minecraft + Playit"""
        embed = discord.Embed(
            title="🟡 Desligando servidor Fran...",
            description="Aguarde",
            color=discord.Color.gold()
        )
        msg = await ctx.send(embed=embed)
        
        stdout, stderr = await asyncio.to_thread(
            self.run_ssh_command,
            "bash /workspaces/fran-server/stop.sh"
        )
        
        embed = discord.Embed(
            title="✅ Servidor desligado",
            description="Minecraft + Playit foram parados",
            color=discord.Color.green()
        )
        await msg.edit(embed=embed)
    
    @commands.command(name="fran_status", description="Verifica status do servidor Fran")
    async def fran_status(self, ctx):
        """Verifica se o servidor Fran está rodando"""
        logs_stdout, _ = await asyncio.to_thread(
            self.run_ssh_command,
            "tail -10 /tmp/fran-server.log"
        )
        
        crafty_status, _ = await asyncio.to_thread(
            self.run_ssh_command,
            "ps aux | grep run_crafty || echo 'Crafty offline'"
        )
        
        playit_status, _ = await asyncio.to_thread(
            self.run_ssh_command,
            "ps aux | grep playit || echo 'Playit offline'"
        )
        
        embed = discord.Embed(
            title="📊 Status do Servidor Fran",
            color=discord.Color.blue()
        )
        
        if "run_crafty" in crafty_status:
            embed.add_field(name="🎮 Crafty", value="✅ Online", inline=True)
        else:
            embed.add_field(name="🎮 Crafty", value="❌ Offline", inline=True)
        
        if "playit" in playit_status and "grep" not in playit_status:
            embed.add_field(name="🌐 Playit", value="✅ Online", inline=True)
        else:
            embed.add_field(name="🌐 Playit", value="❌ Offline", inline=True)
        
        if logs_stdout:
            embed.add_field(
                name="📋 Últimas linhas do log",
                value=f"```\n{logs_stdout[-300:]}\n```",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fran_logs", description="Mostra os logs do servidor Fran")
    async def fran_logs(self, ctx):
        """Mostra os últimos logs do servidor Fran"""
        logs_stdout, _ = await asyncio.to_thread(
            self.run_ssh_command,
            "tail -30 /tmp/fran-server.log"
        )
        
        embed = discord.Embed(
            title="📋 Logs do Servidor Fran",
            description=f"```\n{logs_stdout or 'Sem logs disponíveis'}\n```",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Server(bot))
