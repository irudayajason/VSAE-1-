/**
 * VSAE Frontend — Claude-style Chat Interface
 * Handles API calls, chat, ablation drawer, and view transitions.
 * Phi-2 only.
 */

const API_BASE = '';

// ── State ─────────────────────────────────────────────
let currentAblationId = null;
let chatHistory = [];
let isProcessing = false;
let drawerOpen = false;
let inChatView = false;

// ── Init ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    // Focus input on load
    const input = document.getElementById('chat-input');
    if (input) input.focus();
});

// ── Health Check ──────────────────────────────────────
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        const badge = document.getElementById('model-status-text');
        badge.textContent = `Phi-2 · ${data.device} · ${data.dtype}`;
        document.querySelector('.dot').style.background = 'var(--accent-emerald)';
    } catch (err) {
        const badge = document.getElementById('model-status-text');
        badge.textContent = 'Phi-2 · Connection error';
        document.querySelector('.dot').style.background = 'var(--accent-red)';
    }
}

// ── View Transitions ──────────────────────────────────

function switchToChatView() {
    if (inChatView) return;
    inChatView = true;

    const welcome = document.getElementById('welcome-view');
    const chatView = document.getElementById('chat-view');

    welcome.classList.add('hidden');
    chatView.classList.add('visible');

    // Focus the bottom input
    setTimeout(() => {
        const bottomInput = document.getElementById('chat-input-bottom');
        if (bottomInput) bottomInput.focus();
    }, 100);
}

function resetToWelcome() {
    inChatView = false;

    const welcome = document.getElementById('welcome-view');
    const chatView = document.getElementById('chat-view');

    welcome.classList.remove('hidden');
    chatView.classList.remove('visible');

    // Clear messages
    document.getElementById('chat-messages').innerHTML = '';
    chatHistory = [];

    // Focus the welcome input
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = '';
        input.focus();
    }

    // Update sidebar
    setActiveSidebarBtn('btn-chat');
    closeDrawer();
}

function focusChat() {
    setActiveSidebarBtn('btn-chat');
    closeDrawer();
    if (inChatView) {
        const input = document.getElementById('chat-input-bottom');
        if (input) input.focus();
    } else {
        const input = document.getElementById('chat-input');
        if (input) input.focus();
    }
}

function setActiveSidebarBtn(id) {
    document.querySelectorAll('.sidebar-btn').forEach(btn => btn.classList.remove('active'));
    const btn = document.getElementById(id);
    if (btn) btn.classList.add('active');
}

// ── Ablation Drawer ───────────────────────────────────

function toggleDrawer() {
    if (drawerOpen) {
        closeDrawer();
    } else {
        openDrawer();
    }
}

function openDrawer() {
    drawerOpen = true;
    document.getElementById('ablation-drawer').classList.add('open');
    document.getElementById('drawer-backdrop').classList.add('visible');
    setActiveSidebarBtn('btn-ablation');
}

function closeDrawer() {
    drawerOpen = false;
    document.getElementById('ablation-drawer').classList.remove('open');
    document.getElementById('drawer-backdrop').classList.remove('visible');
    if (!inChatView) {
        setActiveSidebarBtn('btn-chat');
    }
}

// ── Send Button State ─────────────────────────────────

function toggleSendBtn() {
    const welcomeInput = document.getElementById('chat-input');
    const bottomInput = document.getElementById('chat-input-bottom');
    const sendBtn = document.getElementById('send-btn');
    const sendBtnBottom = document.getElementById('send-btn-bottom');

    if (welcomeInput && sendBtn) {
        const hasText = welcomeInput.value.trim().length > 0;
        sendBtn.disabled = !hasText;
        sendBtn.classList.toggle('active', hasText);
    }
    if (bottomInput && sendBtnBottom) {
        const hasText = bottomInput.value.trim().length > 0;
        sendBtnBottom.disabled = !hasText;
        sendBtnBottom.classList.toggle('active', hasText);
    }
}

// ── Chat ──────────────────────────────────────────────

function getActiveInput() {
    if (inChatView) {
        return document.getElementById('chat-input-bottom');
    }
    return document.getElementById('chat-input');
}

async function handleSendChat() {
    const input = getActiveInput();
    const prompt = input.value.trim();
    if (!prompt || isProcessing) return;

    isProcessing = true;

    // Switch to chat view if we're on welcome
    switchToChatView();

    addChatMessage('user', prompt);
    input.value = '';
    autoResize(input);
    toggleSendBtn();

    const typingEl = addChatMessage('assistant', null, true);

    // Disable both send buttons
    disableSendBtns(true);

    try {
        const res = await fetch(`${API_BASE}/probe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                max_tokens: 100,
                temperature: 0.5
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Generation failed');

        typingEl.remove();
        addChatMessage('assistant', data.generated_text || '(empty response)');

    } catch (err) {
        typingEl.remove();
        addChatMessage('assistant', `Error: ${err.message}`);
    } finally {
        isProcessing = false;
        disableSendBtns(false);
        const activeInput = getActiveInput();
        if (activeInput) activeInput.focus();
    }
}

function sendQuickPrompt(text) {
    const input = getActiveInput();
    input.value = text;
    handleSendChat();
}

function handleChatKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSendChat();
    }
}

function disableSendBtns(disabled) {
    const btn1 = document.getElementById('send-btn');
    const btn2 = document.getElementById('send-btn-bottom');
    if (btn1) btn1.disabled = disabled;
    if (btn2) btn2.disabled = disabled;
}

// ── Ablation ──────────────────────────────────────────

async function handleAblate() {
    const forgetText = document.getElementById('forget-text').value.trim();
    if (!forgetText) return;

    const btn = document.getElementById('ablate-btn');
    btn.classList.add('loading');
    btn.disabled = true;

    const statusSection = document.getElementById('status-section');
    const emptyStatus = document.getElementById('empty-status');
    if (emptyStatus) emptyStatus.style.display = 'none';

    statusSection.querySelectorAll('.status-card').forEach(el => el.remove());
    addStatusCard(statusSection, '⏳', 'Pipeline', 'Running Phi-2 ablation pipeline... This may take a moment.', 'warning');

    try {
        const topK = parseInt(document.getElementById('top-k').value);
        const alpha = parseFloat(document.getElementById('ablation-strength').value);

        const res = await fetch(`${API_BASE}/ablate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                forget_text: forgetText,
                top_k_layers: topK,
                target_matrices: ['W_Q', 'W_K', 'W_V', 'dense', 'fc1'],
                ablation_strength: alpha
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Ablation failed');

        statusSection.querySelectorAll('.status-card').forEach(el => el.remove());

        currentAblationId = data.ablation_id;
        checkHealth();

        // 1. Layers targeted
        const layerChips = data.targeted_layers
            .map(l => `<span class="layer-chip">Layer ${l}</span>`)
            .join('');
        addStatusCard(statusSection, '🎯', 'Layers Targeted',
            `<div class="layer-chips">${layerChips}</div>`, 'success', true);

        // 2. Weights modified
        const changedCount = data.layer_results.filter(r => r.changed).length;
        addStatusCard(statusSection, '✅', 'Weights Modified',
            `${changedCount} / ${data.layer_results.length} matrices modified`, 'success');

        // 3. Before/After Proof
        if (data.proof) {
            const proofHtml = `
                <div style="margin-bottom: 6px; font-size: 11px; color: var(--text-muted);">
                    Prompt: "<strong>${escapeHtml(data.proof.probe_prefix)}</strong>"
                </div>
                <div class="proof-comparison">
                    <div class="proof-box proof-before">
                        <div class="proof-label">📗 Before Ablation</div>
                        <div class="proof-text">${escapeHtml(data.proof.before) || '(empty)'}</div>
                    </div>
                    <div class="proof-box proof-after">
                        <div class="proof-label">📕 After Ablation</div>
                        <div class="proof-text">${escapeHtml(data.proof.after) || '(empty)'}</div>
                    </div>
                </div>
            `;
            addStatusCard(statusSection, '🔍', 'Side-by-Side Proof', proofHtml, '', true);
        }

        // 4. Perplexity
        const perpChange = data.perplexity_after - data.perplexity_before;
        const perpPercent = Math.min((data.perplexity_after / Math.max(data.perplexity_before, 1)) * 10, 100);
        addStatusCard(statusSection, '📊', 'Perplexity Score',
            `<div>Before: <strong>${data.perplexity_before}</strong> → After: <strong>${data.perplexity_after}</strong></div>
             <div style="color: ${perpChange > 0 ? 'var(--accent-emerald)' : 'var(--accent-red)'}; margin-top: 4px;">
                ${perpChange > 0 ? '↑' : '↓'} ${Math.abs(perpChange).toFixed(2)} ${perpChange > 0 ? '— Concept erased ✓' : '— Minimal change'}
             </div>
             <div class="perplexity-meter">
                <div class="meter-bar"><div class="meter-fill" style="width: ${perpPercent}%"></div></div>
                <div class="meter-labels"><span>Low (knows it)</span><span>High (forgot it)</span></div>
             </div>`,
            perpChange > 0 ? 'success' : 'warning', true);

        // 5. Ablation ID
        addStatusCard(statusSection, '🔑', 'Ablation ID',
            `<span style="font-size: 10px">${data.ablation_id}</span>`, 'success');

        document.getElementById('rollback-btn').disabled = false;

    } catch (err) {
        statusSection.querySelectorAll('.status-card').forEach(el => el.remove());
        addStatusCard(statusSection, '❌', 'Error', err.message, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// ── Rollback ──────────────────────────────────────────

async function handleRollback() {
    if (!currentAblationId) return;

    const btn = document.getElementById('rollback-btn');
    btn.disabled = true;
    btn.textContent = '↩ Rolling back...';

    try {
        const res = await fetch(`${API_BASE}/rollback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ablation_id: currentAblationId })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Rollback failed');

        const statusSection = document.getElementById('status-section');
        statusSection.querySelectorAll('.status-card').forEach(el => el.remove());

        addStatusCard(statusSection, '↩', 'Rolled Back',
            `Restored ${data.restored_matrices.length} weight matrices to original state`, 'success');

        currentAblationId = null;
        btn.textContent = '↩ Rollback to Original Weights';

    } catch (err) {
        const statusSection = document.getElementById('status-section');
        addStatusCard(statusSection, '❌', 'Rollback Error', err.message, 'error');
        btn.textContent = '↩ Rollback to Original Weights';
        btn.disabled = false;
    }
}

// ── Helpers ───────────────────────────────────────────

function addChatMessage(role, text, isTyping = false) {
    const container = document.getElementById('chat-messages');
    const row = document.createElement('div');
    const rowClass = role === 'user' ? 'user-row' : 'assistant-row';
    row.className = `message-row ${rowClass}`;

    const avatar = role === 'user' ? '👤' : '✦';
    let contentHtml;

    if (isTyping) {
        contentHtml = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
    } else {
        contentHtml = escapeHtml(text);
    }

    row.innerHTML = `
        <div class="message-inner">
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">${contentHtml}</div>
        </div>
    `;

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
    return row;
}

function addStatusCard(container, icon, label, value, type = '', isHtml = false) {
    const card = document.createElement('div');
    card.className = 'status-card';

    card.innerHTML = `
        <div class="status-card-header">
            <span class="status-icon">${icon}</span>
            <span class="status-label">${label}</span>
        </div>
        <div class="status-value ${type}">
            ${isHtml ? value : escapeHtml(value)}
        </div>
    `;

    container.appendChild(card);
    return card;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
}
