import asyncio
import discord
import unidecode
import json

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

    # Atualiza o canal com o changelog
    updatechannel = bot.get_channel(1319356880627171448)
    mention_message = "<@&1319355628195549247>"
    full_message = f"{conteudo}"
    message_chunks = [
        full_message[i : i + 2000] for i in range(0, len(full_message), 2000)
    ]

    # Pega todas as mensagens do canal, mais antigas primeiro
    existing_messages = []
    async for msg in updatechannel.history(oldest_first=True):
        existing_messages.append(msg)

    # Compara o conteúdo atual com as mensagens existentes
    is_same = (
        len(existing_messages) == len(message_chunks) + 1
        and all(
            existing_messages[i].content.strip() == message_chunks[i].strip()
            for i in range(len(message_chunks))
        )
        and existing_messages[-1].content.strip() == mention_message.strip()
    )

    if is_same:
        print("✅ Changelog já está no canal, nenhuma mensagem enviada.")
    else:
        await updatechannel.purge()
        for chunk in message_chunks:
            await updatechannel.send(chunk)
        await updatechannel.send(mention_message)
        print("✅ Changelog atualizado no canal.")

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
