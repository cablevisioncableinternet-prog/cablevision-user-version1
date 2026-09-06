// ================= TOAST NOTIFICATION =================
function showToast(message, type = 'info') {
    const LABELS = {
        success: 'Success',
        error: 'Error',
        info: 'Notice',
        loading: 'Please wait'
    };

    const ICONS = {
        success: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
        error: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
        info: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
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
                @keyframes toastSpin { to { transform: rotate(360deg); } }
                @keyframes toastProgress { from { transform: scaleX(1); } to { transform: scaleX(0); } }
                @keyframes toastLoading { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
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
        <div class="custom-toast-progress">
            <div class="custom-toast-progress-bar"></div>
        </div>
    `;

    toast.className = `custom-toast ${type}`;
    void toast.offsetWidth;
    toast.classList.add('show');

    clearTimeout(toast._hideTimer);

    if (type === 'loading') {
        // Loading stays visible
    } else {
        toast._hideTimer = setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// ================= PROFILE DROPDOWN =================
const profileBtn = document.getElementById("profileBtn");
const profileMenu = document.getElementById("profileMenu");

if (profileBtn && profileMenu) {
    profileBtn.addEventListener("click", e => {
        e.stopPropagation();
        profileMenu.classList.toggle("show");
    });

    window.addEventListener("click", e => {
        if (!profileBtn.contains(e.target)) profileMenu.classList.remove("show");
    });
}

// ================= LOAD PROFILE =================
async function loadProfile() {
    try {
        const res = await fetch("/api/get-user-profile");
        if (!res.ok) throw new Error("Failed to fetch profile");
        const profile = await res.json();

        const userId = profile.user_id || profile.id;
        if (userId) {
            localStorage.setItem('user_id', userId);
            sessionStorage.setItem('user_id', userId);
            console.log('User ID stored:', userId);
            
            if (window.UserNotificationSystem) {
                console.log('Initializing UserNotificationSystem...');
                window.UserNotificationSystem.init();
            }
        }

        const profileImg = document.getElementById("profileIcon");
        if (profileImg) {
            if (profile.profile_photo && profile.profile_photo !== 'none' && profile.profile_photo !== '') {
                profileImg.src = profile.profile_photo;
            } else {
                profileImg.src = "/static/profile.jpg";
            }
        }
        
        const profileNameSpan = document.getElementById("profileName");
        if (profileNameSpan && profile.first_name) {
            profileNameSpan.textContent = profile.first_name;
        }
        
    } catch (err) {
        console.error("Error loading profile:", err);
        const username = sessionStorage.getItem('username');
        const profileNameSpan = document.getElementById("profileName");
        if (profileNameSpan && username) {
            profileNameSpan.textContent = username;
        }
    }
}

loadProfile();

// ================= LOGOUT =================
const logoutBtn = document.getElementById("logoutBtn");
const logoutModal = document.getElementById("logoutModal");
if (logoutBtn && logoutModal) {
    const closeBtn = logoutModal.querySelector(".close-btn");
    const cancelBtn = document.getElementById("cancelLogout");
    const confirmBtn = document.getElementById("confirmLogout");

    logoutBtn.addEventListener("click", e => {
        e.preventDefault();
        logoutModal.classList.add('show');
        document.body.style.overflow = 'hidden';
    });

    const closeModal = () => {
        logoutModal.classList.remove('show');
        document.body.style.overflow = '';
    };

    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

    if (confirmBtn) {
        confirmBtn.addEventListener("click", async () => {
            try {
                const tabId = sessionStorage.getItem('tab_id');
                await fetch('/api/logout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tab_id: tabId })
                }).catch(() => {});
            } catch(e) {}

            localStorage.removeItem('user_id');
            sessionStorage.clear();
            window.location.replace('/');
        });
    }

    window.addEventListener("click", e => {
        if (e.target === logoutModal) closeModal();
    });
}

// ================= DATE & TIME =================
function updateDateTime() {
    const now = new Date();
    const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
    const day = days[now.getDay()];
    const date = now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const time = now.toLocaleTimeString();

    const dayEl = document.getElementById("currentDay");
    const dateEl = document.getElementById("currentDate");
    const timeEl = document.getElementById("liveTime");

    if (dayEl) dayEl.textContent = day;
    if (dateEl) dateEl.textContent = date;
    if (timeEl) timeEl.textContent = time;
}
setInterval(updateDateTime, 1000);
updateDateTime();

// ================= ESCAPE HTML =================
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ================= HAMBURGER MENU =================
const hamburger = document.getElementById('hamburgerBtn');
const sidebar = document.querySelector('.sidebar');
const overlay = document.getElementById('sidebarOverlay');

function toggleSidebar() {
    if (!sidebar) return;
    sidebar.classList.toggle('active');
    if (hamburger) hamburger.classList.toggle('active');
    if (overlay) overlay.classList.toggle('active');
    document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
}

if (hamburger) {
    hamburger.addEventListener('click', toggleSidebar);
}

if (overlay) {
    overlay.addEventListener('click', toggleSidebar);
}

window.addEventListener('resize', function() {
    if (window.innerWidth > 768 && sidebar && sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
        if (hamburger) hamburger.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// ================= LOAD CURRENT PLAN =================
async function loadCurrentPlan() {
    try {
        const res = await fetch('/api/get-user-connection');
        if (!res.ok) throw new Error('Failed to fetch plan');
        const data = await res.json();

        if (data && data.length > 0) {
            const plan = data[0];
            document.getElementById('currentPlanName').textContent = plan.plan_name || 'No Active Plan';
            document.getElementById('currentPlanSpeed').textContent = plan.mbps ? `${plan.mbps} Mbps` : 'N/A';
            
            let priceDisplay = '₱0.00';
            if (plan.plan_price) {
                const cleanPrice = String(plan.plan_price).replace(/[₱,]/g, '').trim();
                const priceNum = parseFloat(cleanPrice);
                if (!isNaN(priceNum) && priceNum > 0) {
                    priceDisplay = `₱${priceNum.toFixed(2)}/mo`;
                }
            }
            document.getElementById('currentPlanPrice').textContent = priceDisplay;
        }
    } catch (err) {
        console.error('Error loading current plan:', err);
        document.getElementById('currentPlanName').textContent = 'Error loading plan';
    }
}

loadCurrentPlan();

// ================= TRANSACTIONS STATE =================
const state = {
    currentPage: 1,
    perPage: 10,
    totalPages: 0,
    totalItems: 0,
    statusFilter: 'All',
    typeFilter: 'All',
    searchQuery: '',
    isLoading: false
};

// ================= TRANSACTION DETAIL MODAL FUNCTIONS =================
let currentDetailTransaction = null;

// Function to open transaction detail modal
function openTransactionDetail(transaction) {
    currentDetailTransaction = transaction;
    const modal = document.getElementById('transactionDetailModal');
    if (!modal) {
        console.error('Transaction detail modal not found!');
        return;
    }

    // Populate modal with transaction data
    populateTransactionDetail(transaction);

    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

// Function to close transaction detail modal
function closeTransactionDetail() {
    const modal = document.getElementById('transactionDetailModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
    currentDetailTransaction = null;
}

// Function to populate transaction detail modal
function populateTransactionDetail(transaction) {
    // Request ID
    document.getElementById('detailRequestId').textContent = transaction.request_id || 'N/A';
    document.getElementById('detailRequestIdValue').textContent = transaction.request_id || 'N/A';

    // Type
    const type = transaction.type || 'Unknown';
    const typeBadge = document.getElementById('detailTypeBadge');
    typeBadge.textContent = type;
    typeBadge.className = `type-badge type-${type.toLowerCase().replace(' ', '-')}`;
    document.getElementById('detailTypeValue').textContent = type;

    // Status
    const status = transaction.status || 'Pending';
    const statusClass = status.toLowerCase();
    const statusIcon = status === 'Approved' ? 'fa-check-circle' : 
                       status === 'Rejected' ? 'fa-times-circle' : 'fa-clock';
    const statusEl = document.getElementById('detailStatus');
    statusEl.innerHTML = `<span class="status-badge status-${statusClass}"><i class="fas ${statusIcon}"></i> ${status}</span>`;
    document.getElementById('detailStatusValue').textContent = status;

    // Dates
    document.getElementById('detailSubmittedValue').textContent = transaction.submitted_at || 'N/A';
    document.getElementById('detailUpdatedValue').textContent = transaction.updated_at || 'N/A';

    // Description
    document.getElementById('detailDescription').textContent = transaction.description || 'No description available';

    // Plan Details
    const currentPlan = transaction.current_plan || 'N/A';
    const newPlan = transaction.new_plan || null;
    document.getElementById('detailCurrentPlan').textContent = currentPlan;

    const newPlanContainer = document.getElementById('detailNewPlanContainer');
    const newPlanEl = document.getElementById('detailNewPlan');
    
    if (newPlan && newPlan !== 'N/A' && newPlan !== 'null') {
        newPlanContainer.style.display = 'flex';
        newPlanEl.textContent = newPlan;
    } else {
        newPlanContainer.style.display = 'none';
        newPlanEl.textContent = '-';
    }

    // Admin Notes
    const adminNotesSection = document.getElementById('detailAdminNotesSection');
    const adminNotesEl = document.getElementById('detailAdminNotes');
    if (transaction.admin_notes && transaction.admin_notes !== 'null' && transaction.admin_notes !== '') {
        adminNotesSection.style.display = 'block';
        adminNotesEl.textContent = transaction.admin_notes;
    } else {
        adminNotesSection.style.display = 'none';
        adminNotesEl.textContent = '-';
    }

    // Timeline
    populateTimeline(transaction);
}

// Function to populate timeline
function populateTimeline(transaction) {
    const timeline = document.getElementById('detailTimeline');
    if (!timeline) return;

    const items = [];
    const status = transaction.status || 'Pending';
    const submittedAt = transaction.submitted_at;
    const updatedAt = transaction.updated_at;

    // Submitted event
    if (submittedAt && submittedAt !== 'N/A' && submittedAt !== '') {
        items.push({
            date: submittedAt,
            text: 'Request submitted',
            type: 'submitted'
        });
    }

    // Status change event (if updated_at is different from submitted_at)
    if (updatedAt && updatedAt !== 'N/A' && updatedAt !== '' && updatedAt !== submittedAt) {
        const statusType = status.toLowerCase();
        const statusText = status === 'Approved' ? 'Request approved' :
                          status === 'Rejected' ? 'Request rejected' :
                          'Request updated';
        items.push({
            date: updatedAt,
            text: statusText,
            type: statusType
        });
    }

    // If no timeline items, show a message
    if (items.length === 0) {
        timeline.innerHTML = `<p style="color: #94a3b8; font-size: 13px; text-align: center; padding: 12px 0;">No timeline events available</p>`;
        return;
    }

    // Render timeline
    let html = '';
    items.forEach((item, index) => {
        const dotClass = item.type || 'pending';
        
        html += `
            <div class="timeline-item">
                <span class="timeline-dot ${dotClass}"></span>
                <div class="timeline-content">
                    <span class="timeline-text">${item.text}</span>
                    <span class="timeline-time">${item.date}</span>
                </div>
            </div>
        `;
    });

    timeline.innerHTML = html;
}

// ================= LOAD TRANSACTIONS =================
async function loadTransactions() {
    if (state.isLoading) return;
    state.isLoading = true;

    const tbody = document.getElementById('transactionsTableBody');
    if (!tbody) {
        console.error('transactionsTableBody not found!');
        return;
    }
    
    tbody.innerHTML = `<tr><td colspan="6" class="loading-data"><i class="fas fa-spinner fa-spin"></i> Loading transactions...</td></tr>`;

    try {
        const params = new URLSearchParams({
            page: state.currentPage,
            per_page: state.perPage,
            status: state.statusFilter,
            type: state.typeFilter,
            search: state.searchQuery
        });

        const res = await fetch(`/api/user/transactions?${params}`);
        if (!res.ok) throw new Error('Failed to fetch transactions');
        const data = await res.json();

        state.totalItems = data.total || 0;
        state.totalPages = data.total_pages || 0;

        // Update stats
        updateStats(data.transactions || []);

        // Render table
        renderTransactions(data.transactions || []);

        // Update pagination
        updatePagination();

    } catch (err) {
        console.error('Error loading transactions:', err);
        const tbody = document.getElementById('transactionsTableBody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" class="error-data"><i class="fas fa-exclamation-circle"></i> Failed to load transactions</td></tr>`;
        }
        showToast('Failed to load transactions. Please try again.', 'error');
    } finally {
        state.isLoading = false;
    }
}

// ================= UPDATE STATS =================
function updateStats(transactions) {
    const pending = transactions.filter(t => t.status === 'Pending').length;
    const approved = transactions.filter(t => t.status === 'Approved').length;
    const rejected = transactions.filter(t => t.status === 'Rejected').length;
    const total = transactions.length;

    document.getElementById('pendingCount').textContent = pending;
    document.getElementById('approvedCount').textContent = approved;
    document.getElementById('rejectedCount').textContent = rejected;
    document.getElementById('totalCount').textContent = total;
}

// ================= RENDER TRANSACTIONS (WITH CLICK HANDLER) =================
function renderTransactions(transactions) {
    const tbody = document.getElementById('transactionsTableBody');
    if (!tbody) return;

    if (!transactions || transactions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty-data"><i class="fas fa-inbox"></i> No transactions found</td></tr>`;
        return;
    }

    let html = '';
    transactions.forEach(t => {
        const statusClass = (t.status || 'pending').toLowerCase();
        const statusIcon = t.status === 'Approved' ? 'fa-check-circle' : 
                          t.status === 'Rejected' ? 'fa-times-circle' : 'fa-clock';

        // Store transaction data as data attributes for the click handler
        const dataAttrs = `
            data-request-id="${escapeHtml(t.request_id || '')}"
            data-type="${escapeHtml(t.type || '')}"
            data-status="${escapeHtml(t.status || 'Pending')}"
            data-description="${escapeHtml(t.description || '')}"
            data-submitted="${escapeHtml(t.submitted_at || '')}"
            data-updated="${escapeHtml(t.updated_at || '')}"
            data-current-plan="${escapeHtml(t.current_plan || '')}"
            data-new-plan="${escapeHtml(t.new_plan || '')}"
            data-admin-notes="${escapeHtml(t.admin_notes || '')}"
        `;

        html += `
            <tr class="clickable-row" ${dataAttrs} onclick="handleRowClick(this)">
                <td><span class="request-id-badge">${escapeHtml(t.request_id || 'N/A')}</span></td>
                <td><span class="type-badge type-${(t.type || '').toLowerCase().replace(' ', '-')}">${escapeHtml(t.type || 'Unknown')}</span></td>
                <td class="description-cell">${escapeHtml(t.description || '')}</td>
                <td><span class="status-badge status-${statusClass}"><i class="fas ${statusIcon}"></i> ${escapeHtml(t.status || 'Pending')}</span></td>
                <td>${t.submitted_at || 'N/A'}</td>
                <td>${t.updated_at || 'N/A'}</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

// ================= HANDLE ROW CLICK =================
function handleRowClick(row) {
    // Extract data from data attributes
    const transaction = {
        request_id: row.dataset.requestId || 'N/A',
        type: row.dataset.type || 'Unknown',
        status: row.dataset.status || 'Pending',
        description: row.dataset.description || 'No description available',
        submitted_at: row.dataset.submitted || 'N/A',
        updated_at: row.dataset.updated || 'N/A',
        current_plan: row.dataset.currentPlan || 'N/A',
        new_plan: row.dataset.newPlan || null,
        admin_notes: row.dataset.adminNotes || null
    };

    // Open the modal
    openTransactionDetail(transaction);
}

// ================= UPDATE PAGINATION =================
function updatePagination() {
    const info = document.getElementById('paginationInfo');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    const pageNumbers = document.getElementById('pageNumbers');

    const start = ((state.currentPage - 1) * state.perPage) + 1;
    const end = Math.min(state.currentPage * state.perPage, state.totalItems);

    info.textContent = state.totalItems > 0 ? `Showing ${start} - ${end} of ${state.totalItems}` : 'No transactions';

    prevBtn.disabled = state.currentPage <= 1;
    nextBtn.disabled = state.currentPage >= state.totalPages;

    // Generate page numbers
    let pageHtml = '';
    const totalPages = state.totalPages;

    if (totalPages <= 1) {
        pageHtml = `<span class="page-number active">1</span>`;
    } else {
        const pages = [];
        const current = state.currentPage;

        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i);
            }
        } else {
            pages.push(1);
            if (current > 3) pages.push('...');
            for (let i = Math.max(2, current - 1); i <= Math.min(totalPages - 1, current + 1); i++) {
                pages.push(i);
            }
            if (current < totalPages - 2) pages.push('...');
            pages.push(totalPages);
        }

        pageHtml = pages.map(p => {
            if (p === '...') {
                return `<span class="page-ellipsis">...</span>`;
            }
            return `<button class="page-number ${p === current ? 'active' : ''}" data-page="${p}">${p}</button>`;
        }).join('');
    }

    pageNumbers.innerHTML = pageHtml;

    // Add click listeners to page buttons
    document.querySelectorAll('.page-number[data-page]').forEach(btn => {
        btn.addEventListener('click', function() {
            const page = parseInt(this.dataset.page);
            if (page !== state.currentPage) {
                state.currentPage = page;
                loadTransactions();
                document.querySelector('.transactions-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// ================= EVENT LISTENERS =================
document.addEventListener('DOMContentLoaded', function() {
    // Initial load
    loadTransactions();

    // Status filter
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            state.statusFilter = this.value;
            state.currentPage = 1;
            loadTransactions();
        });
    }

    // Type filter
    const typeFilter = document.getElementById('typeFilter');
    if (typeFilter) {
        typeFilter.addEventListener('change', function() {
            state.typeFilter = this.value;
            state.currentPage = 1;
            loadTransactions();
        });
    }

    // Search input (with debounce)
    const searchInput = document.getElementById('searchInput');
    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                state.searchQuery = this.value.trim();
                state.currentPage = 1;
                loadTransactions();
            }, 500);
        });
    }

    // Clear filters
    const clearBtn = document.getElementById('clearFiltersBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            if (statusFilter) statusFilter.value = 'All';
            if (typeFilter) typeFilter.value = 'All';
            if (searchInput) searchInput.value = '';
            state.statusFilter = 'All';
            state.typeFilter = 'All';
            state.searchQuery = '';
            state.currentPage = 1;
            loadTransactions();
        });
    }

    // Previous page
    const prevBtn = document.getElementById('prevPageBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            if (state.currentPage > 1) {
                state.currentPage--;
                loadTransactions();
                document.querySelector('.transactions-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }

    // Next page
    const nextBtn = document.getElementById('nextPageBtn');
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            if (state.currentPage < state.totalPages) {
                state.currentPage++;
                loadTransactions();
                document.querySelector('.transactions-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }

    // ================= TRANSACTION DETAIL MODAL EVENT LISTENERS =================
    // Close modal buttons
    const closeBtn = document.getElementById('closeTransactionModal');
    const closeBtn2 = document.getElementById('closeTransactionModalBtn');
    const modal = document.getElementById('transactionDetailModal');

    if (closeBtn) {
        closeBtn.addEventListener('click', closeTransactionDetail);
    }
    if (closeBtn2) {
        closeBtn2.addEventListener('click', closeTransactionDetail);
    }
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeTransactionDetail();
            }
        });
    }

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeTransactionDetail();
        }
    });
});