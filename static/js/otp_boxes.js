// Turns the plain 6-digit code field into digit boxes, and runs resend countdowns.
(() => {
  document.querySelectorAll('.otp-boxes').forEach(group => {
    const form = group.closest('form');
    const realInput = form?.querySelector('#id_otp');
    if (!realInput) return;
    const boxes = [...group.querySelectorAll('.otp-box')];
    const submit = form.querySelector('[type="submit"]');

    const sync = () => {
      realInput.value = boxes.map(box => box.value).join('');
      boxes.forEach(box => box.classList.toggle('filled', box.value !== ''));
    };
    // Spread digits across the boxes from `start` (typing, paste, and one-tap code autofill).
    const fill = (start, text) => {
      const digits = text.replace(/\D/g, '').slice(0, boxes.length - start).split('');
      digits.forEach((digit, offset) => { boxes[start + offset].value = digit; });
      sync();
      if (realInput.value.length === boxes.length) submit?.focus();
      else boxes[Math.min(start + digits.length, boxes.length - 1)].focus();
    };

    boxes.forEach((box, index) => {
      box.addEventListener('input', () => {
        const value = box.value;
        box.value = '';
        fill(index, value);
      });
      box.addEventListener('keydown', event => {
        if (event.key === 'Backspace' && !box.value && index > 0) {
          event.preventDefault();
          boxes[index - 1].value = '';
          boxes[index - 1].focus();
          sync();
        } else if (event.key === 'ArrowLeft' && index > 0) {
          event.preventDefault();
          boxes[index - 1].focus();
        } else if (event.key === 'ArrowRight' && index < boxes.length - 1) {
          event.preventDefault();
          boxes[index + 1].focus();
        }
      });
      box.addEventListener('paste', event => {
        event.preventDefault();
        fill(index, (event.clipboardData || window.clipboardData).getData('text'));
      });
      box.addEventListener('focus', () => box.select());
    });

    // Switch to boxes, keeping any digits the server sent back after an error.
    const fallback = form.querySelector('.otp-fallback');
    if (fallback) fallback.hidden = true;
    group.hidden = false;
    const label = form.querySelector('label[for="id_otp"]');
    if (label) label.htmlFor = '';
    const existing = realInput.value.replace(/\D/g, '');
    boxes.forEach((box, index) => { box.value = existing[index] || ''; });
    sync();
    (boxes.find(box => !box.value) || boxes[0]).focus();
  });

  // <button data-countdown="45" data-label="Resend code"> stays disabled until the wait is over.
  document.querySelectorAll('[data-countdown]').forEach(button => {
    let remaining = parseInt(button.dataset.countdown, 10) || 0;
    const label = button.dataset.label || button.textContent.trim();
    const render = () => {
      const minutes = Math.floor(remaining / 60), seconds = String(remaining % 60).padStart(2, '0');
      button.disabled = remaining > 0;
      button.textContent = remaining > 0 ? `${label} in ${minutes}:${seconds}` : label;
    };
    render();
    if (remaining <= 0) return;
    const timer = window.setInterval(() => {
      remaining -= 1;
      render();
      if (remaining <= 0) window.clearInterval(timer);
    }, 1000);
  });
})();
