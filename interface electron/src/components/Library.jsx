import { useState, useEffect } from 'react';
import './Library.css';

export default function Library() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadLibrary();
  }, []);

  const loadLibrary = async () => {
    setIsLoading(true);
    if (window.electronAPI && window.electronAPI.listLibraryFiles) {
      const res = await window.electronAPI.listLibraryFiles();
      if (res && res.success) {
        setFiles(res.files);
        // Se já havia um selecionado, atualizar
        if (selectedFile) {
          const stillExists = res.files.find(f => f.path === selectedFile.path);
          if (!stillExists) {
            setSelectedFile(null);
            setFileContent('');
          }
        }
      }
    }
    setIsLoading(false);
  };

  const handleSelectFile = async (file) => {
    setSelectedFile(file);
    setFileContent('Carregando...');
    if (window.electronAPI && window.electronAPI.readLibraryFile) {
      const res = await window.electronAPI.readLibraryFile(file.path);
      if (res && res.success) {
        setFileContent(res.content);
      } else {
        setFileContent('[ERRO] ' + res.error);
      }
    }
  };

  const handleDeleteFile = async (e, file) => {
    e.stopPropagation();
    if (!window.confirm(`Tem certeza que deseja apagar ${file.name} da Biblioteca?`)) return;
    
    if (window.electronAPI && window.electronAPI.deleteLibraryFile) {
      await window.electronAPI.deleteLibraryFile(file.path);
      await loadLibrary();
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
  };

  return (
    <div className="library-container">
      <div className="library-sidebar">
        <div className="library-sidebar-header">
          <h2>Biblioteca Central</h2>
          <button className="btn-refresh" onClick={loadLibrary} title="Atualizar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.92-5.27l3.08-1.3"/>
            </svg>
          </button>
        </div>
        
        <div className="library-file-list">
          {isLoading ? (
            <div className="empty-message">Carregando...</div>
          ) : files.length === 0 ? (
            <div className="empty-message">Nenhum capítulo salvo na Biblioteca.</div>
          ) : (
            files.map(file => (
              <div 
                key={file.path} 
                className={`library-file-item ${selectedFile?.path === file.path ? 'active' : ''}`}
                onClick={() => handleSelectFile(file)}
              >
                <div className="file-info">
                  <span className="file-name">{file.name.replace('.txt', '')}</span>
                  <span className="file-meta">
                    {new Date(file.mtime).toLocaleDateString()} • {formatSize(file.size)}
                  </span>
                </div>
                <button 
                  className="btn-delete-file" 
                  onClick={(e) => handleDeleteFile(e, file)}
                  title="Excluir da Biblioteca"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6"/>
                  </svg>
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="library-content">
        {selectedFile ? (
          <>
            <div className="content-header">
              <h3>{selectedFile.name}</h3>
            </div>
            <div className="content-body">
              <textarea 
                className="library-textarea" 
                readOnly 
                value={fileContent}
              />
            </div>
          </>
        ) : (
          <div className="library-placeholder">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--border-strong)" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
            <p>Selecione um capítulo da biblioteca para visualizar o texto final.</p>
          </div>
        )}
      </div>
    </div>
  );
}
