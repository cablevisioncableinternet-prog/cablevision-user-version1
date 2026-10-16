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
        
        // Small delay para smooth transition
        setTimeout(() => {
            // Hide skeleton
            const loadingEl = document.getElementById('currentPlanLoading');
            if (loadingEl) loadingEl.style.display = 'none';
            
            // Show actual details
            const detailsEl = document.getElementById('currentPlanDetails');
            if (detailsEl) detailsEl.style.display = 'grid';

            if (data.error) return;

            document.getElementById('currentPlanName').textContent = data.plan || '--';
            document.getElementById('currentPlanSpeed').textContent = data.speed ? `${data.speed} Mbps` : '-- Mbps';
            document.getElementById('currentPlanPrice').textContent = formatPriceDisplay(data.price);
            document.getElementById('contractNumber').textContent = data.contract_number || '--';
        }, 400);
    } catch (error) {
        console.error('Error loading current plan:', error);
        // Hide skeleton even on error
        const loadingEl = document.getElementById('currentPlanLoading');
        if (loadingEl) loadingEl.style.display = 'none';
        const detailsEl = document.getElementById('currentPlanDetails');
        if (detailsEl) detailsEl.style.display = 'grid';
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
    loadReviewSection(t);
}

function closeTransactionDetails() {
    const modal = document.getElementById('transactionDetailsModal');
    modal.classList.remove('show');
}

// ==================== REVIEW SECTION (SA DETAILS MODAL) ====================
const REVIEW_TYPE_MAP = {
    'Change Plan': 'change_plan',
    'Termination': 'termination',
    'Reconnection': 'reconnect'
};
const TRV_LABELS = ['Select a rating', 'Poor', 'Fair', 'Good', 'Very good', 'Excellent'];
let reviewRenderToken = 0;

function trvStarsHtml(value) {
    let html = '';
    for (let i = 1; i <= 5; i++) {
        html += `<i class="fas fa-star ${i <= value ? 'on' : ''}"></i>`;
    }
    return html;
}

async function loadReviewSection(t) {
    const box = document.getElementById('transactionReviewSection');
    if (!box) return;

    const type = REVIEW_TYPE_MAP[t.type];
    const token = ++reviewRenderToken;   // iwas lumang response na papalit sa bago
    box.innerHTML = '';
    if (!type) return;

    box.innerHTML = '<div class="trv-loading"><i class="fas fa-spinner fa-spin"></i> Loading review...</div>';

    try {
        const res = await fetch(`/api/user/review-status?type=${type}&transaction_id=${encodeURIComponent(t.id)}`);
        const data = await res.json();
        if (token !== reviewRenderToken) return;

        if (!res.ok) { box.innerHTML = ''; return; }

        if (!data.eligible) {
            const st = (t.status || '').toLowerCase();
            box.innerHTML = st === 'pending'
                ? `<div class="trv-note"><i class="fas fa-info-circle"></i> You can review this request once it is approved.</div>`
                : '';
            return;
        }

        if (data.reviewed) renderReviewView(box, t, type, data);
        else renderReviewPrompt(box, t, type, data);
    } catch (err) {
        console.error('Review section error:', err);
        if (token === reviewRenderToken) box.innerHTML = '';
    }
}

function renderReviewPrompt(box, t, type, data) {
    box.innerHTML = `
        <div class="trv-card">
            <div class="trv-head">
                <span class="trv-title"><i class="fas fa-star"></i> How was this service?</span>
                <button type="button" class="trv-btn trv-btn-primary" id="trvRateBtn">
                    <i class="fas fa-star"></i> Rate
                </button>
            </div>
            <p class="trv-muted">Share your feedback to help us improve.</p>
        </div>`;
    document.getElementById('trvRateBtn').addEventListener('click', () => {
        renderReviewForm(box, t, type, data, null);
    });
}

function renderReviewView(box, t, type, data) {
    const r = data.review;
    const postedAs = r.is_anonymous ? data.masked_name : data.full_name;
    const when = r.updated_at
        ? `Edited ${formatDateTime12Hour(r.updated_at)}`
        : formatDateTime12Hour(r.created_at);

    box.innerHTML = `
        <div class="trv-card">
            <div class="trv-head">
                <span class="trv-title"><i class="fas fa-star"></i> Your Review</span>
                <button type="button" class="trv-btn trv-btn-ghost" id="trvEditBtn">
                    <i class="fas fa-pen"></i> Edit
                </button>
            </div>
            <div class="trv-stars">${trvStarsHtml(r.rating)}
                <span class="trv-rating-text">${TRV_LABELS[r.rating] || ''}</span>
            </div>
            ${r.comment
                ? `<p class="trv-comment">${escapeHtml(r.comment)}</p>`
                : `<p class="trv-comment trv-muted">No comment</p>`}
            <div class="trv-meta">Posted as <strong>${escapeHtml(postedAs)}</strong> &middot; ${escapeHtml(when)}</div>
        </div>`;

    document.getElementById('trvEditBtn').addEventListener('click', () => {
        renderReviewForm(box, t, type, data, r);
    });
}

function renderReviewForm(box, t, type, data, existing) {
    const isEdit = !!existing;
    let rating = isEdit ? existing.rating : 0;

    let starButtons = '';
    for (let i = 1; i <= 5; i++) {
        starButtons += `<button type="button" class="trv-star" data-value="${i}" aria-label="${i} star${i > 1 ? 's' : ''}"><i class="fas fa-star"></i></button>`;
    }

    box.innerHTML = `
        <div class="trv-card">
            <div class="trv-head">
                <span class="trv-title"><i class="fas fa-star"></i> ${isEdit ? 'Edit Your Review' : 'Rate This Service'}</span>
            </div>
            <div class="trv-stars-input" id="trvStars">${starButtons}</div>
            <div class="trv-rating-label" id="trvRatingLabel"></div>
            <textarea id="trvComment" class="trv-textarea" rows="3" maxlength="500"
                      placeholder="Tell us what went well or what we can improve (optional)"></textarea>
            <label class="trv-check">
                <input type="checkbox" id="trvAnon">
                <span>Post as anonymous</span>
            </label>
            <div class="trv-anon-preview" id="trvAnonPreview"></div>
            <div class="trv-actions">
                <button type="button" class="trv-btn trv-btn-ghost" id="trvCancelBtn">Cancel</button>
                <button type="button" class="trv-btn trv-btn-primary" id="trvSaveBtn">
                    <i class="fas fa-paper-plane"></i> ${isEdit ? 'Save Changes' : 'Submit Review'}
                </button>
            </div>
        </div>`;

    const starsWrap = document.getElementById('trvStars');
    const stars = Array.from(starsWrap.querySelectorAll('.trv-star'));
    const labelEl = document.getElementById('trvRatingLabel');
    const commentEl = document.getElementById('trvComment');
    const anonEl = document.getElementById('trvAnon');
    const previewEl = document.getElementById('trvAnonPreview');
    const saveBtn = document.getElementById('trvSaveBtn');
    const cancelBtn = document.getElementById('trvCancelBtn');

    function paint(value) {
        stars.forEach(s => s.classList.toggle('on', Number(s.dataset.value) <= value));
        labelEl.textContent = TRV_LABELS[value] || TRV_LABELS[0];
    }

    function paintPreview() {
        const shown = anonEl.checked ? data.masked_name : data.full_name;
        previewEl.innerHTML = `Your name will appear as: <strong>${escapeHtml(shown)}</strong>`;
    }

    commentEl.value = isEdit ? existing.comment : '';
    anonEl.checked = isEdit ? existing.is_anonymous : false;
    paint(rating);
    paintPreview();

    stars.forEach(s => {
        s.addEventListener('click', () => { rating = Number(s.dataset.value); paint(rating); });
        s.addEventListener('mouseenter', () => paint(Number(s.dataset.value)));
    });
    starsWrap.addEventListener('mouseleave', () => paint(rating));
    anonEl.addEventListener('change', paintPreview);

    cancelBtn.addEventListener('click', () => loadReviewSection(t));

    saveBtn.addEventListener('click', async () => {
        if (!rating) {
            showToast('Please select a star rating.', 'error');
            return;
        }

        saveBtn.disabled = true;
        cancelBtn.disabled = true;
        const originalHtml = saveBtn.innerHTML;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        try {
            const res = await fetch(isEdit ? '/api/user/update-review' : '/api/user/submit-review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    transaction_type: type,
                    transaction_id: t.id,
                    rating: rating,
                    comment: commentEl.value.trim(),
                    is_anonymous: anonEl.checked
                })
            });
            const result = await res.json();

            if (res.ok && result.success) {
                showToast(result.message || 'Review saved.', 'success');
                loadReviewSection(t);
            } else if (result.already_reviewed) {
                showToast(result.error, 'info');
                loadReviewSection(t);
            } else {
                showToast(result.error || 'Failed to save review.', 'error');
                saveBtn.disabled = false;
                cancelBtn.disabled = false;
                saveBtn.innerHTML = originalHtml;
            }
        } catch (err) {
            console.error('Save review error:', err);
            showToast('Network error. Please try again.', 'error');
            saveBtn.disabled = false;
            cancelBtn.disabled = false;
            saveBtn.innerHTML = originalHtml;
        }
    });
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
            const status = data.status;
            if (status === 'Terminated' || status === 'Inactive' || status === 'Deactivated') {
                disableRestrictedSidebarLinks();
            }
        })
        .catch(err => console.error('Error checking status:', err));
}

// ==================== DISABLE CHANGE PLAN & TERMINATION LINKS ====================
function disableRestrictedSidebarLinks() {
    const sidebarLinks = document.querySelectorAll('.sidebar-menu a');
    sidebarLinks.forEach(link => {
        if (!link.href.includes('/user/dashboard') && !link.href.includes('/user/transactions')) {
            link.style.pointerEvents = 'none';
            link.style.opacity = '0.5';
            link.style.cursor = 'not-allowed';
            link.title = 'This feature is disabled for your account status.';

            if (!link.querySelector('.fa-lock')) {
                const lockIcon = document.createElement('i');
                lockIcon.className = 'fas fa-lock';
                lockIcon.style.marginLeft = '8px';
                lockIcon.style.fontSize = '12px';
                lockIcon.style.color = '#dc2626';
                link.appendChild(lockIcon);
            }
        }
    });
}


// ==================== AUTO-OPEN DETAILS MODAL (GALING SA NOTIFICATION) ====================
function openTransactionFromNotification() {
    const params = new URLSearchParams(window.location.search);
    const openId = params.get('open_id');
    const openType = params.get('open_type');
    const openStatus = params.get('open_status');

    if (!openId && !openType) return;

    // Linisin ang URL (tira ang tab_id) para hindi bumukas ulit kapag nag-refresh
    params.delete('open_id');
    params.delete('open_type');
    params.delete('open_status');
    const cleanQuery = params.toString();
    history.replaceState(null, '', window.location.pathname + (cleanQuery ? '?' + cleanQuery : ''));

    let target = null;

    // 1) Eksaktong match kung may request ID
    if (openId) {
        target = allTransactions.find(t =>
            String(t.id) === String(openId) && (!openType || t.type === openType)
        );
    }

    // 2) Kung walang ID: pinakabagong request ng type na iyon, na kapareho ng status
    if (!target && openType) {
        const sameType = allTransactions.filter(t => t.type === openType);
        const sameStatus = openStatus
            ? sameType.filter(t => (t.status || '').toLowerCase() === openStatus.toLowerCase())
            : sameType;
        const pool = (sameStatus.length ? sameStatus : sameType).slice();

        pool.sort((a, b) => {
            const aDate = a.updated_at || a.submitted_at || '';
            const bDate = b.updated_at || b.submitted_at || '';
            return bDate.localeCompare(aDate);
        });
        target = pool[0] || null;
    }

    if (!target) return;
    openTransactionDetails(target.id);
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

    // Kung galing sa notification, buksan agad ang details modal
    openTransactionFromNotification();

    checkTerminatedStatus();

    if (window.UserNotificationSystem) {
        window.UserNotificationSystem.init();
    }
});



