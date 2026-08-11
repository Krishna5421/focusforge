document.addEventListener('DOMContentLoaded', function () {
    const display = document.getElementById('pomodoroDisplay');
    const startBtn = document.getElementById('startBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    const stopBtn = document.getElementById('stopBtn');
    const durationSelect = document.getElementById('durationSelect');
    const customDuration = document.getElementById('customDuration');

    let totalSeconds = 25 * 60;
    let remainingSeconds = totalSeconds;
    let timerInterval = null;
    let sessionId = null;
    let focusSecondsElapsed = 0;

    function getCsrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                return cookie.substring(name.length + 1);
            }
        }
        return '';
    }

    function updateDisplay() {
        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = remainingSeconds % 60;
        const minStr = minutes < 10 ? '0' + minutes : minutes;
        const secStr = seconds < 10 ? '0' + seconds : seconds;
        display.textContent = minStr + ':' + secStr;
    }

    function getSelectedDuration() {
        if (customDuration.value) {
            return parseInt(customDuration.value, 10);
        }
        return parseInt(durationSelect.value, 10);
    }

    function tick() {
        if (remainingSeconds > 0) {
            remainingSeconds -= 1;
            focusSecondsElapsed += 1;
            updateDisplay();
        } else {
            clearInterval(timerInterval);
            completeSession();
        }
    }

    function startTimer() {
        const duration = getSelectedDuration();
        totalSeconds = duration * 60;
        remainingSeconds = totalSeconds;
        focusSecondsElapsed = 0;
        updateDisplay();

        fetch('/pomodoro/start/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'duration=' + duration,
        })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            sessionId = data.session_id;
            timerInterval = setInterval(tick, 1000);

            startBtn.disabled = true;
            pauseBtn.disabled = false;
            stopBtn.disabled = false;
            resumeBtn.disabled = true;
        });
    }

    function pauseTimer() {
        clearInterval(timerInterval);
        updateSessionStatus('PAUSED');
        pauseBtn.disabled = true;
        resumeBtn.disabled = false;
    }

    function resumeTimer() {
        timerInterval = setInterval(tick, 1000);
        updateSessionStatus('RUNNING');
        pauseBtn.disabled = false;
        resumeBtn.disabled = true;
    }

    function stopTimer() {
        clearInterval(timerInterval);
        updateSessionStatus('STOPPED');
        resetControls();
    }

    function completeSession() {
        updateSessionStatus('COMPLETED');
        resetControls();
        alert('Focus session complete! Great work.');
    }

    function updateSessionStatus(status) {
        if (!sessionId) return;
        fetch('/pomodoro/' + sessionId + '/update/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'status=' + status + '&focus_seconds=' + focusSecondsElapsed,
        });
    }

    function resetControls() {
        startBtn.disabled = false;
        pauseBtn.disabled = true;
        resumeBtn.disabled = true;
        stopBtn.disabled = true;
        sessionId = null;
    }

    startBtn.addEventListener('click', startTimer);
    pauseBtn.addEventListener('click', pauseTimer);
    resumeBtn.addEventListener('click', resumeTimer);
    stopBtn.addEventListener('click', stopTimer);

    updateDisplay();
});