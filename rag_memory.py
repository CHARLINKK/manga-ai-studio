import json
from pathlib import Path

def get_chroma_collection(workspace_path: Path):
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        return None

    memory_dir = workspace_path / 'Biblioteca' / 'Memory'
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(memory_dir))
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
    collection = client.get_or_create_collection(name='translation_memory', embedding_function=emb_fn)
    return collection

def sync_memory_from_txts(workspace_path: Path, txt_files_paths: list):
    collection = get_chroma_collection(workspace_path)
    if collection is None:
        return False, 'ChromaDB não instalado.'
        
    added = 0
    for txt_path in txt_files_paths:
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('
')
            
            current_en = None
            for line in lines:
                if line.startswith('[EN]:'):
                    current_en = line.replace('[EN]:', '').strip()
                elif line.startswith('[BR]:') and current_en:
                    br_text = line.replace('[BR]:', '').strip()
                    
                    if current_en and br_text:
                        import hashlib
                        doc_id = hashlib.md5(current_en.encode('utf-8')).hexdigest()
                        
                        collection.upsert(
                            documents=[current_en],
                            metadatas=[{'br': br_text, 'source': Path(txt_path).name}],
                            ids=[doc_id]
                        )
                        added += 1
                    current_en = None
        except Exception as e:
            pass
            
    return True, f'Memória RAG atualizada! {added} novas traduções salvas.'

def query_memory(workspace_path: Path, en_text: str, threshold: float = 0.5):
    collection = get_chroma_collection(workspace_path)
    if collection is None:
        return None
        
    if not en_text.strip():
        return None
        
    try:
        results = collection.query(
            query_texts=[en_text],
            n_results=1
        )
        
        if results['distances'] and results['distances'][0]:
            dist = results['distances'][0][0]
            if dist < threshold:
                metadata = results['metadatas'][0][0]
                return metadata['br']
    except Exception:
        pass
    return None
