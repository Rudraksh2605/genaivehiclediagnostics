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
        document.getElementById('page-title').textContent =
            tab === 'dashboard' ? 'Dashboard' :
                tab === 'codegen' ? 'Code Generator' :
                    tab === 'analytics' ? 'Predictive Analytics' : 'Alerts';
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
        const res = await fetch(`${API_BASE}/vehicle/simulate/start`, { method: 'POST' });
        if (res.ok) {
            document.getElementById('btn-start-sim').style.display = 'none';
            document.getElementById('btn-stop-sim').style.display = 'block';
            const pill = document.getElementById('sim-status');
            pill.textContent = '● Running';
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

// ── Data Polling ────────────────────────────────────────────────────────────
function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(fetchTelemetry, 1000);
    fetchTelemetry();
}

function stopPolling() {
    if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
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

// ── Alerts Update ───────────────────────────────────────────────────────────
function updateAlerts(alerts) {
    const container = document.getElementById('alerts-list');
    const badge = document.getElementById('alert-badge');
    badge.textContent = alerts.length;

    if (!alerts.length) {
        container.innerHTML = '<p class="placeholder-text">No alerts yet.</p>';
        return;
    }

    container.innerHTML = alerts.slice().reverse().map(a => `
        <div class="alert-item ${a.severity === 'critical' ? 'critical' : ''}">
            <div class="alert-type">${a.severity.toUpperCase()} — ${a.alert_type.replace(/_/g, ' ')}</div>
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

        // Update Predictions list
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

        // Update Driving Score
        if (data.driving_score) {
            const ds = data.driving_score;
            document.getElementById('overall-score').textContent = Math.round(ds.overall);
            document.getElementById('score-speed').textContent = Math.round(ds.speed);
            document.getElementById('score-braking').textContent = Math.round(ds.braking);
            document.getElementById('score-efficiency').textContent = Math.round(ds.efficiency);

            // Color the score circle based on value
            const circle = document.querySelector('.score-circle');
            if (circle) {
                const score = ds.overall;
                circle.style.borderColor = score >= 80 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';
            }
        }
    } catch (err) { console.error('Predictive fetch error:', err); }
}

setInterval(fetchPredictiveAnalysis, 3000);
