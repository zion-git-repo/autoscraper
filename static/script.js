// State
let eventSource = null;
let isRunning = false;
let allResults = [];
let currentPage = 1;
const resultsPerPage = 10;

// DOM Elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const downloadBtn = document.getElementById('downloadBtn');
const startRangeInput = document.getElementById('startRange');
const endRangeInput = document.getElementById('endRange');
const fieldCheckboxes = document.querySelectorAll('input[name="field"]');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const currentAction = document.getElementById('currentAction');
const statusBadge = document.getElementById('statusBadge');
const logContainer = document.getElementById('logContainer');
const resultsBody = document.getElementById('resultsBody');
const resultCount = document.getElementById('resultCount');
const prevPageBtn = document.getElementById('prevPage');
const nextPageBtn = document.getElementById('nextPage');
const paginationInfo = document.getElementById('paginationInfo');
const filterNoWebsiteCheckbox = document.getElementById('filterNoWebsite');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    connectSSE();
    checkStatus();

    // Event listeners
    startBtn.addEventListener('click', startScraping);
    stopBtn.addEventListener('click', stopScraping);
    downloadBtn.addEventListener('click', downloadCSV);
    prevPageBtn.addEventListener('click', () => changePage(-1));
    nextPageBtn.addEventListener('click', () => changePage(1));
    filterNoWebsiteCheckbox.addEventListener('change', () => {
        currentPage = 1;
        displayCurrentPage();
    });
});

// Connect to Server-Sent Events
function connectSSE() {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource('/api/stream');

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleSSEMessage(data);
    };

    eventSource.onerror = (error) => {
        console.error('SSE Error:', error);
        // Auto-reconnect
        setTimeout(connectSSE, 3000);
    };
}

// Handle SSE messages
function handleSSEMessage(data) {
    switch (data.type) {
        case 'connected':
            console.log('Connected to SSE stream');
            break;

        case 'log':
            addLogEntry(data.message, data.level);
            break;

        case 'progress':
            updateProgress(data.current, data.total, data.status);
            break;

        case 'complete':
            handleComplete(data.total_results);
            break;
    }
}

// Start scraping
async function startScraping() {
    // Get selected fields
    const selectedFields = Array.from(fieldCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

    if (selectedFields.length === 0) {
        alert('Please select at least one field to extract');
        return;
    }

    // Get range values
    const startRange = parseInt(startRangeInput.value) || 1;
    const endRange = parseInt(endRangeInput.value) || 10;

    // Validate range
    if (startRange < 1) {
        alert('Start range must be at least 1');
        return;
    }
    if (endRange < startRange) {
        alert('End range must be greater than or equal to start range');
        return;
    }

    // Clear logs and results
    logContainer.innerHTML = '';
    allResults = [];
    currentPage = 1;

    // Reset progress
    updateProgress(0, 0, 'Starting...');
    updateStatus('running');

    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                start: startRange,
                end: endRange,
                fields: selectedFields
            })
        });

        if (response.ok) {
            isRunning = true;
            updateButtons();
            addLogEntry('Scraping started...', 'info');
        } else {
            const error = await response.json();
            alert('Error: ' + error.error);
            updateStatus('idle');
        }
    } catch (error) {
        console.error('Error starting scraper:', error);
        alert('Failed to start scraper');
        updateStatus('idle');
    }
}

// Stop scraping
async function stopScraping() {
    try {
        const response = await fetch('/api/stop', {
            method: 'POST'
        });

        if (response.ok) {
            addLogEntry('Stop requested...', 'warning');
        }
    } catch (error) {
        console.error('Error stopping scraper:', error);
    }
}

// Download CSV
function downloadCSV() {
    window.location.href = '/api/download';
}

// Update progress bar
function updateProgress(current, total, status) {
    const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

    progressBar.style.width = percentage + '%';
    progressText.textContent = `${current}/${total} (${percentage}%)`;
    currentAction.textContent = status || 'Processing...';

    // Update results periodically
    if (current > 0 && current % 5 === 0) {
        fetchResults();
    }
}

// Update status badge
function updateStatus(status) {
    statusBadge.className = 'status-badge ' + status;
    statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

// Add log entry
function addLogEntry(message, level = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${level}`;

    const timestamp = new Date().toLocaleTimeString();
    const icon = getLogIcon(level);
    entry.textContent = `[${timestamp}] ${icon} ${message}`;

    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Get icon for log level
function getLogIcon(level) {
    const icons = {
        'info': 'ℹ️',
        'success': '✓',
        'warning': '⚠',
        'error': '✗'
    };
    return icons[level] || '';
}

// Handle completion
function handleComplete(totalResults) {
    isRunning = false;
    updateButtons();
    updateStatus('completed');
    currentAction.textContent = `Completed! ${totalResults} clinics scraped`;

    // Fetch final results
    fetchResults();

    // Enable download button
    downloadBtn.disabled = false;

    addLogEntry(`Scraping completed successfully! ${totalResults} clinics collected.`, 'success');
}

// Update button states
function updateButtons() {
    startBtn.disabled = isRunning;
    stopBtn.disabled = !isRunning;
}

// Check scraper status
async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        isRunning = data.is_running;
        updateButtons();

        if (data.results_count > 0) {
            downloadBtn.disabled = false;
            fetchResults();
        }
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

// Fetch and display results
async function fetchResults() {
    try {
        const response = await fetch('/api/results?all=true');
        const data = await response.json();

        allResults = data.results || [];
        resultCount.textContent = `(${data.total} clinics)`;

        // Reset to page 1 and display
        currentPage = 1;
        displayCurrentPage();

    } catch (error) {
        console.error('Error fetching results:', error);
    }
}

// Get filtered results based on checkbox state
function getFilteredResults() {
    if (!filterNoWebsiteCheckbox.checked) {
        return allResults;
    }

    // Filter to show only clinics without website
    return allResults.filter(clinic => {
        return !clinic.website || clinic.website === 'N/A' || clinic.website.trim() === '';
    });
}

// Display current page of results
function displayCurrentPage() {
    const filteredResults = getFilteredResults();

    if (!allResults || allResults.length === 0) {
        resultsBody.innerHTML = '<tr><td colspan="5" class="empty-state">No results yet</td></tr>';
        updatePaginationControls();
        return;
    }

    if (filteredResults.length === 0) {
        resultsBody.innerHTML = '<tr><td colspan="5" class="empty-state">No clinics without websites found</td></tr>';
        updatePaginationControls();
        return;
    }

    // Calculate pagination based on filtered results
    const totalPages = Math.ceil(filteredResults.length / resultsPerPage);
    const startIdx = (currentPage - 1) * resultsPerPage;
    const endIdx = Math.min(startIdx + resultsPerPage, filteredResults.length);
    const pageResults = filteredResults.slice(startIdx, endIdx);

    // Display results for current page
    resultsBody.innerHTML = '';

    pageResults.forEach((clinic) => {
        const row = document.createElement('tr');

        row.innerHTML = `
            <td>${escapeHtml(clinic.name || 'N/A')}</td>
            <td>${escapeHtml(clinic.address || 'N/A')}</td>
            <td>${escapeHtml(clinic.phone || 'N/A')}</td>
            <td>${clinic.website && clinic.website !== 'N/A'
                ? `<a href="${escapeHtml(clinic.website)}" target="_blank">Link</a>`
                : 'N/A'}</td>
            <td><a href="${escapeHtml(clinic.url)}" target="_blank">View</a></td>
        `;

        resultsBody.appendChild(row);
    });

    updatePaginationControls();
}

// Update pagination controls
function updatePaginationControls() {
    const filteredResults = getFilteredResults();
    const totalPages = Math.ceil(filteredResults.length / resultsPerPage);

    prevPageBtn.disabled = currentPage <= 1;
    nextPageBtn.disabled = currentPage >= totalPages || totalPages === 0;

    if (totalPages > 0) {
        paginationInfo.textContent = `Page ${currentPage} of ${totalPages} (Showing ${(currentPage - 1) * resultsPerPage + 1}-${Math.min(currentPage * resultsPerPage, filteredResults.length)} of ${filteredResults.length})`;
    } else {
        paginationInfo.textContent = 'Page 1 of 1';
    }
}

// Change page
function changePage(delta) {
    const filteredResults = getFilteredResults();
    const totalPages = Math.ceil(filteredResults.length / resultsPerPage);
    const newPage = currentPage + delta;

    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        displayCurrentPage();
    }
}

// Legacy displayResults for compatibility
function displayResults(results) {
    allResults = results || [];
    currentPage = 1;
    displayCurrentPage();
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
