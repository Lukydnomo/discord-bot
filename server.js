const express = require('express');
const ytdl = require('ytdl-core');
const ytSearch = require('yt-search');
const fs = require('fs');
const path = require('path');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

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

async function downloadYouTubeAudio(url, videoId, maxRetries = 3) {
  const downloadsDir = path.join(__dirname, 'downloads');
  const outputPath = path.join(downloadsDir, `${videoId}.mp3`);

  // Cria o diretório se não existir
  if (!fs.existsSync(downloadsDir)) {
    fs.mkdirSync(downloadsDir, { recursive: true });
  }

  // Verifica se arquivo já existe e é válido
  if (fs.existsSync(outputPath)) {
    try {
      const stats = fs.statSync(outputPath);
      if (stats.size > 0) {
        return outputPath;
      }
      // Se arquivo existe mas está vazio, remove para baixar novamente
      fs.unlinkSync(outputPath);
    } catch (err) {
      console.error('Erro ao verificar arquivo existente:', err);
    }
  }

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const info = await ytdl.getInfo(url);
      const format = ytdl.chooseFormat(info.formats, {
        quality: 'highestaudio',
        filter: 'audioonly',
      });

      const stream = ytdl(url, { ...YTDL_OPTIONS, format });

      await new Promise((resolve, reject) => {
        const writeStream = fs.createWriteStream(outputPath);
        let dataReceived = false;

        stream.pipe(writeStream);

        stream.on('data', () => {
          dataReceived = true;
        });

        stream.on('error', (error) => {
          writeStream.end();
          if (!dataReceived) {
            reject(new Error(`Erro no download: ${error.message}`));
          } else {
            console.warn(`Aviso: Erro no stream após receber dados:`, error);
            resolve();
          }
        });

        writeStream.on('error', (error) => {
          reject(new Error(`Erro na escrita: ${error.message}`));
        });

        writeStream.on('finish', () => {
          if (dataReceived) {
            resolve();
          } else {
            reject(new Error('Stream finalizado sem dados'));
          }
        });
      });

      // Verifica se o arquivo foi baixado corretamente
      const stats = fs.statSync(outputPath);
      if (stats.size === 0) {
        throw new Error('Arquivo baixado está vazio');
      }

      return outputPath;
    } catch (error) {
      console.error(`Tentativa ${attempt}/${maxRetries} falhou:`, error);

      // Remove arquivo corrompido se existir
      if (fs.existsSync(outputPath)) {
        try {
          fs.unlinkSync(outputPath);
        } catch (err) {
          console.error('Erro ao remover arquivo corrompido:', err);
        }
      }

      if (attempt === maxRetries) {
        throw new Error(
          `Falha após ${maxRetries} tentativas: ${error.message}`
        );
      }

      // Espera antes de tentar novamente (exponential backoff)
      await new Promise((resolve) =>
        setTimeout(resolve, Math.pow(2, attempt) * 1000)
      );
    }
  }
}

app.post('/youtube/search', async (req, res) => {
  const { query } = req.body;

  if (!query) {
    return res.status(400).json({ error: 'Query é obrigatória' });
  }

  try {
    let videoUrl = query;
    let videoInfo;

    if (ytdl.validateURL(query)) {
      const cleanUrl = query.split('&')[0];
      videoInfo = await ytdl.getBasicInfo(cleanUrl);
    } else {
      const results = await ytSearch(query);
      if (!results.videos.length) {
        return res.status(404).json({ error: 'Nenhum vídeo encontrado' });
      }
      videoInfo = await ytdl.getBasicInfo(results.videos[0].url);
    }

    const videoId = videoInfo.videoDetails.videoId;
    const audioPath = await downloadYouTubeAudio(videoUrl, videoId);

    res.json({
      type: 'video',
      title: videoInfo.videoDetails.title,
      filePath: audioPath,
      duration: videoInfo.videoDetails.lengthSeconds,
      author: videoInfo.videoDetails.author.name,
      url: videoInfo.videoDetails.video_url,
    });
  } catch (error) {
    console.error('Erro ao processar vídeo:', error);
    res.status(500).json({
      error: 'Erro ao processar vídeo',
      details: error.message,
    });
  }
});

app.listen(port, () => {
  console.log(`Servidor Node.js rodando na porta ${port}`);
  cleanupDownloads(); // Limpa downloads antigos ao iniciar
});
