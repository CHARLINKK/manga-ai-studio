import { useState, useEffect, useRef } from 'react';
import './Settings.css';
import pkg from '../../package.json';

const GUIDE_CONTENT = {
  ocr: {
    title: 'Motor OCR & CUDA',
    sections: [
      {
        heading: 'Instalação e Aceleração GPU',
        body: `É recomendado que o Motor OCR seja instalado antes do Suporte CUDA. O módulo CUDA atualiza o ambiente do OCR para otimização em placas de vídeo. A inversão dessa ordem pode resultar em incompatibilidades.`
      },
      {
        heading: 'Requisitos para Suporte CUDA',
        body: `A aceleração via hardware é compatível exclusivamente com placas de vídeo NVIDIA.

Hardware AMD (Radeon) ou Intel deve utilizar a versão CPU (configuração padrão do módulo OCR).`
      }
    ]
  },
  ollama: {
    title: 'Modelos Ollama (Local)',
    sections: [
      {
        heading: 'Motor de Tradução e Polimento',
        items: [
          { model: 'llama3.1:8b', desc: 'Excelente desempenho para traduções robustas e coesas. Padrão ouro para 8GB.', vram: '~8GB VRAM' },
          { model: 'gemma2:9b', desc: 'Alta precisão de raciocínio. Excelente para o polimento e revisão da raw.', vram: '~8–10GB VRAM' },
          { model: 'mistral-nemo:12b', desc: 'Versatilidade com grande janela de contexto.', vram: '~12GB VRAM' },
          { model: 'qwen2.5:14b', desc: 'Qualidade superior e compreensão altíssima de nuances.', vram: '~12–16GB VRAM' },
        ]
      },
      {
        heading: 'Diretor de Contexto (Page Director)',
        items: [
          { model: 'phi3:latest', desc: 'Rápido e focado em lógica, perfeito para analisar elementos isolados e gerar feedback veloz.', vram: '~4–6GB VRAM' },
          { model: 'llama3.1:8b', desc: 'Opção robusta caso deseje manter total consistência com o motor de tradução.', vram: '~8GB VRAM' },
        ]
      },
      {
        heading: 'Diretor Visual de Leitura (VLM)',
        items: [
          { model: 'qwen2.5vl:7b', desc: 'Melhor custo-benefício do mercado atual. Extremamente ágil para ler geometria dos balões e filtrar onomatopeias.', vram: '~8GB VRAM' },
          { model: 'llama3.2-vision:11b', desc: 'Visão computacional de ponta, porém exige hardware mais robusto.', vram: '~10–12GB VRAM' },
          { model: 'llava:13b', desc: 'Modelo open-source clássico. Bom para testes, mas inferior em velocidade.', vram: '~12–14GB VRAM' },
        ]
      }
    ]
  }
};

function GuideModal({ onClose }) {
  const [activeGuideTab, setActiveGuideTab] = useState('ocr');
  const guide = GUIDE_CONTENT[activeGuideTab];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Guia da Central de Módulos</h2>
          <button className="btn-icon" onClick={onClose}>✕</button>
        </div>

        <div className="modal-tabs">
          <button className={`modal-tab ${activeGuideTab === 'ocr' ? 'active' : ''}`} onClick={() => setActiveGuideTab('ocr')}>Motor OCR & CUDA</button>
          <button className={`modal-tab ${activeGuideTab === 'ollama' ? 'active' : ''}`} onClick={() => setActiveGuideTab('ollama')}>Modelos Ollama</button>
        </div>

        <div className="modal-content">
          <h3>{guide.title}</h3>
          {guide.sections.map((section, i) => (
            <div key={i} className="guide-section">
              <h4>{section.heading}</h4>
              {section.body && <p className="guide-body">{section.body}</p>}
              {section.items && (
                <div className="model-guide-list">
                  {section.items.map(item => (
                    <div key={item.model} className="model-guide-item">
                      <div className="model-guide-top">
                        <code className="model-name-code">{item.model}</code>
                        <span className="vram-badge">{item.vram}</span>
                      </div>
                      <p>{item.desc}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Settings({ onBaseFolderChange }) {
  const [theme, setTheme] = useState('Dark');
  const [accent, setAccent] = useState('Roxo (Padrão)');
  const [rememberZoom, setRememberZoom] = useState(false);
  const [baseFolder, setBaseFolder] = useState('');
  const [baseFolderInput, setBaseFolderInput] = useState('');
  const [systemNotifications, setSystemNotifications] = useState(true);
  const [autoUpdate, setAutoUpdate] = useState(true);
  const [closeBehavior, setCloseBehavior] = useState('ask');
  const [showGuide, setShowGuide] = useState(false);
  const [stats, setStats] = useState({ pagesProcessed: 0, timeSaved: 0 });
  
  const isInitialMount = useRef(true);

  // Salva a pasta base imediatamente ao clicar em Aplicar
  function applyBaseFolder() {
    const val = baseFolderInput.trim();
    if (!val) return;
    setBaseFolder(val);
    if (window.electronAPI) {
      window.electronAPI.saveSettings({ theme, accent, rememberZoom, baseFolder: val });
    }
    if (onBaseFolderChange) {
      onBaseFolderChange(val);
    }
  }

  // Carregar do backend (Electron) na montagem
  useEffect(() => {
    if (window.electronAPI) {
      window.electronAPI.getSettings().then(settings => {
        setTheme(settings.theme || 'Dark');
        setAccent(settings.accent || 'Roxo (Padrão)');
        setRememberZoom(settings.rememberZoom || false);
        setBaseFolder(settings.baseFolder || '');
        setBaseFolderInput(settings.baseFolder || '');
        setSystemNotifications(settings.systemNotifications !== false);
        setAutoUpdate(settings.autoUpdate !== false);
        setCloseBehavior(settings.closeBehavior || 'ask');
        
        // Carregar estatísticas
        if (window.electronAPI.getStats) {
          window.electronAPI.getStats().then(s => setStats(s || { pagesProcessed: 0, timeSaved: 0 }));
        }

        // Marcamos que terminou de carregar o inicial
        setTimeout(() => { isInitialMount.current = false; }, 100);
      });
    }
  }, []);

  // Salvar no backend toda vez que mudar e atualizar o CSS
  useEffect(() => {
    if (isInitialMount.current) return;

    const newSettings = { theme, accent, rememberZoom, baseFolder, systemNotifications, autoUpdate, closeBehavior };
    
    // Salvar no JSON
    if (window.electronAPI) {
      window.electronAPI.saveSettings(newSettings);
    }
    
    // Aplicar a cor imediatamente na tela
    const colorMap = {
      'Roxo (Padrão)': '#6366f1',
      'Azul': '#3b82f6',
      'Verde': '#10b981',
      'Vermelho': '#ef4444',
      'Laranja': '#f59e0b'
    };
    
    if (colorMap[accent]) {
      document.documentElement.style.setProperty('--brand-blue', colorMap[accent]);
      document.documentElement.style.setProperty('--brand-blue-hover', colorMap[accent]);
    } else if (accent && accent.startsWith('#')) {
      document.documentElement.style.setProperty('--brand-blue', accent);
      document.documentElement.style.setProperty('--brand-blue-hover', accent);
    }

    // Aplicar o tema (Dark / Light / System) imediatamente
    let appliedTheme = theme;
    if (appliedTheme === 'System') {
      const isSystemLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
      appliedTheme = isSystemLight ? 'Light' : 'Dark';
    }
    
    if (appliedTheme === 'Light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }, [theme, accent, rememberZoom, baseFolder, systemNotifications, autoUpdate, closeBehavior]);

  const accentColors = [
    { id: 'purple', label: 'Roxo (Padrão)', color: '#6366f1' },
    { id: 'blue', label: 'Azul', color: '#3b82f6' },
    { id: 'green', label: 'Verde', color: '#10b981' },
    { id: 'red', label: 'Vermelho', color: '#ef4444' },
    { id: 'orange', label: 'Laranja', color: '#f59e0b' },
  ];

  return (
    <div className="settings-container fade-in">
      {showGuide && <GuideModal onClose={() => setShowGuide(false)} />}

      <div className="settings-scroll">
        {/* Header */}
        <div className="settings-page-header">
          <div>
            <h1>Configurações</h1>
            <p>As preferências são salvas automaticamente no seu perfil.</p>
          </div>
          <div style={{display: 'flex', gap: '8px'}}>
            <button className="btn-secondary" onClick={() => setShowGuide(true)}>
              Guia de Modelos
            </button>
          </div>
        </div>

        {/* Gamificação section removed from here */}

        {/* Seção: Interface */}
        <div className="settings-section">
          <div className="section-label">
            <span className="section-icon">🎨</span>
            <span>Personalização de Interface</span>
          </div>

          <div className="settings-card">
            {/* Tema (Aparência) */}
            <div className="settings-row">
              <div className="setting-info">
                <strong>Modo de Fundo (Aparência)</strong>
                <span>Altera entre Dark Mode e Light Mode da interface.</span>
              </div>
              <div className="theme-toggle-group">
                {['Dark', 'Light', 'System'].map(t => (
                  <button
                    key={t}
                    className={`theme-btn ${theme === t ? 'active' : ''}`}
                    onClick={() => setTheme(t)}
                  >
                    {t === 'Dark' ? '🌙 Dark' : t === 'Light' ? '☀️ Light' : '💻 System'}
                  </button>
                ))}
              </div>
            </div>

            <div className="settings-divider" />

            {/* Cor de Destaque */}
            <div className="settings-row">
              <div className="setting-info">
                <strong>Cor de Destaque (Accent)</strong>
                <span>Cor dos botões, abas ativas e indicadores de seleção.</span>
              </div>
              <div className="accent-swatches">
                {accentColors.map(a => (
                  <button
                    key={a.id}
                    className={`swatch ${accent === a.label || accent === a.color ? 'active' : ''}`}
                    style={{ background: a.color }}
                    title={a.label}
                    onClick={() => setAccent(a.label)}
                  >
                    {(accent === a.label || accent === a.color) && <span className="swatch-check">✓</span>}
                  </button>
                ))}
                
                <div 
                  className={`swatch custom-swatch ${accent.startsWith('#') && !accentColors.some(a => a.color === accent || a.label === accent) ? 'active' : ''}`}
                  title="Cor Personalizada (RGB)"
                >
                  <input
                    type="color"
                    className="color-input-hidden"
                    value={accent.startsWith('#') ? accent : '#ffffff'}
                    onChange={(e) => setAccent(e.target.value)}
                  />
                  {accent.startsWith('#') && !accentColors.some(a => a.color === accent || a.label === accent) && (
                    <span className="swatch-check" style={{ pointerEvents: 'none' }}>✓</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Seção: Estúdio */}
        <div className="settings-section">
          <div className="section-label">
            <span className="section-icon">🖼</span>
            <span>Preferências do Estúdio</span>
          </div>

          <div className="settings-card">
            <div className="settings-row">
              <div className="setting-info">
                <strong>Lembrar nível de zoom individual de cada página</strong>
                <span>Ao navegar entre páginas, mantém o zoom aplicado anteriormente a cada uma.</span>
              </div>
              <label className="classic-checkbox">
                <input
                  type="checkbox"
                  checked={rememberZoom}
                  onChange={e => setRememberZoom(e.target.checked)}
                />
                Ativar
              </label>
            </div>

            <div className="settings-divider" />

            {/* Pasta Base do Explorador */}
            <div className="settings-row base-folder-row">
              <div className="setting-info">
                <strong>Pasta Base do Explorador</strong>
                <span>O explorador sempre abrirá nessa pasta ao iniciar o programa.</span>
              </div>
              <div className="base-folder-input-group">
                <input
                  className="base-folder-input"
                  type="text"
                  placeholder="Ex: D:\Manga\Series"
                  value={baseFolderInput}
                  onChange={e => setBaseFolderInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') applyBaseFolder();
                  }}
                />
                <button
                  className="base-folder-btn"
                  onClick={applyBaseFolder}
                >
                  Aplicar
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Seção: Comportamento do Aplicativo */}
        <div className="settings-section">
          <div className="section-label">
            <span className="section-icon">⚙️</span>
            <span>Comportamento do Aplicativo</span>
          </div>

          <div className="settings-card">
            <div className="settings-row">
              <div className="setting-info">
                <strong>Notificações do Sistema</strong>
                <span>Exibir alerta na área de trabalho quando processamentos forem concluídos.</span>
              </div>
              <label className="classic-checkbox">
                <input
                  type="checkbox"
                  checked={systemNotifications}
                  onChange={e => setSystemNotifications(e.target.checked)}
                />
                Ativar
              </label>
            </div>

            <div className="settings-divider" />

            <div className="settings-row">
              <div className="setting-info">
                <strong>Atualizações Automáticas</strong>
                <span>Verificar e baixar novas atualizações silenciosamente ao iniciar.</span>
              </div>
              <label className="classic-checkbox">
                <input
                  type="checkbox"
                  checked={autoUpdate}
                  onChange={e => setAutoUpdate(e.target.checked)}
                />
                Ativar
              </label>
            </div>

            <div className="settings-divider" />

            <div className="settings-row">
              <div className="setting-info">
                <strong>Ao fechar a janela (X)</strong>
                <span>Minimizar para a bandeja permite que a IA continue rodando em segundo plano.</span>
              </div>
              <select 
                className="settings-select"
                value={closeBehavior}
                onChange={e => setCloseBehavior(e.target.value)}
              >
                <option value="ask">Sempre perguntar</option>
                <option value="tray">Sempre minimizar para a bandeja</option>
                <option value="quit">Sempre fechar completamente</option>
              </select>
            </div>
          </div>
        </div>

        {/* Gamificação / Estatísticas */}
        <div className="settings-section">
          <div className="section-label" style={{ color: '#d97706' }}>
            <span className="section-icon">🏆</span>
            <span>Conquistas de Automação</span>
          </div>
          <div className="settings-card" style={{ display: 'flex', gap: '20px', padding: '20px', alignItems: 'center' }}>
            <div style={{ flex: 1, borderRight: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Páginas Processadas</div>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: 'var(--text-main)', marginTop: '4px' }}>{stats.pagesProcessed}</div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Tempo Economizado (Aprox.)</div>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#34d399', marginTop: '4px' }}>
                {stats.timeSaved >= 60 ? `${(stats.timeSaved / 60).toFixed(1)}h` : `${stats.timeSaved}m`}
              </div>
            </div>
          </div>
        </div>

        {/* Seção: Sobre */}
        <div className="settings-section">
          <div className="section-label">
            <span className="section-icon">ℹ️</span>
            <span>Sobre o Aplicativo</span>
          </div>
          <div className="settings-card about-card">
            <div className="about-info">
              <h2>Manga AI Studio <span className="version-badge">v{pkg.version}</span></h2>
              <p className="about-stack">Arquitetura de Extração e Tradução Local</p>
              <p className="about-desc">
                Pipeline de Inteligência Artificial para extração, polimento e tradução nativa de mangás.<br/>
                Desenvolvido com <strong>Qwen2.5-VL</strong> e <strong>Llama-3</strong>, otimizado com <em>Flash Attention (SDPA)</em> e inferência assimétrica assíncrona.
              </p>
            </div>
          </div>
        </div>

        <p className="settings-footer">
          As configurações visuais e preferências são salvas automaticamente no seu perfil.
        </p>
      </div>
    </div>
  );
}
