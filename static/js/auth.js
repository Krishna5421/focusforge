document.addEventListener('DOMContentLoaded', function () {
    const authCard = document.getElementById('authCard');
    const showRegister = document.getElementById('showRegister');
    const showLogin = document.getElementById('showLogin');

    if (showRegister) {
        showRegister.addEventListener('click', function () {
            authCard.classList.add('right-panel-active');
        });
    }

    if (showLogin) {
        showLogin.addEventListener('click', function () {
            authCard.classList.remove('right-panel-active');
        });
    }

    const toggleButtons = document.querySelectorAll('.toggle-password');
    toggleButtons.forEach(function (icon) {
        icon.addEventListener('click', function () {
            const input = icon.previousElementSibling;
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        });
    });
});