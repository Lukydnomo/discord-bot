# cogs/music.py
import os
import random
import asyncio
import json
import re
import unidecode
from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from core.modules import get_file_content, update_file_content

STATE_RE = re.compile(r"\|\|music_state:([A-Za-z0-9_\-]+=*)\|\|")

def encode_state(obj: dict) -> str:
    raw = json.dumps(obj, ensure_ascii=False, separators=(",",":")).encode("utf-8")
    return urlsafe_b64encode(raw).decode("ascii")

def decode_state(token: str) -> dict:
    raw = urlsafe_b64decode(token.encode("ascii"))
    return json.loads(raw.decode("utf-8"))

class MusicControlView(discord.ui.View):
    def __init__(self, disabled: bool = False):
        super().__init__(timeout=None)  # persistent view
        self.disabled = disabled

        def btn(label, cid, style=discord.ButtonStyle.secondary, emoji=None):
            b = discord.ui.Button(label=label, custom_id=cid, style=style, emoji=emoji, disabled=disabled)
            b.callback = self._wrap(cid)
            self.add_item(b)

        btn("Pause/Play", "music:toggle", discord.ButtonStyle.primary, "⏯️")
        btn("Pular", "music:skip", discord.ButtonStyle.secondary, "⏭️")
        btn("Parar", "music:stop", discord.ButtonStyle.danger, "⏹️")
        btn("Loop", "music:loop", discord.ButtonStyle.secondary, "🔁")
        btn("Shuffle", "music:shuffle", discord.ButtonStyle.secondary, "🔀")
        btn("Fila", "music:queue", discord.ButtonStyle.secondary, "📜")

    def _wrap(self, cid: str):
        async def _cb(interaction: discord.Interaction):
            cog = interaction.client.get_cog("Music")
            if cog is None:
                return await interaction.response.send_message("❌ Music cog não carregado.", ephemeral=True)
            await cog._panel_action(interaction, cid)
        return _cb


class Music(commands.Cog):
    """
    Comandos para tocar música no canal de voz.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_clients: dict[int, discord.VoiceClient] = {}
        self.queues: dict[int, list] = {}
        self.loop_status: dict[int, int] = {}  # 0=off,1=track loop,2=queue loop
        # usado para pausar quando canal ficou vazio e restaurar ao voltar gente
        self.paused_for_empty: set[int] = set()

    # configuration helpers --------------------------------------------------
    def _get_guild_cfg(self, guild_id: int) -> dict:
        data = get_file_content()
        if not isinstance(data, dict):
            return {}
        gc = data.get("guild_config", {})
        if not isinstance(gc, dict):
            return {}
        b = gc.get(str(guild_id), {})
        return b if isinstance(b, dict) else {}

    def _music_settings(self, guild_id: int) -> tuple[int, int]:
        """
        returns: (autodc_seconds, bitrate_kbps)
        """
        cfg = self._get_guild_cfg(guild_id)

        # autodc
        try:
            autodc = int(cfg.get("music_auto_disconnect_seconds", 60))
        except Exception:
            autodc = 60
        autodc = max(0, min(3600, autodc))

        # bitrate
        try:
            kbps = int(cfg.get("music_bitrate_kbps", 128))
        except Exception:
            kbps = 128
        kbps = max(48, min(320, kbps))

        return autodc, kbps

    async def cog_load(self):
        # register persistent view so buttons survive bot restarts
        self.bot.add_view(MusicControlView(disabled=False))

    # helpers for panel and configuration ----------------------------------
    def _cfg_bucket(self, guild_id: int) -> dict:
        data = get_file_content()
        if not isinstance(data, dict):
            return {}
        gc = data.get("guild_config", {})
        if not isinstance(gc, dict):
            return {}
        b = gc.get(str(guild_id), {})
        return b if isinstance(b, dict) else {}

    def _get_panel_ids(self, guild_id: int) -> tuple[Optional[int], Optional[int]]:
        b = self._cfg_bucket(guild_id)
        ch = b.get("music_panel_channel_id")
        mid = b.get("music_panel_message_id")
        return (int(ch) if ch else None, int(mid) if mid else None)

    async def _save_panel_message_id(self, guild_id: int, message: discord.Message) -> None:
        def _write() -> bool:
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}
            gc = data.get("guild_config")
            if not isinstance(gc, dict):
                gc = {}
                data["guild_config"] = gc
            bucket = gc.get(str(guild_id))
            if not isinstance(bucket, dict):
                bucket = {}
                gc[str(guild_id)] = bucket
            bucket["music_panel_channel_id"] = int(message.channel.id)
            bucket["music_panel_message_id"] = int(message.id)
            return update_file_content(data)

        await asyncio.to_thread(_write)

    def _listeners_count(self, vc: Optional[discord.VoiceClient]) -> int:
        try:
            if not vc or not vc.channel:
                return 0
            return sum(1 for m in vc.channel.members if not m.bot)
        except Exception:
            return 0

    def _track_title(self, t) -> str:
        if isinstance(t, dict):
            return str(t.get("title") or os.path.basename(str(t.get("path", "???"))))
        return os.path.basename(str(t))

    def _normalize_track(self, t, requester_id: Optional[int] = None) -> dict:
        if isinstance(t, dict):
            path = t.get("path", t)
            title = t.get("title") or os.path.basename(str(path))
            return {"path": str(path), "title": str(title), "requester_id": t.get("requester_id", requester_id)}
        s = str(t)
        return {"path": s, "title": os.path.basename(s), "requester_id": requester_id}

    def _build_panel_embed(self, guild_id: int, status: str) -> discord.Embed:
        queue = self.queues.get(guild_id, [])
        vc = self.voice_clients.get(guild_id)
        now = self._track_title(queue[0]) if queue else "—"
        nexts = [self._track_title(x) for x in queue[1:6]]
        loop = int(self.loop_status.get(guild_id, 0))
        loop_txt = {0: "Desligado", 1: "Música atual", 2: "Fila inteira"}.get(loop, "Desconhecido")

        e = discord.Embed(title="🎧 Painel de Música", description=f"**Status:** {status}", color=discord.Color.blurple())
        e.add_field(name="🎵 Agora", value=now, inline=False)
        e.add_field(name="⏭️ Próximas", value=("\n".join(f"• {x}" for x in nexts) if nexts else "—"), inline=False)
        e.add_field(name="🔁 Loop", value=loop_txt, inline=True)
        e.add_field(name="📦 Tamanho da fila", value=str(max(0, len(queue)-1)), inline=True)

        e.set_footer(text="Se não tiver ninguém ouvindo, o painel desativa sozinho.")
        return e

    def _make_state_token(self, guild_id: int, voice_channel_id: Optional[int]) -> str:
        queue = [self._normalize_track(t) for t in self.queues.get(guild_id, [])][:50]
        payload = {
            "v": 1,
            "voice": int(voice_channel_id) if voice_channel_id else None,
            "loop": int(self.loop_status.get(guild_id, 0)),
            "queue": queue,
        }
        return encode_state(payload)

    async def _get_panel_message(self, guild_id: int) -> Optional[discord.Message]:
        ch_id, msg_id = self._get_panel_ids(guild_id)
        if not ch_id or not msg_id:
            return None
        ch = self.bot.get_channel(ch_id) or await self.bot.fetch_channel(ch_id)
        if not isinstance(ch, discord.TextChannel):
            return None
        try:
            return await ch.fetch_message(msg_id)
        except Exception:
            return None

    async def _update_panel(self, guild_id: int, status: str, disabled: bool = False, voice_channel_id: Optional[int] = None):
        msg = await self._get_panel_message(guild_id)
        if msg is None:
            return
        token = self._make_state_token(guild_id, voice_channel_id)
        content = f"||music_state:{token}||"
        await msg.edit(content=content, embed=self._build_panel_embed(guild_id, status), view=MusicControlView(disabled=disabled))

    async def _ensure_panel(self, guild_id: int, channel: discord.TextChannel, move: bool = False):
        # ensure there is a message tracked as the panel; if it's in a different channel and move=True delete old
        msg = await self._get_panel_message(guild_id)
        if msg and msg.channel.id == channel.id and not move:
            return msg
        if msg and msg.channel.id != channel.id:
            try:
                await msg.delete()
            except Exception:
                pass
        status = "Tocando" if (self.voice_clients.get(guild_id) and self.voice_clients[guild_id].is_playing()) else ("Pausado" if (self.voice_clients.get(guild_id) and getattr(self.voice_clients[guild_id], "is_paused", lambda: False)()) else "Parado")
        token = self._make_state_token(guild_id, getattr(getattr(self.voice_clients.get(guild_id), "channel", None), "id", None))
        newmsg = await channel.send(content=f"||music_state:{token}||", embed=self._build_panel_embed(guild_id, status), view=MusicControlView(disabled=False))
        await self._save_panel_message_id(guild_id, newmsg)
        return newmsg

    # Tocador
    def check_auto_disconnect(self, guild_id):
        async def task():
            delay, _ = self._music_settings(guild_id)
            if delay <= 0:
                return
            await asyncio.sleep(delay)
            vc = self.voice_clients.get(guild_id)
            if vc and not vc.is_playing() and not self.queues.get(guild_id):
                await vc.disconnect()
                self.voice_clients.pop(guild_id, None)
                self.queues.pop(guild_id, None)

        # Certifica-se de que o loop de eventos correto está sendo utilizado
        asyncio.run_coroutine_threadsafe(task(), self.bot.loop)

    def play_next(self, guild_id):
        if guild_id not in self.queues or not self.queues[guild_id]:
            self.check_auto_disconnect(guild_id)
            return

        vc = self.voice_clients.get(guild_id)
        if not vc:
            return

        current_track = self.queues[guild_id][0]

        def after_playback(error):
            if error:
                print(f"Erro ao tocar áudio: {error}")
                # Se houver erro, tenta a próxima faixa
                if self.loop_status.get(guild_id, 0) != 1:  # Se não estiver em loop de música
                    self.queues[guild_id].pop(0)
                if self.queues[guild_id]:
                    self.play_next(guild_id)
                else:
                    self.check_auto_disconnect(guild_id)
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self._update_panel(
                                guild_id,
                                "Parado",
                                disabled=False,
                                voice_channel_id=getattr(getattr(vc, "channel", None), "id", None),
                            ),
                            self.bot.loop,
                        )
                    except Exception:
                        pass
                return

            # Gerencia o loop após reprodução bem-sucedida
            if self.loop_status.get(guild_id, 0) == 1:  # Loop música atual
                self.play_next(guild_id)
            elif self.loop_status.get(guild_id, 0) == 2:  # Loop fila inteira
                self.queues[guild_id].append(self.queues[guild_id].pop(0))
                self.play_next(guild_id)
            else:  # Sem loop
                self.queues[guild_id].pop(0)
                if self.queues[guild_id]:
                    self.play_next(guild_id)
                else:
                    self.check_auto_disconnect(guild_id)
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self._update_panel(
                                guild_id,
                                "Parado",
                                disabled=False,
                                voice_channel_id=getattr(getattr(vc, "channel", None), "id", None),
                            ),
                            self.bot.loop,
                        )
                    except Exception:
                        pass

        try:
            # Configura opções do FFmpeg
            _, kbps = self._music_settings(guild_id)
            common_opts = {
                "options": f"-vn -b:a {kbps}k"  # Apenas áudio, bitrate configurável
            }

            # Verifica o tipo de faixa e obtém o caminho correto
            audio_path = current_track.get("path", current_track) if isinstance(current_track, dict) else current_track
            is_remote = isinstance(audio_path, str) and audio_path.startswith("http")

            # Erro se local e não existe
            if not is_remote and not os.path.exists(audio_path):
                print(f"Arquivo não encontrado: {audio_path}")
                after_playback(Exception("Arquivo não encontrado"))
                return

            opts = common_opts.copy()

            vc.play(
                discord.FFmpegPCMAudio(
                    audio_path,
                    **opts
                ),
                after=after_playback
            )
            # refresh panel to reflect now playing
            try:
                asyncio.run_coroutine_threadsafe(
                    self._update_panel(
                        guild_id,
                        "Tocando",
                        disabled=False,
                        voice_channel_id=getattr(getattr(vc, "channel", None), "id", None),
                    ),
                    self.bot.loop,
                )
            except Exception:
                pass

        except Exception as e:
            print(f"Erro ao tocar a faixa: {e}")
            after_playback(e)

    def buscar_arquivo(self, nome: str) -> Optional[str]:
        # normaliza o nome passado
        nome_normalizado = unidecode.unidecode(nome).lower()

        # percorre cada pasta em assets/audios
        for root, _, files in os.walk("assets/audios"):
            for file in files:
                # compara início do nome do arquivo, sem acentos e em minúsculas
                if unidecode.unidecode(file).lower().startswith(nome_normalizado):
                    return os.path.join(root, file)

        # se não achar, retorna None
        return None

    @app_commands.command(name="entrar", description="Faz o bot entrar no canal de voz e permanecer lá")
    @app_commands.describe(canal="Canal de voz onde o bot entrará")
    async def entrar(self, interaction: discord.Interaction, canal: discord.VoiceChannel):
        if not interaction.user.guild_permissions.connect:
            return await interaction.response.send_message("🚫 Você não tem permissão para usar este comando!", ephemeral=True)

        if interaction.guild.id in self.voice_clients:
            return await interaction.response.send_message("⚠️ Já estou em um canal de voz!", ephemeral=True)

        vc = await canal.connect()
        self.voice_clients[interaction.guild.id] = vc
        await interaction.response.send_message(f"🔊 Entrei no canal {canal.mention}!")

    @app_commands.command(name="tocar", description="Toca um ou mais áudios no canal de voz")
    @app_commands.describe(
    arquivo="Nome(s) de áudio(s) ou pasta(s) (*nome), separados por vírgula"
)
    async def tocar(self, interaction: discord.Interaction, arquivo: str):
        # 1) defer para dar tempo suficiente
        await interaction.response.defer(thinking=True)

        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)

        # 2) conecta se não estiver em canal
        if not vc:
            canal = interaction.user.voice.channel if interaction.user.voice else None
            if not canal:
                return await interaction.followup.send(
                    "❌ Você precisa estar em um canal de voz!", ephemeral=True
                )
            vc = await canal.connect()
            self.voice_clients[guild_id] = vc

        # ensure a panel exists in this channel (and move existing if necessary)
        if isinstance(interaction.channel, discord.TextChannel):
            await self._ensure_panel(guild_id, interaction.channel, move=True)

        nomes = [n.strip() for n in arquivo.split(",")]
        encontrados: list[str] = []
        self.queues.setdefault(guild_id, [])

        for nome in nomes:
            # ───  B) Pasta local (*pasta)  ────────────────────────────────────
            if nome.startswith("*"):
                pasta = nome[1:]
                caminho_pasta = os.path.join("assets/audios", pasta)
                if os.path.isdir(caminho_pasta):
                    arquivos = sorted(
                        os.path.join(caminho_pasta, f)
                        for f in os.listdir(caminho_pasta)
                        if os.path.isfile(os.path.join(caminho_pasta, f))
                    )
                    if arquivos:
                        # convert to dict entries
                        self.queues[guild_id].extend({"path": p, "title": os.path.basename(p), "requester_id": interaction.user.id} for p in arquivos)
                        encontrados.append(f"[{len(arquivos)} faixas de {pasta}]")
                    else:
                        await interaction.followup.send(
                            f"⚠️ A pasta `{pasta}` está vazia!", ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        f"❌ Pasta `{pasta}` não encontrada!", ephemeral=True
                    )
                continue

            # ───  C) Arquivo local simples  ───────────────────────────────────
            audio_file = self.buscar_arquivo(nome)
            if audio_file:
                self.queues[guild_id].append({"path": audio_file, "title": nome, "requester_id": interaction.user.id})
                encontrados.append(nome)
            else:
                await interaction.followup.send(
                    f"⚠️ Arquivo `{nome}` não encontrado!", ephemeral=True
                )

        # ─── Sem nada válido? retorna ──────────────────────────────────────
        if not encontrados:
            return await interaction.followup.send(
                "❌ Nenhum áudio, pasta ou URL válida foi encontrado!", ephemeral=True
            )

        # ─── Inicia reprodução ou adiciona à fila ─────────────────────────
        if not vc.is_playing():
            self.play_next(guild_id)
            await interaction.followup.send(f"🎵 Tocando agora: **{encontrados[0]}**")
        else:
            await interaction.followup.send(
                f"🎶 Adicionado à fila: {', '.join(encontrados)}"
            )

        # depois de qualquer alteração, atualiza o painel
        voice_id = getattr(getattr(vc, "channel", None), "id", None)
        await self._update_panel(guild_id, "Tocando" if vc and vc.is_playing() else "Pausado", disabled=False, voice_channel_id=voice_id)

    @app_commands.command(name="painel_musica", description="Cria/atualiza o painel de música neste servidor.")
    async def painel_musica(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Precisa **Gerenciar Servidor**.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id

        # tenta pegar o canal configurado, senão usa o canal atual
        b = self._cfg_bucket(guild_id)
        ch_id = b.get("music_panel_channel_id")
        ch = None
        if ch_id:
            ch = self.bot.get_channel(int(ch_id)) or await self.bot.fetch_channel(int(ch_id))
        if not isinstance(ch, discord.TextChannel):
            if isinstance(interaction.channel, discord.TextChannel):
                ch = interaction.channel
        if ch is None:
            return await interaction.followup.send("❌ Não consegui identificar canal válido para o painel.", ephemeral=True)

        await self._ensure_panel(guild_id, ch, move=True)
        await interaction.followup.send(f"✅ Painel criado/atualizado em {ch.mention}!", ephemeral=True)

    async def _panel_action(self, interaction: discord.Interaction, action: str):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Isso só funciona em servidor.", ephemeral=True)

        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)

        # se não tá conectado: desativa
        if not vc or not getattr(vc, "channel", None):
            await self._update_panel(guild_id, "Parado", disabled=True, voice_channel_id=None)
            return await interaction.response.send_message("⚠️ Não estou em call aqui. Use `/tocar`.", ephemeral=True)

        listeners = self._listeners_count(vc)
        if listeners <= 0:
            # ninguém ouvindo -> painel “morre”
            await self._update_panel(guild_id, "Sem ouvintes", disabled=True, voice_channel_id=vc.channel.id)
            return await interaction.response.send_message("⚠️ Ninguém está ouvindo música agora, painel desativado.", ephemeral=True)

        # ações
        if action == "music:toggle":
            if getattr(vc, "is_paused", lambda: False)():
                vc.resume()
                status = "Tocando"
            elif vc.is_playing():
                vc.pause()
                status = "Pausado"
            else:
                # se tem fila, tenta tocar
                if self.queues.get(guild_id):
                    self.play_next(guild_id)
                status = "Tocando"
            await self._update_panel(guild_id, status, disabled=False, voice_channel_id=vc.channel.id)
            return await interaction.response.send_message("✅", ephemeral=True)

        if action == "music:skip":
            if vc.is_playing() or getattr(vc, "is_paused", lambda: False)():
                vc.stop()
            await self._update_panel(guild_id, "Pulando…", disabled=False, voice_channel_id=vc.channel.id)
            return await interaction.response.send_message("⏭️", ephemeral=True)

        if action == "music:stop":
            self.queues[guild_id] = []
            vc.stop()
            await self._update_panel(guild_id, "Parado", disabled=False, voice_channel_id=vc.channel.id)
            return await interaction.response.send_message("⏹️", ephemeral=True)

        if action == "music:loop":
            cur = int(self.loop_status.get(guild_id, 0))
            self.loop_status[guild_id] = (cur + 1) % 3
            await self._update_panel(guild_id, "Tocando" if vc.is_playing() else "Pausado", disabled=False, voice_channel_id=vc.channel.id)
            return await interaction.response.send_message("🔁", ephemeral=True)

        if action == "music:shuffle":
            fila = self.queues.get(guild_id, [])
            if len(fila) > 1:
                tocando = fila[0]
                rest = fila[1:]
                random.shuffle(rest)
                self.queues[guild_id] = [tocando] + rest
            await self._update_panel(guild_id, "Tocando" if vc.is_playing() else "Pausado", disabled=False, voice_channel_id=vc.channel.id)
            return await interaction.response.send_message("🔀", ephemeral=True)

        if action == "music:queue":
            queue = self.queues.get(guild_id, [])
            if not queue:
                return await interaction.response.send_message("🎶 fila vazia.", ephemeral=True)
            now = self._track_title(queue[0])
            upcoming = [self._track_title(x) for x in queue[1:16]]
            txt = f"🎵 Agora: **{now}**\n" + ("\n".join(f"{i+1}. {t}" for i, t in enumerate(upcoming)) if upcoming else "—")
            return await interaction.response.send_message(txt, ephemeral=True)

        return await interaction.response.send_message("❌ ação desconhecida.", ephemeral=True)

    @app_commands.command(name="listar", description="Lista todos os áudios")
    async def listar(self, interaction: discord.Interaction):
        # mostra lista de arquivos de áudio disponíveis
        diretorio = "assets/audios"
        if not os.path.exists(diretorio):
            return await interaction.response.send_message("❌ Diretório de áudios não encontrado!", ephemeral=True)

        def build_tree(path, prefix):
            itens = os.listdir(path)
            dirs = [item for item in itens if os.path.isdir(os.path.join(path, item))]
            files = [item for item in itens if os.path.isfile(os.path.join(path, item))]
            combinados = dirs + files

            linhas = []
            for idx, item in enumerate(combinados):
                is_last = (idx == len(combinados) - 1)
                branch = "└──" if is_last else "├──"
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    linhas.append(f"{prefix}{branch} 📁 {item}/")
                    novo_prefix = prefix + ("    " if is_last else "│   ")
                    linhas.extend(build_tree(item_path, novo_prefix))
                else:
                    linhas.append(f"{prefix}{branch} 📄 {item}")
            return linhas

        tree_lines = build_tree(diretorio, "│   ")
        lista_arquivos = f"📂 {os.path.basename(diretorio)}/\n" + "\n".join(tree_lines) if tree_lines else "📂 Diretório vazio."

        if len(lista_arquivos) > 2000:
            with open("lista_arquivos.txt", "w", encoding="utf-8") as f:
                f.write(lista_arquivos)
            await interaction.response.send_message("📜 Lista de arquivos:", file=discord.File("lista_arquivos.txt"))
            os.remove("lista_arquivos.txt")
        else:
            await interaction.response.send_message(f"**Arquivos e pastas disponíveis:**\n```\n{lista_arquivos}\n```")

    @app_commands.command(name="parar", description="Para a reprodução e limpa a fila")
    async def parar(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)

        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ Não há áudio tocando!", ephemeral=True)

        self.queues[guild_id] = []  # Limpa a fila
        vc.stop()
        await interaction.response.send_message("⏹️ Reprodução interrompida e fila limpa!")
        # atualizar painel
        await self._update_panel(guild_id, "Parado", disabled=False, voice_channel_id=getattr(getattr(vc, "channel", None), "id", None))

    @app_commands.command(name="sair", description="Faz o bot sair de todos os canais de voz e limpa todas as filas de reprodução")
    async def sair(self, interaction: discord.Interaction):
        # Desconecta de todas as instâncias registradas, sem checar se está em call no guild invocador
        desconectados = 0
        erros = []

        # Itera sobre uma cópia para poder remover entradas enquanto desconecta
        for guild_id, vc in list(self.voice_clients.items()):
            try:
                if vc:
                    await vc.disconnect()
                desconectados += 1
            except Exception as e:
                erros.append(f"{guild_id}: {e}")
            finally:
                # Remove qualquer estado referente a esse guild
                self.voice_clients.pop(guild_id, None)
                self.queues.pop(guild_id, None)
                self.loop_status.pop(guild_id, None)
                # também atualiza painel se houver
                await self._update_panel(guild_id, "Parado", disabled=True, voice_channel_id=None)

        # Tentativa adicional: remover diretamente uma instância problemática pelo ID conhecido

        resumo = f"👋 Desconectado de {desconectados} canal(is) de voz e limpei as filas correspondentes."
        if erros:
            resumo += f" Porém ocorreram erros ao desconectar de alguns guilds: {'; '.join(erros)}"

        await interaction.response.send_message(resumo)

    @app_commands.command(name="pular", description="Pula para o próximo áudio na fila")
    async def pular(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)

        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ Nenhum áudio está tocando!", ephemeral=True)

        vc.stop()
        await interaction.response.send_message("⏭️ Pulando para o próximo áudio...")

        self.play_next(guild_id)
        # painel será atualizado por play_next quando a próxima música começar

    @app_commands.command(name="fila", description="Mostra a fila de áudios")
    async def fila(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        queue = self.queues.get(guild_id, [])

        if not queue:
            return await interaction.response.send_message("🎶 A fila está vazia!", ephemeral=True)

        # Helper para extrair título de diferentes formatos de track
        def get_title(track):
            try:
                if isinstance(track, dict):
                    for key in ("title", "t itle", "name", "titulo", "fileName"):
                        if key in track and track[key]:
                            return str(track[key])
                    # tenta pegar de campos comuns
                    for key in ("path", "filePath", "url"):
                        if key in track and track[key]:
                            return os.path.basename(str(track[key]))
                    return str(track)
                else:
                    return os.path.basename(str(track))
            except Exception:
                return str(track)

        vc = self.voice_clients.get(guild_id)
        is_playing = bool(vc and getattr(vc, "is_playing", lambda: False)())

        current_label = "Tocando agora" if is_playing else "Próximo a tocar"
        current = get_title(queue[0])

        upcoming = [get_title(t) for t in queue[1:]]
        if not upcoming:
            text = f"🎵 **{current_label}:** {current}\n\n📜 A fila não tem outras faixas."
            return await interaction.response.send_message(text)

        # limita a exibição para evitar ultrapassar o limite do Discord
        MAX_DISPLAY = 15
        display_list = "\n".join([f"{idx+1}. {title}" for idx, title in enumerate(upcoming[:MAX_DISPLAY])])
        more_count = len(upcoming) - MAX_DISPLAY
        more_text = f"\n...e mais {more_count} faixa(s)..." if more_count > 0 else ""

        mensagem = (
            f"🎵 **{current_label}:** {current}\n\n"
            f"📜 **Próximas na fila:**\n```\n{display_list}{more_text}\n```"
        )

        await interaction.response.send_message(mensagem)

    @app_commands.command(name="loop")
    @app_commands.describe(modo="Escolha o modo de loop (opcional). Se deixar vazio, mostra o status atual.")
    @app_commands.choices(modo=[
        app_commands.Choice(name="Desativado", value=0),
        app_commands.Choice(name="Música atual", value=1),
        app_commands.Choice(name="Fila inteira", value=2),
    ])
    async def loop(self, interaction: discord.Interaction, modo: Optional[app_commands.Choice[int]] = None):
        guild_id = interaction.guild.id
        estado_atual = int(self.loop_status.get(guild_id, 0))

        if modo is None:
            mensagens_status = {
                0: "🔁 Loop desativado",
                1: "🔂 Loop da música atual",
                2: "🔁 Loop da fila inteira",
            }
            return await interaction.response.send_message(
                f"📌 Estado atual do loop: **{estado_atual}** — {mensagens_status.get(estado_atual, 'Desconhecido')}",
                ephemeral=True
            )

        novo_estado = int(modo.value)
        self.loop_status[guild_id] = novo_estado

        mensagens = {
            0: "🔁 Loop desativado!",
            1: "🔂 Loop da música atual ativado!",
            2: "🔁 Loop da fila inteira ativado!",
        }

        await interaction.response.send_message(mensagens.get(novo_estado, "Modo de loop definido."))
        # atualiza painel sem mudar disabled
        vc = self.voice_clients.get(guild_id)
        voice_id = getattr(getattr(vc, "channel", None), "id", None)
        await self._update_panel(guild_id, "Tocando" if vc and getattr(vc, "is_playing", lambda: False)() else "Parado", disabled=False, voice_channel_id=voice_id)

    @app_commands.command(name="shuffle", description="Embaralha a fila de áudios")
    async def shuffle(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        fila = self.queues.get(guild_id)

        if not fila or len(fila) <= 1:
            return await interaction.response.send_message("🎶 A fila está vazia ou tem apenas um item!", ephemeral=True)

        # Se a música atual tá tocando, deixa ela no topo e embaralha o resto
        tocando_agora = fila[0]
        restante = fila[1:]
        random.shuffle(restante)
        self.queues[guild_id] = [tocando_agora] + restante

        await interaction.response.send_message("🔀 Fila embaralhada com sucesso!")
        vc = self.voice_clients.get(guild_id)
        voice_id = getattr(getattr(vc, "channel", None), "id", None)
        await self._update_panel(guild_id, "Tocando" if vc and getattr(vc, "is_playing", lambda: False)() else "Parado", disabled=False, voice_channel_id=voice_id)

    @app_commands.command(name="salvar_fila", description="Salva a fila atual em um ID único")
    async def salvar_fila(self, interaction: discord.Interaction):
        import json
        from datetime import datetime

        guild_id = interaction.guild.id
        queue = self.queues.get(guild_id, [])

        if not queue:
            return await interaction.response.send_message("❌ A fila está vazia, nada para salvar!", ephemeral=True)

        # helper para extrair path/title de um track (dict ou str)
        def normalize_track(track):
            if isinstance(track, dict):
                # possíveis chaves
                path = None
                for k in ("path", "filePath", "url"):
                    if k in track and track[k]:
                        path = track[k]
                        break
                title = None
                for k in ("title", "t itle", "name", "titulo", "fileName"):
                    if k in track and track[k]:
                        title = str(track[k])
                        break
                if not path:
                    # fallback para serialização segura
                    path = title or str(track)
                if not title:
                    title = os.path.basename(str(path))
                ttype = "remote" if isinstance(path, str) and str(path).startswith("http") else "local"
                return {"type": ttype, "path": str(path), "title": title}
            else:
                s = str(track)
                ttype = "remote" if s.startswith("http") else "local"
                title = os.path.basename(s)
                return {"type": ttype, "path": s, "title": title}

        serialized_queue = [normalize_track(t) for t in queue]

        vc = self.voice_clients.get(guild_id)
        is_playing = bool(vc and getattr(vc, "is_playing", lambda: False)())

        payload = {
            "version": 1,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "loop": int(self.loop_status.get(guild_id, 0)),
            "is_playing": bool(is_playing),
            "queue": serialized_queue
        }

        try:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            token = urlsafe_b64encode(raw).decode("ascii")
            await interaction.response.send_message(f"✅ Fila salva com sucesso! Use este ID para carregar:\n`{token}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao serializar a fila: {e}", ephemeral=True)

    @app_commands.command(name="carregar_fila", description="Carrega uma fila salva usando um ID")
    @app_commands.describe(fila_id="ID da fila a ser carregada")
    async def carregar_fila(self, interaction: discord.Interaction, fila_id: str):
        import json

        guild_id = interaction.guild.id
        try:
            raw = urlsafe_b64decode(fila_id.encode())
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            return await interaction.response.send_message(f"❌ ID inválido ou corrompido: {e}", ephemeral=True)

        if not isinstance(data, dict) or "queue" not in data:
            return await interaction.response.send_message("❌ Estrutura de fila inválida.", ephemeral=True)

        loaded = []
        not_found = []
        self.queues.setdefault(guild_id, [])

        # Substitui a fila atual pela carregada (mantendo forma de dados usada pelo cog)
        new_queue = []
        for item in data["queue"]:
            try:
                path = item.get("path") if isinstance(item, dict) else str(item)
                title = item.get("title") if isinstance(item, dict) else os.path.basename(path)
                if item.get("type") == "local" or (isinstance(path, str) and not path.startswith("http")):
                    # verifica existência; se não existir, tenta buscar pelo título
                    if not os.path.exists(path):
                        found = self.buscar_arquivo(title)
                        if found:
                            path = found
                        else:
                            not_found.append(title)
                            continue
                    new_queue.append({"path": path, "title": title, "requester_id": None})
                    loaded.append(title)
                else:
                    # remote URL - mantêm como caminho para streaming ffmpeg
                    new_queue.append({"path": path, "title": title, "requester_id": None})
                    loaded.append(title)
            except Exception:
                not_found.append(str(item))

        if not new_queue:
            return await interaction.response.send_message("❌ Nenhuma faixa válida encontrada ao carregar a fila.", ephemeral=True)

        # aplica loop se informado
        try:
            self.loop_status[guild_id] = int(data.get("loop", 0))
        except Exception:
            self.loop_status[guild_id] = 0

        # substitui a fila
        self.queues[guild_id] = new_queue

        # tenta conectar / iniciar reprodução se necessário
        vc = self.voice_clients.get(guild_id)
        if not vc or not getattr(vc, "is_playing", lambda: False)():
            # conecta ao canal do usuário, se possível
            canal = interaction.user.voice.channel if interaction.user and interaction.user.voice else None
            if not canal and (not vc or not getattr(vc, "is_connected", lambda: False)()):
                return await interaction.response.send_message("❌ Você precisa estar em um canal de voz para eu tocar a fila.", ephemeral=True)
            try:
                if not vc or not getattr(vc, "is_connected", lambda: False)():
                    vc = await canal.connect()
                    self.voice_clients[guild_id] = vc
            except Exception as e:
                return await interaction.response.send_message(f"❌ Erro ao conectar no canal de voz: {e}", ephemeral=True)

            # inicia reprodução
            try:
                self.play_next(guild_id)
            except Exception as e:
                return await interaction.response.send_message(f"❌ Erro ao iniciar reprodução: {e}", ephemeral=True)

            msg = f"🎵 Fila carregada e iniciada: **{loaded[0]}**"
        else:
            msg = f"🎶 Fila carregada! Adicionado(s) à fila: {', '.join(loaded)}"

        if not_found:
            msg += f"\n⚠️ Não encontrados/ignorados: {', '.join(not_found)}"

        await interaction.response.send_message(msg)
        # painel fica no canal do comando
        if isinstance(interaction.channel, discord.TextChannel):
            await self._ensure_panel(guild_id, interaction.channel, move=True)
            vc = self.voice_clients.get(guild_id)
            voice_id = getattr(getattr(vc, "channel", None), "id", None)
            await self._update_panel(guild_id, "Tocando" if vc and getattr(vc, "is_playing", lambda: False)() else "Parado", disabled=False, voice_channel_id=voice_id)

    @app_commands.command(name="pausar", description="Pausa ou resume a reprodução (toggle)")
    async def pausar(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)

        if not vc:
            return await interaction.response.send_message("❌ Não estou conectado em nenhum canal de voz neste servidor.", ephemeral=True)

        try:
            # Se estiver pausado, resume; se estiver tocando, pausa; caso contrário, informa que não há nada tocando
            is_paused = getattr(vc, "is_paused", lambda: False)()
            is_playing = bool(getattr(vc, "is_playing", lambda: False)())

            if is_paused:
                vc.resume()
                await interaction.response.send_message("▶️ Reprodução retomada.", ephemeral=True)
                # atualiza painel
                vc2 = self.voice_clients.get(guild_id)
                voice_id = getattr(getattr(vc2, "channel", None), "id", None)
                await self._update_panel(guild_id, "Tocando", disabled=False, voice_channel_id=voice_id)
            elif is_playing:
                vc.pause()
                await interaction.response.send_message("⏸️ Reprodução pausada.", ephemeral=True)
                vc2 = self.voice_clients.get(guild_id)
                voice_id = getattr(getattr(vc2, "channel", None), "id", None)
                await self._update_panel(guild_id, "Pausado", disabled=False, voice_channel_id=voice_id)
            else:
                await interaction.response.send_message("❌ Não há áudio tocando no momento.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao alterar o estado de reprodução: {e}", ephemeral=True)


    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        if member.guild is None:
            return
        guild_id = member.guild.id
        vc = self.voice_clients.get(guild_id)
        if not vc or not getattr(vc, "channel", None):
            return

        if before.channel != vc.channel and after.channel != vc.channel:
            return

        listeners = self._listeners_count(vc)

        if listeners <= 0:
            try:
                if vc.is_playing():
                    vc.pause()
                    self.paused_for_empty.add(guild_id)
            except Exception:
                pass
            await self._update_panel(guild_id, "Sem ouvintes", disabled=True, voice_channel_id=vc.channel.id)
        else:
            if guild_id in self.paused_for_empty:
                try:
                    vc.resume()
                except Exception:
                    pass
                self.paused_for_empty.discard(guild_id)
            await self._update_panel(guild_id, "Tocando" if vc.is_playing() else "Pausado", disabled=False, voice_channel_id=vc.channel.id)

    @commands.Cog.listener()
    async def on_ready(self):
        asyncio.create_task(self._restore_from_panel())

    async def _restore_from_panel(self):
        await asyncio.sleep(2)
        for g in self.bot.guilds:
            guild_id = g.id
            msg = await self._get_panel_message(guild_id)
            if msg is None:
                continue

            m = STATE_RE.search(msg.content or "")
            if not m:
                continue

            try:
                state = decode_state(m.group(1))
            except Exception:
                continue

            try:
                self.loop_status[guild_id] = int(state.get("loop", 0))
            except Exception:
                self.loop_status[guild_id] = 0

            q = state.get("queue") or []
            if isinstance(q, list):
                rebuilt = []
                for it in q:
                    t = self._normalize_track(it)
                    path = t["path"]
                    if isinstance(path, str) and not path.startswith("http") and not os.path.exists(path):
                        continue
                    rebuilt.append(t)
                self.queues[guild_id] = rebuilt

            voice_id = state.get("voice")
            if not voice_id:
                await self._update_panel(guild_id, "Parado", disabled=True, voice_channel_id=None)
                continue

            ch = g.get_channel(int(voice_id))
            if not isinstance(ch, discord.VoiceChannel):
                await self._update_panel(guild_id, "Canal de voz não existe", disabled=True, voice_channel_id=None)
                continue

            if not any((not m.bot) for m in ch.members):
                await self._update_panel(guild_id, "Sem ouvintes", disabled=True, voice_channel_id=int(voice_id))
                continue

            try:
                vc = await ch.connect()
                self.voice_clients[guild_id] = vc
                if self.queues.get(guild_id):
                    self.play_next(guild_id)
                    await self._update_panel(guild_id, "Tocando", disabled=False, voice_channel_id=int(voice_id))
            except Exception:
                await self._update_panel(guild_id, "Falha ao reconectar", disabled=True, voice_channel_id=int(voice_id))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))