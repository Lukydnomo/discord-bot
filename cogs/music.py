# cogs/music.py
import os
import random
import asyncio
import unidecode
from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Optional

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

        if interaction.guild.id in self.self.voice_clients:
            return await interaction.response.send_message("⚠️ Já estou em um canal de voz!", ephemeral=True)

        vc = await canal.connect()
        self.self.voice_clients[interaction.guild.id] = vc
        await interaction.response.send_message(f"🔊 Entrei no canal {canal.mention}!")

    @app_commands.command(name="tocar", description="Toca um ou mais áudios no canal de voz")
    @app_commands.describe(arquivo="Nome(s) do(s) arquivo(s) de áudio ou pasta, separados por vírgula")
    async def tocar(self, interaction: discord.Interaction, arquivo: str):
        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)

        if not vc:
            canal = interaction.user.voice.channel if interaction.user.voice else None
            if not canal:
                return await interaction.response.send_message("❌ Você não está em um canal de voz e o bot também não está!", ephemeral=True)
            vc = await canal.connect()
            self.voice_clients[guild_id] = vc

        nomes = [nome.strip() for nome in arquivo.split(",")]
        encontrados = []

        if guild_id not in self.queues:
            self.queues[guild_id] = []

        for nome in nomes:
            if nome.startswith("*"):
                pasta = nome[1:]
                caminho_pasta = os.path.join("assets/audios", pasta)
                if os.path.exists(caminho_pasta) and os.path.isdir(caminho_pasta):
                    arquivos = sorted([
                        os.path.join(caminho_pasta, f)
                        for f in os.listdir(caminho_pasta)
                        if os.path.isfile(os.path.join(caminho_pasta, f))
                    ])
                    if arquivos:
                        self.queues[guild_id].extend(arquivos)
                        encontrados.append(f"[{len(arquivos)} de {pasta}]")
                    else:
                        await interaction.channel.send(f"⚠️ A pasta `{pasta}` está vazia!")
                else:
                    await interaction.channel.send(f"❌ Pasta `{pasta}` não encontrada!")
            else:
                audio_file = self.buscar_arquivo(nome)
                if audio_file:
                    self.queues[guild_id].append(audio_file)
                    encontrados.append(nome)
                else:
                    await interaction.channel.send(f"⚠️ Arquivo `{nome}` não encontrado!")

        if not encontrados:
            return await interaction.response.send_message("❌ Nenhum dos áudios ou pastas foi encontrado!", ephemeral=True)

        if not vc.is_playing():
            self.play_next(guild_id)
            await interaction.response.send_message(f"🎵 Tocando `{encontrados[0]}` e adicionando o resto à fila!")
        else:
            await interaction.response.send_message(f"🎶 Adicionado(s) à fila: {', '.join(encontrados)}")

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

    @app_commands.command(name="sair", description="Faz o bot sair do canal de voz e limpa a fila de reprodução")
    async def sair(self, interaction: discord.Interaction):
        vc = self.voice_clients.pop(interaction.guild.id, None)
        if not vc:
            return await interaction.response.send_message("❌ Não estou em um canal de voz!", ephemeral=True)

        self.queues.pop(interaction.guild.id, None)  # Limpa a fila de reprodução
        await vc.disconnect()
        await interaction.response.send_message("👋 Saí do canal de voz e limpei a fila de reprodução!")

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

        lista = "\n".join([f"{idx+1}. {track['title']}" for idx, track in enumerate(queue)])
        await interaction.response.send_message(f"📜 **Fila de reprodução:**\n```\n{lista}\n```")

    @app_commands.command(name="loop")
    @app_commands.describe(modo="0: Desativado, 1: Música Atual, 2: Fila Inteira (opcional)")
    async def loop(self, interaction: discord.Interaction, modo: int = None):
        # Alterna o loop entre 0 (desativado), 1 (música atual) e 2 (fila inteira), ou define um modo específico
        guild_id = interaction.guild.id
        estado_atual = self.loop_status.get(guild_id, 0)

        if modo is None:
            # Alterna entre 0 → 1 → 2 → 0...
            novo_estado = (estado_atual + 1) % 3
        else:
            # Se um valor for fornecido, define diretamente (garantindo que esteja entre 0 e 2)
            novo_estado = max(0, min(2, modo))

        self.loop_status[guild_id] = novo_estado

        mensagens = {
            0: "🔁 Loop desativado!",
            1: "🔂 Loop da música atual ativado!",
            2: "🔁 Loop da fila inteira ativado!",
        }

        await interaction.response.send_message(mensagens[novo_estado])

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
        guild_id = interaction.guild.id
        queue = self.queues.get(guild_id, [])

        if not queue:
            return await interaction.response.send_message("❌ A fila está vazia, nada para salvar!", ephemeral=True)

        # Gera um ID único baseado nos nomes dos arquivos na fila
        nomes_arquivos = [track["title"] for track in queue]
        fila_serializada = ",".join(nomes_arquivos)
        fila_codificada = urlsafe_b64encode(fila_serializada.encode()).decode()

        await interaction.response.send_message(f"✅ Fila salva com sucesso! Use este ID para carregar: `{fila_codificada}`", ephemeral=True)

    @app_commands.command(name="carregar_fila", description="Carrega uma fila salva usando um ID")
    @app_commands.describe(fila_id="ID da fila a ser carregada")
    async def carregar_fila(self, interaction: discord.Interaction, fila_id: str):
        try:
            # Decodifica o ID para obter os nomes dos arquivos
            fila_decodificada = urlsafe_b64decode(fila_id.encode()).decode()
            nomes_arquivos = fila_decodificada.split(",")

            guild_id = interaction.guild.id
            if guild_id not in self.queues:
                self.queues[guild_id] = []

            encontrados = []
            for nome in nomes_arquivos:
                audio_file = self.buscar_arquivo(nome)
                if audio_file:
                    self.queues[guild_id].append({
                        "type": "local",
                        "path": audio_file,
                        "title": nome
                    })
                    encontrados.append(nome)
                else:
                    await interaction.channel.send(f"⚠️ Arquivo `{nome}` não encontrado!")

            if not encontrados:
                return await interaction.response.send_message("❌ Nenhum dos áudios foi encontrado!", ephemeral=True)

            vc = self.voice_clients.get(guild_id)
            if not vc or not vc.is_playing():
                self.play_next(guild_id)
                await interaction.response.send_message(f"🎵 Fila carregada e tocando `{encontrados[0]}`!")
            else:
                await interaction.response.send_message(f"🎶 Fila carregada! Adicionado(s) à fila: {', '.join(encontrados)}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao carregar a fila: {e}", ephemeral=True)
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
