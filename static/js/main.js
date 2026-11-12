/* StockFlow — behavior for charts, responsive sidebar, and accessible controls */
document.addEventListener('DOMContentLoaded', () => {
  const iconRefresh = () => { if (window.lucide?.createIcons) window.lucide.createIcons(); };
  iconRefresh();
  // Lucide script is loaded deferred, but continue working without the CDN.
  window.addEventListener('load', iconRefresh);
  const html = document.documentElement;
  const themeSwitch = document.querySelector('#themeSwitch');
  try { if (localStorage.getItem('stockflow-theme') === 'dark') html.classList.add('dark'); } catch (_) {}
  themeSwitch?.addEventListener('click', () => {
    html.classList.toggle('dark');
    try { localStorage.setItem('stockflow-theme', html.classList.contains('dark') ? 'dark' : 'light'); } catch (_) {}
  });
  const sidebar = document.querySelector('#sidebar');
  const overlay = document.querySelector('#sidebarOverlay');
  const menuToggle = document.querySelector('#menuToggle');
  function closeSidebar() { sidebar?.classList.remove('open'); overlay?.classList.remove('show'); menuToggle?.setAttribute('aria-expanded', 'false'); }
  menuToggle?.addEventListener('click', () => { const open = sidebar?.classList.toggle('open'); overlay?.classList.toggle('show', !!open); menuToggle.setAttribute('aria-expanded', String(!!open)); });
  overlay?.addEventListener('click', closeSidebar);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeSidebar();
    if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || '')) {
      const input = document.querySelector('.top-search input');
      if (input) { e.preventDefault(); input.focus(); }
    }
  });
  document.querySelectorAll('[data-dismiss-alert]').forEach(btn => btn.addEventListener('click', () => btn.closest('.alert')?.remove()));
  document.querySelectorAll('[data-confirm]').forEach(form => form.addEventListener('submit', e => {
    if (!confirm(form.dataset.confirm || 'Lanjutkan?')) e.preventDefault();
  }));
  document.querySelector('[data-toggle-password]')?.addEventListener('click', () => {
    const field = document.querySelector('#password'); if (field) field.type = field.type === 'password' ? 'text' : 'password';
  });
  document.querySelector('#fillDemo')?.addEventListener('click', () => {
    const email = document.querySelector('#email'), password = document.querySelector('#password');
    if (email) email.value = 'demo@stockflow.local';
    if (password) password.value = 'Demo12345!';
  });

  const chartNode = document.querySelector('#chartData');
  if (!chartNode) return;
  let chartData;
  try { chartData = JSON.parse(chartNode.textContent); } catch (_) { return; }
  const colors = ['#3f7bf4', '#9564f5', '#20b970', '#f6a024', '#c7d0e4', '#ef6882', '#18a6ca'];
  const legend = document.querySelector('#categoryLegend');
  const total = (chartData.category_counts || []).reduce((sum, n) => sum + n, 0);
  if (legend) {
    const entries = (chartData.categories || []).map((name, i) => ({name, color: colors[i % colors.length], value: chartData.category_counts[i]}));
    legend.replaceChildren(...entries.slice(0, 7).map(entry => {
      const row = document.createElement('div'); row.className = 'category-legend-row';
      const swatch = document.createElement('span'); swatch.className = 'legend-swatch'; swatch.style.backgroundColor = entry.color;
      const label = document.createElement('span'); label.className = 'legend-name'; label.textContent = entry.name;
      const qty = document.createElement('strong'); qty.textContent = total ? `${Math.round(entry.value / total * 100)}%` : '0%';
      row.append(swatch, label, qty); return row;
    }));
  }
  function renderCharts() {
    if (!window.Chart) { const fallback = document.querySelector('#stockChartFallback'); if (fallback) fallback.hidden = false; return; }
    window.Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";
    const stock = document.getElementById('stockChart');
    if (stock) {
      const ctx = stock.getContext('2d');
      const grad = ctx.createLinearGradient(0, 0, 0, 230); grad.addColorStop(0, '#4f89fa45'); grad.addColorStop(1, '#4f89fa00');
      new Chart(stock, { type: 'line', data: { labels: chartData.labels, datasets: [
        {label:'Stok Masuk',data:chartData.incoming,borderColor:'#3f7bf4',backgroundColor:grad,borderWidth:2.5,tension:.42,pointRadius:2,pointHoverRadius:5,fill:true},
        {label:'Stok Keluar',data:chartData.outgoing,borderColor:'#a276f5',backgroundColor:'#a276f511',borderWidth:2.5,tension:.42,pointRadius:2,pointHoverRadius:5,fill:true}
      ]}, options: {responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'index'},plugins:{legend:{display:false},tooltip:{backgroundColor:'#152449',padding:12,titleFont:{size:10},bodyFont:{size:11}}},scales:{x:{grid:{display:false},border:{display:false},ticks:{color:'#98a5bb',font:{size:9},maxTicksLimit:7}},y:{beginAtZero:true,border:{display:false},grid:{color:'#ecf0f7'},ticks:{color:'#98a5bb',font:{size:9},precision:0}}}} });
    }
    const cat = document.getElementById('categoryChart');
    if (cat) new Chart(cat, {type:'doughnut',data:{labels:chartData.categories.length?chartData.categories:['Belum ada data'],datasets:[{data:chartData.category_counts.length?chartData.category_counts:[1],backgroundColor:chartData.categories.length?colors:['#e2e8f0'],borderWidth:0,hoverOffset:3,spacing:1}]},options:{responsive:true,maintainAspectRatio:false,cutout:'75%',plugins:{legend:{display:false},tooltip:{enabled:chartData.categories.length>0}}}});
  }
  if (window.Chart) renderCharts(); else window.addEventListener('load', renderCharts);
});
