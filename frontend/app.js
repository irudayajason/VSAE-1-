/**
 * VSAE Frontend — Client-side logic
 * Handles API calls, chat, ablation workflow, model switching,
 * and side-by-side before/after proof display.
 */

const API_BASE = '';

// ── State ─────────────────────────────────────────────
let currentAblationId = null;
let chatHistory = [];
let isProcessing = false;

// ── Init ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
});

// ── Health Check ──────────────────────────────────────
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        const badge = document.getElementById('model-status-text');
        const modelName = data.model.includes('/') ? data.model.split('/')[1] : data.model;
        badge.textContent = `${modelName} · ${data.device} · ${(data.parameters / 1e6).toFixed(0)}M params`;
    } catch (err) {
        const badge = document.getElementById('model-status-text');
        badge.textContent = 'Connection error';
        document.querySelector('.status-dot').style.background = 'var(--accent-red)';
    }
}

// ── Model Switching ───────────────────────────────────
function handleModelChange() {
    const select = document.getElementById('model-select');
    const modelId = select.value;
    const displayName = select.options[select.selectedIndex].text;

    // Update chat panel title
    document.getElementById('chat-panel-title').textContent = `Chat with ${displayName.split(' (')[0]}`;
    document.getElementById('chat-welcome-title').textContent = `Talk to ${displayName.split(' (')[0]}`;

    // Show loading hint
    const badge = document.getElementById('model-status-text');
    badge.textContent = `Switching to ${displayName}...`;
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

    addStatusCard(statusSection, '⏳', 'Pipeline', 'Running ablation pipeline... This may take a moment for larger models.', 'warning');

    try {
        const topK = parseInt(document.getElementById('top-k').value);
        const modelId = document.getElementById('model-select').value;

        const res = await fetch(`${API_BASE}/ablate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                forget_text: forgetText,
                model_id: modelId,
                top_k_layers: topK,
                target_matrices: ['W_Q', 'W_K', 'W_V']
            })
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Ablation failed');

        // Clear processing card
        statusSection.querySelectorAll('.status-card').forEach(el => el.remove());

        currentAblationId = data.ablation_id;

        // Update health badge with new model info
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

        // 3. Before/After Proof (side-by-side)
        if (data.proof) {
            const proofHtml = `
                <div style="margin-bottom: 8px; font-size: 12px; color: var(--text-muted);">
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
                ${perpChange > 0 ? '↑' : '↓'} ${Math.abs(perpChange).toFixed(2)} ${perpChange > 0 ? '— Model is confused (concept erased ✓)' : '— Minimal change'}
             </div>
             <div class="perplexity-meter">
                <div class="meter-bar"><div class="meter-fill" style="width: ${perpPercent}%"></div></div>
                <div class="meter-labels"><span>Low (knows it)</span><span>High (forgot it)</span></div>
             </div>`,
            perpChange > 0 ? 'success' : 'warning', true);

        // 5. Ablation ID
        addStatusCard(statusSection, '🔑', 'Ablation ID',
            `<span style="font-size: 11px">${data.ablation_id}</span>`, 'success');

        // Enable rollback
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
        const modelId = document.getElementById('model-select').value;
        const res = await fetch(`${API_BASE}/rollback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ablation_id: currentAblationId, model_id: modelId })
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

// ── Chat ──────────────────────────────────────────────
async function handleSendChat() {
    const input = document.getElementById('chat-input');
    const prompt = input.value.trim();
    if (!prompt || isProcessing) return;

    isProcessing = true;

    const welcome = document.getElementById('chat-welcome');
    if (welcome) welcome.style.display = 'none';

    addChatMessage('user', prompt);
    input.value = '';
    autoResize(input);

    const typingEl = addChatMessage('assistant', null, true);
    document.getElementById('send-btn').disabled = true;

    try {
        const modelId = document.getElementById('model-select').value;

        const res = await fetch(`${API_BASE}/probe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                max_tokens: 100,
                temperature: 0.5,
                model_id: modelId
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Generation failed');

        typingEl.remove();
        addChatMessage('assistant', data.generated_text || '(empty response)');

        // Update health badge (model may have switched)
        checkHealth();

    } catch (err) {
        typingEl.remove();
        addChatMessage('assistant', `Error: ${err.message}`);
    } finally {
        isProcessing = false;
        document.getElementById('send-btn').disabled = false;
        document.getElementById('chat-input').focus();
    }
}

function sendQuickPrompt(text) {
    document.getElementById('chat-input').value = text;
    handleSendChat();
}

function handleChatKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSendChat();
    }
}

// ── Helpers ───────────────────────────────────────────

function addChatMessage(role, text, isTyping = false) {
    const chatBody = document.getElementById('chat-body');
    const msgEl = document.createElement('div');
    msgEl.className = `chat-message ${role}`;

    const avatar = role === 'user' ? '👤' : '🤖';
    let bubbleContent;

    if (isTyping) {
        bubbleContent = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
    } else {
        bubbleContent = escapeHtml(text);
    }

    msgEl.innerHTML = `
        <div class="chat-avatar">${avatar}</div>
        <div class="chat-bubble">${bubbleContent}</div>
    `;

    chatBody.appendChild(msgEl);
    chatBody.scrollTop = chatBody.scrollHeight;
    return msgEl;
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
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}
