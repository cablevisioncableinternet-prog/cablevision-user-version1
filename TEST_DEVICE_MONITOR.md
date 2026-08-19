# Device Login Monitor - Complete Test & Debug Guide

## How It Should Work:

1. **User logs in on Device A (Edge)**
   - `sessionStart` is set to current time
   - `tab_id` is set
   - Device A's info recorded in database

2. **User logs in on Device B (Chrome)**
   - New device info recorded in database
   - Different `tab_id` and `session_token`

3. **User goes back to Device A (Edge)**
   - Monitor checks for new devices every 30 seconds
   - Finds Device B's login
   - Compares timestamp - if newer than sessionStart, shows MODAL
   - Modal displays Device B info
   - Buttons: "View in Login History" or "Logout Device"

---

## Quick Test Steps:

### Step 1: Open Console in MS Edge
```
F12 → Console tab
```

### Step 2: Look for These Messages After Login:
```
✅ Login successful!
  - Session Start: 1724078400123
```

### Step 3: Check sessionStorage Values
Type in Console:
```javascript
console.log('sessionStart:', sessionStorage.getItem('sessionStart'));
console.log('tab_id:', sessionStorage.getItem('tab_id'));
```

Should return timestamps and tab ID.

### Step 4: Wait for Monitor to Start
Look for:
```
📱 Device monitor started - checking every 30 seconds
   Current tab_id: tab_1724078400123_abc123def
   Session started at: Mon Aug 18 2024 10:30:00 GMT
   Initial lastCheckTime: 1724078400
⏳ Initial device check scheduled in 2 seconds...
```

### Step 5: Log In From Chrome
1. Open Chrome
2. Go to same website
3. Log in with SAME account
4. Note the time

### Step 6: Go Back to Edge and Wait
- Wait 2-30 seconds
- Should see in Console:
```
🔍 Running initial device check...
📱 Checking for new devices... (last_check: 1724078400)
API URL: /api/check-new-devices?tab_id=...&last_check=1724078400
```

### Step 7: Check API Response
Look for:
```json
{
  "success": true,
  "new_devices": [
    {
      "id": 123,
      "device_info": "Chrome on Windows",
      "browser": "Chrome",
      "os": "Windows",
      "ip_address": "127.0.0.1",
      "location": "Local",
      "login_time": "2024-08-18 10:35:00",
      "formatted_login_time": "Aug 18, 2024 10:35 AM",
      "session_token": "tab_different_from_edge"
    }
  ],
  "current_timestamp": 1724078500,
  "total_new": 1
}
```

### Step 8: Check for Modal
- Modal should auto-popup with device info
- If not, check:
  - Is CSS loaded? Check Network tab for device-login-alert.css
  - Is modal HTML created? In Console: `document.getElementById('deviceLoginAlertModal')`
  - Does modal have 'show' class? `document.querySelector('#deviceLoginAlertModal')?.classList`

---

## Common Issues & Fixes:

### Issue 1: sessionStart is NULL
```javascript
sessionStorage.getItem('sessionStart')  // returns null
```
**Solution**: Login page didn't set it. Check login.html line ~810 for sessionStorage.setItem('sessionStart', ...)

### Issue 2: Monitor not checking
Console shows no "📱 Checking for new devices..." message
**Solution**: 
- Check if tab_id is present: `sessionStorage.getItem('tab_id')`
- Check if monitor loaded: Look for "📱 Device monitor started"
- Check if device-login-monitor.js is linked in template

### Issue 3: API returns empty new_devices
```javascript
"new_devices": []
```
**Solutions**:
- Chrome login might not have been recorded in database
- Check login_history table: `SELECT * FROM login_history WHERE user_id = 'YOUR_ID' ORDER BY login_time DESC;`
- Verify both logins exist in database

### Issue 4: Modal exists but not showing
Modal HTML is there but doesn't appear
**Solutions**:
- Check CSS is loaded: Network tab → Stylesheets → device-login-alert.css
- Check modal CSS has `.device-alert-modal.show { display: block; }`
- Check if `createDeviceAlertModal()` is being called
- Check browser console for JavaScript errors

### Issue 5: Timestamp Comparison Wrong
Modal shows but for old logins
**Solution**: 
- sessionStart should be set at LOGIN time (milliseconds)
- Database times are in seconds (UNIX_TIMESTAMP)
- Conversion: `lastCheckTime = Math.floor(sessionStartedAt / 1000)`

---

## Database Check Commands:

SSH into your server or use MySQL GUI:

```sql
-- Check login history for a user
SELECT id, user_id, session_token, device_info, browser, os, 
       ip_address, location, login_time, status 
FROM login_history 
WHERE user_id = 'YOUR_USER_ID' 
ORDER BY login_time DESC 
LIMIT 10;

-- Check if both devices are recorded
SELECT COUNT(*) as total_logins 
FROM login_history 
WHERE user_id = 'YOUR_USER_ID';

-- Check timestamps
SELECT user_id, session_token, login_time, 
       UNIX_TIMESTAMP(login_time) as unix_time
FROM login_history 
WHERE user_id = 'YOUR_USER_ID' 
ORDER BY login_time DESC 
LIMIT 5;
```

---

## Test Checklist:

- [ ] sessionStart is set after login
- [ ] tab_id is set
- [ ] device-login-monitor.js is loaded (check Network tab)
- [ ] Monitor starts checking (check Console for "📱 Device monitor started")
- [ ] API call is made to /api/check-new-devices
- [ ] API returns new devices from database
- [ ] Modal CSS is loaded
- [ ] Modal HTML is created in DOM
- [ ] Modal shows when new device is detected
- [ ] Buttons work: View History, Logout Device, Dismiss

---

## Expected Console Output Example:

```
✅ Login successful!
  - Session Start: 1724078400123

📱 Device monitor started - checking every 30 seconds
   Current tab_id: tab_1724078400123_abc123
   Session started at: Mon Aug 18 2024 10:30:00 GMT+0000
   Initial lastCheckTime: 1724078400
⏳ Initial device check scheduled in 2 seconds...

(User logs in from Chrome...)

🔍 Running initial device check...
📱 Checking for new devices... (last_check: 1724078400)
📱 Check result: {success: true, new_devices: [{...}], current_timestamp: 1724078500}
🔍 Analyzing new device:
   Device ID: 123
   Device: Chrome on Windows
   Login time (raw): 2024-08-18 10:35:00
   Login time (Unix): 1724078500
   Last check time: 1724078400
   Is newer than last check? true
   Already notified? false
🚨 NEW DEVICE DETECTED - SHOWING MODAL!
🎯 Showing alert modal for device: {...}
✅ Set logout device ID: 123
✅ Modal displayed
```

---

## If Still Not Working:

1. Take a screenshot of the Console showing ALL messages
2. Check Network tab - is /api/check-new-devices being called?
3. What's the response from that API call?
4. Run in console: `document.querySelector('#deviceLoginAlertModal')?.__proto__`
5. Send screenshots to developer

---

## Files to Check:

- ✅ `/templates/user-login.html` - sets sessionStart on success
- ✅ `/templates/user-dashboard.html` - loads device-login-monitor.js
- ✅ `/static/js/device-login-monitor.js` - the monitor script
- ✅ `/static/css/device-login-alert.css` - modal styling
- ✅ `/app.py` - APIs: check-new-devices and logout-device
