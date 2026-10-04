// Shows a spinner on <button data-loading-text="..."> while its form submits, and blocks double submits.
(() => {
  const reset = button => {
    if (!button.dataset.originalHtml) return;
    button.innerHTML = button.dataset.originalHtml;
    button.disabled = false;
    button.classList.remove('is-loading');
    button.removeAttribute('aria-busy');
    delete button.dataset.originalHtml;
  };

  document.addEventListener('submit', event => {
    if (event.defaultPrevented) return; // Another handler stopped this submit; don't show loading.
    const form = event.target;
    const button = (event.submitter?.matches('[data-loading-text]') && event.submitter)
      || form.querySelector('button[type="submit"][data-loading-text]');
    if (!button) return;
    if (button.classList.contains('is-loading')) {
      event.preventDefault(); // Already submitting; ignore repeated clicks or Enter presses.
      return;
    }
    button.dataset.originalHtml = button.innerHTML;
    // Wait a tick so the browser has already queued the submission before the button is disabled.
    window.setTimeout(() => {
      button.classList.add('is-loading');
      button.setAttribute('aria-busy', 'true');
      button.disabled = true;
      button.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span><span></span>';
      button.lastElementChild.textContent = button.dataset.loadingText;
    }, 0);
  });

  // Coming back with the browser's Back button can restore the page from cache mid-"loading".
  window.addEventListener('pageshow', event => {
    if (event.persisted) document.querySelectorAll('button[data-loading-text]').forEach(reset);
  });
})();
