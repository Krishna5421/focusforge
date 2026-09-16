(() => {
  const durations = { success: 4200, info: 5000, warning: 6500, error: 8500 };
  const icons = { success: 'bi-check-circle-fill', error: 'bi-exclamation-octagon-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
  const typeOf = value => ['success', 'error', 'warning', 'info'].includes(value) ? value : 'info';
  const textOf = value => String(value || 'Something went wrong. Please try again.').trim();
  const keyOf = (message, type) => `${type}:${message.toLowerCase()}`;
  const container = () => {
    let element = document.querySelector('.toast-container');
    if (!element) { element = document.createElement('div'); element.className = 'toast-container'; element.setAttribute('aria-live', 'polite'); document.body.appendChild(element); }
    return element;
  };
  const dismiss = item => {
    if (!item || item.dataset.dismissing) return;
    item.dataset.dismissing = 'true'; item.classList.add('hide'); window.setTimeout(() => item.remove(), 240);
  };
  const decorate = (item, message, type) => {
    const safeType = typeOf(type), safeMessage = textOf(message);
    item.className = `toast ${safeType}`; item.dataset.toastKey = keyOf(safeMessage, safeType);
    item.setAttribute('role', safeType === 'error' || safeType === 'warning' ? 'alert' : 'status'); item.replaceChildren();
    const icon = document.createElement('span'); icon.className = 'toast-icon'; icon.setAttribute('aria-hidden', 'true'); icon.innerHTML = `<i class="bi ${icons[safeType]}"></i>`;
    const text = document.createElement('span'); text.className = 'toast-message'; text.textContent = safeMessage;
    const close = document.createElement('button'); close.className = 'toast-dismiss'; close.type = 'button'; close.setAttribute('aria-label', 'Dismiss notification'); close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>'; close.addEventListener('click', () => dismiss(item));
    item.append(icon, text, close); return item;
  };
  const toast = (message, type = 'success') => {
    const safeType = typeOf(type), safeMessage = textOf(message), key = keyOf(safeMessage, safeType);
    const existing = [...document.querySelectorAll('.toast')].find(item => item.dataset.toastKey === key);
    if (existing) return existing;
    const item = decorate(document.createElement('div'), safeMessage, safeType); container().appendChild(item); window.setTimeout(() => dismiss(item), durations[safeType]); return item;
  };
  document.querySelectorAll('.toast-container .toast').forEach(item => { const type = item.dataset.toastType || [...item.classList].find(name => ['success', 'error', 'warning', 'info'].includes(name)); const message = item.textContent; decorate(item, message, type); window.setTimeout(() => dismiss(item), durations[typeOf(type)]); });
  const apiError = (error, fallback = 'Unable to complete this action. Please try again.') => toast(error?.focusForgeMessage || error?.message || fallback, 'error');
  const redirectWithToast = (url, message, type = 'success') => {
    try { sessionStorage.setItem('focusforge-next-toast', JSON.stringify({ message: textOf(message), type: typeOf(type) })); } catch (error) { /* Navigation still succeeds if storage is unavailable. */ }
    window.location.assign(url);
  };
  try {
    const pending = JSON.parse(sessionStorage.getItem('focusforge-next-toast'));
    if (pending?.message) toast(pending.message, pending.type);
    sessionStorage.removeItem('focusforge-next-toast');
  } catch (error) { sessionStorage.removeItem('focusforge-next-toast'); }
  window.addEventListener('unhandledrejection', event => { if (!event.reason?.focusForgeNotified) toast('Something went wrong. Please try again.', 'error'); });
  window.FocusForge = Object.assign(window.FocusForge || {}, { toast, apiError, dismissToast: dismiss, redirectWithToast });
})();
