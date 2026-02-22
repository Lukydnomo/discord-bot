# cogs/serverconfig.py
import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.modules import get_file_content, update_file_content
from core.config import usuarios_autorizados


def _ensure_guild_config(data: dict) -> dict:
    root = data.get("guild_config")
    if not isinstance(root, dict):
        root = {}
        data["guild_config"] = root
    return root


def _ensure_bot_config(data: dict) -> dict:
    root = data.get("bot_config")
    if not isinstance(root, dict):
        root = {}
        data["bot_config"] = root
    return root


class ServerConfig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    botconfig = app_commands.Group(
        name="botconfig",
        description="Config global do bot (somente autorizados).",
    )

    def _is_authorized(self, user_id: int) -> bool:
        try:
            return int(user_id) in set(int(x) for x in usuarios_autorizados)
        except Exception:
            return False

    config = app_commands.Group(
        name="config",
        description="Configurações do servidor (features do bot).",
    )

    @config.command(name="updates", description="Define o canal (e cargo opcional) para postar updates/changelog.")
    @app_commands.describe(
        canal="Canal de texto onde o bot vai postar o changelog/updates",
        cargo="Cargo que será pingado (opcional). Se vazio, não pinga ninguém",
    )
    async def config_updates(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        cargo: Optional[discord.Role] = None,
    ):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Pra configurar isso, precisa permissão **Administrador**.",
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True, ephemeral=True)

        guild_id = interaction.guild.id
        channel_id = canal.id
        role_id = cargo.id if cargo else None

        def _write() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}

            gc = _ensure_guild_config(data)
            bucket = gc.get(str(guild_id))
            if not isinstance(bucket, dict):
                bucket = {}
                gc[str(guild_id)] = bucket

            bucket["updates_channel_id"] = int(channel_id)
            if role_id is None:
                bucket.pop("updates_role_id", None)
            else:
                bucket["updates_role_id"] = int(role_id)

            return update_file_content(data)

        ok = await asyncio.to_thread(_write)

        if not ok:
            return await interaction.followup.send("❌ Falha ao salvar no DB.", ephemeral=True)

        msg = f"✅ Updates configurado!\n📣 Canal: {canal.mention}"
        if cargo:
            msg += f"\n🔔 Ping: {cargo.mention}"
        else:
            msg += "\n🔕 Ping: (desligado)"
        await interaction.followup.send(msg, ephemeral=True)

    @config.command(name="music_autodc", description="Define o auto-disconnect da música (0 desliga).")
    @app_commands.describe(segundos="Ex: 60. Use 0 para desativar.")
    async def config_music_autodc(self, interaction: discord.Interaction, segundos: int):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Precisa **Administrador**.", ephemeral=True)

        segundos = max(0, min(3600, int(segundos)))

        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id

        def _write() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}
            gc = _ensure_guild_config(data)
            bucket = gc.get(str(guild_id))
            if not isinstance(bucket, dict):
                bucket = {}
                gc[str(guild_id)] = bucket
            bucket["music_auto_disconnect_seconds"] = segundos
            return update_file_content(data)

        ok = await asyncio.to_thread(_write)
        await interaction.followup.send(
            f"✅ Auto-disconnect: **{'desligado' if segundos == 0 else f'{segundos}s'}**",
            ephemeral=True
        )

    @config.command(name="music_bitrate", description="Define o bitrate do FFmpeg em kbps (48–320).")
    @app_commands.describe(kbps="Ex: 128")
    async def config_music_bitrate(self, interaction: discord.Interaction, kbps: int):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Precisa **Administrador**.", ephemeral=True)

        kbps = max(48, min(320, int(kbps)))

        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id

        def _write() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}
            gc = _ensure_guild_config(data)
            bucket = gc.get(str(guild_id))
            if not isinstance(bucket, dict):
                bucket = {}
                gc[str(guild_id)] = bucket
            bucket["music_bitrate_kbps"] = kbps
            return update_file_content(data)

        ok = await asyncio.to_thread(_write)
        await interaction.followup.send(f"✅ Bitrate: **{kbps}kbps**" if ok else "❌ Falha ao salvar.", ephemeral=True)

    @config.command(name="updates_clear", description="Remove a configuração de updates deste servidor.")
    async def config_updates_clear(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Pra configurar isso, precisa permissão **Administrador**.",
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True, ephemeral=True)

        guild_id = interaction.guild.id

        def _clear() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                return False

            gc = _ensure_guild_config(data)
            bucket = gc.get(str(guild_id))
            if not isinstance(bucket, dict):
                return True  # já “limpo”

            bucket.pop("updates_channel_id", None)
            bucket.pop("updates_role_id", None)

            # se ficou vazio, remove o bucket
            if not bucket:
                gc.pop(str(guild_id), None)

            return update_file_content(data)

        ok = await asyncio.to_thread(_clear)
        await interaction.followup.send("✅ Config de updates removida." if ok else "❌ Falha ao remover.", ephemeral=True)

    @config.command(name="show", description="Mostra as configs do servidor.")
    async def config_show(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)

        guild_id = interaction.guild.id

        def _read():
            data = get_file_content()
            if not isinstance(data, dict):
                return {}
            gc = (data.get("guild_config") or {})
            if not isinstance(gc, dict):
                return {}
            b = gc.get(str(guild_id)) or {}
            return b if isinstance(b, dict) else {}

        b = await asyncio.to_thread(_read)

        ch_id = b.get("updates_channel_id")
        role_id = b.get("updates_role_id")
        board_id = b.get("hexatombe_board_channel_id")
        dest_id = b.get("hexatombe_dest_channel_id")
        ping_id = b.get("hexatombe_ping_user_id")
        autodc = b.get("music_auto_disconnect_seconds")
        bitrate = b.get("music_bitrate_kbps")

        ch_txt = f"<#{ch_id}>" if ch_id else "(não definido)"
        role_txt = f"<@&{role_id}>" if role_id else "(não definido)"
        board_txt = f"<#{board_id}>" if board_id else "(não definido)"
        dest_txt = f"<#{dest_id}>" if dest_id else "(não definido)"
        ping_txt = f"<@{ping_id}>" if ping_id else "(não definido)"
        autodc_txt = "(padrão 60s)" if autodc is None else ("desligado" if int(autodc) == 0 else f"{int(autodc)}s")
        bitrate_txt = "(padrão 128kbps)" if bitrate is None else f"{int(bitrate)}kbps"

        await interaction.followup.send(
            "⚙️ **Config do servidor**\n"
            f"• Updates channel: {ch_txt}\n"
            f"• Updates ping: {role_txt}\n"
            f"• Hexatombe painel: {board_txt}\n"
            f"• Hexatombe destino: {dest_txt}\n"
            f"• Hexatombe ping: {ping_txt}\n"
            f"• Music autodc: {autodc_txt}\n"
            f"• Music bitrate: {bitrate_txt}",
            ephemeral=True,
        )

    @config.command(name="hexatombe", description="Configura os canais do Hexatombe (painel/destino e ping opcional).")
    @app_commands.describe(
        painel="Canal onde o bot vai postar os botões (painel)",
        destino="Canal onde o bot vai mandar 'Música X'",
        pingar="Pessoa pra pingar quando clicar (opcional)"
    )
    async def config_hexatombe(
        self,
        interaction: discord.Interaction,
        painel: discord.TextChannel,
        destino: discord.TextChannel,
        pingar: Optional[discord.Member] = None,
    ):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Pra configurar isso, precisa permissão **Administrador**.",
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id

        def _write() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}

            gc = _ensure_guild_config(data)
            bucket = gc.get(str(guild_id))
            if not isinstance(bucket, dict):
                bucket = {}
                gc[str(guild_id)] = bucket

            bucket["hexatombe_board_channel_id"] = int(painel.id)
            bucket["hexatombe_dest_channel_id"] = int(destino.id)

            if pingar is None:
                bucket.pop("hexatombe_ping_user_id", None)
            else:
                bucket["hexatombe_ping_user_id"] = int(pingar.id)

            return update_file_content(data)

        ok = await asyncio.to_thread(_write)
        if not ok:
            return await interaction.followup.send("❌ Falha ao salvar no DB.", ephemeral=True)

        msg = (
            "✅ Hexatombe configurado!\n"
            f"🧩 Painel: {painel.mention}\n"
            f"📨 Destino: {destino.mention}\n"
            f"🔔 Ping: {pingar.mention if pingar else '(desligado)'}"
        )
        await interaction.followup.send(msg, ephemeral=True)

    @config.command(name="hexatombe_clear", description="Remove a configuração do Hexatombe deste servidor.")
    async def config_hexatombe_clear(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Pra configurar isso, precisa permissão **Administrador**.",
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id

        def _clear() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                return False

            gc = _ensure_guild_config(data)
            bucket = gc.get(str(guild_id))
            if not isinstance(bucket, dict):
                return True

            bucket.pop("hexatombe_board_channel_id", None)
            bucket.pop("hexatombe_dest_channel_id", None)
            bucket.pop("hexatombe_ping_user_id", None)

            if not bucket:
                gc.pop(str(guild_id), None)

            return update_file_content(data)

        ok = await asyncio.to_thread(_clear)
        await interaction.followup.send("✅ Config do Hexatombe removida." if ok else "❌ Falha ao remover.", ephemeral=True)

    # -- botconfig commands ------------------------------------------------
    @botconfig.command(name="log_channel", description="Define o canal global de logs do bot.")
    @app_commands.describe(canal="Canal onde o bot manda logs globais")
    async def botconfig_log_channel(self, interaction: discord.Interaction, canal: discord.TextChannel):
        if not self._is_authorized(interaction.user.id):
            return await interaction.response.send_message("❌ Só autorizados podem mexer no botconfig.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)

        def _write():
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}
            bc = _ensure_bot_config(data)
            bc["log_channel_id"] = int(canal.id)
            return update_file_content(data)

        ok = await asyncio.to_thread(_write)
        await interaction.followup.send("✅ Log channel global salvo." if ok else "❌ Falha ao salvar.", ephemeral=True)

    @botconfig.command(name="dice_limits", description="Define limites globais do roller (dados e faces).")
    @app_commands.describe(max_dados="Máx de dados no grupo", max_faces="Máx de faces (dN)")
    async def botconfig_dice_limits(self, interaction: discord.Interaction, max_dados: int, max_faces: int):
        if not self._is_authorized(interaction.user.id):
            return await interaction.response.send_message("❌ Só autorizados podem mexer no botconfig.", ephemeral=True)

        if max_dados < 1 or max_dados > 10000 or max_faces < 2 or max_faces > 1_000_000:
            return await interaction.response.send_message("❌ Valores fora do intervalo permitido.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)

        def _write():
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}
            bc = _ensure_bot_config(data)
            bc["max_dice_group"] = int(max_dados)
            bc["max_faces"] = int(max_faces)
            return update_file_content(data)

        ok = await asyncio.to_thread(_write)
        await interaction.followup.send("✅ Limites de dados salvos." if ok else "❌ Falha ao salvar.", ephemeral=True)

    @botconfig.command(name="show", description="Mostra o botconfig atual (global).")
    async def botconfig_show(self, interaction: discord.Interaction):
        if not self._is_authorized(interaction.user.id):
            return await interaction.response.send_message("❌ Só autorizados podem ver o botconfig.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)

        def _read():
            data = get_file_content()
            if not isinstance(data, dict):
                return {}
            bc = data.get("bot_config", {})
            return bc if isinstance(bc, dict) else {}

        bc = await asyncio.to_thread(_read)
        await interaction.followup.send(
            "⚙️ **BotConfig (global)**\n"
            f"• log_channel_id: `{bc.get('log_channel_id', None)}`\n"
            f"• max_dice_group: `{bc.get('max_dice_group', None)}`\n"
            f"• max_faces: `{bc.get('max_faces', None)}`",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerConfig(bot))