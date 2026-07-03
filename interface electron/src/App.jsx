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

  // ── Auto-Updater ─────────────────────────────────────────────────────────
  const [updateStatus, setUpdateStatus] = useState(null); // 'available', 'progress', 'downloaded', 'error'
  const [updateProgress, setUpdateProgress] = useState(null);
  const [updateError, setUpdateError] = useState(null);

  useEffect(() => {
    if (window.electronAPI && window.electronAPI.onUpdaterStatus) {
      const cleanup = window.electronAPI.onUpdaterStatus((data) => {
        setUpdateStatus(data.status);
        if (data.status === 'progress') setUpdateProgress(data.progress);
        if (data.status === 'error') setUpdateError(data.error);
      });
      return cleanup;
    }
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

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      cleanupPaused();
      cleanupResumed();
      cleanupFinished();
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

  return (
    <div className="app-container dark-theme">

      {/* ── Custom Titlebar ── */}
      <div className="custom-titlebar">
        <div className="titlebar-drag-region"></div>
        <div className="titlebar-title">Manga AI Studio</div>
        <div className="titlebar-controls">
          <button className="win-btn" title="Minimizar" onClick={handleMinimize}>🗕</button>
          <button className="win-btn" title="Maximizar" onClick={handleMaximize}>🗖</button>
          <button className="win-btn close" title="Fechar" onClick={handleClose}>✕</button>
        </div>
      </div>

      {updateStatus && (
        <div className="update-banner" style={{ background: updateStatus === 'error' ? 'var(--danger)' : 'var(--accent-primary)', color: 'white', padding: '8px', textAlign: 'center', fontSize: '12px', zIndex: 9999 }}>
          {updateStatus === 'available' && "✨ Nova versão disponível! Baixando em segundo plano..."}
          {updateStatus === 'progress' && updateProgress && `Baixando atualização: ${Math.round(updateProgress.percent)}%`}
          {updateStatus === 'downloaded' && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '15px' }}>
              <span>🚀 Atualização pronta para instalar!</span>
              <button 
                onClick={() => window.electronAPI.installUpdate()} 
                style={{ padding: '4px 10px', background: 'white', color: 'var(--accent-primary)', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
              >
                Reiniciar e Atualizar
              </button>
            </div>
          )}
          {updateStatus === 'error' && `Erro na atualização: ${updateError}`}
        </div>
      )}

      <div className="app-body">
        {/* ── Sidebar Explorador ── */}
        <aside className="app-sidebar" style={{ width: sidebarWidth, minWidth: sidebarWidth, maxWidth: sidebarWidth }}>
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
              entries.map((entry, idx) => {
                if (entry.isImage) {
                  return (
                    <div
                      key={entry.path || idx}
                      className="file-item is-image"
                      onClick={() => handleEntryClick(entry)}
                      style={{ position: 'relative' }}
                    >
                      <div className="file-item-image-wrapper">
                        <img src={`file:///${entry.path.replace(/\\/g, '/')}`} className="explorer-thumbnail" alt="" />
                        <div className="explorer-image-preview">
                          <img src={`file:///${entry.path.replace(/\\/g, '/')}`} alt="" />
                        </div>
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
                  <div key={entry.path || idx} className="accordion-folder-container">
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
                            e.stopPropagation(); // Não alterna o acordeão se clicou no nome
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

        {/* ── Alça de Resize ── */}
        <div
          className="sidebar-resize-handle"
          onMouseDown={onResizeMouseDown}
          title="Arraste para redimensionar o explorador"
        />

        {/* ── Conteúdo Principal ── */}
        <main className="app-main">
          <header className="app-header">
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
          </header>

          <section className={`tab-content ${activeTab === 'estudio' ? 'tab-content--fullscreen' : ''}`}>
            <div style={{ display: activeTab === 'processamento' ? 'flex' : 'none', flexDirection: 'column', height: '100%', width: '100%' }}>
              <Processing initialInputPath={selectedFolder?.path} />
            </div>
            {activeTab === 'biblioteca' && (
              <Library />
            )}
            {activeTab === 'estudio' && (
              <TranslationStudio
                folderPath={selectedFolder?.path}
                folderName={selectedFolder?.name}
                isEditorMode={isEditorMode}
                isPipelinePaused={isPipelinePaused}
              />
            )}
            <div style={{ display: activeTab === 'modulos' ? 'flex' : 'none', flexDirection: 'column', height: '100%', width: '100%' }}>
              <ModulesCenter />
            </div>
            {activeTab === 'configuracoes' && <Settings onBaseFolderChange={(p) => navigateTo(p)} />}
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
