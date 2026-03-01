// Activity feed — fetches from /api/activities on first tab activation, then
// groups by day and builds the card DOM.  Subsequent tab switches are instant.

let feedLoaded = false;

async function loadAndRenderFeed() {
    if (feedLoaded) return;

    const rail = document.getElementById('feedRailNav');
    const stream = document.getElementById('feedStream');
    stream.innerHTML = '<div class="summary-label">Loading…</div>';

    try {
        const res = await fetch('/api/activities');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const activities = await res.json();
        feedLoaded = true;
        renderFeed(activities, rail, stream);
    } catch (err) {
        stream.innerHTML = `<div class="summary-label feed-error">Failed to load activities: ${err.message}</div>`;
    }
}

function formatDayLabel(dayDate, now) {
    const dayStart = new Date(dayDate.getFullYear(), dayDate.getMonth(), dayDate.getDate());
    const nowStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const diff = Math.round((nowStart - dayStart) / 86400000);
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Yesterday';
    return dayDate.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
}

function groupByDay(items) {
    const groups = new Map();
    items.forEach((activity) => {
        const dt = activity.date_iso ? new Date(activity.date_iso) : null;
        if (dt && !Number.isNaN(dt.valueOf())) {
            const key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
            if (!groups.has(key)) groups.set(key, { dt, items: [] });
            groups.get(key).items.push(activity);
        } else {
            if (!groups.has('unknown')) groups.set('unknown', { dt: null, items: [] });
            groups.get('unknown').items.push(activity);
        }
    });
    return [...groups.values()];
}

function renderFeed(items, rail, stream) {
    rail.innerHTML = '';
    stream.innerHTML = '';

    const groups = groupByDay(items);
    const now = new Date();

    if (!groups.length) {
        stream.innerHTML = '<div class="summary-label">No activities yet.</div>';
        return;
    }

    groups.forEach((group) => {
        const section = document.createElement('section');
        section.className = 'feed-day-group';

        const label = group.dt ? formatDayLabel(group.dt, now) : 'Unknown Date';

        const railBtn = document.createElement('button');
        railBtn.type = 'button';
        railBtn.className = 'feed-rail-link';
        railBtn.textContent = label;
        railBtn.addEventListener('click', () => section.scrollIntoView({ behavior: 'smooth', block: 'start' }));
        rail.appendChild(railBtn);

        const dayTitle = document.createElement('h3');
        dayTitle.className = 'feed-day-title';
        dayTitle.textContent = label;
        section.appendChild(dayTitle);

        const cardFlow = document.createElement('div');
        cardFlow.className = 'feed-card-flow';

        group.items.forEach((activity) => {
            const card = document.createElement('article');
            card.className = `feed-card feed-type-${activity.type_key || 'activity'}`;
            if (activity.color) card.style.setProperty('--card-accent', activity.color);

            const cardRail = document.createElement('div');
            cardRail.className = 'feed-card-rail';
            const iconPath = activity.skill
                ? `/static/skills_64/${activity.skill.toLowerCase()}.png`
                : `/static/icons_64/${activity.type_key || 'activity'}.png`;
            cardRail.style.setProperty('--card-icon-url', `url("${iconPath}")`);

            const body = document.createElement('div');
            body.className = 'feed-card-body';

            const title = document.createElement('h4');
            title.className = 'feed-card-title';
            title.textContent = activity.details ?? activity.text;

            const date = document.createElement('div');
            date.className = 'feed-card-date';
            if (activity.date_iso) {
                const dt = new Date(activity.date_iso);
                date.textContent = Number.isNaN(dt.valueOf())
                    ? activity.date
                    : dt.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
            } else {
                date.textContent = activity.date || '';
            }

            body.append(title, date);
            card.append(cardRail, body);
            cardFlow.appendChild(card);
        });

        section.appendChild(cardFlow);
        stream.appendChild(section);
    });
}