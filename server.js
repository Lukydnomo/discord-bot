const express = require('express');
const ytdl = require('ytdl-core');
const ytSearch = require('yt-search'); // Biblioteca para buscar vídeos no YouTube
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

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
        // Se for um link, valida e retorna informações
        if (ytdl.validateURL(query)) {
            const info = await ytdl.getInfo(query);
            return res.json({
                type: 'video',
                title: info.videoDetails.title,
                url: info.videoDetails.video_url,
                duration: info.videoDetails.lengthSeconds,
                author: info.videoDetails.author.name,
            });
        }

        // Caso contrário, busca no YouTube
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
                duration: video.duration.seconds,
                author: video.author.name,
            })),
        });
    } catch (error) {
        res.status(500).json({ error: 'Erro ao buscar vídeos no YouTube.' });
    }
});

// Inicia o servidor
app.listen(port, () => {
    console.log(`Servidor Node.js rodando na porta ${port}`);
});