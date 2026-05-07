document.addEventListener('DOMContentLoaded', () => {
    let currentResultId = null;
    
    // --- Tabs Logic ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(btn.dataset.target).classList.add('active');
        });
    });

    // --- Gabarito Logic ---
    const radiosModo = document.querySelectorAll('input[name="modo_gabarito"]');
    const modeGridContainer = document.getElementById('gabarito-grid-container');
    const modeTextContainer = document.getElementById('gabarito-text-container');
    
    radiosModo.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'grid') {
                modeGridContainer.classList.add('active');
                modeTextContainer.classList.remove('active');
            } else {
                modeTextContainer.classList.add('active');
                modeGridContainer.classList.remove('active');
            }
        });
    });

    // Generate Grid Inputs
    const inputQtd = document.getElementById('qtd_questoes_gabarito');
    const gridInputsContainer = document.getElementById('grid-inputs');

    function renderGridInputs() {
        const num = parseInt(inputQtd.value) || 0;
        gridInputsContainer.innerHTML = '';
        for (let i = 1; i <= num; i++) {
            const div = document.createElement('div');
            div.className = 'input-group';
            div.innerHTML = `
                <label>${i < 10 ? '0'+i : i}</label>
                <input type="text" maxlength="1" data-q="${i}" class="gab-input">
            `;
            gridInputsContainer.appendChild(div);
        }
    }
    
    inputQtd.addEventListener('change', renderGridInputs);
    renderGridInputs(); // init

    // Gabarito Confirmation
    let officialGabarito = {};
    const btnConfirmarGabarito = document.getElementById('btn-confirmar-gabarito');
    const feedbackGabarito = document.getElementById('feedback-gabarito');

    btnConfirmarGabarito.addEventListener('click', () => {
        officialGabarito = {};
        const modo = document.querySelector('input[name="modo_gabarito"]:checked').value;
        
        if (modo === 'grid') {
            const inputs = document.querySelectorAll('.gab-input');
            inputs.forEach(inp => {
                const val = inp.value.toUpperCase();
                if (['A','B','C','D','E'].includes(val)) {
                    officialGabarito[inp.dataset.q] = val;
                }
            });
        } else {
            const text = document.getElementById('gabarito_text').value;
            const regex = /(\d+)[^\w]*([a-eA-E])/g;
            let match;
            while ((match = regex.exec(text)) !== null) {
                officialGabarito[parseInt(match[1])] = match[2].toUpperCase();
            }
        }

        const qtdParsed = Object.keys(officialGabarito).length;
        if (qtdParsed > 0) {
            feedbackGabarito.className = 'feedback-msg success';
            feedbackGabarito.innerText = `✅ Gabarito confirmado: ${qtdParsed} questões identificadas.`;
        } else {
            feedbackGabarito.className = 'feedback-msg error';
            feedbackGabarito.innerText = `⛔ Nenhuma resposta válida identificada.`;
        }
    });

    // --- Processamento de Provas ---
    const btnProcessar = document.getElementById('btn-processar');
    const loadingOverlay = document.getElementById('loading-overlay');

    btnProcessar.addEventListener('click', async () => {
        if (Object.keys(officialGabarito).length === 0) {
            alert("Por favor, confirme o Gabarito Oficial primeiro.");
            return;
        }

        const examFiles = document.getElementById('exam_files').files;
        if (examFiles.length === 0) {
            alert("Por favor, selecione os arquivos das provas.");
            return;
        }

        const formData = new FormData();
        formData.append('gabarito_oficial', JSON.stringify(officialGabarito));
        formData.append('nota_maxima', document.getElementById('nota_maxima').value);
        
        const classListFile = document.getElementById('class_list_file').files[0];
        if (classListFile) {
            formData.append('class_list_file', classListFile);
        }

        for (let i = 0; i < examFiles.length; i++) {
            formData.append('exam_files', examFiles[i]);
        }

        const successMessage = document.getElementById('success-message');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        
        loadingOverlay.classList.remove('hidden');
        successMessage.classList.add('hidden');
        progressContainer.classList.remove('hidden');
        btnProcessar.disabled = true;

        // Simulate progress bar (assume ~2 seconds per file)
        let estimatedTime = examFiles.length * 2000;
        let progress = 0;
        progressBar.style.width = '0%';
        
        let progressInterval = setInterval(() => {
            // max simulated progress is 90%
            if (progress < 90) {
                progress += Math.max(1, 90 / (estimatedTime / 200));
                progressBar.style.width = Math.min(progress, 90) + '%';
            }
        }, 200);

        try {
            const response = await fetch('/process_exams', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || "Erro ao processar provas.");
            }

            const resultData = await response.json();
            currentResultId = resultData.result_id;

            // Finish progress
            clearInterval(progressInterval);
            progressBar.style.width = '100%';
            
            // Wait briefly before showing success and buttons to let UI update
            setTimeout(() => {
                loadingOverlay.classList.add('hidden');
                successMessage.classList.remove('hidden');
                
                const downloadActions = document.getElementById('download-actions');
                downloadActions.classList.remove('hidden');
                
                const btnRelatorio = document.getElementById('btn-download-relatorio');
                const btnLista = document.getElementById('btn-download-lista');
                const btnImagens = document.getElementById('btn-download-imagens');
                
                btnRelatorio.href = `/download/${resultData.result_id}/relatorio`;
                btnImagens.href = `/download/${resultData.result_id}/imagens`;
                
                if (resultData.has_class_list) {
                    btnLista.href = `/download/${resultData.result_id}/lista`;
                    btnLista.classList.remove('hidden');
                } else {
                    btnLista.classList.add('hidden');
                }
                
            }, 500);

        } catch (error) {
            clearInterval(progressInterval);
            loadingOverlay.classList.add('hidden');
            alert(`Erro: ${error.message}`);
        } finally {
            btnProcessar.disabled = false;
        }
    });

    // --- Cleanup Memory Cache ---
    window.addEventListener('beforeunload', () => {
        if (currentResultId) {
            const blob = new Blob([JSON.stringify({result_id: currentResultId})], {type: 'application/json'});
            navigator.sendBeacon('/cleanup', blob);
        }
    });
});
