// ================= USER LOGIN HISTORY SCRIPT =================

function showToast(message, type = 'info') {
    const LABELS = {
        success: 'Success',
        error:   'Error',
        info:    'Notice',
        loading: 'Please wait'
    };

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
        <div class="custom-toast-progress">
            <div class="custom-toast-progress-bar"></div>
        </div>
    `;

    toast.className = `custom-toast ${type}`;
    void toast.offsetWidth;
    toast.classList.add('show');

    clearTimeout(toast._hideTimer);
    if (type !== 'loading') {
        toast._hideTimer = setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// Global Variables & Modal State
let currentTabId = sessionStorage.getItem('tab_id') || new URLSearchParams(window.location.search).get('tab_id') || '';
let pendingLogoutAction = { mode: null, ids: [], includeCurrent: false };

function normalizeLocationText(value) {
    if (!value || typeof value !== 'string') return 'Current Location';

    const clean = value.trim();
    if (!clean) return 'Current Location';

    return clean
        .replace(/\s*,\s*/g, ', ')
        .replace(/\s+/g, ' ')
        .replace(/\(Local\)/gi, '')
        .replace(/\s+,\s*$/g, '')
        .trim();
}

function formatLocationDisplay(value) {
    const cleaned = normalizeLocationText(value);
    if (cleaned === 'Current Location' || cleaned === 'Unknown Location') {
        const saved = sessionStorage.getItem('device_location');
        return saved ? normalizeLocationText(saved) : 'Current Location';
    }
    return cleaned;
}

async function detectCurrentDeviceLocation() {
    if (!navigator.geolocation) return null;

    const alreadyKnown = sessionStorage.getItem('device_location');
    if (alreadyKnown) return alreadyKnown;

    try {
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 8000,
                maximumAge: 300000
            });
        });

        const { latitude, longitude } = position.coords;
        const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`;
        const response = await fetch(url, {
            headers: {
                'Accept-Language': 'en'
            }
        });

        if (!response.ok) return null;

        const data = await response.json();
        const address = data && data.address ? data.address : {};
        const city = address.city || address.town || address.village || address.municipality || '';
        const state = address.state || address.province || address.region || '';
        const country = address.country || 'Philippines';

        let locationText = 'Current Location';
        if (city && state) {
            locationText = `${city}, ${state}, ${country}`;
        } else if (city) {
            locationText = `${city}, ${country}`;
        } else if (state) {
            locationText = `${state}, ${country}`;
        }

        if (locationText !== 'Current Location') {
            sessionStorage.setItem('device_location', locationText);
            return locationText;
        }

        return null;
    } catch (error) {
        console.warn('Geolocation lookup failed:', error);
        return null;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    initLayout();
    await detectCurrentDeviceLocation();
    await syncSessionWithBackend();
    loadProfile();
    loadLoginHistory();
    initModalEvents();
});

async function syncSessionWithBackend() {
    const username = sessionStorage.getItem('username');
    const userType = sessionStorage.getItem('userType');
    const tabId = sessionStorage.getItem('tab_id') || currentTabId;

    if (username && userType === 'user' && tabId) {
        try {
            await fetch('/user/sync-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: username,
                    userType: userType,
                    tab_id: tabId
                }),
                credentials: 'include'
            });
        } catch (e) {
            console.warn("Session sync warning:", e);
        }
    }
}

// ================= LAYOUT INITIALIZATION =================
function initLayout() {
    const hamburger = document.getElementById("hamburgerBtn");
    const sidebar = document.getElementById("sidebar") || document.querySelector(".sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    function toggleSidebar() {
        if (!sidebar) return;
        sidebar.classList.toggle("active");
        if (hamburger) hamburger.classList.toggle("active");
        if (overlay) overlay.classList.toggle("active");
        document.body.style.overflow = sidebar.classList.contains("active") ? "hidden" : "";
    }

    if (hamburger) {
        hamburger.addEventListener("click", toggleSidebar);
    }

    if (overlay) {
        overlay.addEventListener("click", toggleSidebar);
    }

    window.addEventListener("resize", function() {
        if (window.innerWidth > 768 && sidebar && sidebar.classList.contains("active")) {
            sidebar.classList.remove("active");
            if (hamburger) hamburger.classList.remove("active");
            if (overlay) overlay.classList.remove("active");
            document.body.style.overflow = "";
        }
    });

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape" && sidebar && sidebar.classList.contains("active")) {
            toggleSidebar();
        }
    });

    // Profile Dropdown
    const profileBtn = document.getElementById("profileBtn");
    const profileMenu = document.getElementById("profileMenu");

    if (profileBtn && profileMenu) {
        profileBtn.addEventListener("click", e => {
            e.stopPropagation();
            profileMenu.classList.toggle("show");
            profileBtn.classList.toggle("active");
        });

        window.addEventListener("click", e => {
            if (!profileBtn.contains(e.target)) {
                profileMenu.classList.remove("show");
                profileBtn.classList.remove("active");
            }
        });
    }

    // Topbar Header Logout Modal
    const logoutBtn = document.getElementById("logoutBtn");
    const logoutModal = document.getElementById("logoutModal");
    if (logoutBtn && logoutModal) {
        const closeBtn = document.getElementById("closeLogoutModal");
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
                } catch (e) {}

                localStorage.removeItem('user_id');
                sessionStorage.clear();
                window.location.replace('/');
            });
        }
    }
}

// ================= LOAD PROFILE =================
async function loadProfile() {
    try {
        const profileUrl = currentTabId ? `/api/get-user-profile?tab_id=${encodeURIComponent(currentTabId)}` : "/api/get-user-profile";
        const res = await fetch(profileUrl);
        if (!res.ok) throw new Error("Failed to fetch profile");
        const profile = await res.json();

        const userId = profile.user_id || profile.id;
        if (userId) {
            sessionStorage.setItem('user_id', userId);
            if (window.UserNotificationSystem) {
                window.UserNotificationSystem.init();
            }
        }

        const profileImg = document.getElementById("profileIcon");
        if (profileImg) {
            profileImg.src = (profile.profile_photo && profile.profile_photo !== 'none') ? profile.profile_photo : "/static/profile.jpg";
        }
    } catch (err) {
        console.error("Error loading profile:", err);
    }
}

// Helper: Get Icon Class for OS / Device
function getDeviceIconClass(osName, deviceStr) {
    const text = ((osName || '') + ' ' + (deviceStr || '')).toLowerCase();
    if (text.includes('android') || text.includes('iphone') || text.includes('ios') || text.includes('mobile')) {
        return 'fas fa-mobile-alt';
    } else if (text.includes('ipad') || text.includes('tablet')) {
        return 'fas fa-tablet-alt';
    } else if (text.includes('mac') || text.includes('macintosh') || text.includes('apple')) {
        return 'fas fa-laptop-house';
    }
    return 'fas fa-desktop';
}

// Helper: Extract Device Type Name (e.g., "Windows PC", "iPhone", "Android Phone")
function getDeviceTypeName(osName, deviceStr) {
    const text = ((osName || '') + ' ' + (deviceStr || '')).toLowerCase();
    
    // Mobile devices
    if (text.includes('iphone')) return 'iPhone';
    if (text.includes('ipad')) return 'iPad';
    if (text.includes('android')) {
        if (text.includes('tablet')) return 'Android Tablet';
        return 'Android Phone';
    }
    
    // Desktop/Laptop devices
    if (text.includes('mac') || text.includes('macintosh') || text.includes('apple')) {
        if (text.includes('ipad')) return 'iPad';
        return 'Mac';
    }
    if (text.includes('windows')) {
        if (text.includes('mobile')) return 'Windows Phone';
        return 'Windows PC';
    }
    if (text.includes('linux')) return 'Linux';
    
    return osName || 'Device';
}

// ================= LOAD LOGIN HISTORY =================
async function loadLoginHistory() {
    try {
        const username = sessionStorage.getItem('username') || '';
        const detectedLocation = await detectCurrentDeviceLocation();
        const url = `/api/user/login-history?tab_id=${encodeURIComponent(currentTabId)}&username=${encodeURIComponent(username)}`;
        const headers = {};

        if (detectedLocation) {
            headers['X-Device-Location'] = detectedLocation;
        }

        const res = await fetch(url, {
            headers: headers,
            credentials: 'include'
        });
        if (!res.ok) {
            const errJson = await res.json().catch(() => ({}));
            throw new Error(errJson.error || "Failed to fetch login history");
        }
        const data = await res.json();

        if (!data.success) {
            showToast(data.error || "Could not load login history", "error");
            return;
        }

        renderCurrentDevice(data.current_device);
        renderOtherDevices(data.other_devices);
    } catch (err) {
        console.error("Error loading login history:", err);
        showToast(err.message || "Error loading device login history", "error");
    }
}

// Render Current Device Section
function renderCurrentDevice(device) {
    const container = document.getElementById("currentDeviceContainer");
    if (!container) return;

    if (!device) {
        container.innerHTML = `
            <div class="empty-devices">
                <i class="fas fa-exclamation-circle"></i>
                <p>No active current device record found.</p>
            </div>
        `;
        return;
    }

    const iconClass = getDeviceIconClass(device.os, device.device_info);
    const deviceTypeName = getDeviceTypeName(device.os, device.device_info);

    const locationLabel = formatLocationDisplay(device.location || sessionStorage.getItem('device_location'));

    container.innerHTML = `
        <div class="current-device-card">
            <div class="device-card-header">
                <div class="device-main-info">
                    <div class="device-icon-box">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="device-name-wrap">
                        <h3>${deviceTypeName}</h3>
                        <p>${device.browser || 'Browser'} • ${device.os || 'OS'}</p>
                    </div>
                </div>
                <div>
                    <span class="badge-current-device">Active (This Device)</span>
                </div>
            </div>

            <div class="device-details-grid">
                <div class="detail-item">
                    <i class="fas fa-map-marker-alt"></i>
                    <div class="detail-item-text">
                        <label>Location</label>
                        <span>${locationLabel}</span>
                    </div>
                </div>
                <div class="detail-item">
                    <i class="fas fa-network-wired"></i>
                    <div class="detail-item-text">
                        <label>IP Address</label>
                        <span>${device.ip_address || '127.0.0.1'}</span>
                    </div>
                </div>
                <div class="detail-item">
                    <i class="fas fa-clock"></i>
                    <div class="detail-item-text">
                        <label>Login Time</label>
                        <span>${device.formatted_login_time || device.login_time || 'Just Now'}</span>
                    </div>
                </div>
                <div class="detail-item">
                    <i class="fas fa-history"></i>
                    <div class="detail-item-text">
                        <label>Last Active</label>
                        <span>${device.formatted_last_active || device.last_active || 'Active Now'}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Render Other Active Devices & History List
function renderOtherDevices(otherDevices) {
    const tbody = document.getElementById("otherDevicesTbody");
    const emptyState = document.getElementById("emptyDevicesState");
    const tableContainer = document.querySelector(".devices-table-container");
    const batchToolbar = document.getElementById("batchToolbar");
    const selectAllCheck = document.getElementById("selectAllDevices");

    if (!tbody) return;

    if (selectAllCheck) selectAllCheck.checked = false;
    updateBatchToolbar();

    if (!otherDevices || otherDevices.length === 0) {
        tbody.innerHTML = '';
        if (tableContainer) tableContainer.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
        if (batchToolbar) batchToolbar.style.display = 'none';
        return;
    }

    if (tableContainer) tableContainer.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (batchToolbar) batchToolbar.style.display = 'flex';

    tbody.innerHTML = otherDevices.map(device => {
        const iconClass = getDeviceIconClass(device.os, device.device_info);
        const deviceTypeName = getDeviceTypeName(device.os, device.device_info);
        const statusClass = (device.status || 'Active').toLowerCase() === 'active' ? 'active' : 'logged-out';
        const statusText = device.status || 'Active';
        const locationLabel = formatLocationDisplay(device.location || sessionStorage.getItem('device_location'));

        return `
            <tr data-id="${device.id}">
                <td data-label="Select">
                    <input type="checkbox" class="device-checkbox" data-id="${device.id}" data-name="${deviceTypeName}">
                </td>
                <td data-label="Device & Browser">
                    <div class="device-row-info">
                        <div class="device-row-icon">
                            <i class="${iconClass}"></i>
                        </div>
                        <div>
                            <div class="device-row-title">${deviceTypeName}</div>
                            <div class="device-row-subtitle">${device.browser || ''} • ${device.os || ''}</div>
                        </div>
                    </div>
                </td>
                <td data-label="Location & IP">
                    <div><strong>${locationLabel}</strong></div>
                    <div class="device-row-subtitle">${device.ip_address || '-'}</div>
                </td>
                <td data-label="Login Time">
                    <div>${device.formatted_login_time || device.login_time || '-'}</div>
                </td>
                <td data-label="Status">
                    <span class="status-badge ${statusClass}">
                        <i class="fas fa-circle" style="font-size: 6px;"></i> ${statusText}
                    </span>
                </td>
                <td data-label="Action" style="text-align: right;">
                    <button class="btn-device-logout" data-id="${device.id}" data-name="${deviceTypeName}">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Attach row events
    const checkboxes = tbody.querySelectorAll(".device-checkbox");
    checkboxes.forEach(cb => {
        cb.addEventListener("change", updateBatchToolbar);
    });

    const logoutBtns = tbody.querySelectorAll(".btn-device-logout");
    logoutBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const devId = btn.getAttribute("data-id");
            const devName = btn.getAttribute("data-name");
            openDeviceLogoutModal({
                mode: 'single',
                ids: [devId],
                title: 'Confirm Device Logout',
                message: `Are you sure you want to log out this device? The device session will be ended and info removed.`,
                preview: `${devName || 'Selected Device'} (ID: ${devId})`
            });
        });
    });
}

// Checkbox Batch Selection Handler
function updateBatchToolbar() {
    const checkboxes = document.querySelectorAll(".device-checkbox");
    const checked = document.querySelectorAll(".device-checkbox:checked");
    const selectAllCheck = document.getElementById("selectAllDevices");
    const selectedBadge = document.getElementById("selectedCountBadge");
    const logoutSelectedBtn = document.getElementById("logoutSelectedBtn");

    const count = checked.length;

    if (selectedBadge) {
        selectedBadge.textContent = `${count} selected`;
        selectedBadge.style.display = count > 0 ? 'inline-block' : 'none';
    }

    if (logoutSelectedBtn) {
        logoutSelectedBtn.style.display = count > 0 ? 'inline-flex' : 'none';
    }

    if (selectAllCheck && checkboxes.length > 0) {
        selectAllCheck.checked = checkboxes.length === count;
    }
}

// Select All Listener
const selectAllCheck = document.getElementById("selectAllDevices");
if (selectAllCheck) {
    selectAllCheck.addEventListener("change", function() {
        const checkboxes = document.querySelectorAll(".device-checkbox");
        checkboxes.forEach(cb => cb.checked = this.checked);
        updateBatchToolbar();
    });
}

// ================= MODAL & EVENT LISTENERS =================
function initModalEvents() {
    const deviceLogoutModal = document.getElementById("deviceLogoutModal");
    const btnCancel = document.getElementById("btnCancelDeviceLogout");
    const btnConfirm = document.getElementById("btnConfirmDeviceLogout");

    const logoutAllBtn = document.getElementById("logoutAllDevicesBtn");
    const logoutSelectedBtn = document.getElementById("logoutSelectedBtn");

    if (btnCancel && deviceLogoutModal) {
        btnCancel.addEventListener("click", () => {
            deviceLogoutModal.classList.remove("show");
        });
    }

    if (logoutAllBtn) {
        logoutAllBtn.addEventListener("click", () => {
            openDeviceLogoutModal({
                mode: 'all',
                ids: [],
                includeCurrent: true,
                title: 'Confirm Logout All Devices',
                message: 'Are you sure you want to log out ALL devices? This will end every active session, including your current one.',
                preview: 'All Logged-in Devices'
            });
        });
    }

    if (logoutSelectedBtn) {
        logoutSelectedBtn.addEventListener("click", () => {
            const checked = document.querySelectorAll(".device-checkbox:checked");
            const ids = Array.from(checked).map(cb => cb.getAttribute("data-id"));
            if (ids.length === 0) return;

            openDeviceLogoutModal({
                mode: 'selected',
                ids: ids,
                title: 'Logout Selected Devices',
                message: `Are you sure you want to log out the ${ids.length} selected device(s)?`,
                preview: `${ids.length} Selected Device(s)`
            });
        });
    }

    if (btnConfirm) {
        btnConfirm.addEventListener("click", handleModalConfirmLogout);
    }
}

function openDeviceLogoutModal({ mode, ids, title, message, preview, includeCurrent = false }) {
    pendingLogoutAction = { mode, ids, includeCurrent };

    const modal = document.getElementById("deviceLogoutModal");
    const titleEl = document.getElementById("modalLogoutTitle");
    const msgEl = document.getElementById("modalLogoutMessage");
    const previewEl = document.getElementById("modalDeviceText");

    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;
    if (previewEl) previewEl.textContent = preview;

    if (modal) modal.classList.add("show");
}

async function handleModalConfirmLogout() {
    const modal = document.getElementById("deviceLogoutModal");
    if (modal) modal.classList.remove("show");

    showToast("Processing logout request...", "loading");

    try {
        let endpoint = "/api/user/login-history/logout";
        let payload = {};

        if (pendingLogoutAction.mode === 'all') {
            endpoint = "/api/user/login-history/logout-all";
            payload = {
                tab_id: currentTabId,
                include_current: pendingLogoutAction.includeCurrent
            };
        } else {
            payload = {
                device_ids: pendingLogoutAction.ids,
                tab_id: currentTabId
            };
        }

        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (!res.ok || !data.success) {
            showToast(data.error || "Failed to log out device(s)", "error");
            return;
        }

        showToast(data.message || "Logged out successfully!", "success");

        if (data.logout_current) {
            setTimeout(() => {
                sessionStorage.clear();
                localStorage.clear();
                window.location.replace('/');
            }, 1000);
        } else {
            setTimeout(() => {
                loadLoginHistory();
            }, 500);
        }

    } catch (err) {
        console.error("Logout execution error:", err);
        showToast("Network error executing device logout", "error");
    }
}
