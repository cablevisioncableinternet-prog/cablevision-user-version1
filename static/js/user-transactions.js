// ==================== TAB ID HELPER ====================
function getTabId() {
    return sessionStorage.getItem('tab_id') || '';
}

// ==================== TOAST NOTIFICATION ====================
function showToast(message, type = 'info') {
    const LABELS = { success: 'Success', error: 'Error', info: 'Notice', loading: 'Please wait' };
    const ICONS = {
        success: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
        error:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
        info:    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
        loading: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" style="animation: toastSpin 1s linear infinite; display:block;"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`
    };

    let toast = document.querySelector('.custom-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'custom-toast';
        document.body.appendChild(toast);
        if (!document.getElementById('toast-keyframes')) {
            const s = document.createElement('style');
            s.id = 'toast-keyframes';
            s.textContent = `
                @keyframes toastSpin     { to { transform: rotate(360deg); } }
                @keyframes toastProgress { from { transform: scaleX(1); } to { transform: scaleX(0); } }
                @keyframes toastLoading  { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
            `;
            document.head.appendChild(s);
        }
    }

    toast.innerHTML = `
        <div class="custom-toast-body">
            <span class="custom-toast-icon">${ICONS[type] || ICONS.info}</span>
            <div class="custom-toast-text">
                <span class="custom-toast-title">${LABELS[type] || 'Notice'}</span>
                <span class="custom-toast-message">${message}</span>
            </div>
        </div>
        <div class="custom-toast-progress"><div class="custom-toast-progress-bar"></div></div>
    `;
    toast.className = `custom-toast ${type}`;
    void toast.offsetWidth;
    toast.classList.add('show');
    clearTimeout(toast._hideTimer);
    if (type !== 'loading') {
        toast._hideTimer = setTimeout(() => toast.classList.remove('show'), 3000);
    }
}

// ==================== ESCAPE HTML ====================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== FORMAT DATE TIME (12-HOUR) ====================
function formatDateTime12Hour(dateString) {
    if (!dateString) return '—';
    const date = new Date(dateString.replace(' ', 'T'));
    if (isNaN(date.getTime())) return dateString;
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true };
    return date.toLocaleString('en-US', options);
}

function formatPriceDisplay(priceValue) {
    if (!priceValue) return 'N/A';
    const cleanPrice = String(priceValue).replace(/[₱,]/g, '').replace(/\/month.*$/i, '').trim();
    const priceNum = parseFloat(cleanPrice);
    if (!isNaN(priceNum) && priceNum > 0) return `₱${priceNum.toLocaleString()}`;
    return 'N/A';
}

// ==================== GLOBAL STATE ====================
let allTransactions = [];
let filteredTransactions = [];
let currentPage = 1;
const rowsPerPage = 10;
const paginationContainer = document.getElementById('paginationControls');

// ==================== LOAD CURRENT PLAN (MINI CARD) ====================
async function loadCurrentPlan() {
    try {
        const username = sessionStorage.getItem('username');
        const tabId = getTabId();
        if (!username || !tabId) return;

        const response = await fetch(`/api/user/current-plan?username=${encodeURIComponent(username)}&tab_id=${tabId}`);
        const data = await response.json();
        if (data.error) return;

        document.getElementById('currentPlanName').textContent = data.plan || '--';
        document.getElementById('currentPlanSpeed').textContent = data.speed ? `${data.speed} Mbps` : '-- Mbps';
        document.getElementById('currentPlanPrice').textContent = formatPriceDisplay(data.price);
        document.getElementById('contractNumber').textContent = data.contract_number || '--';
    } catch (error) {
        console.error('Error loading current plan:', error);
    }
}

// ==================== FETCH TRANSACTIONS ====================
async function fetchTransactions() {
    const tbody = document.getElementById('transactionsBody');
    const table = document.getElementById('transactionsTable');
    const noDataEl = document.getElementById('noData');

    try {
        const tabId = getTabId();
        const response = await fetch(`/api/user/all-transactions?tab_id=${tabId}`);
        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            allTransactions = [];
        } else {
            allTransactions = Array.isArray(data) ? data : [];
        }

        filteredTransactions = [...allTransactions];
        currentPage = 1;
        renderCurrentPage();
    } catch (error) {
        console.error('Error fetching transactions:', error);
        showToast('Error loading transactions', 'error');
        if (table) table.style.display = 'none';
        if (noDataEl) noDataEl.style.display = 'block';
        if (tbody) tbody.innerHTML = '';
    }
}

// ==================== SEARCH & FILTER ====================
function applyFiltersAndPaginate() {
    const searchTerm = (document.getElementById('searchInput').value || '').toLowerCase().trim();
    const statusValue = document.getElementById('statusFilter').value;

    let filtered = [...allTransactions];

    if (searchTerm) {
        filtered = filtered.filter(t =>
            (t.id && String(t.id).toLowerCase().includes(searchTerm)) ||
            (t.full_name && t.full_name.toLowerCase().includes(searchTerm)) ||
            (t.type && t.type.toLowerCase().includes(searchTerm)) ||
            (t.description && t.description.toLowerCase().includes(searchTerm))
        );
    }

    if (statusValue !== 'all') {
        filtered = filtered.filter(t => t.status && t.status.toLowerCase() === statusValue.toLowerCase());
    }

    filteredTransactions = filtered;
    currentPage = 1;
    renderCurrentPage();
}

// ==================== RENDER TABLE (PAGE) ====================
function renderCurrentPage() {
    const totalItems = filteredTransactions.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / rowsPerPage));

    const countSpan = document.getElementById('transactionCount');
    if (countSpan) countSpan.textContent = totalItems;

    const table = document.getElementById('transactionsTable');
    const noDataEl = document.getElementById('noData');

    if (totalItems === 0) {
        if (table) table.style.display = 'none';
        if (noDataEl) noDataEl.style.display = 'block';
        if (paginationContainer) paginationContainer.style.display = 'none';
        return;
    }

    if (table) table.style.display = 'table';
    if (noDataEl) noDataEl.style.display = 'none';

    if (currentPage > totalPages) currentPage = totalPages;

    // Already sorted latest-first by the backend; keep that order stable.
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = startIndex + rowsPerPage;
    const pageData = filteredTransactions.slice(startIndex, endIndex);

    renderTransactionsTable(pageData);
    renderPaginationControls(totalPages, totalItems);
}

const TYPE_BADGE_CLASS = {
    'Change Plan': 'type-change-plan',
    'Termination': 'type-termination',
    'Reconnection': 'type-reconnection'
};

const TYPE_ICON = {
    'Change Plan': 'fa-exchange-alt',
    'Termination': 'fa-file-invoice',
    'Reconnection': 'fa-plug'
};

function renderTransactionsTable(data) {
    const tbody = document.getElementById('transactionsBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    data.forEach(t => {
        const statusClass = `status-${(t.status || 'pending').toLowerCase()}`;
        const typeClass = TYPE_BADGE_CLASS[t.type] || 'type-change-plan';
        const typeIcon = TYPE_ICON[t.type] || 'fa-file';

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><span class="request-id-cell">${escapeHtml(t.id || 'N/A')}</span></td>
            <td>${escapeHtml(t.full_name || 'N/A')}</td>
            <td><span class="type-badge ${typeClass}"><i class="fas ${typeIcon}"></i> ${escapeHtml(t.type || 'N/A')}</span></td>
            <td>${escapeHtml(t.description || 'N/A')}</td>
            <td><span class="status-badge ${statusClass}">${escapeHtml(t.status || 'Pending')}</span></td>
            <td>${formatDateTime12Hour(t.submitted_at)}</td>
            <td>${t.updated_at ? formatDateTime12Hour(t.updated_at) : '—'}</td>
            <td><button class="btn-view-transaction" data-id="${escapeHtml(t.id)}"><i class="fas fa-eye"></i> View</button></td>
        `;
        tbody.appendChild(row);
    });

    tbody.querySelectorAll('.btn-view-transaction').forEach(btn => {
        btn.addEventListener('click', () => openTransactionDetails(btn.dataset.id));
    });
}

// ==================== PAGINATION CONTROLS ====================
function renderPaginationControls(totalPages, totalItems) {
    if (!paginationContainer) return;
    if (totalItems === 0) {
        paginationContainer.style.display = 'none';
        return;
    }
    paginationContainer.style.display = 'flex';

    let html = `<button class="pagination-btn" id="firstPageBtn" ${currentPage === 1 ? 'disabled' : ''}><i class="fas fa-angle-double-left"></i></button>`;
    html += `<button class="pagination-btn" id="prevPageBtn" ${currentPage === 1 ? 'disabled' : ''}><i class="fas fa-chevron-left"></i> Prev</button>`;

    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

    if (startPage > 1) {
        html += `<button class="pagination-btn" data-page="1">1</button>`;
        if (startPage > 2) html += `<span class="pagination-ellipsis">...</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += `<span class="pagination-ellipsis">...</span>`;
        html += `<button class="pagination-btn" data-page="${totalPages}">${totalPages}</button>`;
    }

    html += `<button class="pagination-btn" id="nextPageBtn" ${currentPage === totalPages ? 'disabled' : ''}>Next <i class="fas fa-chevron-right"></i></button>`;
    html += `<button class="pagination-btn" id="lastPageBtn" ${currentPage === totalPages ? 'disabled' : ''}><i class="fas fa-angle-double-right"></i></button>`;
    html += `<div class="pagination-info"><i class="fas fa-database"></i> Showing ${((currentPage - 1) * rowsPerPage) + 1} - ${Math.min(currentPage * rowsPerPage, totalItems)} of ${totalItems} entries</div>`;

    paginationContainer.innerHTML = html;

    const goTo = (page) => { currentPage = page; renderCurrentPage(); };
    const firstBtn = document.getElementById('firstPageBtn');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    const lastBtn = document.getElementById('lastPageBtn');
    if (firstBtn) firstBtn.addEventListener('click', () => goTo(1));
    if (prevBtn) prevBtn.addEventListener('click', () => { if (currentPage > 1) goTo(currentPage - 1); });
    if (nextBtn) nextBtn.addEventListener('click', () => { if (currentPage < totalPages) goTo(currentPage + 1); });
    if (lastBtn) lastBtn.addEventListener('click', () => goTo(totalPages));
    paginationContainer.querySelectorAll('.pagination-btn[data-page]').forEach(btn => {
        btn.addEventListener('click', () => goTo(parseInt(btn.dataset.page)));
    });
}

// ==================== TRANSACTION DETAILS MODAL ====================
function openTransactionDetails(id) {
    const t = allTransactions.find(x => String(x.id) === String(id));
    if (!t) return;

    const modal = document.getElementById('transactionDetailsModal');
    const body = document.getElementById('transactionDetailsBody');

    let extraRows = '';
    if (t.details) {
        Object.entries(t.details).forEach(([label, value]) => {
            if (value === null || value === undefined || value === '') return;
            extraRows += `
                <div class="info-row">
                    <span class="info-label">${escapeHtml(label)}</span>
                    <span class="info-value">${escapeHtml(String(value))}</span>
                </div>`;
        });
    }

    body.innerHTML = `
        <div class="info-row">
            <span class="info-label">Request ID</span>
            <span class="info-value">${escapeHtml(t.id || 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Type</span>
            <span class="info-value">${escapeHtml(t.type || 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Description</span>
            <span class="info-value">${escapeHtml(t.description || 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Status</span>
            <span class="info-value">${escapeHtml(t.status || 'Pending')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Date Submitted</span>
            <span class="info-value">${formatDateTime12Hour(t.submitted_at)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Date Updated</span>
            <span class="info-value">${t.updated_at ? formatDateTime12Hour(t.updated_at) : '—'}</span>
        </div>
        ${extraRows}
    `;

    modal.classList.add('show');
}

function closeTransactionDetails() {
    const modal = document.getElementById('transactionDetailsModal');
    modal.classList.remove('show');
}

// ==================== PROFILE / ICON ====================
async function loadProfileName() {
    try {
        const username = sessionStorage.getItem('username');
        const tabId = getTabId();
        if (!username) return;
        const response = await fetch(`/api/user/profile?username=${encodeURIComponent(username)}&tab_id=${tabId}`);
        const data = await response.json();
        const profileNameSpan = document.getElementById('profileName');
        if (profileNameSpan) {
            profileNameSpan.textContent = data.name || data.first_name || data.username || 'User';
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

async function loadProfileIcon() {
    try {
        const tabId = getTabId();
        const response = await fetch('/api/get-user-profile?tab_id=' + tabId);
        const data = await response.json();
        const profileIcon = document.getElementById('profileIcon');
        if (profileIcon) {
            profileIcon.src = (data.photo_url || data.profile_photo) && data.profile_photo !== 'none'
                ? (data.photo_url || data.profile_photo)
                : '/static/cablevision.jpg';
        }
    } catch (error) {
        console.error('Error loading profile icon:', error);
        const profileIcon = document.getElementById('profileIcon');
        if (profileIcon) profileIcon.src = '/static/cablevision.jpg';
    }
}

// ==================== HAMBURGER MENU ====================
function setupHamburgerMenu() {
    const hamburger = document.getElementById('hamburgerBtn');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    function toggleSidebar() {
        sidebar.classList.toggle('active');
        if (sidebarOverlay) sidebarOverlay.classList.toggle('active');
        document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
    }

    if (hamburger) hamburger.addEventListener('click', toggleSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', toggleSidebar);
}

// ==================== PROFILE DROPDOWN ====================
function setupProfileDropdown() {
    const profileBtn = document.getElementById('profileBtn');
    const profileMenu = document.getElementById('profileMenu');
    if (profileBtn && profileMenu) {
        profileBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            profileBtn.classList.toggle('active');
            profileMenu.classList.toggle('show');
        });
        document.addEventListener('click', function() {
            profileMenu.classList.remove('show');
            if (profileBtn) profileBtn.classList.remove('active');
        });
    }
}

// ==================== LOGOUT ====================
function setupLogout() {
    const logoutBtn = document.getElementById('logoutBtn');
    const logoutModal = document.getElementById('logoutModal');
    const cancelLogout = document.getElementById('cancelLogout');
    const confirmLogout = document.getElementById('confirmLogout');
    const closeLogoutModal = document.querySelector('#logoutModal .close-btn');

    if (logoutBtn && logoutModal) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            logoutModal.classList.add('show');
            document.body.style.overflow = 'hidden';
        });

        const closeModal = () => {
            logoutModal.classList.remove('show');
            document.body.style.overflow = '';
        };

        if (cancelLogout) cancelLogout.addEventListener('click', closeModal);
        if (closeLogoutModal) closeLogoutModal.addEventListener('click', closeModal);

        if (confirmLogout) {
            confirmLogout.addEventListener('click', () => {
                if (window.SessionManager) {
                    window.SessionManager.logout('You have been logged out successfully.');
                } else {
                    localStorage.clear();
                    sessionStorage.clear();
                    window.location.replace('/');
                }
            });
        }

        window.addEventListener('click', (e) => {
            if (e.target === logoutModal) closeModal();
        });
    }
}

// ==================== MODAL EVENT LISTENERS ====================
function setupTransactionDetailsModal() {
    const modal = document.getElementById('transactionDetailsModal');
    const closeBtn = document.getElementById('closeTransactionDetailsModal');
    const closeFooterBtn = document.getElementById('closeTransactionDetailsBtn');

    if (closeBtn) closeBtn.addEventListener('click', closeTransactionDetails);
    if (closeFooterBtn) closeFooterBtn.addEventListener('click', closeTransactionDetails);

    window.addEventListener('click', (e) => {
        if (e.target === modal) closeTransactionDetails();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('show')) closeTransactionDetails();
    });
}

// ==================== CHECK TERMINATED STATUS ====================
function checkTerminatedStatus() {
    const tabId = getTabId();
    fetch('/api/get-user-status?tab_id=' + tabId)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'Terminated' || data.status === 'Inactive' || data.status === 'Deactivated') {
                sessionStorage.setItem('terminated_redirect', 'true');
                window.location.replace('/user/dashboard');
            }
        })
        .catch(err => console.error('Error checking status:', err));
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', async () => {
    const isLoggedIn = sessionStorage.getItem('username') && sessionStorage.getItem('userType') === 'user';
    if (!isLoggedIn) {
        window.location.replace('/');
        return;
    }

    setupHamburgerMenu();
    setupProfileDropdown();
    setupLogout();
    setupTransactionDetailsModal();

    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const clearBtn = document.getElementById('clearSearch');

    if (searchInput) searchInput.addEventListener('input', () => {
        applyFiltersAndPaginate();
        if (clearBtn) clearBtn.style.display = searchInput.value ? 'flex' : 'none';
    });
    if (statusFilter) statusFilter.addEventListener('change', applyFiltersAndPaginate);
    if (clearBtn) clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        applyFiltersAndPaginate();
        clearBtn.style.display = 'none';
    });

    await loadProfileName();
    await loadProfileIcon();
    await loadCurrentPlan();
    await fetchTransactions();

    checkTerminatedStatus();

    if (window.UserNotificationSystem) {
        window.UserNotificationSystem.init();
    }
});