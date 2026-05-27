const API_BASE = '';

const state = {
  online: false,
  modelVersion: '',
  modelUsed: '',
  lastResult: null,
};

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function toast(msg, type = 'info') {
  const el = $('#toast');
  el.textContent = msg;
  el.className = `toast ${type} visible`;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('visible'), 4000);
}

function showLoading(btn) {
  btn.disabled = true;
  btn._orig = btn.innerHTML;
  btn.innerHTML = '<span class="spinner"></span> Predicting...';
}

function hideLoading(btn) {
  btn.disabled = false;
  if (btn._orig) btn.innerHTML = btn._orig;
}

function setRiskColors(prob) {
  if (prob < 0.25) return { tier: 'Low', color: 'var(--green)', cls: 'low' };
  if (prob < 0.5) return { tier: 'Moderate', color: 'var(--amber)', cls: 'moderate' };
  if (prob < 0.75) return { tier: 'High', color: 'var(--orange)', cls: 'high' };
  return { tier: 'Critical', color: 'var(--red)', cls: 'critical' };
}

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      state.online = true;
      $('#status-dot').className = 'status-dot online';
      $('#status-text').textContent = 'Online';
    }
  } catch { /* ignore */ }
}

async function loadMetadata() {
  try {
    const res = await fetch(`${API_BASE}/metadata`);
    if (res.ok) {
      const meta = await res.json();
      state.modelVersion = meta.model_version;
      state.modelUsed = meta.model_used;
      $('#header-version').textContent = `v${meta.model_version}`;
      $('#footer-version').textContent = `Model: ${meta.model_used} v${meta.model_version}`;
    }
  } catch { /* ignore */ }
}

function collectFormData() {
  const data = {};
  $$('input:not([type="hidden"]), select').forEach(el => {
    const val = el.value.trim();
    if (val !== '') {
      data[el.name] = el.type === 'number' ? parseFloat(val) : val;
    }
  });
  return data;
}

function renderResults(result) {
  state.lastResult = result;
  const panel = $('#results-panel');
  panel.classList.add('visible');

  const prob = result.risk_probability;
  const rc = setRiskColors(prob);
  const circumference = 2 * Math.PI * 82;
  const offset = circumference * (1 - prob);

  // Gauge
  const gaugeFill = $('#gauge-fill');
  gaugeFill.style.stroke = rc.color;
  gaugeFill.style.strokeDasharray = `${circumference}`;
  gaugeFill.style.strokeDashoffset = `${circumference}`;
  requestAnimationFrame(() => {
    gaugeFill.style.strokeDashoffset = `${offset}`;
  });

  $('#gauge-value').textContent = `${(prob * 100).toFixed(1)}%`;
  $('#gauge-value').style.color = rc.color;

  // Tier badge
  const badge = $('#risk-tier-badge');
  badge.className = `risk-tier-badge ${rc.cls}`;
  badge.innerHTML = `<span>${rc.tier}</span>`;

  // Confidence
  $('#confidence-value').textContent = result.confidence || '—';

  // Model version
  $('#result-model').textContent = `${result.model_used} v${result.model_version}`;

  // Recommendations
  const recsList = $('#recommendations-list');
  if (result.recommendations && result.recommendations.length) {
    recsList.innerHTML = result.recommendations.map(r => `<li>${r}</li>`).join('');
  } else {
    recsList.innerHTML = '<li style="color:var(--gray-400);border-left-color:var(--gray-300)">No specific recommendations at this time.</li>';
  }

  // Scroll to results
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function handlePredict(e) {
  e.preventDefault();
  const btn = $('#predict-btn');
  showLoading(btn);

  const patientData = collectFormData();

  try {
    const res = await fetch(`${API_BASE}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_data: patientData }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `API error: ${res.status}`);
    }

    const result = await res.json();
    renderResults(result);
    toast('Prediction complete', 'success');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading(btn);
  }
}

async function handleFeedback(e) {
  e.preventDefault();
  if (!state.lastResult) return;

  const btn = $('#feedback-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Submitting...';

  const actualLabel = $('#actual-label').value;
  if (!actualLabel) {
    toast('Please select the actual outcome', 'error');
    btn.disabled = false;
    btn.innerHTML = 'Submit Feedback';
    return;
  }

  const patientData = collectFormData();
  const predictedLabel = state.lastResult.risk_probability >= 0.5 ? 'ckd' : 'notckd';

  try {
    const res = await fetch(`${API_BASE}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_data: patientData,
        actual_label: actualLabel,
        predicted_label: predictedLabel,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `API error: ${res.status}`);
    }

    const result = await res.json();
    const matchIcon = result.prediction_match ? '✓' : '✗';
    const matchColor = result.prediction_match ? 'var(--green)' : 'var(--red)';
    toast(`Feedback accepted. Prediction match: ${result.prediction_match}`, result.prediction_match ? 'success' : 'info');

    // Update UI with feedback result
    $('#feedback-result').innerHTML = `
      <div style="margin-top:.75rem;padding:.75rem;background:var(--gray-50);border-radius:var(--radius);font-size:.8rem">
        <div style="display:flex;justify-content:space-between;margin-bottom:.25rem">
          <span style="color:var(--gray-500)">Status</span>
          <span style="font-weight:600;color:var(--green)">${result.status}</span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:.25rem">
          <span style="color:var(--gray-500)">Prediction match</span>
          <span style="font-weight:700;color:${matchColor}">${matchIcon}</span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:.25rem">
          <span style="color:var(--gray-500)">Your prediction</span>
          <span style="font-weight:600">${result.predicted_label}</span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:.25rem">
          <span style="color:var(--gray-500)">Actual outcome</span>
          <span style="font-weight:600">${result.actual_label}</span>
        </div>
        <div style="display:flex;justify-content:space-between">
          <span style="color:var(--gray-500)">Feedback records</span>
          <span style="font-weight:600">${result.feedback_records}</span>
        </div>
        ${result.model_retrained ? '<div style="margin-top:.5rem;padding:.25rem .5rem;background:var(--amber-light);border-radius:var(--radius);color:var(--amber);font-weight:600;text-align:center">Model retrained to new version!</div>' : ''}
      </div>
    `;
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Submit Feedback';
  }
}

function resetForm() {
  $$('input').forEach(el => el.value = '');
  $$('select').forEach(el => el.selectedIndex = 0);
  const panel = $('#results-panel');
  panel.classList.remove('visible');
  $('#feedback-result').innerHTML = '';
  state.lastResult = null;
  window.scrollTo({ top: 0, behavior: 'smooth' });
  toast('Form cleared', 'info');
}

function loadSampleData() {
  const sample = {
    age: 65, bp: 140, sg: 1.01, al: 3, su: 2,
    bgr: 180, bu: 58, sc: 3.5, sod: 132, pot: 5.2,
    hemo: 8.5, pcv: 26, wc: 11000, rc: 3.1,
    rbc: 'abnormal', pc: 'abnormal', pcc: 'present', ba: 'notpresent',
    htn: 'yes', dm: 'yes', cad: 'yes', appet: 'poor', pe: 'yes', ane: 'yes',
  };
  Object.entries(sample).forEach(([key, val]) => {
    const el = $(`[name="${key}"]`);
    if (el) el.value = val;
  });
  toast('Sample patient data loaded', 'info');
}

async function init() {
  await Promise.all([checkHealth(), loadMetadata()]);
  $('#predict-form').addEventListener('submit', handlePredict);
  $('#feedback-form').addEventListener('submit', handleFeedback);
  $('#reset-btn').addEventListener('click', resetForm);
  $('#load-sample-btn').addEventListener('click', loadSampleData);
}

document.addEventListener('DOMContentLoaded', init);
