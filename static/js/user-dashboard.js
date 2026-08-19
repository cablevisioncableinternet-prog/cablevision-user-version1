
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

        // Inject keyframes + spin once
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

    // Build inner HTML
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

    // Reset class, force reflow, then show
    toast.className = `custom-toast ${type}`;
    void toast.offsetWidth;
    toast.classList.add('show');

    // Clear any existing hide timer
    clearTimeout(toast._hideTimer);

    if (type === 'loading') {
        // Loading stays visible until next showToast call — no auto-hide
        // Progress bar uses the infinite sweep animation (set in CSS)
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

// ================= LOAD PROFILE AND STORE USER ID =================
async function loadProfile() {
  try {
    const res = await fetch("/api/get-user-profile");
    if (!res.ok) throw new Error("Failed to fetch profile");
    const profile = await res.json();

    const userId = profile.user_id || profile.id;
    if (userId) {
      localStorage.setItem('user_id', userId);
      sessionStorage.setItem('user_id', userId);
      console.log('✅ User ID stored:', userId);
      
      if (window.UserNotificationSystem) {
        console.log('Initializing UserNotificationSystem...');
        window.UserNotificationSystem.init();
      } else {
        console.error('UserNotificationSystem not found!');
      }
    } else {
      console.warn('⚠ No user_id found in profile response:', profile);
    }

    // Display profile name
    const profileNameSpan = document.getElementById("");
    if (profileNameSpan) {
      const displayName = profile.first_name || profile.username || userId || "User";
      profileNameSpan.textContent = displayName;
    }

    const profileImg = document.getElementById("profileIcon");
    if (profile.profile_photo && profile.profile_photo !== 'none') {
      profileImg.src = profile.profile_photo;
    } else {
      profileImg.src = "/static/profile.jpg";
    }
  } catch (err) {
    console.error("Error loading profile:", err);
  }
}

loadProfile();

// ================= LOGOUT MODAL WITH CLEAR STORAGE =================
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
        // 👇 KUHAIN ANG TAB ID BAGO MAG-LOGOUT
        const tabId = sessionStorage.getItem('tab_id');
        
        // 👇 SEND LOGOUT REQUEST WITH TAB ID
        await fetch('/api/logout', { 
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tab_id: tabId })
        }).catch(() => {});
      } catch(e) {}
      
      // 👇 I-CLEAR ANG STORAGE
      localStorage.removeItem('user_id');
      sessionStorage.clear();
      
      // 👇 REDIRECT SA LOGIN PAGE
      window.location.replace('/');
    });
  }
  
  window.addEventListener("click", e => { 
    if (e.target === logoutModal) closeModal(); 
  });
}

// ================= DATE & TIME =================
function updateDateTime(){
  const now = new Date();
  const days = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  const day = days[now.getDay()];
  const date = now.toLocaleDateString('en-US', { year:'numeric', month:'long', day:'numeric' });
  const time = now.toLocaleTimeString();
  
  const dayEl = document.getElementById("currentDay");
  const dateEl = document.getElementById("currentDate");
  const timeEl = document.getElementById("liveTime");
  
  if (dayEl) dayEl.textContent = day;
  if (dateEl) dateEl.textContent = date;
  if (timeEl) timeEl.textContent = time;
}
setInterval(updateDateTime,1000);
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

// ================= GET TIME AGO TEXT =================
function getTimeAgoText(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
}

// ================= IMAGE PREVIEW MODAL =================
function openImagePreviewModal(imgSrc) {
    const modal = document.getElementById('imagePreviewModal');
    const previewImg = document.getElementById('previewImage');
    
    if (previewImg) previewImg.src = imgSrc;
    if (modal) modal.style.display = 'flex';
}

function closeImagePreview() {
    const modal = document.getElementById('imagePreviewModal');
    if (modal) modal.style.display = 'none';
}

// ================= HAMBURGER MENU TOGGLE =================
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

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && sidebar && sidebar.classList.contains('active')) {
    toggleSidebar();
  }
});

// ================= LOAD CUSTOMER TABLE (CONNECTION DETAILS) =================
async function loadCustomerTable() {
  const tbody = document.getElementById("customersTableBody");
  const balanceCardContainer = document.getElementById("balanceCardContainer");
  
  if (!tbody) return;
  
  tbody.innerHTML = `<tr><td colspan="6" class="no-data">Loading...</td></tr>`;

  try {
    const res = await fetch("/api/get-user-connection");
    if (!res.ok) throw new Error("Failed to fetch data");

    const data = await res.json();

    // 🔥 I-CHECK KUNG MAY BALANCE AT INACTIVE ANG STATUS
    if (data && data.length > 0) {
      const user = data[0];
      const balance = user.balance || 0;
      const status = user.status || "Active";
      
      if ((status.toLowerCase() === "inactive" || status.toLowerCase() === "terminated") && balance > 0) {
            showBalanceCard(balance, status);
        } else {
            // I-HIDE ANG CARD KUNG WALANG BALANCE O ACTIVE
            hideBalanceCard();
        }
    }

    if (!data || data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="no-data">No data found</td></tr>`;
      return;
    }

    tbody.innerHTML = "";

    data.forEach(user => {
      const fullName = [
        user.firstname,
        user.middlename || "",
        user.lastname,
        user.suffix || ""
      ].join(" ").replace(/\s+/g, " ").trim() || "N/A";

      const status = user.status || "Pending";
      
      let statusClass = "pending";
      if (status.toLowerCase() === "active") statusClass = "active";
      else if (status.toLowerCase() === "pending approval") statusClass = "pending";
      else if (status.toLowerCase() === "installation pending") statusClass = "warning";
      else if (status.toLowerCase() === "installation ongoing") statusClass = "warning";
      else if (status.toLowerCase() === "inactive") statusClass = "inactive";
      else if (status.toLowerCase() === "rejected") statusClass = "rejected";

      const connectionStatus = user.connection_status || "Disconnected";
      let connectionClass = "disconnected";
      if (connectionStatus.toLowerCase() === "connected") connectionClass = "connected";

      const contractNumber = user.contract_number || "N/A";

      const tr = document.createElement("tr");

      tr.innerHTML = `
        <td>${escapeHtml(fullName)}</td>
        <td>${escapeHtml(user.plan_name || 'N/A')}</td>
        <td>${escapeHtml(user.mbps || '0')} Mbps</td>
        <td><span class="contract-number-badge"><i class="fas fa-file-contract"></i> ${escapeHtml(contractNumber)}</span></td>
        <td><span class="status ${statusClass}">${escapeHtml(status)}</span></td>
        <td><span class="status ${connectionClass}">${escapeHtml(connectionStatus)}</span></td>
      `;

      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Error loading customer table:", err);
    tbody.innerHTML = `<tr><td colspan="6" class="no-data">Failed to load data</td></tr>`;
  }
}

// ================= SHOW BALANCE CARD =================
function showBalanceCard(balance, status = 'Inactive') {
  // I-REMOVE ANG EXISTING CARD
  hideBalanceCard();
  
  // I-CREATE ANG CARD
  const card = document.createElement('div');
  card.id = 'balanceCard';
  card.className = 'balance-card';
  
  // 🔥 IBAHIN ANG KULAY BATAY SA STATUS
  const isTerminated = status.toLowerCase() === 'terminated';
  const bgColor = isTerminated ? 'linear-gradient(135deg, #fef2f2, #fee2e2)' : 'linear-gradient(135deg, #fef2f2, #fee2e2)';
  const borderColor = isTerminated ? '#fecaca' : '#fecaca';
  const titleColor = isTerminated ? '#991b1b' : '#991b1b';
  const textColor = isTerminated ? '#7f1d1d' : '#7f1d1d';
  const iconColor = isTerminated ? '#dc2626' : '#dc2626';
  
  card.style.cssText = `
    background: ${bgColor};
    border: 2px solid ${borderColor};
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
    box-shadow: 0 4px 12px rgba(220, 38, 38, 0.1);
    animation: slideInDown 0.5s ease;
  `;
  
  // 🔥 IBAHIN ANG MESSAGE BATAY SA STATUS
  let statusMessage = '';
  if (isTerminated) {
    statusMessage = `Your account is currently <strong>Terminated</strong>. Please visit our office to settle your outstanding balance or you may pay via GCash. Once payment is confirmed, your account will be reactivated.`;
  } else {
    statusMessage = `Your account is currently <strong>Inactive</strong>. Please visit our office to settle your outstanding balance or you may pay via GCash. Once payment is confirmed, your account will be reactivated.`;
  }
  
  card.innerHTML = `
    <div style="display: flex; align-items: center; gap: 16px;">
      <div style="
        background: #dc2626;
        color: white;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        flex-shrink: 0;
      ">
        <i class="fas fa-exclamation-triangle"></i>
      </div>
      <div>
        <h3 style="margin: 0; font-size: 16px; font-weight: 700; color: ${titleColor};">
          Outstanding Balance: ₱${balance.toFixed(2)}
        </h3>
        <p style="margin: 4px 0 0 0; font-size: 14px; color: ${textColor}; line-height: 1.5;">
          <i class="fas fa-info-circle" style="color: ${iconColor};"></i> 
          ${statusMessage}
          <br><br>
          
        </p>
      </div>
    </div>
    <div style="display: flex; gap: 12px; flex-shrink: 0;">
      <div style="
        background: #dc2626;
        color: white;
        padding: 8px 16px;
        border-radius: 30px;
        font-size: 14px;
        font-weight: 600;
        text-align: center;
      ">
        <i class="fas fa-credit-card"></i> ₱${balance.toFixed(2)}
      </div>
    </div>
  `;
  
  // I-INSERT ANG CARD BAGO ANG TABLE
  const customersSection = document.querySelector('.customers-section');
  if (customersSection) {
    const tableContainer = customersSection.querySelector('.table-container');
    if (tableContainer) {
      customersSection.insertBefore(card, tableContainer);
    } else {
      customersSection.appendChild(card);
    }
  }
  
  // MAG-ADD NG ANIMATION STYLE KUNG WALA PA
  if (!document.getElementById('balanceCardStyles')) {
    const style = document.createElement('style');
    style.id = 'balanceCardStyles';
    style.textContent = `
      @keyframes slideInDown {
        from {
          opacity: 0;
          transform: translateY(-20px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      
      .balance-card {
        animation: slideInDown 0.5s ease;
      }
    `;
    document.head.appendChild(style);
  }
}

// ================= HIDE BALANCE CARD =================
function hideBalanceCard() {
  const existingCard = document.getElementById('balanceCard');
  if (existingCard) {
    existingCard.remove();
  }
}

// ================= TWO COLUMN ANNOUNCEMENTS =================
async function loadTwoColumnAnnouncements() {
    const noImageContainer = document.getElementById("noImageAnnouncements");
    const withImageContainer = document.getElementById("withImageAnnouncements");
    
    if (!noImageContainer || !withImageContainer) return;
    
    noImageContainer.innerHTML = `<div class="loading-text">Loading announcements...</div>`;
    withImageContainer.innerHTML = `<div class="loading-text">Loading announcements...</div>`;
    
    try {
        const res = await fetch("/api/get-announcements");
        if (!res.ok) throw new Error("Failed to fetch announcements");
        let announcements = await res.json();
        
        // Filter out expired announcements
        const currentTime = new Date();
        const activeAnnouncements = announcements.filter(a => {
            if (!a.expirationDate) return true;
            return new Date(a.expirationDate) > currentTime;
        });
        
        // Separate: Walang image vs May image
        const noImageAnnouncements = activeAnnouncements.filter(a => !a.imageBase64 && !a.image_path);
        const withImageAnnouncements = activeAnnouncements.filter(a => a.imageBase64 || a.image_path);
        
        // Render both columns
        renderNoImageColumn(noImageAnnouncements);
        renderWithImageColumn(withImageAnnouncements);
        
    } catch (err) {
        console.error("Error loading announcements:", err);
        noImageContainer.innerHTML = `<div class="empty-state-simple"><i class="fas fa-exclamation-circle"></i><p>Failed to load announcements</p></div>`;
        withImageContainer.innerHTML = `<div class="empty-state-simple"><i class="fas fa-exclamation-circle"></i><p>Failed to load announcements</p></div>`;
    }
}

// Render LEFT column (No Image)
function renderNoImageColumn(announcements) {
    const container = document.getElementById("noImageAnnouncements");
    
    if (announcements.length === 0) {
        container.innerHTML = `<div class="empty-state-simple"><i class="fas fa-newspaper"></i><p>No announcements at this time</p></div>`;
        return;
    }
    
    let html = '';
    announcements.forEach(a => {
        const announcementDate = new Date(a.timestamp * 1000);
        const now = new Date();
        const hoursDiff = (now - announcementDate) / (1000 * 60 * 60);
        const isNew = hoursDiff < 24;
        const badgeClass = isNew ? 'new' : 'recent';
        const badgeText = isNew ? 'NEW' : 'RECENT';
        const timeAgo = getTimeAgoText(announcementDate);
        
        const hasTitle = a.title && a.title.trim() !== '';
        const hasMessage = a.message && a.message.trim() !== '';
        const hasImage = (a.imageBase64 && a.imageBase64 !== '') || (a.image_path && a.image_path !== '');
        
        // Skip image-only for this column
        if (!hasTitle && !hasMessage && hasImage) {
            return;
        }
        
        html += `
            <div class="announcement-card-simple">
                <span class="announcement-badge-simple ${badgeClass}">${badgeText}</span>
                ${hasTitle ? `<div class="announcement-title-simple">${escapeHtml(a.title)}</div>` : ''}
                ${hasMessage ? `<div class="announcement-message-simple">${escapeHtml(a.message)}</div>` : ''}
                <div class="announcement-date-simple"><i class="fas fa-calendar-alt"></i> ${timeAgo}</div>
            </div>
        `;
    });
    
    if (html === '') {
        container.innerHTML = `<div class="empty-state-simple"><i class="fas fa-newspaper"></i><p>No announcements at this time</p></div>`;
    } else {
        container.innerHTML = html;
    }
}

// Render RIGHT column (With Image)
function renderWithImageColumn(announcements) {
    const container = document.getElementById("withImageAnnouncements");
    
    if (announcements.length === 0) {
        container.innerHTML = `<div class="empty-state-simple"><i class="fas fa-image"></i><p>No image announcements at this time</p></div>`;
        return;
    }
    
    let html = '';
    announcements.forEach(a => {
        const announcementDate = new Date(a.timestamp * 1000);
        const now = new Date();
        const hoursDiff = (now - announcementDate) / (1000 * 60 * 60);
        const isNew = hoursDiff < 24;
        const badgeClass = isNew ? 'new' : 'recent';
        const badgeText = isNew ? 'NEW' : 'RECENT';
        const timeAgo = getTimeAgoText(announcementDate);
        
        const hasTitle = a.title && a.title.trim() !== '';
        const hasMessage = a.message && a.message.trim() !== '';
        const imageUrl = a.imageBase64 || a.image_path;
        const hasImage = imageUrl && imageUrl !== '';
        
        // Only image without text
        const isImageOnly = !hasTitle && !hasMessage && hasImage;
        
        html += `
            <div class="announcement-card-simple">
                <span class="announcement-badge-simple ${badgeClass}">${badgeText}</span>
                ${!isImageOnly && hasTitle ? `<div class="announcement-title-simple">${escapeHtml(a.title)}</div>` : ''}
                ${!isImageOnly && hasMessage ? `<div class="announcement-message-simple">${escapeHtml(a.message)}</div>` : ''}
                ${hasImage ? `
                    <div class="announcement-image-preview" onclick="openImagePreviewModal('${escapeHtml(imageUrl)}')">
                        <img src="${escapeHtml(imageUrl)}" alt="Announcement image">
                    </div>
                ` : ''}
                <div class="announcement-date-simple"><i class="fas fa-calendar-alt"></i> ${timeAgo}</div>
            </div>
        `;
    });
    container.innerHTML = html;
}

// ================= SETUP IMAGE PREVIEW MODAL =================
function setupImagePreviewModal() {
    const modal = document.getElementById('imagePreviewModal');
    const closeBtn = document.querySelector('.preview-close');
    
    if (closeBtn) {
        closeBtn.onclick = closeImagePreview;
    }
    
    if (modal) {
        modal.onclick = (e) => { 
            if (e.target === modal) closeImagePreview(); 
        };
    }
    
    document.addEventListener('keydown', (e) => {
        const modalEl = document.getElementById('imagePreviewModal');
        if (e.key === 'Escape' && modalEl && modalEl.style.display === 'flex') {
            closeImagePreview();
        }
    });
}

// ================= INITIALIZE ON PAGE LOAD =================
// ITO ANG UNANG DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    loadCustomerTable();
    loadTwoColumnAnnouncements();
    setupImagePreviewModal();
    checkUserStatusAndDisableFeatures();
});

// ================= USER PROFILE API (if needed) =================
// Add this route in your Flask app if not exists:
// @app.route("/api/get-user-profile")
// def get_user_profile():
//     if "user_id" not in session:
//         return jsonify({"error": "Not logged in"}), 401
//     
//     user_id = session["user_id"]
//     query = "SELECT user_id, first_name, last_name, email, profile_photo FROM users WHERE user_id = %s"
//     user = execute_query(query, (user_id,), fetch_one=True)
//     return jsonify(user or {})


// ================= CHECK USER STATUS AND DISABLE FEATURES =================
async function checkUserStatusAndDisableFeatures() {
    try {
        const response = await fetch('/api/get-user-status');
        const data = await response.json();
        const status = data.status || 'Active';
        
        // 🔥 IBAHIN ANG MESSAHE PARA SA INACTIVE AT TERMINATED
        if (status === 'Terminated' || status === 'Inactive' || status === 'Deactivated') {
            console.log(`⚠️ User status: ${status} - Disabling sidebar features only`);
            
            // ✅ 1. DISABLE SIDEBAR LINKS ONLY (Except Dashboard)
            const sidebarLinks = document.querySelectorAll('.sidebar-menu a');
            sidebarLinks.forEach(link => {
                if (!link.href.includes('/user/dashboard')) {
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
            
            // ✅ 2. DO NOT DISABLE PROFILE LINK (Keep it clickable)
            const profileLink = document.getElementById('profileLink');
            if (profileLink) {
                profileLink.style.pointerEvents = 'auto';
                profileLink.style.opacity = '1';
                profileLink.style.cursor = 'pointer';
                profileLink.title = '';
            }
            
            // ✅ 3. DO NOT DISABLE NOTIFICATION BUTTON (Keep it clickable)
            const notifBtn = document.getElementById('userNotificationBtn');
            if (notifBtn) {
                notifBtn.style.pointerEvents = 'auto';
                notifBtn.style.opacity = '1';
                notifBtn.style.cursor = 'pointer';
            }
            
            // ✅ 4. Show a banner/alert at the top - IBA ANG MESSAHE
            // 🔥 ILAGAY SA TAAS NG SECURITY SECTION (GOOGLE AUTHENTICATOR CARD)
            const securitySection = document.querySelector('.security-section');
            
            if (securitySection) {
                // Remove existing banner if any
                const existingBanner = document.querySelector('.status-banner');
                if (existingBanner) {
                    existingBanner.remove();
                }
                
                const banner = document.createElement('div');
                banner.className = 'status-banner';
                
                // 🔥 IBAHIN ANG MESSAHE BATAY SA STATUS
                let bannerTitle = '';
                let bannerMessage = '';
                let bannerIcon = '';
                let bannerColor = '';
                let bannerBg = '';
                let bannerBorder = '';
                
                if (status === 'Terminated') {
                    bannerTitle = 'Account Terminated';
                    bannerMessage = 'Your account has been permanently terminated. Please contact support for assistance. Sidebar features are disabled, but you can still view your profile and notifications.';
                    bannerIcon = 'fa-exclamation-circle';
                    bannerColor = '#dc2626';
                    bannerBg = '#fef2f2';
                    bannerBorder = '#fecaca';
                } else if (status === 'Inactive' || status === 'Deactivated') {
                    bannerTitle = 'Account Inactive';
                    bannerMessage = 'Your account is currently inactive. Please visit our office to settle your outstanding balance. Once payment is confirmed, your account will be reactivated. Sidebar features are disabled, but you can still view your profile and notifications.';
                    bannerIcon = 'fa-info-circle';
                    bannerColor = '#d97706';
                    bannerBg = '#fffbeb';
                    bannerBorder = '#fde68a';
                }
                
                banner.style.cssText = `
                    background: ${bannerBg};
                    border: 1px solid ${bannerBorder};
                    border-radius: 12px;
                    padding: 16px 20px;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    color: ${bannerColor};
                    animation: slideInDown 0.5s ease;
                `;
                
                banner.innerHTML = `
                    <i class="fas ${bannerIcon}" style="font-size: 24px; flex-shrink: 0; color: ${bannerColor};"></i>
                    <div style="flex: 1;">
                        <strong style="font-size: 16px;">${bannerTitle}</strong>
                        <p style="margin: 4px 0 0 0; font-size: 14px; color: #666;">${bannerMessage}</p>
                        <button id="requestReconnectBtn" class="reconnect-request-btn">
                            <i class="fas fa-plug"></i> Request Reconnect
                        </button>
                    </div>
                    <button onclick="this.parentElement.remove()" style="
                        background: none;
                        border: none;
                        font-size: 20px;
                        cursor: pointer;
                        color: ${bannerColor};
                        margin-left: auto;
                        padding: 0 8px;
                    ">&times;</button>
                `;
                
                // 🔥 I-INSERT ANG BANNER BAGO ANG SECURITY SECTION (Google Authenticator card)
                securitySection.parentNode.insertBefore(banner, securitySection);

                // ✅ WIRE UP RECONNECT BUTTON
                const reconnectBtn = document.getElementById('requestReconnectBtn');
                if (reconnectBtn) {
                  reconnectBtn.addEventListener('click', openReconnectModal);
                  fetch('/api/get-reconnect-info')
                    .then(r => r.json())
                    .then(data => {
                      if (data.already_requested) {
                        reconnectAlreadyRequested = true;
                        reconnectBtn.disabled = true;
                        reconnectBtn.textContent = 'Request Already Submitted';
                      }
                    })
                    .catch(() => {});
                }
            }
            
            // ✅ 5. Show toast notification - IBA ANG MESSAHE
            if (typeof showToast === 'function') {
                if (status === 'Terminated') {
                    showToast('Your account has been terminated. Please contact support.', 'error');
                } else if (status === 'Inactive' || status === 'Deactivated') {
                    showToast('Your account is inactive. Please settle your balance to reactivate.', 'info');
                }
            }
        }
    } catch (error) {
        console.error('Error checking user status:', error);
    }
}


// ================= RECONNECT REQUEST MODAL =================
let reconnectAlreadyRequested = false;

function openReconnectModal() {
  const modal = document.getElementById('reconnectModal');
  if (!modal) return;

  if (reconnectAlreadyRequested) {
    showToast('You already have a reconnect request on file.', 'info');
    return;
  }

  modal.classList.add('show');
  document.body.style.overflow = 'hidden';
  
  // ✅ I-AWAIT MUNA ANG loadReconnectPrefillData() BAGO I-LOAD ANG PLANS
  loadReconnectPrefillData().then(() => {
    loadPlansIntoSelect();
  }).catch((err) => {
    console.error('Error loading reconnect data:', err);
    loadPlansIntoSelect(); // I-load pa rin ang plans kahit may error
  });
}

function closeReconnectModal() {
  const modal = document.getElementById('reconnectModal');
  if (modal) modal.classList.remove('show');
  document.body.style.overflow = '';

  const form = document.getElementById('reconnectForm');
  const successView = document.getElementById('reconnectSuccessView');
  if (form) form.style.display = '';
  if (successView) successView.style.display = 'none';
  
  // ✅ RESET EDIT MODE
  const toggleBtn = document.getElementById('toggleEditBtn');
  const cancelBtn = document.getElementById('cancelEditBtn');
  if (toggleBtn) {
    toggleBtn.classList.remove('editing');
    toggleBtn.innerHTML = '<i class="fas fa-pen"></i> Edit';
  }
  if (cancelBtn) cancelBtn.style.display = 'none';
  
  // ✅ RESET PLAN SELECTION
  const planSelect = document.getElementById('newPlanSelect');
  const noRadio = document.querySelector('input[name="changePlan"][value="no"]');
  if (planSelect && noRadio) {
      planSelect.removeAttribute('required');
      planSelect.disabled = true;
      planSelect.value = '';
      document.getElementById('planSelectGroup').style.display = 'none';
      noRadio.checked = true;
  }
  
  // ✅ RESET TO ORIGINAL DATA
  disableEditing();
  resetToOriginalData();
}

function showReconnectSuccessView(requestId, data) {
  const form = document.getElementById('reconnectForm');
  const successView = document.getElementById('reconnectSuccessView');
  const requestNumberEl = document.getElementById('reconnectRequestNumberValue');

  if (form) form.style.display = 'none';
  if (requestNumberEl) {
    requestNumberEl.textContent = requestId || 'N/A';
    requestNumberEl.style.cursor = 'pointer';
    requestNumberEl.title = 'Click to copy';
    requestNumberEl.onclick = function() {
      navigator.clipboard.writeText(this.textContent).then(() => {
        showToast('Request number copied!', 'success');
      }).catch(() => {});
    };
  }

  if (data) {
    const currentPlanEl = document.getElementById('summaryCurrentPlan');
    if (currentPlanEl && data.current_plan) {
      const plan = data.current_plan;
      let priceDisplay = '₱0.00';
      if (plan.price && plan.price !== '0' && plan.price !== '0.00') {
        const cleanPrice = String(plan.price).replace(/[₱,]/g, '').trim();
        const priceNum = parseFloat(cleanPrice);
        if (!isNaN(priceNum) && priceNum > 0) {
          priceDisplay = `₱${priceNum.toFixed(2)}`;
        }
      }
      currentPlanEl.textContent = `${plan.name || 'No Active Plan'} (${plan.speed || '0'} Mbps) - ${priceDisplay}/mo`;
    }

    const newPlanRow = document.getElementById('summaryNewPlanRow');
    const newPlanEl = document.getElementById('summaryNewPlan');
    const noChangeRow = document.getElementById('summaryNoChangeRow');

    if (data.change_plan && data.new_plan && data.new_plan.name) {
      newPlanRow.style.display = 'flex';
      noChangeRow.style.display = 'none';
      
      if (newPlanEl) {
        const plan = data.new_plan;
        let priceDisplay = '₱0.00';
        if (plan.price && plan.price !== '0' && plan.price !== '0.00') {
          const cleanPrice = String(plan.price).replace(/[₱,]/g, '').trim();
          const priceNum = parseFloat(cleanPrice);
          if (!isNaN(priceNum) && priceNum > 0) {
            priceDisplay = `₱${priceNum.toFixed(2)}`;
          }
        }
        newPlanEl.textContent = `${plan.name} (${plan.speed || '0'} Mbps) - ${priceDisplay}/mo`;
      }
    } else {
      newPlanRow.style.display = 'none';
      noChangeRow.style.display = 'flex';
    }
  }

  if (successView) successView.style.display = 'flex';
}

async function loadReconnectPrefillData() {
  try {
    const res = await fetch('/api/get-reconnect-info');
    const data = await res.json();

    if (data.already_requested) {
      reconnectAlreadyRequested = true;
      showToast('You already have a reconnect request on file.', 'info');
      closeReconnectModal();
      return;
    }

    // ✅ STORE ORIGINAL DATA PARA SA RESET
    window._originalData = {
        full_name: data.full_name || '',
        contact_number: data.contact_number || '',
        email: data.email || '',
        full_address: data.full_address || ''
    };

    // ✅ FILL FIELDS - Single Full Name field
    document.getElementById('reconnectFullName').value = data.full_name || '';
    document.getElementById('reconnectContact').value = data.contact_number || '';
    document.getElementById('reconnectEmail').value = data.email || '';
    document.getElementById('reconnectFullAddress').value = data.full_address || '';

    // ✅ DISPLAY CURRENT PLAN
    const plan = data.current_plan || {};
    const planName = plan.name || 'No Active Plan';
    document.getElementById('currentPlanName').textContent = planName;

    let speedDisplay = '0';
    if (plan.speed) {
      const match = String(plan.speed).match(/(\d+)/);
      speedDisplay = match ? match[1] : plan.speed;
    }
    document.getElementById('currentPlanSpeed').textContent = speedDisplay;

    const priceNum = parseFloat(plan.price) || 0;
    document.getElementById('currentPlanPrice').textContent = priceNum.toFixed(2);
    
    // ✅ SAVE CURRENT PLAN NAME
    const cleanedPlanName = planName.trim().replace(/\s+/g, ' ');
    window.currentPlanName = cleanedPlanName;
    
    console.log('✅ [DEBUG] currentPlanName set to:', `"${window.currentPlanName}"`);

  } catch (err) {
    console.error('Error loading reconnect info:', err);
    showToast('Failed to load your info. Try again.', 'error');
  }
}

async function loadPlansIntoSelect() {
  const select = document.getElementById('newPlanSelect');
  if (!select) return;
  
  select.innerHTML = `<option value="">Loading plans...</option>`;
  
  try {
    console.log('🔍 [DEBUG] Starting loadPlansIntoSelect...');
    console.log('🔍 [DEBUG] window.currentPlanName =', window.currentPlanName);
    console.log('🔍 [DEBUG] Type of window.currentPlanName:', typeof window.currentPlanName);
    
    const res = await fetch('/api/get-plans-for-reconnect');
    console.log('🔍 [DEBUG] Response status:', res.status);
    
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    
    const plans = await res.json();
    console.log('📋 [DEBUG] Raw plans data:', plans);
    console.log('📋 [DEBUG] Number of plans:', plans.length);
    
    if (!plans || plans.length === 0) {
      select.innerHTML = `<option value="">No plans available</option>`;
      return;
    }
    
    // ✅ GET CURRENT PLAN NAME - I-CLEAN ANG NAME
    let currentPlanName = '';
    if (window.currentPlanName) {
      // ✅ I-CONVERT SA STRING, I-TRIM, AT I-REMOVE ANG EXTRA SPACES
      currentPlanName = String(window.currentPlanName).trim().replace(/\s+/g, ' ');
      console.log('📌 [DEBUG] Current plan name (cleaned):', `"${currentPlanName}"`);
      console.log('📌 [DEBUG] Current plan name length:', currentPlanName.length);
      console.log('📌 [DEBUG] Current plan name chars:', Array.from(currentPlanName).map(c => c.charCodeAt(0)));
    }
    
    // ✅ KUNG WALANG CURRENT PLAN NAME, GAMITIN ANG DEFAULT
    if (!currentPlanName) {
      console.warn('⚠️ [DEBUG] No current plan name found, using default');
      // ✅ DEFAULT: I-FILTER OUT ANG "Premium Package"
      currentPlanName = 'Premium Package';
    }
    
    // ✅ I-DISPLAY ANG LAHAT NG PLAN NAMES
    console.log('📌 [DEBUG] All plan names in database:');
    plans.forEach((p, index) => {
      const cleanName = (p.name || '').trim().replace(/\s+/g, ' ');
      console.log(`  ${index + 1}. "${cleanName}" (length: ${cleanName.length})`);
    });
    
    // ✅ FILTER OUT ANG CURRENT PLAN - EXACT MATCH
    const filteredPlans = [];
    const skippedPlans = [];
    
    plans.forEach(p => {
      const planName = (p.name || '').trim().replace(/\s+/g, ' ');
      const isCurrentPlan = planName.toLowerCase() === currentPlanName.toLowerCase();
      
      if (isCurrentPlan) {
        skippedPlans.push(p.name);
        console.log(`⏩ [DEBUG] SKIPPING: "${p.name}" (matches current plan "${currentPlanName}")`);
      } else {
        filteredPlans.push(p);
        console.log(`✅ [DEBUG] KEEPING: "${p.name}"`);
      }
    });
    
    console.log(`📊 [DEBUG] Skipped plans: ${skippedPlans.length} (${skippedPlans.join(', ')})`);
    console.log(`📊 [DEBUG] Filtered plans: ${filteredPlans.length} of ${plans.length} total`);
    
    if (filteredPlans.length === 0) {
      select.innerHTML = `<option value="">No other plans available</option>`;
      console.warn('⚠️ [DEBUG] No filtered plans found!');
      return;
    }
    
    // ✅ BUILD THE OPTIONS
    let optionsHTML = `<option value="">-- Select a plan --</option>`;
    filteredPlans.forEach(p => {
      const price = parseFloat(p.price || 0);
      const priceDisplay = isNaN(price) ? '0.00' : price.toFixed(2);
      const speed = p.speed || '0';
      
      optionsHTML += `<option value="${p.id}">${escapeHtml(p.name)} — ${escapeHtml(speed)} Mbps (₱${priceDisplay})</option>`;
    });
    
    select.innerHTML = optionsHTML;
    console.log('✅ [DEBUG] Plans loaded successfully!');
    console.log(`📋 [DEBUG] Total options: ${select.options.length - 1}`);
    
    // ✅ I-SHOW ANG FINAL OPTIONS
    console.log('📋 [DEBUG] Final options in dropdown:');
    for (let i = 1; i < select.options.length; i++) {
      console.log(`  ${i}. ${select.options[i].text}`);
    }
    
  } catch (err) {
    console.error('❌ [DEBUG] Error loading plans:', err);
    console.error('❌ [DEBUG] Error stack:', err.stack);
    select.innerHTML = `<option value="">Failed to load plans</option>`;
    showToast('Failed to load available plans. Please refresh and try again.', 'error');
  }
}

// ================= RECONNECT MODAL - EVENT HANDLERS =================
document.addEventListener('DOMContentLoaded', function() {
    const closeBtn = document.getElementById('closeReconnectModal');
    const cancelBtn = document.getElementById('cancelReconnect');
    const modal = document.getElementById('reconnectModal');
    const form = document.getElementById('reconnectForm');
    const planGroup = document.getElementById('planSelectGroup');
    const closeSuccessBtn = document.getElementById('closeReconnectSuccessBtn');
    const toggleEditBtn = document.getElementById('toggleEditBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');

    if (closeBtn) closeBtn.addEventListener('click', closeReconnectModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeReconnectModal);
    if (modal) modal.addEventListener('click', function(e) { 
        if (e.target === modal) closeReconnectModal(); 
    });
    if (closeSuccessBtn) closeSuccessBtn.addEventListener('click', closeReconnectModal);

    // ============================================================
    // ✅ EDIT TOGGLE FUNCTIONALITY
    // ============================================================
    
    // Helper: Auto-capitalize function
    function capitalizeWords(str) {
        if (!str) return '';
        return str.replace(/\b\w/g, function(char) {
            return char.toUpperCase();
        });
    }

    // Helper: Apply capitalization to all fields
    function applyCapitalizationToFields() {
        const fullNameField = document.getElementById('reconnectFullName');
        const addressField = document.getElementById('reconnectFullAddress');
        
        if (fullNameField && !fullNameField.disabled) {
            fullNameField.value = capitalizeWords(fullNameField.value);
        }
        if (addressField && !addressField.disabled) {
            addressField.value = capitalizeWords(addressField.value);
        }
    }

    // Enable editing
    function enableEditing() {
        const fields = [
            'reconnectFullName',
            'reconnectContact',
            'reconnectEmail',
            'reconnectFullAddress'
        ];
        
        fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.removeAttribute('readonly');
                el.disabled = false;
            }
        });
        
        // Show cancel button
        if (cancelEditBtn) cancelEditBtn.style.display = 'inline-flex';
    }

    // Disable editing
    function disableEditing() {
        const fields = [
            'reconnectFullName',
            'reconnectContact',
            'reconnectEmail',
            'reconnectFullAddress'
        ];
        
        fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.setAttribute('readonly', 'readonly');
                el.disabled = true;
                // Remove error state
                el.classList.remove('error');
            }
        });
        
        // Hide cancel button
        if (cancelEditBtn) cancelEditBtn.style.display = 'none';
    }

    // Reset to original data
    function resetToOriginalData() {
        if (window._originalData) {
            document.getElementById('reconnectFullName').value = window._originalData.full_name || '';
            document.getElementById('reconnectContact').value = window._originalData.contact_number || '';
            document.getElementById('reconnectEmail').value = window._originalData.email || '';
            document.getElementById('reconnectFullAddress').value = window._originalData.full_address || '';
        }
    }

    // Save changes from edit mode
    function saveEditableFields() {
        // Apply capitalization before saving
        applyCapitalizationToFields();
        
        // Save to original data
        window._originalData = {
            full_name: document.getElementById('reconnectFullName').value.trim(),
            contact_number: document.getElementById('reconnectContact').value.trim(),
            email: document.getElementById('reconnectEmail').value.trim(),
            full_address: document.getElementById('reconnectFullAddress').value.trim()
        };
    }

    // Toggle Edit Button
    if (toggleEditBtn) {
        toggleEditBtn.addEventListener('click', function() {
            const isEditing = this.classList.contains('editing');
            
            if (isEditing) {
                // ✅ SAVE CHANGES MODE
                // Apply capitalization
                applyCapitalizationToFields();
                
                // Validate required fields
                const fullName = document.getElementById('reconnectFullName').value.trim();
                const contact = document.getElementById('reconnectContact').value.trim();
                const email = document.getElementById('reconnectEmail').value.trim();
                const address = document.getElementById('reconnectFullAddress').value.trim();
                
                if (!fullName) {
                    showToast('Full Name is required.', 'error');
                    document.getElementById('reconnectFullName').classList.add('error');
                    return;
                }
                if (!contact) {
                    showToast('Contact Number is required.', 'error');
                    document.getElementById('reconnectContact').classList.add('error');
                    return;
                }
                if (!email) {
                    showToast('Email is required.', 'error');
                    document.getElementById('reconnectEmail').classList.add('error');
                    return;
                }
                if (!address) {
                    showToast('Full Address is required.', 'error');
                    document.getElementById('reconnectFullAddress').classList.add('error');
                    return;
                }
                
                // Remove error states
                document.querySelectorAll('.form-control.error').forEach(el => el.classList.remove('error'));
                
                // Save changes
                saveEditableFields();
                
                // Update button state
                this.classList.remove('editing');
                this.innerHTML = '<i class="fas fa-pen"></i> Edit';
                
                // Disable editing
                disableEditing();
                
                showToast('Changes saved successfully!', 'success');
            } else {
                // ✅ EDIT MODE
                // Remove any error states
                document.querySelectorAll('.form-control.error').forEach(el => el.classList.remove('error'));
                
                this.classList.add('editing');
                this.innerHTML = '<i class="fas fa-save"></i> Save Changes';
                
                // Enable editing
                enableEditing();
                
                showToast('You can now edit your information.', 'info');
            }
        });
    }

    // Cancel Edit Button
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', function() {
            // Reset to original data
            resetToOriginalData();
            
            // Remove error states
            document.querySelectorAll('.form-control.error').forEach(el => el.classList.remove('error'));
            
            // Reset toggle button
            if (toggleEditBtn) {
                toggleEditBtn.classList.remove('editing');
                toggleEditBtn.innerHTML = '<i class="fas fa-pen"></i> Edit';
            }
            
            // Disable editing
            disableEditing();
            
            showToast('Edit cancelled. Changes discarded.', 'info');
        });
    }

    // ✅ Auto-capitalize on input events
    document.addEventListener('input', function(e) {
        if (e.target.id === 'reconnectFullName' || e.target.id === 'reconnectFullAddress') {
            if (!e.target.disabled) {
                // Get cursor position
                const start = e.target.selectionStart;
                const end = e.target.selectionEnd;
                
                // Apply capitalization
                e.target.value = capitalizeWords(e.target.value);
                
                // Restore cursor position
                e.target.setSelectionRange(start, end);
            }
        }
    });

    // ============================================================
    // ✅ RADIO BUTTON CHANGE - SHOW/HIDE PLAN SELECTION
    // ============================================================
    document.querySelectorAll('input[name="changePlan"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            const isYes = this.value === 'yes';
            const planGroup = document.getElementById('planSelectGroup');
            const planSelect = document.getElementById('newPlanSelect');
            
            planGroup.style.display = isYes ? 'block' : 'none';
            
            if (planSelect) {
                if (isYes) {
                    planSelect.setAttribute('required', 'required');
                    planSelect.disabled = false;
                } else {
                    planSelect.removeAttribute('required');
                    planSelect.value = '';
                    planSelect.disabled = true;
                }
            }
        });
    });

    // ✅ I-SET ANG INITIAL STATE
    const planSelect = document.getElementById('newPlanSelect');
    const noRadio = document.querySelector('input[name="changePlan"][value="no"]');
    if (planSelect && noRadio && noRadio.checked) {
        planSelect.removeAttribute('required');
        planSelect.disabled = true;
        planSelect.value = '';
        document.getElementById('planSelectGroup').style.display = 'none';
    }

    // ✅ INITIAL DISABLE EDITING
    disableEditing();

    // ============================================================
    // ✅ FORM SUBMIT HANDLER
    // ============================================================
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            console.log('🟢 Submit button clicked!');

            const changePlanRadio = document.querySelector('input[name="changePlan"]:checked');
            const changePlan = changePlanRadio ? changePlanRadio.value === 'yes' : false;
            
            let newPlanId = null;
            if (changePlan) {
                newPlanId = document.getElementById('newPlanSelect').value;
            }

            console.log('📌 changePlan:', changePlan);
            console.log('📌 newPlanId:', newPlanId);

            if (changePlan && !newPlanId) {
                showToast('Please select a plan to change to.', 'error');
                document.getElementById('newPlanSelect').focus();
                return;
            }

            // ✅ KUNIN ANG MGA VALUES (EDITED OR NOT)
            const payload = {
                change_plan: changePlan,
                first_name: document.getElementById('reconnectFullName').value.trim(),
                contact_number: document.getElementById('reconnectContact').value.trim(),
                email: document.getElementById('reconnectEmail').value.trim(),
                address: document.getElementById('reconnectFullAddress').value.trim()
            };

            if (changePlan && newPlanId) {
                payload.new_plan_id = parseInt(newPlanId);
            }

            // ✅ VALIDATE REQUIRED FIELDS
            if (!payload.first_name) {
                showToast('Full Name is required.', 'error');
                document.getElementById('reconnectFullName').focus();
                return;
            }
            if (!payload.contact_number) {
                showToast('Contact Number is required.', 'error');
                document.getElementById('reconnectContact').focus();
                return;
            }
            if (!payload.email) {
                showToast('Email is required.', 'error');
                document.getElementById('reconnectEmail').focus();
                return;
            }
            if (!payload.address) {
                showToast('Full Address is required.', 'error');
                document.getElementById('reconnectFullAddress').focus();
                return;
            }

            console.log('📤 Sending payload:', payload);

            const submitBtn = document.getElementById('submitReconnectBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';

            try {
                const res = await fetch('/api/submit-reconnect-request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await res.json();

                console.log('📥 Response:', result);

                if (res.ok && result.success) {
                    reconnectAlreadyRequested = true;
                    showReconnectSuccessView(result.request_id, {
                        current_plan: result.current_plan,
                        new_plan: result.new_plan,
                        change_plan: result.change_plan
                    });
                    const reconnectBtn = document.getElementById('requestReconnectBtn');
                    if (reconnectBtn) {
                        reconnectBtn.disabled = true;
                        reconnectBtn.textContent = 'Request Already Submitted';
                    }
                } else if (res.status === 409) {
                    showToast(result.error || 'You already have a reconnect request on file.', 'error');
                    reconnectAlreadyRequested = true;
                    closeReconnectModal();
                    const reconnectBtn = document.getElementById('requestReconnectBtn');
                    if (reconnectBtn) {
                        reconnectBtn.disabled = true;
                        reconnectBtn.textContent = 'Request Already Submitted';
                    }
                } else {
                    showToast(result.error || 'Something went wrong.', 'error');
                    console.error('❌ Error response:', result);
                }
            } catch (err) {
                console.error('Error submitting reconnect request:', err);
                showToast('Failed to submit request. Try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit Request';
            }
        });
    }
});