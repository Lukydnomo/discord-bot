const express = require('express');
const ytdl = require('ytdl-core');
const ytSearch = require('yt-search'); // Biblioteca para buscar vídeos no YouTube
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

// Função para limpar a URL removendo parâmetros extras
function cleanUrl(url) {
    const urlObject = new URL(url);
    urlObject.search = ''; // Remove todos os parâmetros
    return urlObject.toString();
}

// Função para extrair o ID do vídeo da URL
function getVideoId(url) {
    const urlObject = new URL(url);
    const videoId = urlObject.searchParams.get('v');
    return videoId;
}

// Endpoint para obter informações de um vídeo do YouTube
app.post('/youtube/info', async (req, res) => {
    const { url } = req.body;

    if (!ytdl.validateURL(url)) {
        return res.status(400).json({ error: 'URL inválida do YouTube.' });
    }

    try {
        const info = await ytdl.getInfo(url);
        res.json({
            title: info.videoDetails.title,
            lengthSeconds: info.videoDetails.lengthSeconds,
            author: info.videoDetails.author.name,
        });
    } catch (error) {
        res.status(500).json({ error: 'Erro ao obter informações do vídeo.' });
    }
});

// Endpoint para buscar vídeos ou playlists no YouTube
app.post('/youtube/search', async (req, res) => {
    const { query } = req.body;

    if (!query) {
        return res.status(400).json({ error: 'A consulta (query) é obrigatória.' });
    }

    try {
        let videoUrl = query;
        if (ytdl.validateURL(query)) {
            // Limpa a URL removendo parâmetros extras
            videoUrl = cleanUrl(query);
            console.log(`Processando link do YouTube: ${videoUrl}`);

            // Extrai o ID do vídeo
            const videoId = getVideoId(videoUrl);
            if (!videoId) {
                return res.status(400).json({ error: 'ID do vídeo não encontrado na URL.' });
            }

            // Verifica se o vídeo está disponível
            try {
                await ytdl.getInfo(videoId);
            } catch (error) {
                console.error('Erro ao obter informações do vídeo:', error);
                return res.status(500).json({ error: 'Vídeo não disponível.', details: error.message });
            }

            const info = await ytdl.getInfo(videoId);
            return res.json({
                type: 'video',
                title: info.videoDetails.title,
                url: info.videoDetails.video_url,
                duration: info.videoDetails.lengthSeconds,
                author: info.videoDetails.author.name,
            });
        }

        // Caso contrário, busca no YouTube
        console.log(`Realizando busca no YouTube: ${query}`);
        const searchResults = await ytSearch(query);
        const videos = searchResults.videos.slice(0, 5); // Retorna os 5 primeiros resultados

        if (videos.length === 0) {
            return res.status(404).json({ error: 'Nenhum resultado encontrado.' });
        }

        res.json({
            type: 'search',
            results: videos.map(video => ({
                title: video.title,
                url: video.url,
                duration: video.duration.seconds || 0,
                author: video.author.name,
            })),
        });
    } catch (error) {
        console.error('Erro ao buscar vídeos no YouTube:', error);
        res.status(500).json({ error: 'Erro ao buscar vídeos no YouTube.', details: error.message });
    }
});

// Inicia o servidor
app.listen(port, () => {
    console.log(`Servidor Node.js rodando na porta ${port}`);
});

// Exemplo de uso do endpoint /youtube/search
const requests = require('axios');

async function processarLink(nome, interaction) {
    try {
        const response = await requests.post("http://localhost:3000/youtube/search", { query: nome });
        if (response.status !== 200) {
            await interaction.channel.send(`❌ Erro ao processar o link \`${nome}\`: ${response.statusText}`);
            return;
        }

        const data = response.data;
        if ("error" in data) {
            await interaction.channel.send(`❌ Erro ao processar o link \`${nome}\`: ${data.error}`);
            return;
        }

        // Processar os dados retornados
        console.log(data);
    } catch (error) {
        await interaction.channel.send(`❌ Erro ao processar o link \`${nome}\`: ${error.message}`);
    }
}