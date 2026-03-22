/* ═══════════════════════════════════════════════════
   NeuralDoc — app.js  (Terminal Noir)
   All original Flask logic preserved + new footer
═══════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    // ---- Navigation Elements ----
    const homeView      = document.getElementById('home-view');
    const pdfUploadView = document.getElementById('upload-view-pdf');
    const csvUploadView = document.getElementById('upload-view-csv');
    const urlUploadView = document.getElementById('upload-view-url');
    const chatView      = document.getElementById('chat-view');

    const btnPdfMode  = document.getElementById('btn-pdf-mode');
    const btnCsvMode  = document.getElementById('btn-csv-mode');
    const btnUrlMode  = document.getElementById('btn-url-mode');
    const backFromPdf = document.getElementById('back-from-pdf');
    const backFromCsv = document.getElementById('back-from-csv');
    const backFromUrl = document.getElementById('back-from-url');

    // ---- PDF Elements ----
    const dropZonePdf       = document.getElementById('drop-zone-pdf');
    const fileInputPdf      = document.getElementById('file-input-pdf');
    const uploadingStatePdf = document.getElementById('uploading-state-pdf');

    // ---- CSV Elements ----
    const dropZoneCsv       = document.getElementById('drop-zone-csv');
    const fileInputCsv      = document.getElementById('file-input-csv');
    const uploadingStateCsv = document.getElementById('uploading-state-csv');

    // ---- Chat Elements ----
    const chatForm    = document.getElementById('chat-form');
    const chatInput   = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const sendBtn     = document.getElementById('send-button');
    const themeToggle = document.getElementById('theme-toggle');
    const backBtn     = document.getElementById('back-to-home');

    // ---- App State ----
    let currentMode     = 'pdf';
    let currentFilename = '';

    // ── THEME ─────────────────────────────────────────
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    themeToggle.addEventListener('click', () => {
        const cur  = document.documentElement.getAttribute('data-theme');
        const next = cur === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        // Re-run feather so SVG stroke colours inherit the new CSS variables
        if (window.feather) feather.replace();
    });

    // ── BACK FROM CHAT ────────────────────────────────
    backBtn.addEventListener('click', () => {
        switchView(chatView, homeView);
        currentFilename = null;
        chatHistory.innerHTML = '';
        document.getElementById('recommendations-container').classList.add('hidden');
    });

    // ── VIEW SWITCHING ────────────────────────────────
    function switchView(from, to) {
        from.classList.remove('active');
        setTimeout(() => {
            from.classList.add('hidden');
            to.classList.remove('hidden');
            setTimeout(() => to.classList.add('active'), 50);
        }, 400);
    }

    btnPdfMode.addEventListener('click', () => { currentMode = 'pdf'; switchView(homeView, pdfUploadView); });
    btnCsvMode.addEventListener('click', () => { currentMode = 'csv'; switchView(homeView, csvUploadView); });
    btnUrlMode.addEventListener('click', () => { currentMode = 'url'; switchView(homeView, urlUploadView); });

    backFromPdf.addEventListener('click', () => switchView(pdfUploadView, homeView));
    backFromCsv.addEventListener('click', () => switchView(csvUploadView, homeView));
    backFromUrl.addEventListener('click', () => switchView(urlUploadView, homeView));

    // ── URL FORM ──────────────────────────────────────
    const urlForm          = document.getElementById('url-form');
    const urlInput         = document.getElementById('url-input');
    const uplodingStateUrl = document.getElementById('uploading-state-url');
    const urlSubmitBtn     = document.getElementById('url-submit-btn');

    urlForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        let rawUrl = urlInput.value.trim();
        if (!rawUrl) return;
        if (!rawUrl.startsWith('http://') && !rawUrl.startsWith('https://')) {
            rawUrl = 'https://' + rawUrl;
        }

        urlSubmitBtn.disabled = true;
        urlForm.closest('.url-input-box').classList.add('hidden');
        uplodingStateUrl.classList.remove('hidden');
        animateSteps('url');

        try {
            const res  = await fetch('/api/scrape-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: rawUrl })
            });
            const data = await res.json();

            if (res.ok) {
                currentFilename = data.filename;
                currentMode     = 'url';

                const topbarMode = document.getElementById('topbar-mode');
                if (topbarMode) topbarMode.textContent = 'WEB MODE';

                switchView(urlUploadView, chatView);
                chatHistory.innerHTML = '';
                const wordCount = data.word_count ? String(data.word_count) : "Unknown";

                appendMessage(
                    'ai',
                    `Hello! I've read the page: **${data.title}** (${wordCount} words). What would you like to know about it?`
                );                setTimeout(() => chatInput.focus(), 600);
            } else {
                throw new Error(data.error || 'Scraping failed');
            }
        } catch (err) {
            alert(err.message);
            uplodingStateUrl.classList.add('hidden');
            urlForm.closest('.url-input-box').classList.remove('hidden');
        } finally {
            urlSubmitBtn.disabled = false;
        }
    });

    // ── FILE UPLOAD HANDLERS ──────────────────────────
    dropZonePdf.addEventListener('click', () => fileInputPdf.click());
    setupDragDrop(dropZonePdf, (file) => handleFileUpload(file, 'pdf'));
    fileInputPdf.addEventListener('change', (e) => {
        if (e.target.files.length) handleFileUpload(e.target.files[0], 'pdf');
    });

    dropZoneCsv.addEventListener('click', () => fileInputCsv.click());
    setupDragDrop(dropZoneCsv, (file) => handleFileUpload(file, 'csv'));
    fileInputCsv.addEventListener('change', (e) => {
        if (e.target.files.length) handleFileUpload(e.target.files[0], 'csv');
    });

    function setupDragDrop(zone, callback) {
        zone.addEventListener('dragover',  (e) => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', ()  => zone.classList.remove('dragover'));
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

        const dropZone    = mode === 'pdf' ? dropZonePdf       : dropZoneCsv;
        const uploadState = mode === 'pdf' ? uploadingStatePdf : uploadingStateCsv;
        const currentView = mode === 'pdf' ? pdfUploadView      : csvUploadView;

        dropZone.classList.add('hidden');
        uploadState.classList.remove('hidden');
        animateSteps(mode);

        const formData = new FormData();
        formData.append('document', file);

        const endpoint = mode === 'pdf' ? '/api/upload' : '/api/upload-csv';

        try {
            const res  = await fetch(endpoint, { method: 'POST', body: formData });
            
            let data;
            const contentType = res.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                data = await res.json();
            } else {
                const text = await res.text();
                throw new Error(`Server Error (${res.status}): ${text.slice(0, 100)}...`);
            }

            if (res.ok) {
                currentFilename = data.filename || file.name;
                currentMode     = mode;

                const topbarMode = document.getElementById('topbar-mode');
                if (topbarMode) topbarMode.textContent = mode === 'pdf' ? 'PDF MODE' : 'CSV MODE';

                switchView(currentView, chatView);
                chatHistory.innerHTML = '';

                const welcomeMsg = mode === 'pdf'
                    ? 'Hello! Your PDF is indexed. What would you like to know?'
                    : `Hello! I've analyzed your spreadsheet (${currentFilename}). You can ask me about sums, trends, or specific data points.`;
                appendMessage('ai', welcomeMsg);

                fetchRecommendations(currentFilename, mode);
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

    // ── STEP ANIMATOR ─────────────────────────────────
    function animateSteps(mode) {
        let pre;
        if (mode === 'pdf')      pre = 'step';
        else if (mode === 'csv') pre = 'step-csv-';
        else                     pre = 'step-url-';

        [1, 2, 3].forEach((n, i) => {
            const el = document.getElementById(`${pre}${n}`);
            if (!el) return;
            setTimeout(() => {
                if (i > 0) {
                    const prev = document.getElementById(`${pre}${[1,2,3][i - 1]}`);
                    if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
                }
                el.classList.add('active');
            }, i * 900);
        });
    }

    // ── CHAT LOGIC ────────────────────────────────────
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value  = '';
        sendBtn.disabled = true;

        const typingId = appendTypingIndicator();

        try {
            const endpoint = currentMode === 'pdf' ? '/api/chat'
                           : currentMode === 'csv' ? '/api/chat-csv'
                           : '/api/chat-url';
            const body     = { query: text, filename: currentFilename };

            const res  = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            let data;
            const contentType = res.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                data = await res.json();
            } else {
                const text = await res.text();
                throw new Error(`Server Error (${res.status}): ${text.slice(0, 100)}...`);
            }

            removeElement(typingId);
            appendMessage('ai', res.ok ? data.answer : '⚠️ Error: ' + data.error);
        } catch (err) {
            removeElement(typingId);
            appendMessage('ai', '⚠️ Network error communicating with the server.');
        } finally {
            sendBtn.disabled = false;
            chatInput.focus();
        }
    });

    function appendMessage(role, text) {
        const wrap = document.createElement('div');
        wrap.className = `message ${role}-message`;

        if (role === 'ai') {
            wrap.innerHTML = `
                <div class="avatar"><i data-feather="cpu"></i></div>
                <div class="msg-body">
                    <div class="msg-label mono">SYSTEM</div>
                    <div class="message-content"></div>
                </div>`;
            wrap.querySelector('.message-content').innerHTML = marked.parse(text);
        } else {
            wrap.innerHTML = `
                <div class="avatar"><i data-feather="user"></i></div>
                <div class="msg-body">
                    <div class="msg-label mono">YOU</div>
                    <div class="message-content"></div>
                </div>`;
            wrap.querySelector('.message-content').textContent = text;
        }

        chatHistory.appendChild(wrap);
        feather.replace();
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function appendTypingIndicator() {
        const id   = 'typing-' + Date.now();
        const wrap = document.createElement('div');
        wrap.className = 'message ai-message';
        wrap.id = id;
        wrap.innerHTML = `
            <div class="avatar"><i data-feather="cpu"></i></div>
            <div class="msg-body">
                <div class="msg-label mono">SYSTEM</div>
                <div class="typing"><span></span><span></span><span></span></div>
            </div>`;
        chatHistory.appendChild(wrap);
        feather.replace();
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return id;
    }

    function removeElement(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    // ── RECOMMENDATIONS ───────────────────────────────
    async function fetchRecommendations(filename, mode) {
        const container = document.getElementById('recommendations-container');
        const chipsArea = document.getElementById('chips-area');
        chipsArea.innerHTML = '';
        container.classList.add('hidden');

        if (mode !== 'csv') {
            return;
        }

        try {
            const res  = await fetch('/api/recommendations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, mode })
            });
            const data = await res.json();

            if (res.ok && data.questions && data.questions.length > 0) {
                container.classList.remove('hidden');
                data.questions.forEach(q => {
                    const chip = document.createElement('div');
                    chip.className = 'suggestion-chip';
                    chip.innerHTML = `<i data-feather="trending-up"></i><span>${q}</span>`;
                    chip.addEventListener('click', () => {
                        chatInput.value = q;
                        chatForm.dispatchEvent(new Event('submit'));
                        container.classList.add('hidden');
                    });
                    chipsArea.appendChild(chip);
                });
                feather.replace();
            }
        } catch (err) {
            console.error('Failed to fetch recommendations', err);
        }
    }

    // ── FOOTER NAV LINKS ──────────────────────────────
    const footPdf = document.getElementById('foot-pdf');
    const footCsv = document.getElementById('foot-csv');
    const footUrl = document.getElementById('foot-url');

    if (footPdf) footPdf.addEventListener('click', () => { currentMode = 'pdf'; switchView(homeView, pdfUploadView); });
    if (footCsv) footCsv.addEventListener('click', () => { currentMode = 'csv'; switchView(homeView, csvUploadView); });
    if (footUrl) footUrl.addEventListener('click', () => { currentMode = 'url'; switchView(homeView, urlUploadView); });

    // ── FOOTER VISIBILITY — IntersectionObserver ──────
    // The footer lives inside .home-layout (scrollable).
    // We observe the footer element itself: as soon as even
    // 10% of it enters the viewport (i.e. user scrolled down
    // enough to see the cards), we add .visible to trigger
    // the fade-in CSS transition.
    const siteFooter = document.querySelector('.site-footer');
    const homeLayout = document.querySelector('.home-layout');

    if (siteFooter && homeLayout) {
        // IntersectionObserver root = the scrolling container
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        siteFooter.classList.add('visible');
                    } else {
                        // Optional: remove 'visible' when scrolled back up
                        // so it re-animates on next scroll-down.
                        siteFooter.classList.remove('visible');
                    }
                });
            },
            {
                root: homeLayout,   // scroll container
                threshold: 0.08     // trigger when 8% visible
            }
        );

        observer.observe(siteFooter);
    }

    // ── INIT FEATHER ──────────────────────────────────
    if (window.feather) feather.replace();

});