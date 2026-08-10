document.addEventListener('DOMContentLoaded', function () {
    const hamburgerBtn = document.getElementById('hamburgerBtn');
    const drawer = document.getElementById('drawer');
    const drawerBackdrop = document.getElementById('drawerBackdrop');
    const drawerClose = document.getElementById('drawerClose');

    function openDrawer() {
        drawer.classList.add('open');
        drawerBackdrop.classList.add('visible');
    }
    function closeDrawer() {
        drawer.classList.remove('open');
        drawerBackdrop.classList.remove('visible');
    }
    if (hamburgerBtn) hamburgerBtn.addEventListener('click', openDrawer);
    if (drawerClose) drawerClose.addEventListener('click', closeDrawer);
    if (drawerBackdrop) drawerBackdrop.addEventListener('click', closeDrawer);

    // Theme toggle — persists via localStorage, syncs the moon/sun icon
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const htmlEl = document.documentElement;

    function applyTheme(theme) {
        if (theme === 'light') {
            htmlEl.setAttribute('data-theme', 'light');
            if (themeIcon) { themeIcon.classList.remove('bi-moon-stars'); themeIcon.classList.add('bi-sun'); }
        } else {
            htmlEl.removeAttribute('data-theme');
            if (themeIcon) { themeIcon.classList.remove('bi-sun'); themeIcon.classList.add('bi-moon-stars'); }
        }
        localStorage.setItem('ff-theme', theme);
    }

    applyTheme(localStorage.getItem('ff-theme') || 'dark');

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const current = htmlEl.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
            applyTheme(current === 'light' ? 'dark' : 'light');
        });
    }

    // Delete confirmation modal — any element with data-delete-url triggers this
    const deleteModalEl = document.getElementById('deleteModal');
    if (deleteModalEl) {
        const deleteModal = new bootstrap.Modal(deleteModalEl);
        const deleteModalText = document.getElementById('deleteModalText');
        const deleteModalForm = document.getElementById('deleteModalForm');

        document.querySelectorAll('[data-delete-url]').forEach(function (trigger) {
            trigger.addEventListener('click', function (e) {
                e.preventDefault();
                const url = trigger.getAttribute('data-delete-url');
                const name = trigger.getAttribute('data-delete-name') || 'this item';
                deleteModalText.textContent = 'Are you sure you want to delete "' + name + '"? This action cannot be undone.';
                deleteModalForm.setAttribute('action', url);
                deleteModal.show();
            });
        });
    }
});