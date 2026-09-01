// Frontend Logic for PostScript (.ps) to PDF Converter

document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');

    // UI States
    const uploadPrompt = document.getElementById('uploadPrompt');
    const processingState = document.getElementById('processingState');
    const resultState = document.getElementById('resultState');
    const errorState = document.getElementById('errorState');

    // Result elements
    const originalFileName = document.getElementById('originalFileName');
    const pdfFileName = document.getElementById('pdfFileName');
    const originalSize = document.getElementById('originalSize');
    const pdfSize = document.getElementById('pdfSize');
    const conversionTime = document.getElementById('conversionTime');
    const downloadBtn = document.getElementById('downloadBtn');
    const convertAnotherBtn = document.getElementById('convertAnotherBtn');

    // Error elements
    const errorMessage = document.getElementById('errorMessage');
    const retryBtn = document.getElementById('retryBtn');

    // Processing elements
    const processingFileName = document.getElementById('processingFileName');
    const progressBar = document.getElementById('progressBar');

    if (!dropzone || !fileInput) return;

    // Trigger file dialog
    if (selectFileBtn) {
        selectFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
    }

    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag & Drop events
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dropzone-active');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dropzone-active');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
            handleFile(dt.files[0]);
        }
    });

    // Reset buttons
    if (convertAnotherBtn) {
        convertAnotherBtn.addEventListener('click', resetView);
    }
    if (retryBtn) {
        retryBtn.addEventListener('click', resetView);
    }

    function resetView() {
        fileInput.value = '';
        uploadPrompt.classList.remove('hidden');
        processingState.classList.add('hidden');
        resultState.classList.add('hidden');
        errorState.classList.add('hidden');
        progressBar.style.width = '0%';
    }

    function showError(msg) {
        uploadPrompt.classList.add('hidden');
        processingState.classList.add('hidden');
        resultState.classList.add('hidden');
        errorState.classList.remove('hidden');
        errorMessage.textContent = msg || 'Ocurrió un error inesperado al procesar el archivo.';
    }

    function handleFile(file) {
        const validExtensions = ['.ps', '.eps'];
        const fileName = file.name.toLowerCase();
        const hasValidExt = validExtensions.some(ext => fileName.endsWith(ext));

        if (!hasValidExt) {
            showError('Formato no soportado. Por favor selecciona un archivo con extensión .ps o .eps.');
            return;
        }

        const maxBytes = 32 * 1024 * 1024; // 32MB
        if (file.size > maxBytes) {
            showError('El archivo excede el tamaño máximo permitido de 32 MB.');
            return;
        }

        // Switch to processing UI
        uploadPrompt.classList.add('hidden');
        errorState.classList.add('hidden');
        resultState.classList.add('hidden');
        processingState.classList.remove('hidden');

        processingFileName.textContent = file.name;
        progressBar.style.width = '25%';

        const formData = new FormData();
        formData.append('file', file);

        let simulatedProgress = 25;
        const progressInterval = setInterval(() => {
            if (simulatedProgress < 85) {
                simulatedProgress += 10;
                progressBar.style.width = `${simulatedProgress}%`;
            }
        }, 150);

        fetch('/api/convert', {
            method: 'POST',
            body: formData
        })
        .then(async response => {
            clearInterval(progressInterval);
            progressBar.style.width = '100%';

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || `Error del servidor (${response.status})`);
            }
            return data;
        })
        .then(res => {
            setTimeout(() => {
                showSuccess(res.data);
            }, 300);
        })
        .catch(err => {
            clearInterval(progressInterval);
            showError(err.message);
        });
    }

    function showSuccess(data) {
        processingState.classList.add('hidden');
        uploadPrompt.classList.add('hidden');
        errorState.classList.add('hidden');
        resultState.classList.remove('hidden');

        originalFileName.textContent = data.original_filename;
        pdfFileName.textContent = data.pdf_filename;
        originalSize.textContent = data.original_size;
        pdfSize.textContent = data.pdf_size;
        conversionTime.textContent = `${data.conversion_time_ms} ms`;

        downloadBtn.onclick = () => {
            window.location.href = data.download_url;
        };
    }
});
