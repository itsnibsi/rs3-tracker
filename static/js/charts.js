// Chart utilities, total XP sidebar chart, and skill history modal.
// Depends on Chart.js being loaded as a global before this script runs.

const numberFmt = new Intl.NumberFormat();
const cssVars = getComputedStyle(document.documentElement);
const chartAccent = cssVars.getPropertyValue('--accent').trim() || '#8da0b6';
const chartMuted = cssVars.getPropertyValue('--text-muted').trim() || '#9aa1ab';
const chartGrid = cssVars.getPropertyValue('--border').trim() || '#31353c';

function hexToRgba(hex, alpha) {
    if (!hex || !hex.startsWith('#')) return `rgba(141,160,182,${alpha})`;
    const full = hex.length === 4
        ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
        : hex;
    const n = parseInt(full.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}

function formatXp(value) {
    return value == null || Number.isNaN(Number(value))
        ? '-'
        : numberFmt.format(Math.round(Number(value)));
}

function previousNonNull(series, index) {
    for (let i = index - 1; i >= 0; i--) {
        if (series[i] != null) return Number(series[i]);
    }
    return null;
}

function formatDelta(current, previous) {
    if (current == null || previous == null) return 'n/a';
    const d = Number(current) - Number(previous);
    return `${d > 0 ? '+' : ''}${numberFmt.format(Math.round(d))}`;
}

// ---------------------------------------------------------------------------
// Total XP sidebar chart (30 days)
// ---------------------------------------------------------------------------

function initTotalXpChart(timestamps, xpHistory) {
    new Chart(document.getElementById('totalXpChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [{
                label: 'Total XP',
                data: xpHistory,
                borderColor: chartAccent,
                backgroundColor: hexToRgba(chartAccent, 0.15),
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `Total XP: ${formatXp(ctx.parsed.y)}`,
                        afterLabel: (ctx) => `Delta: ${formatDelta(ctx.parsed.y, previousNonNull(ctx.dataset.data, ctx.dataIndex))}`,
                    },
                },
            },
            scales: {
                x: {
                    type: 'time',
                    time: { tooltipFormat: 'PPp' },
                    ticks: { color: chartMuted },
                    grid: { color: chartGrid },
                },
                y: {
                    ticks: { color: chartMuted, callback: (val) => val.toLocaleString() },
                    grid: { color: chartGrid },
                },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// Skill history modal
// ---------------------------------------------------------------------------

function initSkillModal() {
    const modal = document.getElementById('skillModal');
    const modalContent = modal.querySelector('.modal-content');
    const noGains = document.getElementById('skillNoGainsMessage');
    const gainSummary = document.getElementById('skillGainSummary');
    const chartEl = document.getElementById('skillChart');
    let currentSkill = '';
    let currentSkillColor = chartAccent;
    let chartInstance = null;

    const PERIOD_LABELS = { day: 'past day', week: 'past week', month: 'current month', year: 'past year' };

    function rangeGain(series) {
        const vals = (series || []).filter(v => v != null).map(Number);
        return vals.length ? Math.max(0, vals[vals.length - 1] - vals[0]) : null;
    }

    function openModal(skill, color) {
        currentSkill = skill;
        currentSkillColor = color || chartAccent;
        modalContent.style.setProperty('--modal-accent', currentSkillColor);
        document.getElementById('modalSkillTitle').textContent = `${skill} History`;
        modal.classList.add('active');
        document.querySelectorAll('#skillModal .chart-controls .tf-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('#skillModal .chart-controls .tf-btn[data-period="day"]').classList.add('active');
        loadSkillData(skill, 'day');
    }

    // Open on skill card click
    document.querySelectorAll('.skill-card').forEach(card => {
        card.addEventListener('click', () => {
            const color = getComputedStyle(card).getPropertyValue('--skill-color').trim();
            openModal(card.dataset.skill, color);
        });
    });

    // Close — button, overlay click, Escape
    document.getElementById('closeModal').addEventListener('click', () => modal.classList.remove('active'));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('active'); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') modal.classList.remove('active'); });

    // Period buttons
    document.querySelectorAll('#skillModal .chart-controls .tf-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('#skillModal .chart-controls .tf-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            loadSkillData(currentSkill, e.target.dataset.period);
        });
    });

    async function loadSkillData(skill, period) {
        if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
        noGains.style.display = 'none';
        gainSummary.textContent = 'Loading…';

        try {
            const res = await fetch(`/api/chart/${encodeURIComponent(skill)}/${period}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            const label = PERIOD_LABELS[period] ?? 'selected range';

            if (!data.has_gains) {
                noGains.style.display = 'block';
                gainSummary.textContent = `Gained in ${label}: n/a`;
                return;
            }

            noGains.style.display = 'none';
            gainSummary.textContent = `Gained in ${label}: ${formatXp(rangeGain(data.totals))} XP`;

            const timeUnit = period === 'day' ? 'hour' : 'day';
            const tooltipFmt = period === 'day' ? 'PPp' : 'PP';
            const pointRadius = data.labels.length > 180 ? 0 : data.labels.length > 60 ? 1.5 : 3;

            chartInstance = new Chart(chartEl.getContext('2d'), {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: `${skill} XP`,
                        data: data.totals,
                        borderColor: currentSkillColor,
                        backgroundColor: hexToRgba(currentSkillColor, 0.15),
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius,
                    }],
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.dataset.label}: ${formatXp(ctx.parsed.y)}`,
                                afterLabel: (ctx) => `Delta: ${formatDelta(ctx.parsed.y, previousNonNull(ctx.dataset.data, ctx.dataIndex))}`,
                            },
                        },
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: timeUnit,
                                tooltipFormat: tooltipFmt,
                                displayFormats: { hour: 'HH:mm', day: 'MMM d' },
                            },
                            ticks: { color: chartMuted },
                            grid: { color: chartGrid },
                        },
                        y: {
                            ticks: { color: chartMuted, callback: (val) => val.toLocaleString() },
                            grid: { color: chartGrid },
                        },
                    },
                },
            });
        } catch (err) {
            gainSummary.textContent = `Failed to load chart: ${err.message}`;
        }
    }
}