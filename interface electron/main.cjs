const { app, BrowserWindow, ipcMain, dialog, Notification, Tray, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');


const { autoUpdater } = require('electron-updater');

// Configurar logs básicos para o autoUpdater
autoUpdater.logger = require('console');

// 🧪 HACK PARA TESTES LOCAIS DO AUTO-UPDATER 🧪
// Se rodarmos com cross-env LOCAL_TEST=true, ele vai procurar o release num servidor local na porta 8080
if (process.env.LOCAL_TEST === 'true') {
  autoUpdater.setFeedURL({
    provider: 'generic',
    url: 'http://localhost:8080'
  });
  // Força checagem de atualizações mesmo no ambiente dev/não empacotado
  autoUpdater.forceDevUpdateConfig = true;
  
  // Como o modo dev não chama a atualização automática, forçamos aqui
  setTimeout(() => {
    autoUpdater.checkForUpdates();
  }, 2000);
}

let mainWindow;

const getProjectRoot = () => {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend');
  }
  const localRepo = path.join(__dirname, '..');
  const installedBackend = path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Manga AI Studio', 'resources', 'backend');
  if (!fs.existsSync(path.join(localRepo, 'venv_ui', 'Scripts', 'python.exe')) &&
      fs.existsSync(path.join(installedBackend, 'venv_ui', 'Scripts', 'python.exe'))) {
    return installedBackend;
  }
  return localRepo;
};


function createWindow() {
  app.setAppUserModelId("com.genikasuri.manga-ai-studio");

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false, // Frameless window para design moderno
    show: false, // Não mostrar a janela até que esteja pronta e maximizada
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs'),
      webSecurity: false
    },
    backgroundColor: '#0f1115',
    show: false // Mostrar apenas quando estiver pronto para evitar piscar branco
  });

  const isDev = process.argv.includes('--dev');
  
  if (isDev) {
    // Vite Dev Server
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.maximize();
    mainWindow.show();
    if (!isDev) {
      const settings = getSettingsSync();
      if (settings.autoUpdate !== false) {
        autoUpdater.checkForUpdates();
      }
    }
  });

  // -- Auto-Updater Events --
  autoUpdater.on('checking-for-update', () => {
    if (mainWindow) mainWindow.webContents.send('updater-status', { status: 'checking' });
  });

  autoUpdater.on('update-available', (info) => {
    if (mainWindow) mainWindow.webContents.send('updater-status', { status: 'available', info });
  });

  autoUpdater.on('update-not-available', (info) => {
    if (mainWindow) mainWindow.webContents.send('updater-status', { status: 'not-available', info });
  });

  autoUpdater.on('download-progress', (progressObj) => {
    if (mainWindow) mainWindow.webContents.send('updater-status', { status: 'progress', progress: progressObj });
  });

  autoUpdater.on('update-downloaded', (info) => {
    if (mainWindow) mainWindow.webContents.send('updater-status', { status: 'downloaded', info });
  });

  autoUpdater.on('error', (err) => {
    if (mainWindow) mainWindow.webContents.send('updater-status', { status: 'error', error: err.message });
  });
}

ipcMain.handle('install-update', () => {
  app.isQuiting = true;
  
  // Esconde a janela imediatamente para tirar a sensação de "travamento"
  if (mainWindow) {
    mainWindow.hide();
  }

  if (activePipelineProcess) {
    const { exec } = require('child_process');
    try { exec('taskkill /pid ' + activePipelineProcess.pid + ' /T /F'); } catch(e) {}
    activePipelineProcess = null;
  }
  
  // Dá um tempinho rápido pro processo fechar e dispara o instalador silencioso (que com oneClick=true mostrará só a barra)
  setTimeout(() => {
    autoUpdater.quitAndInstall(false, true);
  }, 500);
});

ipcMain.handle('check-for-updates', () => {
  autoUpdater.checkForUpdates();
});

// -- Funções de Backend (Interface) ------------------------------------------

// Persistência de Configurações
const settingsPath = path.join(app.getPath('userData'), 'settings.json');

// --- BIBLIOTECA IPC HANDLERS ---
ipcMain.handle('list-library-files', async (event) => {
  try {
    const bibliotecaDir = path.join(os.homedir(), 'Documents', 'Manga AI Studio', 'Biblioteca');
    if (!fs.existsSync(bibliotecaDir)) return { success: true, files: [] };
    
    const files = fs.readdirSync(bibliotecaDir)
      .filter(f => f.endsWith('.txt'))
      .map(f => {
        const filePath = path.join(bibliotecaDir, f);
        const stats = fs.statSync(filePath);
        return {
          name: f,
          path: filePath,
          size: stats.size,
          mtime: stats.mtime
        };
      })
      .sort((a, b) => b.mtime - a.mtime);
      
    return { success: true, files };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('read-library-file', async (event, filePath) => {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return { success: true, content };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('delete-library-file', async (event, filePath) => {
  try {
    fs.unlinkSync(filePath);
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

const defaultSettings = {
  theme: 'Dark',
  accent: 'Roxo (Padrão)',
  rememberZoom: false,
  baseFolder: '',
  sidebarWidth: 260,
  systemNotifications: true,
  autoUpdate: true,
  closeBehavior: 'ask' // 'tray', 'quit', 'ask'
};

function getSettingsSync() {
  try {
    if (fs.existsSync(settingsPath)) {
      const data = fs.readFileSync(settingsPath, 'utf-8');
      return { ...defaultSettings, ...JSON.parse(data) };
    }
  } catch (error) {
    console.error('Erro ao ler settings:', error);
  }
  return defaultSettings;
}

ipcMain.handle('get-settings', () => {
  return getSettingsSync();
});

  ipcMain.handle('save-settings', (event, settings) => {
    try {
      const currentSettings = getSettingsSync();
      const updatedSettings = { ...currentSettings, ...settings };
      fs.writeFileSync(settingsPath, JSON.stringify(updatedSettings, null, 2));
      return true;
    } catch (error) {
      console.error('Erro ao salvar settings:', error);
      return false;
    }
  });

  ipcMain.handle('get-stats', () => {
    try {
      const configDir = path.join(os.homedir(), 'AppData', 'Local', 'MangaAIStudio');
      const statsPath = path.join(configDir, 'stats.json');
      if (fs.existsSync(statsPath)) {
        return JSON.parse(fs.readFileSync(statsPath, 'utf8'));
      }
    } catch (error) {
      console.error('Erro ao ler stats:', error);
    }
    return { pagesProcessed: 0, timeSaved: 0 };
  });

  // -- Módulos -------------------------------------------------------------
  ipcMain.handle('check-modules-status', async () => {
    const status = {
      ocr: { state: 'not_installed', progress: 0 },
      cuda: { state: 'not_installed', progress: 0 },
      ollama: { state: 'not_installed', progress: 0 },
      rag: { state: 'not_installed', progress: 0 },
      ollamaModels: []
    };

    const projectRoot = getProjectRoot();

    const checkModuleExists = (venvName, moduleName) => {
      const venvSite = path.join(projectRoot, venvName, 'Lib', 'site-packages', moduleName);
      if (fs.existsSync(venvSite)) return true;
      try {
        const cfgPath = path.join(projectRoot, venvName, 'pyvenv.cfg');
        if (fs.existsSync(cfgPath)) {
          const cfg = fs.readFileSync(cfgPath, 'utf8');
          if (cfg.includes('include-system-site-packages = true')) {
            const homeMatch = cfg.match(/home\s*=\s*(.+)/);
            if (homeMatch && homeMatch[1]) {
              const homeSite = path.join(homeMatch[1].trim(), 'Lib', 'site-packages', moduleName);
              if (fs.existsSync(homeSite)) return true;
            }
          }
        }
      } catch(e) {}
      return false;
    };

    try {
      if (checkModuleExists('venv_ocr', 'transformers') && checkModuleExists('venv_ocr', 'einops')) {
        status.ocr.state = 'installed';
        status.ocr.progress = 100;
      }
    } catch(e) {}

    try {
      const pythonExe = path.join(projectRoot, 'venv_ocr', 'Scripts', 'python.exe');
      if (fs.existsSync(pythonExe) && checkModuleExists('venv_ocr', 'torch')) {
        status.cuda.state = 'installed';
        status.cuda.progress = 100;
      }
    } catch(e) {}

    try {
      if (checkModuleExists('venv_ui', 'chromadb') && checkModuleExists('venv_ui', 'sentence_transformers')) {
        status.rag.state = 'installed';
        status.rag.progress = 100;
      }
    } catch(e) {}

    try {
      const { execSync } = require('child_process');
      let ollamaPath = null;
      try {
        execSync('where ollama', { stdio: 'ignore' });
        ollamaPath = 'ollama';
      } catch {
        const localAppPath = path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Ollama', 'ollama.exe');
        if (fs.existsSync(localAppPath)) ollamaPath = localAppPath;
      }
      
      if (ollamaPath) {
        status.ollama.state = 'installed_but_closed';
        try {
          // Use fetch with a very short timeout so it doesn't hang if server is unreachable
          const req = await fetch('http://127.0.0.1:11434/', { signal: AbortSignal.timeout(1500) });
          if (req.ok) {
            status.ollama.state = 'installed_and_running';
            try {
              const tagsReq = await fetch('http://127.0.0.1:11434/api/tags', { signal: AbortSignal.timeout(1500) });
              if (tagsReq.ok) {
                const tagsData = await tagsReq.json();
                status.ollamaModels = tagsData.models ? tagsData.models.map(m => m.name) : [];
              }
            } catch(e) {}
          }
        } catch {}
      }
    } catch(e) {}

    return status;
  });

  ipcMain.handle('check-ollama-model', async (event, modelName) => {
    const { exec } = require('child_process');
    return new Promise((resolve) => {
      exec(`ollama show ${modelName}`, { windowsHide: true }, (error) => {
        resolve(!error);
      });
    });
  });

  ipcMain.handle('get-gpu-name', async () => {
    return new Promise((resolve) => {
      const { exec } = require('child_process');
      exec('powershell -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"', { windowsHide: true }, (err, stdout) => {
        if (err) return resolve("GPU");
        const lines = stdout.trim().split('\n');
        // Take the first line (in case there are multiple GPUs, we take the primary one)
        const name = lines[0].trim();
        resolve(name ? name : "GPU");
      });
    });
  });

  ipcMain.handle('pull-ollama-model', async (event, modelName) => {
    const { spawn } = require('child_process');
    return new Promise((resolve) => {
      const ollama = spawn('ollama', ['pull', modelName]);
      
      let lastProgress = 0;
      let buffer = '';
      const parseData = (data) => {
        buffer += data.toString('utf8');
        let lines = buffer.split(/[\r\n]+/);
        buffer = lines.pop(); // keep incomplete part
        for (const str of lines) {
          const match = str.match(/(\d+)%/);
          if (match) {
            const prog = parseInt(match[1], 10);
            if (prog !== lastProgress || prog === 100) {
              lastProgress = prog;
              const cleanText = str.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, '');
              const statsMatch = cleanText.match(/(\d+(?:\.\d+)?\s*[KMG]B\s*\/\s*\d+(?:\.\d+)?\s*[KMG]B.*)/i);
              let formattedText = cleanText.replace(/[▕▏█▒░━╸=|-]+/g, '').replace(/\s+/g, ' ').trim();
              if (statsMatch) {
                formattedText = 'Baixando... ' + prog + '% - ' + statsMatch[1];
              }
              event.sender.send('ollama-progress', { model: modelName, progress: prog, text: formattedText });
            }
          }
        }
      };

      ollama.stdout.on('data', parseData);
      ollama.stderr.on('data', parseData);

      ollama.on('close', (code) => {
        resolve({ success: code === 0 });
      });
      
      ollama.on('error', (err) => {
        resolve({ success: false, error: err.message });
      });
    });
  });

  ipcMain.handle('open-ollama-site', () => {
    require('electron').shell.openExternal('https://ollama.com/');
  });

  ipcMain.handle('start-ollama-server', () => {
    const { spawn } = require('child_process');
    const localAppPath = path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Ollama', 'ollama app.exe');
    if (fs.existsSync(localAppPath)) {
      spawn(`"${localAppPath}"`, { shell: true, detached: true, stdio: 'ignore', windowsHide: true });
    } else {
      spawn('ollama', ['serve'], { detached: true, stdio: 'ignore', windowsHide: true });
    }
  });

  ipcMain.handle('delete-ollama-model', async (event, modelName) => {
    const { execSync } = require('child_process');
    try {
      execSync(`ollama rm "${modelName}"`, { stdio: 'ignore' });
      return { success: true };
    } catch(e) {
      return { success: false, error: e.message };
    }
  });

  ipcMain.handle('repair-python-venv', async (event, envName) => {
    // envName pode ser 'ocr' ou 'ui'
    const { spawn } = require('child_process');
    const projectRoot = getProjectRoot();
    
    // Inicia um terminal visível para o usuário ver o progresso do pip
    try {
      const venvPath = envName === 'ocr' ? path.join(projectRoot, 'venv_ocr') : path.join(projectRoot, 'venv_ui');
      const pipPath = path.join(venvPath, 'Scripts', 'pip.exe');
      
      if (!fs.existsSync(pipPath)) {
        event.sender.send('venv-progress', { envName: envName, progress: 10, text: 'Criando ambiente virtual (venv)...' });
        const { spawnSync } = require('child_process');
        spawnSync('python', ['-m', 'venv', venvPath], { cwd: projectRoot, windowsHide: true });
      }

      let reqFile = envName === 'ocr' ? 'requirements-ocr.txt' : 'requirements.txt';
      const reqPath = path.join(projectRoot, reqFile);

      // Usar spawn em background enviando o output para o frontend
      const proc = spawn(pipPath, ['install', '-r', reqPath], { cwd: projectRoot, windowsHide: true });
      
      let buffer = '';
      const sendProgress = (data) => {
        buffer += data.toString('utf8');
        let lines = buffer.split(/[\r\n]+/);
        buffer = lines.pop();
        for (const str of lines) {
          const cleanText = str.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, '').trim();
          if (cleanText) {
            let formattedText = cleanText.replace(/[▕▏█▒░━╸=|-]+/g, '').replace(/\s+/g, ' ').trim();
            event.sender.send('venv-progress', { envName: envName, progress: 50, text: formattedText.substring(0, 80) });
          }
        }
      };

      proc.stdout.on('data', sendProgress);
      proc.stderr.on('data', sendProgress);

      proc.on('close', (code) => {
        if (code === 0) {
          event.sender.send('venv-progress', { envName: envName, progress: 100, text: 'Instalação concluída com sucesso!' });
        } else {
          event.sender.send('venv-progress', { envName: envName, progress: 100, text: 'Erro na instalação. Verifique o console.' });
        }
      });
      
      return { success: true };
    } catch(e) {
      return { success: false, error: e.message };
    }
  });

  ipcMain.handle('install-cuda', async (event) => {
    const { spawn } = require('child_process');
    const projectRoot = getProjectRoot();
    
    try {
      const venvPath = path.join(projectRoot, 'venv_ocr');
      const pipPath = path.join(venvPath, 'Scripts', 'pip.exe');
      
      if (!fs.existsSync(pipPath)) {
        event.sender.send('venv-progress', { envName: 'ocr', progress: 10, text: 'Criando ambiente virtual (venv)...' });
        const { spawnSync } = require('child_process');
        spawnSync('python', ['-m', 'venv', venvPath], { cwd: projectRoot, windowsHide: true });
      }
      
      const proc = spawn(pipPath, [
        'install', '--pre', 'torch', 'torchvision', '--upgrade',
        '--index-url', 'https://download.pytorch.org/whl/nightly/cu128'
      ], { cwd: projectRoot, windowsHide: true });
      
      let buffer = '';
      const sendProgress = (data) => {
        buffer += data.toString('utf8');
        let lines = buffer.split(/[\r\n]+/);
        buffer = lines.pop();
        for (const str of lines) {
          const cleanText = str.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, '').trim();
          if (cleanText) {
            let formattedText = cleanText.replace(/[▕▏█▒░━╸=|-]+/g, '').replace(/\s+/g, ' ').trim();
            event.sender.send('venv-progress', { envName: 'ocr', progress: 50, text: formattedText.substring(0, 80) });
          }
        }
      };

      proc.stdout.on('data', sendProgress);
      proc.stderr.on('data', sendProgress);

      proc.on('close', (code) => {
        if (code === 0) {
          event.sender.send('venv-progress', { envName: 'ocr', progress: 100, text: 'Aceleração CUDA instalada com sucesso!' });
        } else {
          event.sender.send('venv-progress', { envName: 'ocr', progress: 100, text: 'Erro ao instalar CUDA. Verifique o console.' });
        }
      });
      
      return { success: true };
    } catch(e) {
      return { success: false, error: e.message };
    }
  });

  // Controles da Janela (Titlebar)
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window-close', () => {
  if (!mainWindow) return;
  const settings = getSettingsSync();
  const behavior = settings.closeBehavior || 'ask';

  if (behavior === 'tray') {
    mainWindow.hide();
  } else if (behavior === 'quit') {
    app.isQuiting = true;
    app.quit();
  } else {
    const choice = dialog.showMessageBoxSync(mainWindow, {
      type: 'question',
      buttons: ['Minimizar para a Bandeja', 'Encerrar o Programa', 'Cancelar'],
      defaultId: 0,
      cancelId: 2,
      title: 'Confirmação',
      message: 'Você clicou em fechar. O que deseja fazer?',
      detail: 'Minimizar mantém a IA processando tarefas em segundo plano.'
    });

    if (choice === 0) {
      mainWindow.hide();
    } else if (choice === 1) {
      app.isQuiting = true;
      app.quit();
    }
  }
});

ipcMain.handle('load-studio-data', async (event, folderPath, isEditorMode) => {
  try {
    const folderName = path.basename(folderPath);
    const tempDir = path.join(os.homedir(), 'Documents', 'Manga AI Studio', 'Biblioteca', 'Temp');
    
    let txtPath = null;
    try {
      const statusPath = path.join(tempDir, 'status.json');
      if (fs.existsSync(statusPath)) {
        const st = JSON.parse(fs.readFileSync(statusPath, 'utf8'));
        const entry = st[folderName];
        if (entry) {
          if (isEditorMode) {
            txtPath = entry.raw || entry.corrigido;
          } else {
            txtPath = entry.traduzido;
          }
        }
      }
    } catch (e) {}

    if (!txtPath || !fs.existsSync(txtPath)) {
      txtPath = null;
      const suffixes = isEditorMode 
        ? ['_raw.txt', '_corrigido.txt', '_corrected.txt']
        : ['_traduzido.txt', '_translated.txt'];
  
      for (const suffix of suffixes) {
        const candidate = path.join(tempDir, `${folderName}${suffix}`);
        if (fs.existsSync(candidate)) {
          txtPath = candidate;
          break;
        }
      }
  
      if (!txtPath && fs.existsSync(folderPath)) {
        const allFiles = fs.readdirSync(folderPath);
        for (const suffix of suffixes) {
          const found = allFiles.find(f => f.toLowerCase().includes(suffix));
          if (found) {
            txtPath = path.join(folderPath, found);
            break;
          }
        }
      }
    }

    if (!txtPath || !fs.existsSync(txtPath)) {
      const errorMessage = isEditorMode 
        ? 'Nenhum arquivo raw/corrigido encontrado. Você precisa rodar a extração de OCR primeiro.'
        : 'Este capítulo ainda não foi traduzido. Se você deseja visualizar ou editar o OCR bruto, feche esta tela e clique no botão "Editor".';
      return { success: false, error: errorMessage };
    }

    const buffer = fs.readFileSync(txtPath);
    let text = buffer.toString('utf8');
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
    
    const parsed = parseStudioTxt(text);

    const imagesPaths = {};
    if (fs.existsSync(folderPath)) {
      const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];
      const images = fs.readdirSync(folderPath).filter(f => {
        const ext = path.extname(f).toLowerCase();
        return IMAGE_EXTS.includes(ext);
      });
      
      images.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
      
      images.forEach(img => {
        imagesPaths[img] = 'file://' + path.join(folderPath, img).replace(/\\/g, '/');
      });
    }

    return { 
      success: true, 
      data: parsed, 
      imagesPaths, 
      txtPath 
    };

  } catch (err) {
    console.error('Erro no load-studio-data:', err);
    return { success: false, error: err.message };
  }
});

ipcMain.handle('save-studio-data', async (event, txtPath, pagesData, isEditorMode) => {
  try {
    let content = '';
    let pageCount = 1;

    const pages = Object.keys(pagesData).sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));

    for (const pageName of pages) {
      const sep = '='.repeat(50);
      content += `${sep}\n`;
      content += `PÁGINA ${pageCount}: ${pageName}\n`;
      content += `${sep}\n\n`;
      const blocks = pagesData[pageName];
      
      if (!blocks || blocks.length === 0) {
        content += '[Nenhum texto detectado nesta página]\n\n';
      } else {
        for (let i = 0; i < blocks.length; i++) {
          if (isEditorMode) {
            content += blocks[i].original + '\n';
          } else {
            content += `[EN]: ${blocks[i].original}\n`;
            content += `[BR]: ${blocks[i].translated}\n`;
            content += `${sep}\n\n`;
          }
        }
        if (isEditorMode) content += '\n';
      }
      pageCount++;
    }

    fs.writeFileSync(txtPath, content.trim() + '\n', 'utf8');
    return { success: true };
  } catch (err) {
    console.error('Erro no save-studio-data:', err);
    return { success: false, error: err.message };
  }
});

// Lista imagens dentro de uma pasta (para o Estúdio)
ipcMain.handle('list-images', (event, dirPath) => {
  const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];
  try {
    const files = fs.readdirSync(dirPath);
    return files
      .filter(f => IMAGE_EXTS.includes(path.extname(f).toLowerCase()))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
      .map(f => ({
        name: f,
        path: path.join(dirPath, f),
        // Electron: usar file:// para exibir no browser
        url: 'file:///' + path.join(dirPath, f).replace(/\\/g, '/')
      }));
  } catch {
    return [];
  }
});


let tray = null;

app.whenReady().then(() => {
  createWindow();

  try {
    const iconPath = path.join(__dirname, 'public', 'icon.ico');
    if (fs.existsSync(iconPath)) {
      tray = new Tray(iconPath);
      const contextMenu = Menu.buildFromTemplate([
        { label: 'Mostrar Manga AI Studio', click: () => { if (mainWindow) mainWindow.show(); } },
        { label: 'Sair Completamente', click: () => { app.isQuiting = true; app.quit(); } }
      ]);
      tray.setToolTip('Manga AI Studio');
      tray.setContextMenu(contextMenu);
      
      tray.on('click', () => {
        if (mainWindow) mainWindow.show();
      });
    }
  } catch(e) { console.error('Erro ao criar Tray:', e); }

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuiting = true;
  if (activePipelineProcess) {
    const { exec } = require('child_process');
    try { exec('taskkill /pid ' + activePipelineProcess.pid + ' /T /F'); } catch (e) {}
    activePipelineProcess = null;
  }
});



// -- Pipeline de IA ----------------------------------------------------------
let activePipelineProcess = null;
let pipelinePaused = false;
let pipelineResumeCallback = null;
let isPipelineCanceled = false;

const sendLog = (event, msg, progress = null, isError = false) => {
  event.sender.send('pipeline-log', { text: msg, progress, isError });
};

ipcMain.handle('cancel-pipeline', (event) => {
  isPipelineCanceled = true;
  const { exec } = require('child_process');
  if (activePipelineProcess) {
    try {
      exec('taskkill /pid ' + activePipelineProcess.pid + ' /T /F');
    } catch (e) {}
    activePipelineProcess = null;
  }
  if (pipelinePaused && pipelineResumeCallback) {
    pipelinePaused = false;
    pipelineResumeCallback();
    pipelineResumeCallback = null;
  }
  // Libera VRAM do Ollama se estiver rodando tradução
  try {
    const http = require('http');
    const req = http.request('http://localhost:11434/api/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    req.write(JSON.stringify({ model: '', keep_alive: 0 }));
    req.end();
  } catch (e) {}
  if (event && event.sender) {
    event.sender.send('pipeline-canceled');
  }
  return true;
});

ipcMain.handle('resume-pipeline', (event) => {
  if (pipelinePaused && pipelineResumeCallback) {
    pipelinePaused = false;
    pipelineResumeCallback();
    pipelineResumeCallback = null;
    event.sender.send('pipeline-resumed');
    return true;
  }
  return false;
});

// -- Explorador de Arquivos ----------------------------------------------------

// Lista drives disponÃ­veis no Windows (C:\, D:\, ...)
ipcMain.handle('list-drives', async () => {
  const drives = [];
  for (let i = 65; i <= 90; i++) { // A-Z
    const letter = String.fromCharCode(i);
    const drivePath = letter + ':\\';
    try {
      fs.accessSync(drivePath);
      drives.push({ name: letter + ':', path: drivePath, isDrive: true });
    } catch { /* drive nÃ£o existe */ }
  }
  return drives;
});

// Retorna o diretório pai de um caminho
ipcMain.handle('get-parent-path', (event, dirPath) => {
  const parent = path.dirname(dirPath);
  if (parent === dirPath) return null;
  return parent;
});

// Lista subpastas e imagens de um diretório com metadados extras
ipcMain.handle('list-directory', (event, dirPath) => {
  const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];
  
  let pipelineStatus = {};
  try {
    const statusPath = path.join(os.homedir(), 'Documents', 'Manga AI Studio', 'Biblioteca', 'Temp', 'status.json');
    if (fs.existsSync(statusPath)) {
      pipelineStatus = JSON.parse(fs.readFileSync(statusPath, 'utf8'));
    }
  } catch (e) { /* ignore */ }

  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    
    const folders = entries
      .filter(e => e.isDirectory())
      .map(e => {
        const subPath = path.join(dirPath, e.name);
        let hasImages = false;
        try {
          const subFiles = fs.readdirSync(subPath);
          hasImages = subFiles.some(f => IMAGE_EXTS.includes(path.extname(f).toLowerCase()));
        } catch { /* sem permissão */ }

        let estado = 'nenhum';
        const st = pipelineStatus[e.name];
        if (st) {
          if (st.traduzido) estado = 'traduzido';
          else if (st.corrigido) estado = 'corrigido';
          else if (st.raw) estado = 'raw';
          else if (st.nome_final) estado = 'traduzido';
        } else {
          try {
            const tempDir = path.join(os.homedir(), 'Documents', 'Manga AI Studio', 'Biblioteca', 'Temp');
            if (fs.existsSync(path.join(tempDir, e.name + '_traduzido.txt'))) estado = 'traduzido';
            else if (fs.existsSync(path.join(tempDir, e.name + '_corrigido.txt'))) estado = 'corrigido';
            else if (fs.existsSync(path.join(tempDir, e.name + '_raw.txt'))) estado = 'raw';
          } catch (e) { /* ignore */ }
        }
        
        if (estado !== 'nenhum') hasImages = true;

        return { name: e.name, path: subPath, hasImages, isDirectory: true, estado };
      })
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

    const files = entries
      .filter(e => e.isFile() && IMAGE_EXTS.includes(path.extname(e.name).toLowerCase()))
      .map(e => {
        const filePath = path.join(dirPath, e.name);
        return {
          name: e.name,
          path: filePath,
          isImage: true,
          url: 'file:///' + filePath.replace(/\\/g, '/')
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

    return [...folders, ...files];
  } catch {
    return { error: 'Acesso negado ou caminho inválido.' };
  }
});

// -- Handlers do Leitor (Biblioteca) --
ipcMain.handle('list-biblioteca-files', async () => {
  try {
    const bibliotecaDir = path.join(os.homedir(), 'Documents', 'Manga AI Studio', 'Biblioteca');
    if (!fs.existsSync(bibliotecaDir)) return [];
    
    const files = fs.readdirSync(bibliotecaDir)
      .filter(f => f.toLowerCase().endsWith('.txt'))
      .map(f => {
        const fullPath = path.join(bibliotecaDir, f);
        const stat = fs.statSync(fullPath);
        return { name: f, path: fullPath, mtime: stat.mtimeMs };
      })
      .sort((a, b) => b.mtime - a.mtime);
    return files;
  } catch (err) {
    console.error('Erro ao listar biblioteca:', err);
    return [];
  }
});

ipcMain.handle('read-text-file', async (event, filePath) => {
  try {
    const buffer = fs.readFileSync(filePath);
    let text = buffer.toString('utf8');
    if (text.charCodeAt(0) === 0xFEFF) {
      text = text.slice(1);
    }
    return { success: true, content: text };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('save-text-file', async (event, filePath, content) => {
  try {
    fs.writeFileSync(filePath, content, 'utf8');
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

// -- Handlers do Estúdio de Tradução / Editor OCR --


function parseStudioTxt(content) {
  const pagesOriginal = {};
  const pagesTranslated = {};
  let currentPage = null;
  const pageRe = /(?:^|===\s*)P.{0,2}GINA\s+\d+\s*:\s*(.*?)(?:\s*===|$)/i;

  const lines = content.split('\n');
  for (let line of lines) {
    const ls = line.trim();
    if (!ls) continue;

    const m = pageRe.exec(ls);
    if (m) {
      currentPage = m[1].trim();
      pagesOriginal[currentPage] = [];
      pagesTranslated[currentPage] = [];
    } else if (currentPage !== null && !ls.startsWith('===')) {
      if (ls.toUpperCase().startsWith('[EN]:')) {
        pagesOriginal[currentPage].push(ls.substring(5).trim());
      } else if (ls.toUpperCase().startsWith('[BR]:')) {
        pagesTranslated[currentPage].push(ls.substring(5).trim());
      } else {
        pagesOriginal[currentPage].push(ls);
        pagesTranslated[currentPage].push('');
      }
    }
  }

  return { pagesOriginal, pagesTranslated };
}

ipcMain.handle('select-folder', async () => {
  const { dialog } = require('electron');
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'openDirectory']
  });
  if (!result.canceled) return result.filePaths[0];
  return null;
});

ipcMain.handle('finalize-pipeline', async (event, data) => {
  const { finalTarget, finalName, folderName, inputPath } = data;
  if (!finalTarget || !finalName || !fs.existsSync(finalTarget)) return { success: false, error: 'Target invalid' };

  try {
    const bibliotecaDir = path.join(os.homedir(), 'Documents', 'Manga AI Studio', 'Biblioteca');
    const tempDir = path.join(bibliotecaDir, 'Temp');
    const destBiblioteca = path.join(bibliotecaDir, finalName.endsWith('.txt') ? finalName : finalName + '.txt');
    
    // Copy to Biblioteca
    fs.copyFileSync(finalTarget, destBiblioteca);

    // Copy to original folder if possible
    let destScanlator = null;
    if (inputPath) {
      try {
        const scanlatorDir = fs.statSync(inputPath).isDirectory() ? inputPath : path.dirname(inputPath);
        destScanlator = path.join(scanlatorDir, path.basename(destBiblioteca));
        fs.copyFileSync(finalTarget, destScanlator);
      } catch (copyErr) {
        console.warn('Aviso: Não foi possível copiar para o diretório de origem:', copyErr.message);
      }
    }

    // Update status.json
    const statusPath = path.join(tempDir, 'status.json');
    let st = {};
    if (fs.existsSync(statusPath)) {
      try { st = JSON.parse(fs.readFileSync(statusPath, 'utf8')); } catch(e){}
    }
    if (!st[folderName]) st[folderName] = {};
    st[folderName].nome_final = path.basename(destBiblioteca);
    fs.writeFileSync(statusPath, JSON.stringify(st, null, 2), 'utf8');

    new Notification({
      title: 'Manga AI Studio',
      body: `Processamento salvo: ${path.basename(destBiblioteca)}`
    }).show();

    return { success: true, destBiblioteca, destScanlator };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('run-pipeline', async (event, config) => {
  isPipelineCanceled = false;
  const { spawn } = require('child_process');
  const projectRoot = getProjectRoot();
  let pythonExeOcr = path.join(projectRoot, 'venv_ocr', 'Scripts', 'python.exe');
  let pythonExeUi = path.join(projectRoot, 'venv_ui', 'Scripts', 'python.exe');
  const installedBackend = path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Manga AI Studio', 'resources', 'backend');
  if (!fs.existsSync(pythonExeOcr) && fs.existsSync(path.join(installedBackend, 'venv_ocr', 'Scripts', 'python.exe'))) {
    pythonExeOcr = path.join(installedBackend, 'venv_ocr', 'Scripts', 'python.exe');
  }
  if (!fs.existsSync(pythonExeUi) && fs.existsSync(path.join(installedBackend, 'venv_ui', 'Scripts', 'python.exe'))) {
    pythonExeUi = path.join(installedBackend, 'venv_ui', 'Scripts', 'python.exe');
  }
  
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

  const isSingleImage = !fs.statSync(inputPath).isDirectory() && pInput.ext.toLowerCase() !== '.txt';
  const folderName = isSingleImage ? path.basename(path.dirname(inputPath)) : baseName;
  const statusPath = path.join(tempDir, 'status.json');
  let st = {};
  if (fs.existsSync(statusPath)) {
    try { st = JSON.parse(fs.readFileSync(statusPath, 'utf8')); } catch(e){}
  }
  const existingEntry = st[folderName];

  let currentTarget = inputPath;
  
  const runScript = (exe, scriptName, args) => {
    return new Promise((resolve, reject) => {
      if (isPipelineCanceled) {
        return reject(new Error('Cancelado pelo usuário.'));
      }
      const instBackend = path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Manga AI Studio', 'resources', 'backend');
      let targetExe = exe;
      if (!fs.existsSync(targetExe)) {
        const altExe = path.join(instBackend, path.basename(path.dirname(path.dirname(exe))), 'Scripts', 'python.exe');
        if (fs.existsSync(altExe)) targetExe = altExe;
      }
      const actualRoot = fs.existsSync(path.join(projectRoot, scriptName)) ? projectRoot : instBackend;
      const scriptFullPath = path.join(actualRoot, scriptName);

      activePipelineProcess = spawn(targetExe, [scriptFullPath, ...args], { 
        cwd: actualRoot, 
        windowsHide: true,
        env: { ...process.env, PYTHONUNBUFFERED: "1" }
      });
      
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
    let expectedTxtPath = null;
    if (config.steps.ocr) {
      sendLog(event, '\n>>> ETAPA 1: EXTRAÇÃO DE TEXTO BRUTO (GPU)', 10);
      expectedTxtPath = path.join(tempDir, baseName + '_raw.txt');
      let args = [inputPath, '--output', expectedTxtPath];
      
      // Auto-mesclagem: anexar ao arquivo existente quando processando imagem avulsa
      if (isSingleImage) {
        // Primeiro tenta usar o caminho do status.json
        let existingRawPath = null;
        if (existingEntry && existingEntry.raw && fs.existsSync(existingEntry.raw)) {
          existingRawPath = existingEntry.raw;
        } else if (fs.existsSync(expectedTxtPath)) {
          // Fallback: o arquivo _raw.txt já existe no disco
          existingRawPath = expectedTxtPath;
        }
        
        if (existingRawPath) {
          expectedTxtPath = existingRawPath;
          args = [inputPath, '--output', expectedTxtPath, '--append'];
          sendLog(event, `\n Auto-Mesclagem ativada! Anexando página avulsa ao arquivo: ${path.basename(expectedTxtPath)}`);
        }
      }

      args.push('--gpu');
      if (config.steps && config.steps.vlmDirector && config.models && config.models.vlm && config.models.vlm !== "Nenhum modelo local") {
        args.push('--vlm-director', '--vlm-model', config.models.vlm);
        sendLog(event, `\n [VLM] Diretor Visual Ativado: ${config.models.vlm}`);
      }
      
      await runScript(pythonExeOcr, 'manga_ocr.py', args);
      currentTarget = expectedTxtPath;
      
      if (config.steps.pauseOcr) {
        sendLog(event, '\n PAUSA MANUAL ATIVADA. Alternando para o Editor Visual...', 30);
        // We will pause here
        await new Promise((resolve) => {
          pipelinePaused = true;
          pipelineResumeCallback = resolve;
          // Notify UI to open studio
          let folderPath = inputPath;
          if (!fs.statSync(inputPath).isDirectory()) {
            folderPath = path.dirname(inputPath);
          }
          event.sender.send('pipeline-paused', { inputPath: folderPath, targetPath: currentTarget });
        });
        sendLog(event, '\n RETOMANDO PIPELINE...', 35);
      }
    } else {
      expectedTxtPath = path.join(tempDir, baseName + '_raw.txt');
      if (existingEntry && existingEntry.raw && fs.existsSync(existingEntry.raw)) {
        currentTarget = existingEntry.raw;
      } else if (fs.existsSync(expectedTxtPath)) {
        currentTarget = expectedTxtPath;
      } else {
        const outRaw = path.join(inputPath, 'output_raw', `${baseName}_raw.txt`);
        const directRaw = path.join(inputPath, `${baseName}_raw.txt`);
        if (fs.existsSync(outRaw)) {
          currentTarget = outRaw;
        } else if (fs.existsSync(directRaw)) {
          currentTarget = directRaw;
        }
      }
      sendLog(event, `\n [INFO] Usando OCR existente em: ${path.basename(currentTarget)}`);
    }

    if (config.overwrite) {
      sendLog(event, '\n [INFO] Modo Sobrescrever ativo: Limpando arquivos intermediários antigos para reprocessamento...');
      try {
        const corrCandidate = path.join(tempDir, baseName + '_corrigido.txt');
        const transCandidate = path.join(tempDir, baseName + '_traduzido.txt');
        if (fs.existsSync(corrCandidate)) fs.unlinkSync(corrCandidate);
        if (fs.existsSync(transCandidate)) fs.unlinkSync(transCandidate);
      } catch(e) {}
    }

    // ETAPA 2: Correção
    if (config.steps.correct) {
      sendLog(event, '\n>>> ETAPA 2: POLIMENTO DE INGLÊS (IA)', 40);
      let args = [currentTarget, '--dict-global', globalDictPath, '--dict-local', localDictPath, '--output', tempDir, '--model', config.models.corr];
      await runScript(pythonExeUi, 'ocr_corrector.py', args);
      let corrStem = path.basename(currentTarget, path.extname(currentTarget)).replace('_raw', '');
      currentTarget = path.join(tempDir, corrStem + '_corrigido.txt');
    } else {
      let corrStem = path.basename(currentTarget, path.extname(currentTarget)).replace('_raw', '');
      let possibleCorrPath = path.join(tempDir, corrStem + '_corrigido.txt');
      if (fs.existsSync(possibleCorrPath)) currentTarget = possibleCorrPath;
    }

    // ETAPA 2.5: Page Director (Diretor de Contexto)
    if (config.steps && config.steps.pageDirector && config.models && config.models.ctx && config.models.ctx !== "Nenhum modelo local") {
      sendLog(event, '\n>>> ETAPA 2.5: ANALISANDO CONTEXTO DA CENA (PAGE DIRECTOR)', 55);
      let args = [currentTarget, '--model', config.models.ctx];
      try {
        await runScript(pythonExeUi, 'page_director.py', args);
      } catch (err) {
        sendLog(event, '\n [Aviso] Falha no Page Director. A tradução prosseguirá sem anotações de contexto.');
      }
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
      let fPath = inputPath;
      if (!fs.statSync(inputPath).isDirectory()) {
        fPath = path.dirname(inputPath);
      }
      event.sender.send('pipeline-finished', { inputPath: fPath, targetPath: currentTarget });
    }

    // Salvar os caminhos no status.json para o Auto-Merge funcionar corretamente
    try {
      let currentSt = {};
      if (fs.existsSync(statusPath)) {
        currentSt = JSON.parse(fs.readFileSync(statusPath, 'utf8'));
      }
      if (!currentSt[folderName]) currentSt[folderName] = {};
      
      if (expectedTxtPath) currentSt[folderName].raw = expectedTxtPath;
      if (currentTarget.endsWith('_corrigido.txt')) currentSt[folderName].corrigido = currentTarget;
      if (currentTarget.endsWith('_traduzido.txt')) {
        currentSt[folderName].traduzido = currentTarget;
        currentSt[folderName].corrigido = currentTarget.replace('_traduzido', '_corrigido');
      }
      // Preservar o nome final se já existir
      if (existingEntry && existingEntry.nome_final) currentSt[folderName].nome_final = existingEntry.nome_final;
      
      fs.writeFileSync(statusPath, JSON.stringify(currentSt, null, 2), 'utf8');
    } catch (e) {
      console.error('Erro ao salvar status.json:', e);
    }

    if (getSettingsSync().systemNotifications !== false) {
      new Notification({
        title: 'Manga AI Studio',
        body: `Processamento finalizado para ${folderName}!`
      }).show();
    }

    // Atualizar Estatísticas (Gamificação)
    try {
      const statsPath = path.join(configDir, 'stats.json');
      let stats = { pagesProcessed: 0, timeSaved: 0 };
      if (fs.existsSync(statsPath)) {
        stats = JSON.parse(fs.readFileSync(statsPath, 'utf8'));
      }
      
      let pagesCount = 1;
      if (fs.existsSync(inputPath) && fs.statSync(inputPath).isDirectory()) {
        const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];
        pagesCount = fs.readdirSync(inputPath).filter(f => IMAGE_EXTS.includes(path.extname(f).toLowerCase())).length || 1;
      }
      
      stats.pagesProcessed += pagesCount;
      // Estima-se 15 minutos economizados por página (Limpeza OCR + Tradução + Typesetting base)
      stats.timeSaved += (pagesCount * 15); 
      
      fs.writeFileSync(statsPath, JSON.stringify(stats, null, 2), 'utf8');
    } catch(e) {
      console.error('Erro ao salvar stats.json:', e);
    }

    return { 
      success: true, 
      finalTarget: currentTarget,
      needsName: !(existingEntry && existingEntry.nome_final) && (currentTarget.endsWith('_traduzido.txt') || config.steps.translate),
      existingName: existingEntry ? existingEntry.nome_final : null,
      folderName,
      inputPath
    };

  } catch (err) {
    if (isPipelineCanceled) {
      sendLog(event, '\n[CANCELADO] Processamento interrompido pelo usuário.', null, false);
      return { success: false, canceled: true };
    }
    sendLog(event, '\n[ERRO] ERRO: ' + err.message, null, true);
    if (getSettingsSync().systemNotifications !== false) {
      new Notification({
        title: 'Erro no Processamento',
        body: err.message
      }).show();
    }
    return { success: false, error: err.message };
  }
});
