/* ═══════════════════════════════════════════════════════════════════════════
   GenAI Vehicle HMI Dashboard — Application Logic
   ═══════════════════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;
let pollInterval = null;

// ── Tab Navigation ──────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', e => {
        e.preventDefault();
        const tab = item.dataset.tab;
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.getElementById(`tab-${tab}`).classList.add('active');
        const titles = {
            dashboard: 'Dashboard', codegen: 'Code Generator',
            analytics: 'Predictive Analytics', alerts: 'Alerts',
            ml: 'ML Training', ota: 'OTA Updates'
        };
        document.getElementById('page-title').textContent = titles[tab] || tab;

        // Auto-refresh specific tab data
        if (tab === 'ota') {
            if (typeof fetchOTAHistory === 'function') fetchOTAHistory();
        }
    });
});

// ── Clock ───────────────────────────────────────────────────────────────────
function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// ── Simulation Controls ─────────────────────────────────────────────────────
document.getElementById('btn-start-sim').addEventListener('click', async () => {
    try {
        const variant = document.getElementById('variant-select').value;
        const res = await fetch(`${API_BASE}/vehicle/simulate/start?variant=${variant}`, { method: 'POST' });
        if (res.ok) {
            document.getElementById('btn-start-sim').style.display = 'none';
            document.getElementById('btn-stop-sim').style.display = 'block';
            const pill = document.getElementById('sim-status');
            pill.textContent = `● Running (${variant})`;
            pill.classList.add('running');
            startPolling();
        }
    } catch (err) { console.error('Start sim failed:', err); }
});

document.getElementById('btn-stop-sim').addEventListener('click', async () => {
    try {
        const res = await fetch(`${API_BASE}/vehicle/simulate/stop`, { method: 'POST' });
        if (res.ok) {
            document.getElementById('btn-stop-sim').style.display = 'none';
            document.getElementById('btn-start-sim').style.display = 'block';
            const pill = document.getElementById('sim-status');
            pill.textContent = '● Idle';
            pill.classList.remove('running');
            stopPolling();
        }
    } catch (err) { console.error('Stop sim failed:', err); }
});

// ── WebSocket + Polling ─────────────────────────────────────────────────────
let ws = null;
let wsConnected = false;

function connectWebSocket() {
    try {
        const wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws/telemetry';
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
            wsConnected = true;
            console.log('WebSocket connected — live streaming');
            stopPolling(); // Stop HTTP polling, WS takes over
        };
        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'telemetry' && msg.data) {
                    updateDashboardFromWS(msg.data);
                }
            } catch (e) { /* ignore parse errors */ }
        };
        ws.onclose = () => {
            wsConnected = false;
            ws = null;
            console.log('WebSocket disconnected — falling back to polling');
            startPolling();
        };
        ws.onerror = () => { ws.close(); };
    } catch (e) {
        console.log('WebSocket not available, using polling');
    }
}

function updateDashboardFromWS(data) {
    // Re-use the existing updateDashboard by reshaping WS data
    const shaped = {
        speed: data.speed,
        battery: {
            soc: data.battery_soc, voltage: data.battery_voltage,
            temperature: data.battery_temp, health_status: data.battery_health
        },
        tires: data.tires,
        engine_status: data.engine_status,
        odometer: data.odometer,
        timestamp: data.timestamp,
        vehicle_variant: data.vehicle_variant,
        drivetrain: { throttle_position: data.throttle, brake_position: data.brake, gear: data.gear },
        ev_status: { ev_range: data.ev_range },
    };
    updateDashboard(shaped);
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    if (!wsConnected) {
        pollInterval = setInterval(fetchTelemetry, 1000);
        fetchTelemetry();
    }
    connectWebSocket(); // Always try WS upgrade
}

function stopPolling() {
    if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
    if (ws) { try { ws.close(); } catch (e) { } ws = null; wsConnected = false; }
}

async function fetchTelemetry() {
    try {
        const [telRes, alertRes] = await Promise.all([
            fetch(`${API_BASE}/vehicle/all`),
            fetch(`${API_BASE}/vehicle/alerts?limit=20`),
        ]);
        if (telRes.ok) updateDashboard(await telRes.json());
        if (alertRes.ok) updateAlerts(await alertRes.json());
    } catch (err) { console.error('Fetch error:', err); }
}

// ── Dashboard Update ────────────────────────────────────────────────────────
function updateDashboard(data) {
    // Speed
    const speed = data.speed || 0;
    document.getElementById('speed-val').textContent = Math.round(speed);
    const pct = Math.min(1, speed / 140);
    const offset = 251 * (1 - pct);
    const arc = document.getElementById('speed-arc');
    arc.style.strokeDashoffset = offset;
    arc.style.stroke = speed > 100 ? '#ef4444' : speed > 60 ? '#f59e0b' : '#3b82f6';

    // Battery
    const batt = data.battery || {};
    const soc = batt.soc || 0;
    document.getElementById('battery-val').textContent = Math.round(soc);
    const battFill = document.getElementById('battery-fill');
    battFill.style.width = soc + '%';
    battFill.style.background = soc < 20 ? 'linear-gradient(90deg, #ef4444, #f59e0b)' :
        soc < 50 ? 'linear-gradient(90deg, #f59e0b, #22c55e)' :
            'linear-gradient(90deg, #22c55e, #06b6d4)';
    document.getElementById('battery-sub').textContent =
        `${(batt.voltage || 0).toFixed(0)}V · ${(batt.temperature || 0).toFixed(0)}°C · ${batt.health_status || 'N/A'}`;

    // EV Range
    const ev = data.ev_status || {};
    document.getElementById('ev-range-val').textContent = Math.round(ev.ev_range || 0);
    document.getElementById('ev-regen').textContent = ev.regen_braking ? 'Regen: Active ♻️' : 'Regen: Off';

    // Tires
    const tires = data.tires || {};
    updateTire('tire-fl', tires.front_left);
    updateTire('tire-fr', tires.front_right);
    updateTire('tire-rl', tires.rear_left);
    updateTire('tire-rr', tires.rear_right);

    // Drivetrain
    const dt = data.drivetrain || {};
    document.getElementById('throttle-bar').style.width = (dt.throttle_position || 0) + '%';
    document.getElementById('throttle-val').textContent = Math.round(dt.throttle_position || 0) + '%';
    document.getElementById('brake-bar').style.width = (dt.brake_position || 0) + '%';
    document.getElementById('brake-val').textContent = Math.round(dt.brake_position || 0) + '%';
    document.getElementById('gear-val').textContent = dt.gear_position || 'P';
    document.getElementById('steering-val').textContent = Math.round(dt.steering_angle || 0) + '°';

    // GPS
    const gps = data.gps || {};
    document.getElementById('gps-lat').textContent = (gps.latitude || 0).toFixed(6);
    document.getElementById('gps-lon').textContent = (gps.longitude || 0).toFixed(6);

    // Odometer
    document.getElementById('odo-val').textContent = (data.odometer || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function updateTire(id, pressure) {
    const el = document.getElementById(id);
    const val = el.querySelector('.tire-val');
    val.textContent = (pressure || 0).toFixed(1);
    el.classList.remove('warning', 'critical');
    if (pressure < 25) el.classList.add('critical');
    else if (pressure < 28) el.classList.add('warning');
}

// ── Alerts Update (flicker-free) ────────────────────────────────────────────
let _lastAlertHash = '';

function updateAlerts(alerts) {
    const container = document.getElementById('alerts-list');
    const badge = document.getElementById('alert-badge');
    badge.textContent = alerts.length;

    // Build a hash of current alerts to detect actual changes
    const alertHash = alerts.map(a => `${a.severity}|${a.alert_type}|${a.timestamp}`).join(';');

    // Skip DOM update if nothing changed
    if (alertHash === _lastAlertHash) return;
    _lastAlertHash = alertHash;

    if (!alerts.length) {
        container.innerHTML = '<p class="placeholder-text">No alerts yet.</p>';
        return;
    }

    // Remove .slice().reverse() since backend already sends newest first.
    // This fixes the bug where users had to scroll down to see new alerts.
    container.innerHTML = alerts.map(a => `
        <div class="alert-item ${a.severity === 'critical' ? 'critical' : ''}">
            <div class="alert-type">
                ${a.severity.toUpperCase()} — ${a.alert_type.replace(/_/g, ' ')}
                ${a.source === 'OTA' ? '<span class="badge" style="background:#8b5cf6; margin-left: 8px;">OTA Module</span>' : ''}
            </div>
            <div class="alert-msg">${a.message}</div>
            <div class="alert-time">${new Date(a.timestamp).toLocaleTimeString()}</div>
        </div>
    `).join('');
}

// ── Code Generation ─────────────────────────────────────────────────────────
document.getElementById('btn-generate').addEventListener('click', () => generateCode('single'));
document.getElementById('btn-gen-all').addEventListener('click', () => generateCode('all'));
document.getElementById('btn-gen-design').addEventListener('click', () => generateCode('design'));
document.getElementById('btn-gen-test').addEventListener('click', () => generateCode('test'));

async function generateCode(mode) {
    const req = document.getElementById('codegen-input').value.trim();
    if (!req) return alert('Enter a requirement first.');

    const lang = document.getElementById('codegen-lang').value;
    const card = document.getElementById('codegen-output-card');
    const label = document.getElementById('codegen-output-label');
    const meta = document.getElementById('codegen-meta');
    const output = document.getElementById('codegen-output');

    card.style.display = 'block';
    output.textContent = 'Generating...';
    meta.textContent = '';

    try {
        let url, body;
        if (mode === 'single') {
            url = `${API_BASE}/codegen/generate`;
            body = { requirement: req, language: lang };
        } else if (mode === 'all') {
            url = `${API_BASE}/codegen/generate-all`;
            body = { requirement: req };
        } else if (mode === 'design') {
            url = `${API_BASE}/codegen/design`;
            body = { requirement: req };
        } else {
            url = `${API_BASE}/codegen/test`;
            body = { requirement: req, language: lang };
        }

        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        const data = await res.json();

        if (mode === 'single') {
            const gc = data.generated_code;
            label.textContent = `Generated: ${gc.language_name}`;
            meta.textContent = `${gc.lines_of_code} lines · ${gc.generation_method} · ${gc.generation_time_ms}ms`;
            output.textContent = gc.code;

            // Add OTA deploy button for single generation
            const deployBtn = document.createElement('button');
            deployBtn.className = 'btn btn-primary';
            deployBtn.style = 'background:linear-gradient(135deg,#06b6d4,#0891b2);font-weight:600; float: right; margin-top: -30px;';
            deployBtn.innerHTML = '🚀 Deploy via OTA';
            deployBtn.onclick = () => autoDeployToOTA(gc.code, gc.language, true, 'single-deploy-btn');

            // Remove old button if exists to prevent duplicates
            const oldBtn = document.getElementById('single-deploy-btn');
            if (oldBtn) oldBtn.remove();

            deployBtn.id = 'single-deploy-btn';
            meta.appendChild(deployBtn);

        } else if (mode === 'all') {
            label.textContent = `Generated All Languages (${data.total_lines} lines)`;
            meta.textContent = `Total: ${data.total_time_ms}ms`;
            output.textContent = data.generated_files.map(f =>
                `${'═'.repeat(60)}\n${f.language_name} (${f.lines_of_code} lines, ${f.generation_method})\n${'═'.repeat(60)}\n${f.code}\n`
            ).join('\n');
        } else if (mode === 'design') {
            const dd = data.design_document;
            label.textContent = 'Design Document';
            meta.textContent = `${dd.generation_method} · ${dd.generation_time_ms}ms`;
            output.textContent = dd.content;
        } else {
            const gt = data.generated_test;
            label.textContent = `Generated Tests: ${gt.language_name}`;
            meta.textContent = `${gt.test_count} tests · ${gt.generation_method} · ${gt.generation_time_ms}ms`;
            output.textContent = gt.code;
        }
    } catch (err) {
        output.textContent = 'Error: ' + err.message;
    }
}

// ── Compliance Check ────────────────────────────────────────────────────────
document.getElementById('btn-compliance').addEventListener('click', async () => {
    console.log('Compliance check button clicked');
    const codeOutput = document.getElementById('codegen-output').textContent;
    const compCard = document.getElementById('compliance-output-card');
    const compMeta = document.getElementById('compliance-meta');
    const compResults = document.getElementById('compliance-results');

    // If no code generated yet, try generating C++ first
    let codeToCheck = codeOutput;
    if (!codeToCheck || codeToCheck === 'Generating...' || codeToCheck.startsWith('Error')) {
        const req = document.getElementById('codegen-input').value.trim();
        if (!req) { alert('Enter a requirement and generate C++ code first.'); return; }

        // Auto-generate C++ code first
        try {
            const res = await fetch(`${API_BASE}/codegen/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ requirement: req, language: 'cpp' }),
            });
            const data = await res.json();
            codeToCheck = data.generated_code.code;
            // Also show the generated code
            const outputCard = document.getElementById('codegen-output-card');
            outputCard.style.display = 'block';
            document.getElementById('codegen-output-label').textContent = `Generated: ${data.generated_code.language_name}`;
            document.getElementById('codegen-meta').textContent = `${data.generated_code.lines_of_code} lines · ${data.generated_code.generation_method} · ${data.generated_code.generation_time_ms}ms`;
            document.getElementById('codegen-output').textContent = codeToCheck;
        } catch (err) {
            alert('Failed to generate code: ' + err.message);
            return;
        }
    }

    compCard.style.display = 'block';
    compMeta.textContent = 'Checking compliance...';
    compResults.innerHTML = '<p class="placeholder-text">Analyzing code against MISRA C++:2008 & AUTOSAR rules...</p>';

    try {
        const res = await fetch(`${API_BASE}/compliance/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: codeToCheck }),
        });
        const data = await res.json();

        // Summary meta
        const passColor = data.compliance_percentage >= 80 ? '#22c55e' : data.compliance_percentage >= 50 ? '#f59e0b' : '#ef4444';
        compMeta.innerHTML = `
            <span style="color:${passColor};font-weight:700;font-size:1.2em">${data.compliance_percentage.toFixed(1)}% Compliant</span> · 
            ${data.rules_passed}/${data.total_rules_checked} rules passed · 
            ASPICE Level: <strong>${data.aspice_level}</strong> · 
            <span style="color:#ef4444">${data.rules_failed} violation(s)</span>
        `;

        // Violations list
        if (data.violations && data.violations.length > 0) {
            compResults.innerHTML = data.violations.map(v => `
                <div class="alert-item ${v.severity === 'required' || v.severity === 'critical' ? 'critical' : 'warning'}">
                    <div class="alert-type">${v.severity.toUpperCase()} — ${v.rule_id}</div>
                    <div class="alert-msg">${v.rule_description}</div>
                    <div class="alert-msg" style="color:#94a3b8;font-size:0.85em">Line ${v.line_number}: <code>${v.line_content}</code></div>
                    <div class="alert-msg" style="color:#f59e0b">${v.message}</div>
                </div>
            `).join('');
        } else {
            compResults.innerHTML = '<div class="alert-item"><div class="alert-type" style="color:#22c55e">✅ ALL RULES PASSED</div><div class="alert-msg">Code is fully compliant with MISRA C++:2008 and AUTOSAR guidelines.</div></div>';
        }
    } catch (err) {
        compMeta.textContent = 'Error';
        compResults.innerHTML = `<div class="alert-item critical"><div class="alert-msg">Compliance check failed: ${err.message}</div></div>`;
    }
});

// ── Validate & Auto-Fix (Iterative Build Pipeline) ──────────────────────────
document.getElementById('btn-validate').addEventListener('click', async () => {
    console.log('Validate & Auto-Fix clicked');
    const req = document.getElementById('codegen-input').value.trim();
    if (!req) { alert('Enter a requirement first.'); return; }

    const lang = document.getElementById('codegen-lang').value;
    const valCard = document.getElementById('validate-output-card');
    const valMeta = document.getElementById('validate-meta');
    const valResults = document.getElementById('validate-results');
    const valCode = document.getElementById('validate-code-output');

    valCard.style.display = 'block';
    valMeta.textContent = '⏳ Running iterative validation pipeline...';
    valResults.innerHTML = '<p class="placeholder-text">Generating code → Generating tests → Executing tests → Auto-fixing errors (up to 3 retries)...</p>';
    valCode.style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/codegen/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ requirement: req, language: lang, max_retries: 3 }),
        });
        const data = await res.json();

        // Summary — match backend field names
        const passed = data.final_success || false;
        const statusColor = passed ? '#22c55e' : '#ef4444';
        const statusIcon = passed ? '✅' : '❌';
        const totalIter = data.total_iterations || 1;
        const retries = Math.max(0, totalIter - 1);
        const improvement = data.improvement || {};

        valMeta.innerHTML = `
            <span style="color:${statusColor};font-weight:700;font-size:1.2em">${statusIcon} ${passed ? 'ALL TESTS PASSED' : 'TESTS FAILED'}</span> · 
            Iterations: <strong>${totalIter}</strong> · 
            Pass rate: <strong>${improvement.initial_pass_rate || 0}% → ${improvement.final_pass_rate || 0}%</strong> · 
            Language: <strong>${lang}</strong>
        `;

        // Build step-by-step results
        let html = '';

        // Step 1: Code Generation
        const srcInfo = data.source_code || {};
        html += `<div class="alert-item"><div class="alert-type">Step 1 — Code Generation</div>
                  <div class="alert-msg">✅ Generated ${srcInfo.lines || '?'} lines of ${lang} code</div></div>`;

        // Step 2: Test Generation
        const testInfo = data.test_code || {};
        html += `<div class="alert-item"><div class="alert-type">Step 2 — Test Generation</div>
                  <div class="alert-msg">✅ Auto-generated ${testInfo.lines || '?'} lines of tests (${testInfo.method || 'auto'})</div></div>`;

        // Step 3: Test Execution
        if (passed) {
            html += `<div class="alert-item"><div class="alert-type" style="color:#22c55e">Step 3 — Test Execution</div>
                      <div class="alert-msg">✅ All tests passed${retries > 0 ? ` (after ${retries} auto-fix attempt${retries > 1 ? 's' : ''})` : ' on first try'}</div></div>`;
        } else {
            html += `<div class="alert-item critical"><div class="alert-type">Step 3 — Test Execution</div>
                      <div class="alert-msg">❌ Tests failed after ${retries} auto-fix attempt${retries !== 1 ? 's' : ''}</div></div>`;
        }

        // Show iteration history
        if (data.iterations && Array.isArray(data.iterations)) {
            data.iterations.forEach((iter, i) => {
                const tr = iter.test_result || {};
                const iterPassed = tr.success || false;
                const iterStatus = iterPassed ? '✅' : '🔄';
                const passRate = tr.pass_rate != null ? `${tr.pass_rate}%` : 'N/A';
                const action = iter.action === 'initial_generation' ? 'Initial Generation' :
                    iter.action === 'iterative_fix' ? 'LLM Auto-Fix' :
                        iter.action === 'skip_no_llm' ? 'Skipped (no LLM)' :
                            iter.action || 'Unknown';
                html += `<div class="alert-item ${iterPassed ? '' : 'warning'}">
                    <div class="alert-type">${iterStatus} Iteration ${iter.iteration || i + 1} — ${action}</div>
                    <div class="alert-msg">Passed: ${tr.passed || 0} · Failed: ${tr.failed || 0} · Errors: ${tr.errors || 0} · Pass rate: ${passRate}</div>
                    ${iter.message ? `<div class="alert-msg" style="color:#f59e0b">${iter.message}</div>` : ''}
                    ${iter.error ? `<div class="alert-msg" style="color:#ef4444">${iter.error}</div>` : ''}
                </div>`;
            });
        }

        valResults.innerHTML = html;

        // Show the final code
        const finalCode = (data.source_code && data.source_code.code) || data.final_code || data.code || '';
        if (finalCode) {
            valCode.style.display = 'block';
            valCode.textContent = finalCode;

            // Show Deploy via OTA button and attach code
            const deployBtn = document.getElementById('btn-deploy-ota');
            if (deployBtn) {
                deployBtn.style.display = 'inline-block';
                deployBtn.onclick = () => autoDeployToOTA(finalCode, lang, passed, 'btn-deploy-ota');
            }
        }
    } catch (err) {
        valMeta.textContent = 'Error';
        valResults.innerHTML = `<div class="alert-item critical"><div class="alert-msg">Validation pipeline failed: ${err.message}</div></div>`;
    }
});

async function autoDeployToOTA(code, lang, passed, buttonId = 'btn-deploy-ota') {
    if (!passed) {
        if (!confirm("This code failed validation. Are you sure you want to deploy it?")) {
            return;
        }
    }

    const deployBtn = document.getElementById(buttonId);
    const originalText = deployBtn ? deployBtn.innerHTML : '🚀 Deploy via OTA';
    if (deployBtn) {
        deployBtn.innerHTML = '⏳ Deploying...';
        deployBtn.disabled = true;
    }

    try {
        const payload = {
            module_name: `ai_module_${Date.now()}`,
            language: lang,
            code: code
        };

        const res = await fetch(`${API_BASE}/ota/deploy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                update_type: 'code_module',
                payload: payload,
                description: `Auto-deployed AI generated ${lang.toUpperCase()} module`
            }),
        });

        const data = await res.json();

        if (data.success) {
            if (deployBtn) {
                deployBtn.innerHTML = '✅ Deployed v' + data.version;
                deployBtn.classList.remove('btn-primary');
                deployBtn.style.background = '#22c55e';

                // Flash success
                setTimeout(() => {
                    deployBtn.innerHTML = originalText;
                    deployBtn.style.background = 'linear-gradient(135deg,#06b6d4,#0891b2)';
                    deployBtn.disabled = false;
                }, 3000);
            } else {
                alert('Successfully deployed OTA version v' + data.version);
            }
        } else {
            alert('Failed to deploy: ' + (data.error || 'Unknown error'));
            if (deployBtn) {
                deployBtn.innerHTML = originalText;
                deployBtn.disabled = false;
            }
        }
    } catch (err) {
        alert('Deploy error: ' + err.message);
        if (deployBtn) {
            deployBtn.innerHTML = originalText;
            deployBtn.disabled = false;
        }
    }
}

// ── Build Check (Syntax / Compile) ──────────────────────────────────────────
document.getElementById('btn-build').addEventListener('click', async () => {
    console.log('Build Check clicked');
    const codeOutput = document.getElementById('codegen-output').textContent;
    const lang = document.getElementById('codegen-lang').value;
    const valCard = document.getElementById('validate-output-card');
    const valMeta = document.getElementById('validate-meta');
    const valResults = document.getElementById('validate-results');

    let codeToCheck = codeOutput;
    if (!codeToCheck || codeToCheck === 'Generating...' || codeToCheck.startsWith('Error')) {
        alert('Generate code first, then click Build Check.'); return;
    }

    // Strip markdown code fences if present (LLM sometimes wraps output)
    codeToCheck = codeToCheck.trim();
    if (codeToCheck.startsWith('```')) {
        const lines = codeToCheck.split('\n');
        lines.shift(); // remove opening ```lang
        if (lines.length && lines[lines.length - 1].trim() === '```') lines.pop();
        codeToCheck = lines.join('\n').trim();
    }

    valCard.style.display = 'block';
    valMeta.textContent = '⏳ Running build/compile check...';
    valResults.innerHTML = '<p class="placeholder-text">Checking syntax and compilation...</p>';

    try {
        const res = await fetch(`${API_BASE}/codegen/build`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: codeToCheck, language: lang }),
        });
        const data = await res.json();

        const success = data.build_success || data.success || data.valid || false;
        const statusColor = success ? '#22c55e' : '#ef4444';
        const statusIcon = success ? '✅' : '❌';

        valMeta.innerHTML = `
            <span style="color:${statusColor};font-weight:700;font-size:1.2em">${statusIcon} ${success ? 'BUILD PASSED' : 'BUILD FAILED'}</span> · 
            Language: <strong>${data.language || lang}</strong> · 
            Compiler: <strong>${data.compiler || 'syntax check'}</strong>
        `;

        let html = '';
        if (success) {
            html += `<div class="alert-item"><div class="alert-type" style="color:#22c55e">✅ Build Successful</div>
                      <div class="alert-msg">${data.message || 'Code passed syntax and compilation checks.'}</div></div>`;
        } else {
            html += `<div class="alert-item critical"><div class="alert-type">❌ Build Failed</div>
                      <div class="alert-msg">${data.message || 'Compilation errors detected.'}</div></div>`;
        }

        // Show warnings or details
        if (data.warnings && data.warnings.length > 0) {
            data.warnings.forEach(w => {
                html += `<div class="alert-item warning"><div class="alert-type">⚠️ Warning</div>
                          <div class="alert-msg">${w}</div></div>`;
            });
        }
        if (data.errors && data.errors.length > 0) {
            data.errors.forEach(e => {
                html += `<div class="alert-item critical"><div class="alert-type">❌ Error</div>
                          <div class="alert-msg"><code>${e}</code></div></div>`;
            });
        }
        if (data.details) {
            html += `<div class="alert-item"><div class="alert-type">Details</div>
                      <div class="alert-msg">${typeof data.details === 'string' ? data.details : JSON.stringify(data.details, null, 2)}</div></div>`;
        }

        valResults.innerHTML = html;
    } catch (err) {
        valMeta.textContent = 'Error';
        valResults.innerHTML = `<div class="alert-item critical"><div class="alert-msg">Build check failed: ${err.message}</div></div>`;
    }
});

// ── Vehicle Variant ─────────────────────────────────────────────────────────
document.getElementById('variant-select').addEventListener('change', e => {
    const variant = e.target.value;
    const evCard = document.getElementById('card-ev-range');
    evCard.style.display = variant === 'ICE' ? 'none' : 'block';
});

// ── Predictive Analytics Polling ────────────────────────────────────────────
async function fetchPredictiveAnalysis() {
    try {
        const res = await fetch(`${API_BASE}/predictive/analysis`);
        if (!res.ok) return;
        const data = await res.json();

        const predList = document.getElementById('predictions-list');
        if (data.predictions && data.predictions.length > 0) {
            predList.innerHTML = data.predictions.map(p => `
                <div class="alert-item ${p.severity === 'critical' ? 'critical' : p.severity === 'warning' ? 'warning' : ''}">
                    <div class="alert-type">${p.severity.toUpperCase()} — ${p.signal}</div>
                    <div class="alert-msg">${p.message}</div>
                    <div class="alert-time">Confidence: ${Math.round(p.confidence * 100)}%</div>
                </div>
            `).join('');
        } else if (data.data_points > 0) {
            predList.innerHTML = '<p class="placeholder-text">All readings nominal. No warnings.</p>';
        }

        if (data.driving_score) {
            const ds = data.driving_score;
            document.getElementById('overall-score').textContent = Math.round(ds.overall);
            document.getElementById('score-speed').textContent = Math.round(ds.speed);
            document.getElementById('score-braking').textContent = Math.round(ds.braking);
            document.getElementById('score-efficiency').textContent = Math.round(ds.efficiency);
            const circle = document.querySelector('.score-circle');
            if (circle) {
                const score = ds.overall;
                circle.style.borderColor = score >= 80 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';
            }
        }
    } catch (err) { console.error('Predictive fetch error:', err); }
}

setInterval(fetchPredictiveAnalysis, 3000);

// ═══════════════════════════════════════════════════════════════════════════
// Chart.js Trend Charts
// ═══════════════════════════════════════════════════════════════════════════
let speedBatteryChart = null;
let tireChart = null;

function initCharts() {
    if (typeof Chart === 'undefined') return;

    const commonOptions = {
        responsive: true,
        animation: { duration: 300 },
        scales: {
            x: {
                display: true, title: { display: true, text: 'Time', color: '#94a3b8' },
                ticks: { color: '#64748b', maxTicksLimit: 10 }, grid: { color: 'rgba(148,163,184,0.1)' }
            },
            y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(148,163,184,0.1)' } }
        },
        plugins: { legend: { labels: { color: '#e2e8f0', usePointStyle: true } } }
    };

    const ctx1 = document.getElementById('chart-speed-battery');
    if (ctx1) {
        speedBatteryChart = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'Speed (km/h)', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.3, pointRadius: 0 },
                    { label: 'Battery SoC (%)', data: [], borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', fill: true, tension: 0.3, pointRadius: 0 },
                ]
            },
            options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, min: 0, max: 150 } } }
        });
    }

    const ctx2 = document.getElementById('chart-tires');
    if (ctx2) {
        tireChart = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'FL', data: [], borderColor: '#3b82f6', tension: 0.3, pointRadius: 0 },
                    { label: 'FR', data: [], borderColor: '#8b5cf6', tension: 0.3, pointRadius: 0 },
                    { label: 'RL', data: [], borderColor: '#f59e0b', tension: 0.3, pointRadius: 0 },
                    { label: 'RR', data: [], borderColor: '#ef4444', tension: 0.3, pointRadius: 0 },
                ]
            },
            options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, min: 15, max: 40, title: { display: true, text: 'PSI', color: '#94a3b8' } } } }
        });
    }
}

async function fetchHistory() {
    try {
        const res = await fetch(`${API_BASE}/vehicle/history?limit=60`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data.history || data.history.length === 0) return;

        const labels = data.history.map((_, i) => `${i}s`);

        if (speedBatteryChart) {
            speedBatteryChart.data.labels = labels;
            speedBatteryChart.data.datasets[0].data = data.history.map(h => h.speed);
            speedBatteryChart.data.datasets[1].data = data.history.map(h => h.battery_soc);
            speedBatteryChart.update('none');
        }

        if (tireChart) {
            tireChart.data.labels = labels;
            tireChart.data.datasets[0].data = data.history.map(h => h.tire_fl);
            tireChart.data.datasets[1].data = data.history.map(h => h.tire_fr);
            tireChart.data.datasets[2].data = data.history.map(h => h.tire_rl);
            tireChart.data.datasets[3].data = data.history.map(h => h.tire_rr);
            tireChart.update('none');
        }
    } catch (err) { console.error('History fetch error:', err); }
}

// Initialize charts after Chart.js loads
window.addEventListener('load', () => {
    setTimeout(initCharts, 100);
});
setInterval(fetchHistory, 2000);

// ═══════════════════════════════════════════════════════════════════════════
// ML Training Controls
// ═══════════════════════════════════════════════════════════════════════════
document.getElementById('btn-train-ml').addEventListener('click', async () => {
    const samples = document.getElementById('ml-samples').value;
    const statusEl = document.getElementById('ml-status');
    const btn = document.getElementById('btn-train-ml');

    btn.disabled = true;
    btn.textContent = '⏳ Training...';
    statusEl.innerHTML = '<div class="status-dot training"></div><span>Training in progress...</span>';

    try {
        const res = await fetch(`${API_BASE}/ml/train?num_sequences=${samples}`, { method: 'POST' });
        const data = await res.json();
        statusEl.innerHTML = `<div class="status-dot success"></div><span>${data.message || 'Training started'}</span>`;

        // Poll for completion — check status field (not models_ready)
        let pollCount = 0;
        const pollStatus = setInterval(async () => {
            pollCount++;
            try {
                const sRes = await fetch(`${API_BASE}/ml/status`);
                const sData = await sRes.json();

                // Update progress
                if (sData.progress) {
                    statusEl.innerHTML = `<div class="status-dot training"></div><span>Training... ${sData.progress}% (${sData.current_model || ''})</span>`;
                }

                if (sData.status === 'completed') {
                    clearInterval(pollStatus);
                    statusEl.innerHTML = '<div class="status-dot success"></div><span>✅ Models trained and ready!</span>';
                    btn.disabled = false;
                    btn.textContent = '🚀 Retrain Models';
                    fetchMLPredictions();
                } else if (sData.status === 'failed') {
                    clearInterval(pollStatus);
                    statusEl.innerHTML = `<div class="status-dot error"></div><span>❌ Training failed: ${sData.error || 'Unknown error'}</span>`;
                    btn.disabled = false;
                    btn.textContent = '🚀 Train Models';
                }
            } catch (e) { /* continue polling */ }

            // Safety timeout: stop polling after 60s
            if (pollCount > 30) {
                clearInterval(pollStatus);
                statusEl.innerHTML = '<div class="status-dot error"></div><span>⚠️ Training timed out — try again</span>';
                btn.disabled = false;
                btn.textContent = '🚀 Train Models';
            }
        }, 2000);
    } catch (err) {
        statusEl.innerHTML = `<div class="status-dot error"></div><span>Error: ${err.message}</span>`;
        btn.disabled = false;
        btn.textContent = '🚀 Train Models';
    }
});

document.getElementById('btn-ml-predict').addEventListener('click', fetchMLPredictions);

async function fetchMLPredictions() {
    const container = document.getElementById('ml-predictions');
    try {
        const res = await fetch(`${API_BASE}/ml/predict`);
        const data = await res.json();

        if (data.error) {
            container.innerHTML = `<p class="placeholder-text">${data.error}</p>`;
            return;
        }

        let html = '';
        if (data.battery_depletion) {
            const b = data.battery_depletion;
            html += `<div class="alert-item"><div class="alert-type">🔋 Battery Depletion</div>
                     <div class="alert-msg">Predicted: ${b.predicted_minutes_remaining?.toFixed(1) || 'N/A'} min remaining</div></div>`;
        }
        if (data.tire_wear) {
            const t = data.tire_wear;
            html += `<div class="alert-item"><div class="alert-type">🛞 Tire Wear</div>
                     <div class="alert-msg">Wear score: ${t.wear_score?.toFixed(2) || 'N/A'}</div></div>`;
        }
        if (data.anomaly_detection) {
            const a = data.anomaly_detection;
            html += `<div class="alert-item ${a.is_anomaly ? 'critical' : ''}"><div class="alert-type">⚠️ Anomaly Detection</div>
                     <div class="alert-msg">${a.is_anomaly ? '🔴 Anomaly detected!' : '🟢 Normal behavior'} (score: ${a.anomaly_score?.toFixed(3) || 'N/A'})</div></div>`;
        }
        container.innerHTML = html || '<p class="placeholder-text">No predictions available. Ensure simulation is running.</p>';
    } catch (err) {
        container.innerHTML = `<p class="placeholder-text">Error fetching predictions: ${err.message}</p>`;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// OTA Update Controls
// ═══════════════════════════════════════════════════════════════════════════
document.getElementById('btn-ota-deploy').addEventListener('click', async () => {
    const updateType = document.getElementById('ota-type').value;
    const description = document.getElementById('ota-desc').value;
    const payloadStr = document.getElementById('ota-payload').value;
    const statusEl = document.getElementById('ota-status');

    let payload;
    try {
        payload = payloadStr ? JSON.parse(payloadStr) : {};
    } catch (e) {
        statusEl.innerHTML = '<div class="alert-item critical"><div class="alert-msg">Invalid JSON payload</div></div>';
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/ota/deploy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ update_type: updateType, payload, description }),
        });
        const data = await res.json();
        const deployTime = data.update?.deployed_at ? new Date(data.update.deployed_at).toLocaleString() : new Date().toLocaleString();
        statusEl.innerHTML = `<div class="alert-item"><div class="alert-type">✅ Deployed v${data.version}</div>
                              <div class="alert-msg">${data.update?.applied || 'Success'}</div>
                              <div class="alert-time" style="color:#22c55e;font-weight:700;font-size:0.95em;">🕐 Deployed at: ${deployTime}</div></div>`;
        fetchOTAHistory();
    } catch (err) {
        statusEl.innerHTML = `<div class="alert-item critical"><div class="alert-msg">Deploy failed: ${err.message}</div></div>`;
    }
});

async function fetchOTAHistory() {
    try {
        const res = await fetch(`${API_BASE}/ota/history`);
        const data = await res.json();
        document.getElementById('ota-version').textContent = `Current Version: v${data.current_version}`;

        const container = document.getElementById('ota-history');
        if (data.history && data.history.length > 0) {
            container.innerHTML = data.history.map(h => {
                const ts = new Date(h.deployed_at).toLocaleString();
                const payloadPreview = h.payload ? JSON.stringify(h.payload).substring(0, 80) : '';
                return `
                <div class="alert-item" style="border-left: 3px solid #3b82f6; margin-bottom: 8px;">
                    <div class="alert-type" style="font-size:1em;">📦 v${h.version} — ${h.update_type}</div>
                    <div class="alert-msg">${h.description}</div>
                    <div class="alert-msg" style="color:#94a3b8;font-size:0.8em;font-family:monospace;">${payloadPreview}${payloadPreview.length >= 80 ? '…' : ''}</div>
                    <div class="alert-time" style="color:#22c55e;font-weight:700;">🕐 ${ts}</div>
                </div>`;
            }).join('');
        }
    } catch (err) { console.error('OTA history error:', err); }
}
