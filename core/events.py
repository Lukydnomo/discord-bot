import asyncio
import discord
import unidecode
import json
import unicodedata
import re

from core.modules import *


async def on_ready_custom(bot, conteudo):
    """
    Evento executado quando o bot está pronto.
    """
    # Carrega o conteúdo do arquivo do GitHub
    get_file_content()
    await asyncio.sleep(3)

    print(f"Bot conectado como {bot.user}")
    for guild in bot.guilds:
        try:
            print(f"Sincronizando comandos para o servidor: {guild.name}")
            await bot.tree.sync(guild=guild)
            print(
                f"✅ Comandos sincronizados com sucesso para o servidor: {guild.name}"
            )
        except Exception as e:
            print(f"❌ Falha ao sincronizar comandos no servidor {guild.name}: {e}")

    # Atualiza o canal com o changelog (configurável por servidor)
    # use force=True to ensure we read the latest config from disk/GitHub
    data = get_file_content(force=True)
    guild_cfg = (data.get("guild_config") or {}) if isinstance(data, dict) else {}

    full_message = f"{conteudo}"

    def normalize_text(s: str) -> str:
        if s is None:
            return ""
        s = unicodedata.normalize("NFC", s)
        s = re.sub(r"[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    async def post_changelog(updatechannel: discord.TextChannel, mention_message: str | None):
        # quebra em chunks de 2000 chars (limite do Discord)
        message_chunks = [full_message[i:i + 2000] for i in range(0, len(full_message), 2000)]
        normalized_chunks = [normalize_text(ch) for ch in message_chunks]

        expected_count = len(message_chunks) + (1 if mention_message else 0)

        # pega as ÚLTIMAS mensagens (mais confiável que oldest_first=True)
        existing_messages = [msg async for msg in updatechannel.history(limit=expected_count + 5, oldest_first=False)]
        existing_messages.reverse()  # deixa em ordem cronológica

        existing_texts = [normalize_text(m.content) for m in existing_messages if m.content is not None]

        is_same = False
        if len(existing_texts) >= expected_count:
            for i in range(0, len(existing_texts) - expected_count + 1):
                window = existing_texts[i:i + expected_count]
                if mention_message:
                    if window[-1] == normalize_text(mention_message) and window[:-1] == normalized_chunks:
                        is_same = True
                        break
                else:
                    if window == normalized_chunks:
                        is_same = True
                        break

        if is_same:
            print(f"✅ Changelog já está no canal ({updatechannel.id}), nenhuma mensagem enviada.")
            return

        # tenta limpar só mensagens do bot (pra não sair deletando coisa dos outros)
        try:
            await updatechannel.purge(limit=200, check=lambda m: m.author == bot.user)
        except Exception as e:
            print(f"⚠️ Não consegui limpar mensagens no canal {updatechannel.id}: {e}")

        for chunk in message_chunks:
            await updatechannel.send(chunk)
        if mention_message:
            await updatechannel.send(mention_message)

        print(f"✅ Changelog atualizado no canal ({updatechannel.id}).")

    for guild in bot.guilds:
        cfg = guild_cfg.get(str(guild.id), {})
        if not isinstance(cfg, dict):
            continue

        ch_id = cfg.get("updates_channel_id")
        if not ch_id:
            continue

        try:
            ch_id = int(ch_id)
        except Exception:
            continue

        updatechannel = bot.get_channel(ch_id)
        if updatechannel is None:
            try:
                updatechannel = await bot.fetch_channel(ch_id)
            except Exception as e:
                print(f"❌ Falha ao buscar canal de updates {ch_id} no guild {guild.name}: {e}")
                continue

        role_id = cfg.get("updates_role_id")
        mention_message = None
        if role_id:
            try:
                mention_message = f"<@&{int(role_id)}>"
            except Exception:
                mention_message = None

        # posta
        try:
            await post_changelog(updatechannel, mention_message)
        except Exception as e:
            print(f"❌ Erro ao postar changelog no guild {guild.name}: {e}")

    # Configura a presença do bot
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="Franciele tem robô agr? oloko",
        details="Tenso",
        large_image="punish",
        large_text="Moderando",
        small_image="punish",
        small_text="Feito por Luky",
    )
    await bot.change_presence(activity=activity)


# Reações pré-definidas
REACTIONS = {
    "bem-vindo": ["👋", "🎉"],
    "importante": ["⚠️", "📢"],
    "parabéns": ["🥳", "🎊"],
    "obrigado": ["🙏"],
}
# Prefixos que ativam o bot
TRIGGERS = [
    "ei bot,", "ei bot, ",
    "ei franbot,", "ei franbot, "
]
# Carregar respostas automáticas
with open("./assets/resources/respostasia.json", "r", encoding="utf-8") as f:
    AUTO_RESPONSES = json.load(f)
async def on_message_custom(bot, message):
    if message.author.bot:
        return  # Ignora mensagens de bots

    conteudo = message.content.lower().strip()

    # --- Verifica se começa com algum prefixo ---
    prefixo_usado = None
    for trigger in TRIGGERS:
        if conteudo.startswith(trigger):
            prefixo_usado = trigger
            break

    if prefixo_usado:
        # Remove o prefixo da mensagem
        pergunta = message.content[len(prefixo_usado):].strip()

        # Procura no JSON
        if pergunta in AUTO_RESPONSES:
            resposta = AUTO_RESPONSES[pergunta]

            # Calcula tempo de espera: 160ms * nº de caracteres
            delay = len(resposta) * 0.160

            async with message.channel.typing():
                await asyncio.sleep(delay)
                await safe_request(message.channel.send, resposta)
            return

    # Reações pré-definidas
    for keyword, emojis in REACTIONS.items():
        if keyword in message.content.lower():
            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except discord.Forbidden:
                    print(
                        f"❌ Não tenho permissão para reagir a mensagens em {message.channel}"
                    )

    # Detecta expressões de rolagem no formato "$..."
    matches = re.findall(r"\$(\d*#?\d*d\d+[\+\-\*/\(\)\d]*)", message.content)
    if matches:
        resultados = []
        for m in matches:
            res = await asyncio.to_thread(rolar_dado, m, True)
            resultados.append(
                f"``{res['resultado']}`` ⟵ {res['resultadoWOutEval']} {res.get('dice_group', m)}"
            )
        await message.channel.send("\n".join(resultados))

    # Respostas sarcásticas
    if len(message.content) > 300 and not is_spam(message.content):
        await asyncio.sleep(2)
        async with message.channel.typing():
            await asyncio.sleep(3)
            await safe_request(message.channel.send, random.choice(SARCASM_RESPONSES))

    # Palavra do dia
    mensagem_normalizada = unidecode.unidecode(message.content.lower())
    palavra_normalizada = unidecode.unidecode(palavra_do_dia.lower())
    if palavra_normalizada in mensagem_normalizada:
        await message.channel.send(
            f"{palavra_do_dia.upper()} DETECTADA! INICIANDO PROTOCOLO DE SEGURANÇA!"
        )
        await castigar_automatico(message.author, 60)

    await bot.process_commands(message)
