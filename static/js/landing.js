/* FocusForge landing page interactions (templates/core/landing.html) */
(() => {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  $('#year').textContent = new Date().getFullYear();

  /* ---------- Theme ---------- */
  const themeBtn = $('#themeBtn');
  const icons = {
    dark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>',
    light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
  };
  const paintTheme = () => {
    const t = document.documentElement.dataset.theme;
    themeBtn.innerHTML = icons[t];
    themeBtn.setAttribute('aria-label', t === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
  };
  themeBtn.onclick = () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('ff-theme', next); } catch (e) {}
    paintTheme();
  };
  paintTheme();

  /* ---------- Nav ---------- */
  addEventListener('scroll', () => $('#nav').classList.toggle('scrolled', scrollY > 20), { passive: true });
  const menuBtn = $('#menuBtn'), menu = $('#mobileMenu');
  const setMenu = open => { menu.classList.toggle('open', open); menuBtn.setAttribute('aria-expanded', open); };
  menuBtn.onclick = e => { e.stopPropagation(); setMenu(!menu.classList.contains('open')); };
  document.addEventListener('click', e => { if (!menu.contains(e.target)) setMenu(false); });
  const links = $$('.nav-links a');
  const spy = new IntersectionObserver(es => es.forEach(e => e.isIntersecting &&
    links.forEach(a => a.classList.toggle('active', a.hash === '#' + e.target.id))), { rootMargin: '-45% 0px -50% 0px' });
  ['features', 'how', 'analytics', 'ai'].forEach(id => spy.observe(document.getElementById(id)));

  /* ---------- Helpers ---------- */
  const onView = (el, fn, threshold = .2) => {
    if (!el) return;
    const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { fn(el); io.disconnect(); } }, { threshold, rootMargin: '0px 0px -60px 0px' });
    io.observe(el);
  };
  const fillBars = root => root.querySelectorAll('.bar > i[data-w]').forEach(b => b.style.width = b.dataset.w + '%');
  const countUp = (el, to, ms = 1200, fmt = v => v) => {
    if (reduce) { el.textContent = fmt(to); return; }
    const from = parseInt(el.textContent.replace(/\D/g, '')) || 0, run = el._run = {};
    let t0;
    const step = now => { if (el._run !== run) return; t0 ??= now; const t = Math.min(1, (now - t0) / ms), v = Math.round(from + (to - from) * (1 - (1 - t) ** 3)); el.textContent = fmt(v); if (t < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  };
  const toast = (icon, title, text) => {
    const el = document.createElement('div');
    el.className = 'toast';
    el.innerHTML = `<span class="ico" style="background:var(--orange-soft)">${icon}</span><div><b></b><span></span></div>`;
    el.querySelector('b').textContent = title; el.querySelector(':scope > div > span').textContent = text;
    $('#toasts').append(el); setTimeout(() => el.remove(), 3300);
  };
  const xpFloat = (amount, source) => {
    const r = source.getBoundingClientRect(), el = document.createElement('div');
    el.className = 'xp-float'; el.textContent = `+${amount} XP`;
    el.style.left = r.left + r.width / 2 + 'px'; el.style.top = r.top + 'px';
    document.body.append(el); setTimeout(() => el.remove(), 1500);
  };
  const unlocked = new Set();
  const unlock = (emoji, name, xp) => {
    if (unlocked.has(name)) return; unlocked.add(name);
    $('#unlockEmoji').textContent = emoji; $('#unlockName').textContent = name; $('#unlockXp').textContent = `+${xp} XP`;
    $('#unlock').classList.add('show'); setTimeout(() => $('#unlock').classList.remove('show'), 2600);
  };
  let xp = 1150;
  const addXP = (amount, source) => {
    xp += amount; xpFloat(amount, source);
    ['#dashXp', '#bigXp'].forEach(s => countUp($(s), xp, 700, v => s === '#dashXp' ? v + ' XP' : v));
    const w = (xp % 100) + '%'; $('#dashXpBar').style.width = w; $('#bigXpBar').style.width = w;
    $('#bigXp').nextElementSibling.innerHTML = `Level <b style="color:var(--text)">${Math.floor(xp / 100) + 1}</b> · ${100 - xp % 100} XP to Level ${Math.floor(xp / 100) + 2}`;
  };

  const shimmerIO = new IntersectionObserver(es => es.forEach(e => e.target.classList.toggle('live', e.isIntersecting)));
  $$('.accent').forEach(el => shimmerIO.observe(el));

  /* ---------- Reveal + one-time animations ---------- */
  $$('.reveal, .stagger').forEach(el => onView(el, e => e.classList.add('in'), .12));
  onView($('.preview'), fillBars, .1);
  onView($('#bento'), el => { fillBars(el); el.querySelector('.draw').classList.add('in'); });
  onView($('#hub'), el => el.classList.add('in'), .35);
  onView($('#steps'), el => el.classList.add('in'), .4);
  onView($('.gamify'), fillBars, .3);
  const heroNums = $$('.hero-stat .val[data-count]');
  if (!reduce) { heroNums.forEach(el => el.textContent = '0'); setTimeout(() => heroNums.forEach(el => countUp(el, +el.dataset.count, 1400)), 800); }

  /* ---------- Heatmaps (fixed demo pattern, so it looks the same every visit) ---------- */
  const level = i => [0, 2, 3, 1, 4, 2, 0, 3, 4, 2, 1, 3, 0, 4, 3, 2, 1, 4, 3, 0, 2, 4][(i * 7 + (i >> 3)) % 22];
  const fillHeat = (el, n) => { for (let i = 0; i < n; i++) { const c = document.createElement('i'); const l = level(i); if (l) c.className = 'lv' + l; c.style.transitionDelay = (i * 3) + 'ms'; el.append(c); } };
  fillHeat($('#miniHeat'), 112);
  fillHeat($('#heat'), 182);
  onView($('#heat'), el => el.classList.add('in'), .2);

  /* ---------- Hero: a task gets ticked off after a moment ---------- */
  if (!reduce) setTimeout(() => {
    const next = $('#dashTasks .task:not(.done)');
    if (!next) return;
    next.classList.add('done'); $('#taskCount').textContent = '3 / 5 done';
    addXP(10, next.querySelector('.ck'));
  }, 3600);


  /* ---------- Focus timer ---------- */
  const TOTAL = 1500, CIRC = 678.6;
  let left = TOTAL, timer = null, sessions = 11;
  const ring = $('#ringFg'), time = $('#ringTime'), state = $('#ringState'), btn = $('#timerBtn');
  const render = () => { time.textContent = `${String(left / 60 | 0).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`; ring.style.strokeDashoffset = CIRC * (1 - left / TOTAL); };
  const setState = (text, on, label) => { state.textContent = text; state.classList.toggle('on', on); btn.textContent = label; };
  const stop = () => { clearInterval(timer); timer = null; };
  btn.onclick = () => {
    if (timer) { stop(); return setState('Paused', false, '▶ Resume'); }
    if (!left) left = TOTAL;
    setState('Focusing', true, '❚❚ Pause');
    timer = setInterval(() => {
      left = Math.max(0, left - 20); render();
      if (left) return;
      stop(); setState('Session saved ✓', false, '▶ Start Session');
      $('#sessionCount').textContent = ++sessions;
      toast('🍅', 'Focus session completed', '25 minutes saved');
      addXP(15, btn);
      setTimeout(() => unlock('⏳', '10 Focus Hours', 60), 900);
    }, 100);
  };
  $('#timerReset').onclick = () => { stop(); left = TOTAL; render(); setState('Ready to focus', false, '▶ Start Session'); };
  render();

  /* ---------- Milestones ---------- */
  $$('#msList .ms').forEach(ms => ms.onclick = () => {
    const done = !ms.classList.contains('done');
    ms.classList.toggle('done', done); ms.setAttribute('aria-pressed', done);
    const all = $$('#msList .ms'), pct = Math.round(all.filter(m => m.classList.contains('done')).length / all.length * 100);
    $('#goalPct').textContent = pct; $('#goalBar').style.width = pct + '%';
    if (!done) return;
    addXP(20, ms);
    toast('✨', 'Milestone complete', ms.querySelector('.t').textContent);
    if (pct === 100) setTimeout(() => { addXP(50, $('#goalBar')); unlock('🎯', 'Goal Achiever', 50); }, 700);
  });

  /* ---------- Analytics chart: smooth curves that grow in, axis labels and a hover tooltip ---------- */
  const series = {
    7: { labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], focus: [1.2, 2.5, 1.4, 3.1, 2.2, .8, 1.6], tasks: [3, 5, 2, 6, 4, 1, 3] },
    30: { labels: ['Sep 7', 'Sep 9', 'Sep 11', 'Sep 13', 'Sep 15', 'Sep 17', 'Sep 19', 'Sep 21', 'Sep 23', 'Sep 25', 'Sep 27', 'Sep 29', 'Oct 1', 'Oct 3'], focus: [1, 1.8, 2.4, 1.5, 2.8, 3.2, 2.1, 2.6, 3.4, 2.9, 3.6, 3.1, 3.8, 3.3], tasks: [2, 3, 5, 3, 4, 6, 4, 5, 7, 5, 6, 6, 8, 7] },
    90: { labels: ['Jul 1', 'Jul 8', 'Jul 15', 'Jul 22', 'Aug 1', 'Aug 8', 'Aug 15', 'Aug 22', 'Sep 1', 'Sep 8', 'Sep 15', 'Sep 22'], focus: [8, 10, 9, 12, 14, 13, 16, 15, 18, 17, 20, 22], tasks: [15, 18, 17, 21, 24, 22, 27, 26, 30, 29, 33, 35] }
  };
  const svg = $('#chart'), tip = $('#tip'), chartBox = $('.chart');
  let current = 7, geo = null;
  const curve = pts => pts.map((p, i) => {
    if (!i) return `M${p[0]},${p[1]}`;
    const p0 = pts[i - 2] || pts[i - 1], p1 = pts[i - 1], p3 = pts[i + 1] || p;
    return `C${p1[0] + (p[0] - p0[0]) / 6},${p1[1] + (p[1] - p0[1]) / 6} ${p[0] - (p3[0] - p1[0]) / 6},${p[1] - (p3[1] - p1[1]) / 6} ${p[0]},${p[1]}`;
  }).join(' ');
  const drawChart = (grow = 1) => {
    const d = series[current], W = svg.clientWidth, H = svg.clientHeight, L = 38, R = 30, T = 14, B = 30;
    // Axis top sits just above the highest value, on a round step, so the curves fill the chart.
    const fTop = Math.max(...d.focus), tTop = Math.max(...d.tasks);
    const fStep = [.5, 1, 2, 5, 10].find(s => Math.ceil(fTop / s) <= 7), n = Math.max(3, Math.ceil(fTop / fStep));
    const fMax = n * fStep, tMax = n * [1, 2, 4, 5, 8, 10, 20].find(s => s * n >= tTop);
    const x = i => L + i * (W - L - R) / (d.labels.length - 1), base = H - B;
    const y = (v, max) => base - v * grow / max * (H - T - B);
    const fp = d.focus.map((v, i) => [x(i), y(v, fMax)]), tp = d.tasks.map((v, i) => [x(i), y(v, tMax)]);
    geo = { x, base, fp, tp, d };
    const gap = (H - T - B) / n;
    const grid = Array.from({ length: n + 1 }, (_, k) => {
      const yy = base - k * gap, lbl = gap >= 28 || k % 2 === 0;
      return `<line x1="${L}" x2="${W - R}" y1="${yy}" y2="${yy}"/>` + (lbl ? `<text x="${L - 8}" y="${yy + 4}" text-anchor="end">${(fStep * k).toFixed(fStep < 1 ? 1 : 0)}h</text><text x="${W - R + 8}" y="${yy + 4}">${tMax / n * k}</text>` : '');
    }).join('');
    const step = Math.ceil(d.labels.length / (W < 500 ? 4 : 7));
    const labels = d.labels.map((l, i) => i % step ? '' : `<text x="${x(i)}" y="${H - 8}" text-anchor="middle">${l}</text>`).join('');
    const area = (pts, c) => `<path d="${curve(pts)} L${pts.at(-1)[0]},${base} L${pts[0][0]},${base}Z" fill="url(#${c})"/>`;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = `<defs>
        <linearGradient id="gf" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--orange)" stop-opacity=".28"/><stop offset="1" stop-color="var(--orange)" stop-opacity="0"/></linearGradient>
        <linearGradient id="gt" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--blue)" stop-opacity=".18"/><stop offset="1" stop-color="var(--blue)" stop-opacity="0"/></linearGradient></defs>
      <g class="grid">${grid}</g>${area(tp, 'gt')}${area(fp, 'gf')}
      <path d="${curve(tp)}" fill="none" stroke="var(--blue)" stroke-width="2.5"/>
      <path d="${curve(fp)}" fill="none" stroke="var(--orange)" stroke-width="3"/>
      <line class="cross" id="cross" y1="${T}" y2="${base}"/>
      <circle class="dot" id="dotF" r="5" fill="var(--orange)"/><circle class="dot" id="dotT" r="5" fill="var(--blue)"/>${labels}`;
  };
  // Small smooth line for the Analytics feature card
  const miniPath = curve([62, 52, 57, 37, 42, 27, 32, 17, 22, 12, 20].map((v, i) => [i * 40, v - 6]));
  $('#miniLine').setAttribute('d', miniPath); $('#miniArea').setAttribute('d', `${miniPath} L400,64 L0,64Z`);
  const animateChart = () => {
    if (reduce) return drawChart(1);
    let t0;
    const frame = now => { t0 ??= now; const t = Math.min(1, (now - t0) / 1100); drawChart(1 - (1 - t) ** 4); if (t < 1) requestAnimationFrame(frame); };
    requestAnimationFrame(frame);
  };
  svg.addEventListener('mousemove', e => {
    if (!geo) return;
    const r = svg.getBoundingClientRect(), mx = e.clientX - r.left;
    const i = Math.max(0, Math.min(geo.d.labels.length - 1, Math.round((mx - geo.x(0)) / (geo.x(1) - geo.x(0)))));
    $('#cross').setAttribute('x1', geo.x(i)); $('#cross').setAttribute('x2', geo.x(i));
    [['#dotF', geo.fp], ['#dotT', geo.tp]].forEach(([id, pts]) => { $(id).setAttribute('cx', pts[i][0]); $(id).setAttribute('cy', pts[i][1]); });
    tip.innerHTML = `<b>${geo.d.labels[i] || 'Day ' + (i + 1)}</b><i style="background:var(--orange)"></i>Focus ${geo.d.focus[i]}h<br><i style="background:var(--blue)"></i>Tasks ${geo.d.tasks[i]}`;
    tip.style.left = Math.min(geo.x(i) + 14, r.width - tip.offsetWidth) + 'px';
    chartBox.classList.add('hover');
  });
  svg.addEventListener('mouseleave', () => chartBox.classList.remove('hover'));
  let chartW = 0, resizeQueued = false;
  addEventListener('resize', () => {
    if (!geo || resizeQueued) return;
    resizeQueued = true;
    requestAnimationFrame(() => { resizeQueued = false; if (svg.clientWidth !== chartW) { chartW = svg.clientWidth; drawChart(1); } });
  });
  onView(svg, animateChart, .3);
  $$('#tabs button').forEach(b => b.onclick = () => {
    $$('#tabs button').forEach(x => x.setAttribute('aria-pressed', x === b));
    current = +b.dataset.range; animateChart();
  });

  /* ---------- Numbers count up when they scroll into view ---------- */
  $$('[data-num]').forEach(el => {
    const to = parseFloat(el.dataset.num), suffix = el.dataset.suffix || '';
    if (reduce) return;
    el.textContent = '0' + suffix;
    onView(el, () => countUp(el, to, 1200, v => v + suffix), .5);
  });

  /* ---------- AI coach (demo answers in the real assistant's style) ---------- */
  const answers = {
    first: ['What should I do first?', `Your most urgent work:<table><tr><th>Task</th><th>Due</th><th>Priority</th></tr><tr><td>Pay electricity bill</td><td>Today 5:00 PM</td><td>High</td></tr><tr><td>Book dentist appointment</td><td>Tomorrow</td><td>Medium</td></tr></table><b>Pay the bill first.</b> It takes about 10 minutes and it's due in a few hours, so doing it now keeps it from going overdue.`],
    habits: ['How are my habits going?', `<table><tr><th>Habit</th><th>Streak</th><th>Last 7 days</th></tr><tr><td>Read 20 pages</td><td>5 days</td><td>6/7</td></tr><tr><td>Workout</td><td>2 days</td><td>3/7</td></tr><tr><td>Meditate</td><td>0 days</td><td>1/7</td></tr></table>Reading is strong. Restart meditation by doing it right after you read.`],
    plan: ['Plan my evening', `It's 6 PM, so here's a realistic evening:<ul><li><b>6:00–6:15</b> Pay electricity bill</li><li><b>6:20–6:45</b> Focus: finish presentation slides</li><li><b>7:00</b> Break and dinner</li><li><b>8:00–8:20</b> Read 20 pages (habit)</li></ul>Book the dentist appointment tomorrow morning, when the clinic opens.`],
    book: ['Tell me about Atomic Habits', `<i>Atomic Habits</i> by James Clear shows how tiny, consistent changes compound into big results by focusing on systems, not goals.<br><br><b>Add to FocusForge</b><ul><li><b>Task:</b> Read chapters 1–3 · Medium · Friday</li><li><b>Habit:</b> Read 10 pages · Daily</li><li><b>Goal:</b> Finish the book · 3 milestones</li></ul>`]
  };
  const chat = $('#chat'), chips = $$('#prompts button');
  const bubble = (who, html) => {
    const m = document.createElement('div');
    m.className = 'msg ' + who;
    m.innerHTML = `<span class="avatar">${who === 'user' ? 'K' : '✦'}</span><div class="bubble"></div>`;
    m.querySelector('.bubble').innerHTML = html; chat.append(m); return m;
  };
  const ask = key => {
    const [q, a] = answers[key];
    chat.innerHTML = ''; chips.forEach(c => c.disabled = true);
    bubble('user', q);
    const bot = bubble('bot', '<span class="typing"><i></i><i></i><i></i></span>');
    setTimeout(() => { bot.querySelector('.bubble').innerHTML = a; chips.forEach(c => c.disabled = false); }, reduce ? 0 : 1100);
  };
  chips.forEach(c => c.onclick = () => ask(c.dataset.q));

  /* ---------- FAQ: one answer open at a time ---------- */
  $$('.faq-q').forEach(q => q.onclick = () => {
    const item = q.parentElement, open = !item.classList.contains('open');
    $$('.faq-item.open').forEach(o => { o.classList.remove('open'); o.querySelector('.faq-q').setAttribute('aria-expanded', 'false'); });
    item.classList.toggle('open', open); q.setAttribute('aria-expanded', open);
  });
  onView(chat, () => ask('first'), .5);

})();
