
const urlInput = document.getElementById('urlInput');
const addBtn = document.getElementById('addBtn');
const websiteList = document.getElementById('websiteList');

// Connect to WebSocket
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws`;
const ws = new WebSocket(wsUrl);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    renderWebsites(data);
};

ws.onopen = () => {
    console.log('Connected to WebSocket');
};

ws.onclose = () => {
    console.log('Disconnected from WebSocket');
    // Optional: Implement reconnect logic here
};

addBtn.addEventListener('click', addWebsite);
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addWebsite();
});

async function addWebsite() {
    const url = urlInput.value.trim();
    if (!url) return;

    if (!isValidUrl(url)) {
        alert('Please enter a valid URL (including http:// or https://)');
        return;
    }

    try {
        const response = await fetch('/api/websites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        if (response.ok) {
            urlInput.value = '';
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to add website');
        }
    } catch (e) {
        console.error(e);
        alert('Error adding website');
    }
}

async function removeWebsite(url) {
    if (!confirm(`Are you sure you want to stop monitoring ${url}?`)) return;

    try {
        const response = await fetch('/api/websites', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        if (!response.ok) {
            alert('Failed to remove website');
        }
    } catch (e) {
        console.error(e);
        alert('Error removing website');
    }
}

function renderWebsites(websites) {
    if (websites.length === 0) {
        websiteList.innerHTML = '<div class="empty-state">No websites monitored yet. Add one above!</div>';
        return;
    }

    websiteList.innerHTML = websites.map(site => {
        let statusClass = 'status-check';
        let statusText = site.status;

        if (site.is_up) {
            statusClass = 'status-up';
        } else if (site.status !== "UNKNOWN") {
            statusClass = 'status-down';
        }

        const lastChecked = site.last_checked ? new Date(site.last_checked).toLocaleTimeString() : '-';

        return `
            <div class="website-item">
                <div class="website-url" title="${site.url}">${site.url}</div>
                <div><span class="status-badge ${statusClass}">${statusText}</span></div>
                <div class="response-time">${site.response_time > 0 ? site.response_time + ' ms' : '-'}</div>
                <div class="last-checked">${lastChecked}</div>
                <div>
                    <button class="delete-btn" onclick="removeWebsite('${site.url}')">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}
