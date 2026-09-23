(() => {
  const widget = document.getElementById('ffFloatingTimer');
  if (!widget) return;

  const stateUrl = widget.dataset.stateUrl;
  const csrfToken = widget.dataset.csrf;
  const source = document.getElementById('ffTimerSource');
  const title = document.getElementById('ffTimerTitle');
  const time = document.getElementById('ffTimerTime');
  const progress = document.getElementById('ffTimerProgress');
  const toggle = document.getElementById('ffTimerToggle');
  const save = document.getElementById('ffTimerSave');
  let current = null;
  let deadline = null;
  let remaining = 0;
  let busy = false;
  let finishing = false;

  async function readJson(response) {
    if (response.redirected && /login/i.test(response.url)) {
      throw new Error('Your sign-in session has expired. Please sign in again.');
    }
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new Error(`The timer request returned a page instead of data (HTTP ${response.status}). Reload the page and try again.`);
    }
    return response.json();
  }

  const secondsRemaining = () => current?.running && deadline !== null
    ? Math.max(0, Math.ceil((deadline - Date.now()) / 1000))
    : remaining;

  const formatTime = value => {
    const safe = Math.max(0, value);
    const hours = Math.floor(safe / 3600);
    const minutes = Math.floor((safe % 3600) / 60);
    const seconds = safe % 60;
    return hours
      ? `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
      : `${minutes}:${String(seconds).padStart(2, '0')}`;
  };

  const render = () => {
    if (!current) return;
    const left = secondsRemaining();
    remaining = left;
    time.textContent = formatTime(left);
    source.textContent = current.label;
    title.textContent = current.title || '';
    toggle.innerHTML = `<i class="bi bi-${current.running ? 'pause' : 'play'}-fill" aria-hidden="true"></i>`;
    toggle.setAttribute('aria-label', current.running ? 'Pause timer' : 'Resume timer');
    widget.classList.toggle('is-paused', !current.running);
    const elapsed = current.running
      ? Math.max(0, current.duration_seconds - left)
      : current.elapsed_seconds;
    progress.style.width = `${current.duration_seconds ? Math.min(100, Math.max(0, elapsed / current.duration_seconds * 100)) : 0}%`;
    widget.hidden = false;
  };

  async function refresh() {
    try {
      const response = await fetch(stateUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, cache: 'no-store' });
      if (!response.ok) return;
      const data = await readJson(response);
      if (!data.active) {
        current = null;
        deadline = null;
        widget.hidden = true;
        return;
      }
      current = data;
      remaining = Math.max(0, Number(data.remaining_seconds) || 0);
      deadline = data.running ? Date.now() + remaining * 1000 : null;
      finishing = false;
      render();
    } catch (_) {
      // Keep the last known timer visible during a brief network interruption.
    }
  }

  async function post(url, values) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
      body: new URLSearchParams(values),
    });
    const data = await readJson(response);
    if (!response.ok) throw new Error(data.error || 'Unable to update the timer.');
    return data;
  }

  const reportError = error => {
    if (window.FocusForge?.apiError) window.FocusForge.apiError(error, 'Unable to update the timer.');
    else window.FocusForge?.toast(error.message || 'Unable to update the timer.', 'error');
  };

  async function finishAtZero() {
    if (finishing || !current?.running) return;
    // The dashboard and Focus page already own completion for their local
    // timer controls. Let those page timers finish to avoid duplicate writes.
    if (current.source === 'focus' && document.querySelector('.focus-widget, .focus-main')) return;
    finishing = true;
    try {
      if (current.source === 'focus') {
        await post(current.update_url, {
          status: 'COMPLETED', focus_seconds: current.duration_seconds,
        });
        current = null;
        widget.hidden = true;
        window.location.reload();
      } else {
        await post(current.pause_url, {});
        await refresh();
      }
    } catch (error) {
      finishing = false;
      reportError(error);
    }
  }

  toggle.addEventListener('click', async () => {
    if (!current || busy) return;
    busy = true;
    toggle.disabled = true;
    try {
      if (current.source === 'focus') {
        await post(current.update_url, {
          status: current.running ? 'PAUSED' : 'RUNNING',
          focus_seconds: current.duration_seconds - secondsRemaining(),
        });
      } else {
        await post(current.running ? current.pause_url : current.start_url, {});
      }
      await refresh();
      window.location.reload();
    } catch (error) {
      reportError(error);
    } finally {
      busy = false;
      toggle.disabled = false;
    }
  });

  save.addEventListener('click', async () => {
    if (!current || busy) return;
    busy = true;
    toggle.disabled = true;
    save.disabled = true;
    try {
      if (current.source === 'focus') {
        await post(current.update_url, {
          status: 'STOPPED', focus_seconds: current.duration_seconds - secondsRemaining(),
        });
      } else {
        await post(current.save_url, {});
      }
      current = null;
      widget.hidden = true;
      window.FocusForge?.toast('Timer session saved.', 'success');
      window.location.reload();
    } catch (error) {
      reportError(error);
    } finally {
      busy = false;
      toggle.disabled = false;
      save.disabled = false;
    }
  });

  window.FocusForgeTimer = { refresh };
  refresh();
  window.setInterval(() => {
    if (!current) return;
    render();
    if (secondsRemaining() <= 0) finishAtZero();
  }, 1000);
  window.setInterval(refresh, 15000);
})();
