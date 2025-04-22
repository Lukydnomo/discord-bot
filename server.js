const express = require('express');
const ytdl = require('ytdl-core');
const ytSearch = require('yt-search');
const fs = require('fs');
const path = require('path');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

// Função para limpar a URL removendo parâmetros extras
function cleanUrl(url) {
    const urlObject = new URL(url);
    // Captura o valor de 'v'
    const v = urlObject.searchParams.get('v');
    // Remove todos os parâmetros
    urlObject.search = '';
    // Se tiver 'v', insere-o de volta
    if (v) {
        urlObject.search = `?v=${v}`;
    }
    return urlObject.toString();
}

// Função para extrair o ID do vídeo da URL
function getVideoId(url) {
    try {
        const urlObject = new URL(url);
        let videoId = urlObject.searchParams.get('v');

        // Verifica se o ID foi encontrado no parâmetro 'v'
        if (!videoId) {
            // Tenta extrair o ID de outros formatos de URL
            const path = urlObject.pathname.split('/');
            videoId = path[path.length - 1];
        }

        return videoId;
    } catch (error) {
        console.error('Erro ao extrair o ID do vídeo:', error);
        return null;
    }
}

// Função para baixar o áudio do YouTube
async function downloadYouTubeAudio(url, videoId) {
    const outputPath = path.join(__dirname, 'downloads', `${videoId}.mp3`);
    
    // Cria o diretório se não existir
    if (!fs.existsSync(path.join(__dirname, 'downloads'))) {
        fs.mkdirSync(path.join(__dirname, 'downloads'));
    }

    return new Promise((resolve, reject) => {
        ytdl(url, {
            filter: 'audioonly',
            quality: 'highestaudio',
            requestOptions: {
                headers: {
                    cookie: 'CONSENT=YES+1',
                    'x-youtube-client-name': '1',
                    'x-youtube-client-version': '2.20200101'
                }
            }
        })
        .pipe(fs.createWriteStream(outputPath))
        .on('finish', () => resolve(outputPath))
        .on('error', reject);
    });
}

// Endpoint para obter informações de um vídeo do YouTube
app.post('/youtube/info', async (req, res) => {
    const { url } = req.body;

    if (!ytdl.validateURL(url)) {
        return res.status(400).json({ error: 'URL inválida do YouTube.' });
    }

    try {
        const info = await ytdl.getInfo(url);
        const format = ytdl.chooseFormat(info.formats, { 
            quality: 'highestaudio',
            filter: 'audioonly' 
        });

        res.json({
            title: info.videoDetails.title,
            lengthSeconds: info.videoDetails.lengthSeconds,
            author: info.videoDetails.author.name,
            audioUrl: format.url
        });
    } catch (error) {
        console.error('Erro ao obter informações do vídeo:', error);
        res.status(500).json({ error: 'Erro ao obter informações do vídeo.' });
    }
});

// Endpoint para buscar e baixar vídeos do YouTube
app.post('/youtube/search', async (req, res) => {
    const { query } = req.body;

    if (!query) {
        return res.status(400).json({ error: 'A consulta (query) é obrigatória.' });
    }

    try {
        let videoUrl = query;
        if (ytdl.validateURL(query)) {
            const info = await ytdl.getBasicInfo(videoUrl, {
                requestOptions: {
                    headers: {
                        cookie: 'CONSENT=YES+1',
                        'x-youtube-client-name': '1',
                        'x-youtube-client-version': '2.20200101'
                    }
                }
            });
            
            const videoId = info.videoDetails.videoId;
            
            // Baixa o áudio
            const audioPath = await downloadYouTubeAudio(videoUrl, videoId);

            return res.json({
                type: 'video',
                title: info.videoDetails.title,
                filePath: audioPath,
                duration: info.videoDetails.lengthSeconds,
                author: info.videoDetails.author.name
            });
        }

        // Caso seja uma busca
        const searchResults = await ytSearch(query);
        const firstVideo = searchResults.videos[0];
        if (!firstVideo) {
            return res.status(404).json({ error: 'Nenhum vídeo encontrado.' });
        }

        // Baixa o primeiro resultado
        const videoId = firstVideo.videoId;
        const audioPath = await downloadYouTubeAudio(firstVideo.url, videoId);

        return res.json({
            type: 'video',
            title: firstVideo.title,
            filePath: audioPath,
            duration: firstVideo.duration.seconds,
            author: firstVideo.author.name
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