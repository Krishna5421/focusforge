(() => {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const menu = document.getElementById('menuToggle');
  const theme = document.getElementById('themeToggle');

  const applyTheme = value => {
    document.documentElement.setAttribute('data-theme', value);
    const icon = theme?.querySelector('i');
    if (icon) icon.className = `bi ${value === 'dark' ? 'bi-moon-fill' : 'bi-sun-fill'}`;
    if (theme) {
      const label = value === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
      theme.title = label;
      theme.setAttribute('aria-label', label);
    }
  };
  applyTheme(localStorage.getItem('ff-theme') || 'dark');

  menu?.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
  });

  overlay?.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  });

  theme?.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('ff-theme', next);
    applyTheme(next);
  });

  document.querySelectorAll('[data-avatar-image]').forEach(image => image.addEventListener('error', () => {
    image.hidden = true;
    const fallback = image.nextElementSibling;
    if (fallback) fallback.hidden = false;
  }, { once: true }));

  document.querySelectorAll('.toast').forEach(toast => {
    window.setTimeout(() => {
      toast.classList.add('hide');
      window.setTimeout(() => toast.remove(), 240);
    }, 3500);
  });

  const toastContainer = () => {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      container.setAttribute('aria-live', 'polite');
      document.body.appendChild(container);
    }
    return container;
  };

  const toast = (message, type = 'success') => {
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    const icon = type === 'error' ? 'bi-exclamation-circle' : type === 'info' ? 'bi-info-circle' : 'bi-check-lg';
    item.innerHTML = `<span class="toast-icon"><i class="bi ${icon}"></i></span><span>${message}</span>`;
    toastContainer().appendChild(item);
    window.setTimeout(() => {
      item.classList.add('hide');
      window.setTimeout(() => item.remove(), 240);
    }, 3500);
  };

  const xpPopup = amount => {
    if (!amount) return;
    const popup = document.createElement('div');
    popup.className = 'xp-popup';
    popup.textContent = `${amount > 0 ? '+' : ''}${amount} XP`;
    document.body.appendChild(popup);
    window.setTimeout(() => popup.remove(), 1500);
  };

  let knownXp = null;
  const refreshShell = async (showXp = false) => {
    try {
      const response = await fetch('/api/dashboard-summary/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!response.ok) return;
      const data = await response.json();
      const bell = document.getElementById('notificationBell');
      if (bell) {
        let dot = bell.querySelector('.dot');
        if (data.unread_notifications) {
          if (!dot) {
            dot = document.createElement('span');
            dot.className = 'dot';
            bell.appendChild(dot);
          }
        } else {
          dot?.remove();
        }
      }
      if (showXp && knownXp !== null) xpPopup(data.total_xp - knownXp);
      knownXp = data.total_xp;
    } catch (error) {
      /* Keep navigation and page actions independent of a background refresh. */
    }
  };

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    const options = args[1] || {};
    if ((options.method || 'GET').toUpperCase() === 'POST') window.setTimeout(() => refreshShell(true), 120);
    return response;
  };

  window.FocusForge = { toast, xpPopup, refreshShell: () => refreshShell(true) };
  refreshShell();
  window.setInterval(refreshShell, 30000);
})();