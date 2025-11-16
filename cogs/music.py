# cogs/music.py
import os
import random
import asyncio
import unidecode
from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Optional
from yt_dlp import YoutubeDL
import re, requests

import discord
from discord import app_commands
from discord.ext import commands

class Music(commands.Cog):
    """
    Comandos para tocar música no canal de voz.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_clients: dict[int, discord.VoiceClient] = {}
        self.queues: dict[int, list] = {}
        self.loop_status: dict[int, int] = {}  # 0=off,1=track loop,2=queue loop

    YDL_OPTS = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
        # força usar um front-end Invidious que não exige cookies
        "extractor_args": {
            "youtube": {
                "base_url": "https://yewtu.be",
                "api_url":  "https://yewtu.be"
            }
        },
        "geo_bypass": True,
        "nocheckcertificate": True,
    }

    def fetch_invidious_audio(self, vid: str, instances=None) -> tuple[str,str]:
        """
        Tenta instâncias Invidious para pegar o melhor formato de áudio.
        Retorna (audio_url, title) ou lança Exception.
        """
        if instances is None:
            instances = [
                "https://yewtu.eu.org",
                "https://yewtu.be",
                "https://yewtu.snopyta.org",
            ]

        for base in instances:
            api = f"{base}/api/v1/videos/{vid}"
            resp = requests.get(api, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            title = data.get("videoDetails", {}).get("title", vid)
            # filtra só áudio
            adaptive = data.get("adaptiveFormats", [])
            audios = [
                f for f in adaptive
                if f.get("mimeType", "").startswith("audio/")
                and "url" in f
            ]
            if not audios:
                continue
            # escolhe a maior bitrate
            best = max(audios, key=lambda a: a.get("bitrate", 0))
            return best["url"], title

        raise RuntimeError("Não foi possível obter áudio via Invidious")

    # --- NOVO: extrai URL direto via yt_dlp (assíncrono via to_thread) ---
    def extract_youtube_stream(self, url: str) -> tuple[str, str]:
        """
        Extrai a melhor URL de áudio utilizável pelo ffmpeg a partir de um link do YouTube
        usando yt_dlp (não faz download). Retorna (direct_media_url, title).
        Usa cookies.txt se existir (gerado pelo GitHub Actions via secret).
        Se cookies.txt não existir, usa a configuração padrão (Invidious) como fallback.
        """
        # copia as opções padrão
        ydl_opts = dict(self.YDL_OPTS)

        # garante que não faça download e retorne formatos
        ydl_opts.update({"quiet": True, "skip_download": True, "forcejson": True})

        # Se houver cookies.txt, usa-o e remove extractor_args (para usar o extractor oficial do YouTube)
        if os.path.exists("cookies.txt"):
            print("[Music] cookies.txt encontrado — usando cookies para yt_dlp (YouTube login).")
            ydl_opts["cookies"] = "cookies.txt"
            # remover extractor_args para permitir o extractor oficial do youtube usar os cookies
            ydl_opts.pop("extractor_args", None)
        else:
            print("[Music] cookies.txt não encontrado — usando Invidious como fallback (sem login).")

        # Extrai info com yt_dlp
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get("title") or info.get("videoDetails", {}).get("title") or str(url)

        formats = info.get("formats") or [info]

        # filtra formatos que contenham áudio e tenham URL
        audios = []
        for f in formats:
            if not f.get("url"):
                continue
            # seleciona preferencialmente audio-only ou com vcodec == 'none'
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            format_note = (f.get("format_note") or "").lower()
            if acodec and acodec != "none":
                audios.append(f)
            elif vcodec == "none" or "audio" in format_note:
                audios.append(f)

        if not audios:
            # fallback para qualquer formato com url
            audios = [f for f in formats if f.get("url")]
            if not audios:
                raise RuntimeError("Nenhum formato de áudio encontrado via yt_dlp")

        # escolhe o melhor por taxa de bits (abr, tbr ou bitrate)
        def quality_score(f):
            return f.get("abr") or f.get("tbr") or f.get("bitrate") or 0

        best = max(audios, key=quality_score)
        media_url = best["url"]
        return media_url, title

    # Tocador
    def check_auto_disconnect(self, guild_id):
        async def task():
            await asyncio.sleep(60)  # Aguarda 1 minuto
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
            # Configura opções do FFmpeg
            common_opts = {
                'options': '-vn -b:a 128k'  # Apenas áudio, bitrate 128k
            }
            reconnect_opts = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'  # Opções de reconexão
            }

            # Verifica o tipo de faixa e obtém o caminho correto
            audio_path = current_track.get('path', current_track) if isinstance(current_track, dict) else current_track
            is_remote = isinstance(audio_path, str) and audio_path.startswith("http")

            # Erro se local e não existe
            if not is_remote and not os.path.exists(audio_path):
                print(f"Arquivo não encontrado: {audio_path}")
                after_playback(Exception("Arquivo não encontrado"))
                return

            # Para URLs, aplica reconnect; para locais, só o básico
            opts = common_opts.copy()
            if is_remote:
                opts.update(reconnect_opts)

            vc.play(
                discord.FFmpegPCMAudio(
                    audio_path,
                    **opts
                ),
                after=after_playback
            )

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
        arquivo="Nome(s) de arquivo(s), pasta(s) (*nome) ou URL(s) do YouTube, separados por vírgula"
    )
    async def tocar(self, interaction: discord.Interaction, arquivo: str):
        # 1) defer para dar tempo suficiente à extração/stream
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

        nomes = [n.strip() for n in arquivo.split(",")]
        encontrados: list[str] = []
        self.queues.setdefault(guild_id, [])

        for nome in nomes:
            # ───  A) URL do YouTube  ──────────────────────────────────────────

            if nome.startswith(("http://", "https://")):
                try:
                    # aceita qualquer URL do youtube / youtu.be
                    # extrai stream direto via yt_dlp em thread para não bloquear o event-loop
                    audio_url, title = await asyncio.to_thread(self.extract_youtube_stream, nome)

                    # enfileira stream remoto com chave consistente ("path" e "title")
                    self.queues[guild_id].append({"path": audio_url, "title": title})
                    encontrados.append(title)
                    print(f"[Music] extraído yt_dlp: {title}")

                except Exception as e:
                    print(f"[Music] ERRO ao obter áudio via yt_dlp: {e}")
                    await interaction.followup.send(f"❌ Erro ao processar link `{nome}`: {e}", ephemeral=True)
                    continue


            # ───  B) Pasta local (*pasta)  ────────────────────────────────────
            elif nome.startswith("*"):
                pasta = nome[1:]
                caminho_pasta = os.path.join("assets/audios", pasta)
                if os.path.isdir(caminho_pasta):
                    arquivos = sorted(
                        os.path.join(caminho_pasta, f)
                        for f in os.listdir(caminho_pasta)
                        if os.path.isfile(os.path.join(caminho_pasta, f))
                    )
                    if arquivos:
                        self.queues[guild_id].extend(arquivos)
                        encontrados.append(f"[{len(arquivos)} faixas de {pasta}]")
                    else:
                        await interaction.followup.send(
                            f"⚠️ A pasta `{pasta}` está vazia!", ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        f"❌ Pasta `{pasta}` não encontrada!", ephemeral=True
                    )

            # ───  C) Arquivo local simples  ───────────────────────────────────
            else:
                audio_file = self.buscar_arquivo(nome)
                if audio_file:
                    self.queues[guild_id].append(audio_file)
                    encontrados.append(nome)
                else:
                    await interaction.followup.send(
                        f"⚠️ Arquivo `{nome}` não encontrado!", ephemeral=True
                    )

        # ─── Sem nada válido? retorna ──────────────────────────────────────
        if not encontrados:
            return await interaction.followup.send(
                "❌ Nenhum áudio, pasta ou URL válido foi encontrado!", ephemeral=True
            )

        # ─── Inicia reprodução ou adiciona à fila ─────────────────────────
        if not vc.is_playing():
            self.play_next(guild_id)
            await interaction.followup.send(f"🎵 Tocando agora: **{encontrados[0]}**")
        else:
            await interaction.followup.send(
                f"🎶 Adicionado à fila: {', '.join(encontrados)}"
            )

    @app_commands.command(name="listar", description="Lista todos os áudios")
    async def listar(self, interaction: discord.Interaction):
        diretorio = "assets/audios"
        if not os.path.exists(diretorio):
            return await interaction.response.send_message("❌ Diretório não encontrado!", ephemeral=True)

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
            await interaction.response.send_message(f"**Arquivos e pastas em `{diretorio}`:**\n```\n{lista_arquivos}\n```")

    @app_commands.command(name="parar", description="Para a reprodução e limpa a fila")
    async def parar(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)

        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ Não há áudio tocando!", ephemeral=True)

        self.queues[guild_id] = []  # Limpa a fila
        vc.stop()
        await interaction.response.send_message("⏹️ Reprodução interrompida e fila limpa!")

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

        # Tentativa adicional: remover diretamente uma instância problemática pelo ID conhecido
        try:
            problematic_id = 1317632778505814046  # ID fornecido
            if problematic_id in self.voice_clients:
                try:
                    vc = self.voice_clients.get(problematic_id)
                    if vc:
                        await vc.disconnect()
                    desconectados += 1
                except Exception as e:
                    erros.append(f"force-{problematic_id}: {e}")
                finally:
                    self.voice_clients.pop(problematic_id, None)
                    self.queues.pop(problematic_id, None)
                    self.loop_status.pop(problematic_id, None)
        except Exception as e:
            erros.append(f"cleanup-force-{problematic_id}-error: {e}")

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
                    new_queue.append({"path": path, "title": title})
                    loaded.append(title)
                else:
                    # remote URL - mantêm como caminho para streaming ffmpeg/invidious
                    new_queue.append({"path": path, "title": title})
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
            elif is_playing:
                vc.pause()
                await interaction.response.send_message("⏸️ Reprodução pausada.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Não há áudio tocando no momento.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao alterar o estado de reprodução: {e}", ephemeral=True)
            
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
