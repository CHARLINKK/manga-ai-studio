import { useState, useEffect } from 'react';
import './ModulesCenter.css';

const AVAILABLE_MODELS = {
  vlm: ['qwen2.5vl:7b', 'llama3.2-vision:11b', 'llava:13b'],
  trans: ['llama3.1:8b', 'gemma2:9b', 'mistral-nemo:12b'],
  ctx: ['llama3.1:8b', 'phi3:latest', 'qwen2.5:7b']
};

export default function ModulesCenter() {
  const [statuses, setStatuses] = useState({
    ocr: { state: 'verifying', progress: 0 },
    cuda: { state: 'verifying', progress: 0 },
    ollama: { state: 'verifying', progress: 0 },
    rag: { state: 'verifying', progress: 0 }
  });

  const [ollamaModels, setOllamaModels] = useState([]);
  const [downloading, setDownloading] = useState({});
  const [isChecking, setIsChecking] = useState(false);

  const [models, setModels] = useState(() => {
    const saved = localStorage.getItem('selectedAiModels');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return {
          vlm: parsed.vlm || AVAILABLE_MODELS.vlm[0],
          transPol: parsed.transPol || parsed.trans || AVAILABLE_MODELS.trans[0],
          ctx: parsed.ctx || AVAILABLE_MODELS.ctx[0]
        };
      } catch (e) {}
    }
    return {
      vlm: AVAILABLE_MODELS.vlm[0],
      transPol: AVAILABLE_MODELS.trans[0],
      ctx: AVAILABLE_MODELS.ctx[0]
    };
  });

  useEffect(() => {
    const toSave = {
      vlm: models.vlm,
      transPol: models.transPol,
      corr: models.transPol,
      trans: models.transPol,
      ctx: models.ctx
    };
    localStorage.setItem('selectedAiModels', JSON.stringify(toSave));
  }, [models]);

  const checkStatus = async () => {
    setIsChecking(true);
    if (window.electronAPI && window.electronAPI.checkModulesStatus) {
      const res = await window.electronAPI.checkModulesStatus();
      setStatuses({
        ocr: res.ocr,
        cuda: res.cuda,
        ollama: res.ollama,
        rag: res.rag
      });
      setOllamaModels(res.ollamaModels || []);
    }
    setTimeout(() => setIsChecking(false), 500);
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 5000); // Check periodically
    
    if (window.electronAPI && window.electronAPI.onOllamaProgress) {
      const cleanupOllama = window.electronAPI.onOllamaProgress((data) => {
        setDownloading(prev => ({
          ...prev,
          [data.model]: { progress: data.progress, text: data.text }
        }));
        if (data.progress >= 100) {
          setTimeout(() => {
            setDownloading(prev => {
              const nd = {...prev};
              delete nd[data.model];
              return nd;
            });
            checkStatus();
          }, 1000);
        }
      });

      const cleanupVenv = window.electronAPI.onVenvProgress((data) => {
        setDownloading(prev => ({
          ...prev,
          [data.envName]: { progress: data.progress, text: data.text }
        }));
        if (data.progress >= 100) {
          setTimeout(() => {
            setDownloading(prev => {
              const nd = {...prev};
              delete nd[data.envName];
              return nd;
            });
            checkStatus();
          }, 3000);
        }
      });

      return () => {
        clearInterval(interval);
        cleanupOllama();
        cleanupVenv();
      };
    }
    return () => clearInterval(interval);
  }, []);

  const getModelStatus = (modelName) => {
    if (downloading[modelName]) return { state: 'downloading', progress: downloading[modelName].progress, text: downloading[modelName].text };
    if (statuses.ollama.state !== 'installed_and_running') return { state: 'not_installed', progress: 0 };
    if (ollamaModels.includes(modelName)) return { state: 'installed', progress: 100 };
    return { state: 'not_installed', progress: 0 };
  };

  const pullModel = async (modelName) => {
    if (statuses.ollama.state !== 'installed_and_running') {
       if (statuses.ollama.state === 'installed_but_closed') {
           await window.electronAPI.startOllamaServer();
           await new Promise(r => setTimeout(r, 2000));
           await checkStatus();
       } else {
           if (window.electronAPI && window.electronAPI.openOllamaSite) window.electronAPI.openOllamaSite();
           return;
       }
    }
    setDownloading(prev => ({ ...prev, [modelName]: { progress: 0, text: 'Iniciando download...' } }));
    if (window.electronAPI && window.electronAPI.pullOllamaModel) {
      const result = await window.electronAPI.pullOllamaModel(modelName);
      if (!result || !result.success) {
        setDownloading(prev => {
          const nd = {...prev};
          delete nd[modelName];
          return nd;
        });
        window.alert(`O download do modelo ${modelName} falhou ou foi interrompido.`);
      }
      checkStatus();
    }
  };

  const deleteModel = async (modelName) => {
    if (!window.confirm(`Tem certeza que deseja desinstalar e apagar o modelo ${modelName} do seu computador?`)) return;
    if (window.electronAPI && window.electronAPI.deleteOllamaModel) {
      setIsChecking(true);
      await window.electronAPI.deleteOllamaModel(modelName);
      await checkStatus();
      setIsChecking(false);
    }
  };

  const repairVenv = async (envName) => {
    setDownloading(prev => ({ ...prev, [envName]: { progress: 0, text: 'Iniciando reparo...' } }));
    if (window.electronAPI && window.electronAPI.repairPythonVenv) {
      await window.electronAPI.repairPythonVenv(envName);
    }
  };

  const getStatusDisplay = (statusObj) => {
    switch (statusObj.state) {
      case 'verifying': return <span className="status-warn">Status: Verificando...</span>;
      case 'installed': return <span className="status-on">Status: [ ON ] Instalado e Pronto</span>;
      case 'downloading': return <span className="status-warn">Status: Baixando ({statusObj.progress}%)</span>;
      case 'not_installed': return <span className="status-off">Status: [ OFF ] Não Instalado</span>;
      case 'installed_but_closed': return <span className="status-warn">Status: Instalado, mas Desligado</span>;
      case 'installed_and_running': return <span className="status-on">Status: [ ON ] Instalado e Rodando</span>;
      default: return <span>Status: Desconhecido</span>;
    }
  };

  const vlmStatus = getModelStatus(models.vlm);
  const transStatus = getModelStatus(models.transPol);
  const ctxStatus = getModelStatus(models.ctx);

  return (
    <div className="modules-container">
      <div className="modules-header">
        <div className="header-content">
          <h2>Central de Módulos</h2>
          <p>Gerencie os motores de inteligência artificial locais e dependências do sistema.</p>
        </div>
        <button 
          className="btn-secondary" 
          onClick={checkStatus}
          style={{ opacity: isChecking ? 0.6 : 1, transition: 'all 0.2s', borderColor: '#3b82f6', color: '#3b82f6' }}
        >
          {isChecking ? 'Verificando...' : 'Verificar Módulos'}
        </button>
      </div>

      <div className="modules-grid">
        
        {/* Ollama Core */}
        <div className="module-card">
          <div className="module-top">
            <div className="module-title">
              <h3 style={{color: '#fff'}}>Ollama (Servidor Local)</h3>
              <p className="module-desc">O motor principal para rodar os modelos LLM. Precisa estar aberto em background.</p>
            </div>
          </div>
          <div className="module-status">
            {getStatusDisplay(statuses.ollama)}
          </div>
          <div className="module-actions">
            {statuses.ollama.state === 'installed_but_closed' && (
              <button className="btn-secondary" style={{borderColor: '#10b981', color: '#10b981'}} onClick={() => { window.electronAPI.startOllamaServer(); setTimeout(checkStatus, 2000); }}>Ligar Ollama</button>
            )}
            {statuses.ollama.state === 'not_installed' && (
              <button className="btn-secondary" onClick={() => window.electronAPI.openOllamaSite()}>Baixar Ollama</button>
            )}
          </div>
        </div>

        {/* OCR */}
        <div className="module-card">
          <div className="module-top">
            <div className="module-title">
              <h3 style={{color: '#a855f7'}}>Motor Base (Florence-2 / Manga-OCR)</h3>
              <p className="module-desc">Modelos de visão computacional para detectar as bolhas e extrair texto em japonês. (VENV_OCR)</p>
            </div>
          </div>
          <div className="module-status">
            {getStatusDisplay(statuses.ocr)}
            <span style={{marginLeft: '12px'}}>CUDA: {getStatusDisplay(statuses.cuda)}</span>
          </div>
          <div className="module-actions">
            {downloading['ocr'] ? (
              <span style={{color: '#94a3b8', fontSize: '14px', fontFamily: 'monospace'}}>{downloading['ocr'].text}</span>
            ) : (
              <button className="btn-secondary" onClick={() => repairVenv('ocr')}>Reparar VENV</button>
            )}
          </div>
        </div>

        {/* VLM */}
        <div className="module-card">
          <div className="module-top">
            <div className="module-title">
              <h3 style={{color: '#f59e0b'}}>Motor Visão (Vision Language Model)</h3>
              <p className="module-desc">Analisa os quadros do mangá, expressões faciais e contextos visuais para guiar a tradução.</p>
            </div>
          </div>
          <div className="action-row">
            <label>Modelo VLM (Etapa 2):</label>
            <select className="module-select" value={models.vlm} onChange={(e) => setModels({...models, vlm: e.target.value})}>
              {AVAILABLE_MODELS.vlm.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div className="module-status">
            {getStatusDisplay(vlmStatus)}
            {vlmStatus.state === 'downloading' && (
              <div className="progress-text">
                Baixando modelo...<br/>
                {vlmStatus.text}
              </div>
            )}
          </div>
          <div className="module-actions">
            {vlmStatus.state === 'not_installed' && (
              <button className="btn-secondary" style={{borderColor: '#f59e0b', color: '#f59e0b'}} onClick={() => pullModel(models.vlm)}>Baixar Modelo</button>
            )}
            {vlmStatus.state === 'installed' && (
              <button className="link-btn" style={{fontSize: '12px', color: '#ef4444'}} onClick={() => deleteModel(models.vlm)}>Apagar Local</button>
            )}
          </div>
        </div>

        {/* Tradução */}
        <div className="module-card">
          <div className="module-top">
            <div className="module-title">
              <h3 style={{color: '#10b981'}}>Motor de Tradução e Polimento</h3>
              <p className="module-desc">Responsável por traduzir o texto bruto para PT-BR natural. Usa a memória (RAG) se ativada.</p>
            </div>
          </div>
          <div className="action-row">
            <label>Modelo p/ Tradução (Etapa 3):</label>
            <select className="module-select" value={models.transPol} onChange={(e) => setModels({...models, transPol: e.target.value})}>
              {AVAILABLE_MODELS.trans.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div className="module-status">
            {getStatusDisplay(transStatus)}
            {transStatus.state === 'downloading' && (
              <div className="progress-text">
                Baixando modelo...<br/>
                {transStatus.text}
              </div>
            )}
          </div>
          <div className="module-actions">
            {transStatus.state === 'not_installed' && (
              <button className="btn-secondary" style={{borderColor: '#10b981', color: '#10b981'}} onClick={() => pullModel(models.transPol)}>Baixar Modelo</button>
            )}
            {transStatus.state === 'installed' && (
              <button className="link-btn" style={{fontSize: '12px', color: '#ef4444'}} onClick={() => deleteModel(models.transPol)}>Apagar Local</button>
            )}
          </div>
        </div>

        {/* Contexto */}
        <div className="module-card">
          <div className="module-top">
            <div className="module-title">
              <h3 style={{color: '#60a5fa'}}>Diretor de Contexto (Page Director)</h3>
              <p className="module-desc">Processa o capítulo de forma independente para construir orientações de semântica.</p>
            </div>
          </div>
          <div className="action-row">
            <label>Modelo p/ Contexto (Etapa 2.5):</label>
            <select className="module-select" value={models.ctx} onChange={(e) => setModels({...models, ctx: e.target.value})}>
              {AVAILABLE_MODELS.ctx.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div className="module-status">
            {getStatusDisplay(ctxStatus)}
            {ctxStatus.state === 'downloading' && (
              <div className="progress-text">
                Baixando modelo...<br/>
                {ctxStatus.text}
              </div>
            )}
          </div>
          <div className="module-actions">
            {ctxStatus.state === 'not_installed' && (
              <button className="btn-secondary" style={{borderColor: '#60a5fa', color: '#60a5fa'}} onClick={() => pullModel(models.ctx)}>Baixar Modelo</button>
            )}
            {ctxStatus.state === 'installed' && (
              <button className="link-btn" style={{fontSize: '12px', color: '#ef4444'}} onClick={() => deleteModel(models.ctx)}>Apagar Local</button>
            )}
          </div>
        </div>

        {/* Memória RAG */}
        <div className="module-card">
          <div className="module-top">
            <div className="module-title">
              <h3 style={{color: '#a3a3a3'}}>Motor de Memória (RAG Vector DB)</h3>
              <p className="module-desc">Busca semântica no histórico de traduções usando ChromaDB. Tamanho: ~1.5 GB</p>
            </div>
          </div>
          <div className="module-status">
            {getStatusDisplay(statuses.rag)}
          </div>
          <div className="module-actions">
            {downloading['ui'] ? (
              <span style={{color: '#94a3b8', fontSize: '14px', fontFamily: 'monospace'}}>{downloading['ui'].text}</span>
            ) : (
              <button className="btn-secondary" onClick={() => repairVenv('ui')}>Verificar / Instalar</button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
