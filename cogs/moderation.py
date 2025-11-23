# cogs/moderation.py
import asyncio
import discord
import random
import string
import re
from discord import app_commands
from discord.ext import commands
from core.modules import save, load

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
                            cargo="(Opcional) Apenas move membros com um cargo específico")
    async def mover(self, interaction: discord.Interaction, origem: discord.VoiceChannel, destino: discord.VoiceChannel, cargo: discord.Role = None):
        if not interaction.user.guild_permissions.move_members:
            return await interaction.response.send_message("🚫 Você não tem permissão para mover membros!", ephemeral=True)

        membros_movidos = 0

        for membro in origem.members:
            if cargo and cargo not in membro.roles:
                continue  # Se um cargo foi especificado, ignora membros que não o possuem
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
            member_list.append(m)
            member_ids.add(m.id)

        # Processa cada parte
        mention_re = re.compile(r"^<@!?(\d+)>$")
        for part in parts:
            # mention format
            m = mention_re.match(part)
            if m:
                try:
                    await add_member_by_id(int(m.group(1)))
                    continue
                except Exception:
                    continue

            # plain ID
            if part.isdigit():
                try:
                    await add_member_by_id(int(part))
                    continue
                except Exception:
                    continue

            # Try name/display name substring match (first matches up to limit)
            lower = part.lower()
            for gm in interaction.guild.members:
                if gm.id in member_ids:
                    continue
                if lower in gm.display_name.lower() or lower in gm.name.lower():
                    member_list.append(gm)
                    member_ids.add(gm.id)
                    break

            if len(member_list) >= 10:
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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))