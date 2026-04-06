# Changelog

## [1.0.0] - 2024-12-13

### Added

- Comando para avisar os jogadores que a sessão iniciou

### Testando

- Testando a funcionalidade para enviar as atualizações do bot automaticamente

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.0v2] - 2024-12-13

### Fixed

- Bot marcando usuário inexistente nos updates
- Pouco espaço pra marcação do cargo

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.0v3] - 2024-12-19

### Fixed

- Arquivo inteiro de changelog sendo enviado (esqueci q agr é o bot q faz meu trabalho sujo)

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.0v4] - 2024-12-19

### Fixed

- Changelog sendo enviada de forma errada

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.1] - 2024-12-19

### Changed

- Foi mudado como o aviso que a sessão iria iniciar era interpretado. Agora ele escolhe uma entre 30 opções para manter a fluidez da funcionalidade

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.1v2] - 2024-12-19

### Fixed

- Ajustes no código

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.1v3] - 2024-12-19

### Fixed

- JSON sendo bugado como sempre

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.2] - 2024-12-19

### Changed

- (Admin Only) Foi mudado a dinâmica de como funciona o comando de iniciar e terminar sessão, fundindo a mecânica de abri e fechar a sessão em um unico comando

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.2v2] - 2024-12-19

### Fixed

- (Admin Only) /togglesession agora funciona corretamente (esqueci da porra de uma variável)

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.3] - 2024-12-19

### Added

- Compatibilidade com a mesa "Desordem"

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.0.3v2] - 2024-12-19

### Fixed

- (Admins Only) Opção "Desordem" não estava aparecendo

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.1.0] - 2025-03-05

### Added (only authorized users)

- "/executar_comando"

### Added (moderation only)

- "/mutar"
- "/desmutar"
- "/mover"

### Removed

- "/togglesessao"

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.1.1] - 2025-03-05

### Added

- Tocador de Músicas

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.1.2] - 2025-03-06

### Added

- Jokenpô (jogo de pedra, papel e tesoura)

### Removed

- Tocador de músicas (tava foda pra fazer funcionar)

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.2.0] - 2025-03-07

### Added

- Função para rodar dados

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.3.0] - 2025-03-24

🔥 **El big update '0'** 🔥

### 🆕 Adicionado

✅ **Comandos de Moderação:**

- **`/mutar`** _(Admin only)_ – Muta todos os membros de um canal de voz, um usuário ou um cargo específico.
- **`/desmutar`** _(Admin only)_ – Desmuta todos os membros de um canal de voz ou apenas um usuário/cargo específico.
- **`/mover`** _(Admin only)_ – Move todos os membros de um canal de voz para outro.

🎵 **Comandos de Áudio:**

- **`/tocar [arquivo]`** – Toca um áudio do repositório no canal de FFFFFvoz.
- **`/fila`** – Exibe a fila de reprodução de áudios.
- **`/pular`** – Pula para o próximo áudio na fila.
- **`/parar`** – Para a reprodução e limpa a fila.

### ❌ Removido

- **`/executar_comando`** – Comando genérico de execução de código foi descontinuado.

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.4.1] - 2025-03-28

🔥 **A atualização do caos chegou!** 🔥

### 🆕 Adicionado

🎲 **Comandos de Diversão:**

- **`/roleta`** – Escolhe uma opção aleatória dentre as fornecidas.
- **Sistema de palavra proibida** – Todo dia, uma palavra aleatória da língua portuguesa será escolhida. Se alguém digitá-la, receberá um castigo de **1 minuto** _(duração sujeita a mudanças)_.
- **`/pdd`** _(Admin only)_ – Exibe a palavra proibida do dia.

🏀 **Notificações Esportivas:**

- **Aviso automático de jogo do Botafogo** – Especialmente para a Bilau, já que ela tem **fogo no rabito**. 🔥

### ❌ Removido

- **Suporte a comandos prefixados** (`!comando`, `foa!comando`) – Agora é só na base do slash.

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.5.0] - 2025-04-03

🎧 **Update da playlist noggers** 🎧

### 🆕 Adicionado

🎵 **Comandos de Áudio:**

- **`/shippar`** – Mede a compatibilidade entre dois nomes. 💘
- **`/loop`** – Define o modo de repetição: sem loop, música atual ou fila inteira. 🔁
- **`/shuffle`** – Embaralha a ordem da fila de áudios! 🔀

### ⚙️ Alterado

- Agora é possível adicionar **várias músicas de uma vez** no `/tocar` separando com vírgula e espaço.
  > Exemplo: `/tocar music:disturbio, orquestra, convulsao`
- Melhorias internas de performance no código (dicionários e afins 🧠💨).

### ❌ Removido

- **Aviso automático de jogo do Botafogo** – A API era ineficiente e custava **R$300 por mês**, o que não justificava o uso.

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.6.0] - 2025-04-07

✨ **O bot tá cada vez mais poliglota e frito!** ✨

### 🆕 Adicionado

🌐 **Comandos de Tradução:**

- **`/hypertranslate`** – Traduz um texto passando por várias línguas aleatórias e retorna o resultado final.

🍟 **Comandos de Imagem:**

- **`/deepfry`** – Aplica o famoso efeito "deep fry" em uma imagem.

### 📝 Observação

- O bot está aberto a cada vez mais possibilidades graças aos novos conhecimentos do dev mais lindo do mundo/meu criador, Luky! Ele continua estudando Python e melhorando o código constantemente, mas ainda luta para ter ideias de novas funções. Sugestões são muito bem-vindas para deixar o bot cada vez mais completo.

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.7.0] - 2025-04-17

**Minor Update**

### 🆕 Adicionado

- **`/lapide`** - Gera uma imagem com uma frase/palavra em especifico em uma lápide.

### ⚙️ Alterado

- Foi reorganizado algumas coisinhas no código para deixá-lo mais leve

### 📝 Observação

- Luky não está trabalhando muito no bot por um motivo bem simples, os seus estudos em python estão sendo aperfeiçoados justamente pra por em prática no bot, e isso vai ajudar a melhorar a performance do bot com o tempo.

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.7.1] - 2025-04-21

**Another Minor Update**

### 🆕 Adicionado

- **`/ascii`** - Gera uma arte ASCII personalizada podendo escolher dentre algumas fontes.

### 📝 Observação

- O código está mais organizado e otimizado do que nunca, com uma base sólida para futuras melhorias. Além disso, mudanças no ambiente de desenvolvimento do criador prometem acelerar a produção de atualizações, possibilitando um ritmo mais constante de novidades.

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.7.1v2] - 2025-04-21

**Atualização rápida para otimizar o bot e resolver problemas que estavam causando desafios significativos para o desenvolvedor.**

## ⚙️ Alterado

- Foi decidido focar na otimização do bot devido à demora na inicialização.
- As funções foram separadas em arquivos distintos.
- Os arquivos foram reorganizados para melhorar a leitura e o funcionamento.

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.7.1v3] - 2025-04-21

**Refatoração e Otimização Avançada**

## ⚙️ Alterado

- Continuando o trabalho de otimização iniciado na última atualização, o código foi ainda mais refinado, resultando em uma redução significativa no número de linhas (de quase 1300 para 918). Isso melhora a legibilidade, organização e desempenho geral do bot.

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.8.0] - 2025-04-25

**SUPER OPTIMIZATION UPDATE**

## ⚙️ Alterações Técnicas

- **`Refatoração massiva de código`** - O main.py foi desmontado em módulos menores e reorganizado — antes com mais de 400 linhas, agora concentra só a inicialização e o carregamento de Cogs, deixando o fluxo muito mais limpo e fácil de entender.

- **`Adoção do sistema de Cogs`** - Cada grupo de comandos (moderação, música, diversão, etc.) foi movido para seu próprio Cog, melhorando a separação de responsabilidades, acelerando o carregamento de extensões e evitando gargalos de performance na inicialização do bot.

- **`Timers de desconexão mais precisos`** - A contagem regressiva de inatividade agora só começa quando realmente não há mais nada na fila de reprodução, e foi reduzida para 60s com asyncio.create_task, garantindo que o bot saia rápido de canais vazios sem disparar desconexões prematuras.

## 📝 Observação

- Cuidem do dev, ele nunca esteve em um estado de cansaço tão grande só pra deixar o nosso bot pessoal bom...

<!-- prettier-ignore -->
- - - - - - - - - -

## [1.9.0] - 2025-08-02

## 📝 Observação

- O dev está com tendências suícidas extremas, tá tudo dando errado nessa porra.

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.0.0] - 2025-08-28

**TALVEZ ATUALIZAREMOS COM CERTA FREQUENCIA**

- **`Adicionado sistema de IA manual ao bot (beta)`** - Foi adicionado um sistema em que o bot detecta se uma pergunta está em uma lista de respostas, bem preguiçoso e mal feito, mas vai ser legal quando a lista estiver longa. Para ativar use o prefixo "Ei bot, "

## 📝 Observação

- Cuidem do dev, ele tá no ponto de recorrer a programar pra se distrair.

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.0.1] - 2025-09-22

**okay, talvez não com tanta frequencia quanto eu gostaria, mas sabe como é né**

- **`Adicionado painel de mute utilzando embed (/mutecall)`** - Basicamente um painel embed que serve pra mutar e desmutar todos presentes na call de forma rápida, mais utilizado para jogar Among Us, Suspects, GGD (se não utilizar o in-game), dentre outros jogos que precisam do silêncio de todos.

## 📝 Observação

- ta

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.0.2] - 2025-09-29

**tão tá né**

## 📝 Observação

- Eu já nem sei como ainda tô aqui. Tudo me cansa, até respirar parece pesado. O que eu ªgostava já não faz maªis senªtido, tá tudo ficando vazio. Qualquer ªhora eªu largo tudo, sumo da internet, sumo do mundo. Viver assim tá me acaªbando, jogo meus problemas pros outros e só me sinto mais exausto, mais sozinho. No fundo já não sinto nada… se eu sumir ou ficar, tanto faz, ninguém vai se importar. Eu não sou nada demais. Talvez esse seja mesmo meu _Destino_. E é isso. Eu só não ligo mais pra nada.

Dito isso, vlw, por tudo. _Eu já não vejo mais nada_.

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.1.0] - 2025-11-15

**atualização foda tá**

## 🆕 Improved

- **`Melhora no player de áudio`** - Umas melhorinhas nas informações de loop. Os comandos `Salvar Fila` e `Carregar Fila` agora estão completamente funcionais.

## ⚙️ Adjustments

- **`Bugs com o comando Sair e Tocar`** - Ocorria certos bugs com estes comandos, fazendo com que eles não funcionassem quando o bot reiniciasse sua instância.

- **`Changelog`** - Havia um bug no código que fazia com que o changelog fosse reenviado no <#1319356880627171448> sem checar se realmente tivesse um update.

## ⚙️ Testing

- **`Compatibilidade com YouTube`** - A nossa equipe está testando a funcionaldiade de tocar vídeos do youtube no player de áudio.

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.2.0] - 2026-02-13

**Random Update**

## Added

- **`/glitch_nickname`** - Novo comando que aplica um efeito de “glitch” no nickname de um ou mais usuários. Ideal para momentos de imersão, eventos narrativos ou só pra causar o caos de leve.
- **`/converter_sanidade_para_pd`** - Converte valores de Sanidade do sistema padrão de Ordem Paranormal para Pontos de Determinação (PD), mantendo coerência com o sistema adaptado.
- **`/calcular_pd`** - Calcula os Pontos de Determinação (PD) levando em consideração a classe do personagem, o NEX, o atributo base, a presença de Potencial Aprimorado, Afinidade com Morte e Cicatrizes Psicológicas. O comando foi implementado para corrigir inconsistências do C.R.I.S., garantindo um cálculo mais preciso e confiável.

## Adjustments

- **`Adicionado o parâmetro 'exceto' para o comando de moderação '/mover', permitindo excluir usuários específicos da movimentação em massa.`**

## Observação

- difícil

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.3.0] - 2026-02-22

**update de utilidades e sistemas que facilitam a vida da mesa**

### 🆕 Adicionado

🎲 **Sistema de Macros**

- Agora é possível salvar rolagens e usar depois com comandos rápidos.
- Permite criar, listar, visualizar e remover macros pessoais ou do servidor.

📚 **Sistema de Referências (`/ref`)**

- Salve termos importantes com fonte, página, notas, tags e sinônimos.
- Ideal pra consultar regras, condições e rituais sem ficar abrindo PDF.

🔇 **Painel de mute para call (`/mutecall`)**

- Embed com botões para mutar ou desmutar todos da call rapidamente.
- Perfeito para jogos que exigem silêncio.

🎮 **Organização dos comandos de diversão**

- Comandos como **jokenpô**, **roleta**, **piadas**, **missões**, **ASCII**, **lápide**, **deepfry** e outros foram reunidos e melhor organizados.

🧩 **Melhorias em painéis interativos**

- Botões de alguns sistemas agora continuam funcionando mesmo após reinicializações do bot.

### ⚙️ Alterado

- Ajustes no balanceamento da conversão de **Sanidade → PD** para resultados mais consistentes.
- Sistema de referências ficou mais inteligente ao buscar termos (menos erro com variações e acentos).
- Melhorias gerais na organização dos comandos para deixar o bot mais fácil de usar.

### 🛠️ Correções

- Correções em salvamento de dados que podiam causar perda de informações em raros casos.
- Ajustes em sistemas interativos que às vezes paravam de responder após atualizações.
- Pequenas correções de inconsistências em comandos de rolagem e utilidades.

### 📝 Observação

- madrugada foi foda guys

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.3.1] - 2026-02-22

**update do Wordle e mudanças no player de música**

### 🆕 Adicionado

- Novo minigame **Wordle**: adivinhe a palavra do dia e receba feedback por letras (posição correta, letra existente ou inexistente).
- O número de tentativas agora se ajusta automaticamente ao tamanho da palavra.
- Adicionado **ranking semanal do Wordle** dentro do servidor.

### ⚙️ Alterado

- O player de música agora aceita apenas **áudios locais**.
- Links do YouTube não são mais suportados.

### 🛠️ Correções

- Melhorias no sistema de reprodução para tornar a fila mais estável e reduzir erros ao tocar arquivos.

### 📝 Observação

- Se você utilizava YouTube para tocar músicas, agora é necessário baixar o áudio e mandar pro adm.

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.3.2] - 2026-02-22

**update de configurações por servidor e personalização do bot**

### 🆕 Adicionado

⚙️ **Sistema de Configuração do Servidor (`/config`)**

- Agora é possível definir onde o bot posta **updates/changelog** e qual cargo será pingado.
- Configuração do **Hexatombê** (canal do painel, canal de envio e pessoa para ping).
- Ajustes de música por servidor: **auto-disconnect** e **qualidade do áudio (bitrate)**.
- Novo comando para visualizar as configurações atuais do servidor.

🛠️ **Configurações globais do bot (`/botconfig`)**

- Donos/autorizados podem definir limites do sistema de rolagem e canal global de logs.

### ⚙️ Alterado

- O player de música agora respeita as configurações de cada servidor (tempo para sair da call e qualidade do áudio).
- Painéis interativos (como Hexatombê) passaram a funcionar com configurações próprias de cada servidor.
- O envio de changelog/updates ficou configurável e mais inteligente (evita repost desnecessário).
- Prefixo do bot passou a ser configurável.

### 🛠️ Correções

- Melhorias na estabilidade de sistemas que antes dependiam de IDs fixos.
- Limpeza de comportamentos antigos que podiam causar inconsistências em call ou painéis.

### 🗑️ Removido

- Sistema antigo de eventos de voz automáticos.
- Áudio especial associado a esse sistema.

### 📝 Observação

- O bot agora foi preparado para funcionar de forma diferente em cada servidor, abrindo espaço para futuras features personalizáveis.

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.4.0] - 2026-02-24

**grande update do player de música e kk coisinhas**

### 🆕 Adicionado

🎧 **Painel de Música interativo**

- Embed fixo com botões para **pausar, pular, parar, loop, embaralhar e ver fila**.
- O painel se atualiza automaticamente conforme a música muda.
- Novo comando para criar/mover o painel no servidor.

💾 **Estado da música persistente**

- A fila, modo de loop e contexto da call agora podem ser restaurados após reinicializações do bot.
- O bot tenta reconectar e continuar a reprodução quando possível.

👤 **Identificação de quem pediu a música**

- Faixas agora guardam quem solicitou, preparando recursos sociais futuros.

### ⚙️ Alterado

- Sistema de fila refeito para suportar painel, persistência e controle por botões.
- O player agora pausa automaticamente quando não há ouvintes e volta quando alguém retorna.
- Configuração do painel de música passou a fazer parte das configurações do servidor.
- Comandos de configuração foram simplificados e centralizados em `/config`.
- Permissões de configuração ficaram mais claras (baseadas em administrador).

### 🛠️ Correções

- Correções em sincronização de configurações após reinicializações.
- Melhor tratamento de erros em sistemas interativos como Hexatombe.
- Ajustes na leitura de configurações para evitar dados desatualizados.

### 🧹 Ajustes

- Padronização de nomes e mensagens (ex.: Hexatombe).
- Melhor organização interna de logs e limites do sistema de rolagem.

### 📝 Observação

- Este update prepara o player para recursos mais avançados (ex.: votação de skip, estatísticas, sessões de música e automações).

<!-- prettier-ignore -->
- - - - - - - - - -

## [2.4.2] - 2026-04-06

**novos cálculos automáticos para personagens**

### 🆕 Adicionado

📊 **Cálculo de Pontos de Esforço (PE)**

- Novo comando `/calcular_pe`
- Considera classe, NEX, atributo e modificadores como potencial aprimorado e afinidade.

🧠 **Cálculo de Sanidade (SAN)**

- Novo comando `/calcular_san`
- Inclui variações por classe e bônus como cicatrizes psicológicas.

❤️ **Cálculo de Pontos de Vida (PV)**

- Novo comando `/calcular_pv`
- Leva em conta classe, atributos e habilidades como sangue de ferro, calejado e vitalidade sofrida.

### ⚙️ Como usar

- Todos os cálculos são feitos automaticamente via comando.
- Basta preencher os campos e o bot retorna o valor final.

### 📝 Observação

- Os cálculos seguem as regras do sistema e já consideram bônus e variações comuns automaticamente.

<!-- prettier-ignore -->
- - - - - - - - - -
