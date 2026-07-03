import { useState, useEffect, useRef } from 'react';
import './Processing.css';

export default function Processing({ initialInputPath }) {
  const [inputPath, setInputPath] = useState(initialInputPath || '');
  const [outputPath, setOutputPath] = useState('');
  
  const loadSavedSteps = () => {
    const saved = localStorage.getItem('pipelineSteps');
    if (saved) {
      try {
        const p = JSON.parse(saved);
        return {
          ocr: p.ocr ?? true, pauseOcr: p.pauseOcr ?? false, vlmDirector: p.vlmDirector ?? false,
          correct: p.correct ?? true, pageDirector: p.pageDirector ?? true,
          translate: p.translate ?? false, exportBilingual: p.exportBilingual ?? false, openStudio: p.openStudio ?? true
        };
      } catch(e){}
    }
    return {
      ocr: true, pauseOcr: false, vlmDirector: false,
      correct: true, pageDirector: true,
      translate: false, exportBilingual: false, openStudio: true
    };
  };

  const [steps, setSteps] = useState(loadSavedSteps);
  const [tone, setTone] = useState(localStorage.getItem('pipelineTone') || 'Neutro');

  useEffect(() => {
    localStorage.setItem('pipelineSteps', JSON.stringify(steps));
  }, [steps]);

  useEffect(() => {
    localStorage.setItem('pipelineTone', tone);
  }, [tone]);
  const [dictGlobal, setDictGlobal] = useState('Macho Cooksan = Macho Cooksan\n');
  const [dictLocal, setDictLocal] = useState('');
  
  const [isEditorMode, setIsEditorMode] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [promptData, setPromptData] = useState(null);
  const [gpuName, setGpuName] = useState('GPU');
  const [consoleHeight, setConsoleHeight] = useState(() => {
    const saved = localStorage.getItem('pipelineConsoleHeight');
    const parsed = saved ? parseInt(saved, 10) : 280;
    return parsed < 260 ? 280 : Math.min(parsed, 600);
  });

  useEffect(() => {
    localStorage.setItem('pipelineConsoleHeight', consoleHeight);
  }, [consoleHeight]);

  const isDragging = useRef(false);
  const startY = useRef(0);
  const startHeight = useRef(280);

  const handleMouseDown = (e) => {
    isDragging.current = true;
    startY.current = e.clientY;
    startHeight.current = consoleHeight;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = 'none'; // Prevenir seleção de texto ao arrastar
  };

  const handleMouseMove = (e) => {
    if (!isDragging.current) return;
    const diff = startY.current - e.clientY;
    let newHeight = startHeight.current + diff;
    if (newHeight < 80) newHeight = 80;
    if (newHeight > 700) newHeight = 700;
    setConsoleHeight(newHeight);
  };

  const handleMouseUp = () => {
    isDragging.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = 'auto';
  };

  useEffect(() => {
    if (window.electronAPI && window.electronAPI.getGpuName) {
      window.electronAPI.getGpuName().then(name => {
        let short = name.replace(/NVIDIA /ig, '').replace(/GeForce /ig, '').replace(/AMD /ig, '').replace(/Radeon /ig, '').trim();
        setGpuName(short);
      });
    }
  }, []);
  const [progress, setProgress] = useState(0);
  const [consoleText, setConsoleText] = useState('');

  // Ler modelos do localStorage sincronizados com a Central de Módulos
  const [models, setModels] = useState(() => {
    const saved = localStorage.getItem('selectedAiModels');
    if (saved) {
      try {
        const p = JSON.parse(saved);
        return {
          corr: p.corr || p.transPol || 'llama3.1:8b',
          trans: p.trans || p.transPol || 'llama3.1:8b',
          vlm: p.vlm || 'qwen2.5vl:7b',
          ctx: p.ctx || 'llama3.1:8b'
        };
      } catch (e) {}
    }
    return {
      corr: 'llama3.1:8b',
      trans: 'llama3.1:8b',
      vlm: 'qwen2.5vl:7b',
      ctx: 'llama3.1:8b'
    };
  });

  useEffect(() => {
    const checkModels = () => {
      const saved = localStorage.getItem('selectedAiModels');
      if (saved) {
        try {
          const p = JSON.parse(saved);
          setModels({
            corr: p.corr || p.transPol || 'llama3.1:8b',
            trans: p.trans || p.transPol || 'llama3.1:8b',
            vlm: p.vlm || 'qwen2.5vl:7b',
            ctx: p.ctx || 'llama3.1:8b'
          });
        } catch(e){}
      }
    };
    checkModels();
    const interval = setInterval(checkModels, 1500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!window.electronAPI || !window.electronAPI.onPipelineLog) return;
    const cleanup = window.electronAPI.onPipelineLog((data) => {
      setConsoleText(prev => prev + data.text + '\n');
      if (data.progress !== null) {
        setProgress(data.progress);
      }
    });
    return () => cleanup();
  }, []);

  useEffect(() => {
    if (initialInputPath) {
      setInputPath(initialInputPath);
    }
  }, [initialInputPath]);

  async function handleStart() {
    setIsRunning(true);
    setProgress(0);
    setConsoleText(`[${new Date().toLocaleTimeString()}] Preparando para iniciar pipeline...\n`);

    const config = {
      inputPath, outputPath, steps, tone, dictGlobal, dictLocal, models
    };

    if (window.electronAPI && window.electronAPI.runPipeline) {
      const res = await window.electronAPI.runPipeline(config);
      if (res && res.success) {
        if (res.needsName) {
           setPromptData({ res, folderName: res.folderName });
           return; // Interrompe aqui, o modal cuidará do setIsRunning(false)
        } else if (res.existingName) {
           await window.electronAPI.finalizePipeline({ ...res, finalName: res.existingName });
           setConsoleText(prev => prev + `\n[OK] Auto-atualização: Biblioteca Central atualizada automaticamente!`);
        } else {
           setConsoleText(prev => prev + '\n[OK] Pipeline concluída com sucesso!');
        }
      } else if (res) {
        setConsoleText(prev => prev + '\n[ERRO] Falha na pipeline: ' + res.error);
      }
    }
    setIsRunning(false);
  }

  async function handleCancel() {
    if (window.electronAPI && window.electronAPI.cancelPipeline) {
      await window.electronAPI.cancelPipeline();
    }
    setIsRunning(false);
  }

  function handleReset() {
    setInputPath('');
    setOutputPath('');
    setDictLocal('');
    setProgress(0);
    setIsRunning(false);
    setConsoleText('');
  }

  async function handleBrowseInput() {
    if (window.electronAPI && window.electronAPI.selectFolder) {
      const p = await window.electronAPI.selectFolder();
      if (p) setInputPath(p);
    }
  }

  async function handleBrowseOutput() {
    if (window.electronAPI && window.electronAPI.selectFolder) {
      const p = await window.electronAPI.selectFolder();
      if (p) setOutputPath(p);
    }
  }

  return (
    <div className="processing-tab">
      
      {/* ── Inputs ───────────────────────────────────────────────────────── */}
      <div className="path-rows">
        <div className="path-row">
          <label>Pasta ou Arquivo:</label>
          <input 
            type="text" 
            placeholder="Caminho da imagem ou da pasta do capítulo..." 
            value={inputPath}
            onChange={e => setInputPath(e.target.value)}
          />
          <button className="btn-browse" onClick={handleBrowseInput}>Procurar...</button>
        </div>
        <div className="path-row">
          <label>Pasta de Saída:</label>
          <input 
            type="text" 
            placeholder="Opcional. Se vazio, salva ao lado da original."
            value={outputPath}
            onChange={e => setOutputPath(e.target.value)}
          />
          <button className="btn-browse" onClick={handleBrowseOutput}>Procurar...</button>
        </div>
      </div>

      {/* ── Grid Central ─────────────────────────────────────────────────── */}
      <div className="processing-grid">
        
        {/* Coluna Esquerda: Etapas */}
        <div className="col-steps">
          <h4>Etapas de Processamento:</h4>
          
          <div className="steps-list">
            {/* Etapa 1 */}
            <div className="step-section">
              <label className="checkbox-label step-title">
                <input type="checkbox" checked={steps.ocr} onChange={e => setSteps({...steps, ocr: e.target.checked})} />
                <span>1. Extrair Texto Bruto (GPU)</span>
              </label>
              <div className="step-options">
                <label className="checkbox-label">
                  <input type="checkbox" checked={steps.pauseOcr} disabled={!steps.ocr} onChange={e => setSteps({...steps, pauseOcr: e.target.checked})} />
                  <span>Pausar após OCR (Ir para Editor OCR)</span>
                </label>
                <label className="checkbox-label" title="Utiliza modelo de visão para ordenar balões e filtrar onomatopeias">
                  <input type="checkbox" checked={steps.vlmDirector} disabled={!steps.ocr} onChange={e => setSteps({...steps, vlmDirector: e.target.checked})} />
                  <span>Ativar Diretor Visual (VLM Geométrico)</span>
                </label>
              </div>
            </div>

            <div className="step-divider" />

            {/* Etapa 2 */}
            <div className="step-section">
              <label className="checkbox-label step-title">
                <input type="checkbox" checked={steps.correct} onChange={e => setSteps({...steps, correct: e.target.checked})} />
                <span>2. Polir Texto Extraído (IA Local)</span>
              </label>
              <div className="step-options">
                <label className="checkbox-label">
                  <input type="checkbox" checked={steps.pageDirector} onChange={e => setSteps({...steps, pageDirector: e.target.checked})} />
                  <span>2.5. Analisar Contexto da Cena (Page Director)</span>
                </label>
              </div>
            </div>

            <div className="step-divider" />

            {/* Etapa 3 */}
            <div className="step-section">
              <label className="checkbox-label step-title">
                <input type="checkbox" checked={steps.translate} onChange={e => setSteps({...steps, translate: e.target.checked})} />
                <span>3. Traduzir para PT-BR (IA Local)</span>
              </label>
              <div className="step-options">
                <label className="checkbox-label">
                  <input type="checkbox" checked={steps.exportBilingual} disabled={!steps.translate} onChange={e => setSteps({...steps, exportBilingual: e.target.checked})} />
                  <span>Exportar Formato Bilíngue [EN/PTBR]</span>
                </label>
                <label className="checkbox-label">
                  <input type="checkbox" checked={steps.openStudio} disabled={!steps.translate} onChange={e => setSteps({...steps, openStudio: e.target.checked})} />
                  <span>Abrir Estúdio de Tradução após finalizar</span>
                </label>
              </div>
            </div>

            <div className="step-divider" />

            {/* Tom da Tradução */}
            <div className="tone-row">
              <span className="tone-label">Tom da Tradução:</span>
              <div className="tone-toggle-group">
                {['Formal', 'Neutro', 'Informal'].map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`tone-btn ${tone === t ? 'active' : ''}`}
                    onClick={() => setTone(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
          
          <div className="status-indicators mt-auto">
            <span className="status-on">{gpuName}: [ON]</span>
            <span className="status-on">RAG: [ON]</span>
          </div>
        </div>

        {/* Coluna Direita: Dicionários */}
        <div className="col-dicts">
          <div className="dict-box">
            <h4>Dicionário Global Permanente:</h4>
            <textarea 
              value={dictGlobal}
              onChange={e => setDictGlobal(e.target.value)}
              className="dict-textarea"
            />
          </div>
          
          <div className="dict-box mt-3">
            <h4>Dicionário Temporário (Exclusivo da fila atual):</h4>
            <textarea 
              value={dictLocal}
              onChange={e => setDictLocal(e.target.value)}
              className="dict-textarea"
            />
          </div>
        </div>
      </div>

      <div className="processing-footer">
        {/* ── Botões de Ação ──────────────────────────────────────────────────────── */}
        <div className="action-bar">
          <button className="btn-start" onClick={handleStart} disabled={isRunning}>
            INICIAR PROCESSAMENTO
          </button>
          <button className="btn-reset" onClick={handleReset} disabled={isRunning}>Limpar</button>
          <button className="btn-cancel" onClick={handleCancel} disabled={!isRunning}>CANCELAR</button>
        </div>

        {/* ── Progresso ─────────────────────────────────────────────────────────────── */}
        <div className="progress-bar-container">
          <div className="progress-fill" style={{ width: `${progress}%` }}></div>
        </div>

      {promptData && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
          <div style={{ background: '#1c1e26', padding: '24px', borderRadius: '8px', width: '400px', border: '1px solid #333', boxShadow: '0 4px 20px rgba(0,0,0,0.5)' }}>
            <h3 style={{ marginTop: 0, color: '#fff' }}>Processamento Concluído</h3>
            <p style={{ fontSize: '14px', color: '#a3a3a3', marginBottom: '16px' }}>Digite o nome do capítulo para salvá-lo na Biblioteca Central:</p>
            <input 
              type="text" 
              defaultValue={promptData.folderName} 
              id="finalNameInput"
              autoFocus
              style={{ width: '100%', padding: '10px', background: '#0d0e12', color: '#fff', border: '1px solid #444', borderRadius: '4px', marginBottom: '20px', fontSize: '14px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                className="btn-secondary"
                onClick={() => {
                  setConsoleText(prev => prev + `\n[AVISO] Exportação cancelada. O arquivo ficou apenas na pasta Temp.`);
                  setPromptData(null);
                  setIsRunning(false);
                }}
              >
                Cancelar
              </button>
              <button 
                className="btn-primary"
                onClick={async () => {
                  const input = document.getElementById('finalNameInput');
                  const finalName = input ? (input.value || promptData.folderName) : promptData.folderName;
                  await window.electronAPI.finalizePipeline({ ...promptData.res, finalName });
                  setConsoleText(prev => prev + `\n[OK] Salvo na Biblioteca Central e na pasta original como: ${finalName}.txt`);
                  setPromptData(null);
                  setIsRunning(false);
                }}
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resizer Handle */}
      <div 
        className="console-resizer" 
        onMouseDown={handleMouseDown}
        title="Arraste para redimensionar o console"
      >
        <div className="resizer-bar"></div>
      </div>

      {/* Console */}
      <div className="classic-console" style={{ height: consoleHeight }}>
        <textarea 
          className="console-textarea" 
          readOnly 
          value={consoleText} 
          ref={(textarea) => { if (textarea) textarea.scrollTop = textarea.scrollHeight; }}
        />
      </div>
      </div>

    </div>
  );
}
