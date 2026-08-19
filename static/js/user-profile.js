// ================= SHOW MESSAGE FUNCTION =================
function showMessage(message, type) {
    const formMessage = document.getElementById("formMessage");
    if (!formMessage) return;
    formMessage.textContent = message;
    formMessage.className = `form-message ${type}`;
    formMessage.style.display = "block";
    
    setTimeout(() => {
        formMessage.style.display = "none";
    }, 5000);
}

// ================= SYNC SESSION WITH BACKEND =================
let sessionSynced = false;

async function syncSessionWithBackend() {
    const username = sessionStorage.getItem('username');
    const userType = sessionStorage.getItem('userType');
    const tabId = sessionStorage.getItem('tab_id');
    
    console.log('Syncing session - username:', username, 'userType:', userType, 'tabId:', tabId);
    
    if (username && userType === 'user' && tabId) {
        try {
            const response = await fetch('/user/sync-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    userType: userType,
                    tab_id: tabId  // 👈 ISAMA ANG TAB ID
                }),
                credentials: 'include'
            });
            
            const result = await response.json();
            console.log('Session sync result:', result);
            
            if (result.success) {
                console.log('Session synced successfully with backend');
                sessionSynced = true;
                return true;
            } else {
                console.error('Session sync failed:', result.error);
                return false;
            }
        } catch (error) {
            console.error('Failed to sync session:', error);
            return false;
        }
    } else {
        console.log('No valid session data in sessionStorage');
        return false;
    }
}

// Run sync immediately
(async function() {
    await syncSessionWithBackend();
})();

const inputs = document.querySelectorAll(".editable");
const editBtn = document.getElementById("editBtn");
const updateBtn = document.getElementById("updateBtn");
const cancelBtn = document.getElementById("cancelBtn");
const deleteBtn = document.getElementById("deleteBtn");

const form = document.getElementById("profileForm");
const currentPasswordInput = document.querySelector("input[name='current_password']");
const newPasswordInput = document.querySelector("input[name='new_password']");
const confirmPasswordInput = document.querySelector("input[name='confirm_password']");

const formMessage = document.getElementById("formMessage");
const passwordStrength = document.getElementById("passwordStrength");

const confirmModal = document.getElementById("confirmModal");
const confirmYesBtn = document.getElementById("confirmYes");
const confirmNoBtn = document.getElementById("confirmNo");

let originalValues = [];

// ================= PASSWORD STRENGTH CHECKER =================
// ================= PASSWORD STRENGTH CHECKER =================
function checkPasswordStrength(password) {
  if (password.length < 8) {
    passwordStrength.textContent = "Password too short";
    passwordStrength.className = "password-strength weak";
    passwordStrength.style.display = "block";
    return false;
  }

  const letters = password.replace(/[^A-Za-z]/g, "");
  if (letters && letters === letters.toUpperCase()) {
    passwordStrength.textContent = "All uppercase letters not allowed ";
    passwordStrength.className = "password-strength weak";
    passwordStrength.style.display = "block";
    return false;
  }

  if (/^\d+$/.test(password)) {
    passwordStrength.textContent = "All numbers not allowed ";
    passwordStrength.className = "password-strength weak";
    passwordStrength.style.display = "block";
    return false;
  }

  // 👇 BAGONG CHECK — kailangan may letter AT number
  const hasLetter = /[A-Za-z]/.test(password);
  const hasNumber = /\d/.test(password);
  if (!hasLetter || !hasNumber) {
    passwordStrength.textContent = "Password must contain both letters and numbers ";
    passwordStrength.className = "password-strength weak";
    passwordStrength.style.display = "block";
    return false;
  }

  passwordStrength.textContent = "Password looks good ";
  passwordStrength.className = "password-strength strong";
  passwordStrength.style.display = "block";
  return true;
}

// ================= STORE ORIGINAL VALUES =================
function storeValues() {
  originalValues = [];
  inputs.forEach(input => originalValues.push(input.value));
}
storeValues();

// ================= EDIT =================
if (editBtn) {
    editBtn.addEventListener("click", () => {
        // 👇 KUNIN ANG TAB ID
        const tabId = sessionStorage.getItem('tab_id');
        
        // Check if user is terminated
        fetch('/api/get-user-status?tab_id=' + tabId)  // 👈 ISAMA ANG TAB ID
            .then(res => res.json())
            .then(data => {
                if (data.status === 'Terminated' || data.status === 'Inactive' || data.status === 'Deactivated') {
                    showToast('Profile editing is disabled for terminated accounts.', 'error');
                    return;
                }
                
                // If not terminated, allow editing
                inputs.forEach(input => input.disabled = false);
                editBtn.style.display = "none";
                updateBtn.style.display = "inline-block";
                cancelBtn.style.display = "inline-block";
            })
            .catch(err => {
                console.error('Error checking status:', err);
                showToast('Unable to verify account status.', 'error');
            });
    });
}

// ================= CANCEL =================
if (cancelBtn) {
  cancelBtn.addEventListener("click", () => {
    inputs.forEach((input, i) => {
      input.value = originalValues[i];
      input.disabled = true;
    });
    formMessage.style.display = "none";
    passwordStrength.style.display = "none";
    editBtn.style.display = "inline-block";
    updateBtn.style.display = "none";
    cancelBtn.style.display = "none";
  });
}

// ================= LIVE PASSWORD STRENGTH =================
if (newPasswordInput) {
  newPasswordInput.addEventListener("input", () => {
    const pwd = newPasswordInput.value.trim();
    if (!pwd) {
      passwordStrength.style.display = "none";
      return;
    }
    checkPasswordStrength(pwd);
  });
}

// ================= VALIDATION BEFORE MODAL =================
async function validatePasswordChangeAttempt() {
  const currentPassword = currentPasswordInput ? currentPasswordInput.value.trim() : "";
  const newPassword = newPasswordInput ? newPasswordInput.value.trim() : "";
  const confirmPassword = confirmPasswordInput ? confirmPasswordInput.value.trim() : "";

  const isPasswordChangeAttempt = !!currentPassword || !!newPassword || !!confirmPassword;

  if (!isPasswordChangeAttempt) {
    return true;
  }

  if (!currentPassword) {
    showToast("Enter your current password before changing your password.", "error");
    return false;
  }

  if (!newPassword || !confirmPassword) {
    showToast("Please set your new password and confirm it after entering your current password.", "error");
    return false;
  }

  if (newPassword !== confirmPassword) {
    showToast("Passwords do not match!", "error");
    return false;
  }

  if (newPassword.length < 8) {
    showToast("Password must be at least 8 characters!", "error");
    return false;
  }

  const hasLetter = /[A-Za-z]/.test(newPassword);
  const hasNumber = /\d/.test(newPassword);
  if (!hasLetter || !hasNumber) {
    showToast("Password must contain both letters and numbers!", "error");
    return false;
  }

  const isValid = checkPasswordStrength(newPassword);
  if (!isValid) {
    showToast("Password does not meet the requirements.", "error");
    return false;
  }

  try {
    const response = await fetch('/user/verify-current-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        current_password: currentPassword,
        tab_id: sessionStorage.getItem('tab_id') || ''
      }),
      credentials: 'include'
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
      showToast(result.error || 'Current password is incorrect.', 'error');
      return false;
    }

    return true;
  } catch (error) {
    console.error('Error verifying current password:', error);
    showToast('Unable to verify your current password. Please try again.', 'error');
    return false;
  }
}

if (updateBtn) {
  updateBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    const isValid = await validatePasswordChangeAttempt();
    if (!isValid) {
      return;
    }

    formMessage.style.display = "none";
    confirmModal.classList.add("show");
  });
}

// ================= CONFIRM YES =================
if (confirmYesBtn) {
  confirmYesBtn.addEventListener("click", () => {
    const tabIdInput = document.getElementById("profileTabId");
    if (tabIdInput) {
      tabIdInput.value = sessionStorage.getItem('tab_id') || '';
    }

    confirmModal.classList.remove("show");
    document.body.classList.remove("modal-open");
    storeValues();
    form.submit();
  });
}

// ================= CONFIRM NO =================
if (confirmNoBtn) {
  confirmNoBtn.addEventListener("click", () => {
    confirmModal.classList.remove("show");
    document.body.classList.remove("modal-open");
  });
}

// ================= CLICK OUTSIDE MODAL =================
window.addEventListener("click", (e) => {
  if (e.target === confirmModal) {
    confirmModal.classList.remove("show");
    document.body.classList.remove("modal-open");
  }
});

// ================= DELETE PROFILE =================
if (deleteBtn) {
  deleteBtn.addEventListener("click", () => {
    const confirmDelete = confirm("Are you sure you want to delete your profile? This action cannot be undone.");
    if (confirmDelete) {
      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/user/profile/delete";
      document.body.appendChild(form);
      form.submit();
    }
  });
}

// ================= HELPER FUNCTIONS FOR CONTRACT =================
// ✅ IMPROVED: Better filtering of 'none' values
function getCleanFullName(firstName, middleName, lastName, suffix) {
    const nameParts = [];
    if (firstName && firstName !== 'none' && firstName !== 'None' && firstName.trim() !== '') nameParts.push(firstName.trim());
    if (middleName && middleName !== 'none' && middleName !== 'None' && middleName.trim() !== '') nameParts.push(middleName.trim());
    if (lastName && lastName !== 'none' && lastName !== 'None' && lastName.trim() !== '') nameParts.push(lastName.trim());
    if (suffix && suffix !== 'none' && suffix !== 'None' && suffix.trim() !== '') nameParts.push(suffix.trim());
    return nameParts.length > 0 ? nameParts.join(' ') : 'Not provided';
}

function getCleanValue(value) {
    if (!value) return '';
    const cleanValue = String(value).trim();
    if (cleanValue === '' || cleanValue.toLowerCase() === 'none' || cleanValue === 'null') return '';
    return cleanValue;
}

function calculateAge(birthdate) {
    if (!birthdate) return '';
    const birth = new Date(birthdate);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const m = today.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) {
        age--;
    }
    return age;
}

// ================= FETCH FUNCTIONS =================
async function fetchContractNumber() {
    try {
        const tabId = sessionStorage.getItem('tab_id');
        const response = await fetch('/user/get-contract-number?tab_id=' + tabId, {
            credentials: 'include'
        });
        const data = await response.json();
        console.log('Fetch contract number response:', data);
        
        if (data.success && data.contract_number) {
            currentContractNumber = data.contract_number;
            return data.contract_number;
        }
        return null;
    } catch (error) {
        console.error('Error fetching contract number:', error);
        return null;
    }
}

async function fetchUserApplicationData() {
    try {
        const tabId = sessionStorage.getItem('tab_id');
        const response = await fetch('/user/get-application-data?tab_id=' + tabId, {
            credentials: 'include'
        });
        const data = await response.json();
        console.log('Fetch application data response:', data);
        
        if (data.success) {
            currentApplicationData = data;
            return data;
        }
        return null;
    } catch (error) {
        console.error('Error fetching application data:', error);
        return null;
    }
}

async function fetchContractDetails(contractNumber) {
    try {
        const tabId = sessionStorage.getItem('tab_id');
        const response = await fetch(`/user/get-contract-details/${contractNumber}?tab_id=${tabId}`, {
            credentials: 'include'
        });
        const data = await response.json();
        if (data.success) {
            return data;
        }
        return null;
    } catch (error) {
        console.error('Error fetching contract details:', error);
        return null;
    }
}

// ================= TOAST MESSAGE =================
function showToastMessage(message, type = 'info') {
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
        `;
        document.body.appendChild(toastContainer);
    }
    
    const toast = document.createElement('div');
    toast.style.cssText = `
        background: ${type === 'warning' ? '#f59e0b' : '#10b981'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideInRight 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
    `;
    
    const icon = type === 'warning' ? '⚠️' : '✅';
    toast.innerHTML = `${icon} ${message}`;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Add animation styles
if (!document.getElementById('toastAnimations')) {
    const style = document.createElement('style');
    style.id = 'toastAnimations';
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// ================= GENERATE FULL CONTRACT PREVIEW (KATULAD NG SUPERADMIN) =================
let currentContractNumber = null;
let currentApplicationData = null;
let isInstallmentPlan = false;
let currentFirstInstallmentDate = null;
let currentLastInstallmentDate = null;
let currentBillingDate = null;

function generateContractPreview(applicationData, contractNumber, billingDate, signatureImageUrl = null) {
    const fullName = getCleanFullName(applicationData.first_name, applicationData.middle_name, applicationData.last_name, applicationData.suffix);
    const age = calculateAge(applicationData.birthdate);
    const civilStatus = getCleanValue(applicationData.civil_status);
    const barangay = getCleanValue(applicationData.barangay);
    const city = getCleanValue(applicationData.city);
    const province = getCleanValue(applicationData.province);
    const address = `${barangay}, ${city}, ${province}`.trim().replace(/^,|,$/g, '').replace(/,,/g, ',');
    const addressDisplay = address || '_____________';
    const dateSubmitted = applicationData.date_submitted || new Date().toLocaleDateString();
    const planName = getCleanValue(applicationData.plan);
    const planSpeed = getCleanValue(applicationData.plan_speed);
    const approvalDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    
    const formatMonthYear = (dateStr) => {
        if (!dateStr) return '_____________';
        const [year, month] = dateStr.split('-');
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        return `${monthNames[parseInt(month) - 1]} ${year}`;
    };
    
    const firstInstallmentFormatted = currentFirstInstallmentDate ? formatMonthYear(currentFirstInstallmentDate) : '_____________';
    const lastInstallmentFormatted = currentLastInstallmentDate ? formatMonthYear(currentLastInstallmentDate) : '_____________';
    
    const signatureSrc = signatureImageUrl || applicationData.signature || '';
    const hasSignature = signatureSrc && signatureSrc !== '' && signatureSrc.toLowerCase() !== 'none';
    
    const topSignatureSection = `
        <div class="signature-block" style="margin-top: 20px;">
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <tr>
                    <td style="width: 50%; text-align: center; vertical-align: top; padding: 0 10px;">
                        ${hasSignature ? `<img src="${signatureSrc}" alt="Signature" style="max-width: 200px; max-height: 80px; display: block; margin: 0 auto; border: none;" />` : '<div style="border-bottom: 1px solid #000; width: 80%; margin: 0 auto;"></div>'}
                        <div style="margin-top: 8px;">
                            <u><strong>${fullName}</strong></u>
                        </div>
                        <div style="font-size: 10px; color: #666; margin-top: 4px;">Subscriber's Signature Over Printed Name</div>
                    </td>
                    <td style="width: 50%; text-align: center; vertical-align: top; padding: 0 10px;">
                        <div style="margin-top: 85px;">
                            <u><strong>${dateSubmitted}</strong></u>
                        </div>
                        <div style="font-size: 10px; color: #666; margin-top: 4px;">Date</div>
                    </td>
                </tr>
            </table>
        </div>
    `;
    
    const bottomSignatureSection = `
        <div class="signature-block" style="margin-top: 30px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="width: 50%; text-align: left; vertical-align: top;"></td>
                    <td style="width: 50%; text-align: center; vertical-align: top; padding: 0 10px;">
                        ${hasSignature ? `<img src="${signatureSrc}" alt="Signature" style="max-width: 200px; max-height: 80px; display: block; margin: 0 auto; border: none;" />` : '<div style="border-bottom: 1px solid #000; width: 80%; margin: 0 auto;"></div>'}
                        <div style="margin-top: 8px;">
                            <u><strong>${fullName}</strong></u>
                        </div>
                        <div style="font-size: 10px; color: #666; margin-top: 4px;">Subscriber's Signature Over Printed Name</div>
                    </td>
                </tr>
            </table>
        </div>
    `;
    
    const addendumSection = `
        <div class="addendum-section">
            <div class="addendum-title">
                <strong>CABLEVISION SYSTEMS CORPORATION</strong>
            </div>
            <div class="addendum-content">
                <p style="text-align: center;"><strong>ADDENDUM TO CONTRACT NUMBER ${contractNumber}</strong></p>
                <p>That I, <strong>${fullName}</strong> holder of CONTRACT Number <strong>${contractNumber}</strong> dated <strong>${approvalDate}</strong> wishes to avail of your INTERNET SERVICE under <strong>${planName} (${planSpeed})</strong>. To take effect on <strong>_________________________</strong>.</p>
                <p>This is also to acknowledge that I have to pay in advance the monthly dues corresponding to the plan that I choose and it is understood that the TERMS AND CONDITIONS on the original contract remain.</p>
            </div>
        </div>
    `;
    
    let installmentSection = '';
    if (isInstallmentPlan) {
        installmentSection = `
            <div class="installment-section">
                <div class="installment-title">
                    <strong>AGREEMENT TO PAY ON INSTALLMENT</strong><br>
                    FOR THE INSTALLATION FEE AND/OR SET TOP BOX FOR TV EXTENSION
                </div>
                <div class="addendum-content">
                    <p>That I, <strong>${fullName}</strong> holder of contract no. <strong>${contractNumber}</strong> wishes to avail of the INSTALLMENT PLAN for the INSTALLATION FEE starting <strong>${firstInstallmentFormatted}</strong> up to <strong>${lastInstallmentFormatted}</strong> and the SET TOP BOX for our <strong>_________</strong> TV Extension/s for five (5) months.</p>
                    <p><strong>NOTE:</strong> In the event that the account is disconnected during the said period, the remaining installment shall be paid in full.</p>
                </div>
            </div>
        `;
    }
    
    return `
        <div style="max-height: 70vh; overflow-y: auto; padding: 20px; background: #ffffff; border-radius: 8px; font-family: 'Times New Roman', serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div style="width: 80px;">
                    <img src="/static/logo.png" alt="Logo" style="max-width: 70px; max-height: 70px; display: block;" onerror="this.style.display='none'">
                </div>
                <div style="flex: 1; text-align: center;">
                    <h1 style="font-size: 16px; margin: 0; font-weight: bold;">CABLE TELEVISION/CABLE ONLY/OR</h1>
                    <h1 style="font-size: 16px; margin: 5px 0; font-weight: bold;">CABLE &amp; INTERNET SERVICE CONTRACT</h1>
                    <div style="font-size: 13px; font-weight: bold; margin-top: 10px;">
                        NO. <span style="font-weight: bold; color: #0047ab;">${contractNumber}</span>
                    </div>
                </div>
                <div style="width: 80px;">
                    <img src="/static/logo_right.png" alt="Right Logo" style="max-width: 70px; max-height: 70px; display: block; margin-left: auto;" onerror="this.style.display='none'">
                </div>
            </div>
            
            <h3 style="font-size: 14px; font-weight: bold; margin: 15px 0 10px 0; text-align: center;">CONTRACT TERMS AND CONDITIONS</h3>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 10px; text-align: justify;">
                I, <span style="font-weight: bold; color: #0047ab;">${fullName}</span>, legal age, <span style="font-weight: bold; color: #0047ab;">${age}</span> years old, ${civilStatus} and residing at <span style="font-weight: bold; color: #0047ab;">${addressDisplay}</span> hereby apply and subscribed for the service of CABLE &amp; INTERNET and agree to the following terms and conditions:
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                <strong>Payment:</strong> The subscriber shall pay a Non-Refundable connection fee of P 1800 and cable in excess of 100 meters at P10.00 per meter. For CABLE/INTERNET BUNDLE subscriber, a one (1) month subscription fee of P800 shall be paid upon installation and activation of the service. Succeeding monthly subscription fee is due and payable every <span style="font-weight: bold; color: #0047ab;">${billingDate}</span> of each month. Failure to pay the monthly subscription fee on due date and after the grace period of 7 days will mean automatic disconnection of cable/internet service. The company shall have the right to discontinue/terminate/cancel and effect disconnection of Cable TV services in case of default or non-payment of accounts for two (2) succeeding payments.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                <strong>Deposit:</strong> Subscriber, who leases his/her house or does not own the house where service will be installed, shall pay a DEPOSIT upon installation. A deposit equivalent to one (1) month subscription fee for CABLE/INTERNET BUNDLE subscriber while two (2) months subscription fee for CABLE SUBSCRIBER ONLY. The said deposit cannot be applied to the monthly fee and shall only be refunded upon termination of the contract and upon pull out of all equipment installed in the premises of the subscriber. Should the subscriber wishes to apply for reconnection, a reconnection fee of P500.00 shall be paid plus the Deposit and the one (1) month advance subscription fee for CABLE/INTERNET BUNDLE subscriber. For CABLE SUBSCRIBER ONLY, a reconnection fee of P300.00 plus the DEPOSIT shall be paid.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                <strong>Access to the Premises:</strong> The subscriber authorizes our employees, contractors and representatives to enter your premise in order to install, maintain, inspect, repair, remove and replace Equipment at a time mutually agreeable upon by both parties.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                <strong>Subscriber Usage:</strong> The subscriber shall not in any way use his subscription for commercial purposes. Transmission of any Internet content which violates national or international law is prohibited. This includes but not limited to copyrighted materials, those legally adjudged to be threat to national security, or intruding into the privacy of individuals, offensive on moral, religious, racial or political grounds; abusive, indecent, obscene or menacing nature of material or information, infringement of intellectual property rights of any person as well as trade secrets.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                <strong>Relocating Equipment:</strong> The subscriber is not allowed to relocate equipment installed in their premises. However, equipment may be relocated by the company's authorized representatives upon the request of the subscriber at a time mutually agreeable to both parties. Applicable fees and charges may apply.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                <strong>Cable Modem and Setup Box:</strong> The subscriber will be given FREE USE of a Cable Modem and Set Top Box. This equipment will remain the property of CABLEVISION SYSTEMS CORP. For any Cable TV Extension the subscriber will have to pay for the cost of the SET TOP BOX amounting to 1400 and a HUB amounting to 420. There will be no additional cost on the monthly subscription. All equipment has one (1) year warranty against factory defects. If the defect was due to improper use and mishandling by the user during the warranty period, the cost of replacement will be chargeable to the account of the subscriber. If cable modem or Set Top Box becomes defective after the warranty period, cost of the new equipment is chargeable to the subscriber.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                <strong>Termination/Suspension of Service:</strong> The company reserves the right to suspend or terminate this contract without prior notice and pull out equipment provided at the subscriber's premises due to non-payment of all applicable fees and charges within the period and shall not be held liable for any damage; or loss which the Subscriber may incur by reason of suspension and/or termination of services based on this agreement.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                <strong>Disclaimer:</strong> Cablevision Systems Corp./MyCv Broadband shall not be held liable for any damages or delay in business transaction or communication of the subscriber or whatsoever, the subscriber may suffer or may have suffered due to the use of myCv Broadband Services. This includes but not limited to any loss of profits, incidental or consequential damages arising out of the Costumer's use of or inability to use; any loss of information howsoever caused whether as a result of any interruption, suspension, or termination of the Service or otherwise, or for the contents, accuracy or quality of information available, received or transmitted through the Service; or for failure of the Subscriber to comply with applicable laws, rules and regulations and all the terms prescribed by the Philippine National Telecommunications Commission for the use of any telecommunication systems, service or equipment. myCv Broadband shall not be liable for any delay or failure in the performance of service under this agreement resulting from acts beyond its control, including without limitation, acts of God, acts or regulations of any government or national authority, war or national emergency, accident, fire, electric power failure, temporary loss of signal not attributed to myCv Broadband, lightning, strikes, lock-outs, industrial disputes whether or not involving myCv Broadband employees.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 8px; text-align: justify;">
                myCv Broadband reserves the right to adjust, modify, amend or supplements these terms and condition as the service may require. myCv Broadband will advise SUBSCRIBER of any change by sending him notice setting out these changes.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 15px; text-align: justify;">
                <strong>Governing Law and Jurisdiction:</strong> The Laws of the Republic of the Philippines governs this Agreement and the Subscriber and myCv Broadband hereby submit to the exclusive jurisdiction of the courts of Sta. Cruz, Laguna, Philippines.
            </p>
            
            <p style="font-size: 11px; line-height: 1.5; margin-bottom: 15px; text-align: justify;">
                I hereby acknowledge that I have read and understood all the terms and conditions herein and that I voluntarily sign this agreement with full knowledge and consent of everything this Agreement contains, implies and entails.
            </p>
            
            ${topSignatureSection}
            ${addendumSection}
            ${installmentSection}
            ${bottomSignatureSection}
        </div>
    `;
}

// ================= SHOW CONTRACT FUNCTION =================
async function showContract() {
    const contractPreviewModal = document.getElementById('contractPreviewModal');
    const contractPreviewContent = document.getElementById('contractPreviewContent');
    
    if (!contractPreviewContent) return;
    
    // Ipakita agad ang modal na may loading spinner
    const modal = new bootstrap.Modal(contractPreviewModal);
    
    // Set loading content
    contractPreviewContent.innerHTML = `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">Loading contract...</p>
        </div>
    `;
    
    // Ipakita ang modal AGAD
    modal.show();
    
    // Siguraduhing naka-center ang modal
    setTimeout(() => {
        contractPreviewModal.style.display = 'flex';
        contractPreviewModal.style.alignItems = 'center';
        contractPreviewModal.style.justifyContent = 'center';
    }, 10);
    
    // I-load ang data habang nakikita ang modal
    const contractNumber = await fetchContractNumber();
    
    if (!contractNumber) {
        contractPreviewContent.innerHTML = `
            <div class="text-center p-5 text-danger">
                <i class="fas fa-exclamation-circle fa-3x mb-3"></i>
                <p>No contract found. Your application may not be approved yet.</p>
            </div>
        `;
        return;
    }
    
    const appData = await fetchUserApplicationData();
    
    if (!appData) {
        contractPreviewContent.innerHTML = `
            <div class="text-center p-5 text-danger">
                <i class="fas fa-exclamation-circle fa-3x mb-3"></i>
                <p>Unable to load application data.</p>
            </div>
        `;
        return;
    }
    
    const contractDetails = await fetchContractDetails(contractNumber);
    
    if (contractDetails) {
        currentBillingDate = contractDetails.billing_date || '15th';
        currentFirstInstallmentDate = contractDetails.first_installment_date || null;
        currentLastInstallmentDate = contractDetails.last_installment_date || null;
        
        const installationFee = appData.installation_fee || '';
        isInstallmentPlan = installationFee && (installationFee.toLowerCase().includes('installment') || 
                          installationFee.toLowerCase().includes('installment - 6 months') || 
                          installationFee.toLowerCase().includes('installment - 9 months'));
    }
    
    const billingDate = currentBillingDate || '15th';
    const signatureUrl = appData.signature || null;
    const contractHtml = generateContractPreview(appData, contractNumber, billingDate, signatureUrl);
    
    contractPreviewContent.innerHTML = contractHtml;
    
    // 👇 KUNIN ANG TAB ID
    const tabId = sessionStorage.getItem('tab_id');
    
    // I-update ang download button
    const downloadBtn = document.getElementById('downloadContractBtn');
    if (downloadBtn) {
        const newDownloadBtn = downloadBtn.cloneNode(true);
        downloadBtn.parentNode.replaceChild(newDownloadBtn, downloadBtn);
        newDownloadBtn.addEventListener('click', () => {
            // 👇 ISAMA ANG TAB ID SA DOWNLOAD URL
            window.open(`/user/download-contract/${contractNumber}?tab_id=${tabId}`, '_blank');
        });
    }
}

// ================= INITIALIZE VIEW CONTRACT BUTTON =================
async function initViewContractButton() {
    const viewContractBtn = document.getElementById('viewContractBtn');
    if (!viewContractBtn) {
        console.log('View Contract button not found');
        return;
    }
    
    console.log('Initializing View Contract button...');
    viewContractBtn.style.display = 'inline-flex';
    
    if (!sessionSynced) {
        await syncSessionWithBackend();
    }
    
    const contractNumber = await fetchContractNumber();
    console.log('Contract number:', contractNumber);
    
    const newBtn = viewContractBtn.cloneNode(true);
    viewContractBtn.parentNode.replaceChild(newBtn, viewContractBtn);
    
    if (contractNumber) {
        newBtn.disabled = false;
        newBtn.style.opacity = '1';
        newBtn.style.cursor = 'pointer';
        newBtn.style.background = 'linear-gradient(135deg, #059669 0%, #10b981 100%)';
        newBtn.title = 'View your service contract';
        newBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showContract();
        });
        console.log('View Contract button: ENABLED');
    } else {
        newBtn.disabled = true;
        newBtn.style.opacity = '0.6';
        newBtn.style.cursor = 'not-allowed';
        newBtn.style.background = 'linear-gradient(135deg, #9ca3af 0%, #6b7280 100%)';
        newBtn.title = 'No contract available yet';
        newBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showToastMessage('Your application has not been approved yet. No contract is available.', 'warning');
        });
        console.log('View Contract button: DISABLED');
    }
}

// ================= APPLICATION MODAL FUNCTIONALITY =================
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded');
    
    checkUserStatusAndDisableFeatures();

    initViewContractButton();
    
    const modal = document.getElementById('applicationModal');
    const appBtn = document.querySelector('.view-app-btn');
    const closeBtn = document.getElementById('closeAppModal');
    const dataElement = document.getElementById('appData');
    
    if (!dataElement) {
        console.error('appData element not found');
        return;
    }
    
    // ✅ IMPROVED: Better filtering of 'none' values for data attributes
    function getDataValue(key) {
        const value = dataElement.getAttribute(`data-${key}`);
        // Filter out 'none', 'None', 'null', at empty values
        if (!value || value === 'None' || value === 'null' || value.toLowerCase() === 'none') {
            return '';
        }
        // For fullname, also clean it
        if (key === 'fullname') {
            return value.replace(/\s*none\s*/gi, ' ').replace(/\s+/g, ' ').trim();
        }
        return value;
    }
    
    function initMap(lat, lng) {
        const mapContainer = document.getElementById('map-modal');
        if (!mapContainer) return;
        
        if (mapContainer._leaflet_map) {
            mapContainer._leaflet_map.remove();
            mapContainer._leaflet_map = null;
        }
        
        if (typeof L === 'undefined') {
            mapContainer.innerHTML = '<p style="text-align:center; padding:50px;">Leaflet library not loaded</p>';
            return;
        }
        
        if (lat && lng && lat !== 0 && lng !== 0 && !isNaN(lat) && !isNaN(lng)) {
            try {
                const map = L.map('map-modal').setView([lat, lng], 16);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; OpenStreetMap contributors'
                }).addTo(map);
                L.marker([lat, lng]).addTo(map).bindPopup("Pinned Location").openPopup();
                mapContainer._leaflet_map = map;
            } catch (error) {
                mapContainer.innerHTML = '<p style="text-align:center; padding:50px;">Error loading map</p>';
            }
        } else {
            mapContainer.innerHTML = '<p style="text-align:center; padding:50px;">No location pinned</p>';
        }
    }
    
    function setupImagePreview() {
        const previewModal = document.getElementById('imagePreviewModal');
        const previewImage = document.getElementById('previewImage');
        if (!previewModal || !previewImage) return;
        
        const clickableImages = document.querySelectorAll('#applicationModal .doc-img, #applicationModal .signature-img, #applicationModal .profile-photo-img');
        
        clickableImages.forEach(img => {
            img.removeEventListener('click', img._previewHandler);
            const handler = (e) => {
                e.stopPropagation();
                if (img.src && img.src !== '' && img.src.toLowerCase() !== 'none') {
                    previewImage.src = img.src;
                    previewModal.style.display = 'flex';
                    document.body.style.overflow = 'hidden';
                }
            };
            img._previewHandler = handler;
            img.addEventListener('click', handler);
        });
        
        previewModal.removeEventListener('click', previewModal._overlayHandler);
        previewModal._overlayHandler = (e) => {
            if (e.target === previewModal || e.target.classList.contains('preview-content')) {
                previewModal.style.display = 'none';
                document.body.style.overflow = '';
                previewImage.src = '';
            }
        };
        previewModal.addEventListener('click', previewModal._overlayHandler);
    }
    
    function populateModal() {
        function setInputValue(id, value) {
            const elem = document.getElementById(id);
            if (elem) {
                // Clean the value before setting
                let cleanValue = value || '';
                if (cleanValue.toLowerCase() === 'none') cleanValue = '';
                elem.value = cleanValue;
            }
        }
        
        function setTextContent(id, value) {
            const elem = document.getElementById(id);
            if (elem) {
                let cleanValue = value || 'N/A';
                if (cleanValue.toLowerCase() === 'none') cleanValue = 'N/A';
                elem.textContent = cleanValue;
            }
        }
        
        function setImage(id, src, defaultSrc = '') {
            const elem = document.getElementById(id);
            if (elem) {
                if (src && src !== 'None' && src !== 'null' && src !== '' && src.toLowerCase() !== 'none') {
                    elem.src = src;
                    elem.style.display = '';
                } else if (defaultSrc) {
                    elem.src = defaultSrc;
                    elem.style.display = '';
                } else {
                    elem.style.display = 'none';
                }
            }
        }
        
        setTextContent('app_applicationNumber', getDataValue('application-number'));
        setInputValue('app_fullname', getDataValue('fullname'));
        setInputValue('app_email', getDataValue('email'));
        setInputValue('app_mobile', getDataValue('mobile'));
        setInputValue('app_secondaryMobile', getDataValue('secondary-mobile'));
        setInputValue('app_phone', getDataValue('phone'));
        setInputValue('app_birthdate', getDataValue('birthdate'));
        setInputValue('app_placeOfBirth', getDataValue('place-of-birth'));
        setInputValue('app_motherMaidenName', getDataValue('mother-maiden-name'));
        setInputValue('app_sex', getDataValue('sex'));
        setInputValue('app_civilStatus', getDataValue('civil-status'));
        setInputValue('app_citizenship', getDataValue('citizenship'));
        setInputValue('app_occupation', getDataValue('occupation'));
        setInputValue('app_homeOwnership', getDataValue('home-ownership'));
        setInputValue('app_plan', getDataValue('plan'));
        setInputValue('app_serviceType', getDataValue('service-type'));
        setInputValue('app_address', getDataValue('address'));
        setInputValue('app_billingAddress', getDataValue('billing-address'));
        setInputValue('app_houseNumber', getDataValue('house-number'));
        setInputValue('app_landmark', getDataValue('landmark'));
        setInputValue('app_barangay', getDataValue('barangay'));
        setInputValue('app_city', getDataValue('city'));
        setInputValue('app_province', getDataValue('province'));
        setInputValue('app_zip', getDataValue('zip'));
        setInputValue('app_employer', getDataValue('employer'));
        setInputValue('app_businessAddress', getDataValue('business-address'));
        setInputValue('app_businessPhone', getDataValue('business-phone'));
        setInputValue('app_spouseName', getDataValue('spouse-name'));
        setInputValue('app_spouseOccupation', getDataValue('spouse-occupation'));
        setInputValue('app_spouseEmployer', getDataValue('spouse-employer'));
        setInputValue('app_spousePhone', getDataValue('spouse-phone'));
        setInputValue('app_fatherName', getDataValue('father-name'));
        setInputValue('app_installationAddress', getDataValue('installation-address'));
        setInputValue('app_installationPhone', getDataValue('installation-phone'));
        setInputValue('app_dateSubmitted', getDataValue('date-submitted'));
        setInputValue('app_timeSubmitted', getDataValue('time-submitted'));
        setInputValue('app_installationFee', getDataValue('installation-fee'));
        
        const defaultProfilePhoto = "/static/default-profile.png";
        setImage('app_profilePhoto', getDataValue('profile-photo'), defaultProfilePhoto);
        setImage('app_signature', getDataValue('signature'));
        setImage('app_idFront', getDataValue('id-front'));
        setImage('app_idBack', getDataValue('id-back'));
        setImage('app_proofBilling', getDataValue('proof-billing'));
        
        const tvTableBody = document.querySelector('#app_tvTable tbody');
        if (tvTableBody) {
            tvTableBody.innerHTML = '';
            const brands = getDataValue('tv-brand') ? getDataValue('tv-brand').split(',') : [];
            const qtys = getDataValue('tv-qty') ? getDataValue('tv-qty').split(',') : [];
            const types = getDataValue('tv-type') ? getDataValue('tv-type').split(',') : [];
            
            if (brands.length === 0 || (brands.length === 1 && brands[0] === '')) {
                tvTableBody.innerHTML = '<tr><td colspan="3" style="text-align:center">No TV sets added</td></tr>';
            } else {
                for (let i = 0; i < brands.length; i++) {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${getCleanValue(qtys[i]) || ''}</td>
                        <td>${getCleanValue(brands[i]) || ''}</td>
                        <td>${getCleanValue(types[i]) || ''}</td>
                    `;
                    tvTableBody.appendChild(row);
                }
            }
        }
        
        const lat = parseFloat(getDataValue('lat')) || 0;
        const lng = parseFloat(getDataValue('lng')) || 0;
        const latElem = document.getElementById('lat-modal');
        const lngElem = document.getElementById('lng-modal');
        if (latElem) latElem.value = lat || '0';
        if (lngElem) lngElem.value = lng || '0';
        initMap(lat, lng);
        setTimeout(() => setupImagePreview(), 100);
    }
    
    if (appBtn) {
        appBtn.addEventListener('click', (e) => {
            e.preventDefault();
            populateModal();
            if (modal) {
                modal.style.display = 'block';
                document.body.style.overflow = 'hidden';
                setTimeout(() => {
                    const lat = parseFloat(getDataValue('lat')) || 0;
                    const lng = parseFloat(getDataValue('lng')) || 0;
                    initMap(lat, lng);
                    setupImagePreview();
                }, 200);
            }
        });
    }
    
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    }
    
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
});


// ================= CHECK USER STATUS AND DISABLE FEATURES =================
async function checkUserStatusAndDisableFeatures() {
    try {
        // 👇 KUNIN ANG TAB ID MULA SA SESSION STORAGE
        const tabId = sessionStorage.getItem('tab_id');
        
        // 👇 ISAMA ANG TAB ID SA FETCH REQUEST
        const response = await fetch('/api/get-user-status?tab_id=' + tabId);
        const data = await response.json();
        const status = data.status || 'Active';
        
        console.log(`📊 User status: ${status}`);
        console.log(`🆔 Tab ID: ${tabId}`);
        
        if (status === 'Terminated' || status === 'Inactive' || status === 'Deactivated') {
            console.log(`⚠️ User status: ${status} - Disabling profile editing`);
            
            // Disable Edit button
            const editBtn = document.getElementById('editBtn');
            if (editBtn) {
                editBtn.disabled = true;
                editBtn.style.opacity = '0.5';
                editBtn.style.cursor = 'not-allowed';
                editBtn.title = 'Profile editing is disabled for your account status.';
            }
            
            // Disable password fields
            const passwordFields = document.querySelectorAll('input[name="new_password"], input[name="confirm_password"]');
            passwordFields.forEach(field => {
                field.disabled = true;
                field.style.opacity = '0.5';
                field.style.cursor = 'not-allowed';
            });
            
            // Disable View Application button (optional)
            const viewAppBtn = document.querySelector('.view-app-btn');
            if (viewAppBtn) {
                viewAppBtn.title = 'You can view your application but cannot make changes.';
            }
            
            // 🔥 IBAHIN ANG BANNER BATAY SA STATUS
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                // Remove existing banner
                const existingBanner = document.querySelector('.status-banner');
                if (existingBanner) {
                    existingBanner.remove();
                }
                
                const banner = document.createElement('div');
                banner.className = 'status-banner';
                
                let bannerTitle = '';
                let bannerMessage = '';
                let bannerIcon = '';
                let bannerColor = '';
                let bannerBg = '';
                let bannerBorder = '';
                
                if (status === 'Terminated') {
                    bannerTitle = 'Account Terminated';
                    bannerMessage = 'Your account has been terminated. You can view your profile but cannot make changes. Sidebar features are disabled.';
                    bannerIcon = 'fa-exclamation-circle';
                    bannerColor = '#dc2626';
                    bannerBg = '#fef2f2';
                    bannerBorder = '#fecaca';
                } else if (status === 'Inactive' || status === 'Deactivated') {
                    bannerTitle = 'Account Inactive';
                    bannerMessage = 'Your account is currently inactive. Please visit our office to settle your outstanding balance. Once payment is confirmed, your account will be reactivated. You can view your profile but cannot make changes. Sidebar features are disabled.';
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
                
                // I-insert ang banner bago ang profile header card
                const profileHeaderCard = document.querySelector('.profile-header-card');
                if (profileHeaderCard) {
                    mainContent.insertBefore(banner, profileHeaderCard);
                } else {
                    const formCard = document.querySelector('.form-card');
                    if (formCard) {
                        mainContent.insertBefore(banner, formCard);
                    } else {
                        mainContent.prepend(banner);
                    }
                }
            }
            
            // Show toast notification
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

// ================= CONFIRM MODAL =================
function openConfirmModal() {
    const modal = document.getElementById('confirmModal');
    if (modal) {
        modal.classList.add('show');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeConfirmModal() {
    const modal = document.getElementById('confirmModal');
    if (modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('confirmModal');
    const closeBtn = document.getElementById('closeModalBtn');
    const confirmNo = document.getElementById('confirmNo');
    const confirmYes = document.getElementById('confirmYes');
    
    // Close on X button
    if (closeBtn) {
        closeBtn.addEventListener('click', closeConfirmModal);
    }
    
    // Close on Cancel button
    if (confirmNo) {
        confirmNo.addEventListener('click', closeConfirmModal);
    }
    
    // Close on outside click
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeConfirmModal();
            }
        });
    }
    
    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && modal.classList.contains('show')) {
            closeConfirmModal();
        }
    });
    
    // Save button
    if (confirmYes) {
        confirmYes.addEventListener('click', function() {
            // TODO: Add your save logic here
            console.log('Save confirmed!');
            closeConfirmModal();
        });
    }
});