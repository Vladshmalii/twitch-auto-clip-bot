let dailyTrendsChart;
let triggerEffectivenessChart;
let correlationChart;
let hourlyChart;

async function fetchData(endpoint) {
    const response = await fetch(endpoint);
    return await response.json();
}

function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

async function updateOverview() {
    const data = await fetchData('/api/stats/overview');

    document.getElementById('totalClips').textContent = data.total_clips;
    document.getElementById('successfulClips').textContent = data.successful_clips;
    document.getElementById('successRate').textContent = `${data.success_rate}%`;
    document.getElementById('totalViews').textContent = data.total_views.toLocaleString();
    document.getElementById('avgScore').textContent = data.avg_score;

    const tbody = document.getElementById('recentClipsBody');
    tbody.innerHTML = '';

    if (data.recent_clips.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">No clips yet</td></tr>';
        return;
    }

    data.recent_clips.forEach(clip => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${clip.id}</td>
            <td><strong>${clip.score}</strong></td>
            <td>${clip.views}</td>
            <td>${formatTimestamp(clip.created_at)}</td>
            <td><a href="${clip.url}" target="_blank" class="clip-link">Watch</a></td>
        `;
        tbody.appendChild(row);
    });
}

async function updateDailyTrends() {
    const data = await fetchData('/api/stats/daily-trends');

    const ctx = document.getElementById('dailyTrendsChart').getContext('2d');

    if (dailyTrendsChart) {
        dailyTrendsChart.destroy();
    }

    dailyTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.date),
            datasets: [
                {
                    label: 'Total Clips',
                    data: data.map(d => d.total_clips),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Successful Clips',
                    data: data.map(d => d.successful_clips),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

async function updateTriggerEffectiveness() {
    const data = await fetchData('/api/stats/trigger-effectiveness');

    const ctx = document.getElementById('triggerEffectivenessChart').getContext('2d');

    if (triggerEffectivenessChart) {
        triggerEffectivenessChart.destroy();
    }

    triggerEffectivenessChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.trigger_type),
            datasets: [
                {
                    label: 'Avg Views',
                    data: data.map(d => d.avg_views),
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(245, 158, 11, 0.8)',
                        'rgba(239, 68, 68, 0.8)'
                    ],
                    borderWidth: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

async function updateCorrelation() {
    const data = await fetchData('/api/stats/signal-correlation');

    const ctx = document.getElementById('correlationChart').getContext('2d');

    if (correlationChart) {
        correlationChart.destroy();
    }

    correlationChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Chat', 'Audio', 'Video'],
            datasets: [{
                label: 'Correlation with Views',
                data: [
                    data.chat_correlation,
                    data.audio_correlation,
                    data.video_correlation
                ],
                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                borderColor: '#667eea',
                borderWidth: 2,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#667eea'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 1,
                    ticks: {
                        stepSize: 0.2
                    }
                }
            }
        }
    });
}

async function updateHourlyDistribution() {
    const data = await fetchData('/api/stats/hourly-distribution');

    const ctx = document.getElementById('hourlyChart').getContext('2d');

    if (hourlyChart) {
        hourlyChart.destroy();
    }

    hourlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => `${d.hour}:00`),
            datasets: [{
                label: 'Clips per Hour',
                data: data.map(d => d.count),
                backgroundColor: 'rgba(118, 75, 162, 0.8)',
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

async function updateRecentSignals() {
    const data = await fetchData('/api/stats/recent-signals');

    const tbody = document.getElementById('signalsBody');
    tbody.innerHTML = '';

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No signals yet</td></tr>';
        return;
    }

    data.slice(0, 20).forEach(signal => {
        const row = document.createElement('tr');
        const badgeClass = signal.clip_created ? 'success' : 'failed';
        const badgeText = signal.clip_created ? 'YES' : 'NO';

        row.innerHTML = `
            <td>${formatTimestamp(signal.timestamp)}</td>
            <td>${signal.chat_velocity}</td>
            <td>${signal.audio_rms}</td>
            <td>${signal.motion_score}</td>
            <td><strong>${signal.final_score}</strong></td>
            <td><span class="clip-badge ${badgeClass}">${badgeText}</span></td>
        `;
        tbody.appendChild(row);
    });
}

async function updateAll() {
    await updateOverview();
    await updateDailyTrends();
    await updateTriggerEffectiveness();
    await updateCorrelation();
    await updateHourlyDistribution();
    await updateRecentSignals();
}

updateAll();

setInterval(updateAll, 30000);