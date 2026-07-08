import { useState, useEffect, useCallback, useRef } from 'react';
import ModulesCenter from './components/ModulesCenter';
import TranslationStudio from './components/TranslationStudio';
import Processing from './components/Processing';
import Settings from './components/Settings';
import Library from './components/Library';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('processamento');

  // ── Explorer state ────────────────────────────────────────────────────────
  const [currentPath, setCurrentPath] = useState(null);    // pasta atual
  const [entries, setEntries] = useState([]);              // subpastas listadas
  const [isAtRoot, setIsAtRoot] = useState(false);         // mostrando drives
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [isEditorMode, setIsEditorMode] = useState(false); // Modo OCR (true) ou Estúdio (false)
  const [isPipelinePaused, setIsPipelinePaused] = useState(false);
  const [expandedFolder, setExpandedFolder] = useState(null); // pasta expandida no acordeão
  const [isLoading, setIsLoading] = useState(false);
  const [explorerError, setExplorerError] = useState('');
  const [isTheaterMode, setIsTheaterMode] = useState(false);
  const [isDraggingGlobal, setIsDraggingGlobal] = useState(false);
  const [hoveredImage, setHoveredImage] = useState(null);

  // ── Auto-Updater ─────────────────────────────────────────────────────────
  const [updateStatus, setUpdateStatus] = useState(null); // 'available', 'progress', 'downloaded', 'error', 'installing'
  const [updateProgress, setUpdateProgress] = useState(null);
  const [updateError, setUpdateError] = useState(null);
  const [updateInfo, setUpdateInfo] = useState(null);
  const [showUpdateModal, setShowUpdateModal] = useState(false);

  useEffect(() => {
    if (window.electronAPI && window.electronAPI.onUpdaterStatus) {
      const cleanup = window.electronAPI.onUpdaterStatus((data) => {
        setUpdateStatus(data.status);
        if (data.info) setUpdateInfo(data.info);
        if (data.status === 'available' || data.status === 'progress' || data.status === 'downloaded') {
          setShowUpdateModal(true);
        }
        if (data.status === 'progress') setUpdateProgress(data.progress);
        if (data.status === 'error') {
          setUpdateError(data.error);
          setShowUpdateModal(true);
        }
      });
      return cleanup;
    }
  }, []);

  // ── Global Pipeline Progress ─────────────────────────────────────────────
  const [globalProgress, setGlobalProgress] = useState(0);
  const [isGlobalRunning, setIsGlobalRunning] = useState(false);

  useEffect(() => {
    if (!window.electronAPI) return;
    const cleanupLog = window.electronAPI.onPipelineLog((data) => {
      if (data.progress !== null) {
        setGlobalProgress(data.progress);
        setIsGlobalRunning(true);
        if (data.progress >= 100) {
          setTimeout(() => setIsGlobalRunning(false), 2000);
        }
      }
    });
    return () => cleanupLog();
  }, []);

  // ── Global Model Download Progress ─────────────────────────────────────────
  const [downloadingModels, setDownloadingModels] = useState({});

  useEffect(() => {
    if (!window.electronAPI || !window.electronAPI.onOllamaProgress) return;
    const cleanupOllama = window.electronAPI.onOllamaProgress((data) => {
      setDownloadingModels(prev => ({
        ...prev,
        [data.model]: { progress: data.progress, text: data.text }
      }));
      if (data.progress >= 100) {
        setTimeout(() => {
          setDownloadingModels(prev => {
            const nd = {...prev};
            delete nd[data.model];
            return nd;
          });
        }, 2000);
      }
    });
    return () => cleanupOllama();
  }, []);

  // ── Resize do Sidebar ────────────────────────────────────────────────────
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [viewMode, setViewMode] = useState('list');
  const isResizing = useRef(false);
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(0);

  const SIDEBAR_MIN = 180;
  const SIDEBAR_MAX = 520;

  // ── Settings / Theme ─────────────────────────────────────────────────────
  useEffect(() => {
    if (window.electronAPI) {
      window.electronAPI.getSettings().then(settings => {
        applySettings(settings);
        // Restaurar largura do sidebar salva
        if (settings.sidebarWidth && settings.sidebarWidth >= 180) {
          setSidebarWidth(settings.sidebarWidth);
        }
        // Abre a pasta base salva nas configurações
        const base = settings.baseFolder;
        if (base && base.trim()) {
          navigateTo(base.trim());
        } else {
          loadDrives(); // sem pasta base → mostra drives
        }
      });
    } else {
      // Dev sem Electron: mock
      navigateTo('D:\\Manga');
    }
  }, []);

  // ── Handlers de resize do sidebar ────────────────────────────────────
  const onResizeMouseDown = useCallback((e) => {
    e.preventDefault();
    isResizing.current = true;
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [sidebarWidth]);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!isResizing.current) return;
      const delta = e.clientX - resizeStartX.current;
      const newWidth = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, resizeStartWidth.current + delta));
      setSidebarWidth(newWidth);
    };

    const onMouseUp = (e) => {
      if (!isResizing.current) return;
      isResizing.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      // Persiste no backend
      const finalWidth = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, resizeStartWidth.current + (e.clientX - resizeStartX.current)));
      if (window.electronAPI) {
        window.electronAPI.getSettings().then(settings => {
          window.electronAPI.saveSettings({ ...settings, sidebarWidth: finalWidth });
        });
      }
    };

    const cleanupPaused = window.electronAPI.onPipelinePaused((data) => {
      setSelectedFolder({ path: data.inputPath, name: data.inputPath.split(/[/\\]/).pop(), hasImages: true });
      setIsEditorMode(true);
      setIsPipelinePaused(true);
      setActiveTab('estudio');
    });

    const cleanupResumed = window.electronAPI.onPipelineResumed(() => {
      setIsPipelinePaused(false);
      setActiveTab('processamento');
    });

    const cleanupFinished = window.electronAPI.onPipelineFinished((data) => {
      setSelectedFolder({ path: data.inputPath, name: data.inputPath.split(/[/\\]/).pop(), hasImages: true });
      setIsEditorMode(false);
      setIsPipelinePaused(false);
      setActiveTab('estudio');
    });

    const cleanupCanceled = window.electronAPI.onPipelineCanceled && window.electronAPI.onPipelineCanceled(() => {
      setIsGlobalRunning(false);
      setGlobalProgress(0);
    });

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      cleanupPaused();
      cleanupResumed();
      cleanupFinished();
      if (cleanupCanceled) cleanupCanceled();
    };
  }, []);

  const applySettings = (settings) => {
    const colorMap = {
      'Roxo (Padrão)': '#6366f1', 'Azul': '#3b82f6',
      'Verde': '#10b981', 'Vermelho': '#ef4444', 'Laranja': '#f59e0b'
    };
    if (settings.accent) {
      const hexColor = colorMap[settings.accent] || settings.accent;
      document.documentElement.style.setProperty('--brand-blue', hexColor);
      document.documentElement.style.setProperty('--brand-blue-hover', hexColor);
    }
    let theme = settings.theme || 'Dark';
    if (theme === 'System') {
      theme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'Light' : 'Dark';
    }
    document.documentElement.setAttribute('data-theme', theme === 'Light' ? 'light' : 'dark');
  };

  const handleMinimize = () => window.electronAPI?.minimize();
  const handleMaximize = () => window.electronAPI?.maximize();
  const handleClose   = () => window.electronAPI?.close();

  // ── Lógica do explorador ─────────────────────────────────────────────────

  // Mostra lista de drives (nível raiz)
  const loadDrives = async () => {
    setIsLoading(true);
    setExplorerError('');
    const drives = window.electronAPI
      ? await window.electronAPI.listDrives()
      : [{ name: 'C:', path: 'C:\\', isDrive: true }];
    setEntries(drives);
    setCurrentPath(null);
    setIsAtRoot(true);
    setIsLoading(false);
  };

  // Navega para um diretório listando suas subpastas
  const navigateTo = useCallback(async (folderPath) => {
    setIsLoading(true);
    setExplorerError('');
    try {
      let result;
      if (window.electronAPI) {
        result = await window.electronAPI.listDirectory(folderPath);
      } else {
        const lowerPath = folderPath.toLowerCase();
        if (lowerPath.endsWith('ch001') || lowerPath.endsWith('ch003') || lowerPath.endsWith('chapter 001') || lowerPath.endsWith('chapter 003')) {
          result = [
            { name: 'page_001.png', path: folderPath + '/page_001.png', isImage: true, url: 'https://picsum.photos/400/600?random=11' },
            { name: 'page_002.png', path: folderPath + '/page_002.png', isImage: true, url: 'https://picsum.photos/400/600?random=22' },
            { name: 'page_003.png', path: folderPath + '/page_003.png', isImage: true, url: 'https://picsum.photos/400/600?random=33' }
          ];
        } else {
          result = [
            { name: 'Chapter 001 — The Beginning', path: folderPath + '/Chapter 001', hasImages: true },
            { name: 'Chapter 002 — The Battle',    path: folderPath + '/Chapter 002', hasImages: false },
            { name: 'Chapter 003 — Resolution',    path: folderPath + '/Chapter 003', hasImages: true },
          ];
        }
      }
      if (result.error) {
        setExplorerError(result.error);
      } else {
        setEntries(result);
        setCurrentPath(folderPath);
        setIsAtRoot(false);
      }
    } catch {
      setExplorerError('Erro ao ler o diretório.');
    }
    setIsLoading(false);
  }, []);

  // Botão "↑ Subir" → vai para o pai ou para os drives se na raiz de um drive
  const handleGoUp = async () => {
    if (!currentPath) return;
    if (window.electronAPI) {
      const parent = await window.electronAPI.getParentPath(currentPath);
      if (!parent) {
        loadDrives(); // chegou na raiz do drive → mostra drives
      } else {
        navigateTo(parent);
      }
    } else {
      loadDrives();
    }
  };

  // Clique em item: se é drive ou pasta normal, entra. Se tem imagens, alterna o acordeão.
  const handleEntryClick = (entry, e) => {
    if (entry.isDrive) {
      navigateTo(entry.path);
    } else if (entry.hasImages) {
      // Alterna acordeão
      setExpandedFolder(prev => prev === entry.path ? null : entry.path);
    } else if (entry.isImage) {
      // Clique em imagem: pode abrir no Estúdio como selecionado se necessário
      setSelectedFolder({ name: currentPath.split(/[/\\]/).pop(), path: currentPath });
      setActiveTab('estudio');
    } else {
      // Pasta sem imagens → navega para dentro
      navigateTo(entry.path);
    }
  };

  // Duplo clique sempre navega para dentro (mesmo nas com imagens)
  const handleEntryDoubleClick = (entry) => {
    if (entry.isDrive) return;
    navigateTo(entry.path);
  };

  // Segmentos do caminho atual para breadcrumb
  const pathSegments = currentPath
    ? currentPath.replace(/\\/g, '/').split('/').filter(Boolean)
    : [];

  const handleBreadcrumbClick = async (idx) => {
    const parts = pathSegments;
    // Para Windows: ["C:", "Users", "foo"] → "C:/Users"
    const rebuilt = parts.slice(0, idx + 1).join('/');
    // Se é só o drive (ex: "C:"), transformar em "C:\"
    const finalPath = rebuilt.endsWith(':') ? rebuilt + '\\' : rebuilt;
    navigateTo(finalPath);
  };

  const handleGlobalDragOver = (e) => {
    e.preventDefault();
    if (!isDraggingGlobal) setIsDraggingGlobal(true);
  };
  
  const handleGlobalDragLeave = (e) => {
    e.preventDefault();
    if (e.currentTarget.contains(e.relatedTarget)) return;
    setIsDraggingGlobal(false);
  };

  const handleGlobalDrop = async (e) => {
    e.preventDefault();
    setIsDraggingGlobal(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const path = files[0].path;
      if (path) {
        navigateTo(path);
      }
    }
  };

  return (
    <div 
      className="app-container dark-theme"
      onDragOver={handleGlobalDragOver}
      onDragLeave={handleGlobalDragLeave}
      onDrop={handleGlobalDrop}
    >
      {isDraggingGlobal && (
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, 
          backgroundColor: 'rgba(99, 102, 241, 0.2)', backdropFilter: 'blur(4px)',
          zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: '4px dashed var(--brand-blue)'
        }}>
          <h2 style={{color: 'white', textShadow: '0 2px 10px rgba(0,0,0,0.5)'}}>Solte a pasta aqui para abrir no Explorador</h2>
        </div>
      )}

      {hoveredImage && (
        <div className="explorer-image-preview" style={{ display: 'block' }}>
          <img src={`file:///${hoveredImage.replace(/\\/g, '/')}`} alt="Preview" />
        </div>
      )}

      {/* ── Custom Titlebar ── */}
      <div className="custom-titlebar">
        <div className="titlebar-drag-region"></div>
        <div className="titlebar-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Manga AI Studio</span>
          {updateStatus && (
            <button
              onClick={() => setShowUpdateModal(true)}
              style={{
                background: updateStatus === 'error' ? 'var(--danger)' : 'var(--accent-primary)',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                padding: '2px 10px',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.3)'
              }}
            >
              🔄 {updateStatus === 'downloaded' ? 'Atualização Pronta!' : updateProgress ? `Atualizando (${Math.round(updateProgress.percent)}%)` : 'Atualização'}
            </button>
          )}
        </div>
        <div className="titlebar-controls">
          <button className="win-btn" title="Minimizar" onClick={handleMinimize}>🗕</button>
          <button className="win-btn" title="Maximizar" onClick={handleMaximize}>🗖</button>
          <button className="win-btn close" title="Fechar" onClick={handleClose}>✕</button>
        </div>
      </div>

      {showUpdateModal && updateStatus && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.75)',
          backdropFilter: 'blur(5px)',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            width: '480px',
            padding: '24px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                background: 'rgba(99, 102, 241, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '24px'
              }}>
                🚀
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-primary)' }}>Atualização de Software</h3>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {updateInfo?.version ? `Nova Versão v${updateInfo.version}` : 'Manga AI Studio Updater'}
                </span>
              </div>
            </div>

            <div style={{
              background: 'var(--bg-secondary)',
              padding: '14px',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              fontSize: '13px',
              color: 'var(--text-primary)'
            }}>
              {updateStatus === 'available' && "✨ Uma nova versão foi detectada! O download do instalador foi iniciado automaticamente em segundo plano."}
              {updateStatus === 'progress' && updateProgress && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontWeight: 'bold' }}>
                    <span>Baixando atualização...</span>
                    <span>{updateProgress.percent.toFixed(1)}%</span>
                  </div>
                  <div style={{
                    width: '100%',
                    height: '10px',
                    background: 'var(--bg-primary)',
                    borderRadius: '5px',
                    overflow: 'hidden',
                    border: '1px solid var(--border-color)'
                  }}>
                    <div style={{
                      width: `${Math.min(100, Math.max(0, updateProgress.percent))}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #6366f1, #a855f7)',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                    <span>{((updateProgress.transferred || 0) / 1048576).toFixed(1)} MB / {((updateProgress.total || 0) / 1048576).toFixed(1)} MB</span>
                    <span>Velocidade: {((updateProgress.bytesPerSecond || 0) / 1048576).toFixed(2)} MB/s</span>
                  </div>
                </div>
              )}
              {updateStatus === 'downloaded' && (
                <div style={{ color: 'var(--success)', fontWeight: 'bold' }}>
                  🎉 Download Concluído! O instalador está pronto para aplicar a nova versão com segurança.
                </div>
              )}
              {updateStatus === 'installing' && "⏳ Encerrando subprocessos e iniciando o instalador da nova versão... Por favor, aguarde."}
              {updateStatus === 'error' && (
                <div style={{ color: 'var(--danger)' }}>
                  ❌ Ocorreu um problema na verificação ou download da atualização: {updateError}
                </div>
              )}
            </div>

            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              {updateStatus === 'downloaded'
                ? "Clique em 'Reiniciar e Atualizar' para fechar o aplicativo e iniciar o processo automático de substituição."
                : "Você pode continuar usando o Manga AI Studio normalmente enquanto o download é preparado em segundo plano."}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
              {updateStatus === 'downloaded' ? (
                <>
                  <button
                    className="btn-secondary"
                    onClick={() => setShowUpdateModal(false)}
                    style={{ padding: '8px 16px', fontSize: '13px' }}
                  >
                    Lembrar Mais Tarde
                  </button>
                  <button
                    className="btn-primary"
                    onClick={() => {
                      setUpdateStatus('installing');
                      window.electronAPI.installUpdate();
                    }}
                    style={{ padding: '8px 18px', fontSize: '13px', fontWeight: 'bold' }}
                  >
                    🚀 Reiniciar e Atualizar Agora
                  </button>
                </>
              ) : (
                <button
                  className="btn-secondary"
                  onClick={() => setShowUpdateModal(false)}
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  {updateStatus === 'error' ? 'Fechar' : 'Minimizar para o Topo'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="app-body">
        {/* ── Sidebar Explorador ── */}
        {!isTheaterMode && (
          <aside className="app-sidebar fade-in-tab" style={{ width: sidebarWidth, minWidth: sidebarWidth, maxWidth: sidebarWidth }}>
            <div className="sidebar-header">
            <h3>EXPLORADOR</h3>
            <div style={{ display: 'flex', gap: '4px', marginLeft: 'auto' }}>
              <button 
                className={`btn-icon ${viewMode === 'list' ? 'active' : ''}`}
                style={{ opacity: viewMode === 'list' ? 1 : 0.5, padding: '4px', color: 'var(--text-main)' }}
                onClick={() => setViewMode('list')}
                title="Modo Lista"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
              </button>
              <button 
                className={`btn-icon ${viewMode === 'grid' ? 'active' : ''}`}
                style={{ opacity: viewMode === 'grid' ? 1 : 0.5, padding: '4px', color: 'var(--text-main)' }}
                onClick={() => setViewMode('grid')}
                title="Modo Galeria"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
              </button>
              <button 
                className="btn-process-image"
                style={{ opacity: 1, padding: '4px', fontSize: '14px', color: 'var(--text-muted)' }}
                onClick={(e) => {
                  e.stopPropagation();
                  navigateTo(currentPath);
                }}
                title="Atualizar pasta atual"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="23 4 23 10 17 10"></polyline>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
              </button>
            </div>
          </div>

          {/* Barra de navegação */}
          <div className="sidebar-nav-bar">
            <button
              className="sidebar-back-btn"
              onClick={handleGoUp}
              disabled={isAtRoot && !currentPath}
              title="Subir um nível"
            >
              ↑
            </button>
            <div className="sidebar-breadcrumb">
              {isAtRoot || !currentPath ? (
                <span className="breadcrumb-seg" style={{ pointerEvents: 'none', color: 'var(--text-main)' }}>
                  Este Computador
                </span>
              ) : (
                pathSegments.map((seg, idx) => (
                  <span key={idx} className="breadcrumb-chain">
                    <button
                      className="breadcrumb-seg"
                      onClick={() => handleBreadcrumbClick(idx)}
                    >
                      {seg}
                    </button>
                    {idx < pathSegments.length - 1 && (
                      <span className="breadcrumb-sep">›</span>
                    )}
                  </span>
                ))
              )}
            </div>
          </div>

          {/* Botão Processar Fila */}
          <div className="sidebar-actions">
            <button className="btn-explorer-action">▶ Processar Fila</button>
          </div>

          {/* Lista de pastas */}
          <div className={`sidebar-file-list ${viewMode}`}>
            {isLoading ? (
              <div className="sidebar-empty">
                <div className="sidebar-spinner"></div>
                <p>Carregando...</p>
              </div>
            ) : explorerError ? (
              <div className="sidebar-empty sidebar-error">
                <span>[AVISO]</span>
                <p>{explorerError}</p>
              </div>
            ) : entries.length === 0 ? (
              <div className="sidebar-empty">
                <span>🗂</span>
                <p>Pasta vazia</p>
              </div>
            ) : (
              entries.map((entry, index) => {
                if (entry.isImage) {
                  return (
                    <div
                      key={entry.path || index}
                      className="file-item is-image"
                      onClick={() => handleEntryClick(entry)}
                      onMouseEnter={() => setHoveredImage(entry.path)}
                      onMouseLeave={() => setHoveredImage(null)}
                      style={{ position: 'relative' }}
                    >
                      <div className="file-item-image-wrapper">
                        <img src={`file:///${entry.path.replace(/\\/g, '/')}`} className="explorer-thumbnail" alt="" loading="lazy" />
                      </div>
                      <span className="file-name">{entry.name}</span>
                      <button 
                        className="btn-process-image" 
                        title="Processar apenas esta imagem"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFolder(entry);
                          setActiveTab('processamento');
                        }}
                      >
                        ▶
                      </button>
                    </div>
                  );
                }

                const isExpanded = expandedFolder === entry.path;
                return (
                  <div key={entry.path || index} className="accordion-folder-container">
                    <div
                      className={`file-item ${selectedFolder?.path === entry.path ? 'active' : ''} ${entry.hasImages ? 'has-images' : ''}`}
                      onClick={(e) => handleEntryClick(entry, e)}
                      onDoubleClick={() => handleEntryDoubleClick(entry)}
                      title={
                        entry.isDrive
                          ? `Drive ${entry.name}`
                          : entry.hasImages
                            ? `📸 Clique na seta para ver opções. Duplo clique ou clique no nome para entrar.`
                            : `Clique para entrar na pasta`
                      }
                    >
                      {entry.hasImages && (
                        <>
                          <span className="accordion-checkbox"></span>
                          {entry.estado && entry.estado !== 'nenhum' && (
                            <span className={`accordion-status-dot ${
                              entry.estado === 'traduzido' ? 'green' :
                              entry.estado === 'corrigido' ? 'blue' :
                              'red'
                            }`}></span>
                          )}
                        </>
                      )}
                      
                      <span className="icon-folder">
                        {entry.isDrive ? '💽' : entry.hasImages ? '📁' : '📁'}
                      </span>
                      
                      <span 
                        className="file-name clickable-name"
                        onClick={(e) => {
                          if (entry.hasImages) {
                            e.stopPropagation();
                            navigateTo(entry.path);
                          }
                        }}
                      >
                        {entry.name}
                      </span>
                      
                      {entry.hasImages && (
                        <span 
                          className={`accordion-arrow ${isExpanded ? 'expanded' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedFolder(prev => prev === entry.path ? null : entry.path);
                          }}
                          title={isExpanded ? "Recolher opções" : "Expandir opções"}
                        >
                          ▼
                        </span>
                      )}
                    </div>

                    {entry.hasImages && isExpanded && (
                      <div className="accordion-body">
                        <button 
                          className="accordion-btn-action"
                          onClick={() => {
                            setSelectedFolder(entry);
                            setActiveTab('processamento');
                          }}
                        >
                          ⚙ Processar
                        </button>
                        <button 
                          className="accordion-btn-action"
                          onClick={() => {
                            setSelectedFolder(entry);
                            setIsEditorMode(true);
                            setActiveTab('estudio');
                          }}
                        >
                          Editor
                        </button>
                        <button 
                          className="accordion-btn-action"
                          onClick={() => {
                            setSelectedFolder(entry);
                            setIsEditorMode(false);
                            setActiveTab('estudio');
                          }}
                        >
                          Estúdio
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </aside>
        )}

        {/* ── Alça de Resize ── */}
        {!isTheaterMode && (
          <div
            className="sidebar-resize-handle"
            onMouseDown={onResizeMouseDown}
            title="Arraste para redimensionar o explorador"
          />
        )}

        {/* ── Conteúdo Principal ── */}
        <main className="app-main">
          <header className="app-header" style={{ display: isTheaterMode ? 'none' : 'flex', position: 'relative' }}>
            <nav className="top-tabs">
              <button 
                className={`tab-btn ${activeTab === 'processamento' ? 'active' : ''}`}
                onClick={() => setActiveTab('processamento')}
              >
                Processamento
              </button>

              <button 
                className={`tab-btn ${activeTab === 'biblioteca' ? 'active' : ''}`}
                onClick={() => setActiveTab('biblioteca')}
              >
                Biblioteca
              </button>

              {['estudio', 'modulos', 'configuracoes'].map(tab => {
                const labels = {
                  'estudio': 'Estúdio de Tradução',
                  'modulos': 'Central de Módulos',
                  'configuracoes': 'Configurações'
                };
                return (
                  <button
                    key={tab}
                    className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
                    onClick={() => setActiveTab(tab)}
                  >
                    {labels[tab]}
                  </button>
                );
              })}
            </nav>

            {/* ── Indicador Global Discreto na Aba Superior ── */}
            <div style={{ position: 'absolute', right: '20px', top: '16px', display: 'flex', flexDirection: 'column', gap: '8px', width: '200px', zIndex: 10 }}>
              {isGlobalRunning && activeTab !== 'processamento' && (
                <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: 'bold', color: 'var(--text-muted)' }}>
                    <span style={{ color: 'var(--brand-blue)' }}>⚡ Processando...</span>
                    <span>{Math.round(globalProgress)}%</span>
                  </div>
                  <div style={{ width: '100%', height: '4px', background: 'var(--bg-dark)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${globalProgress}%`, background: 'var(--brand-blue)', transition: 'width 0.3s ease' }} />
                  </div>
                </div>
              )}

              {Object.entries(downloadingModels).length > 0 && activeTab !== 'modulos' && (
                <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {Object.entries(downloadingModels).map(([model, data]) => (
                    <div key={model} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: 'bold', color: 'var(--text-muted)' }}>
                        <span style={{ color: 'var(--brand-blue)' }}>⬇ {model}</span>
                        <span>{Math.round(data.progress)}%</span>
                      </div>
                      <div style={{ width: '100%', height: '4px', background: 'var(--bg-dark)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${data.progress}%`, background: 'var(--brand-blue)', transition: 'width 0.3s ease' }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </header>

          <section className={`tab-content ${activeTab === 'estudio' ? 'tab-content--fullscreen' : ''}`}>
            <div className="fade-in-tab" style={{ display: activeTab === 'processamento' ? 'flex' : 'none', flexDirection: 'column' }}>
              <Processing initialInputPath={selectedFolder?.path} />
            </div>
            {activeTab === 'biblioteca' && (
              <div className="fade-in-tab" style={{ display: 'flex', flexDirection: 'column' }}>
                <Library />
              </div>
            )}
            {activeTab === 'estudio' && (
              <div className="fade-in-tab" style={{ display: 'flex', flexDirection: 'column' }}>
                <TranslationStudio
                  folderPath={selectedFolder?.path}
                  folderName={selectedFolder?.name}
                  isEditorMode={isEditorMode}
                  isPipelinePaused={isPipelinePaused}
                  isTheaterMode={isTheaterMode}
                  onToggleTheaterMode={() => setIsTheaterMode(!isTheaterMode)}
                />
              </div>
            )}
            <div className="fade-in-tab" style={{ display: activeTab === 'modulos' ? 'flex' : 'none', flexDirection: 'column' }}>
              <ModulesCenter />
            </div>
            {activeTab === 'configuracoes' && (
              <div className="fade-in-tab" style={{ display: 'flex', flexDirection: 'column' }}>
                <Settings onBaseFolderChange={(p) => navigateTo(p)} />
              </div>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
