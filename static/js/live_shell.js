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
      const sidebarProgress = document.getElementById('sidebarUserProgress');
      if (sidebarProgress) {
        sidebarProgress.textContent = `Level ${data.level} · ${data.total_xp} XP`;
        sidebarProgress.dataset.level = data.level;
        sidebarProgress.dataset.xp = data.total_xp;
      }
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

  const refreshAchievementToasts = async () => {
    try {
      const response = await fetch('/notifications/achievement-toasts/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        cache: 'no-store',
      });
      if (!response.ok) return;
      const data = await response.json();
      data.notifications?.forEach(notification => {
        window.FocusForge?.toast(
          `${notification.title} ${notification.message}`,
          'achievement',
        );
      });
    } catch (error) {
      /* Achievement notifications remain in the notification list if polling fails. */
    }
  };

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    const options = args[1] || {};
    if ((options.method || 'GET').toUpperCase() === 'POST') {
      window.setTimeout(() => {
        refreshShell(true);
        refreshAchievementToasts();
      }, 120);
    }
    return response;
  };

  window.FocusForge = Object.assign(window.FocusForge || {}, { xpPopup, refreshShell: () => refreshShell(true) });
  refreshAchievementToasts();
  window.setInterval(refreshAchievementToasts, 30000);
  const syncSearchPlaceholder = () => document.querySelectorAll('[data-mobile-placeholder]').forEach(input => {
    input.placeholder = window.matchMedia('(max-width: 640px)').matches ? input.dataset.mobilePlaceholder : input.dataset.desktopPlaceholder;
  });
  syncSearchPlaceholder();
  window.addEventListener('resize', syncSearchPlaceholder);
  refreshShell();
  window.setInterval(refreshShell, 30000);
})();
