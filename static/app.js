/* ═══════════════════════════════════════════════════
   NeuralDoc — app.js
   Original logic preserved · Aurora background added
═══════════════════════════════════════════════════ */

/* ── AURORA CANVAS (runs immediately) ────────────── */
(function initAurora() {
    const canvas = document.getElementById('aurora-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H;

    const blobs = [
        { bx: 0.15, by: 0.25, r: 0.35, hue: 240, a: 0.18, ang: 0,   spd: 0.0003, drft: 0.06 },
        { bx: 0.80, by: 0.15, r: 0.30, hue: 280, a: 0.14, ang: 1,   spd: 0.0004, drft: 0.05 },
        { bx: 0.55, by: 0.75, r: 0.38, hue: 190, a: 0.12, ang: 2,   spd: 0.0003, drft: 0.07 },
        { bx: 0.10, by: 0.80, r: 0.25, hue: 260, a: 0.10, ang: 3,   spd: 0.0005, drft: 0.04 },
    ];

    function resize() {
        W = canvas.width  = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }

    function loop() {
        ctx.clearRect(0, 0, W, H);
        blobs.forEach(b => {
            b.ang += b.spd;
            const cx = (b.bx + Math.sin(b.ang) * b.drft) * W;
            const cy = (b.by + Math.cos(b.ang * 0.7) * b.drft) * H;
            const r  = b.r * Math.min(W, H);
            const g  = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
            g.addColorStop(0, `hsla(${b.hue},80%,60%,${b.a})`);
            g.addColorStop(1, `hsla(${b.hue},80%,60%,0)`);
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fillStyle = g;
            ctx.fill();
        });
        requestAnimationFrame(loop);
    }

    window.addEventListener('resize', resize);
    resize();
    loop();
})();


/* ── CARD TILT (runs immediately) ────────────────── */
document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width  - 0.5;
        const y = (e.clientY - rect.top)  / rect.height - 0.5;
        card.style.transform      = `translateY(-8px) scale(1.01) rotateX(${-y * 5}deg) rotateY(${x * 5}deg)`;
        card.style.transformStyle = 'preserve-3d';
    });
    card.addEventListener('mouseleave', () => {
        card.style.transform      = '';
        card.style.transformStyle = '';
    });
});


/* ── MAIN APP LOGIC ──────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {

    // ---- Navigation Elements ----
    const homeView     = document.getElementById('home-view');
    const pdfUploadView = document.getElementById('upload-view-pdf');
    const csvUploadView = document.getElementById('upload-view-csv');
    const chatView     = document.getElementById('chat-view');

    const btnPdfMode  = document.getElementById('btn-pdf-mode');
    const btnCsvMode  = document.getElementById('btn-csv-mode');
    const backFromPdf = document.getElementById('back-from-pdf');
    const backFromCsv = document.getElementById('back-from-csv');

    // ---- PDF Elements ----
    const dropZonePdf      = document.getElementById('drop-zone-pdf');
    const fileInputPdf     = document.getElementById('file-input-pdf');
    const uploadingStatePdf = document.getElementById('uploading-state-pdf');

    // ---- CSV Elements ----
    const dropZoneCsv      = document.getElementById('drop-zone-csv');
    const fileInputCsv     = document.getElementById('file-input-csv');
    const uploadingStateCsv = document.getElementById('uploading-state-csv');

    // ---- Chat Elements ----
    const chatForm    = document.getElementById('chat-form');
    const chatInput   = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const sendBtn     = document.getElementById('send-button');
    const themeToggle = document.getElementById('theme-toggle');
    const backBtn     = document.getElementById('back-to-home');

    // ---- Navigation ----
    backBtn.addEventListener('click', () => {
        switchView(chatView, homeView);
        currentFilename = null;
        chatHistory.innerHTML = '';
    });

    // ---- Theme Persistence ----
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.setAttribute('data-theme', savedTheme);
    themeToggle.innerHTML = `<i data-feather="${savedTheme === 'light' ? 'sun' : 'moon'}"></i>`;
    feather.replace();

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.body.getAttribute('data-theme');
        const newTheme     = currentTheme === 'light' ? 'dark' : 'light';
        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        themeToggle.innerHTML = `<i data-feather="${newTheme === 'light' ? 'sun' : 'moon'}"></i>`;
        feather.replace();
    });

    // ---- App State ----
    let currentMode     = 'pdf'; // 'pdf' or 'csv'
    let currentFilename = '';

    // ---- View Switching Logic ----
    function switchView(from, to) {
        from.classList.remove('active');
        setTimeout(() => {
            from.classList.add('hidden');
            to.classList.remove('hidden');
            setTimeout(() => to.classList.add('active'), 50);
        }, 400);
    }

    btnPdfMode.addEventListener('click', () => {
        currentMode = 'pdf';
        switchView(homeView, pdfUploadView);
    });

    btnCsvMode.addEventListener('click', () => {
        currentMode = 'csv';
        switchView(homeView, csvUploadView);
    });

    backFromPdf.addEventListener('click', () => switchView(pdfUploadView, homeView));
    backFromCsv.addEventListener('click', () => switchView(csvUploadView, homeView));

    // ---- File Upload Handlers ----

    // PDF
    dropZonePdf.addEventListener('click', () => fileInputPdf.click());
    setupDragDrop(dropZonePdf, (file) => handleFileUpload(file, 'pdf'));
    fileInputPdf.addEventListener('change', (e) => {
        if (e.target.files.length) handleFileUpload(e.target.files[0], 'pdf');
    });

    // CSV
    dropZoneCsv.addEventListener('click', () => fileInputCsv.click());
    setupDragDrop(dropZoneCsv, (file) => handleFileUpload(file, 'csv'));
    fileInputCsv.addEventListener('change', (e) => {
        if (e.target.files.length) handleFileUpload(e.target.files[0], 'csv');
    });

    function setupDragDrop(zone, callback) {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length) callback(e.dataTransfer.files[0]);
        });
    }

    async function handleFileUpload(file, mode) {
        if (mode === 'pdf' && file.type !== 'application/pdf') {
            alert('Please upload a PDF file.');
            return;
        }
        if (mode === 'csv' && !file.name.endsWith('.csv') && !file.name.endsWith('.xlsx')) {
            alert('Please upload a .csv or .xlsx file.');
            return;
        }

        const dropZone    = mode === 'pdf' ? dropZonePdf      : dropZoneCsv;
        const uploadState = mode === 'pdf' ? uploadingStatePdf : uploadingStateCsv;
        const currentView = mode === 'pdf' ? pdfUploadView     : csvUploadView;

        dropZone.classList.add('hidden');
        uploadState.classList.remove('hidden');
        animateUploadSteps(mode);

        const formData = new FormData();
        formData.append('document', file);

        const endpoint = mode === 'pdf' ? '/api/upload' : '/api/upload-csv';

        try {
            const res  = await fetch(endpoint, { method: 'POST', body: formData });
            const data = await res.json();

            if (res.ok) {
                currentFilename = data.filename || file.name;
                currentMode     = mode;

                // Transition to Chat View
                switchView(currentView, chatView);

                // Reset initial chat message based on mode
                chatHistory.innerHTML = '';
                const welcomeMsg = mode === 'pdf'
                    ? "Hello! Your PDF is indexed. What would you like to know?"
                    : `Hello! I've analyzed your spreadsheet (${currentFilename}). You can ask me about sums, trends, or specific data points.`;
                appendMessage('ai', welcomeMsg);

                setTimeout(() => chatInput.focus(), 600);
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (err) {
            alert(err.message);
            uploadState.classList.add('hidden');
            dropZone.classList.remove('hidden');
        }
    }

    // ---- Upload Step Animation ----
    function animateUploadSteps(mode) {
        const pre   = mode === 'pdf' ? 'step' : 'step-csv-';
        const steps = [1, 2, 3];
        steps.forEach((n, i) => {
            const el = document.getElementById(`${pre}${n}`);
            if (!el) return;
            setTimeout(() => {
                if (i > 0) {
                    const prev = document.getElementById(`${pre}${steps[i - 1]}`);
                    if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
                }
                el.classList.add('active');
            }, i * 900);
        });
    }

    // ---- Chat Logic ----
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value  = '';
        sendBtn.disabled = true;

        const typingId = appendTypingIndicator();

        try {
            const endpoint = currentMode === 'pdf' ? '/api/chat' : '/api/chat-csv';
            const body     = currentMode === 'pdf'
                ? { query: text }
                : { query: text, filename: currentFilename };

            const res  = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await res.json();

            removeElement(typingId);

            if (res.ok) {
                appendMessage('ai', data.answer);
            } else {
                appendMessage('ai', '⚠️ Error: ' + data.error);
            }
        } catch (err) {
            removeElement(typingId);
            appendMessage('ai', '⚠️ Network error communicating with the server.');
        } finally {
            sendBtn.disabled = false;
            chatInput.focus();
        }
    });

    function appendMessage(role, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}-message`;
        const icon = role === 'user' ? 'user' : 'cpu';

        msgDiv.innerHTML = `
            <div class="avatar"><i data-feather="${icon}"></i></div>
            <div class="message-content"></div>
        `;

        if (role === 'ai') {
            msgDiv.querySelector('.message-content').innerHTML = marked.parse(text);
        } else {
            msgDiv.querySelector('.message-content').textContent = text;
        }

        chatHistory.appendChild(msgDiv);
        feather.replace();
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function appendTypingIndicator() {
        const id     = 'typing-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai-message';
        msgDiv.id = id;
        msgDiv.innerHTML = `
            <div class="avatar"><i data-feather="cpu"></i></div>
            <div class="message-content typing">
                <span></span><span></span><span></span>
            </div>
        `;
        chatHistory.appendChild(msgDiv);
        feather.replace();
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return id;
    }

    function removeElement(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }



});