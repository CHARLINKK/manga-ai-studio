import { useState, useRef, useCallback, useEffect } from 'react';
import './TranslationStudio.css';

const ZOOM_MIN = 20;
const ZOOM_MAX = 300;
const ZOOM_STEP = 10;

export default function TranslationStudio({ folderPath, folderName, isEditorMode, isPipelinePaused }) {
  const [pagesData, setPagesData] = useState({}); 
  const [imagesPaths, setImagesPaths] = useState({});
  const [pagesList, setPagesList] = useState([]);
  
  const [currentPage, setCurrentPage] = useState(null);
  const [txtPath, setTxtPath] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [savedFlash, setSavedFlash] = useState(false);

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
  const handleSave = async () => {
    if (!window.electronAPI || !txtPath) return;
    
    const res = await window.electronAPI.saveStudioData(txtPath, pagesData, isEditorMode);
    if (res.success) {
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 2000);
    } else {
      alert("Erro ao salvar: " + res.error);
    }
  };

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

  const handleSaveAndContinue = async () => {
    try {
      setIsResuming(true);
      await handleSave();
      if (window.electronAPI && window.electronAPI.resumePipeline) {
        await window.electronAPI.resumePipeline();
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
    setDraggedIndex(idx);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnter = (e, targetIdx) => {
    e.preventDefault();
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
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDraggedIndex(null);
  };

  const handleDragEnd = () => {
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

        <div className="toolbar-right">
          {isEditorMode && isPipelinePaused && (
            <button
              className="btn-save-studio"
              style={{ backgroundColor: '#d97706', borderColor: '#b45309', marginRight: '8px', opacity: isResuming ? 0.7 : 1 }}
              onClick={handleSaveAndContinue}
              disabled={isResuming}
            >
              {isResuming ? 'Retomando...' : 'Salvar e Continuar Processamento'}
            </button>
          )}
          <button
            className={`btn-save-studio ${savedFlash ? 'saved' : ''}`}
            onClick={handleSave}
          >
            {savedFlash ? '[OK] Salvo!' : (isEditorMode ? 'Apenas Salvar' : 'Salvar Tradução')}
          </button>
        </div>
      </div>

      <div className="studio-split-container">
        {/* ── Painel Esquerdo: Páginas ── */}
        <div className="studio-sidebar-pages">
          <div className="sidebar-pages-header">Páginas</div>
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
    </div>
  );
}
