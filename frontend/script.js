
const urlInput = document.getElementById('urlInput');
const addBtn = document.getElementById('addBtn');
const websiteList = document.getElementById('websiteList');
const searchInput = document.getElementById('searchInput');
const exportJsonBtn = document.getElementById('exportJsonBtn');
const exportCsvBtn = document.getElementById('exportCsvBtn');

let allWebsites = [];
let searchTerm = '';

// Connect to WebSocket
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws`;
const ws = new WebSocket(wsUrl);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    allWebsites = data;
    renderWebsites(filterWebsites());
    updateStatistics();
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

searchInput.addEventListener('input', (e) => {
    searchTerm = e.target.value.toLowerCase();
    renderWebsites(filterWebsites());
});

exportJsonBtn.addEventListener('click', () => {
    window.location.href = '/api/export/json';
});

exportCsvBtn.addEventListener('click', () => {
    window.location.href = '/api/export/csv';
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

function filterWebsites() {
    if (!searchTerm) return allWebsites;
    
    return allWebsites.filter(site => 
        site.url.toLowerCase().includes(searchTerm) ||
        site.status.toLowerCase().includes(searchTerm)
    );
}

async function updateStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const stats = await response.json();
        
        document.getElementById('totalWebsites').textContent = stats.total_websites;
        document.getElementById('websitesUp').textContent = stats.websites_up;
        document.getElementById('websitesDown').textContent = stats.websites_down;
        document.getElementById('avgUptime').textContent = stats.average_uptime.toFixed(1) + '%';
        document.getElementById('avgResponseTime').textContent = Math.round(stats.average_response_time) + 'ms';
    } catch (e) {
        console.error('Error fetching statistics:', e);
    }
}

function showHistory(url, history) {
    const modal = document.getElementById('historyModal');
    const content = document.getElementById('historyContent');
    
    if (!history || history.length === 0) {
        content.innerHTML = '<div class="empty-state">No status changes recorded yet.</div>';
    } else {
        content.innerHTML = `
            <h3 style="margin-bottom: 1rem; color: var(--text-primary);">${url}</h3>
            <div class="history-list">
                ${history.map(event => `
                    <div class="history-item">
                        <div class="history-time">${new Date(event.timestamp).toLocaleString()}</div>
                        <div class="history-change">
                            <span class="old-status">${event.old_status}</span>
                            <span>→</span>
                            <span class="new-status">${event.new_status}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    modal.style.display = 'flex';
}

function closeHistoryModal() {
    document.getElementById('historyModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = (event) => {
    const modal = document.getElementById('historyModal');
    if (event.target === modal) {
        closeHistoryModal();
    }
};

function renderWebsites(websites) {
    if (websites.length === 0) {
        if (searchTerm) {
            websiteList.innerHTML = '<div class="empty-state">No websites found matching your search.</div>';
        } else {
            websiteList.innerHTML = '<div class="empty-state">No websites monitored yet. Add one above!</div>';
        }
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
        const uptimeClass = site.uptime_percentage >= 95 ? 'uptime-good' : 
                           site.uptime_percentage >= 80 ? 'uptime-fair' : 'uptime-poor';

        return `
            <div class="website-item">
                <div class="website-url" title="${site.url}">${site.url}</div>
                <div><span class="status-badge ${statusClass}">${statusText}</span></div>
                <div class="response-time">
                    ${site.response_time > 0 ? site.response_time + ' ms' : '-'}
                    ${site.avg_response_time > 0 ? '<br><small>(avg: ' + site.avg_response_time + ' ms)</small>' : ''}
                </div>
                <div class="uptime ${uptimeClass}" title="${site.total_checks} checks">
                    ${site.uptime_percentage.toFixed(1)}%
                </div>
                <div class="last-checked">${lastChecked}</div>
                <div class="action-buttons">
                    <button class="history-btn" onclick='showHistory(${JSON.stringify(site.url)}, ${JSON.stringify(site.status_history)})' title="View History">
                        📊
                    </button>
                    <button class="delete-btn" onclick="removeWebsite('${site.url}')" title="Remove">
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
