# cogs/moderation.py
import asyncio
import discord
import random
import string
import re
from discord import app_commands
from discord.ext import commands
from core.modules import save, load
from discord.ui import View, Button

from core.modules import save, load, get_file_content, update_file_content

AFK_PREFIX = "[AFK] "
AFK_PREFIX_RE = re.compile(r"^\[AFK\]\s*")
class MuteUnmuteView(View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(label="Mutar Todos", style=discord.ButtonStyle.danger, custom_id="mute_all")
    async def mute_all(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message("❌ Você não tem permissão para mutar membros.", ephemeral=True)
            return

        count = 0
        for member in self.channel.members:
            if member.bot:
                continue
            if member.voice and not member.voice.mute:
                try:
                    await member.edit(mute=True)
                    count += 1
                except Exception:
                    pass

        await interaction.response.send_message(f"🔇 Mutados: {count} membros.", ephemeral=True)

    @discord.ui.button(label="Desmutar Todos", style=discord.ButtonStyle.success, custom_id="unmute_all")
    async def unmute_all(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message("❌ Você não tem permissão para desmutar membros.", ephemeral=True)
            return

        count = 0
        for member in self.channel.members:
            if member.bot:
                continue
            if member.voice and member.voice.mute:
                try:
                    await member.edit(mute=False)
                    count += 1
                except Exception:
                    pass

        await interaction.response.send_message(f"🔊 Desmutados: {count} membros.", ephemeral=True)

class Moderation(commands.Cog):
    """Comandos de punição, mover, mutar e desmutar."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.glitch_active = set()  # Rastreia usuários com glitch ativo

    @app_commands.command(name="punir", description="Pune um membro movendo-o para um canal de voz específico por um tempo determinado.")
    @app_commands.describe(
        member="Membro a ser punido",
        punish_channel="Canal de voz onde o membro será movido",
        duration="Duração da punição em minutos (opcional, padrão: 1 minuto)"
    )
    async def punir(self, interaction: discord.Interaction, member: discord.Member, punish_channel: discord.VoiceChannel, duration: int = 1):
        try:
            # Verifica permissões do autor
            if interaction.user.top_role <= interaction.guild.me.top_role:
                await interaction.response.send_message("❌ **Você precisa ter um cargo superior ao meu para usar este comando!**", ephemeral=True)
                return

            # Verifica se o autor está em um canal de voz
            if not interaction.user.voice:
                await interaction.response.send_message("❌ **Você precisa estar em um canal de voz para usar este comando!**", ephemeral=True)
                return

            # Salva o canal original e move o membro para o canal de punição
            original_channel = member.voice.channel if member.voice else None
            await member.move_to(punish_channel)
            await interaction.response.send_message(f'✅ **{member.mention} foi punido e movido para {punish_channel.name} por {duration} minutos**')

            # Desabilita a permissão de conectar aos outros canais
            for channel in interaction.guild.voice_channels:
                if channel != punish_channel:
                    await channel.set_permissions(member, connect=False)

            # Aguarda a duração da punição
            await asyncio.sleep(duration * 60)

            # Restaura as permissões de conexão
            for channel in interaction.guild.voice_channels:
                if channel != punish_channel:
                    await channel.set_permissions(member, overwrite=None)

            # Move o membro de volta para o canal original
            if original_channel:
                await member.move_to(original_channel)
                await interaction.followup.send(f'✅ **{member.mention} foi movido de volta para {original_channel.name}**')
            else:
                await interaction.followup.send(f'✅ **{member.mention} foi liberado, mas não havia um canal original para movê-lo.**')

        except discord.Forbidden:
            await interaction.followup.send("❌ **Eu não tenho permissão suficiente para executar essa ação!**", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ **Ocorreu um erro ao mover o membro: {e}**", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ **Algo deu errado: {e}**", ephemeral=True)

    @app_commands.command(name="mover", description="Move todos os membros de um canal de voz para outro")
    @app_commands.describe(origem="Canal de onde os usuários serão movidos",
                            destino="Canal para onde os usuários serão movidos",
                            cargo="(Opcional) Apenas move membros com um cargo específico",
                            exceto="(Opcional) Usuários a serem excluídos (separe por vírgula)")
    async def mover(self, interaction: discord.Interaction, origem: discord.VoiceChannel, destino: discord.VoiceChannel, cargo: discord.Role = None, exceto: str = None):
        if not interaction.user.guild_permissions.move_members:
            return await interaction.response.send_message("🚫 Você não tem permissão para mover membros!", ephemeral=True)

        exceto_members = set()
        if exceto:
            exceto_parts = [p.strip() for p in exceto.split(",") if p.strip()]
            mention_re = re.compile(r"^<@!?(\d+)>$")
            for part in exceto_parts:
                m = mention_re.match(part)
                if m:
                    mid = int(m.group(1))
                    member = interaction.guild.get_member(mid)
                    if member:
                        exceto_members.add(member.id)
                elif part.isdigit():
                    mid = int(part)
                    member = interaction.guild.get_member(mid)
                    if member:
                        exceto_members.add(member.id)

        membros_movidos = 0

        for membro in origem.members:
            if cargo and cargo not in membro.roles:
                continue  # Se um cargo foi especificado, ignora membros que não o possuem
            if membro.id in exceto_members:
                continue  # Se o membro estiver na lista de excluídos, ignora
            try:
                await membro.move_to(destino)
                membros_movidos += 1
            except discord.Forbidden:
                await interaction.response.send_message(f"🚨 Não tenho permissão para mover {membro.mention}!", ephemeral=True)

        await interaction.response.send_message(f"✅ **{membros_movidos}** membros movidos de {origem.mention} para {destino.mention}!")
    
    @app_commands.command(name="mutar", description="Muta todos em um canal de voz, um usuário ou um cargo específico")
    @app_commands.describe(
        canal="Canal de voz onde os membros serão mutados",
        excecao_usuario="(Opcional) Usuário que NÃO será mutado",
        excecao_cargo="(Opcional) Cargo cujos membros NÃO serão mutados",
        apenas_usuario="(Opcional) Mutar SOMENTE este usuário",
        apenas_cargo="(Opcional) Mutar SOMENTE este cargo"
    )
    async def mutar(
        self,
        interaction: discord.Interaction,
        canal: discord.VoiceChannel,
        excecao_usuario: discord.Member = None,
        excecao_cargo: discord.Role = None,
        apenas_usuario: discord.Member = None,
        apenas_cargo: discord.Role = None
    ):
        if not interaction.user.guild_permissions.mute_members:
            return await interaction.response.send_message("🚫 Você não tem permissão para mutar membros!", ephemeral=True)

        # Mutar apenas um usuário
        if apenas_usuario:
            try:
                await apenas_usuario.edit(mute=True)
                return await interaction.response.send_message(f"🔇 {apenas_usuario.mention} foi mutado em {canal.mention}!")
            except discord.Forbidden:
                return await interaction.response.send_message(f"🚨 Não tenho permissão para mutar {apenas_usuario.mention}!", ephemeral=True)

        # Mutar apenas um cargo
        if apenas_cargo:
            membros_mutados = 0
            for membro in canal.members:
                if apenas_cargo in membro.roles:
                    try:
                        await membro.edit(mute=True)
                        membros_mutados += 1
                    except discord.Forbidden:
                        await interaction.response.send_message(f"🚨 Não tenho permissão para mutar {membro.mention}!", ephemeral=True)
            return await interaction.response.send_message(f"🔇 **{membros_mutados}** membros do cargo {apenas_cargo.mention} foram mutados em {canal.mention}!")

        # Mutar todo mundo (exceto quem for exceção)
        membros_mutados = 0
        for membro in canal.members:
            if membro == excecao_usuario or (excecao_cargo and excecao_cargo in membro.roles):
                continue  # Pula quem deve ser ignorado

            try:
                await membro.edit(mute=True)
                membros_mutados += 1
            except discord.Forbidden:
                await interaction.response.send_message(f"🚨 Não tenho permissão para mutar {membro.mention}!", ephemeral=True)

        await interaction.response.send_message(f"🔇 **{membros_mutados}** membros foram mutados em {canal.mention}!")
    
    @app_commands.command(name="desmutar", description="Desmuta todos em um canal de voz ou apenas um membro específico")
    @app_commands.describe(
        canal="Canal de voz onde os membros serão desmutados",
        apenas_usuario="(Opcional) Desmutar SOMENTE este usuário",
        apenas_cargo="(Opcional) Desmutar SOMENTE membros desse cargo"
    )
    async def desmutar(
        self,
        interaction: discord.Interaction,
        canal: discord.VoiceChannel,
        apenas_usuario: discord.Member = None,
        apenas_cargo: discord.Role = None
    ):
        if not interaction.user.guild_permissions.mute_members:
            return await interaction.response.send_message("🚫 Você não tem permissão para desmutar membros!", ephemeral=True)

        if apenas_usuario:
            try:
                await apenas_usuario.edit(mute=False)
                return await interaction.response.send_message(f"🔊 {apenas_usuario.mention} foi desmutado em {canal.mention}!")
            except discord.Forbidden:
                return await interaction.response.send_message(f"🚨 Não tenho permissão para desmutar {apenas_usuario.mention}!", ephemeral=True)

        membros_desmutados = 0

        for membro in canal.members:
            if apenas_cargo and apenas_cargo not in membro.roles:
                continue  # Pula quem não faz parte do cargo especificado

            try:
                await membro.edit(mute=False)
                membros_desmutados += 1
            except discord.Forbidden:
                await interaction.response.send_message(f"🚨 Não tenho permissão para desmutar {membro.mention}!", ephemeral=True)

        if apenas_cargo:
            await interaction.response.send_message(f"🔊 **{membros_desmutados}** membros com o cargo {apenas_cargo.mention} foram desmutados em {canal.mention}!")
        else:
            await interaction.response.send_message(f"🔊 **{membros_desmutados}** membros foram desmutados em {canal.mention}!")

    @app_commands.command(name="glitch_nickname", description="Causa um 'glitch' no apelido de um ou mais usuários por um tempo determinado")
    @app_commands.describe(
        members="Membro(s) que sofrerão o glitch (separe por vírgula)",
        duration="Duração do glitch em segundos"
    )
    async def glitch_nickname(self, interaction: discord.Interaction, members: str, duration: int):
        """Troca o apelido por caracteres aleatórios continuamente e volta após o tempo.

        `members` deve ser uma lista separada por vírgulas contendo mentions (`<@id>`), IDs ou partes de nomes.
        """

        # Verifica permissões do autor
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message(
                "🚫 Você não tem permissão para gerenciar apelidos!",
                ephemeral=True
            )

        # Normaliza e separa as entradas por vírgula
        parts = [p.strip() for p in members.split(",") if p.strip()]
        if not parts:
            return await interaction.response.send_message(
                "❌ Você precisa informar pelo menos um membro (separados por vírgula).",
                ephemeral=True
            )

        member_list = []
        member_ids = set()

        # Função auxiliar para adicionar membro único
        async def add_member_by_id(mid: int):
            if mid in member_ids:
                return
            m = interaction.guild.get_member(mid)
            if m is None:
                try:
                    m = await interaction.guild.fetch_member(mid)
                except discord.NotFound:
                    return
            # Ignora membros cujo cargo seja maior ou igual ao do bot
            try:
                if m.top_role >= interaction.guild.me.top_role:
                    return
            except Exception:
                # Em caso de guild.me não disponível ou outro erro, ignora a verificação
                pass

            member_list.append(m)
            member_ids.add(m.id)

        # Processa cada parte: suportando mention de membro <@id>, mention de cargo <@&id>, IDs e nomes/parciais
        mention_re = re.compile(r"^<@!?(\d+)>$")
        role_re = re.compile(r"^<@&(\d+)>$")
        MAX_MEMBERS = 10
        for part in parts:
            # role mention format <@&id>
            rm = role_re.match(part)
            if rm:
                try:
                    role_id = int(rm.group(1))
                    role = interaction.guild.get_role(role_id)
                    if role:
                        for gm in role.members:
                            if gm.id in member_ids:
                                continue
                            # Ignora membros cujo cargo seja maior ou igual ao do bot
                            try:
                                if gm.top_role >= interaction.guild.me.top_role:
                                    continue
                            except Exception:
                                pass
                            member_list.append(gm)
                            member_ids.add(gm.id)
                            if len(member_list) >= MAX_MEMBERS:
                                break
                except Exception:
                    pass
                if len(member_list) >= MAX_MEMBERS:
                    break
                continue

            # member mention format <@id>
            m = mention_re.match(part)
            if m:
                try:
                    await add_member_by_id(int(m.group(1)))
                except Exception:
                    pass
                if len(member_list) >= MAX_MEMBERS:
                    break
                continue

            # If it's all digits, it may be a role ID or member ID
            if part.isdigit():
                pid = int(part)
                # Prefer role if exists
                role = interaction.guild.get_role(pid)
                if role:
                    for gm in role.members:
                        if gm.id in member_ids:
                            continue
                        member_list.append(gm)
                        member_ids.add(gm.id)
                        if len(member_list) >= MAX_MEMBERS:
                            break
                    if len(member_list) >= MAX_MEMBERS:
                        break
                    continue
                else:
                    try:
                        await add_member_by_id(pid)
                    except Exception:
                        pass
                    if len(member_list) >= MAX_MEMBERS:
                        break
                    continue

            # Try matching role by name substring first
            lower = part.lower()
            matched_role = None
            for role in interaction.guild.roles:
                if lower in role.name.lower():
                    matched_role = role
                    break
            if matched_role:
                for gm in matched_role.members:
                    if gm.id in member_ids:
                        continue
                    try:
                        if gm.top_role >= interaction.guild.me.top_role:
                            continue
                    except Exception:
                        pass
                    member_list.append(gm)
                    member_ids.add(gm.id)
                    if len(member_list) >= MAX_MEMBERS:
                        break
                if len(member_list) >= MAX_MEMBERS:
                    break
                continue

            # Try name/display name substring match (first match)
            for gm in interaction.guild.members:
                if gm.id in member_ids:
                    continue
                if lower in gm.display_name.lower() or lower in gm.name.lower():
                    try:
                        if gm.top_role >= interaction.guild.me.top_role:
                            continue
                    except Exception:
                        pass
                    member_list.append(gm)
                    member_ids.add(gm.id)
                    break

            if len(member_list) >= MAX_MEMBERS:
                break

        if not member_list:
            return await interaction.response.send_message(
                f"❌ Nenhum membro encontrado para: {members}",
                ephemeral=True
            )

        # Verifica quem já está em glitch
        already_glitching = [m for m in member_list if m.id in self.glitch_active]
        if already_glitching:
            already_names = ", ".join([m.display_name for m in already_glitching])
            return await interaction.response.send_message(
                f"❌ **{already_names}** já está(ão) em glitch! Aguarde antes de tentar novamente.",
                ephemeral=True
            )

        # Verifica cargo do bot
        invalid_members = [m for m in member_list if m.top_role >= interaction.guild.me.top_role]
        if invalid_members:
            invalid_names = ", ".join([m.display_name for m in invalid_members])
            return await interaction.response.send_message(
                f"🚫 Meu cargo não é superior ao de {invalid_names}. Não posso mudar seus apelidos!",
                ephemeral=True
            )

        # Salva nicks originais e marca ativos
        original_nicks = {}
        valid_members = []
        for m in member_list:
            original_nicks[m.id] = m.display_name
            valid_members.append(m)
            self.glitch_active.add(m.id)

        try:
            member_names = ", ".join([m.display_name for m in valid_members])
            await interaction.response.send_message(
                f"🌀 **Glitch ativado em: {member_names}** Duração: {duration}s",
                ephemeral=True
            )

            end_time = asyncio.get_event_loop().time() + duration
            while asyncio.get_event_loop().time() < end_time:
                for m in valid_members:
                    glitch_length = len(original_nicks.get(m.id, m.display_name))
                    random_chars = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=glitch_length))
                    try:
                        await m.edit(nick=random_chars)
                    except (discord.Forbidden, discord.NotFound):
                        pass
                    except Exception:
                        pass
                await asyncio.sleep(0.5)

            for m in valid_members:
                try:
                    original = original_nicks.get(m.id)
                    await m.edit(nick=original if original != m.name else None)
                except Exception:
                    pass

        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Erro ao aplicar glitch: {e}", ephemeral=True)
            except Exception:
                pass
        finally:
            for m in valid_members:
                self.glitch_active.discard(m.id)

    @app_commands.command(name="db_test", description="Testa o banco de dados")
    @app_commands.describe(action="Escolha entre save ou load", name="Nome da chave", value="Valor a ser salvo (apenas para save)")
    async def db_test(self, interaction: discord.Interaction, action: str, name: str, value: str = None):
        # Defer a resposta para garantir mais tempo para processamento
        await interaction.response.defer()

        if action == "save":
            if value is None:
                await interaction.followup.send("Você precisa fornecer um valor para salvar!", ephemeral=True)
                return
            await save(name, value)
            await interaction.followup.send(f"Salvo: `{name}` = `{value}`")
        elif action == "load":
            result = load(name)
            if result is None:
                await interaction.followup.send(f"Nenhum dado encontrado para `{name}`.", ephemeral=True)
            else:
                await interaction.followup.send(f"Valor de `{name}`: `{result}`")
        else:
            await interaction.followup.send("Ação inválida! Use 'save' ou 'load'.", ephemeral=True)
        
    # ---------- Mute Call ----------
    @app_commands.command(name="mutecall", description="Cria botões para mutar/desmutar todos na call atual.")
    async def mutecall(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Você precisa estar em um canal de voz.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        embed = discord.Embed(
            title="Controle de Mute da Call",
            description=f"Canal: **{channel.name}**\nUse os botões abaixo para mutar ou desmutar todos na call.",
            color=discord.Color.blue(),
        )
        view = MuteUnmuteView(channel)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="afk", description="Alterna seu apelido entre normal e [AFK] no servidor.")
    async def afk(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "❌ Isso só funciona em servidor.",
                ephemeral=True,
            )

        member = interaction.user
        me = interaction.guild.me

        if not isinstance(member, discord.Member):
            return await interaction.response.send_message(
                "❌ Não consegui identificar seu membro no servidor.",
                ephemeral=True,
            )

        if me is None:
            return await interaction.response.send_message(
                "❌ Não consegui identificar meu usuário no servidor.",
                ephemeral=True,
            )

        if not me.guild_permissions.manage_nicknames:
            return await interaction.response.send_message(
                "❌ Eu preciso da permissão **Gerenciar Apelidos** para usar esse comando.",
                ephemeral=True,
            )

        if member == interaction.guild.owner:
            return await interaction.response.send_message(
                "❌ Não consigo alterar o apelido do dono do servidor.",
                ephemeral=True,
            )

        if member.top_role >= me.top_role:
            return await interaction.response.send_message(
                "❌ Meu cargo precisa estar acima do seu para eu conseguir mudar seu apelido.",
                ephemeral=True,
            )

        current_display = member.display_name or member.name
        is_afk = bool(AFK_PREFIX_RE.match(current_display))

        def _read_afk_state():
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}

            afk_root = data.get("afk_nicks")
            if not isinstance(afk_root, dict):
                afk_root = {}
                data["afk_nicks"] = afk_root

            guild_bucket = afk_root.get(str(interaction.guild.id))
            if not isinstance(guild_bucket, dict):
                guild_bucket = {}
                afk_root[str(interaction.guild.id)] = guild_bucket

            user_key = str(member.id)
            stored = guild_bucket.get(user_key)
            if not isinstance(stored, dict):
                stored = {}

            original_nick = stored.get("nick")
            fallback_name = AFK_PREFIX_RE.sub("", current_display, count=1).strip() or member.name
            return original_nick, fallback_name

        def _persist_afk_state(turn_on: bool):
            data = get_file_content()
            if not isinstance(data, dict):
                data = {}

            afk_root = data.get("afk_nicks")
            if not isinstance(afk_root, dict):
                afk_root = {}
                data["afk_nicks"] = afk_root

            guild_bucket = afk_root.get(str(interaction.guild.id))
            if not isinstance(guild_bucket, dict):
                guild_bucket = {}
                afk_root[str(interaction.guild.id)] = guild_bucket

            user_key = str(member.id)
            if turn_on:
                guild_bucket[user_key] = {
                    "nick": member.nick,
                    "display_name": current_display,
                }
            else:
                guild_bucket.pop(user_key, None)

            return update_file_content(data)

        original_nick, fallback_name = await asyncio.to_thread(_read_afk_state)

        if not is_afk:
            base_name = current_display.strip() or member.name
            max_base_len = 32 - len(AFK_PREFIX)
            new_nick = f"{AFK_PREFIX}{base_name[:max_base_len]}"

            try:
                await member.edit(nick=new_nick)
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "❌ Não tenho permissão suficiente para alterar seu apelido.",
                    ephemeral=True,
                )
            except discord.HTTPException as e:
                return await interaction.response.send_message(
                    f"❌ Não consegui ativar o AFK: {e}",
                    ephemeral=True,
                )

            saved = await asyncio.to_thread(_persist_afk_state, True)
            if not saved:
                return await interaction.response.send_message(
                    f"⚠️ Ativei seu AFK, mas não consegui salvar o nome original no banco. Seu apelido agora é **{new_nick}**.",
                    ephemeral=True,
                )

            await interaction.response.send_message(
                f"💤 Modo AFK ativado. Seu apelido agora é **{new_nick}**.",
                ephemeral=True,
            )
        else:
            try:
                await member.edit(nick=original_nick)
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "❌ Não tenho permissão suficiente para restaurar seu apelido.",
                    ephemeral=True,
                )
            except discord.HTTPException as e:
                return await interaction.response.send_message(
                    f"❌ Não consegui remover o AFK: {e}",
                    ephemeral=True,
                )

            saved = await asyncio.to_thread(_persist_afk_state, False)
            restored_name = original_nick if original_nick else fallback_name
            if not saved:
                return await interaction.response.send_message(
                    f"⚠️ Removi seu AFK, mas não consegui limpar o registro salvo no banco. Seu apelido voltou para **{restored_name}**.",
                    ephemeral=True,
                )

            await interaction.response.send_message(
                f"✅ Modo AFK removido. Seu apelido voltou para **{restored_name}**.",
                ephemeral=True,
            )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))