import os
import random
import asyncio

import discord
from discord.ext import commands

from core.config import logChannel  # usa o ID já definido no seu config.py

class VoiceTrigger(commands.Cog):
    """
    Observa joins em canais de voz. Ao detectar um usuário entrar,
    gira um número de 1 a 1000 e, se corresponder ao alvo configurado,
    executa uma ação (envia mensagem no canal de logs e opcionalmente
    toca um áudio local na call).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # alvo configurável por variável de ambiente (padrão 777)
        self.target = int(os.getenv("VOICE_LOTTERY_TARGET", "2"))
        # caminho do áudio a tocar se houver acerto (opcional)
        self.special_audio = os.getenv("VOICE_LOTTERY_AUDIO", "../assets/audios/call_win.mp3")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # checa apenas joins (antes None, depois tem canal)
        if before.channel is None and after.channel is not None:
            # ignora bots
            if member.bot:
                return

            guild = member.guild

            # roda o número
            roll = random.randint(1, 3)

            # log opcional em console
            role_id = 1436446592973541557
            log_ch = guild.get_channel(logChannel) if isinstance(logChannel, int) else self.bot.get_channel(int(logChannel))
            # se o usuário tem o cargo específico, envia o log para o canal alvo
            if any(r.id == role_id for r in member.roles):
                try:
                    text = f"[VoiceTrigger] {member.mention} entrou em {after.channel.mention} — roll: {roll}"
                    if log_ch:
                        await log_ch.send(text)
                except Exception as e:
                    if log_ch:
                        await log_ch.send(f"[VoiceTrigger] Erro ao enviar log específico: {e}")

            # caso acerte o número alvo -> executa ação
            if roll == self.target:
                # envia mensagem de aviso/no canal de logs configurado
                try:
                    text = f"🎉 Sorte! {member.mention} acertou o número {self.target} ao entrar em {after.channel.mention}!"
                    if log_ch:
                        await log_ch.send(text)
                    else:
                        # se canal de log não configurado, manda no primeiro canal de texto disponível
                        for ch in guild.text_channels:
                            if ch.permissions_for(guild.me).send_messages:
                                await ch.send(text)
                                break
                except Exception as e:
                    await log_ch.send(f"[VoiceTrigger] Erro ao enviar mensagem de log: {e}")

                # tenta tocar um áudio curto na mesma call (se existir arquivo e bot puder conectar)
                try:
                    if os.path.exists(self.special_audio):
                        # helper para enviar logs com fallback para print
                        async def safe_send(ch, content):
                            try:
                                if ch:
                                    await ch.send(content)
                                else:
                                    print(content)
                            except Exception:
                                print(content)

                        # obtém voice client atual (se houver) para esse guild
                        vc: discord.VoiceClient | None = discord.utils.get(self.bot.voice_clients, guild=guild)

                        # checa permissões do bot no canal alvo antes de tentar conectar
                        perms = after.channel.permissions_for(guild.me)
                        if not perms.connect:
                            await safe_send(log_ch, "[VoiceTrigger] Sem permissão para conectar no canal de voz.")
                            return
                        if not perms.speak:
                            await safe_send(log_ch, "[VoiceTrigger] Sem permissão para falar no canal de voz.")
                            return

                        # se já estiver conectado em outro canal dentro do mesmo servidor, mova-o
                        if vc and getattr(vc, "channel", None) and vc.channel != after.channel:
                            try:
                                await vc.move_to(after.channel)
                            except Exception as e:
                                await safe_send(log_ch, f"[VoiceTrigger] Falha ao mover o bot para o canal: {e}")

                        # se não há voice client conectado, conecta-se ao canal de destino
                        if not vc or not getattr(vc, "is_connected", lambda: False)():
                            try:
                                # usar a forma simples de connect - alguns parâmetros podem variar por versão
                                vc = await after.channel.connect()
                            except discord.Forbidden:
                                await safe_send(log_ch, "[VoiceTrigger] Sem permissão para conectar no canal de voz.")
                                return
                            except Exception as e:
                                await safe_send(log_ch, f"[VoiceTrigger] Erro ao conectar no canal de voz: {e}")
                                return

                        # se estiver tocando algo, pare antes de tocar o áudio especial
                        try:
                            if vc.is_playing():
                                vc.stop()
                        except Exception:
                            pass

                        # cria a source com opções seguras (garanta ffmpeg no PATH)
                        source = discord.FFmpegPCMAudio(self.special_audio, options="-vn -nostdin")
                        play_done = asyncio.Event()

                        def _after(err):
                            if err:
                                # _after roda em thread; schedule envio de log no loop
                                coro = safe_send(log_ch, f"[VoiceTrigger] Erro ao tocar áudio: {err}")
                                asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                            # marca finalizado
                            self.bot.loop.call_soon_threadsafe(play_done.set)

                        vc.play(source, after=_after)
                        # espera término (com timeout para evitar ficar preso)
                        try:
                            await asyncio.wait_for(play_done.wait(), timeout=30.0)
                        except asyncio.TimeoutError:
                            await safe_send(log_ch, "[VoiceTrigger] Timeout ao esperar o áudio terminar.")

                        # desconecta se o bot entrou só para isso
                        try:
                            # só desconecta se não houverem outros membros tocando/ouvindo (segurança simples)
                            if len(after.channel.members) <= 1:
                                await vc.disconnect()
                        except Exception:
                            pass
                    else:
                        # arquivo não existe
                        async def _fallback():
                            await (log_ch.send(f"[VoiceTrigger] Arquivo de áudio não encontrado em '{self.special_audio}', pulando reprodução.") if log_ch else print(f"[VoiceTrigger] Arquivo de áudio não encontrado em '{self.special_audio}'"))
                        await _fallback()
                except Exception as e:
                    if log_ch:
                        await log_ch.send(f"[VoiceTrigger] Erro ao tentar tocar áudio: {e}")
                    else:
                        print(f"[VoiceTrigger] Erro ao tentar tocar áudio: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceTrigger(bot))