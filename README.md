# Nota 10 - Sistema OMR (Optical Mark Recognition) 📝

Um sistema de correção automática de provas via reconhecimento de imagens (OMR) desenvolvido em Python e Flask. Feito sob medida para professores, este aplicativo permite a geração de gabaritos customizáveis e a correção automática de provas digitalizadas usando Visão Computacional (OpenCV).

## Funcionalidades Principais ✨

1. **Gerador de Provas**: Crie matrizes (PDFs) dinâmicas com os marcadores fiduciais (quadrados pretos nos cantos) necessários para o alinhamento da Visão Computacional.
2. **Correção Automática (CV2)**: O sistema detecta as marcações dos alunos de forma robusta e resistente a leves inclinações do escaneamento.
3. **Relatórios Automáticos**: Cruza as notas obtidas com uma "Lista de Alunos" predefinida (opcional) e gera planilhas Excel formatadas prontas para lançamento no diário.
4. **Recorte de Provas**: Separa e salva as imagens de cada página de prova corrigida para eventual auditoria (download automático via ZIP).
5. **Privacy by Design / Clean Architecture**: Processamento inteiramente realizado em memória RAM. Nenhum arquivo de prova ou relatório é salvo no disco do servidor, garantindo privacidade e impedindo o vazamento de notas. O cache em memória também conta com expiração automática (autoclean).

## Interface de Usuário (UI) 🎨
O frontend adota uma abordagem moderna, minimalista e *Glassmorphism*. O processamento é assíncrono (sem travamentos ou reload de página), e os downloads são gerados em tempo real na aba do usuário via botões dedicados.

## Tecnologias Utilizadas 🚀
- **Backend:** Python 3.11, Flask, Gunicorn.
- **Processamento de PDF e Imagens:** OpenCV (`opencv-python-headless`), PyMuPDF (`fitz`), ReportLab.
- **Dados e Relatórios:** Pandas, OpenPyXL.
- **Frontend:** HTML5, CSS3, Vanilla JS, Phosphor Icons.
- **Deploy:** Docker, Docker Compose.

---

## Como Rodar Localmente (Desenvolvimento) 💻

1. Clone o repositório:
   ```bash
   git clone https://github.com/meneguinha/nota10-flask.git
   cd nota10-flask
   ```
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate # (No Windows: venv\Scripts\activate)
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Rode o aplicativo:
   ```bash
   python app.py
   ```
5. Acesse `http://127.0.0.1:5000` no seu navegador.

---

## Como Fazer Deploy em Produção (Docker / Oracle Cloud) ☁️

Para uso intenso (múltiplos professores acessando ao mesmo tempo), utilize o Docker Compose. Ele já está configurado com `gunicorn` (4 workers) e política `restart: always`.

1. Na sua VPS (ex: Oracle Cloud / AWS / Digital Ocean), instale o Docker e o Docker Compose.
2. Clone o repositório e rode o comando abaixo na porta 80:
   ```bash
   sudo docker compose up -d --build
   ```
3. O sistema estará disponível diretamente pelo IP da sua máquina.

---

## Desenvolvido por
**Felipe Nunes Menegotto**
- GitHub: [github.com/meneguinha](https://github.com/meneguinha)
- Website: [www.felipemenegotto.com.br](https://www.felipemenegotto.com.br)

Gostou do projeto? Considere apoiar pelo PIX disponível no rodapé do aplicativo! ☕
