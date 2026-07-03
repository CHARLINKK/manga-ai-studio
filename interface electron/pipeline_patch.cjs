
// ── Pipeline de IA ──────────────────────────────────────────────────────────
let activePipelineProcess = null;
let pipelinePaused = false;
let pipelineResumeCallback = null;

const sendLog = (event, msg, progress = null, isError = false) => {
  event.sender.send('pipeline-log', { text: msg, progress, isError });
};

ipcMain.handle('cancel-pipeline', () => {
  if (activePipelineProcess) {
    const { exec } = require('child_process');
    exec('taskkill /pid ' + activePipelineProcess.pid + ' /T /F');
    activePipelineProcess = null;
    return true;
  }
  return false;
});

ipcMain.handle('resume-pipeline', () => {
  if (pipelinePaused && pipelineResumeCallback) {
    pipelinePaused = false;
    pipelineResumeCallback();
    pipelineResumeCallback = null;
    return true;
  }
  return false;
});

ipcMain.handle('run-pipeline', async (event, config) => {
  const { spawn } = require('child_process');
  const projectRoot = path.join(__dirname, '..');
  const pythonExeOcr = path.join(projectRoot, 'venv_ocr', 'Scripts', 'python.exe');
  const pythonExeUi = path.join(projectRoot, 'venv_ui', 'Scripts', 'python.exe');
  
  // Dicionários Globais e Locais
  const configDir = path.join(os.homedir(), 'AppData', 'Local', 'MangaAIStudio');
  if (!fs.existsSync(configDir)) fs.mkdirSync(configDir, { recursive: true });
  const globalDictPath = path.join(configDir, 'dicionario_global.txt');
  const localDictPath = path.join(configDir, 'temp_dict_local.txt');
  
  fs.writeFileSync(globalDictPath, config.dictGlobal || '', 'utf8');
  fs.writeFileSync(localDictPath, config.dictLocal || '', 'utf8');

  // Determinar base name e destino
  const inputPath = config.inputPath;
  const pInput = path.parse(inputPath);
  let baseName = pInput.name;
  if (!fs.statSync(inputPath).isDirectory() && pInput.ext.toLowerCase() !== '.txt') {
    baseName = path.basename(path.dirname(inputPath));
  } else {
    baseName = baseName.replace('_raw', '').replace('_corrigido', '').replace('_traduzido', '');
  }

  const bibliotecaDir = path.join(os.homedir(), 'Documents', 'Manga AI Studio', 'Biblioteca');
  const tempDir = path.join(bibliotecaDir, 'Temp');
  if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });

  let currentTarget = inputPath;
  
  const runScript = (exe, scriptName, args) => {
    return new Promise((resolve, reject) => {
      activePipelineProcess = spawn(exe, [scriptName, ...args], { cwd: projectRoot, windowsHide: true });
      
      activePipelineProcess.stdout.on('data', (data) => {
        const str = data.toString('utf8');
        const clean = str.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, '');
        // Tentar extrair progresso
        const match = clean.match(/(\d+)%/);
        let prog = null;
        if (match) prog = parseInt(match[1], 10);
        sendLog(event, clean, prog);
      });
      activePipelineProcess.stderr.on('data', (data) => {
        const str = data.toString('utf8');
        sendLog(event, str.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, ''));
      });
      activePipelineProcess.on('close', (code) => {
        activePipelineProcess = null;
        if (code === 0) resolve();
        else reject(new Error(scriptName + ' exited with code ' + code));
      });
      activePipelineProcess.on('error', (err) => {
        activePipelineProcess = null;
        reject(err);
      });
    });
  };

  try {
    sendLog(event, '==================================================', 5);
    sendLog(event, ' INICIANDO PIPELINE: ' + path.basename(inputPath));
    sendLog(event, '==================================================');

    // ETAPA 1: OCR
    if (config.steps.ocr) {
      sendLog(event, '\n>>> ETAPA 1: EXTRAÇÃO DE TEXTO BRUTO (GPU)', 10);
      let expectedTxtPath = path.join(tempDir, baseName + '_raw.txt');
      let args = [inputPath, '--output', expectedTxtPath];
      args.push('--gpu');
      
      await runScript(pythonExeOcr, 'manga_ocr.py', args);
      currentTarget = expectedTxtPath;
      
      if (config.steps.pauseOcr) {
        sendLog(event, '\n PAUSA MANUAL ATIVADA. Alternando para o Editor Visual...', 30);
        // We will pause here
        await new Promise((resolve) => {
          pipelinePaused = true;
          pipelineResumeCallback = resolve;
          // Notify UI to open studio
          event.sender.send('pipeline-paused', { inputPath, targetPath: currentTarget });
        });
        sendLog(event, '\n RETOMANDO PIPELINE...', 35);
      }
    } else {
      let expectedTxtPath = path.join(tempDir, baseName + '_raw.txt');
      if (fs.existsSync(expectedTxtPath)) currentTarget = expectedTxtPath;
    }

    // ETAPA 2: Correção
    if (config.steps.correct) {
      sendLog(event, '\n>>> ETAPA 2: POLIMENTO DE INGLÊS (IA)', 40);
      let args = [currentTarget, '--dict-global', globalDictPath, '--dict-local', localDictPath, '--output', tempDir, '--model', config.models.corr];
      await runScript(pythonExeUi, 'ocr_corrector.py', args);
      let corrStem = path.basename(currentTarget, path.extname(currentTarget)).replace('_raw', '');
      currentTarget = path.join(tempDir, corrStem + '_corrigido.txt');
    }

    // ETAPA 3: Tradução
    if (config.steps.translate) {
      sendLog(event, '\n>>> ETAPA 3: TRADUÇÃO PT-BR (IA)', 70);
      let args = [currentTarget, '--dict-global', globalDictPath, '--dict-local', localDictPath, '--output', tempDir, '--model', config.models.trans];
      if (config.tone) args.push('--tone', config.tone);
      if (config.steps.exportBilingual) args.push('--bilingual');
      await runScript(pythonExeUi, 'manga_translator.py', args);
      let transStem = path.basename(currentTarget, path.extname(currentTarget)).replace('_corrigido', '').replace('_raw', '');
      currentTarget = path.join(tempDir, transStem + '_traduzido.txt');
    }

    sendLog(event, '\n[!] PROCESSAMENTO FINALIZADO.', 100);
    
    if (config.steps.openStudio) {
      event.sender.send('pipeline-finished', { inputPath, targetPath: currentTarget });
    }

    return { success: true, finalTarget: currentTarget };

  } catch (err) {
    sendLog(event, '\n[!] ERRO: ' + err.message, null, true);
    return { success: false, error: err.message };
  }
});
