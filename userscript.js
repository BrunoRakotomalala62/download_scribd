// ==UserScript==
// @name         Scribd Downloader
// @namespace    https://github.com/ThanhNguyxn/scribd-downloader
// @version      1.1.0
// @description  📚 Download documents from Scribd for free as PDF
// @author       ThanhNguyxn
// @match        https://www.scribd.com/document/*
// @match        https://www.scribd.com/doc/*
// @match        https://www.scribd.com/embeds/*/content
// @match        https://www.scribd.com/read/*
// @icon         https://www.scribd.com/favicon.ico
// @grant        GM_addStyle
// @grant        GM_openInTab
// @license      MIT
// ==/UserScript==

(function() {
    'use strict';

    // ==================== STYLES ====================
    GM_addStyle(`
        #scribd-dl-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 99999;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 25px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        #scribd-dl-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }

        #scribd-dl-btn:active {
            transform: translateY(-1px);
        }

        #scribd-dl-btn.loading {
            opacity: 0.7;
            cursor: wait;
        }

        #scribd-dl-btn .icon {
            margin-right: 8px;
        }

        #scribd-dl-status {
            position: fixed;
            bottom: 80px;
            right: 20px;
            z-index: 99999;
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 14px;
            max-width: 300px;
            display: none;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            backdrop-filter: blur(10px);
        }

        #scribd-dl-status.show {
            display: block;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        #scribd-dl-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 999999;
            display: none;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(5px);
        }

        #scribd-dl-modal.show {
            display: flex;
        }

        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 20px;
            max-width: 500px;
            width: 90%;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .modal-content h2 {
            margin: 0 0 20px 0;
            color: #333;
            font-size: 24px;
        }

        .modal-content p {
            color: #666;
            line-height: 1.6;
            margin-bottom: 20px;
        }

        .modal-content .btn-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .modal-content button {
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .modal-content .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .modal-content .btn-secondary {
            background: #f0f0f0;
            color: #333;
        }

        .modal-content .btn-warning {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }

        .modal-content button:hover {
            transform: scale(1.05);
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
        }

        .progress-bar .progress {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 10px;
        }

        .info-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            text-align: left;
            border-radius: 0 10px 10px 0;
        }

        .info-box code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
        }
    `);

    // ==================== UTILITIES ====================

    function getDocumentId() {
        const url = window.location.href;
        // Match: /document/123456/ or /doc/123456/ or /embeds/123456/ or /read/123456/
        const match = url.match(/(?:document|doc|embeds|read)\/(\d+)/);
        return match ? match[1] : null;
    }

    function isEmbedPage() {
        return window.location.href.includes('/embeds/');
    }

    function getEmbedUrl(docId) {
        return `https://www.scribd.com/embeds/${docId}/content`;
    }

    function showStatus(message, duration = 3000) {
        let status = document.getElementById('scribd-dl-status');
        if (!status) {
            status = document.createElement('div');
            status.id = 'scribd-dl-status';
            document.body.appendChild(status);
        }
        status.textContent = message;
        status.classList.add('show');

        if (duration > 0) {
            setTimeout(() => {
                status.classList.remove('show');
            }, duration);
        }
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ==================== MAIN FUNCTIONS ====================

    async function scrollAllPages(progressCallback) {
        const pages = document.querySelectorAll("[class*='page']");
        const totalPages = pages.length;

        if (totalPages === 0) {
            // Try alternative selectors
            const altPages = document.querySelectorAll('.text_layer, .page_container, [data-page]');
            if (altPages.length > 0) {
                for (let i = 0; i < altPages.length; i++) {
                    altPages[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
                    await sleep(400);
                    if (progressCallback) {
                        progressCallback(Math.round(((i + 1) / altPages.length) * 50));
                    }
                }
                return;
            }
            // Fallback: scroll the whole page
            const scrollHeight = document.documentElement.scrollHeight;
            const steps = 20;
            for (let i = 0; i <= steps; i++) {
                window.scrollTo(0, (scrollHeight / steps) * i);
                await sleep(300);
                if (progressCallback) {
                    progressCallback(Math.round((i / steps) * 50));
                }
            }
            return;
        }

        for (let i = 0; i < pages.length; i++) {
            pages[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
            await sleep(400);
            if (progressCallback) {
                progressCallback(Math.round(((i + 1) / totalPages) * 50));
            }
        }
    }

    function removeToolbars() {
        const selectorsToRemove = [
            '.toolbar_top',
            '.toolbar_bottom',
            '.promo_div',
            '.blurred_page',
            '[class*="blur"]',
            '[class*="paywall"]',
            '[class*="overlay"]',
            '[class*="upsell"]',
            '[class*="signup"]',
            '[class*="login"]',
            '.auto_mobile_first',
            '.mobile_banner',
            '.ReactModalPortal',
            '[data-e2e="document-upsell"]'
        ];

        let removed = 0;
        selectorsToRemove.forEach(selector => {
            try {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    el.remove();
                    removed++;
                });
            } catch (e) {}
        });

        // Clean document_scroller class
        const scrollers = document.querySelectorAll('.document_scroller');
        scrollers.forEach(el => {
            el.removeAttribute('class');
        });

        return removed;
    }

    function cleanupForPrint() {
        // Remove blur effects
        document.querySelectorAll('*').forEach(el => {
            try {
                const style = window.getComputedStyle(el);
                if (style.filter && style.filter.includes('blur')) {
                    el.style.filter = 'none';
                }
                if (style.opacity && parseFloat(style.opacity) < 1) {
                    el.style.opacity = '1';
                }
            } catch (e) {}
        });

        // Make all pages visible
        document.querySelectorAll("[class*='page']").forEach(page => {
            page.style.visibility = 'visible';
            page.style.opacity = '1';
        });
    }

    function triggerPrint() {
        window.print();
    }

    // ==================== UI COMPONENTS ====================

    function createDownloadButton() {
        const btn = document.createElement('button');
        btn.id = 'scribd-dl-btn';
        btn.innerHTML = '<span class="icon">📥</span>Download PDF';
        btn.onclick = handleDownloadClick;
        document.body.appendChild(btn);
    }

    function createModal() {
        const modal = document.createElement('div');
        modal.id = 'scribd-dl-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h2>📚 Scribd Downloader</h2>
                <p id="modal-message">Preparing document...</p>
                <div class="progress-bar" id="progress-container">
                    <div class="progress" id="download-progress"></div>
                </div>
                <div id="modal-info"></div>
                <div class="btn-group" id="modal-buttons" style="display: none;">
                    <button class="btn-primary" id="btn-print">🖨️ Print/Save PDF</button>
                    <button class="btn-secondary" id="btn-close">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        document.getElementById('btn-close').onclick = () => {
            modal.classList.remove('show');
        };

        document.getElementById('btn-print').onclick = () => {
            modal.classList.remove('show');
            setTimeout(triggerPrint, 300);
        };

        return modal;
    }

    function showModal(message, showButtons = false, progress = 0, info = '') {
        let modal = document.getElementById('scribd-dl-modal');
        if (!modal) {
            modal = createModal();
        }

        document.getElementById('modal-message').textContent = message;
        document.getElementById('download-progress').style.width = progress + '%';
        document.getElementById('modal-buttons').style.display = showButtons ? 'flex' : 'none';
        document.getElementById('modal-info').innerHTML = info;
        document.getElementById('progress-container').style.display = progress >= 0 ? 'block' : 'none';
        modal.classList.add('show');
    }

    function showInfoModal(title, message, buttons = []) {
        let modal = document.getElementById('scribd-dl-modal');
        if (!modal) {
            modal = createModal();
        }

        const content = modal.querySelector('.modal-content');
        content.innerHTML = `
            <h2>${title}</h2>
            <div style="text-align: left; color: #666; line-height: 1.8;">${message}</div>
            <div class="btn-group" style="margin-top: 20px;">
                ${buttons.map(b => `<button class="${b.class || 'btn-secondary'}" onclick="${b.onclick}">${b.text}</button>`).join('')}
            </div>
        `;
        modal.classList.add('show');
    }

    function updateProgress(percent) {
        const progressEl = document.getElementById('download-progress');
        if (progressEl) {
            progressEl.style.width = percent + '%';
        }
    }

    // ==================== HANDLERS ====================

    async function handleDownloadClick() {
        const btn = document.getElementById('scribd-dl-btn');
        const docId = getDocumentId();

        if (!docId) {
            showStatus('❌ Document ID not found!');
            return;
        }

        if (!isEmbedPage()) {
            // Show info and redirect to embed page
            const embedUrl = getEmbedUrl(docId);
            
            showInfoModal(
                '📚 Scribd Downloader',
                `
                <div class="info-box">
                    <strong>ℹ️ How it works:</strong><br><br>
                    1. Click <strong>"Open Embed Page"</strong> below<br>
                    2. A new page will open with the document<br>
                    3. Click <strong>"Download PDF"</strong> button again<br>
                    4. Wait for all pages to load<br>
                    5. Save as PDF!
                </div>
                <p style="margin-top: 15px; font-size: 13px; color: #888;">
                    💡 The embed page doesn't require login and shows the full document.
                </p>
                `,
                [
                    { text: '🚀 Open Embed Page', class: 'btn-primary', onclick: `window.open('${embedUrl}', '_blank')` },
                    { text: 'Close', class: 'btn-secondary', onclick: `document.getElementById('scribd-dl-modal').classList.remove('show')` }
                ]
            );
            return;
        }

        // We're on embed page, start download process
        btn.classList.add('loading');
        btn.innerHTML = '<span class="icon">⏳</span>Processing...';

        try {
            showModal('🔄 Loading all pages...', false, 0);

            // Step 1: Scroll through all pages
            await scrollAllPages((progress) => {
                updateProgress(progress);
                showModal(`📄 Loading pages... (${progress}%)`, false, progress);
            });

            // Step 2: Remove toolbars
            showModal('🧹 Cleaning up interface...', false, 60);
            await sleep(500);
            const removed = removeToolbars();

            // Step 3: Cleanup for print
            showModal('✨ Optimizing for print...', false, 80);
            await sleep(500);
            cleanupForPrint();

            // Step 4: Ready to print
            showModal('✅ Ready! Click the button below to save PDF', true, 100);

            btn.classList.remove('loading');
            btn.innerHTML = '<span class="icon">✅</span>Ready!';

        } catch (error) {
            console.error('Scribd Downloader Error:', error);
            showModal('❌ An error occurred: ' + error.message, false, 0);
            btn.classList.remove('loading');
            btn.innerHTML = '<span class="icon">📥</span>Download PDF';
        }
    }

    // ==================== INITIALIZATION ====================

    function init() {
        // Wait for page to load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(createDownloadButton, 1000);
            });
        } else {
            setTimeout(createDownloadButton, 1000);
        }
    }

    init();

})();
