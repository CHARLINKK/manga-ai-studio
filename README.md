<div align="center">
  <h1>Manga AI Studio</h1>
  <p><i>A modular, offline pipeline for automated extraction, processing, and translation of manga and comics.</i></p>
</div>

---

## 📌 Overview

**Manga AI Studio** is a standalone, fully offline desktop application designed to automate the translation workflow for manga and comic book scans. The system integrates advanced Optical Character Recognition (OCR), Large Language Models (LLMs) for text polishing, and Retrieval-Augmented Generation (RAG) for maintaining contextual consistency across chapters. 

The architecture is highly modular, ensuring that intensive AI models (such as LLMs and CUDA dependencies) are optional and locally executed, completely bypassing third-party APIs or cloud infrastructure.

---

## ⚙️ Core Architecture & Pipeline

The processing pipeline is executed sequentially through the following modules:

1. **OCR Engine (EasyOCR + Custom Algorithms):**
   - Implements bounding box detection tailored for right-to-left reading formats.
   - Applies geometric clustering to preserve the natural reading order of text bubbles in complex panel layouts.
2. **Text Polishing Engine (LLM):**
   - Intercepts raw OCR output and utilizes an LLM (e.g., `Gemma3:4b` via Ollama) to correct hallucinated characters and syntax errors (often referred to as "Engrish").
3. **Translation Engine & RAG Integration:**
   - Processes the corrected text through localized LLMs for contextual translation.
   - Connects to a `ChromaDB` vector database to retrieve historical translation entities (e.g., character names, specific jargon, location names) using `SentenceTransformers`, guaranteeing consistency across volumes.

---

## 🛠️ Technology Stack

- **Application Interface:** Python (`CustomTkinter`)
- **LLM Runtime:** Ollama API
- **Computer Vision & OCR:** `OpenCV`, `PyTorch`, `EasyOCR`
- **Vector Database (RAG):** `ChromaDB`, `SentenceTransformers`
- **Distribution:** `PyInstaller` (Standalone executable bundle)

---

## 🖥️ System Requirements & Limitations

### Recommended Specifications
To ensure smooth execution of the localized OCR and LLM translation models, the following hardware is recommended:
- **CPU:** Modern multi-core processor (e.g., Intel Core i5 10th Gen / AMD Ryzen 5 3600 or higher).
- **RAM:** 16 GB minimum (32 GB recommended if running heavily quantized LLMs alongside RAG).
- **Storage:** 50 GB of free space on an **SSD** (NVMe preferred) for fast model loading and storing multiple AI weights (Ollama models, PyTorch CUDA binaries, etc.). HDD is not recommended due to high I/O latency when parsing models.
- **Internet Speed:** 50 Mbps or higher is strongly recommended during the initial setup to download the heavy AI models (Ollama weights, PyTorch binaries, and OCR datasets). Completely offline post-installation.

### Hardware Limitations
- **AMD GPUs:** Currently **NOT supported** by the standalone CUDA acceleration module. PyTorch with ROCm is not natively bundled for Windows environments. Processing will fallback to CPU.
- **NVIDIA RTX 5000 Series:** Due to unresolved compatibility issues in the bundled PyTorch/CUDA 11.x and 12.x wheels on PyInstaller, the RTX 5000 series is currently **unsupported** and will cause silent crashes or fallback to CPU processing.

---

## 📥 Installation

Manga AI Studio utilizes a proprietary silent Auto-Updater and Setup Wizard to manage isolated environments and heavy dependencies.

1. Navigate to the **[Releases](https://github.com/CHARLINKK/manga-ai-studio/releases)** page.
2. Download the latest `.zip` archive.
3. Extract the contents and execute the provided `Setup.exe`. The installer will automatically provision a dedicated Python environment (`venv_ui`).
4. Upon launching the application, access the **Central de Módulos (IA)** tab to download and install optional modules (e.g., NVIDIA CUDA acceleration, Ollama runtime, OCR datasets).

---

## 💻 Developer & Contribution Guide

The project is structured to run locally for development and debugging. Pull Requests optimizing the OCR clustering algorithms or the RAG database interactions are encouraged.

### Local Environment Setup

```bash
# Clone the repository
git clone https://github.com/CHARLINKK/manga-ai-studio.git
cd manga-ocr-extractor

# Create a virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-ocr.txt

# Launch the application
python app.py
```

*Note: Ensure you have compatible NVIDIA drivers and the CUDA toolkit installed if you intend to test GPU-accelerated OCR workflows locally.*
