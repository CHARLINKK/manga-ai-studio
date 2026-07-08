import { useState, useRef, useCallback, useEffect } from 'react';
import './TranslationStudio.css';

const ZOOM_MIN = 20;
const ZOOM_MAX = 300;
const ZOOM_STEP = 10;

export default function TranslationStudio({ folderPath, folderName, isEditorMode, isPipelinePaused, isTheaterMode, onToggleTheaterMode, onContinueProcessing }) {
  const [pagesData, setPagesData] = useState({}); 
  const [imagesPaths, setImagesPaths] = useState({});
  const [pagesList, setPagesList] = useState([]);
  
  const [currentPage, setCurrentPage] = useState(null);
  const [txtPath, setTxtPath] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [savedFlash, setSavedFlash] = useState(false);
  const [lastSavedTime, setLastSavedTime] = useState(null);

  // Sincroniza refs para uso em listeners globais
  const stateRef = useRef({ pagesData, txtPath, isEditorMode, currentPage, pagesList });
  useEffect(() => {
    stateRef.current = { pagesData, txtPath, isEditorMode, currentPage, pagesList };
  }, [pagesData, txtPath, isEditorMode, currentPage, pagesList]);

  // Canvas / Pan & Zoom
  const [zoom, setZoom] = useState(40);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const dragStart = useRef({ x: 0, y: 0 });
  const canvasRef = useRef(null);
  const textareaRefs = useRef({});

  // Local dictionary
  const [dictionaryText, setDictionaryText] = useState('');

  // ── Carregar Dados do Estúdio ─────────────────────────────────────────────
  useEffect(() => {
    if (!folderPath) {
      setPagesData({});
      setImagesPaths({});
      setPagesList([]);
      setCurrentPage(null);
      setTxtPath(null);
      return;
    }

    const load = async () => {
      setIsLoading(true);
      setErrorMsg('');
      if (window.electronAPI && window.electronAPI.loadStudioData) {
        const result = await window.electronAPI.loadStudioData(folderPath, isEditorMode);
        if (result.success) {
          const { pagesOriginal, pagesTranslated } = result.data;
          const mergedData = {};
          
          const allKeys = new Set([...Object.keys(pagesOriginal), ...Object.keys(pagesTranslated)]);
          
          allKeys.forEach(page => {
            const origArr = pagesOriginal[page] || [];
            const transArr = pagesTranslated[page] || [];
            const maxLen = Math.max(origArr.length, transArr.length);
            mergedData[page] = [];
            for (let i = 0; i < maxLen; i++) {
              mergedData[page].push({
                id: Math.random().toString(36).substr(2, 9),
                original: origArr[i] || '',
                translated: transArr[i] || ''
              });
            }
          });

          setPagesData(mergedData);
          setImagesPaths(result.imagesPaths);
          setTxtPath(result.txtPath);

          let availablePages = Object.keys(result.imagesPaths);
          if (availablePages.length === 0) {
            availablePages = Array.from(allKeys).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
          }
          setPagesList(availablePages);
          
          if (availablePages.length > 0) {
            setCurrentPage(availablePages[0]);
          }
        } else {
          setErrorMsg(result.error);
        }
      }
      setIsLoading(false);
    };

    load();
  }, [folderPath, isEditorMode]);

  // ── Salvar ────────────────────────────────────────────────────────────────
  const handleSave = useCallback(async (showFlash = true) => {
    const { txtPath, pagesData, isEditorMode } = stateRef.current;
    if (!window.electronAPI || !txtPath) return;
    
    const res = await window.electronAPI.saveStudioData(txtPath, pagesData, isEditorMode);
    if (res.success) {
      const now = new Date();
      setLastSavedTime(`${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`);
      if (showFlash) {
        setSavedFlash(true);
        setTimeout(() => setSavedFlash(false), 2000);
      }
    } else {
      if (showFlash) alert("Erro ao salvar: " + res.error);
    }
  }, []);

  // ── Auto-Save & Hotkeys ───────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleSave(true);
      }
      if (e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'INPUT') {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          const { pagesList, currentPage } = stateRef.current;
          if (!pagesList.length || !currentPage) return;
          const idx = pagesList.indexOf(currentPage);
          if (e.key === 'ArrowRight' && idx < pagesList.length - 1) {
            setCurrentPage(pagesList[idx + 1]);
            setPan({ x: 0, y: 0 });
          } else if (e.key === 'ArrowLeft' && idx > 0) {
            setCurrentPage(pagesList[idx - 1]);
            setPan({ x: 0, y: 0 });
          }
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave]);

  useEffect(() => {
    const interval = setInterval(() => handleSave(false), 120000); // 2 mins
    return () => clearInterval(interval);
  }, [handleSave]);

  useEffect(() => {
    handleSave(false); // auto-save on page change
  }, [currentPage, handleSave]);

  // 🖲️ Pan e Zoom 🖲️
  const handleWheel = (e) => {
    const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
    setZoom(z => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z + delta)));
  };

  const handleMouseDown = (e) => {
    if (e.button === 0) {
      setIsDragging(true);
      dragStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  // ── Modificadores de Texto ────────────────────────────────────────────────
  const updateBlock = (index, field, value) => {
    setPagesData(prev => {
      const newData = { ...prev };
      const blocks = [...(newData[currentPage] || [])];
      blocks[index] = { ...blocks[index], [field]: value };
      newData[currentPage] = blocks;
      return newData;
    });
  };

  const addBlock = () => {
    setPagesData(prev => {
      const newData = { ...prev };
      const blocks = [...(newData[currentPage] || [])];
      blocks.push({ id: Math.random().toString(36).substr(2, 9), original: '', translated: '' });
      newData[currentPage] = blocks;
      return newData;
    });
  };

  const [isResuming, setIsResuming] = useState(false);
  const [showConfirmOverwrite, setShowConfirmOverwrite] = useState(false);

  const handleSaveAndContinue = async () => {
    try {
      setIsResuming(true);
      await handleSave();
      let resumed = false;
      if (window.electronAPI && window.electronAPI.resumePipeline) {
        resumed = await window.electronAPI.resumePipeline();
      }
      if (!resumed && onContinueProcessing) {
        setShowConfirmOverwrite(true);
      }
    } finally {
      setIsResuming(false);
    }
  };

  const autoResize = (el) => {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = (el.scrollHeight + 12) + 'px';
  };

  const resizeAllTextareas = () => {
    Object.values(textareaRefs.current).forEach(el => {
      if (el) autoResize(el);
    });
  };

  // Ajusta todos os textareas quando a página muda, modo de editor muda ou os dados carregam
  useEffect(() => {
    resizeAllTextareas();
    const timer1 = setTimeout(resizeAllTextareas, 20);
    const timer2 = setTimeout(resizeAllTextareas, 150);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [pagesData, currentPage, isEditorMode]);

  const deleteBlock = (index) => {
    setPagesData(prev => {
      const newData = { ...prev };
      const blocks = [...(newData[currentPage] || [])];
      blocks.splice(index, 1);
      newData[currentPage] = blocks;
      return newData;
    });
  };

  // 🖱️ Drag and Drop Vivo (Swap) 🖱️
  const handleDragStart = (e, idx) => {
    e.stopPropagation();
    setDraggedIndex(idx);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnter = (e, targetIdx) => {
    e.preventDefault();
    e.stopPropagation();
    if (draggedIndex === null || draggedIndex === targetIdx) return;

    setPagesData(prev => {
      const newData = { ...prev };
      const blocks = [...(newData[currentPage] || [])];
      
      const item = blocks.splice(draggedIndex, 1)[0];
      blocks.splice(targetIdx, 0, item);
      
      newData[currentPage] = blocks;
      return newData;
    });
    setDraggedIndex(targetIdx); // Atualiza o índice para seguir a posição
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDraggedIndex(null);
  };

  const handleDragEnd = (e) => {
    if (e && e.stopPropagation) e.stopPropagation();
    setDraggedIndex(null);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  if (!folderPath) {
    return (
      <div className="translation-studio studio-empty">
        <div className="studio-empty-icon">📂</div>
        <h2>Nenhum capítulo aberto</h2>
        <p>Selecione uma pasta no <strong>Explorador</strong> à esquerda e clique em <strong>Editor</strong> ou <strong>Estúdio</strong>.</p>
      </div>
    );
  }

  if (isLoading) {
    return <div className="translation-studio studio-empty"><div className="canvas-spinner" /></div>;
  }

  if (errorMsg) {
    return (
      <div className="translation-studio studio-empty">
        <div className="studio-empty-icon">[ERRO]</div>
        <h2>Erro ao carregar estúdio</h2>
        <p>{errorMsg}</p>
      </div>
    );
  }

  const currentBlocks = pagesData[currentPage] || [];
  const currentImageUrl = currentPage ? imagesPaths[currentPage] : null;

  return (
    <div className="translation-studio">
      {/* ── Toolbar ── */}
      <div className="studio-toolbar" style={{ backgroundColor: isEditorMode ? 'var(--bg-panel)' : '#0d1f14' }}>
        <div className="toolbar-left" style={{ gap: '16px' }}>
          <h3 style={{ margin: 0, color: isEditorMode ? '#60a5fa' : '#34d399', letterSpacing: '1px' }}>
            {isEditorMode ? '📝 EDITOR OCR' : '🌍 ESTÚDIO DE TRADUÇÃO'}
          </h3>
          <span className="folder-name" style={{ color: 'var(--text-muted)' }}>{folderName}</span>
        </div>

        <div className="toolbar-right" style={{ display: 'flex', gap: '8px' }}>
          <button
            className="btn-save-studio"
            style={{ backgroundColor: 'transparent', border: '1px solid var(--border-subtle)', color: 'var(--text-main)' }}
            onClick={onToggleTheaterMode}
            title="Alternar Modo Teatro (Tela Cheia)"
          >
            {isTheaterMode ? 'Sair do Modo Teatro' : 'Modo Teatro'}
          </button>
          {isEditorMode && (
            <button
              className="btn-save-studio"
              style={{ backgroundColor: '#d97706', borderColor: '#b45309', opacity: isResuming ? 0.7 : 1 }}
              onClick={handleSaveAndContinue}
              disabled={isResuming}
              title="Salva as edições do OCR e inicia as etapas seguintes da pipeline (Correção/Tradução)"
            >
              {isResuming ? 'Iniciando...' : 'Salvar e Continuar Processamento'}
            </button>
          )}
          {lastSavedTime && (
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', marginRight: '8px', fontStyle: 'italic' }}>
              Auto-salvo às {lastSavedTime}
            </span>
          )}
          <button
            className={`btn-save-studio ${savedFlash ? 'saved' : ''}`}
            onClick={() => handleSave(true)}
            title="Atalho: Ctrl + S"
          >
            {savedFlash ? '[OK] Salvo!' : (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {isEditorMode ? 'Apenas Salvar' : 'Salvar Tradução'}
                <kbd style={{ fontSize: '10px', background: 'rgba(255,255,255,0.2)', padding: '2px 5px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>Ctrl+S</kbd>
              </span>
            )}
          </button>
        </div>
      </div>

      <div className="studio-split-container">
        {/* ── Painel Esquerdo: Páginas ── */}
        <div className="studio-sidebar-pages">
          <div className="sidebar-pages-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Páginas</span>
            <div style={{ display: 'flex', gap: '4px' }}>
              <kbd style={{ fontSize: '9px', background: 'var(--bg-dark)', color: 'var(--text-muted)', padding: '2px 4px', borderRadius: '3px', border: '1px solid var(--border-subtle)' }}>←</kbd>
              <kbd style={{ fontSize: '9px', background: 'var(--bg-dark)', color: 'var(--text-muted)', padding: '2px 4px', borderRadius: '3px', border: '1px solid var(--border-subtle)' }}>→</kbd>
            </div>
          </div>
          <div className="sidebar-pages-list">
            {pagesList.map(page => {
              const hasText = pagesData[page] && pagesData[page].length > 0 && pagesData[page].some(b => b.original.trim() || b.translated.trim());
              return (
                <button
                  key={page}
                  className={`page-nav-btn ${currentPage === page ? 'active' : ''}`}
                  onClick={() => {
                    setCurrentPage(page);
                    setPan({ x: 0, y: 0 });
                  }}
                >
                  <span className={`page-dot ${hasText ? 'has-text' : ''}`} />
                  <span className="page-name">{page}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Painel Central: Imagem ── */}
        <div 
          className="studio-canvas-area" 
          ref={canvasRef} 
          onMouseDown={handleMouseDown} 
          onMouseMove={handleMouseMove} 
          onMouseUp={handleMouseUp} 
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        >
          <div className="canvas-controls">
            <span className="zoom-hint">Scroll para Zoom. Clique e Arraste para Pan.</span>
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <button className="btn-icon sm" onClick={() => setZoom(z => Math.max(ZOOM_MIN, z - ZOOM_STEP))}>-</button>
              <span className="zoom-pill" style={{ padding: '2px 8px' }}>{zoom}%</span>
              <button className="btn-icon sm" onClick={() => setZoom(z => Math.min(ZOOM_MAX, z + ZOOM_STEP))}>+</button>
              <button className="btn-icon sm" onClick={() => { setZoom(100); setPan({x:0, y:0}); }}>Reset</button>
            </div>
          </div>
          
          <div className="canvas-viewport">
            {currentImageUrl ? (
              <img
                src={currentImageUrl}
                alt={currentPage}
                draggable={false}
                style={{
                  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom / 100})`,
                  transformOrigin: 'center center',
                  cursor: isDragging ? 'grabbing' : 'grab',
                  transition: isDragging ? 'none' : 'transform 0.1s',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
                  maxWidth: '100%',
                  objectFit: 'contain'
                }}
              />
            ) : (
              <div className="canvas-loading">Imagem não encontrada</div>
            )}
          </div>
        </div>

        {/* ── Painel Direito: Textos ── */}
        <div className="studio-editor-panel">
          
          <div className="editor-fixed-header">
            <label className="editor-label" style={{ marginTop: '12px' }}>
              {isEditorMode ? 'Texto OCR (Extraído):' : 'Tradução:'}
            </label>
          </div>

          <div className="editor-blocks-scroll">
            {currentBlocks.map((block, idx) => (
              <div 
                key={block.id || idx} 
                className={`studio-text-block ${draggedIndex === idx ? 'dragging' : ''}`}
                draggable
                onDragStart={(e) => handleDragStart(e, idx)}
                onDragEnter={(e) => handleDragEnter(e, idx)}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onDragEnd={handleDragEnd}
              >
                <div className="block-header">
                  <span className="block-index">#{idx + 1}</span>
                  <button className="btn-delete-block" onClick={() => deleteBlock(idx)}>✖</button>
                </div>
                {!isEditorMode && (
                  <div className="reference-text">
                    <label>Texto OCR:</label>
                    <div className="ref-content">{block.original}</div>
                  </div>
                )}
                <textarea
                  ref={el => textareaRefs.current[idx] = el}
                  className="studio-textarea"
                  style={{ overflow: 'hidden', resize: 'none' }}
                  value={isEditorMode ? block.original : block.translated}
                  onChange={(e) => {
                    updateBlock(idx, isEditorMode ? 'original' : 'translated', e.target.value);
                    autoResize(e.target);
                  }}
                  placeholder={isEditorMode ? "Texto bruto..." : "Sua tradução aqui..."}
                />
              </div>
            ))}
            
            <button className="btn-add-block" onClick={addBlock}>
              + Adicionar Bloco de Texto
            </button>
          </div>

          <div className="editor-dict-area">
            <label className="editor-label">Dicionário Temporário:</label>
            <textarea
              className="dict-textarea"
              value={dictionaryText}
              onChange={e => setDictionaryText(e.target.value)}
            />
          </div>

        </div>
      </div>

      {showConfirmOverwrite && (
        <div className="modal-overlay" onClick={() => setShowConfirmOverwrite(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()} style={{ maxWidth: '480px', padding: '26px' }}>
            <h3 style={{ marginTop: 0, color: '#fff', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ color: '#EAB308' }}>⚠️</span> Reprocessar e Sobrescrever?
            </h3>
            <p style={{ fontSize: '14px', color: '#d4d4d4', lineHeight: '1.6', margin: '14px 0' }}>
              Você solicitou continuar o processamento para este capítulo.
            </p>
            <p style={{ fontSize: '13px', color: '#a3a3a3', lineHeight: '1.5', margin: '0 0 22px 0', backgroundColor: 'rgba(234, 179, 8, 0.08)', borderLeft: '3px solid #EAB308', padding: '12px 14px', borderRadius: '4px' }}>
              Deseja executar novamente as etapas de IA (Polimento de Inglês, Diretor de Cena e Tradução PT-BR) e <strong>sobrescrever os arquivos anteriores</strong> usando o texto original salvo?
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button 
                className="btn-secondary"
                style={{ padding: '9px 18px', borderRadius: '6px', border: '1px solid #404040', background: '#262626', color: '#ccc', cursor: 'pointer', fontWeight: '500' }}
                onClick={() => setShowConfirmOverwrite(false)}
              >
                Cancelar
              </button>
              <button
                className="btn-primary"
                style={{ padding: '9px 20px', borderRadius: '6px', border: 'none', background: 'linear-gradient(135deg, #EAB308 0%, #CA8A04 100%)', color: '#000', fontWeight: 'bold', cursor: 'pointer' }}
                onClick={() => {
                  setShowConfirmOverwrite(false);
                  if (onContinueProcessing) {
                    onContinueProcessing(folderPath, true);
                  }
                }}
              >
                Sim, Sobrescrever e Reprocessar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
