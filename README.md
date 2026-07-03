<div align="center">
  <h1>Manga AI Studio 2.0</h1>
  <p><i>A modular, offline pipeline for automated extraction, processing, and translation of manga and comics.</i></p>
</div>

---

## 📌 Overview

**Manga AI Studio** is a standalone, fully offline desktop application designed to automate the translation workflow for manga and comic book scans. The system integrates advanced Optical Character Recognition (OCR), Large Language Models (LLMs) for text polishing, and Retrieval-Augmented Generation (RAG) for maintaining contextual consistency across chapters. 

The architecture is highly modular, ensuring that intensive AI models (such as LLMs and CUDA dependencies) are optional and locally executed, completely bypassing third-party APIs or cloud infrastructure.

### 🚀 Two Available Versions
To accommodate different workflows, this repository hosts two major versions of the application:
- **🌟 Version 2.x (Electron GUI - Recommended):** The definitive modern experience. Features a complete graphical interface, Visual Correction Studio, dark themes, a smart status semaphore system, and an integrated Auto-Updater. *(Found in the `interface electron/` folder).*
- **💻 Version 1.x (Classic Python GUI):** The original application. Features a robust Python-native graphical interface (`CustomTkinter`). Recommended for Python developers or users who prefer the classic package management environment. *(Found in the repository root).*

---

## ⚙️ Core Architecture & Pipeline

The processing pipeline is executed sequentially through the following modules:

1. **OCR Engine (Florence-2 & Manga OCR):**
   - Implements OCR using state-of-the-art vision models (like Microsoft's `Florence-2-Large` and `Manga OCR`) tailored for complex panel layouts, Japanese text, and sound effects.
   - Applies custom bounding box clustering to ensure correct right-to-left reading order of text bubbles.
2. **Text Polishing & Visual Director (VLM):**
   - Utilizes localized Vision-Language Models (e.g., `Qwen-2.5-VL`) to contextually understand the manga panels, intercept raw OCR output, and correct OCR hallucinations and character errors.
3. **Translation Engine & RAG Integration:**
   - Processes the corrected text through local LLMs for context-aware translation without censorship.
   - Connects to a `ChromaDB` vector database using `SentenceTransformers` to retrieve historical translation entities (e.g., character names, jargons, locations) to ensure terminological consistency across chapters.

---

## 🛠️ Technology Stack

- **Application Interface:** `Electron` + `React 19` (v2.x) | `CustomTkinter` (v1.x)
- **LLM Runtime:** Ollama API (supports models like `qwen2.5-vl:7b`, `llama3.1:8b`, etc.)
- **Computer Vision & OCR:** `OpenCV`, `PyTorch` (with optional CUDA/Accelerate support), `Transformers (HuggingFace)`
- **Vector Database (RAG):** `ChromaDB`, `SentenceTransformers`
- **Distribution:** `electron-builder` (v2.x Setup Wizard & Auto-Updater) | `PyInstaller` (v1.x Standalone Package)

---

## 🖥️ System Requirements & Limitations

### Recommended Specifications
To ensure smooth execution of the localized OCR and LLM translation models, the following hardware is recommended:
- **CPU:** Modern multi-core processor (e.g., Intel Core i5 10th Gen / AMD Ryzen 5 3600 or higher).
- **RAM:** 16 GB minimum (32 GB recommended if running heavily quantized LLMs alongside RAG).
- **Storage:** 50 GB of free space on an **SSD** (NVMe preferred) for fast model loading and storing multiple AI weights. HDD is not recommended due to high I/O latency when parsing models.
- **Internet Speed:** 50 Mbps or higher is strongly recommended during the initial setup to download the heavy AI models (Ollama weights, PyTorch binaries, and OCR datasets). Completely offline post-installation.

### Hardware Limitations
- **AMD GPUs:** Currently **NOT supported** by the standalone CUDA acceleration module. PyTorch with ROCm is not natively bundled for Windows environments. Processing will fallback to CPU.
- **NVIDIA RTX 5000 Series:** Due to unresolved compatibility issues in the bundled PyTorch/CUDA 11.x and 12.x wheels, the RTX 5000 series is currently **unsupported** and will cause silent crashes or fallback to CPU processing.

---

## 📥 Installation

Manga AI Studio utilizes a proprietary silent Auto-Updater and Setup Wizard to manage isolated environments and heavy dependencies.

1. Navigate to the **[Releases](https://github.com/CHARLINKK/manga-ai-studio/releases)** page.
2. **For v2.x (Recommended):** Download the latest `Manga AI Studio Setup x.x.x.exe` installer.
3. **For v1.x (Classic):** Download the legacy `.zip` archive and extract the `Setup.exe`.
4. Double-click the installer to deploy the application.
5. Upon launching the application, access the **Modules / Settings** tab to download and configure optional AI modules (e.g., NVIDIA CUDA acceleration, Ollama runtime, OCR datasets).

---

## 💻 Developer & Contribution Guide

The project is structured to run locally for development and debugging. Pull Requests optimizing the OCR clustering algorithms or the Electron frontend are encouraged.

### Local Environment Setup (v2.x Electron)

```bash
# Clone the repository
git clone https://github.com/CHARLINKK/manga-ai-studio.git
cd manga-ai-studio/interface\ electron

# Install NodeJS dependencies
npm install

# Launch the Electron interface in development mode
npm run electron:dev
```

### Local Environment Setup (v1.x Python)

```bash
# From the root directory, create a virtual environment
python -m venv venv
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-ocr.txt

# Launch the classic Python UI
python launcher.py
```

*Note: Ensure you have compatible NVIDIA drivers and the CUDA toolkit installed if you intend to test GPU-accelerated workflows locally.*
