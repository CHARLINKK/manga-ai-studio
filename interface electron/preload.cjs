const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Window Controls
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),

  // Settings
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
  getStats: () => ipcRenderer.invoke('get-stats'),
  
  // Auto-Updater
  onUpdaterStatus: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('updater-status', handler);
    return () => ipcRenderer.removeListener('updater-status', handler);
  },
  installUpdate: () => ipcRenderer.invoke('install-update'),
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  
  // ── Módulos ───────────────────────────────────────
  checkModulesStatus: () => ipcRenderer.invoke('check-modules-status'),
  getGpuName: () => ipcRenderer.invoke('get-gpu-name'),
  pullOllamaModel: (modelName) => ipcRenderer.invoke('pull-ollama-model', modelName),
  onOllamaProgress: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('ollama-progress', handler);
    return () => ipcRenderer.removeListener('ollama-progress', handler);
  },
  openOllamaSite: () => ipcRenderer.invoke('open-ollama-site'),
  startOllamaServer: () => ipcRenderer.invoke('start-ollama-server'),
  deleteOllamaModel: (modelName) => ipcRenderer.invoke('delete-ollama-model', modelName),
  repairPythonVenv: (envName) => ipcRenderer.invoke('repair-python-venv', envName),
  installCuda: () => ipcRenderer.invoke('install-cuda'),
  onVenvProgress: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('venv-progress', handler);
    return () => ipcRenderer.removeListener('venv-progress', handler);
  },

  // ── Pipeline de Processamento ──────────────────────────────────────────
  selectFolder: () => ipcRenderer.invoke('select-folder'),
  runPipeline: (config) => ipcRenderer.invoke('run-pipeline', config),
  finalizePipeline: (data) => ipcRenderer.invoke('finalize-pipeline', data),
  cancelPipeline: () => ipcRenderer.invoke('cancel-pipeline'),
  resumePipeline: () => ipcRenderer.invoke('resume-pipeline'),
  onPipelineLog: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('pipeline-log', handler);
    return () => ipcRenderer.removeListener('pipeline-log', handler);
  },
  onPipelinePaused: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('pipeline-paused', handler);
    return () => ipcRenderer.removeListener('pipeline-paused', handler);
  },
  onPipelineResumed: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('pipeline-resumed', handler);
    return () => ipcRenderer.removeListener('pipeline-resumed', handler);
  },
  onPipelineFinished: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('pipeline-finished', handler);
    return () => ipcRenderer.removeListener('pipeline-finished', handler);
  },

  // ── Estúdio ─────────────────────────────────────────────────────────────
  loadStudioData: (folderPath, isEditorMode) => ipcRenderer.invoke('load-studio-data', folderPath, isEditorMode),
  saveStudioData: (txtPath, pagesData, isEditorMode) => ipcRenderer.invoke('save-studio-data', txtPath, pagesData, isEditorMode),

  // Leitor
  listBibliotecaFiles: () => ipcRenderer.invoke('list-biblioteca-files'),
  readTextFile: (filePath) => ipcRenderer.invoke('read-text-file', filePath),
  saveTextFile: (filePath, content) => ipcRenderer.invoke('save-text-file', filePath, content),

  // Explorador de Arquivos
  listDrives: () => ipcRenderer.invoke('list-drives'),
  getParentPath: (dirPath) => ipcRenderer.invoke('get-parent-path', dirPath),
  listDirectory: (dirPath) => ipcRenderer.invoke('list-directory', dirPath),
  listImages: (dirPath) => ipcRenderer.invoke('list-images', dirPath),

  // Biblioteca Central
  listLibraryFiles: () => ipcRenderer.invoke('list-library-files'),
  readLibraryFile: (path) => ipcRenderer.invoke('read-library-file', path),
  deleteLibraryFile: (path) => ipcRenderer.invoke('delete-library-file', path)
});
