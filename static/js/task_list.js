/* =========================================
   FOCUSFORGE TASKS - OPTIMIZED JAVASCRIPT
   ========================================= */

let priorityChart = null;

document.addEventListener('DOMContentLoaded', function () {
    initFilterToggle();
    initTaskToggle();
    initPriorityChart();
    initCustomDropdowns();
    initDeleteModal();
    fixDropdownClipping();
    
    // Reorder tasks on page load so completed are at bottom
    reorderTasks();
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

/* ---------- 2. Priority Donut Chart (Chart.js) ---------- */
function initPriorityChart() {
    const canvas = document.getElementById('priorityChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    const total = priorityData.high + priorityData.medium + priorityData.low;
    const isEmpty = total === 0;

    try {
        priorityChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: isEmpty ? ['No tasks'] : ['High', 'Medium', 'Low'],
                datasets: [{
                    data: isEmpty ? [1] : [priorityData.high, priorityData.medium, priorityData.low],
                    backgroundColor: isEmpty
                        ? (isLight ? 'rgba(15,23,42,0.08)' : 'rgba(255,255,255,0.06)')
                        : ['#E77A7A', '#E5B054', '#63C989'],
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
                        boxWidth: 7,
                        boxHeight: 7,
                        boxPadding: 4,
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed;
                                const pct = Math.round((value / total) * 100);
                                return ' ' + value + ' task' + (value === 1 ? '' : 's') + ' (' + pct + '%)';
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

/* ---------- 3. AJAX Task Status Toggle & Reordering ---------- */
function initTaskToggle() {
    document.querySelectorAll('.task-checkbox, .task-check').forEach(function(element) {
        element.addEventListener('click', function(e) {
            e.stopPropagation();
            
            const taskId = this.dataset.taskId;
            if (!taskId) return;
            
            const row = this.closest('.task-row-item');
            const titleEl = row ? row.querySelector('.task-title') : null;
            const statusBadge = row ? row.querySelector('.status-badge') : null;
            
            const isCurrentlyCompleted = this.classList.contains('done') || this.checked;
            const willBeCompleted = !isCurrentlyCompleted;
            
            // ⚡ INSTANT UI UPDATE (Optimistic)
            if (willBeCompleted) {
                if (this.tagName === 'INPUT') this.checked = true;
                else {
                    this.classList.add('done');
                    this.innerHTML = '<i class="bi bi-check"></i>';
                }
                if (titleEl) titleEl.classList.add('task-done');
                if (statusBadge) {
                    statusBadge.className = 'status-badge status-completed';
                    statusBadge.textContent = 'Completed';
                }
                bumpStat('statPending', -1);
                bumpStat('statProgress', -1);
                bumpStat('statCompleted', 1);
            } else {
                if (this.tagName === 'INPUT') this.checked = false;
                else {
                    this.classList.remove('done');
                    this.innerHTML = '';
                }
                if (titleEl) titleEl.classList.remove('task-done');
                if (statusBadge) {
                    statusBadge.className = 'status-badge status-pending';
                    statusBadge.textContent = 'Pending';
                }
                bumpStat('statCompleted', -1);
                bumpStat('statPending', 1);
            }
            
            // Visual feedback animation
            this.style.transform = 'scale(0.9)';
            setTimeout(() => { this.style.transform = 'scale(1)'; }, 150);
            
            // 🔄 Sync with server in background
            fetch('/tasks/ajax/' + taskId + '/toggle/', {
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
                
                // ✅ REORDER TASKS AFTER SUCCESSFUL TOGGLE
                reorderTasks();
                
                console.log('Task toggled successfully');
            })
            .catch(err => {
                console.error('Toggle error:', err);
                
                // Revert UI if server failed
                if (willBeCompleted) {
                    if (this.tagName === 'INPUT') this.checked = false;
                    else {
                        this.classList.remove('done');
                        this.innerHTML = '';
                    }
                    if (titleEl) titleEl.classList.remove('task-done');
                    if (statusBadge) {
                        statusBadge.className = 'status-badge status-pending';
                        statusBadge.textContent = 'Pending';
                    }
                    bumpStat('statCompleted', -1);
                    bumpStat('statPending', 1);
                } else {
                    if (this.tagName === 'INPUT') this.checked = true;
                    else {
                        this.classList.add('done');
                        this.innerHTML = '<i class="bi bi-check"></i>';
                    }
                    if (titleEl) titleEl.classList.add('task-done');
                    if (statusBadge) {
                        statusBadge.className = 'status-badge status-completed';
                        statusBadge.textContent = 'Completed';
                    }
                    bumpStat('statPending', -1);
                    bumpStat('statCompleted', 1);
                }
                
                showToast('Failed to update task. Please try again.', 'error');
            });
        });
    });
}

/* ---------- Helper: Reorder Tasks (Pending Top, Completed Bottom) ---------- */
function reorderTasks() {
    const taskTableBody = document.querySelector('.task-table-body');
    if (!taskTableBody) return;
    
    const tasks = Array.from(taskTableBody.querySelectorAll('.task-row-item'));
    const pendingTasks = tasks.filter(task => !task.querySelector('.task-check.done'));
    const completedTasks = tasks.filter(task => task.querySelector('.task-check.done'));
    
    // Clear and reorder
    taskTableBody.innerHTML = '';
    pendingTasks.forEach(task => taskTableBody.appendChild(task));
    
    // Add visual separator if there are both pending and completed tasks
    if (completedTasks.length > 0 && pendingTasks.length > 0) {
        const separator = document.createElement('div');
        separator.className = 'task-separator';
        separator.innerHTML = '<span>Completed</span>';
        separator.style.cssText = `
            grid-column: 1 / -1;
            padding: 12px 16px;
            text-align: center;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            border-top: 1px solid var(--border-subtle);
            background: rgba(99, 201, 137, 0.05);
        `;
        taskTableBody.appendChild(separator);
    }
    
    completedTasks.forEach(task => taskTableBody.appendChild(task));
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
    const container = document.querySelector('.messages-wrap') || createMessageContainer();
    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.textContent = message;
    toast.style.cssText = 'position: fixed; bottom: 30px; right: 30px; z-index: 9999; min-width: 250px; animation: slideIn 0.3s ease;';
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function createMessageContainer() {
    const container = document.createElement('div');
    container.className = 'messages-wrap';
    container.style.cssText = 'position: fixed; bottom: 0; right: 0; z-index: 9999;';
    document.body.appendChild(container);
    return container;
}

/* ---------- 4. Delete Modal Handler ---------- */
function initDeleteModal() {
    const deleteModalEl = document.getElementById('deleteModal');
    if (!deleteModalEl) return;
    
    const deleteModal = new bootstrap.Modal(deleteModalEl);
    const deleteModalText = document.getElementById('deleteModalText');
    const deleteModalForm = document.getElementById('deleteModalForm');
    
    if (!deleteModalText || !deleteModalForm) return;
    
    // Bind to all delete buttons
    document.querySelectorAll('[data-delete-url]').forEach(function(trigger) {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const url = this.getAttribute('data-delete-url');
            const name = this.getAttribute('data-delete-name') || 'this task';
            
            if (!url) return;
            
            deleteModalText.textContent = 'Are you sure you want to delete "' + name + '"? This action cannot be undone.';
            deleteModalForm.setAttribute('action', url);
            
            // Close any open dropdown
            const dropdown = bootstrap.Dropdown.getInstance(this.closest('.dropdown'));
            if (dropdown) dropdown.hide();
            
            deleteModal.show();
        });
    });
}

/* ---------- 5. Fix Dropdown Clipping on Bottom Rows ---------- */
function fixDropdownClipping() {
    document.querySelectorAll('.dropdown').forEach(function(dropdown) {
        dropdown.addEventListener('show.bs.dropdown', function(e) {
            const menu = dropdown.querySelector('.dropdown-menu');
            const toggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
            
            if (!menu || !toggle) return;
            
            const dropdownRect = toggle.getBoundingClientRect();
            const menuHeight = 120;
            const viewportHeight = window.innerHeight;
            const spaceBelow = viewportHeight - dropdownRect.bottom;
            
            if (spaceBelow < menuHeight) {
                menu.classList.add('dropdown-flip-up');
                menu.style.position = 'fixed';
                menu.style.top = 'auto';
                menu.style.bottom = (viewportHeight - dropdownRect.top + 8) + 'px';
                menu.style.left = dropdownRect.left + 'px';
                menu.style.right = 'auto';
                menu.style.margin = '0';
                menu.style.zIndex = '9999';
            } else {
                menu.classList.remove('dropdown-flip-up');
                menu.style.position = 'absolute';
                menu.style.top = '100%';
                menu.style.bottom = 'auto';
                menu.style.left = 'auto';
                menu.style.right = '0';
                menu.style.marginTop = '8px';
            }
        });
        
        dropdown.addEventListener('hidden.bs.dropdown', function(e) {
            const menu = dropdown.querySelector('.dropdown-menu');
            if (menu) {
                menu.style.position = '';
                menu.style.top = '';
                menu.style.bottom = '';
                menu.style.left = '';
                menu.style.right = '';
                menu.style.margin = '';
                menu.classList.remove('dropdown-flip-up');
            }
        });
    });
}

/* ---------- 6. Custom Filter Dropdowns ---------- */
function initCustomDropdowns() {
    document.querySelectorAll('.custom-select').forEach(select => {
        const trigger = select.querySelector('.custom-select__trigger');
        const options = select.querySelectorAll('.custom-option');
        const hiddenInput = select.querySelector('input[type="hidden"]');
        const triggerText = trigger.querySelector('span');
        
        // Mark initial selected option based on Django template value
        const currentValue = hiddenInput.value;
        options.forEach(opt => {
            if (opt.getAttribute('data-value') === currentValue) {
                opt.classList.add('selected');
            }
        });

        // Toggle dropdown
        trigger.addEventListener('click', function(e) {
            e.stopPropagation();
            document.querySelectorAll('.custom-select.open').forEach(openSelect => {
                if (openSelect !== select) openSelect.classList.remove('open');
            });
            select.classList.toggle('open');
        });
        
        // Select option
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
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.custom-select')) {
            document.querySelectorAll('.custom-select.open').forEach(select => {
                select.classList.remove('open');
            });
        }
    });
}