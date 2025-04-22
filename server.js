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

// Função para baixar o áudio do YouTube com retry
async function downloadYouTubeAudio(url, videoId, maxRetries = 3) {
    const outputPath = path.join(__dirname, 'downloads', `${videoId}.mp3`);
    
    // Cria o diretório se não existir
    if (!fs.existsSync(path.join(__dirname, 'downloads'))) {
        fs.mkdirSync(path.join(__dirname, 'downloads'));
    }

    // Se o arquivo já existe, retorna o caminho
    if (fs.existsSync(outputPath)) {
        return outputPath;
    }

    const ytdlOptions = {
        filter: 'audioonly',
        quality: 'highestaudio',
        requestOptions: {
            headers: {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'en-US,en;q=0.9',
                'origin': 'https://www.youtube.com',
                'referer': 'https://www.youtube.com/'
            }
        }
    };

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const stream = ytdl(url, ytdlOptions);
            
            await new Promise((resolve, reject) => {
                const writeStream = fs.createWriteStream(outputPath);
                
                stream.pipe(writeStream);

                stream.on('error', (error) => {
                    console.error(`Tentativa ${attempt}: Erro no stream:`, error);
                    writeStream.end();
                    reject(error);
                });

                writeStream.on('error', (error) => {
                    console.error(`Tentativa ${attempt}: Erro na escrita:`, error);
                    reject(error);
                });

                writeStream.on('finish', () => {
                    console.log(`Download concluído: ${outputPath}`);
                    resolve();
                });
            });

            return outputPath;
        } catch (error) {
            console.error(`Tentativa ${attempt} falhou:`, error);
            
            // Se for a última tentativa, lança o erro
            if (attempt === maxRetries) {
                throw error;
            }
            
            // Espera um pouco antes de tentar novamente
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
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
            videoUrl = query.split('&')[0]; // Remove parâmetros extras

            let info = await ytdl.getBasicInfo(videoUrl);
            const videoId = info.videoDetails.videoId;
            
            // Baixa o áudio
            const audioPath = await downloadYouTubeAudio(videoUrl, videoId);

            return res.json({
                type: 'video',
                title: info.videoDetails.title,
                filePath: audioPath, // Retorna o caminho do arquivo baixado
                duration: info.videoDetails.lengthSeconds,
                author: info.videoDetails.author.name
            });
        }

        // Caso seja busca
        const searchResults = await ytSearch(query);
        if (!searchResults.videos.length) {
            return res.status(404).json({ error: 'Nenhum vídeo encontrado.' });
        }

        const firstVideo = searchResults.videos[0];
        const audioPath = await downloadYouTubeAudio(firstVideo.url, firstVideo.videoId);

        return res.json({
            type: 'video',
            title: firstVideo.title,
            filePath: audioPath, // Retorna o caminho do arquivo baixado
            duration: firstVideo.duration.seconds,
            author: firstVideo.author.name
        });

    } catch (error) {
        console.error('Erro ao processar vídeo:', error);
        res.status(500).json({ 
            error: 'Erro ao processar vídeo.', 
            details: error.message 
        });
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