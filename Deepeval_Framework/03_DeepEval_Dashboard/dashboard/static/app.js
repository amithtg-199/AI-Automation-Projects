// DeepEval Framework UI Dashboard JavaScript Engine

document.addEventListener('DOMContentLoaded', () => {
    let metricsData = [];
    let currentCategory = 'all';

    const gridEl = document.getElementById('metricsGrid');
    const filterPillsEl = document.getElementById('filterPills');
    const runAllBtn = document.getElementById('runAllBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const saveConfigBtn = document.getElementById('saveConfigBtn');

    const geminiKeyInput = document.getElementById('geminiKey');
    const mistralKeyInput = document.getElementById('mistralKey');
    const providerSelect = document.getElementById('providerSelect');
    const modelSelect = document.getElementById('modelSelect');

    const totalMetricsEl = document.getElementById('totalMetricsCount');
    const passedCountEl = document.getElementById('passedCount');
    const failedCountEl = document.getElementById('failedCount');
    const avgScoreEl = document.getElementById('avgScoreVal');
    const totalTokensEl = document.getElementById('totalTokensVal');

    // Initialize Dashboard
    init();

    async function init() {
        await fetchConfig();
        await fetchMetrics();
        setupEventListeners();
    }

    async function fetchConfig() {
        try {
            const resp = await fetch('/api/config');
            const data = await resp.json();
            if (data.active_provider) providerSelect.value = data.active_provider;
            if (data.active_model) modelSelect.value = data.active_model;
        } catch (e) {
            console.error('Error fetching config:', e);
        }
    }

    async function fetchMetrics() {
        try {
            const resp = await fetch('/api/metrics');
            metricsData = await resp.json();
            renderGrid();
            await updateSummaryStats();
        } catch (e) {
            console.error('Error fetching metrics:', e);
            gridEl.innerHTML = `<div class="loading-state"><p style="color:#ef4444">Failed to load metrics from server.</p></div>`;
        }
    }

    async function updateSummaryStats() {
        try {
            const resp = await fetch('/api/summary');
            const summary = await resp.json();
            totalMetricsEl.textContent = summary.total_metrics || 25;
            passedCountEl.textContent = summary.passed_count || 0;
            failedCountEl.textContent = summary.failed_count || 0;
            avgScoreEl.textContent = (summary.average_score || 0).toFixed(2);
            totalTokensEl.textContent = (summary.token_usage?.total_tokens || 0).toLocaleString();
        } catch (e) {
            console.error('Error updating summary:', e);
        }
    }

    function setupEventListeners() {
        // Filter pills
        filterPillsEl.addEventListener('click', (e) => {
            if (e.target.classList.contains('filter-pill')) {
                document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
                e.target.classList.add('active');
                currentCategory = e.target.dataset.category;
                renderGrid();
            }
        });

        // Save Config
        saveConfigBtn.addEventListener('click', async () => {
            const payload = {
                gemini_key: geminiKeyInput.value.trim() || undefined,
                mistral_key: mistralKeyInput.value.trim() || undefined,
                active_provider: providerSelect.value,
                active_model: modelSelect.value,
            };
            saveConfigBtn.textContent = 'Saving...';
            try {
                await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                alert('API Keys and Model settings saved!');
            } catch (e) {
                alert('Failed to save configuration: ' + e);
            } finally {
                saveConfigBtn.textContent = 'Save Keys';
            }
        });

        // Refresh Grid
        refreshBtn.addEventListener('click', () => {
            fetchMetrics();
        });

        // Run All Metrics
        runAllBtn.addEventListener('click', async () => {
            runAllBtn.disabled = true;
            
            for (let i = 0; i < metricsData.length; i++) {
                const spec = metricsData[i];
                runAllBtn.innerHTML = `<span class="btn-icon">⏳</span> (${i + 1}/${metricsData.length}) ${spec.name}...`;
                await runSingleMetric(spec.id, true);
            }

            await updateSummaryStats();
            runAllBtn.disabled = false;
            runAllBtn.innerHTML = `<span class="btn-icon">▶</span> Run All 25 Metrics`;
        });
    }

    function renderGrid() {
        const filtered = metricsData.filter(m => {
            if (currentCategory === 'all') return true;
            return m.category === currentCategory;
        });

        if (filtered.length === 0) {
            gridEl.innerHTML = `<div class="loading-state"><p>No metrics found in category "${currentCategory}".</p></div>`;
            return;
        }

        gridEl.innerHTML = filtered.map(m => createCardHTML(m)).join('');

        // Attach click handlers to Run buttons
        document.querySelectorAll('.run-card-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.dataset.id;
                btn.disabled = true;
                btn.textContent = 'Evaluating...';
                await runSingleMetric(id, true);
            });
        });
    }

    async function runSingleMetric(metricId, updateStats = true) {
        const idx = metricsData.findIndex(m => m.id === metricId);
        if (idx !== -1) {
            metricsData[idx].evaluating = true;
            renderGrid();
        }

        try {
            const resp = await fetch('/api/run-metric', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    metric_id: metricId,
                    provider: providerSelect.value,
                    model: modelSelect.value,
                    api_key: (providerSelect.value === 'gemini' ? geminiKeyInput.value : mistralKeyInput.value) || undefined
                })
            });

            const result = await resp.json();

            if (idx !== -1) {
                metricsData[idx].evaluating = false;
                metricsData[idx].result = result;
            }

            renderGrid();
            if (updateStats) await updateSummaryStats();
        } catch (e) {
            if (idx !== -1) metricsData[idx].evaluating = false;
            console.error(`Error running metric ${metricId}:`, e);
        }
    }

    function createCardHTML(m) {
        const res = m.result;
        const targetClass = m.target === 'Chatbot' ? 'target-chatbot' : 'target-rag';
        
        let statusBadge = `<span class="status-badge status-pending">UNTESTED</span>`;
        if (m.evaluating) {
            statusBadge = `<span class="status-badge status-evaluating" style="background:#3b82f6; color:#ffffff; animation: pulse 1s infinite;">⏳ EVALUATING</span>`;
        }
        let scoreDisplay = `<span class="score-num">--</span>`;
        let progressWidth = 0;
        let progressClass = 'progress-fill-pass';
        let reasonText = m.description;
        let tokenText = `Token Usage: Not run yet`;
        let latencyText = `-- ms`;

        if (res) {
            const isPass = res.passed;
            statusBadge = isPass 
                ? `<span class="status-badge status-pass">PASS</span>` 
                : `<span class="status-badge status-fail">FAIL</span>`;
            
            const scoreVal = (res.score !== undefined ? res.score : 0).toFixed(3);
            const scoreClass = isPass ? 'score-pass' : 'score-fail';
            scoreDisplay = `<span class="score-num ${scoreClass}">${scoreVal}</span>`;
            
            progressWidth = Math.min(100, Math.max(0, (res.score || 0) * 100));
            progressClass = isPass ? 'progress-fill-pass' : 'progress-fill-fail';
            reasonText = res.reason || 'Evaluation completed.';
            
            if (res.token_usage) {
                tokenText = `${res.token_usage.formatted || res.token_usage.total_tokens + ' tokens'}`;
            }
            if (res.latency_ms) {
                latencyText = `${res.latency_ms} ms`;
            }
        }

        const tickLeft = (m.threshold * 100).toFixed(1);

        return `
            <div class="metric-card" id="card-${m.id}">
                <div>
                    <div class="card-header">
                        <span class="target-badge ${targetClass}">${m.target}</span>
                        ${statusBadge}
                    </div>

                    <h3 class="card-title">${m.name}</h3>
                    <p class="card-desc">${m.description}</p>

                    <div class="score-box">
                        <div class="score-text">
                            <div>Score ${scoreDisplay}</div>
                            <div class="threshold-num">${m.comparison} ${m.threshold.toFixed(2)} Thresh</div>
                        </div>

                        <div class="progress-container">
                            <div class="progress-fill ${progressClass}" style="width: ${progressWidth}%"></div>
                            <div class="threshold-tick" style="left: ${tickLeft}%" title="Threshold: ${m.threshold}"></div>
                        </div>
                    </div>

                    <div class="scale-hint">💡 ${m.scale_hint}</div>
                    <div class="token-meter-box">📊 ${tokenText}</div>
                    <div class="reason-box"><strong>Judge Reason:</strong> ${reasonText}</div>
                </div>

                <div class="card-footer">
                    <span class="latency-tag">⏱️ ${latencyText}</span>
                    <button class="btn btn-primary btn-sm run-card-btn" data-id="${m.id}">Run Test</button>
                </div>
            </div>
        `;
    }
});
