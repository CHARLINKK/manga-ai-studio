# Changelog

## [2.2.0](https://github.com/CHARLINKK/manga-ai-studio/compare/manga-ai-studio-v2.1.7...manga-ai-studio-v2.2.0) (2026-07-11)


### Features

* atualiza PyTorch para 2.7.0 (suporte RTX 5000) e melhora UX do Light Theme ([1d24ac5](https://github.com/CHARLINKK/manga-ai-studio/commit/1d24ac518460a279607a1619d5cd663e69b3889d))
* **core:** implement fail-safe locks, UI fixes, and semantic CI/CD automation ([7c7c003](https://github.com/CHARLINKK/manga-ai-studio/commit/7c7c00385570356a3259997fbd148e2248285122))
* **core:** Lançamento da v2.0 com Interface nativa, Estúdio Visual e Auto-Updater ([ee39a92](https://github.com/CHARLINKK/manga-ai-studio/commit/ee39a9261decfd476175e10d7ddc2131d1faf0e1))
* Otimização de performance com SDPA no Florence-2 ([69bf903](https://github.com/CHARLINKK/manga-ai-studio/commit/69bf903ca58a10713d597fe060033d05a60c2663))
* Servidor Base nativo embutido com PyInstaller ([d8089d2](https://github.com/CHARLINKK/manga-ai-studio/commit/d8089d21e4466e4c0f3d276490be6ebe869c6a51))
* Sistema global de Toasts e Limpeza do boot (Fix ENOENT) ([66a746e](https://github.com/CHARLINKK/manga-ai-studio/commit/66a746e400db020076a31950b7066eb82329b8bb))
* **updater:** refine update notification UX and window management ([ff485e5](https://github.com/CHARLINKK/manga-ai-studio/commit/ff485e572612962486f4a058f616d7d233ba574b))


### Bug Fixes

* Auto-criação de VENV e limpeza de código-fonte morto ([0ab2ad6](https://github.com/CHARLINKK/manga-ai-studio/commit/0ab2ad6598df8366df526233797a620deedd6d38))
* Configuração correta de repository no package.json para o electron-builder ([ac52699](https://github.com/CHARLINKK/manga-ai-studio/commit/ac526997ab1e21fa6356da67f9a3d73a14eb9fbd))
* Correção do target de requirements na instalação do OCR ([c6973ce](https://github.com/CHARLINKK/manga-ai-studio/commit/c6973ce9e4786d78a5645bcb1bd78573517f6156))
* Corrige crash do logger na inicialização ([b792912](https://github.com/CHARLINKK/manga-ai-studio/commit/b792912ae94e2344647db161333acded972c4831))
* Corrige tela em branco e nome da janela no Electron ([89d4331](https://github.com/CHARLINKK/manga-ai-studio/commit/89d433172f520d659a280c83fe198783e4d1ce1e))
* Restauração do bloco publish no package.json ([2f8e69b](https://github.com/CHARLINKK/manga-ai-studio/commit/2f8e69bd7d1c1620f802eecf6f692104275cbea7))
