// ==================== USER NOTIFICATION SYSTEM (XAMPP/MYSQL VERSION) ====================

let userNotifications = [];
let userNotificationInterval = null;

// Configuration
const USER_NOTIFICATION_API_BASE = '/api/user/notifications';
const USER_POLLING_INTERVAL = 10000; // 10 seconds

// Get current user ID from localStorage or session
let currentUserId = localStorage.getItem('user_id') || sessionStorage.getItem('user_id');
let currentTabId = sessionStorage.getItem('tab_id');

// Function to fetch and set user ID from profile if not available
async function fetchAndSetUserId() {
    if (currentUserId) return currentUserId;
    
    try {
        const tabId = sessionStorage.getItem('tab_id');
        const response = await fetch('/api/get-user-profile?tab_id=' + tabId);
        if (response.ok) {
            const profile = await response.json();
            currentUserId = profile.user_id || profile.id || profile.userId;
            
            if (currentUserId) {
                localStorage.setItem('user_id', currentUserId);
                sessionStorage.setItem('user_id', currentUserId);
                console.log('User ID set from profile:', currentUserId);
            } else {
                console.error('No user_id found in profile response:', profile);
            }
        }
    } catch (err) {
        console.error('Error fetching user profile for ID:', err);
    }
    return currentUserId;
}

// ==================== API CALLS ====================

// Fetch notifications for current user
async function fetchUserNotifications() {
    if (!currentUserId) {
        console.log('No user ID found, attempting to fetch...');
        await fetchAndSetUserId();
        if (!currentUserId) return [];
    }
    
    try {
        const tabId = sessionStorage.getItem('tab_id');
        const response = await fetch(`${USER_NOTIFICATION_API_BASE}?user_id=${encodeURIComponent(currentUserId)}&tab_id=${tabId}`);
        if (response.ok) {
            userNotifications = await response.json();
            console.log('Fetched notifications:', userNotifications.length);
            updateUserNotificationBadge();
            renderUserNotificationList();
            return userNotifications;
        } else {
            console.error('Failed to fetch notifications:', response.status);
        }
    } catch (err) {
        console.error('Error fetching user notifications:', err);
    }
    return [];
}

// Mark notification as read
async function markUserNotificationAsRead(notificationId) {
    try {
        const tabId = sessionStorage.getItem('tab_id');
        const response = await fetch(`${USER_NOTIFICATION_API_BASE}/${notificationId}/read?tab_id=${tabId}`, {
            method: 'PUT'
        });
        if (response.ok) {
            const notification = userNotifications.find(n => n.id == notificationId);
            if (notification) {
                notification.read = true;
                updateUserNotificationBadge();
                renderUserNotificationList();
            }
            return true;
        }
    } catch (err) {
        console.error('Error marking notification as read:', err);
    }
    return false;
}

// Mark all as read
async function markAllUserNotificationsAsRead() {
    if (!currentUserId) return false;
    
    try {
        const tabId = sessionStorage.getItem('tab_id');
        const response = await fetch(`${USER_NOTIFICATION_API_BASE}/read-all?user_id=${encodeURIComponent(currentUserId)}&tab_id=${tabId}`, {
            method: 'PUT'
        });
        if (response.ok) {
            const data = await response.json();
            userNotifications.forEach(n => n.read = true);
            updateUserNotificationBadge();
            renderUserNotificationList();
            console.log(`Marked ${data.count || userNotifications.length} notifications as read`);
            return true;
        }
    } catch (err) {
        console.error('Error marking all as read:', err);
    }
    return false;
}

// ==================== UI FUNCTIONS ====================

// Update notification badge
function updateUserNotificationBadge() {
    const badge = document.getElementById('userNotificationBadge');
    if (!badge) return;
    
    const unreadCount = userNotifications.filter(n => !n.read).length;
    if (unreadCount > 0) {
        badge.style.display = 'flex';
        badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
    } else {
        badge.style.display = 'none';
    }
}

// Helper function to get time ago
function getUserTimeAgo(timestamp) {
    if (!timestamp) return 'Unknown';
    try {
        const seconds = Math.floor((new Date() - new Date(timestamp)) / 1000);
        if (seconds < 60) return 'Just now';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        const days = Math.floor(hours / 24);
        if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;
        return new Date(timestamp).toLocaleDateString();
    } catch(e) {
        return 'Unknown';
    }
}

// Get notification icon based on type - NO COLORS
function getUserNotificationIcon(type) {
    switch (type) {
        case 'plan_change_approved':
            return '<i class="fas fa-check-circle"></i>';
        case 'plan_change_rejected':
            return '<i class="fas fa-times-circle"></i>';
        case 'plan_change_request':
            return '<i class="fas fa-exchange-alt"></i>';
        case 'connection_activated':
            return '<i class="fas fa-wifi"></i>';
        case 'connection_deactivated':
            return '<i class="fas fa-wifi-slash"></i>';
        case 'account_activated':
            return '<i class="fas fa-user-check"></i>';
        case 'account_deactivated':
            return '<i class="fas fa-user-slash"></i>';
        case 'request_approved':
            return '<i class="fas fa-thumbs-up"></i>';
        case 'request_rejected':
            return '<i class="fas fa-thumbs-down"></i>';
        case 'termination_approved':
            return '<i class="fas fa-trash-alt"></i>';
        case 'termination_rejected':
            return '<i class="fas fa-ban"></i>';
        default:
            return '<i class="fas fa-bell"></i>';
    }
}

// Get notification icon class
function getUserNotificationIconClass(type) {
    switch (type) {
        case 'plan_change_approved':
            return 'plan_change_approved';
        case 'plan_change_rejected':
            return 'plan_change_rejected';
        case 'plan_change_request':
            return 'plan_change_request';
        case 'connection_activated':
            return 'connection_activated';
        case 'connection_deactivated':
            return 'connection_deactivated';
        case 'account_activated':
            return 'account_activated';
        case 'account_deactivated':
            return 'account_deactivated';
        case 'request_approved':
            return 'request_approved';
        case 'request_rejected':
            return 'request_rejected';
        case 'termination_approved':
            return 'termination_approved';
        case 'termination_rejected':
            return 'termination_rejected';
        default:
            return 'default';
    }
}

// Escape HTML helper
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Determine target URL based on notification type - PURELY IN JS
function getNotificationTargetUrl(notification) {
    const tabId = sessionStorage.getItem('tab_id') || '';
    const baseUrl = tabId ? `/user/dashboard?tab_id=${tabId}` : '/user/dashboard';
    
    // Plan change related notifications
    const planChangeTypes = [
        'plan_change_approved',
        'plan_change_rejected', 
        'plan_change_request'
    ];
    
    if (planChangeTypes.includes(notification.type)) {
        return tabId ? `/user/change-plan?tab_id=${tabId}` : '/user/change-plan';
    }
    
    // All other notifications go to dashboard
    return baseUrl;
}

// Render notification list with click navigation
function renderUserNotificationList() {
    const container = document.getElementById('userNotificationList');
    if (!container) {
        console.log('Notification list container not found');
        return;
    }
    
    if (userNotifications.length === 0) {
        container.innerHTML = `
            <div class="notification-empty">
                <i class="fas fa-bell-slash"></i>
                <p>No notifications</p>
                <small>You'll see notifications here when your connection status changes</small>
            </div>
        `;
        return;
    }
    
    container.innerHTML = userNotifications.map(notification => {
        const iconHtml = getUserNotificationIcon(notification.type);
        const iconClass = getUserNotificationIconClass(notification.type);
        const timeAgo = getUserTimeAgo(notification.timestamp);
        const unreadClass = notification.read ? '' : 'unread';
        const targetUrl = getNotificationTargetUrl(notification); // 👈 DETERMINE URL IN JS
        
        return `
            <div class="notification-item ${unreadClass}" 
                 data-id="${notification.id}" 
                 data-url="${targetUrl}">
                <div class="notification-icon ${iconClass}">
                    ${iconHtml}
                </div>
                <div class="notification-content">
                    <div class="notification-title">${escapeHtml(notification.title)}</div>
                    <div class="notification-message">${escapeHtml(notification.message)}</div>
                    <div class="notification-time">${timeAgo}</div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers with navigation
    document.querySelectorAll('#userNotificationList .notification-item').forEach(item => {
        const newItem = item.cloneNode(true);
        item.parentNode.replaceChild(newItem, item);
        
        newItem.addEventListener('click', async (e) => {
            e.stopPropagation();
            const id = parseInt(newItem.dataset.id);
            const targetUrl = newItem.dataset.url;
            
            console.log('Notification clicked:', id, 'Target URL:', targetUrl);
            
            // Mark as read first
            await markUserNotificationAsRead(id);
            
            // Close notification menu
            const menu = document.getElementById('userNotificationMenu');
            if (menu) menu.classList.remove('show');
            
            // Navigate to target URL after short delay
            if (targetUrl) {
                setTimeout(() => {
                    window.location.href = targetUrl;
                }, 300);
            }
        });
    });
}

// ==================== AUTO-INJECT "VIEW ALL" UI ====================
// ✅ Awtomatikong ginagawa ang button + modal sa runtime - hindi na
// kailangang i-edit ang HTML ng bawat page. Basta't may #userNotificationMenu
// sa page (standard structure sa lahat ng user pages), gagana ito.

function injectAllUserNotificationsUI() {
    const notificationMenu = document.getElementById('userNotificationMenu');
    if (!notificationMenu) return; // walang notification dropdown sa page na ito

    // ✅ 1. I-inject ang "View All Notifications" button sa ilalim ng dropdown
    if (!document.getElementById('viewAllUserNotificationsBtn')) {
        const footer = document.createElement('div');
        footer.className = 'notification-footer';
        footer.innerHTML = `
            <button id="viewAllUserNotificationsBtn" class="view-all-btn">
                <i class="fas fa-list"></i> View All Notifications
            </button>
        `;
        notificationMenu.appendChild(footer);
    }

    // ✅ 2. I-inject ang buong "All Notifications" modal sa dulo ng <body>
    if (!document.getElementById('allUserNotificationsModal')) {
        const modal = document.createElement('div');
        modal.id = 'allUserNotificationsModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content all-notifications-modal-content">
                <div class="modal-header">
                    <h3><i class="fas fa-bell"></i> All Notifications</h3>
                    <button class="close-modal" id="closeAllUserNotificationsModal">&times;</button>
                </div>
                <div class="modal-body" style="padding: 0;">
                    <div id="allUserNotificationsList" class="all-notifications-list">
                        <div class="notification-empty">
                            <i class="fas fa-bell-slash"></i>
                            <p>No notifications</p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="justify-content: center;">
                    <button id="markAllReadFromUserModalBtn" class="btn-cancel">
                        <i class="fas fa-check"></i> Mark all as read
                    </button>
                    <button id="closeAllUserNotificationsBtn" class="btn-confirm">
                        <i class="fas fa-times"></i> Close
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
}

// Render FULL list ng notifications sa "View All" modal
function renderAllUserNotificationsList() {
    const container = document.getElementById('allUserNotificationsList');
    if (!container) return;

    if (userNotifications.length === 0) {
        container.innerHTML = `
            <div class="notification-empty">
                <i class="fas fa-bell-slash"></i>
                <p>No notifications</p>
                <small>You'll see notifications here when your connection status changes</small>
            </div>
        `;
        return;
    }

    container.innerHTML = userNotifications.map(notification => {
        const iconHtml = getUserNotificationIcon(notification.type);
        const iconClass = getUserNotificationIconClass(notification.type);
        const timeAgo = getUserTimeAgo(notification.timestamp);
        const unreadClass = notification.read ? '' : 'unread';
        const targetUrl = getNotificationTargetUrl(notification);

        return `
            <div class="notification-item ${unreadClass}" data-id="${notification.id}" data-url="${targetUrl}">
                <div class="notification-icon ${iconClass}">
                    ${iconHtml}
                </div>
                <div class="notification-content">
                    <div class="notification-title">${escapeHtml(notification.title)}</div>
                    <div class="notification-message">${escapeHtml(notification.message)}</div>
                    <div class="notification-time">${timeAgo}</div>
                </div>
            </div>
        `;
    }).join('');

    container.querySelectorAll('.notification-item').forEach(item => {
        item.addEventListener('click', async () => {
            const id = parseInt(item.dataset.id);
            const targetUrl = item.dataset.url;

            await markUserNotificationAsRead(id);
            renderAllUserNotificationsList();

            if (targetUrl) {
                setTimeout(() => {
                    window.location.href = targetUrl;
                }, 300);
            }
        });
    });
}

// Buksan ang "View All Notifications" modal
async function openAllUserNotificationsModal() {
    await fetchUserNotifications();
    renderAllUserNotificationsList();

    const modal = document.getElementById('allUserNotificationsModal');
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

// Isara ang "View All Notifications" modal
function closeAllUserNotificationsModal() {
    const modal = document.getElementById('allUserNotificationsModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// ==================== INITIALIZATION ====================

// Initialize user notification system
async function initUserNotifications() {
    console.log('Initializing user notification system...');

    // ✅ I-inject muna ang "View All" button + modal bago i-attach ang events
    injectAllUserNotificationsUI();
    
    // First try to get user ID from storage
    currentUserId = localStorage.getItem('user_id') || sessionStorage.getItem('user_id');
    currentTabId = sessionStorage.getItem('tab_id');
    
    // If not found, fetch from profile
    if (!currentUserId) {
        await fetchAndSetUserId();
    }
    
    if (!currentUserId) {
        console.error('Cannot initialize notifications: No user ID found');
        return;
    }
    
    console.log('Initializing notifications for user:', currentUserId);
    console.log('Tab ID:', currentTabId);
    
    // Fetch notifications
    await fetchUserNotifications();
    
    // Setup event listeners
    const notificationBtn = document.getElementById('userNotificationBtn');
    const notificationMenu = document.getElementById('userNotificationMenu');
    
    if (notificationBtn && notificationMenu) {
        // Remove existing listeners
        const newBtn = notificationBtn.cloneNode(true);
        notificationBtn.parentNode.replaceChild(newBtn, notificationBtn);
        
        newBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Notification bell clicked');
            notificationMenu.classList.toggle('show');
            if (notificationMenu.classList.contains('show')) {
                fetchUserNotifications();
            }
        });
        
        // Close when clicking outside
        document.addEventListener('click', (e) => {
            if (!newBtn.contains(e.target) && !notificationMenu.contains(e.target)) {
                notificationMenu.classList.remove('show');
            }
        });
    } else {
        console.log('Notification button or menu not found in DOM');
    }
    
    const markAllReadBtn = document.getElementById('userMarkAllReadBtn');
    if (markAllReadBtn) {
        const newMarkBtn = markAllReadBtn.cloneNode(true);
        markAllReadBtn.parentNode.replaceChild(newMarkBtn, markAllReadBtn);
        newMarkBtn.addEventListener('click', () => {
            markAllUserNotificationsAsRead();
        });
    }

    // ✅ VIEW ALL NOTIFICATIONS BUTTON
    const viewAllBtn = document.getElementById('viewAllUserNotificationsBtn');
    if (viewAllBtn) {
        const newViewAllBtn = viewAllBtn.cloneNode(true);
        viewAllBtn.parentNode.replaceChild(newViewAllBtn, viewAllBtn);

        newViewAllBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (notificationMenu) notificationMenu.classList.remove('show');
            openAllUserNotificationsModal();
        });
    }

    // ✅ ALL NOTIFICATIONS MODAL - CLOSE HANDLERS
    const allModal = document.getElementById('allUserNotificationsModal');
    const closeAllModalBtn = document.getElementById('closeAllUserNotificationsModal');
    const closeAllBtn = document.getElementById('closeAllUserNotificationsBtn');
    const markAllReadFromModalBtn = document.getElementById('markAllReadFromUserModalBtn');

    if (closeAllModalBtn) {
        closeAllModalBtn.addEventListener('click', closeAllUserNotificationsModal);
    }
    if (closeAllBtn) {
        closeAllBtn.addEventListener('click', closeAllUserNotificationsModal);
    }
    if (allModal) {
        allModal.addEventListener('click', (e) => {
            if (e.target === allModal) closeAllUserNotificationsModal();
        });
    }
    if (markAllReadFromModalBtn) {
        markAllReadFromModalBtn.addEventListener('click', async () => {
            await markAllUserNotificationsAsRead();
            renderAllUserNotificationsList();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('allUserNotificationsModal');
            if (modal && modal.classList.contains('show')) {
                closeAllUserNotificationsModal();
            }
        }
    });
    
    // Start polling
    if (userNotificationInterval) clearInterval(userNotificationInterval);
    userNotificationInterval = setInterval(() => {
        fetchUserNotifications();
    }, USER_POLLING_INTERVAL);
    
    console.log('User notification system initialized');
}

// Stop polling
function stopUserNotifications() {
    if (userNotificationInterval) {
        clearInterval(userNotificationInterval);
        userNotificationInterval = null;
    }
}

// Make functions globally available
window.UserNotificationSystem = {
    init: initUserNotifications,
    stop: stopUserNotifications,
    openAllModal: openAllUserNotificationsModal,
    closeAllModal: closeAllUserNotificationsModal,
    fetch: fetchUserNotifications,
    markAsRead: markUserNotificationAsRead,
    markAllAsRead: markAllUserNotificationsAsRead,
    getNotifications: () => userNotifications,
    getUnreadCount: () => userNotifications.filter(n => !n.read).length
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in
    const isLoggedIn = sessionStorage.getItem('username') && sessionStorage.getItem('userType') === 'user';
    if (isLoggedIn) {
        setTimeout(() => {
            initUserNotifications();
        }, 1000);
    }
});