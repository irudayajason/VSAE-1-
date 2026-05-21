/**
 * VSAE Frontend -- Dark Gold Theme
 * Handles API calls, chat, ablation drawer, and view transitions.
 */

const API_BASE = (window.location.port === '8000') ? '' : 'http://localhost:8000';

// State
let currentAblationId = null;
let chatHistory = [];
let isProcessing = false;
let drawerOpen = false;
let inChatView = false;
let pendingAblationRequest = null;

// Init
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    const input = document.getElementById('chat-input');
    if (input) input.focus();

    // Programmatically bind clear memory button to ensure it works even if inline handler fails
    const clearBtn = document.querySelector('.clear-memory-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            clearHindsightMemory();
        });
    }
});

// Health Check
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        const badge = document.getElementById('model-status-text');
        if (badge) badge.textContent = `Phi-2 -- ${data.device} -- ${data.dtype}`;
        const dot = document.querySelector('.dot');
        if (dot) dot.style.background = 'var(--green)';
        
        // Update Hindsight status indicator
        updateHindsightStatus(data.hindsight_enabled || false, data.ablation_history_count || 0);
    } catch (err) {
        console.error('Health check failed:', err);
        const badge = document.getElementById('model-status-text');
        if (badge) badge.textContent = 'Phi-2 -- Connection error';
        const dot = document.querySelector('.dot');
        if (dot) dot.style.background = 'var(--red)';
        updateHindsightStatus(false, 0);
    }
}

function updateHindsightStatus(enabled, historyCount) {
    const dot = document.getElementById('hindsight-dot');
    const text = document.getElementById('hindsight-text');
    if (!dot || !text) return;
    
    if (enabled) {
        dot.className = 'hindsight-dot active';
        const count = historyCount || 0;
        text.textContent = `Hindsight -- Active (${count})`;
        text.style.color = '';
    } else {
        dot.className = 'hindsight-dot active';  // Still active since local cache works
        text.textContent = 'Hindsight -- Local';
        text.style.color = '';
    }
}

// Sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('collapsed');
}

// View Transitions
function switchToChatView() {
    if (inChatView) return;
    inChatView = true;
    const welcome = document.getElementById('welcome-view');
    const chatView = document.getElementById('chat-view');
    if (welcome) welcome.classList.add('hidden');
    if (chatView) chatView.classList.add('visible');
    setTimeout(() => {
        const bottomInput = document.getElementById('chat-input-bottom');
        if (bottomInput) bottomInput.focus();
    }, 100);
}

function resetToWelcome() {
    inChatView = false;
    const welcome = document.getElementById('welcome-view');
    const chatView = document.getElementById('chat-view');
    if (welcome) welcome.classList.remove('hidden');
    if (chatView) chatView.classList.remove('visible');
    document.getElementById('chat-messages').innerHTML = '';
    chatHistory = [];
    const input = document.getElementById('chat-input');
    if (input) { input.value = ''; input.focus(); }
    closeDrawer();
}

function focusChat() {
    closeDrawer();
    if (inChatView) {
        const input = document.getElementById('chat-input-bottom');
        if (input) input.focus();
    } else {
        const input = document.getElementById('chat-input');
        if (input) input.focus();
    }
}

// Ablation Drawer
function toggleDrawer() {
    drawerOpen ? closeDrawer() : openDrawer();
}

function openDrawer() {
    drawerOpen = true;
    const drawer = document.getElementById('ablation-drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    if (drawer) drawer.classList.add('open');
    if (backdrop) backdrop.classList.add('visible');
}

function closeDrawer() {
    drawerOpen = false;
    const drawer = document.getElementById('ablation-drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('visible');
}

// Send Button State
function toggleSendBtn() {
    const welcomeInput = document.getElementById('chat-input');
    const bottomInput = document.getElementById('chat-input-bottom');
    const sendBtn = document.getElementById('send-btn');
    const sendBtnBottom = document.getElementById('send-btn-bottom');
    if (welcomeInput && sendBtn) {
        const hasText = welcomeInput.value.trim().length > 0;
        sendBtn.disabled = !hasText;
    }
    if (bottomInput && sendBtnBottom) {
        const hasText = bottomInput.value.trim().length > 0;
        sendBtnBottom.disabled = !hasText;
    }
}

// Chat
function getActiveInput() {
    return inChatView ? document.getElementById('chat-input-bottom') : document.getElementById('chat-input');
}

async function handleSendChat() {
    const input = getActiveInput();
    const prompt = input.value.trim();
    if (!prompt || isProcessing) return;
    isProcessing = true;
    switchToChatView();
    addChatMessage('user', prompt);
    input.value = '';
    autoResize(input);
    toggleSendBtn();
    const typingEl = addChatMessage('assistant', null, true);
    disableSendBtns(true);

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);
        const res = await fetch(`${API_BASE}/probe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, max_tokens: 100, temperature: 0.5 }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Generation failed');
        typingEl.remove();
        addChatMessage('assistant', data.generated_text || '(empty response)');
    } catch (err) {
        typingEl.remove();
        let errorMsg = err.message;
        if (err.name === 'AbortError') errorMsg = 'Request timed out. Please try again.';
        else if (err.message === 'Failed to fetch' || err instanceof TypeError)
            errorMsg = `Cannot connect to backend at ${API_BASE || 'this server'}.`;
        addChatMessage('assistant', `Error: ${errorMsg}`);
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

// Ablation
async function handleAblate(forceAblate = false) {
    const forgetText = document.getElementById('forget-text').value.trim();
    if (!forgetText) return;
    const btn = document.getElementById('ablate-btn');
    btn.classList.add('loading');
    btn.disabled = true;
    const statusSection = document.getElementById('status-section');
    const emptyStatus = document.getElementById('empty-status');
    if (emptyStatus) emptyStatus.style.display = 'none';
    statusSection.querySelectorAll('.status-card').forEach(el => el.remove());
    
    // Show initial status with smooth transition
    const pipelineCard = addStatusCard(statusSection, 'Pipeline', 'Running Phi-2 ablation pipeline...', 'warning');
    pipelineCard.style.opacity = '0';
    setTimeout(() => pipelineCard.style.opacity = '1', 10);

    try {
        const topK = parseInt(document.getElementById('top-k').value);
        const alpha = parseFloat(document.getElementById('ablation-strength').value);
        const cascadeEnabled = document.getElementById('cascade-enabled')?.checked || false;
        const cascadeThreshold = cascadeEnabled ? 50.0 : null;
        
        // Store request for potential retry
        pendingAblationRequest = {
            forget_text: forgetText,
            top_k_layers: topK,
            target_matrices: ['W_Q', 'W_K', 'W_V'],
            ablation_strength: alpha,
            force_ablate: forceAblate,
            cascade_threshold: cascadeThreshold
        };
        
        const res = await fetch(`${API_BASE}/ablate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pendingAblationRequest)
        });
        const data = await res.json();
        
        // Check for overlap warning (Hindsight feature)
        if (data.status === 'warning') {
            showOverlapModal(data);
            btn.classList.remove('loading');
            btn.disabled = false;
            statusSection.querySelectorAll('.status-card').forEach(el => el.remove());
            if (emptyStatus) emptyStatus.style.display = 'block';
            return;
        }
        
        // Show cascade exhaustion warning (CascadeFlow now always proceeds)
        if (data.cascade_exhausted) {
            addStatusCard(statusSection, 'CascadeFlow Note', data.cascade_message || 'CascadeFlow tried shifted layers but used original.', 'warning', true);
        }
        
        if (!res.ok) throw new Error(data.detail || 'Ablation failed');
        statusSection.querySelectorAll('.status-card').forEach(el => el.remove());
        currentAblationId = data.ablation_id;
        checkHealth();
        
        // Show CascadeFlow info if it was triggered
        if (data.cascade_triggered) {
            const cascadeHtml = `
                <div style="color: var(--gold); font-weight: 600; margin-bottom: 8px;">
                    🔄 CascadeFlow Activated
                </div>
                <div style="font-size: 12px; line-height: 1.6;">
                    Initial ablation exceeded ${cascadeThreshold}% degradation threshold.<br>
                    Automatically shifted layers by ${data.cascade_shift > 0 ? '+' : ''}${data.cascade_shift} and retried.<br>
                    <strong>Result:</strong> ${data.perplexity_degradation_pct.toFixed(1)}% degradation (within threshold)
                </div>
                <div style="margin-top: 8px; font-size: 11px; color: var(--text-dim);">
                    Original layers: ${data.original_layers.join(', ')}<br>
                    Final layers: ${data.final_layers.join(', ')}
                </div>
            `;
            addStatusCard(statusSection, 'CascadeFlow', cascadeHtml, 'success', true);
        }

        // Layers targeted
        const layerChips = data.targeted_layers.map(l => `<span class="layer-chip">Layer ${l}</span>`).join('');
        addStatusCard(statusSection, 'Layers Targeted', `<div class="layer-chips">${layerChips}</div>`, 'success', true);

        // Weights modified
        const changedCount = data.layer_results.filter(r => r.changed).length;
        addStatusCard(statusSection, 'Weights Modified', `${changedCount} / ${data.layer_results.length} matrices modified`, 'success');

        // Before/After Proof
        if (data.proof) {
            const proofHtml = `
                <div style="margin-bottom:6px;font-size:11px;color:var(--text-dim);">Prompt: "<strong>${escapeHtml(data.proof.probe_prefix)}</strong>"</div>
                <div class="proof-comparison">
                    <div class="proof-box proof-before">
                        <div class="proof-label">Before Ablation</div>
                        <div class="proof-text">${escapeHtml(data.proof.before) || '(empty)'}</div>
                    </div>
                    <div class="proof-box proof-after">
                        <div class="proof-label">After Ablation</div>
                        <div class="proof-text">${escapeHtml(data.proof.after) || '(empty)'}</div>
                    </div>
                </div>`;
            addStatusCard(statusSection, 'Side-by-Side Proof', proofHtml, '', true);
        }

        // Perplexity
        const perpChange = data.perplexity_after - data.perplexity_before;
        const perpPercent = Math.min((data.perplexity_after / Math.max(data.perplexity_before, 1)) * 10, 100);
        addStatusCard(statusSection, 'Perplexity Score',
            `<div>Before: <strong>${data.perplexity_before}</strong> -> After: <strong>${data.perplexity_after}</strong></div>
             <div style="color:${perpChange > 0 ? 'var(--green)' : 'var(--red)'}; margin-top:4px;">
                ${perpChange > 0 ? '+' : '-'} ${Math.abs(perpChange).toFixed(2)} ${perpChange > 0 ? '-- Concept erased' : '-- Minimal change'}
             </div>
             <div class="perplexity-meter">
                <div class="meter-bar"><div class="meter-fill" style="width:${perpPercent}%"></div></div>
                <div class="meter-labels"><span>Low (knows it)</span><span>High (forgot it)</span></div>
             </div>`,
            perpChange > 0 ? 'success' : 'warning', true);

        // Ablation ID
        addStatusCard(statusSection, 'Ablation ID', `<span style="font-size:10px">${data.ablation_id}</span>`, 'success');
        document.getElementById('rollback-btn').disabled = false;

        // Add to sidebar history
        addSidebarEntry(forgetText);
        
        // Clear pending request after success
        pendingAblationRequest = null;
    } catch (err) {
        statusSection.querySelectorAll('.status-card').forEach(el => el.remove());
        addStatusCard(statusSection, 'Error', err.message, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// Overlap Warning Modal
function showOverlapModal(warningData) {
    const modal = document.getElementById('overlap-modal');
    const messageEl = document.getElementById('overlap-message');
    const pastConceptEl = document.getElementById('overlap-past-concept');
    const similarityEl = document.getElementById('overlap-similarity');
    const degradationEl = document.getElementById('overlap-degradation');
    
    if (messageEl) messageEl.textContent = warningData.message || 'Semantic overlap detected with a past ablation.';
    if (pastConceptEl) pastConceptEl.textContent = warningData.past_concept || 'Unknown';
    if (similarityEl) similarityEl.textContent = `${(warningData.similarity * 100).toFixed(1)}%`;
    if (degradationEl) degradationEl.textContent = `${warningData.historical_perplexity_degradation}% perplexity increase`;
    
    if (modal) modal.style.display = 'flex';
}

function closeOverlapModal() {
    const modal = document.getElementById('overlap-modal');
    if (modal) modal.style.display = 'none';
    pendingAblationRequest = null;
}

function proceedWithAblation() {
    // Save before closeOverlapModal nullifies it
    const savedRequest = pendingAblationRequest;
    closeOverlapModal();
    if (savedRequest) {
        handleAblate(true);
    }
}

// Rollback
async function handleRollback() {
    if (!currentAblationId) return;
    const btn = document.getElementById('rollback-btn');
    btn.disabled = true;
    btn.textContent = 'Rolling back...';
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
        addStatusCard(statusSection, 'Rolled Back', `Restored ${data.restored_matrices.length} weight matrices`, 'success');
        currentAblationId = null;
        btn.textContent = 'Rollback to Original Weights';
    } catch (err) {
        const statusSection = document.getElementById('status-section');
        addStatusCard(statusSection, 'Rollback Error', err.message, 'error');
        btn.textContent = 'Rollback to Original Weights';
        btn.disabled = false;
    }
}

// Helpers
function addChatMessage(role, text, isTyping = false) {
    const container = document.getElementById('chat-messages');
    const row = document.createElement('div');
    row.className = `message-row ${role === 'user' ? 'user-row' : 'assistant-row'}`;
    const avatar = role === 'user' ? 'U' : 'V';
    let contentHtml = isTyping
        ? '<div class="typing-dots"><span></span><span></span><span></span></div>'
        : escapeHtml(text);
    row.innerHTML = `
        <div class="message-inner">
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">${contentHtml}</div>
        </div>`;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
    return row;
}

function addStatusCard(container, label, value, type = '', isHtml = false) {
    const card = document.createElement('div');
    card.className = 'status-card';
    card.innerHTML = `
        <div class="status-card-header">
            <span class="status-label">${label}</span>
        </div>
        <div class="status-value ${type}">
            ${isHtml ? value : escapeHtml(value)}
        </div>`;
    container.appendChild(card);
    return card;
}

function addSidebarEntry(text) {
    const hist = document.getElementById('sidebar-history');
    if (!hist) return;
    const item = document.createElement('div');
    item.className = 'sidebar-history-item';
    const label = text.length > 30 ? text.substring(0, 30) + '...' : text;
    item.innerHTML = `<span>${escapeHtml(label)}</span><button class="more-btn">...</button>`;
    hist.prepend(item);
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

async function clearHindsightMemory() {
    if (!confirm("Are you sure you want to clear the ablation history? This cannot be undone.")) {
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/history/clear`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error("Failed to clear memory");
        
        // Re-check health to update the badge
        checkHealth();
    } catch (err) {
        console.error("Error clearing memory:", err);
        alert("Failed to clear memory: " + err.message);
    }
}
