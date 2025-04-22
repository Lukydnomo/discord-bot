const express = require('express');
const ytdl = require('ytdl-core');
const ytSearch = require('yt-search');
const fs = require('fs');
const path = require('path');
const app = express();
const port = process.env.PORT || 3000;

// Fila de logs para o Python consumir
const logQueue = [];

// Função para adicionar logs
function addLog(message, type = 'info') {
  const log = {
    timestamp: new Date().toISOString(),
    type: type,
    message: message,
  };
  logQueue.push(log);
  console.log(`[${type.toUpperCase()}] ${message}`); // Mantém o log no console do Node
}

// Novo endpoint para buscar logs
app.get('/logs', (req, res) => {
  const logs = [...logQueue]; // Copia os logs
  logQueue.length = 0; // Limpa a fila
  res.json(logs);
});

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
        addLog(`Arquivo antigo removido: ${file}`, 'info');
      } catch (err) {
        addLog(`Erro ao remover arquivo antigo ${file}: ${err}`, 'error');
      }
    }
  });
}

// Limpa downloads antigos a cada hora
setInterval(cleanupDownloads, 60 * 60 * 1000);

app.post('/youtube/search', async (req, res) => {
  const { query } = req.body;

  if (!query) {
    addLog('Query é obrigatória', 'error');
    return res.status(400).json({ error: 'Query é obrigatória' });
  }

  let videoInfo;
  try {
    if (ytdl.validateURL(query)) {
      const cleanUrl = query.split('&')[0];
      try {
        addLog(`Buscando info do vídeo: ${cleanUrl}`, 'info');
        videoInfo = await ytdl.getInfo(cleanUrl, {
          requestOptions: YTDL_OPTIONS.requestOptions, // Passa os requestOptions aqui
        });
      } catch (err) {
        addLog(
          `getInfo falhou, tentando buscar via yt-search: ${err.message}`,
          'warn'
        );
        const results = await ytSearch(query);
        if (!results.videos.length) throw err;
        videoInfo = await ytdl.getInfo(results.videos[0].url, {
          requestOptions: YTDL_OPTIONS.requestOptions, // Passa os requestOptions aqui também
        });
      }
    } else {
      const results = await ytSearch(query);
      if (!results.videos.length) {
        return res.status(404).json({ error: 'Nenhum vídeo encontrado' });
      }
      videoInfo = await ytdl.getInfo(results.videos[0].url, {
        requestOptions: YTDL_OPTIONS.requestOptions, // Passa os requestOptions aqui também
      });
    }
  } catch (err) {
    addLog(`Erro ao obter informações do vídeo: ${err}`, 'error');
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
    addLog(`Erro ao baixar áudio: ${err}`, 'error');
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
      addLog(`Tentativa ${attempt} falhou: ${error.message}`, 'warn');
      if (attempt === maxRetries) throw error;
    }
  }
}

app.listen(port, () => {
  addLog(`Servidor Node.js rodando na porta ${port}`, 'info');
  cleanupDownloads(); // Limpa downloads antigos ao iniciar
});
