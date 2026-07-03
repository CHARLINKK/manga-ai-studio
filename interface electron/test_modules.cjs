const path = require('path');
const fs = require('fs');
const os = require('os');

async function test() {
  console.log('Starting...');
  const status = {};
  const projectRoot = path.join(__dirname, '..');
  
  console.log('Checking OCR...');
  const ocrTransformers = path.join(projectRoot, 'venv_ocr', 'Lib', 'site-packages', 'transformers');
  console.log(ocrTransformers, fs.existsSync(ocrTransformers));

  console.log('Checking CUDA...');
  const pythonExe = path.join(projectRoot, 'venv_ocr', 'Scripts', 'python.exe');
  if (fs.existsSync(pythonExe)) {
    const { execSync } = require('child_process');
    try {
      const result = execSync(`"${pythonExe}" -c "import torch; print(torch.cuda.is_available())"`, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] }).trim();
      console.log('CUDA result:', result);
    } catch(e) { console.log('CUDA error', e.message); }
  }

  console.log('Checking Ollama...');
  const { execSync } = require('child_process');
  let ollamaPath = null;
  try {
    execSync('where ollama', { stdio: 'ignore' });
    ollamaPath = 'ollama';
  } catch {
    const localAppPath = path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Ollama', 'ollama.exe');
    if (fs.existsSync(localAppPath)) ollamaPath = localAppPath;
  }
  console.log('Ollama path:', ollamaPath);

  if (ollamaPath) {
    try {
      console.log('Fetching Ollama...');
      // Use standard fetch
      const req = await fetch('http://127.0.0.1:11434/');
      console.log('Fetch ok:', req.ok);
      if (req.ok) {
        console.log('Running list...');
        const res = execSync(`"${ollamaPath}" list`, { encoding: 'utf8' });
        console.log('List returned length:', res.length);
      }
    } catch(e) {
      console.log('Ollama fetch error:', e.message);
    }
  }
  console.log('Done!');
}
test();
