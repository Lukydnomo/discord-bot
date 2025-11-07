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
        self.target = int(os.getenv("VOICE_LOTTERY_TARGET", "666"))
        # caminho do áudio a tocar se houver acerto (opcional)
        self.special_audio = os.getenv("VOICE_LOTTERY_AUDIO", "assets/audios/call_win.mp3")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Helper para representar canais nos logs
        def ch_repr(ch):
            return f"{ch.name}({ch.id})" if ch else "None"

        # Debug rápido para inspecionar eventos (remova ou comente em produção)
        try:
            print(f"[VoiceTrigger] voice update: user={member} before={ch_repr(before.channel)} after={ch_repr(after.channel)}")
        except Exception:
            pass

        # Ignora bots
        if member.bot:
            return

        before_ch = before.channel
        after_ch = after.channel

        # Se não houve mudança de canal (mesmo objeto ou mesmos IDs), ignora
        if before_ch is after_ch:
            return
        if before_ch and after_ch and getattr(before_ch, "id", None) == getattr(after_ch, "id", None):
            return

        # Ignora saídas (se desejar contar saídas, remova este return)
        if after_ch is None:
            return

        # A partir daqui: é join (before_ch is None) OU move (before_ch != after_ch)
        is_move = before_ch is not None and (getattr(before_ch, "id", None) != getattr(after_ch, "id", None))
        action_text = "mudou para" if is_move else "entrou em"

        guild = member.guild

        # roda o número
        roll = random.randint(1, 1000)

        # log opcional em console
        role_id = 1436446592973541557
        log_ch = guild.get_channel(logChannel) if isinstance(logChannel, int) else self.bot.get_channel(int(logChannel))
        # se o usuário tem o cargo específico, envia o log para o canal alvo
        if any(r.id == role_id for r in member.roles):
            try:
                text = f"[VoiceTrigger] {member.mention} {action_text} {after_ch.mention} — roll: {roll}"
                if log_ch:
                    await log_ch.send(text)
            except Exception as e:
                if log_ch:
                    await log_ch.send(f"[VoiceTrigger] Erro ao enviar log específico: {e}")

        # caso acerte o número alvo -> executa ação
        if roll == self.target:
            try:
                text = f"🎉 Sorte! {member.mention} acertou o número {self.target} ao {action_text} {after_ch.mention}!"
                if log_ch:
                    await log_ch.send(text)
                else:
                    for ch in guild.text_channels:
                        if ch.permissions_for(guild.me).send_messages:
                            await ch.send(text)
                            break
            except Exception as e:
                if log_ch:
                    await log_ch.send(f"[VoiceTrigger] Erro ao enviar mensagem de log: {e}")

            # tenta tocar um áudio curto na mesma call (se existir arquivo e bot puder conectar)
            try:
                if os.path.exists(self.special_audio):
                    async def safe_send(ch, content):
                        try:
                            if ch:
                                await ch.send(content)
                            else:
                                print(content)
                        except Exception:
                            print(content)

                    vc: discord.VoiceClient | None = discord.utils.get(self.bot.voice_clients, guild=guild)

                    perms = after_ch.permissions_for(guild.me)
                    if not perms.connect:
                        await safe_send(log_ch, "[VoiceTrigger] Sem permissão para conectar no canal de voz.")
                        return
                    if not perms.speak:
                        await safe_send(log_ch, "[VoiceTrigger] Sem permissão para falar no canal de voz.")
                        return

                    if vc and getattr(vc, "channel", None) and vc.channel != after_ch:
                        try:
                            await vc.move_to(after_ch)
                        except Exception as e:
                            await safe_send(log_ch, f"[VoiceTrigger] Falha ao mover o bot para o canal: {e}")

                    if not vc or not getattr(vc, "is_connected", lambda: False)():
                        try:
                            vc = await after_ch.connect()
                        except discord.Forbidden:
                            await safe_send(log_ch, "[VoiceTrigger] Sem permissão para conectar no canal de voz.")
                            return
                        except Exception as e:
                            await safe_send(log_ch, f"[VoiceTrigger] Erro ao conectar no canal de voz: {e}")
                            return

                    try:
                        if vc.is_playing():
                            vc.stop()
                    except Exception:
                        pass

                    source = discord.FFmpegPCMAudio(self.special_audio, options="-vn -nostdin")
                    play_done = asyncio.Event()

                    def _after(err):
                        if err:
                            coro = safe_send(log_ch, f"[VoiceTrigger] Erro ao tocar áudio: {err}")
                            asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                        self.bot.loop.call_soon_threadsafe(play_done.set)

                    vc.play(source, after=_after)
                    try:
                        await asyncio.wait_for(play_done.wait(), timeout=30.0)
                    except asyncio.TimeoutError:
                        await safe_send(log_ch, "[VoiceTrigger] Timeout ao esperar o áudio terminar.")

                    try:
                        if len(after_ch.members) <= 1:
                            await vc.disconnect()
                    except Exception:
                        pass
                else:
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