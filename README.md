# Manga AI Studio 🤖

![Manga AI Studio](icon.ico) <!-- Substitua por um banner depois! -->

O **Manga AI Studio** é um ecossistema completo de extração (OCR), correção e tradução de Mangás e Quadrinhos utilizando inteligência artificial de ponta operando **100% offline e localmente** na sua máquina.

Construído para não depender de APIs pagas, nuvem ou vazamento de dados, o Manga AI Studio baixa os próprios "Cérebros Artificiais" (LLMs e OCR) e roda tudo pelo seu computador.

---

## 🌟 Principais Funcionalidades

1. **OCR Avançado para Mangás (Extração de Texto)**
   - Utiliza `EasyOCR` com algoritmos proprietários de redimensionamento e agrupamento matemático de balões de fala, garantindo a ordem certa de leitura (Direita ➔ Esquerda).
2. **Polimento de IA (Zero "Engrish")**
   - Transforma extrações falhas do OCR em um inglês 99,9% puro usando o LLM `Gemma3:4b`.
3. **Tradução Contextual RAG**
   - Usa Memória RAG (Vector Database com `ChromaDB`) para lembrar como nomes de personagens e ataques foram traduzidos nos capítulos anteriores.
4. **Instalador Modular**
   - Não quer queimar a sua franquia de dados baixando 10GB de IA? O app conta com um **Wizard de Instalação Inteligente**: ele instala apenas os módulos que você desejar (OCR Base, Aceleração NVIDIA CUDA, Motor de Tradução e Motor de Memória RAG).
5. **Modo Editor Visual (Em Breve)**
   - Arraste, solte e edite os textos diretamente na página do mangá!

---

## ⚙️ Instalação Rápida

1. Baixe o executável `Manga_AI_Studio_Setup.exe` [disponível nas Releases](https://github.com/SEU-USUARIO/SEU-REPOSITORIO/releases) (ou na raiz do repositório).
2. Abra o aplicativo.
3. Vá na aba **Gerenciador de Módulos (IA)**.
4. Baixe os módulos que deseja utilizar. **Recomendado:** Baixe a `Aceleração NVIDIA` se você tiver uma placa de vídeo da NVIDIA (GTX/RTX) para deixar a extração em menos de 1 segundo!

---

## 🚀 Como Usar o Pipeline

1. Vá para a aba **Processamento**.
2. Selecione uma pasta contendo suas páginas brutas (`.jpg`, `.png`).
3. Escolha o Tom da Tradução (ex: *Shounen Enérgico*, *Seinen Maduro*, etc).
4. Clique em **Iniciar Pipeline Mágico**!
5. Os textos serão processados, corrigidos, traduzidos e salvos na mesma pasta ou na pasta Temp do sistema!

---

## 🛠️ Tecnologias Utilizadas

- **Frontend:** CustomTkinter (Python)
- **IA e LLM:** Ollama (Gemma3:4b)
- **Vector DB (RAG):** ChromaDB & SentenceTransformers
- **Computer Vision:** OpenCV & EasyOCR
- **Pacotes:** PyInstaller (Standalone App)

---

## 👥 Contribuição
Fique à vontade para fazer um **Fork** deste projeto e enviar **Pull Requests**! Para rodar do código-fonte:
```bash
git clone https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
cd manga-ocr-extractor
python app.py
```
