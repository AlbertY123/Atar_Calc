/* global TomSelect, Chart, STUDIES, DEFAULT_ROWS */

const $ = (sel) => document.querySelector(sel);

const el = (tag, attrs = {}, children = []) => {
  const e = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === 'class') e.className = v;
    else if (k === 'html') e.innerHTML = v;
    else e.setAttribute(k, v);
  });
  children.forEach((c) => e.appendChild(c));
  return e;
};

function clamp(n, lo, hi) {
  const x = Number(n);
  if (!Number.isFinite(x)) return lo;
  return Math.max(lo, Math.min(hi, x));
}

function showAlert(kind, msg) {
  const area = $('#alertArea');
  area.innerHTML = '';
  if (!msg) return;
  const icon = kind === 'danger' ? 'exclamation-triangle' : (kind === 'warning' ? 'exclamation-circle' : 'info-circle');
  area.appendChild(el('div', {
    class: `alert alert-${kind} mb-3`,
    html: `<div class="d-flex gap-2 align-items-start"><i class="bi bi-${icon} fs-5"></i><div>${msg}</div></div>`
  }));
}

function makeSubjectSelect(code) {
  const select = el('select', { class: 'form-select subject-select', 'aria-label': 'Subject' });
  select.appendChild(el('option', { value: '', html: 'Select a subject…' }));

  for (const s of STUDIES) {
    const opt = el('option', {
      value: s.code,
      html: `${s.study}${s.isEnglish ? ' (English)' : ''}`
    });
    // Store metadata so TomSelect can read it later
    opt.dataset.isEnglish = String(!!s.isEnglish);

    if (s.code === code) opt.selected = true;
    select.appendChild(opt);
  }

  return select;
}

function initTomSelect(select) {
  if (!select || select.dataset.tsInit === '1') return;
  select.dataset.tsInit = '1';

  // TomSelect needs the <select> to be in the DOM when constructed.
  // Otherwise it hides the original select but can't mount the replacement control.
  // eslint-disable-next-line no-new
  new TomSelect(select, {
    create: false,
    allowEmptyOption: true,
    placeholder: 'Select a subject…',
    maxOptions: 200,
    closeAfterSelect: true,
    render: {
      option(data, escape) {
        const isEnglish = String(data.customProperties?.isEnglish || data.isEnglish || '') === 'true';
        const badge = isEnglish ? '<span class="badge rounded-pill text-bg-primary ms-2">English</span>' : '';
        return `<div class="d-flex justify-content-between align-items-center"><div>${escape(data.text)}</div>${badge}</div>`;
      },
      item(data, escape) {
        const isEnglish = String(data.customProperties?.isEnglish || data.isEnglish || '') === 'true';
        const badge = isEnglish ? '<span class="badge rounded-pill text-bg-primary ms-2">English</span>' : '';
        return `<div class="d-flex align-items-center">${escape(data.text)}${badge}</div>`;
      }
    },
    onInitialize() {
      // Inject customProperties from dataset for badges
      for (const opt of select.options) {
        if (!opt.value) continue;
        this.options[opt.value] = this.options[opt.value] || {};
        this.options[opt.value].customProperties = this.options[opt.value].customProperties || {};
        this.options[opt.value].customProperties.isEnglish = opt.dataset.isEnglish;
      }
    }
  });
}

function makeRow({ code = '', raw = 35 } = {}) {
  const card = el('div', { class: 'subject-row-card' });

  const row = el('div', { class: 'row g-2 align-items-end' });

  // Subject
  const colSubj = el('div', { class: 'col-12 col-md-7' });
  colSubj.appendChild(el('label', { class: 'form-label small text-secondary mb-1', html: 'Subject' }));
  const select = makeSubjectSelect(code);
  colSubj.appendChild(select);
  // Init TomSelect *after* we mount this row into the DOM.
  // We do it next-tick so the select has a parentNode.
  setTimeout(() => initTomSelect(select), 0);

  // Raw score
  const colRaw = el('div', { class: 'col-8 col-md-3' });
  colRaw.appendChild(el('label', { class: 'form-label small text-secondary mb-1', html: 'Raw score (0–50)' }));

  const group = el('div', { class: 'input-group input-group-score' });
  const btnMinus = el('button', { class: 'btn btn-outline-secondary btn-minus', type: 'button', html: '<i class="bi bi-dash"></i>' });
  const input = el('input', {
    class: 'form-control raw-input text-center',
    type: 'number',
    inputmode: 'numeric',
    min: '0',
    max: '50',
    step: '1',
    value: String(raw)
  });
  const btnPlus = el('button', { class: 'btn btn-outline-secondary btn-plus', type: 'button', html: '<i class="bi bi-plus"></i>' });
  group.appendChild(btnMinus);
  group.appendChild(input);
  group.appendChild(btnPlus);
  colRaw.appendChild(group);

  // Remove
  const colDel = el('div', { class: 'col-4 col-md-2 text-end' });
  colDel.appendChild(el('label', { class: 'form-label small text-secondary mb-1 d-block', html: '&nbsp;' }));
  const del = el('button', { class: 'btn btn-outline-danger w-100 btn-remove', type: 'button', html: '<i class="bi bi-trash3"></i> <span class="d-none d-md-inline">Remove</span>' });
  colDel.appendChild(del);

  row.appendChild(colSubj);
  row.appendChild(colRaw);
  row.appendChild(colDel);

  card.appendChild(row);

  const setVal = (v) => {
    const next = clamp(v, 0, 50);
    input.value = String(next);
  };

  btnMinus.addEventListener('click', () => setVal(Number(input.value || 0) - 1));
  btnPlus.addEventListener('click', () => setVal(Number(input.value || 0) + 1));
  input.addEventListener('input', () => setVal(input.value));

  del.addEventListener('click', () => card.remove());

  return card;
}

function getRows() {
  const cards = Array.from($('#rows').querySelectorAll('.subject-row-card'));
  const pairs = [];

  for (const card of cards) {
    const sel = card.querySelector('select');
    const raw = card.querySelector('input.raw-input');
    const code = (sel && sel.value) ? sel.value : '';
    const score = clamp(raw ? raw.value : NaN, 0, 50);

    if (!code) continue;
    pairs.push({ code, raw_score: score });
  }

  return pairs;
}

async function predict() {
  showAlert('info', 'Calculating…');
  $('#result').classList.add('d-none');

  const studies = getRows();

  if (studies.length < 4) {
    showAlert('warning', 'Add at least 4 subjects (an ATAR aggregate needs 4+ studies).');
    return;
  }

  // English requirement
  const englishCodes = new Set(STUDIES.filter(s => s.isEnglish).map(s => s.code));
  const hasEnglish = studies.some(s => englishCodes.has(s.code));
  if (!hasEnglish) {
    showAlert('danger', 'You must include at least one English-group subject (English / EAL / English Language / Literature).');
    return;
  }
  showAlert('', '');

  const res = await fetch('/api/predict', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ studies })
  });

  const data = await res.json();
  if (!res.ok) {
    showAlert('danger', data.error || 'Prediction failed');
    return;
  }

  const atar = Number(data.atar);
  const agg = Number(data.aggregate);

  const hero = `
    <div class="result-hero">
      <div class="row g-3 align-items-stretch">
        <div class="col-12 col-md-6">
          <div class="metric">
            <div class="label">Predicted ATAR</div>
            <div class="value">${atar.toFixed(2)}</div>
            <div class="hint">Rounded to 0.05 (as published)</div>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="metric">
            <div class="label">Scaled aggregate</div>
            <div class="value">${agg.toFixed(2)}</div>
            <div class="hint">Top 4 + 10% of 5th/6th</div>
          </div>
        </div>
      </div>

      <div class="row g-3 mt-1">
        <div class="col-12 col-md-5">
          <div class="chart-card">
            <div class="small text-secondary mb-2">ATAR gauge</div>
            <canvas id="chartAtar" height="180"></canvas>
          </div>
        </div>
        <div class="col-12 col-md-7">
          <div class="chart-card">
            <div class="small text-secondary mb-2">Scaled scores (approx)</div>
            <canvas id="chartScaled" height="180"></canvas>
          </div>
        </div>
      </div>
    </div>
  `;

  const rows = data.details.map(d => `
    <tr>
      <td>
        <div class="fw-semibold">${d.study}</div>
        <div class="small text-secondary">${d.code}</div>
      </td>
      <td class="text-end">${Number(d.raw).toFixed(1)}</td>
      <td class="text-end">${Number(d.scaled).toFixed(2)}</td>
      <td class="text-end">
        ${d.in_top4 ? '<span class="badge text-bg-primary">Top 4</span>' : (d.is_bonus ? '<span class="badge text-bg-info">10% bonus</span>' : '<span class="badge text-bg-secondary">Unused</span>')}
      </td>
    </tr>
  `).join('');

  const breakdown = `
    <div class="table-responsive">
      <table class="table table-sm align-middle mb-0">
        <thead>
          <tr class="small text-secondary">
            <th>Subject</th>
            <th class="text-end">Raw</th>
            <th class="text-end">Scaled~</th>
            <th class="text-end">Counts as</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;

  $('#result').innerHTML = `
    <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
      <div>
        <h2 class="h4 mb-1">Results</h2>
        <div class="text-secondary">Instant estimate from your inputs.</div>
      </div>
      <div class="small text-secondary">VTAC 2024</div>
    </div>
    <hr class="my-3" />
    ${hero}
    <div class="mt-3">${breakdown}</div>
  `;

  $('#result').classList.remove('d-none');

  // Charts
  try {
    const ctxAtar = document.getElementById('chartAtar');
    if (ctxAtar) {
      // eslint-disable-next-line no-new
      new Chart(ctxAtar, {
        type: 'doughnut',
        data: {
          labels: ['ATAR', ''],
          datasets: [{
            data: [atar, Math.max(0, 100 - atar)],
            backgroundColor: ['rgba(37,99,235,.85)', 'rgba(15,23,42,.10)'],
            borderWidth: 0,
            hoverOffset: 2,
            cutout: '72%'
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: { enabled: false }
          }
        },
        plugins: [{
          id: 'centerText',
          afterDraw(chart) {
            const { ctx } = chart;
            const meta = chart.getDatasetMeta(0);
            if (!meta || !meta.data || !meta.data[0]) return;
            const { x, y } = meta.data[0];
            ctx.save();
            ctx.fillStyle = '#0b1020';
            ctx.font = '700 24px system-ui, -apple-system, Segoe UI, Roboto, Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(atar.toFixed(2), x, y - 4);
            ctx.fillStyle = '#64748b';
            ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, Arial';
            ctx.fillText('ATAR', x, y + 16);
            ctx.restore();
          }
        }]
      });
    }

    const ctxScaled = document.getElementById('chartScaled');
    if (ctxScaled) {
      const labels = data.details.map(d => d.code);
      const vals = data.details.map(d => Number(d.scaled));
      // eslint-disable-next-line no-new
      new Chart(ctxScaled, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Scaled~',
            data: vals,
            backgroundColor: 'rgba(124,58,237,.55)',
            borderRadius: 10
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true, suggestedMax: 60 }
          }
        }
      });
    }
  } catch (e) {
    // Charts are cosmetic; ignore failures.
  }
}

function resetRows() {
  $('#rows').innerHTML = '';
  DEFAULT_ROWS.forEach(r => $('#rows').appendChild(makeRow(r)));
}

function exampleRows() {
  $('#rows').innerHTML = '';
  const ex = [
    { code: 'EN', raw: 35 },
    { code: 'NJ', raw: 40 },
    { code: 'BI', raw: 38 },
    { code: 'CH', raw: 33 },
    { code: 'BM', raw: 36 },
    { code: 'NF', raw: 32 },
  ];
  ex.forEach(r => $('#rows').appendChild(makeRow(r)));
}

// Init
resetRows();

$('#btnAdd').addEventListener('click', () => $('#rows').appendChild(makeRow({}))); 
$('#btnReset').addEventListener('click', () => { showAlert('', ''); $('#result').classList.add('d-none'); resetRows(); });
$('#btnExample').addEventListener('click', () => { showAlert('', ''); $('#result').classList.add('d-none'); exampleRows(); });
$('#btnPredict').addEventListener('click', (e) => { e.preventDefault(); predict(); });
