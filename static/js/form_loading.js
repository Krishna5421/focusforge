// Loading states for buttons.
//  - Forms: <button data-loading-text="Saving…"> shows a spinner while its form submits and blocks double submits.
//  - Scripts: FocusForge.withLoading(button, 'Saving…', async () => { ... }) does the same around a fetch.
(() => {
  const start = (button, text) => {
    if (!button || button.classList.contains('is-loading')) return false;
    button.dataset.originalHtml = button.innerHTML;
    button.classList.add('is-loading');
    button.setAttribute('aria-busy', 'true');
    button.disabled = true;
    button.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span><span></span>';
    button.lastElementChild.textContent = text;
    return true;
  };

  const reset = button => {
    if (!button || button.dataset.originalHtml === undefined) return;
    button.innerHTML = button.dataset.originalHtml;
    button.disabled = false;
    button.classList.remove('is-loading');
    button.removeAttribute('aria-busy');
    delete button.dataset.originalHtml;
  };

  // Returned by a task that is navigating away, so the button keeps spinning until the next page loads.
  const KEEP_LOADING = Symbol('keep-loading');

  // Runs `task` with the button in its loading state; returns undefined if a run is already in progress.
  const withLoading = async (button, text, task) => {
    if (!start(button, text)) return undefined;
    let result;
    try {
      result = await task();
      return result;
    } finally {
      if (result !== KEEP_LOADING) reset(button);
    }
  };

  document.addEventListener('submit', event => {
    if (event.defaultPrevented) return; // Another handler stopped this submit (or handles it with fetch).
    const button = (event.submitter?.matches('[data-loading-text]') && event.submitter)
      || event.target.querySelector('button[type="submit"][data-loading-text]');
    if (!button) return;
    if (button.classList.contains('is-loading')) {
      event.preventDefault(); // Already submitting; ignore repeated clicks or Enter presses.
      return;
    }
    // Wait a tick so the browser has already queued the submission before the button is disabled.
    window.setTimeout(() => start(button, button.dataset.loadingText), 0);
  });

  // Coming back with the browser's Back button can restore the page from cache mid-"loading".
  window.addEventListener('pageshow', event => {
    if (event.persisted) document.querySelectorAll('.is-loading[aria-busy]').forEach(reset);
  });

  window.FocusForge = Object.assign(window.FocusForge || {}, { withLoading, KEEP_LOADING, startLoading: start, stopLoading: reset });
})();
