/* =========================================
   FOCUSFORGE HABITS PAGE - TASK PAGE PATTERN
   ========================================= */

let frequencyChart = null;

document.addEventListener('DOMContentLoaded', function () {
    initFilterToggle();
    initHabitToggle();
    initFrequencyChart();
    initCustomDropdowns();
    initCalendar();
});

/* ---------- 1. Filter Panel Toggle ---------- */
function initFilterToggle() {
    const filterToggle = document.getElementById('filterToggle');
    const filterPanel = document.getElementById('filterPanel');
    if (!filterToggle || !filterPanel) return;

    filterToggle.addEventListener('click', function () {
        const isHidden = filterPanel.style.display === 'none' || filterPanel.style.display === '';
        filterPanel.style.display = isHidden ? 'block' : 'none';
    });
}

/* ---------- 2. AJAX Habit Toggle (Same as Task Page) ---------- */
function initHabitToggle() {
    document.querySelectorAll('.task-check').forEach(function(element) {
        element.addEventListener('click', function(e) {
            e.stopPropagation();
            
            const habitId = this.dataset.habitId;
            if (!habitId) return;
            
            const row = this.closest('.task-row-item');
            const titleEl = row ? row.querySelector('.task-title') : null;
            const streakEl = row ? row.querySelector('.streak-badge, .text-muted') : null;
            const progressFill = row ? row.querySelector('.progress-bar-fill') : null;
            const progressText = row ? row.querySelector('.progress-text') : null;
            
            const isCurrentlyCompleted = this.classList.contains('done');
            const willBeCompleted = !isCurrentlyCompleted;
            
            // ⚡ INSTANT UI UPDATE (Optimistic)
            if (willBeCompleted) {
                this.classList.add('done');
                this.innerHTML = '<i class="bi bi-check"></i>';
                if (titleEl) titleEl.classList.add('task-done');
            } else {
                this.classList.remove('done');
                this.innerHTML = '';
                if (titleEl) titleEl.classList.remove('task-done');
            }
            
            // Visual feedback animation
            this.style.transform = 'scale(0.9)';
            setTimeout(() => { this.style.transform = 'scale(1)'; }, 150);
            
            // 🔄 Sync with server in background
            fetch('/habits/ajax/' + habitId + '/toggle/', {
                method: 'POST',
                headers: { 
                    'X-CSRFToken': csrfToken, 
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(res => {
                if (!res.ok) throw new Error('Server error');
                return res.json();
            })
            .then(data => {
                if (!data.success) throw new Error('Toggle failed');
                
                // Update stats
                bumpStat('statCompleted', data.completed_today_count - parseInt(document.getElementById('statCompleted').textContent));
                bumpStat('statStreaks', data.active_streaks - parseInt(document.getElementById('statStreaks').textContent));
                
                // Update streak badge
                if (streakEl) {
                    if (data.streak > 0) {
                        streakEl.className = 'streak-badge';
                        streakEl.innerHTML = '<i class="bi bi-fire"></i> ' + data.streak + ' days';
                    } else {
                        streakEl.className = 'text-muted';
                        streakEl.textContent = '0 days';
                    }
                }
                
                // Update progress bar
                if (progressFill && progressText) {
                    progressFill.style.width = data.completion_rate + '%';
                    progressText.textContent = data.completion_rate + '%';
                }
                
                // Update calendar
                updateCalendarToday(data.completed);
                
                // Show toast
                showToast(
                    data.completed ? 'Habit completed! +XP 🔥' : 'Habit unchecked',
                    data.completed ? 'success' : 'info'
                );
                
                console.log('Habit toggled successfully');
            })
            .catch(err => {
                console.error('Toggle error:', err);
                
                // Revert UI if server failed
                if (willBeCompleted) {
                    this.classList.remove('done');
                    this.innerHTML = '';
                    if (titleEl) titleEl.classList.remove('task-done');
                } else {
                    this.classList.add('done');
                    this.innerHTML = '<i class="bi bi-check"></i>';
                    if (titleEl) titleEl.classList.add('task-done');
                }
                
                showToast('Failed to update habit. Please try again.', 'error');
            });
        });
    });
}

/* ---------- Helper: Live Stat Counter ---------- */
function bumpStat(id, delta) {
    const el = document.getElementById(id);
    if (!el) return;
    const val = parseInt(el.textContent, 10) || 0;
    el.textContent = Math.max(0, val + delta);
}

/* ---------- Helper: Toast Notification ---------- */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    const colors = {
        success: 'rgba(99, 201, 137, 0.95)',
        error: 'rgba(231, 122, 122, 0.95)',
        info: 'rgba(99, 179, 237, 0.95)'
    };
    
    toast.style.cssText = `
        background: ${colors[type]};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease;
        min-width: 250px;
    `;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/* ---------- 3. Frequency Donut Chart ---------- */
function initFrequencyChart() {
    const canvas = document.getElementById('frequencyChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    const total = frequencyData.daily + frequencyData.weekly;
    const isEmpty = total === 0;

    try {
        frequencyChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: isEmpty ? ['No habits'] : ['Daily', 'Weekly'],
                datasets: [{
                    data: isEmpty ? [1] : [frequencyData.daily, frequencyData.weekly],
                    backgroundColor: isEmpty
                        ? (isLight ? 'rgba(15,23,42,0.08)' : 'rgba(255,255,255,0.06)')
                        : ['#63B3ED', '#8B5CF6'],
                    borderWidth: 0,
                    spacing: isEmpty ? 0 : 2,
                    borderRadius: isEmpty ? 0 : 6,
                    hoverOffset: isEmpty ? 0 : 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '74%',
                animation: { animateRotate: true, duration: 800, easing: 'easeOutQuart' },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: !isEmpty,
                        backgroundColor: isLight ? 'rgba(255,255,255,0.96)' : 'rgba(16,21,29,0.96)',
                        titleColor: isLight ? '#0f172a' : '#EDF1F7',
                        bodyColor: isLight ? '#475569' : '#98A4B5',
                        borderColor: isLight ? 'rgba(15,23,42,0.12)' : 'rgba(255,255,255,0.10)',
                        borderWidth: 1,
                        cornerRadius: 10,
                        padding: 10,
                        usePointStyle: true,
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed;
                                const pct = Math.round((value / total) * 100);
                                return ' ' + value + ' habit' + (value === 1 ? '' : 's') + ' (' + pct + '%)';
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Chart rendering failed:', error);
    }
}

/* ---------- 4. Custom Filter Dropdowns ---------- */
function initCustomDropdowns() {
    document.querySelectorAll('.custom-select').forEach(select => {
        const trigger = select.querySelector('.custom-select__trigger');
        const options = select.querySelectorAll('.custom-option');
        const hiddenInput = select.querySelector('input[type="hidden"]');
        const triggerText = trigger.querySelector('span');
        
        trigger.addEventListener('click', function(e) {
            e.stopPropagation();
            document.querySelectorAll('.custom-select.open').forEach(openSelect => {
                if (openSelect !== select) openSelect.classList.remove('open');
            });
            select.classList.toggle('open');
        });
        
        options.forEach(option => {
            option.addEventListener('click', function() {
                const value = this.getAttribute('data-value');
                const text = this.textContent;
                
                triggerText.textContent = text;
                hiddenInput.value = value;
                
                options.forEach(opt => opt.classList.remove('selected'));
                this.classList.add('selected');
                
                select.classList.remove('open');
            });
        });
    });
    
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.custom-select')) {
            document.querySelectorAll('.custom-select.open').forEach(select => {
                select.classList.remove('open');
            });
        }
    });
}

/* ---------- 5. Real Calendar with API Data ---------- */
function initCalendar() {
    const grid = document.getElementById('calendarGrid');
    const monthYearLabel = document.getElementById('calendarMonthYear');
    if (!grid || !monthYearLabel) return;

    const date = new Date();
    const currentYear = date.getFullYear();
    const currentMonth = date.getMonth();
    const today = date.getDate();

    const monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"];
    monthYearLabel.textContent = monthNames[currentMonth] + ' ' + currentYear;

    const firstDay = new Date(currentYear, currentMonth, 1).getDay();
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

    grid.innerHTML = '';

    for (let i = 0; i < firstDay; i++) {
        const emptyDay = document.createElement('div');
        emptyDay.className = 'calendar-day empty';
        grid.appendChild(emptyDay);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dayEl = document.createElement('div');
        dayEl.className = 'calendar-day';
        dayEl.textContent = day;

        if (day === today) {
            dayEl.classList.add('today');
        } else if (day < today) {
            fetchCompletionStatus(currentYear, currentMonth, day, dayEl);
        }

        grid.appendChild(dayEl);
    }
}

function fetchCompletionStatus(year, month, day, dayEl) {
    const dateStr = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');

    fetch('/habits/api/completion/' + dateStr + '/')
        .then(res => res.json())
        .then(data => {
            if (data.has_completion) {
                dayEl.classList.add('has-completion');
                dayEl.title = data.count + ' habit(s) completed';
            }
        })
        .catch(err => console.error('Calendar fetch failed:', err));
}

function updateCalendarToday(completed) {
    const todayEl = document.querySelector('.calendar-day.today');
    if (todayEl) {
        if (completed) {
            todayEl.classList.add('has-completion');
        } else {
            todayEl.classList.remove('has-completion');
        }
    }
}