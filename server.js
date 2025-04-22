const express = require('express');
const ytdl = require('ytdl-core');
const ytSearch = require('yt-search');
const fs = require('fs');
const path = require('path');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

// Serve a pasta de downloads via URL
const downloadsDir = path.join(__dirname, 'downloads');
app.use('/downloads', express.static(downloadsDir));

// Configurações do ytdl
const YTDL_OPTIONS = {
  filter: 'audioonly',
  quality: 'highestaudio',
  format: 'mp3',
  requestOptions: {
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      Accept: '*/*',
      'Accept-Encoding': 'gzip, deflate, br',
      'Accept-Language': 'en-US,en;q=0.9',
      Origin: 'https://www.youtube.com',
      Referer: 'https://www.youtube.com/',
    },
  },
};

// Função para limpar diretório de downloads antigos
function cleanupDownloads() {
  const downloadsDir = path.join(__dirname, 'downloads');
  if (!fs.existsSync(downloadsDir)) return;

  const files = fs.readdirSync(downloadsDir);
  const now = Date.now();
  const MAX_AGE = 24 * 60 * 60 * 1000; // 24 horas

  files.forEach((file) => {
    const filePath = path.join(downloadsDir, file);
    const stats = fs.statSync(filePath);
    if (now - stats.mtimeMs > MAX_AGE) {
      try {
        fs.unlinkSync(filePath);
        console.log(`Arquivo antigo removido: ${file}`);
      } catch (err) {
        console.error(`Erro ao remover arquivo antigo ${file}:`, err);
      }
    }
  });
}

// Limpa downloads antigos a cada hora
setInterval(cleanupDownloads, 60 * 60 * 1000);

app.post('/youtube/search', async (req, res) => {
  const { query } = req.body;

  if (!query) {
    return res.status(400).json({ error: 'Query é obrigatória' });
  }

  let videoInfo;
  try {
    if (ytdl.validateURL(query)) {
      const cleanUrl = query.split('&')[0];
      try {
        videoInfo = await ytdl.getInfo(cleanUrl); // Substituído por getInfo
      } catch (err) {
        console.warn(
          'getInfo falhou, tentando buscar via yt-search:',
          err.message
        );
        const results = await ytSearch(query);
        if (!results.videos.length) throw err;
        videoInfo = await ytdl.getInfo(results.videos[0].url); // Substituído por getInfo
      }
    } else {
      const results = await ytSearch(query);
      if (!results.videos.length) {
        return res.status(404).json({ error: 'Nenhum vídeo encontrado' });
      }
      videoInfo = await ytdl.getInfo(results.videos[0].url); // Substituído por getInfo
    }
  } catch (err) {
    console.error('Erro ao obter informações do vídeo:', err);
    return res.status(500).json({
      error: 'Erro ao obter informações do vídeo',
      details: err.message.includes('Status code:')
        ? err.message
        : err.toString(),
    });
  }

  const videoId = videoInfo.videoDetails.videoId;
  const audioUrl = ytdl.validateURL(query)
    ? query.split('&')[0]
    : videoInfo.videoDetails.video_url;

  // Trata erro de download
  let audioPath;
  try {
    audioPath = await downloadYouTubeAudio(audioUrl, videoId);
  } catch (err) {
    console.error('Erro ao baixar áudio:', err);
    return res
      .status(502)
      .json({ error: 'Erro ao baixar áudio', details: err.message });
  }

  // Se tudo deu certo, retorna o JSON normal
  return res.json({
    type: 'video',
    title: videoInfo.videoDetails.title,
    filePath: audioPath,
    downloadUrl: `http://localhost:${port}/downloads/${videoId}.mp3`,
    duration: videoInfo.videoDetails.lengthSeconds,
    author: videoInfo.videoDetails.author.name,
    url: videoInfo.videoDetails.video_url,
  });
});

async function downloadYouTubeAudio(url, videoId, maxRetries = 3) {
  const downloadsDir = path.join(__dirname, 'downloads');
  const outputPath = path.join(downloadsDir, `${videoId}.mp3`);

  if (!fs.existsSync(downloadsDir)) {
    fs.mkdirSync(downloadsDir, { recursive: true });
  }

  if (fs.existsSync(outputPath)) {
    try {
      const stats = fs.statSync(outputPath);
      if (stats.size > 0) {
        return outputPath;
      }
      fs.unlinkSync(outputPath);
    } catch {}
  }

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      // Pula getInfo e baixa direto o áudio
      const stream = ytdl(url, {
        filter: 'audioonly',
        quality: 'highestaudio',
        requestOptions: YTDL_OPTIONS.requestOptions,
      });

      await new Promise((resolve, reject) => {
        const writeStream = fs.createWriteStream(outputPath);
        stream.pipe(writeStream);
        stream.on('end', resolve);
        stream.on('error', reject);
      });

      return outputPath;
    } catch (error) {
      console.warn(`Tentativa ${attempt} falhou:`, error.message);
      if (attempt === maxRetries) throw error;
    }
  }
}

app.listen(port, () => {
  console.log(`Servidor Node.js rodando na porta ${port}`);
  cleanupDownloads(); // Limpa downloads antigos ao iniciar
});
