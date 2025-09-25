$(document).ready(function() {
    // Activate Bootstrap tabs
    $('#myTab a').on('click', function (e) {
        e.preventDefault();
        $(this).tab('show');
    });

    // Example: Load content when a tab is shown
    $('#myTab a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        var targetTabId = $(e.target).attr('href'); // newly activated tab
        console.log('Tab ' + targetTabId + ' is now active.');
        // Here you would typically load data or update content for the active tab
        loadTabContent(targetTabId);
    });

    // Function to load content for a given tab
    function loadTabContent(tabId) {
        // This is a placeholder. In a real application, you would fetch data
        // from your API and update the content of the tab.
        console.log('Loading content for ' + tabId + '...');
        // Example: if (tabId === '#feed') { fetchFeedData(); }
        // Example: if (tabId === '#alerts') { fetchAlertsData(); }
    }

    // Initial load for the default active tab
    var activeTab = $('#myTab a.active').attr('href');
    if (activeTab) {
        loadTabContent(activeTab);
    }
});

(async function(){
  const api = (p)=>fetch(p).then(r=>r.json());

  function evidenceToggleHTML(related_links, tech_links){
    const all_links = [...(related_links || []), ...(tech_links || [])];
    if(!all_links.length) return '';
    const list = all_links.map(u=>`<li><a href="${u}" target="_blank">${u}</a></li>`).join('');
    return `
      <details style="margin-top:6px;">
        <summary style="cursor:pointer;color:#888;">증거 보기</summary>
        <ul style="margin:6px 0 0 16px;">${list}</ul>
      </details>`;
  }

  async function loadFeed(company_name) {
    const data = await api(`/me/feed?company_name=${encodeURIComponent(company_name)}&min_importance=55&limit=20`);
    const el = document.getElementById('feed');
    el.innerHTML = (data.items||[]).map(it=>{
      const pub = new Date(it.published_at).toLocaleString('ko-KR');
      const severityBadge = it.severity ? `<span style="padding:2px 6px;border-radius:6px;border:1px solid ${it.severity === 'HIGH' ? '#ff6b6b' : it.severity === 'MEDIUM' ? '#feca57' : '#4ecdc4'};color:${it.severity === 'HIGH' ? '#ff6b6b' : it.severity === 'MEDIUM' ? '#feca57' : '#4ecdc4'};font-size:11px;margin-left:6px;">${it.severity}</span>` : '';
      const importanceBar = it.importance_pct != null ? `
        <div style="width:100%;background:#333;border-radius:4px;height:6px;margin-top:4px;">
          <div style="width:${it.importance_pct}%;background:#3b82f6;height:100%;border-radius:4px;"></div>
        </div>
        <span style="font-size:11px;color:#aaa;">중요도: ${it.importance_pct}%</span>
      ` : '';
      const impactLevelBadge = it.impact_level ? `<span style="padding:2px 6px;border-radius:6px;border:1px solid #ddd;font-size:11px;margin-left:6px;">${it.impact_level}</span>` : '';
      const topicTags = (it.topic_tags && it.topic_tags.length > 0) ? `<div style="font-size:11px;color:#aaa;margin-top:4px;">주제: ${it.topic_tags.join(', ')}</div>` : '';
      const keywordSummary = (it.keyword_summary && it.keyword_summary.length > 0) ? `<div style="font-size:12px;color:#ccc;margin-top:6px;">키워드: ${it.keyword_summary.join(', ')}</div>` : '';
      const relatedEvent = it.related_event ? `<div style="font-size:12px;color:#ccc;margin-top:6px;">사건: ${it.related_event}</div>` : '';
      const analysisNotes = it.analysis_notes ? `<div style="font-size:12px;color:#ccc;margin-top:6px;">분석: ${it.analysis_notes}</div>` : '';
      const watchPoints = (it.watch_points && it.watch_points.length > 0) ? `<div style="font-size:12px;color:#ccc;margin-top:6px;">관전 포인트: ${it.watch_points.join(', ')}</div>` : '';

      return `<div style="border:1px solid #333;border-radius:10px;padding:12px;margin-bottom:10px;">
        <div style="font-weight:600">${it.title}${severityBadge}${impactLevelBadge}</div>
        ${importanceBar}
        <div style="font-size:12px;color:#999">${it.source_domain} · ${pub}</div>
        <div style="font-size:12px;color:#ccc">카테고리: ${it.category}</div>
        ${topicTags}
        <div style="font-size:14px;margin-top:8px;">${it.ko_short || it.summary || ''}</div>
        ${keywordSummary}
        ${relatedEvent}
        ${analysisNotes}
        ${watchPoints}
        <a href="${it.canonical_url}" target="_blank" style="font-size:12px;margin-top:8px;display:inline-block;">원문보기</a>
        ${evidenceToggleHTML(it.related_links, it.tech_links)}
      </div>`;
    }).join('') || '<div>데이터 없음</div>';
  }

  const today = new Date();
  const yday = new Date(today.getTime() - 86400000);
  const ydayStr = yday.toISOString().slice(0,10);

  async function loadRecap(){
    const res = await api(`/me/recap?ticker=NVDA&date=${ydayStr}`);
    const el = document.getElementById('recap');
    const list = (res.top_events||[]).map(e=>`<li>${e.title} <small>(${e.importance})</small></li>`).join('');
    el.innerHTML = `<div style="border:1px solid #333;border-radius:10px;padding:12px;">
      <div><strong>${res.date}</strong> 주요 사건</div>
      <ul>${list || '<li>없음</li>'}</ul>
      <div style="margin-top:6px;color:#ccc;">${res.yday_explain}</div>
      <div style="margin-top:6px;font-size:12px;">관전 포인트: ${(res.watch_points||[]).join(', ')}</div>
    </div>`;
  }

  async function loadIExplain(){
    const t = today.toISOString().slice(0,10);
    const res = await api(`/me/intraday_explain?ticker=NVDA&date=${t}&sector_ticker=SOXX&index_ticker=NDX`);
    const el = document.getElementById('iexplain');
    el.innerHTML = `<div style="border:1px solid #333;border-radius:10px;padding:12px;">
      <div>당일 등락: <strong>${res.move_pct}%</strong> / 투자자 심리: <strong>${res.sentiment_label}</strong></div>
      <div>기여도 - 회사 ${res.contrib.company}%, 섹터 ${res.contrib.sector}%, 거시 ${res.contrib.macro}%, 흐름 ${res.contrib.flow}%</div>
      <div>VWAP: ${res.vwap ?? 'N/A'} / 섹터 상관: ${res.sector_corr} / 지수 상관: ${res.index_corr}</div>
      <div style="margin-top:6px;">1일: ${res.one_day_view}</div>
      <div>단기: ${res.short_term_view}</div>
      <div>중장기: ${res.mid_long_view}</div>
    </div>`;
  }

  function startSSE(){
    const es = new EventSource('/me/alerts/stream');
    const banner = document.getElementById('alert-banner');
    const text = document.getElementById('alert-text');
    es.addEventListener('alert', (ev)=>{
      try{
        const d = JSON.parse(ev.data);
        banner.style.display='block';
        text.textContent = `[${d.severity}] ${d.title} (중요도 ${d.importance_pct}%, 정확도 ${d.accuracy_pct}%)`;
        setTimeout(()=>{ banner.style.display='none'; }, 15000);
        loadFeed();
      }catch(e){}
    });
  }

  async function loadRisk(ticker='NVDA'){
    const r = await api(`/market/risk?ticker=${ticker}`);
    const el = document.getElementById('risk-body');
    const gx = r.gamma_exposure!=null ? `${r.gamma_exposure.toLocaleString()} (USD)` : 'N/A';
    const mp = r.max_pain!=null ? r.max_pain : 'N/A';
    const pcr = r.put_call_ratio!=null ? r.put_call_ratio : 'N/A';
    const sf = r.short_float_pct!=null ? `${r.short_float_pct}%` : 'N/A';
    const dtc = r.days_to_cover!=null ? r.days_to_cover : 'N/A';
    el.innerHTML = `
      감마 노출: <b>${gx}</b><br/>
      맥스 페인: <b>${mp}</b> / Put-Call Ratio: <b>${pcr}</b><br/>
      공매도 비중: <b>${sf}</b> / Days-to-Cover: <b>${dtc}</b><br/>
      <span style="color:#777;font-size:12px;">source: ${r.source || 'N/A'}</span>
    `;
  }

  let ctxRadar;
  async function loadCompanyContext(name='NVIDIA'){
    const r = await api(`/company/context?company=${encodeURIComponent(name)}`);
    const scores = r.scores || {};
    const data = [
      scores.customers ?? 60,
      scores.supply ?? 60,
      scores.policy_inverse ?? 70,
      scores.competition_inverse ?? 65
    ];
    const labels = ['고객', '공급', '정책(낮을수록↑)', '경쟁(낮을수록↑)'];
    const ctx = document.getElementById('ctx-radar').getContext('2d');
    if (ctxRadar) ctxRadar.destroy();
    ctxRadar = new Chart(ctx, {
      type: 'radar',
      data: {
        labels,
        datasets: [{
          label: (r.company || name),
          data,
          fill: true,
          backgroundColor: 'rgba(59, 130, 246, 0.2)',
          borderColor: 'rgba(59, 130, 246, 1)',
          pointBackgroundColor: 'rgba(59, 130, 246, 1)',
        }]
      },
      options: {
        responsive: true,
        scales: { r: { beginAtZero: true, max: 100, ticks: { backdropColor: '#222' }, pointLabels: { color: '#fff' } } },
        plugins: { legend: { display: false } }
      }
    });
    const L = r.lists || {};
    document.getElementById('ctx-lists').innerHTML =
      `<div>고객: ${(L.customers||[]).join(', ') || '-'}</div>
       <div>공급: ${(L.suppliers||[]).join(', ') || '-'}</div>
       <div>정책: ${(L.policies||[]).join(', ') || '-'}</div>
       <div>경쟁: ${(L.competitors||[]).join(', ') || '-'}</div>`;
  }

  const modal = document.getElementById('modal-settings');
  const backdrop = document.getElementById('modal-backdrop');

  async function openSettings(){
    const s = await api('/me/settings/alerts');
    document.getElementById('qh-start').value = (s.quiet_hours?.start) || '23:00';
    document.getElementById('qh-end').value   = (s.quiet_hours?.end)   || '07:00';
    document.getElementById('min-imp').value  = s.min_importance ?? 70;
    document.getElementById('sev-min').value  = (s.severity_min || 'LOW');
    const cats = s.categories || [];
    document.querySelectorAll('.cat').forEach(ch=>{
      ch.checked = cats.includes(ch.value);
    });
    document.getElementById('gex-en').checked = !!s.gex?.enabled;
    document.getElementById('gex-band').value = (s.gex?.zero_band_pct ?? 1.0);
    document.getElementById('mp-en').checked = !!s.maxpain?.enabled;
    document.getElementById('mp-gap').value = (s.maxpain?.gap_pct ?? 3.0);
    modal.style.display='block'; backdrop.style.display='block';
  }
  function closeSettings(){
    modal.style.display='none'; backdrop.style.display='none';
  }

  async function saveSettings(){
    const payload = {
      quiet_hours: { start: document.getElementById('qh-start').value,
                     end:   document.getElementById('qh-end').value },
      min_importance: parseInt(document.getElementById('min-imp').value,10),
      categories: Array.from(document.querySelectorAll('.cat:checked')).map(x=>x.value),
      severity_min: document.getElementById('sev-min').value,
      gex: { enabled: document.getElementById('gex-en').checked,
             zero_band_pct: parseFloat(document.getElementById('gex-band').value) },
      maxpain: { enabled: document.getElementById('mp-en').checked,
                 gap_pct: parseFloat(document.getElementById('mp-gap').value) }
    };
    await fetch('/me/settings/alerts', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    closeSettings();
  }

  document.getElementById('btn-alert-settings').addEventListener('click', openSettings);
  document.getElementById('btn-cancel').addEventListener('click', closeSettings);
  document.getElementById('btn-save').addEventListener('click', saveSettings);

  let gexChart;
  async function loadGexSnake(ticker='NVDA'){
    const js = await api(`/market/gex_curve?ticker=${ticker}`);
    const curve = js.curve || [];
    const labels = curve.map(d=>d.strike);
    const data = curve.map(d=>d.gex);
    const ctx = document.getElementById('gex-snake').getContext('2d');
    if (gexChart) gexChart.destroy();
    gexChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [{ label: 'GEX', data, tension: 0.2, borderColor: '#60a5fa', backgroundColor: 'rgba(96, 165, 250, 0.1)', fill: true }] },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: { title: { display: true, text: 'Strike', color: '#aaa' }, ticks: { color: '#aaa' } },
          y: { title: { display: true, text: 'GEX (sum of C - P)', color: '#aaa' }, ticks: { color: '#aaa' } }
        }
      }
    });
    document.getElementById('gex-meta').innerHTML =
      `현물(Spot): <b>${js.spot ?? 'N/A'}</b>, 맥스페인: <b>${js.max_pain ?? 'N/A'}</b> · 업데이트: ${js.updated_at ? new Date(js.updated_at).toLocaleString() : '-'}`;
  }

  // New functions for Market Analysis tab
  async function loadMarketRisk(ticker){
    const r = await api(`/market/risk?ticker=${encodeURIComponent(ticker)}`);
    const el = document.getElementById('market-risk-body');
    const gx = r.gamma_exposure!=null ? `${r.gamma_exposure.toLocaleString()} (USD)` : 'N/A';
    const mp = r.max_pain!=null ? r.max_pain : 'N/A';
    const pcr = r.put_call_ratio!=null ? r.put_call_ratio : 'N/A';
    const sf = r.short_float_pct!=null ? `${r.short_float_pct}%` : 'N/A';
    const dtc = r.days_to_cover!=null ? r.days_to_cover : 'N/A';
    el.innerHTML = `
      감마 노출: <b>${gx}</b><br/>
      맥스 페인: <b>${mp}</b> / Put-Call Ratio: <b>${pcr}</b><br/>
      공매도 비중: <b>${sf}</b> / Days-to-Cover: <b>${dtc}</b><br/>
      <span style="color:#777;font-size:12px;">source: ${r.source || 'N/A'}</span>
    `;
  }

  let marketGexChart;
  async function loadMarketGexSnake(ticker){
    const js = await api(`/market/gex_curve?ticker=${encodeURIComponent(ticker)}`);
    const curve = js.curve || [];
    const labels = curve.map(d=>d.strike);
    const data = curve.map(d=>d.gex);
    const ctx = document.getElementById('market-gex-snake').getContext('2d');
    if (marketGexChart) marketGexChart.destroy();
    marketGexChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [{ label: 'GEX', data, tension: 0.2, borderColor: '#60a5fa', backgroundColor: 'rgba(96, 165, 250, 0.1)', fill: true }] },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: { title: { display: true, text: 'Strike', color: '#aaa' }, ticks: { color: '#aaa' } },
          y: { title: { display: true, text: 'GEX (sum of C - P)', color: '#aaa' }, ticks: { color: '#aaa' } }
        }
      }
    });
    document.getElementById('market-gex-meta').innerHTML =
      `현물(Spot): <b>${js.spot ?? 'N/A'}</b>, 맥스페인: <b>${js.max_pain ?? 'N/A'}</b> · 업데이트: ${js.updated_at ? new Date(js.updated_at).toLocaleString() : '-'}`;
  }

  // Function to load all data for the selected company
  async function loadCompanyData(company_name) {
    const ticker = company_name; // Assuming company_name can also be used as ticker for now
    await loadFeed(company_name);
    await loadRecap(ticker);
    await loadIExplain(ticker);
    await loadRisk(ticker);
    await loadCompanyContext(company_name);
    await loadGexSnake(ticker);
  }

  // Tab switching logic
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');

  function showTab(tabId) {
    tabContents.forEach(content => {
      content.style.display = 'none';
    });
    document.getElementById(`tab-content-${tabId}`).style.display = 'block';

    tabButtons.forEach(button => {
      button.classList.remove('active');
    });
    document.querySelector(`.tab-button[data-tab="${tabId}"]`).classList.add('active');

    window.location.hash = tabId;

    // Load data for the active tab
    const currentCompany = document.getElementById('company-select').value;
    const ticker = currentCompany; // Assuming company_name can also be used as ticker for now

    switch (tabId) {
      case 'feed':
        loadFeed(currentCompany);
        break;
      case 'analysis':
        loadRisk(ticker);
        loadCompanyContext(currentCompany);
        loadGexSnake(ticker);
        break;
      case 'pre_market':
        loadIExplain(ticker);
        break;
      case 'post_market':
        loadRecap(ticker);
        break;
      case 'alerts':
        // Alerts are handled by SSE, no specific load function here
        // If there's a list of past alerts, a load function would go here.
        break;
      case 'market_analysis':
        loadMarketRisk(ticker);
        loadMarketGexSnake(ticker);
        break;
    }
  }

  // Function to handle hash changes
  function handleHashChange() {
    const hash = window.location.hash.substring(1); // Remove '#'
    if (hash && document.getElementById(`tab-content-${hash}`)) {
      showTab(hash);
    } else {
      showTab('feed'); // Default to 'feed' tab if hash is invalid or not present
    }
  }

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      showTab(button.dataset.tab);
    });
  });

  // Initial load
  const initialCompany = document.getElementById('company-select').value;
  loadCompanyData(initialCompany);
  startSSE();

  // Call handleHashChange on initial load and when hash changes
  handleHashChange();
  window.addEventListener('hashchange', handleHashChange);

})();