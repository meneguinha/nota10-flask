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

        progressBar.style.width = '0%';
        const loadingText = document.getElementById('loading-text');
        loadingText.innerText = "Iniciando processamento...";

        try {
            const response = await fetch('/process_exams', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || "Erro ao iniciar processamento.");
            }

            const resultData = await response.json();
            const taskId = resultData.task_id;
            
            // Polling
            let pollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`/status/${taskId}`);
                    if (!statusRes.ok) throw new Error("Erro ao checar status.");
                    const statusData = await statusRes.json();
                    
                    if (statusData.status === "processing") {
                        progressBar.style.width = statusData.progress + '%';
                        loadingText.innerText = `Processando: ${statusData.current} de ${statusData.total} páginas...`;
                    } else if (statusData.status === "completed") {
                        clearInterval(pollInterval);
                        progressBar.style.width = '100%';
                        loadingText.innerText = "Finalizando arquivos...";
                        
                        currentResultId = taskId;
                        
                        setTimeout(() => {
                            loadingOverlay.classList.add('hidden');
                            successMessage.classList.remove('hidden');
                            
                            const downloadActions = document.getElementById('download-actions');
                            downloadActions.classList.remove('hidden');
                            
                            const btnRelatorio = document.getElementById('btn-download-relatorio');
                            const btnLista = document.getElementById('btn-download-lista');
                            const btnImagens = document.getElementById('btn-download-imagens');
                            
                            btnRelatorio.href = `/download/${taskId}/relatorio`;
                            btnImagens.href = `/download/${taskId}/imagens`;
                            
                            if (statusData.has_class_list) {
                                btnLista.href = `/download/${taskId}/lista`;
                                btnLista.classList.remove('hidden');
                            } else {
                                btnLista.classList.add('hidden');
                            }
                            
                            btnProcessar.disabled = false;
                        }, 500);
                    } else if (statusData.status === "error") {
                        clearInterval(pollInterval);
                        throw new Error(statusData.error || "Erro interno no processamento.");
                    }
                } catch (err) {
                    clearInterval(pollInterval);
                    loadingOverlay.classList.add('hidden');
                    alert(`Erro: ${err.message}`);
                    btnProcessar.disabled = false;
                }
            }, 1000);

        } catch (error) {
            loadingOverlay.classList.add('hidden');
            alert(`Erro: ${error.message}`);
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
