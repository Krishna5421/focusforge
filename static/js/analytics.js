document.addEventListener('DOMContentLoaded', function () {

    fetch('/api/analytics/task-completion/')
        .then(function (res) { return res.json(); })
        .then(function (data) {
            new Chart(document.getElementById('taskTrendChart'), {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Tasks completed',
                        data: data.data,
                        borderColor: '#2dd4bf',
                        backgroundColor: 'rgba(45, 212, 191, 0.1)',
                        fill: true,
                        tension: 0.3,
                    }]
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#8b93a7', font: { size: 11 } }, grid: { display: false } },
                        y: { ticks: { color: '#8b93a7', font: { size: 11 } }, grid: { color: 'rgba(148,163,184,0.08)' } }
                    },
                    maintainAspectRatio: false,
                }
            });
        });

    fetch('/api/analytics/habit-consistency/')
        .then(function (res) { return res.json(); })
        .then(function (data) {
            new Chart(document.getElementById('habitConsistencyChart'), {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Completion %',
                        data: data.data,
                        backgroundColor: '#3b82f6',
                        borderRadius: 6,
                        maxBarThickness: 32,
                    }]
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#8b93a7', font: { size: 11 } }, grid: { display: false } },
                        y: { ticks: { color: '#8b93a7', font: { size: 11 } }, grid: { color: 'rgba(148,163,184,0.08)' }, max: 100 }
                    },
                    maintainAspectRatio: false,
                }
            });
        });

    fetch('/api/analytics/study-breakdown/')
        .then(function (res) { return res.json(); })
        .then(function (data) {
            new Chart(document.getElementById('studyBreakdownChart'), {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.data,
                        backgroundColor: ['#2dd4bf', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899'],
                        borderWidth: 0,
                    }]
                },
                options: {
                    plugins: { legend: { position: 'bottom', labels: { color: '#8b93a7', font: { size: 11 }, boxWidth: 10, padding: 12 } } },
                    maintainAspectRatio: false,
                    cutout: '65%',
                }
            });
        });

    fetch('/api/analytics/focus-trend/')
        .then(function (res) { return res.json(); })
        .then(function (data) {
            new Chart(document.getElementById('focusTrendChart'), {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Focus minutes',
                        data: data.data,
                        borderColor: '#fb923c',
                        backgroundColor: 'rgba(251, 146, 60, 0.1)',
                        fill: true,
                        tension: 0.3,
                    }]
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#8b93a7', font: { size: 11 } }, grid: { display: false } },
                        y: { ticks: { color: '#8b93a7', font: { size: 11 } }, grid: { color: 'rgba(148,163,184,0.08)' } }
                    },
                    maintainAspectRatio: false,
                }
            });
        });

    fetch('/api/analytics/goal-progress/')
        .then(function (res) { return res.json(); })
        .then(function (data) {
            new Chart(document.getElementById('goalProgressChart'), {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Completion %',
                        data: data.data,
                        backgroundColor: '#8b5cf6',
                        borderRadius: 6,
                        maxBarThickness: 32,
                    }]
                },
                options: {
                    indexAxis: 'y',
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#8b93a7', font: { size: 11 } }, grid: { color: 'rgba(148,163,184,0.08)' }, max: 100 },
                        y: { ticks: { color: '#8b93a7', font: { size: 11 } }, grid: { display: false } }
                    },
                    maintainAspectRatio: false,
                }
            });
        });

});