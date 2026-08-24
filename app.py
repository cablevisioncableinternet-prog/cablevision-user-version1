from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
import random
from datetime import datetime
import re
import time
import hashlib
import hmac
import struct
import requests
import base64
import traceback
import io
import os
from urllib.parse import quote
from PIL import Image

from flask_cors import CORS

# Import database config (MySQL)
from db_config import execute_query, get_db_connection

from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Optional: for PDF generation (i-keep kung kailangan)
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# ===============================
# Initialize Flask
# ===============================
app = Flask(__name__)
CORS(app)




import cloudinary
import cloudinary.uploader
import os
from flask import Flask, request, jsonify

app = Flask(__name__)


def get_cloudinary_url(image_path):
    """Convert image path to Cloudinary URL"""
    print(f"🔍 get_cloudinary_url called with: {image_path}")
    
    if not image_path:
        print(f"⚠️ image_path is empty")
        return ''
    
    # If already a full URL
    if image_path.startswith('http'):
        print(f"✅ Already a full URL: {image_path}")
        return image_path
    
    # If path starts with 'cablevision/'
    if image_path.startswith('cablevision/'):
        result = f"https://res.cloudinary.com/oa3fcr2b/image/upload/{image_path}"
        print(f"✅ Converted cablevision/ to: {result}")
        return result
    
    # If path still has /shared-uploads/ (legacy)
    if image_path.startswith('/shared-uploads/'):
        cloudinary_path = image_path.replace('/shared-uploads/', 'cablevision/')
        result = f"https://res.cloudinary.com/oa3fcr2b/image/upload/{cloudinary_path}"
        print(f"✅ Converted legacy path to: {result}")
        return result
    
    # If path starts with just 'plans/' (no cablevision prefix)
    if image_path.startswith('plans/'):
        result = f"https://res.cloudinary.com/oa3fcr2b/image/upload/cablevision/{image_path}"
        print(f"✅ Converted plans/ to: {result}")
        return result
    
    # Default: return as is
    print(f"⚠️ No matching condition, returning as is: {image_path}")
    return image_path


# Configure Cloudinary (gagamitin nito ang environment variables na na-set mo sa Railway)
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# ✅ I-ADD ITO: Ang /api/upload route
@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    folder = request.form.get('folder', 'general') 

    try:
        upload_result = cloudinary.uploader.upload(
            file, 
            folder=f"cablevision/{folder}"
        )
        image_url = upload_result['secure_url']
        
        return jsonify({
            'message': 'Upload successful!',
            'url': image_url,
            'public_id': upload_result['public_id']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



app.secret_key = "my_super_secure_random_key_12345"


def ensure_user_security_columns():
    try:
        columns = execute_query("SHOW COLUMNS FROM users", fetch=True) or []
        existing_fields = {col.get("Field") for col in columns if col.get("Field")}

        if "ga_secret" not in existing_fields:
            execute_query("ALTER TABLE users ADD COLUMN ga_secret VARCHAR(64) NULL")
        if "ga_enabled" not in existing_fields:
            execute_query("ALTER TABLE users ADD COLUMN ga_enabled TINYINT(1) NOT NULL DEFAULT 0")
        if "reset_code" not in existing_fields:
            execute_query("ALTER TABLE users ADD COLUMN reset_code VARCHAR(32) NULL")
    except Exception as e:
        print(f"Could not ensure user security columns: {e}")


def ensure_temp_reset_table():
    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS temp_reset (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NULL,
                otp VARCHAR(32) NULL,
                expiry DOUBLE NULL,
                user_type VARCHAR(32) NULL,
                area VARCHAR(255) NULL,
                username VARCHAR(255) NULL,
                new_password VARCHAR(255) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except Exception as e:
        print(f"Could not ensure temp_reset table: {e}")


def ensure_login_history_table():
    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS login_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                session_token VARCHAR(255) NOT NULL,
                device_info VARCHAR(255) NULL,
                browser VARCHAR(100) NULL,
                os VARCHAR(100) NULL,
                ip_address VARCHAR(100) NULL,
                location VARCHAR(255) NULL,
                login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'Active',
                INDEX idx_user_id (user_id),
                INDEX idx_session_token (session_token)
            )
        """)
        # Ensure `user_type` column exists (may be added later)
        cols = execute_query("SHOW COLUMNS FROM login_history", fetch=True) or []
        col_names = {c.get('Field') for c in cols if c.get('Field')}
        if 'user_type' not in col_names:
            try:
                execute_query("ALTER TABLE login_history ADD COLUMN user_type VARCHAR(32) NULL")
            except Exception:
                # Ignore if alter fails on certain MySQL versions
                pass
        else:
            # Backfill existing records with user role where missing
            try:
                execute_query(
                    "UPDATE login_history lh JOIN users u ON lh.user_id = u.user_id SET lh.user_type = u.role WHERE (lh.user_type IS NULL OR lh.user_type = '') AND u.role IS NOT NULL"
                )
            except Exception:
                pass
    except Exception as e:
        print(f"Could not ensure login_history table: {e}")


def parse_user_agent(ua_string):
    if not ua_string:
        return "Web Browser", "Windows"
    ua_lower = ua_string.lower()

    if "windows nt 10.0" in ua_lower:
        os_name = "Windows 10/11"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "mac os x" in ua_lower or "macintosh" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    else:
        os_name = "Desktop/Mobile"

    if "edg/" in ua_lower or "edge/" in ua_lower:
        browser = "Microsoft Edge"
    elif "chrome/" in ua_lower and "edg/" not in ua_lower:
        browser = "Google Chrome"
    elif "firefox/" in ua_lower:
        browser = "Mozilla Firefox"
    elif "safari/" in ua_lower and "chrome/" not in ua_lower:
        browser = "Apple Safari"
    elif "opera/" in ua_lower or "opr/" in ua_lower:
        browser = "Opera"
    else:
        browser = "Web Browser"

    return browser, os_name


def format_location_from_geo(city=None, region=None, country=None):
    parts = []
    if city:
        parts.append(city)
    if region and region.lower() != (city or '').lower():
        parts.append(region)
    if country and country.lower() not in ("ph", "philippines"):
        parts.append(country)
    elif country and not parts:
        parts.append(country)
    if not parts:
        return "Current Location"
    return ", ".join(parts)


def detect_location_from_ip(ip_addr):
    if not ip_addr or ip_addr in ("127.0.0.1", "::1", "localhost"):
        return None

    try:
        response = requests.get(f"https://ipapi.co/{ip_addr}/json/", timeout=3)
        if response.status_code == 200:
            data = response.json() or {}
            city = (data.get("city") or "").strip()
            region = (data.get("region") or data.get("region_name") or data.get("state") or "").strip()
            country = (data.get("country_name") or data.get("country") or "").strip()
            if city or region or country:
                return format_location_from_geo(city, region, country)
    except Exception:
        pass

    try:
        response = requests.get(f"http://ip-api.com/json/{ip_addr}", timeout=3)
        if response.status_code == 200:
            data = response.json() or {}
            if data.get("status") == "success":
                city = (data.get("city") or "").strip()
                region = (data.get("regionName") or data.get("region") or "").strip()
                country = (data.get("country") or "").strip()
                if city or region or country:
                    return format_location_from_geo(city, region, country)
    except Exception:
        pass

    return None


def resolve_device_location(ip_addr):
    location = (request.headers.get("X-Device-Location") or request.args.get("location") or request.form.get("location") or "").strip()
    if location:
        return location

    if ip_addr in ("127.0.0.1", "::1", "localhost") or ip_addr.startswith("192.168.") or ip_addr.startswith("10."):
        return "Local Device"

    detected = detect_location_from_ip(ip_addr)
    if detected:
        return detected

    return "Metro Manila, Philippines"


def record_login_history(user_id, tab_id=None):
    try:
        ensure_login_history_table()
        ua_string = request.headers.get("User-Agent", "")
        ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
        browser, os_name = parse_user_agent(ua_string)
        device_info = f"{browser} on {os_name}"
        location = resolve_device_location(ip_addr)

        session_token = tab_id if tab_id else f"sess_{user_id}_{int(time.time())}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Determine user_type/role from users table (server-side source of truth)
        user_type = 'user'
        try:
            user_row = execute_query("SELECT role FROM users WHERE user_id = %s LIMIT 1", (user_id,), fetch_one=True)
            if user_row and user_row.get('role'):
                role_val = (user_row.get('role') or '').lower()
                if role_val in ('admin', 'administrator'):
                    user_type = 'admin'
                elif role_val in ('customer', 'user', 'customer_user'):
                    user_type = 'user'
                else:
                    user_type = role_val
        except Exception:
            pass
        existing = execute_query(
            "SELECT id FROM login_history WHERE user_id = %s AND session_token = %s LIMIT 1",
            (user_id, session_token),
            fetch_one=True
        )

        if existing:
            execute_query(
                "UPDATE login_history SET last_active = %s, status = 'Active', ip_address = %s, location = %s, device_info = %s, user_type = %s WHERE id = %s",
                (now_str, ip_addr, location, device_info, user_type, existing["id"])
            )
        else:
            execute_query(
                """INSERT INTO login_history 
                   (user_id, session_token, device_info, browser, os, ip_address, location, login_time, last_active, status, user_type) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active', %s)""",
                (user_id, session_token, device_info, browser, os_name, ip_addr, location, now_str, now_str, user_type)
            )
        return session_token
    except Exception as e:
        print(f"[LOGIN HISTORY ERROR] {e}")
        return None


ensure_user_security_columns()
ensure_temp_reset_table()
ensure_login_history_table()


@app.after_request
def add_no_cache_headers(response):
    """Prevent caching of protected pages"""
    if request.endpoint in ['user_dashboard', 'user_profile', 'user_application_status', 'user_login_history']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response



# ===============================
# CHECK IF EMAIL IS DUPLICATE (MYSQL VERSION)
# ===============================
def is_email_duplicate_allowed(email, exclude_application_id=None):
    """
    Returns (is_blocked, existing_app_data)
    is_blocked = True  -> bawal gamitin ang email na ito (may pending/approved application)
    is_blocked = False -> pwede (walang existing non-rejected application)
    """
    try:
        # Query applications with this email
        query = """
            SELECT application_number as app_id, status, first_name, last_name 
            FROM applications 
            WHERE email = %s
        """
        applications = execute_query(query, (email,), fetch_all=True) or []
        
        for app in applications:
            app_id = app.get('app_id')
            status = app.get('status')
            
            # Kung ito ang sariling application (re-apply), huwag i-block
            if exclude_application_id and str(app_id) == str(exclude_application_id):
                continue
            
            # Kung ang status ay HINDI "Rejected" → bawal
            if status != 'Rejected':
                return True, app   # blocked
        
        return False, None   # allowed
        
    except Exception as e:
        print(f"Error checking email duplicate: {e}")
        return False, None


# ===============================
# GET ALLOWED BARANGAYS FROM MYSQL (WITH DEBUGGING)
# ===============================
def get_allowed_barangays():
    """Get allowed barangays dynamically from MySQL areas table"""
    try:
        print("🔍 DEBUG: Starting get_allowed_barangays()")
        
        connection = get_db_connection()

        if not connection:
            print("❌ DEBUG: Database connection failed")
            return get_fallback_barangays()

        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT DISTINCT UPPER(city) as city, UPPER(barangay) as barangay 
            FROM areas 
            ORDER BY city, barangay
        """
        cursor.execute(query)
        all_areas = cursor.fetchall()
        cursor.close()
        connection.close()
        
        print(f"🔍 DEBUG: Found {len(all_areas)} records in areas table")
        
        allowed_barangays = {}
        for area in all_areas:
            city = area.get("city", "").strip()
            barangay = area.get("barangay", "").strip()
            
            # Convert to UPPERCASE for consistent comparison
            city = city.upper()
            barangay = barangay.upper()
            
            if not barangay:
                continue
                
            if city not in allowed_barangays:
                allowed_barangays[city] = []
            
            if barangay not in allowed_barangays[city]:
                allowed_barangays[city].append(barangay)
        
        # Sort barangays alphabetically
        for city in allowed_barangays:
            allowed_barangays[city].sort()
        
        print(f"🔍 DEBUG: Final allowed_barangays: {allowed_barangays}")
        print(f"🔍 DEBUG: Cities found: {list(allowed_barangays.keys())}")
        
        return allowed_barangays
        
    except Exception as e:
        print(f"❌ Error getting allowed barangays: {e}")
        import traceback
        traceback.print_exc()
        return get_fallback_barangays()

# ===============================
# CACHED VERSION OF ALLOWED BARANGAYS
# ===============================
import time

_cached_allowed_barangays = None
_cached_timestamp = 0
CACHE_DURATION = 60  # 60 seconds

def get_cached_allowed_barangays():
    """Get cached allowed barangays (para hindi laging nagfa-fetch sa database)"""
    global _cached_allowed_barangays, _cached_timestamp
    now = time.time()
    
    if _cached_allowed_barangays is None or (now - _cached_timestamp) > CACHE_DURATION:
        print("🔍 DEBUG: Cache expired or empty, fetching from database...")
        _cached_allowed_barangays = get_allowed_barangays()
        _cached_timestamp = now
        print(f"🔍 DEBUG: Cached data: {_cached_allowed_barangays}")
        
    return _cached_allowed_barangays

# ===============================
# HELPER: GET BARANGAYS BY CITY
# ===============================
def get_barangays_by_city(city_name):
    """Get all barangays for a specific city from MySQL"""
    try:
        query = "SELECT barangay FROM areas WHERE city = %s ORDER BY barangay"
        results = execute_query(query, (city_name,), fetch_all=True) or []
        return [r.get('barangay') for r in results if r.get('barangay')]
    except Exception as e:
        print(f"Error getting barangays for {city_name}: {e}")
        return []


# ===============================
# HELPER: CHECK IF BARANGAY IS VALID
# ===============================
def is_valid_barangay(city_name, barangay_name):
    """Check if a barangay exists in the specified city"""
    try:
        query = """
            SELECT COUNT(*) as count 
            FROM areas 
            WHERE city = %s AND barangay = %s
        """
        result = execute_query(query, (city_name, barangay_name), fetch_one=True)
        return result.get('count', 0) > 0 if result else False
    except Exception as e:
        print(f"Error checking barangay: {e}")
        return False


# ===============================
# SERVE SHARED UPLOADS (para ma-access ang mga images)
# ===============================
import os
from flask import send_from_directory

import os

# Detect if running on Railway
IS_RAILWAY = os.environ.get('RAILWAY_ENVIRONMENT') is not None

if IS_RAILWAY:
    # Railway: Use shared volume
    SHARED_UPLOADS_BASE = '/app/uploads'
else:
    # Local: Use Windows path
    SHARED_UPLOADS_BASE = r"C:\xampp\htdocs\cablevision_uploads"


UPLOADS_FOLDER_NAME = "application_uploads"



@app.route('/shared-uploads/<path:filename>')
def serve_shared_uploads(filename):
    """Serve files from shared uploads folder"""
    # Security: prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
    
    return send_from_directory(SHARED_UPLOADS_BASE, filename)


@app.route("/")
def home():
    try:
        # Fetch plans from MySQL
        plans_data = execute_query(
            "SELECT id, name, speed, price, image_path FROM plans ORDER BY price ASC",
            fetch=True
        ) or []
        
        plan_list = []
        for plan in plans_data:
            image_path = plan.get("image_path", "")
            
            # ✅ I-PRINT PARA MAKITA SA LOGS
            print(f"📸 Raw image_path: {image_path}")
            
            cloudinary_url = get_cloudinary_url(image_path)
            
            # ✅ I-PRINT ANG RESULT
            print(f"✅ Cloudinary URL: {cloudinary_url}")
            
            plan_list.append({
                "id": plan.get("id"),
                "name": plan.get("name", ""),
                "speed": plan.get("speed", ""),
                "price": float(plan.get("price", 0)),
                "image": cloudinary_url
            })
        
        return render_template("user-homepage.html", plans=plan_list)
        
    except Exception as e:
        print(f"Home error: {e}")
        return render_template("user-homepage.html", plans=[])


# ===============================
# GET PLANS FOR SUPERADMIN (XAMPP/MYSQL)
# ===============================
@app.route("/api/superadmin/plans", methods=["GET"])
def get_plans():
    try:
        query = "SELECT id, name, speed, price, image_path FROM plans ORDER BY price ASC"
        plans_data = execute_query(query, fetch_all=True) or []
        
        plan_list = []
        for plan in plans_data:
            raw_image = plan.get("image_path", "")
            
            # Format image properly
            formatted_image = ""
            if raw_image:
                if raw_image.startswith('/shared-uploads/'):
                    formatted_image = raw_image
                elif not raw_image.startswith('data:image'):
                    formatted_image = f"data:image/png;base64,{raw_image}"
                else:
                    formatted_image = raw_image
            
            plan_list.append({
                "id": plan.get("id"),
                "name": plan.get("name", ""),
                "speed": plan.get("speed", ""),
                "price": float(plan.get("price", 0)),
                "image": formatted_image
            })

        return jsonify(plan_list)

    except Exception as e:
        print(f"Get plans error: {e}")
        return jsonify([])


# ===============================
# GET CHANNEL LOGOS FOR USER WEBSITE (XAMPP/MYSQL)
# ===============================
@app.route("/api/channel-logos", methods=["GET"])
def get_channel_logos_for_users():
    """Public endpoint for user website to fetch channel logos from MySQL"""
    try:
        # Query channel_logos from MySQL
        query = """
            SELECT id, image_path, date, timestamp
            FROM channel_logos 
            ORDER BY timestamp DESC
        """
        logos_data = execute_query(query, fetch_all=True) or []
        
        logo_list = []
        for logo in logos_data:
            image_path = logo.get("image_path", "")
            
            # I-format ang image path para ma-display
            formatted_image = ""
            if image_path:
                if image_path.startswith('/shared-uploads/'):
                    formatted_image = image_path
                elif image_path.startswith('data:image'):
                    formatted_image = image_path
                else:
                    # If it's a relative path, convert to shared-uploads URL
                    formatted_image = f"/shared-uploads/{image_path}"
            
            logo_list.append({
                "id": logo.get("id"),
                "name": f"logo_{logo.get('id')}",
                "image": formatted_image,
                "date": logo.get("date", "")
            })
        
        return jsonify(logo_list)
        
    except Exception as e:
        print(f"Error getting channel logos for users: {e}")
        return jsonify([])


# ===============================
# GET SINGLE CHANNEL LOGO (XAMPP/MYSQL)
# ===============================
@app.route("/api/channel-logos/<int:logo_id>", methods=["GET"])
def get_single_channel_logo(logo_id):
    """Get a single channel logo by ID"""
    try:
        query = "SELECT id, image_path, date FROM channel_logos WHERE id = %s"
        logo = execute_query(query, (logo_id,), fetch_one=True)
        
        if not logo:
            return jsonify({"error": "Logo not found"}), 404
        
        image_path = logo.get("image_path", "")
        formatted_image = ""
        if image_path:
            if image_path.startswith('/shared-uploads/'):
                formatted_image = image_path
            else:
                formatted_image = f"/shared-uploads/{image_path}"
        
        return jsonify({
            "id": logo.get("id"),
            "name": f"logo_{logo.get('id')}",
            "image": formatted_image,
            "date": logo.get("date", "")
        })
        
    except Exception as e:
        print(f"Error getting channel logo: {e}")
        return jsonify({"error": str(e)}), 500
    
# ===============================
# PUBLIC ENDPOINTS FOR USER HOMEPAGE (XAMPP/MYSQL)
# ===============================

@app.route('/api/public/plans')
def public_plans():
    """Public endpoint for plans"""
    try:
        plans = execute_query(
            "SELECT id, name, speed, price, image_path FROM plans ORDER BY price ASC",
            fetch=True
        ) or []
        
        # Format the response
        plan_list = []
        for plan in plans:
            image_path = plan.get('image_path', '')
            if image_path and image_path.startswith('/shared-uploads/'):
                formatted_image = image_path
            else:
                formatted_image = image_path or ''
            
            plan_list.append({
                "id": plan['id'],
                "name": plan['name'],
                "speed": plan['speed'],
                "price": float(plan['price']) if plan['price'] else 0,
                "image": formatted_image
            })
        
        return jsonify(plan_list)
    except Exception as e:
        print(f"Public plans error: {e}")
        return jsonify([])


# ===============================
# PUBLIC ADVERTISEMENTS API (for homepage - both images and videos)
# ===============================
@app.route("/api/public/advertisements", methods=["GET"])
def get_public_advertisements():
    """Public endpoint for homepage to fetch both images and videos from advertisements table"""

    conn = None
    cursor = None
    try:
        print("🔍 Fetching advertisements for public homepage...")
        
        conn = get_db_connection()

        if not conn:
            print("❌ Database connection failed")
            return jsonify([])

        cursor = conn.cursor(dictionary=True)
        
        # Query to get both images and videos from advertisements table
        query = """
            SELECT id, file_path, file_type, file_size, date, timestamp, created_at
            FROM advertisements 
            WHERE file_type IN ('image', 'video')
            ORDER BY timestamp DESC
        """
        cursor.execute(query)
        ads = cursor.fetchall()
        
        print(f"📊 Found {len(ads)} advertisements total")
        
        ad_list = []
        for ad in ads:
            ad_list.append({
                "id": ad['id'],
                "filePath": ad.get('file_path', ''),
                "fileType": ad.get('file_type', 'image'),
                "fileSize": ad.get('file_size', 0),
                "date": ad.get('date', ''),
                "timestamp": ad.get('timestamp', 0)
            })
        
        # Count for debugging
        images = [a for a in ad_list if a['fileType'] == 'image']
        videos = [a for a in ad_list if a['fileType'] == 'video']
        print(f"📸 Images: {len(images)}, 🎬 Videos: {len(videos)}")
        
        return jsonify(ad_list)
        
    except Exception as e:
        print(f"❌ Error getting public advertisements: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/public/announcements')
def public_announcements():
    """Public endpoint for announcements - ginagamit ng announcements modal"""
    try:
        current_time_utc = datetime.utcnow().isoformat() + "Z"
        
        query = """
            SELECT id, title, message, image_path, date, timestamp, expirationDate
            FROM announcements 
            WHERE expirationDate IS NULL OR expirationDate > %s
            ORDER BY timestamp DESC
        """
        announcements = execute_query(query, (current_time_utc,), fetch_all=True) or []
        
        result = []
        for ann in announcements:
            image_path = ann.get('image_path', '')
            if image_path and image_path.startswith('/shared-uploads/'):
                formatted_image = image_path
            else:
                formatted_image = image_path or ''
            
            result.append({
                "id": ann['id'],
                "title": ann.get('title', ''),
                "message": ann.get('message', ''),
                "imageBase64": formatted_image,
                "date": ann.get('date', ''),
                "timestamp": ann.get('timestamp', 0),
                "expirationDate": ann.get('expirationDate', '')
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Public announcements error: {e}")
        return jsonify([])

@app.route('/api/public/channel-logos')
def public_channel_logos():
    """Public endpoint for channel logos"""
    try:
        logos = execute_query(
            "SELECT id, image_path, date FROM channel_logos ORDER BY timestamp DESC",
            fetch=True
        ) or []
        
        result = []
        for logo in logos:
            image_path = logo.get('image_path', '')
            if image_path and image_path.startswith('/shared-uploads/'):
                formatted_image = image_path
            else:
                formatted_image = image_path or ''
            
            result.append({
                "id": logo['id'],
                "image": formatted_image,
                "name": f"logo_{logo['id']}",
                "date": logo.get('date', '')
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Public channel logos error: {e}")
        return jsonify([])


@app.route("/contact-us")
def contact_us():
    return render_template("user-contact-us.html")

@app.route("/coverage")
def coverage():
    return render_template("user-coverage.html")

@app.route("/api/areas")
def get_public_areas():
    """Public endpoint para kunin ang lahat ng areas"""
    try:
        areas_data = execute_query(
            "SELECT id, province, city, barangay, zip FROM areas ORDER BY city, barangay",
            fetch=True
        ) or []
        
        result = []
        for area in areas_data:
            result.append({
                "id": area.get("id"),
                "province": area.get("province", ""),
                "city": area.get("city", ""),
                "barangay": area.get("barangay", ""),
                "zip": area.get("zip", "")
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error getting areas: {e}")
        return jsonify([])



@app.route("/plans")
def plans():
    try:
        plans_data = execute_query(
            "SELECT id, name, speed, price, image_path FROM plans ORDER BY price ASC",
            fetch=True
        ) or []
        
        plan_list = []
        for plan in plans_data:
            image_path = plan.get("image_path", "")
            
            # Debug: print para makita ang actual na path
            print(f"Plan: {plan.get('name')}, Image path: {image_path}")
            
            # Format image path correctly
            if image_path and image_path.startswith('/shared-uploads/'):
                formatted_image = image_path
            elif image_path:
                # If path doesn't start with /shared-uploads, add it
                formatted_image = f"/shared-uploads/plans/{image_path.split('/')[-1]}"
            else:
                formatted_image = ''
            
            plan_list.append({
                "id": plan.get("id"),
                "name": plan.get("name", ""),
                "speed": plan.get("speed", ""),
                "price": float(plan.get("price", 0)),
                "image": formatted_image
            })
        
        # Get selected plan from query string
        selected_plan = request.args.get("selected", "")
        
        return render_template("user-plans.html", plans=plan_list, selected_plan=selected_plan)
        
    except Exception as e:
        print(f"Plans page error: {e}")
        import traceback
        traceback.print_exc()
        return render_template("user-plans.html", plans=[], selected_plan="")

# =========================
# APPLY PLAN PAGE (ALREADY CONVERTED - OK NA)
# =========================
@app.route("/apply/<plan_name>")
def apply_plan(plan_name):
    # Check if this is a re-apply
    form_data = request.args.get('form_data')
    is_reapply = request.args.get('reapply') == 'true'
    original_id = request.args.get('app_id')
    
    # Fetch plan details from MySQL
    try:
        query = """
            SELECT id, name, speed, price, image_path 
            FROM plans 
            WHERE name = %s OR id = %s
            ORDER BY price ASC
            LIMIT 1
        """
        plan_data = execute_query(query, (plan_name, plan_name), fetch_one=True)
        
        if plan_data:
            plan_speed = plan_data.get('speed', 'N/A')
            plan_price = f"₱{float(plan_data.get('price', 0)):.2f}/month"
            plan_display_name = plan_data.get('name', plan_name)
        else:
            plan_speed = 'N/A'
            plan_price = 'Contact us'
            plan_display_name = plan_name
        
        return render_template(
            "user-application.html", 
            plan_name=plan_display_name,
            plan_speed=plan_speed,
            plan_price=plan_price,
            form_data=form_data if form_data else None,
            is_reapply=is_reapply,
            original_application_id=original_id
        )
        
    except Exception as e:
        print(f"Error fetching plan details: {e}")
        return render_template(
            "user-application.html", 
            plan_name=plan_name,
            plan_speed='N/A',
            plan_price='Contact us',
            form_data=None,
            is_reapply=False,
            original_application_id=None
        )


# =========================
# GET AREAS FOR USER (MYSQL VERSION)
# =========================
@app.route("/api/areas")
def get_areas():
    """Get all areas from MySQL"""
    try:
        query = """
            SELECT id, province, city, barangay, zip 
            FROM areas 
            ORDER BY city, barangay
        """
        areas_data = execute_query(query, fetch_all=True) or []
        
        result = []
        for area in areas_data:
            result.append({
                "id": area.get("id"),
                "province": area.get("province", ""),
                "city": area.get("city", ""),
                "barangay": area.get("barangay", ""),
                "zip": area.get("zip", "")
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error getting areas: {e}")
        return jsonify([]), 500


# =========================
# VALIDATE AREA (MYSQL VERSION)
# =========================
@app.route("/api/areas/validate", methods=["POST"])
def validate_area():
    """Check if province/city/barangay combination exists in service coverage"""
    try:
        data = request.json
        province = data.get("province", "").upper().strip()
        city = data.get("city", "").upper().strip()
        barangay = data.get("barangay", "").upper().strip()
        
        if not province or not city or not barangay:
            return jsonify({
                "valid": False, 
                "message": "Province, city, and barangay are required"
            }), 400
        
        query = """
            SELECT id, zip FROM areas 
            WHERE province = %s AND city = %s AND barangay = %s
            LIMIT 1
        """
        area = execute_query(query, (province, city, barangay), fetch_one=True)
        
        if area:
            return jsonify({
                "valid": True,
                "zip": area.get("zip", ""),
                "message": "Location is within service area"
            })
        
        return jsonify({
            "valid": False, 
            "message": "This location is not yet covered by our service area"
        })
        
    except Exception as e:
        print(f"Error validating area: {e}")
        return jsonify({"valid": False, "error": str(e)}), 500


# =========================
# GET BARANGAYS BY CITY (MYSQL VERSION)
# =========================
@app.route("/api/areas/by-city/<city>")
def get_areas_by_city(city):
    """Get barangays by city name"""
    cursor = None
    connection = None

    try:
        print(f"🔍 Getting barangays for city: {city}")

        connection = get_db_connection()

        if not connection:
            print("❌ Database connection failed")
            return jsonify([]), 500

        cursor = connection.cursor(dictionary=True)

        # I-print ang lahat ng cities sa database
        cursor.execute("SELECT DISTINCT city FROM areas")
        all_cities = cursor.fetchall()
        print(f"📊 Cities in database: {all_cities}")

        # Query para sa specific city
        # Tinatanggal ang extra spaces at trailing comma
        query = """
            SELECT id, barangay, zip
            FROM areas
            WHERE UPPER(TRIM(TRAILING ',' FROM TRIM(city))) =
                  UPPER(TRIM(TRAILING ',' FROM TRIM(%s)))
            ORDER BY barangay
        """

        cursor.execute(query, (city,))
        areas_data = cursor.fetchall()

        print(f"📊 Found {len(areas_data)} barangays for {city}")
        print(f"📊 Data: {areas_data}")

        result = []

        for area in areas_data:
            result.append({
                "id": area.get("id"),
                "barangay": area.get("barangay", ""),
                "zip": area.get("zip", "")
            })

        return jsonify(result)

    except Exception as e:
        print(f"❌ Error: {e}")

        import traceback
        traceback.print_exc()

        return jsonify([]), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================
# GET ALL CITIES (MYSQL VERSION)
# =========================
@app.route("/api/areas/cities")
def get_all_cities():
    """Get all unique cities from service areas"""
    try:
        query = """
            SELECT DISTINCT city 
            FROM areas 
            ORDER BY city
        """
        cities_data = execute_query(query, fetch_all=True) or []
        
        cities = [c.get("city") for c in cities_data if c.get("city")]
        
        return jsonify(cities)
        
    except Exception as e:
        print(f"Error getting cities: {e}")
        return jsonify([]), 500

# ===============================
# APPLICATION SUBMIT
# ===============================
from flask import abort

# ===============================
# VALIDATE LOCATION BARANGAY (FIXED - UPPERCASE COMPARISON)
# ===============================

MAINTENANCE_LOCATION_MESSAGE = "We are currently under maintenance. You cannot apply at the moment. Please try again later."


def validate_location_barangay(lat, lng):
    import requests
    import json
    
    try:
        georisk_url = "https://portal.georisk.gov.ph/arcgis/rest/services/PSA/Barangay/MapServer/4/query"
        
        query_params = {
            "geometry": f"{lng},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "outFields": "brgy_name,city_name,prov_name",
            "returnGeometry": "false",
            "f": "geojson"
        }
        
        response = requests.get(georisk_url, params=query_params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("features") and len(data["features"]) > 0:
                props = data["features"][0]["properties"]
                detected_city = props.get("city_name", "").upper()
                detected_barangay = props.get("brgy_name", "").upper()
                
                print(f"📍 GeoRisk detected: City='{detected_city}', Barangay='{detected_barangay}'")
                
                if detected_city and detected_barangay:
                    ALLOWED_CITIES = ["SANTA CRUZ", "PAGSANJAN", "PILA", "MAGDALENA"]
                    
                    if detected_city not in ALLOWED_CITIES:
                        return False, f"'{detected_city}' is not within our coverage area."
                    
                    # Convert detected barangay to match database format
                    converted_barangay = detected_barangay
                    converted_barangay = converted_barangay.replace('(POB.)', '(POBLACION)')
                    
                    # Special handling for Pila
                    if detected_city == "PILA":
                        if "BULILAN NORTE" in converted_barangay:
                            converted_barangay = "BULILAN NORTE (POBLACION)"
                        elif "BULILAN SUR" in converted_barangay:
                            converted_barangay = "BULILAN SUR (POBLACION)"
                        elif "SANTA CLARA NORTE" in converted_barangay:
                            converted_barangay = "SANTA CLARA NORTE (POBLACION)"
                        elif "SANTA CLARA SUR" in converted_barangay:
                            converted_barangay = "SANTA CLARA SUR (POBLACION)"
                    
                    allowed_barangays = get_cached_allowed_barangays()
                    
                    if detected_city not in allowed_barangays:
                        return False, f"'{detected_city}' is not found in our database."
                    
                    # Check if converted barangay is in allowed list
                    if converted_barangay not in allowed_barangays[detected_city]:
                        return False, f"Barangay '{detected_barangay}' is not within our coverage area for {detected_city}."
                    
                    print(f"✅ Location validated: {detected_city}, {converted_barangay}")
                    return True, converted_barangay
            
            # Fallback to OSM
            print("⚠️ GeoRisk returned no data, trying OSM fallback...")
            osm_url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}"
            osm_response = requests.get(osm_url, headers={"User-Agent": "CableVision-App"}, timeout=10)
            osm_data = osm_response.json()
            osm_addr = osm_data.get("address", {})
            
            fallback_city = osm_addr.get("town") or osm_addr.get("city") or osm_addr.get("municipality") or ""
            fallback_barangay = osm_addr.get("village") or osm_addr.get("suburb") or osm_addr.get("neighbourhood") or ""
            
            if fallback_city and fallback_barangay:
                fallback_city = fallback_city.upper()
                fallback_barangay = fallback_barangay.upper()
                ALLOWED_CITIES = ["SANTA CRUZ", "PAGSANJAN", "PILA", "MAGDALENA"]
                
                if fallback_city not in ALLOWED_CITIES:
                    return False, f"'{fallback_city}' is not within our coverage area."
                
                allowed_barangays = get_cached_allowed_barangays()
                
                if fallback_city not in allowed_barangays:
                    return False, f"'{fallback_city}' is not found in our database."
                
                if fallback_barangay not in allowed_barangays[fallback_city]:
                    return False, f"Barangay '{fallback_barangay}' is not within our coverage area for {fallback_city}."
                
                return True, fallback_barangay
            
            return False, MAINTENANCE_LOCATION_MESSAGE
        
        else:
            return False, MAINTENANCE_LOCATION_MESSAGE
            
    except requests.exceptions.Timeout:
        return False, MAINTENANCE_LOCATION_MESSAGE
    except Exception as e:
        print(f"Location validation error: {e}")
        import traceback
        traceback.print_exc()
        return False, MAINTENANCE_LOCATION_MESSAGE



# ===============================
# APPLICATION SUBMIT (XAMPP/MYSQL VERSION WITH FILE UPLOADS)
# ===============================
@app.route("/submit_application", methods=["POST"])
def submit_application():
    import io
    from PIL import Image
    import json
    import os
    from datetime import datetime

    data = request.form
    now = datetime.now()
    
    # ========== HELPER: CONVERT BIRTHDATE FORMAT ==========
    def convert_birthdate_format(birthdate_str):
        """Convert MM-DD-YYYY to YYYY-MM-DD for MySQL date column"""
        if not birthdate_str:
            return None
        try:
            parts = birthdate_str.split('-')
            if len(parts) == 3:
                month = parts[0].zfill(2)
                day = parts[1].zfill(2)
                year = parts[2]
                # I-validate na ang year ay 4 digits
                if len(year) == 4 and year.isdigit():
                    return f"{year}-{month}-{day}"
            return birthdate_str
        except:
            return birthdate_str
    
    # ========== HELPER FUNCTION PARA SA OPTIONAL FIELDS ==========
    def get_optional_field(field_name):
        """Get optional field value, checking _submitted hidden field first"""
        # Unahin ang _submitted version (galing sa hidden field)
        submitted_key = f'{field_name}_submitted'
        if submitted_key in request.form:
            value = request.form[submitted_key]
            print(f"📥 {field_name} from _submitted: '{value}'")
            return value
        
        # Kung wala, balik sa regular field
        value = request.form.get(field_name, '')
        print(f"📥 {field_name} from regular: '{value}'")
        return value if value else ''
    
    # ========== GET ALL OPTIONAL FIELD VALUES ==========
    middle_name = get_optional_field('middle_name')
    suffix = get_optional_field('suffix')
    secondary_mobile = get_optional_field('secondary_mobile')
    phone = get_optional_field('phone')
    address = get_optional_field('address')
    house_number = get_optional_field('house_number')
    business_phone = get_optional_field('business_phone')
    spouse_name = get_optional_field('spouse_name')
    spouse_occupation = get_optional_field('spouse_occupation')
    spouse_employer = get_optional_field('spouse_employer')
    spouse_phone = get_optional_field('spouse_phone')
    father_name = get_optional_field('father_name')
    mother_maiden_name = get_optional_field('mother_maiden_name')
    
    # ========== CONVERT BIRTHDATE ==========
    birthdate_raw = data.get('birthdate', '')
    birthdate = convert_birthdate_format(birthdate_raw)
    print(f"📅 Birthdate converted: '{birthdate_raw}' -> '{birthdate}'")
    
    # ========== TV FIELDS (special handling) ==========
    def get_tv_field_values(prefix, count):
        """Get TV field values from either regular or submitted fields"""
        values = []
        for i in range(count):
            # Check kung may _submitted version
            submitted_key = f'{prefix}_{i}_submitted'
            if submitted_key in request.form:
                values.append(request.form[submitted_key])
                print(f"📥 {prefix}[{i}] from _submitted: '{request.form[submitted_key]}'")
            else:
                # Kunin mula sa regular list
                regular_values = request.form.getlist(f'{prefix}[]')
                if i < len(regular_values) and regular_values[i]:
                    values.append(regular_values[i])
                    print(f"📥 {prefix}[{i}] from regular: '{regular_values[i]}'")
                else:
                    values.append('')
                    print(f"📥 {prefix}[{i}] is empty")
        return values
    
    # Kunin ang TV values
    tv_qty_raw = request.form.getlist('tv_qty[]')
    tv_brand_raw = request.form.getlist('tv_brand[]')
    tv_type_raw = request.form.getlist('tv_type[]')
    
    tv_count = max(len(tv_qty_raw), len(tv_brand_raw), len(tv_type_raw))
    
    tv_qty = get_tv_field_values('tv_qty', tv_count)
    tv_brand = get_tv_field_values('tv_brand', tv_count)
    tv_type = get_tv_field_values('tv_type', tv_count)
    
    # I-convert sa JSON (para sa database)
    tv_qty_json = json.dumps(tv_qty) if tv_qty and any(tv_qty) else None
    tv_brand_json = json.dumps(tv_brand) if tv_brand and any(tv_brand) else None
    tv_type_json = json.dumps(tv_type) if tv_type and any(tv_type) else None
    
    # ========== I-PRINT PARA MAKITA KUNG GUMAWA ==========
    print("\n" + "="*50)
    print(" OPTIONAL FIELD VALUES (FROM BACKEND):")
    print("="*50)
    print(f"middle_name: '{middle_name}'")
    print(f"suffix: '{suffix}'")
    print(f"secondary_mobile: '{secondary_mobile}'")
    print(f"phone: '{phone}'")
    print(f"address: '{address}'")
    print(f"house_number: '{house_number}'")
    print(f"business_phone: '{business_phone}'")
    print(f"spouse_name: '{spouse_name}'")
    print(f"spouse_occupation: '{spouse_occupation}'")
    print(f"spouse_employer: '{spouse_employer}'")
    print(f"spouse_phone: '{spouse_phone}'")
    print(f"father_name: '{father_name}'")
    print(f"mother_maiden_name: '{mother_maiden_name}'")
    print("="*50)
    print(f"TV Qty: {tv_qty}")
    print(f"TV Brand: {tv_brand}")
    print(f"TV Type: {tv_type}")
    print("="*50 + "\n")
    
    
    
    def save_uploaded_file(file_input, application_number, file_type, max_size=(800, 800), quality=75):
        """Save uploaded file to shared uploads folder and return URL path"""
        if not file_input or file_input.filename == '':
            return None
        
        try:
            # Open and process image
            img = Image.open(file_input)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Create folder structure: cablevision_uploads/application_uploads/[application_number]/
            app_folder = os.path.join(SHARED_UPLOADS_BASE, UPLOADS_FOLDER_NAME, application_number)
            if not os.path.exists(app_folder):
                os.makedirs(app_folder)
                print(f"📁 Created folder: {app_folder}")
            
            # Generate filename with timestamp
            timestamp = int(time.time())
            filename = f"{file_type}_{timestamp}.jpg"
            file_path = os.path.join(app_folder, filename)
            
            # Save image
            img.save(file_path, format='JPEG', quality=quality, optimize=True)
            
            # Return URL path (for database and template)
            url_path = f"/shared-uploads/{UPLOADS_FOLDER_NAME}/{application_number}/{filename}"
            print(f"✅ Image saved: {file_path} -> URL: {url_path}")
            return url_path
            
        except Exception as e:
            print(f"❌ Error saving {file_type}: {e}")
            return None
    
    def save_base64_image(base64_string, application_number, file_type, max_size=(800, 800), quality=75):
        """Save base64 image to shared uploads folder and return URL path"""
        if not base64_string:
            return None
        
        try:
            # Remove data:image prefix if present
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',', 1)[1]
            
            # Decode base64
            img_data = base64.b64decode(base64_string)
            img = Image.open(io.BytesIO(img_data))
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Create folder structure
            app_folder = os.path.join(SHARED_UPLOADS_BASE, UPLOADS_FOLDER_NAME, application_number)
            if not os.path.exists(app_folder):
                os.makedirs(app_folder)
                print(f"📁 Created folder: {app_folder}")
            
            # Generate filename with timestamp
            timestamp = int(time.time())
            filename = f"{file_type}_{timestamp}.jpg"
            file_path = os.path.join(app_folder, filename)
            
            # Save image
            img.save(file_path, format='JPEG', quality=quality, optimize=True)
            
            # Return URL path
            url_path = f"/shared-uploads/{UPLOADS_FOLDER_NAME}/{application_number}/{filename}"
            print(f"✅ Base64 image saved: {file_path} -> URL: {url_path}")
            return url_path
            
        except Exception as e:
            print(f"❌ Error saving base64 {file_type}: {e}")
            return None

    # ========== CHECK EMAIL VERIFICATION ==========
    email = data.get('email')
    if not email:
        return 'Email is required', 400
    
    if session.get('email_verified') != email:
        return 'Please verify your email address before submitting.', 400
    
    verified_time = session.get('email_verified_time', 0)
    if time.time() - verified_time > 300:
        session.pop('email_verified', None)
        session.pop('email_verified_time', None)
        return 'Email verification has expired. Please verify again.', 400

    # ========== CHECK IF THIS IS A RE-APPLICATION ==========
    is_reapply = data.get('is_reapply') == 'true'
    original_application_id = data.get('original_application_id')
    
    if is_reapply and original_application_id:
        check_query = """
            SELECT status, reapplied_count, rejection_reason, date_submitted, 
                   signature, id_front, id_back, proof_billing, profile_photo
            FROM applications 
            WHERE application_number = %s
        """
        existing_app = execute_query(check_query, (original_application_id,), fetch_one=True)
        
        if not existing_app:
            print(f"❌ Re-apply failed: Application {original_application_id} not found")
            return 'Application not found. Please contact support.', 404
        
        if existing_app.get('status') != 'Rejected':
            print(f"❌ Re-apply failed: Application {original_application_id} status is {existing_app.get('status')}, not Rejected")
            return 'This application cannot be re-applied. Only rejected applications are eligible.', 400
        
        reapplied_count = existing_app.get('reapplied_count', 0)
        if reapplied_count >= 2:
            print(f"❌ Re-apply failed: Application {original_application_id} has already re-applied {reapplied_count} times (max 2)")
            return 'You have already re-applied twice. Further re-applications are not allowed.', 400
        
        application_number = original_application_id
        print(f"🔄 Re-applying application #{application_number} (reapplied_count={reapplied_count})")
    else:
        application_number = str(random.randint(1000000000, 9999999999))
        print(f"📝 New application #{application_number}")

    # ========== PROCESS SIGNATURE ==========
    signature_value = None
    signature_upload = request.files.get('signature_upload')
    signature_drawn = request.form.get('signature_drawn')
    
    if signature_upload and signature_upload.filename != '':
        signature_value = save_uploaded_file(signature_upload, application_number, 'signature', max_size=(500, 200), quality=70)
    elif signature_drawn:
        signature_value = save_base64_image(signature_drawn, application_number, 'signature', max_size=(500, 200), quality=70)

    # ========== PROCESS DOCUMENTS ==========
    id_front_file = request.files.get('id_front')
    id_back_file = request.files.get('id_back')
    billing_file = request.files.get('proof_billing')
    profile_file = request.files.get('profile_photo')
    
    id_front_value = save_uploaded_file(id_front_file, application_number, 'id_front', max_size=(600, 600), quality=75) if id_front_file and id_front_file.filename != '' else None
    id_back_value = save_uploaded_file(id_back_file, application_number, 'id_back', max_size=(600, 600), quality=75) if id_back_file and id_back_file.filename != '' else None
    billing_value = save_uploaded_file(billing_file, application_number, 'proof_billing', max_size=(600, 600), quality=75) if billing_file and billing_file.filename != '' else None
    profile_value = save_uploaded_file(profile_file, application_number, 'profile_photo', max_size=(300, 300), quality=80) if profile_file and profile_file.filename != '' else None

    # ========== LOCATION VALIDATION ==========
    lat = data.get('latitude')
    lng = data.get('longitude')
    if lat and lng:
        try:
            lat = float(lat)
            lng = float(lng)
            ok, err_msg = validate_location_barangay(lat, lng)
            if not ok:
                if err_msg == MAINTENANCE_LOCATION_MESSAGE:
                    return MAINTENANCE_LOCATION_MESSAGE, 400
                return f"Location not allowed: {err_msg}", 400
        except:
            return "Invalid latitude/longitude", 400
    else:
        return "Please pin your location on the map", 400

    # ========== GET EXISTING DATA FOR RE-APPLY ==========
    existing_app_data = {}
    reapplied_count_value = 0
    if is_reapply and original_application_id:
        existing_app_data = existing_app or {}
        reapplied_count_value = existing_app.get('reapplied_count', 0) + 1

    # ========== GET SELECTED NAP BOX FROM FORM ==========
    selected_napbox_info = data.get('selected_napbox_info')
    preferred_napbox_id = None
    preferred_napbox_name = None
    
    if selected_napbox_info:
        try:
            napbox_data = json.loads(selected_napbox_info)
            preferred_napbox_id = napbox_data.get('napbox_id')
            preferred_napbox_name = napbox_data.get('napbox_name')
            if preferred_napbox_id:
                print(f"📌 User selected NAP Box: {preferred_napbox_name} (ID: {preferred_napbox_id}) - SAVING TO DATABASE")
        except Exception as e:
            print(f"⚠️ Error parsing napbox info: {e}")

    # ========== CHECK IF APPLICATION ALREADY EXISTS (for re-apply) ==========
    if is_reapply and original_application_id:
        update_query = """
            UPDATE applications SET
                plan = %s, plan_speed = %s, plan_price = %s,
                date_submitted = %s, time_submitted = %s, timestamp = %s,
                first_name = %s, middle_name = %s, last_name = %s, suffix = %s,
                email = %s, mobile = %s, secondary_mobile = %s, phone = %s,
                birthdate = %s, place_of_birth = %s, mother_maiden_name = %s,
                father_name = %s, sex = %s, civil_status = %s, citizenship = %s,
                occupation = %s, home_ownership = %s, address = %s, billing_address = %s,
                barangay = %s, city = %s, province = %s, zip = %s,
                house_number = %s, landmark = %s, employer = %s,
                business_address = %s, business_phone = %s, spouse_name = %s,
                spouse_occupation = %s, spouse_employer = %s, spouse_phone = %s,
                service_type = %s, tv_qty = %s, tv_brand = %s, tv_type = %s,
                installation_address = %s, installation_phone = %s, installation_fee = %s,
                signature = %s, id_front = %s, id_back = %s, proof_billing = %s, profile_photo = %s,
                latitude = %s, longitude = %s, status = %s, reapplied_count = %s,
                preferred_napbox_id = %s, preferred_napbox_name = %s,
                reapply_requested = 0, reapply_requested_at = NULL, reapply_message = NULL,
                is_archived = 0
            WHERE application_number = %s
        """

        params = (
            data.get('plan'), data.get('plan_speed'), data.get('plan_price'),
            now.strftime('%B %d, %Y'), now.strftime('%I:%M %p'), now.timestamp(),
            data.get('first_name'), middle_name, data.get('last_name'), suffix,
            email, data.get('mobile'), secondary_mobile, phone,
            birthdate,  # ✅ CONVERTED BIRTHDATE
            data.get('place_of_birth'), mother_maiden_name,
            father_name, data.get('sex'), data.get('civil_status'), data.get('citizenship'),
            data.get('occupation'), data.get('home_ownership'), address, data.get('billing_address'),
            data.get('barangay'), data.get('city'), data.get('province'), data.get('zip'),
            house_number, data.get('landmark'), data.get('employer'),
            data.get('business_address'), business_phone, spouse_name,
            spouse_occupation, spouse_employer, spouse_phone,
            data.get('service_type'), tv_qty_json, tv_brand_json, tv_type_json,
            data.get('installation_address'), data.get('installation_phone'), data.get('installation_fee'),
            signature_value or existing_app_data.get('signature'),
            id_front_value or existing_app_data.get('id_front'),
            id_back_value or existing_app_data.get('id_back'),
            billing_value or existing_app_data.get('proof_billing'),
            profile_value or existing_app_data.get('profile_photo'),
            data.get('latitude'), data.get('longitude'), 'Pending', reapplied_count_value,
            preferred_napbox_id, preferred_napbox_name,
            application_number
        )

        execute_query(update_query, params)
        print(f"✅ Application {application_number} updated (re-apply) with preferred NAP Box: {preferred_napbox_name}")
        
    else:
        insert_query = """
            INSERT INTO applications (
                application_number, plan, plan_speed, plan_price,
                date_submitted, time_submitted, timestamp,
                first_name, middle_name, last_name, suffix, email,
                mobile, secondary_mobile, phone, birthdate, place_of_birth,
                mother_maiden_name, father_name, sex, civil_status, citizenship,
                occupation, home_ownership, address, billing_address,
                barangay, city, province, zip, house_number, landmark,
                employer, business_address, business_phone,
                spouse_name, spouse_occupation, spouse_employer, spouse_phone,
                service_type, tv_qty, tv_brand, tv_type,
                installation_address, installation_phone, installation_fee,
                signature, id_front, id_back, proof_billing, profile_photo,
                latitude, longitude, status, reapplied_count,
                preferred_napbox_id, preferred_napbox_name
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s
            )
        """

        params = (
            application_number,
            data.get('plan'), data.get('plan_speed'), data.get('plan_price'),
            now.strftime('%B %d, %Y'), now.strftime('%I:%M %p'), now.timestamp(),
            data.get('first_name'), middle_name, data.get('last_name'), suffix, email,
            data.get('mobile'), secondary_mobile, phone,
            birthdate,  # ✅ CONVERTED BIRTHDATE
            data.get('place_of_birth'), mother_maiden_name,
            father_name, data.get('sex'), data.get('civil_status'), data.get('citizenship'),
            data.get('occupation'), data.get('home_ownership'), address, data.get('billing_address'),
            data.get('barangay'), data.get('city'), data.get('province'), data.get('zip'), house_number, data.get('landmark'),
            data.get('employer'), data.get('business_address'), business_phone,
            spouse_name, spouse_occupation, spouse_employer, spouse_phone,
            data.get('service_type'), tv_qty_json, tv_brand_json, tv_type_json,
            data.get('installation_address'), data.get('installation_phone'), data.get('installation_fee'),
            signature_value, id_front_value, id_back_value, billing_value, profile_value,
            data.get('latitude'), data.get('longitude'), 'Pending', 0,
            data.get('preferred_napbox_id'), data.get('preferred_napbox_name')
        )

        print(f"📊 Number of params: {len(params)}")
        print(f"📊 Expected: 57 (55 original + 2 for preferred napbox)")
        print(f"📊 Application Number: {application_number}")
        print(f"📅 Birthdate saved as: {birthdate}")
        
        if preferred_napbox_id:
            print(f"📌 Preferred NAP Box saved: {preferred_napbox_name} (ID: {preferred_napbox_id})")

        result = execute_query(insert_query, params)
        print(f"✅ Insert result: {result}")
        print(f"✅ New application {application_number} saved with preferred NAP Box")

    # ========== CREATE NOTIFICATIONS ==========
    try:
        notification_id = int(datetime.now().timestamp() * 1000)
        applicant_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
        application_city = data.get('city', 'Unknown')
        reapply_text = " (RE-APPLICATION)" if is_reapply else ""
        
        notif_query = """
            INSERT INTO notifications (id, title, message, type, relatedId, timestamp, read_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(notif_query, (
            notification_id,
            f"New Application{reapply_text}",
            f"New {data.get('plan')} Plan from {applicant_name}, Application No.({application_number}) in {application_city}",
            "new_application",
            application_number,
            datetime.now().isoformat(),
            0
        ))
        print(f"🔔 Superadmin notification created")
        
        admin_notif_id = notification_id + 1
        admin_notif_query = """
            INSERT INTO admin_notifications (
                id, title, message, type, relatedId, timestamp, read_status,
                admin_city, application_city, application_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(admin_notif_query, (
            admin_notif_id,
            f"New Application in Your Area{reapply_text}",
            f"New {data.get('plan')} Plan application from {applicant_name} (Application No. {application_number}) in {application_city}",
            "new_application",
            application_number,
            datetime.now().isoformat(),
            0,
            application_city,
            application_city,
            application_number
        ))
        print(f"🔔 Admin notification created for city: {application_city}")
        
    except Exception as e:
        print(f"⚠️ Notification failed: {e}")

    # ========== 🔒 SAFEGUARD: ENSURE NO SLOT OCCUPATION ==========
    try:
        check_slot_query = """
            SELECT id, status, application_number 
            FROM napbox_slots 
            WHERE application_number = %s
        """
        existing_slot = execute_query(check_slot_query, (application_number,), fetch_one=True)
        
        if existing_slot and existing_slot.get('status') == 'occupied':
            reset_slot_query = """
                UPDATE napbox_slots 
                SET status = 'available', 
                    customer_name = NULL, 
                    customer_phone = NULL, 
                    application_number = NULL, 
                    installation_date = NULL, 
                    updated_at = NOW() 
                WHERE application_number = %s
            """
            execute_query(reset_slot_query, (application_number,))
            print(f"🔒 SAFEGUARD: Reset occupied slot for application {application_number}")
        else:
            print(f"✅ SAFEGUARD: No occupied slot found for application {application_number}")
    except Exception as safeguard_err:
        print(f"⚠️ Safeguard check failed: {safeguard_err}")

    # Clear email verification session
    session.pop('email_verified', None)
    session.pop('email_verified_time', None)

    return redirect(url_for('application_success', application_number=application_number))


@app.route("/reapply/<application_id>")
def reapply_application(application_id):
    """
    Load rejected application data for re-application.
    User can edit and resubmit with the SAME application number.
    Maximum 2 re-applications only.
    """
    try:
        print(f"🔄 Loading re-apply for application #{application_id}")
        
        # Fetch the existing application data from MySQL
        query = "SELECT * FROM applications WHERE application_number = %s"
        app_data = execute_query(query, (application_id,), fetch_one=True)
        
        if not app_data:
            print(f"❌ Application #{application_id} not found")
            flash('Application not found.', 'danger')
            return redirect('/')
        
        # ========== 🔍 DEBUG: RAW BIRTHDATE FROM DATABASE ==========
        print("="*60)
        print(f"🔍 RAW birthdate value: {app_data.get('birthdate')!r}")
        print(f"🔍 RAW birthdate type: {type(app_data.get('birthdate'))}")
        print("="*60)
        
        # Convert None values to empty strings
        app_data = {k: (v if v is not None else '') for k, v in app_data.items()}
        
        # Check if status is Rejected (only rejected apps can reapply)
        if app_data.get('status') != 'Rejected':
            print(f"❌ Application #{application_id} status is {app_data.get('status')}, not Rejected")
            flash('This application cannot be re-applied. Only rejected applications are eligible.', 'warning')
            return redirect('/')
        
        # CHECK RE-APPLY COUNT (max 2)
        reapplied_count = int(app_data.get('reapplied_count', 0) or 0)
        if reapplied_count >= 2:
            print(f"❌ Application #{application_id} has already re-applied {reapplied_count} times (max 2)")
            flash('You have already re-applied twice. Further re-applications are not allowed.', 'danger')
            return redirect('/')
        
        # Get plan details
        plan_name = app_data.get('plan', '')
        plan_speed = app_data.get('plan_speed', 'N/A')
        plan_price = app_data.get('plan_price', 'Contact us')
        
        # Helper function to get value (handle 'none' string and None)
        def get_value(key, default=''):
            value = app_data.get(key, default)
            if value == 'none' or value is None or value == '':
                return ''
            return value
        
        # ========== PREPARE FORM DATA WITH ALL FIELDS ==========
        form_data = {}

        # ========== HELPER: FORMAT BIRTHDATE FOR DISPLAY (✅ FIXED VERSION) ==========
        def format_birthdate_for_display(birthdate_value):
            """Convert stored birthdate (date object or string) to MM-DD-YYYY for display"""
            if not birthdate_value or birthdate_value == '':
                return ''
            try:
                # ✅ CRITICAL FIX: mysql.connector returns DATE columns as
                # datetime.date objects, NOT strings. Must use strftime here,
                # BEFORE the value ever reaches Jinja's |tojson filter.
                if hasattr(birthdate_value, 'strftime'):
                    return birthdate_value.strftime('%m-%d-%Y')

                birthdate_str = str(birthdate_value)
                if '-' in birthdate_str:
                    parts = birthdate_str.split('-')
                    if len(parts) == 3:
                        if len(parts[0]) == 4 and len(parts[1]) == 2 and len(parts[2]) == 2:
                            return f"{parts[1]}-{parts[2]}-{parts[0]}"
                        elif len(parts[0]) == 2 and len(parts[1]) == 2 and len(parts[2]) == 4:
                            return birthdate_str
                return birthdate_str
            except Exception as e:
                print(f"⚠️ Error formatting birthdate for display: {e}")
                return ''
        
        # Personal Information
        form_data['first_name'] = get_value('first_name')
        form_data['middle_name'] = get_value('middle_name')
        form_data['last_name'] = get_value('last_name')
        form_data['suffix'] = get_value('suffix')
        form_data['birthdate'] = format_birthdate_for_display(get_value('birthdate'))
        
        # ========== 🔍 DEBUG: FORMATTED BIRTHDATE ==========
        print("="*60)
        print(f"🔍 FORMATTED birthdate: {form_data['birthdate']!r}")
        print("="*60)
        
        form_data['place_of_birth'] = get_value('place_of_birth')
        form_data['citizenship'] = get_value('citizenship')
        form_data['sex'] = get_value('sex')
        form_data['civil_status'] = get_value('civil_status')
        form_data['occupation'] = get_value('occupation')
        
        # Contact Details
        form_data['email'] = get_value('email')
        form_data['mobile'] = get_value('mobile')
        form_data['secondary_mobile'] = get_value('secondary_mobile')
        form_data['phone'] = get_value('phone')
        
        # Address
        form_data['province'] = get_value('province')
        form_data['city'] = get_value('city')
        form_data['barangay'] = get_value('barangay')
        form_data['zip'] = get_value('zip')
        form_data['address'] = get_value('address')
        form_data['house_number'] = get_value('house_number')
        form_data['home_ownership'] = get_value('home_ownership')
        form_data['landmark'] = get_value('landmark')
        form_data['billing_address'] = get_value('billing_address')
        
        # Employment
        form_data['employer'] = get_value('employer')
        form_data['business_address'] = get_value('business_address')
        form_data['business_phone'] = get_value('business_phone')
        
        # Spouse
        form_data['spouse_name'] = get_value('spouse_name')
        form_data['spouse_occupation'] = get_value('spouse_occupation')
        form_data['spouse_employer'] = get_value('spouse_employer')
        form_data['spouse_phone'] = get_value('spouse_phone')
        
        # Family
        form_data['father_name'] = get_value('father_name')
        form_data['mother_maiden_name'] = get_value('mother_maiden_name')
        
        # Service
        form_data['service_type'] = get_value('service_type')
        
        # ========== TV Details ==========
        import json
        tv_qty = app_data.get('tv_qty')
        tv_brand = app_data.get('tv_brand')
        tv_type = app_data.get('tv_type')
        
        try:
            if tv_qty and isinstance(tv_qty, str) and tv_qty not in ['', 'none', 'None']:
                form_data['tv_qty'] = json.loads(tv_qty) if tv_qty else []
            elif tv_qty and isinstance(tv_qty, list):
                form_data['tv_qty'] = tv_qty
            else:
                form_data['tv_qty'] = []
        except (json.JSONDecodeError, TypeError):
            form_data['tv_qty'] = []
            
        try:
            if tv_brand and isinstance(tv_brand, str) and tv_brand not in ['', 'none', 'None']:
                form_data['tv_brand'] = json.loads(tv_brand) if tv_brand else []
            elif tv_brand and isinstance(tv_brand, list):
                form_data['tv_brand'] = tv_brand
            else:
                form_data['tv_brand'] = []
        except (json.JSONDecodeError, TypeError):
            form_data['tv_brand'] = []
            
        try:
            if tv_type and isinstance(tv_type, str) and tv_type not in ['', 'none', 'None']:
                form_data['tv_type'] = json.loads(tv_type) if tv_type else []
            elif tv_type and isinstance(tv_type, list):
                form_data['tv_type'] = tv_type
            else:
                form_data['tv_type'] = []
        except (json.JSONDecodeError, TypeError):
            form_data['tv_type'] = []
        
        max_len = max(len(form_data['tv_qty']), len(form_data['tv_brand']), len(form_data['tv_type']))
        while len(form_data['tv_qty']) < max_len:
            form_data['tv_qty'].append('')
        while len(form_data['tv_brand']) < max_len:
            form_data['tv_brand'].append('')
        while len(form_data['tv_type']) < max_len:
            form_data['tv_type'].append('')
        
        # Installation
        form_data['installation_address'] = get_value('installation_address')
        form_data['installation_phone'] = get_value('installation_phone')
        form_data['installation_fee'] = get_value('installation_fee')
        
        # ========== LOCATION AND NAP BOX ==========
        form_data['latitude'] = get_value('latitude')
        form_data['longitude'] = get_value('longitude')
        form_data['preferred_napbox_id'] = get_value('preferred_napbox_id')
        form_data['preferred_napbox_name'] = get_value('preferred_napbox_name')
        form_data['assigned_napbox_id'] = get_value('assigned_napbox_id')
        form_data['assigned_napbox_name'] = get_value('assigned_napbox_name')
        
        # ========== Image Paths ==========
        form_data['existing_profile_photo'] = get_value('profile_photo')
        form_data['existing_signature'] = get_value('signature')
        form_data['existing_id_front'] = get_value('id_front')
        form_data['existing_id_back'] = get_value('id_back')
        form_data['existing_proof_billing'] = get_value('proof_billing')
        
        rejection_reason = app_data.get('rejection_reason', 'No specific reason provided')
        reapply_message = get_value('reapply_message')
        
        print(f"✅ Loading re-apply form for application #{application_id} (reapplied_count={reapplied_count})")
        print(f"📌 First Name: {form_data['first_name']}")
        print(f"📌 Last Name: {form_data['last_name']}")
        print(f"📌 Email: {form_data['email']}")
        print(f"📌 City: {form_data['city']}")
        print(f"📌 Barangay: {form_data['barangay']}")
        
        return render_template(
            'user-application.html',
            plan_name=plan_name,
            plan_speed=plan_speed,
            plan_price=plan_price,
            form_data=form_data,
            is_reapply=True,
            original_application_id=application_id,
            rejection_reason=rejection_reason,
            reapply_message=reapply_message
        )
        
    except Exception as e:
        print(f"❌ Error in reapply route: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while loading your application. Please try again.', 'danger')
        return redirect('/')




# ===============================
# CHECK EMAIL DUPLICATE (MYSQL VERSION - FIXED)
# ===============================
@app.route("/check-email-duplicate", methods=["POST"])
def check_email_duplicate():
    connection = None
    cursor = None
    try:
        data = request.get_json()
        email = data.get('email')
        is_reapply = data.get('is_reapply') == 'true' if data.get('is_reapply') else False
        original_application_id = data.get('original_application_id')
        
        if not email:
            return jsonify({"available": False, "message": "Email is required"}), 400
        
        # Direct MySQL connection (para iwas sa execute_query issue)
        connection = get_db_connection()

        if not connection:
            return jsonify({
                "available": False,
                "message": "Database connection failed. Please try again."
            }), 500

        cursor = connection.cursor(dictionary=True)
                
        # Query to check existing applications
        query = """
            SELECT application_number, status FROM applications 
            WHERE email = %s
        """
        cursor.execute(query, (email,))
        applications = cursor.fetchall()
        
        # Check each application
        for app in applications:
            app_id = str(app.get('application_number'))
            status = app.get('status')
            
            # Skip if this is the same application being re-applied
            if is_reapply and original_application_id and app_id == str(original_application_id):
                continue
            
            # Block if status is NOT 'Rejected'
            if status != 'Rejected':
                return jsonify({
                    "available": False,
                    "message": f"This email is already used in an application with status '{status}'. Only rejected applications can re-apply."
                })
        
        # Email is available
        return jsonify({"available": True, "message": "Email is available"})
        
    except Exception as e:
        print(f"❌ Error checking email: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"available": False, "message": "Error checking email. Please try again."}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()



# ===============================
# SAVE TERMS AGREEMENT (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/save_terms_agreement", methods=["POST"])
def save_terms_agreement():
    try:
        data = request.get_json()
        
        email = data.get('email')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        terms_agreed = data.get('terms_agreed', True)
        agreed_at = data.get('agreed_at')
        ip_address = data.get('ip_address', 'unknown')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if there's an existing application with this email in MySQL
        app_query = """
            SELECT application_number FROM applications 
            WHERE email = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        existing_app = execute_query(app_query, (email,), fetch_one=True)
        existing_app_id = existing_app.get('application_number') if existing_app else None
        
        # Generate unique ID for terms agreement (same format as before)
        terms_id = str(int(datetime.now().timestamp() * 1000))
        
        # Save terms agreement to terms_agreements table
        terms_query = """
            INSERT INTO terms_agreements (
                id, email, first_name, last_name, terms_agreed, agreed_at, 
                ip_address, application_id, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(terms_query, (
            terms_id,
            email,
            first_name,
            last_name,
            1 if terms_agreed else 0,
            agreed_at,
            ip_address,
            existing_app_id,
            datetime.now().isoformat()
        ))
        print(f"✓ Terms agreement saved for {email} with ID: {terms_id}")
        
        # Also update the application record if it exists
        if existing_app_id:
            update_query = """
                UPDATE applications 
                SET terms_agreed = %s, terms_agreed_at = %s, terms_agreed_ip = %s
                WHERE application_number = %s
            """
            execute_query(update_query, (1, agreed_at, ip_address, existing_app_id))
            print(f"✓ Updated application {existing_app_id} with terms agreement")
        
        return jsonify({
            'success': True, 
            'message': 'Terms agreement saved successfully',
            'terms_id': terms_id
        }), 200
        
    except Exception as e:
        print(f"❌ Error saving terms agreement: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
    


# ===============================
# APPLICATION SUCCESS PAGE (XAMPP/MYSQL VERSION WITH FILE UPLOADS)
# ===============================
@app.route('/application/success/<application_number>')
def application_success(application_number):
    """
    Display application success page with application details from MySQL
    """
    try:
        print(f"🔍 Loading application #{application_number} for success page")
        
        # Query the application from MySQL
        query = """
            SELECT 
                application_number, plan, plan_speed, plan_price,
                date_submitted, time_submitted,
                first_name, middle_name, last_name, suffix,
                email, mobile, secondary_mobile, phone,
                birthdate, place_of_birth, mother_maiden_name, father_name,
                sex, civil_status, citizenship, occupation,
                home_ownership, address, billing_address,
                barangay, city, province, zip,
                house_number, landmark, employer, business_address, business_phone,
                spouse_name, spouse_occupation, spouse_employer, spouse_phone,
                service_type, tv_qty, tv_brand, tv_type,
                installation_address, installation_phone, installation_fee,
                latitude, longitude, status, reapplied_count,
                rejection_reason, terms_agreed, terms_agreed_at,
                signature, id_front, id_back, proof_billing, profile_photo
            FROM applications 
            WHERE application_number = %s
            LIMIT 1
        """
        
        application_data = execute_query(query, (application_number,), fetch_one=True)
        
        # Check if application exists
        if application_data is None:
            print(f"❌ Application #{application_number} not found in MySQL database")
            abort(404, description=f'Application #{application_number} not found. Please contact support.')
        
        # Convert None values to empty strings for template rendering
        application_data = {k: (v if v is not None else '') for k, v in application_data.items()}
        
        # Process TV details (convert JSON strings to lists if needed)
        import json
        tv_qty = application_data.get('tv_qty')
        tv_brand = application_data.get('tv_brand')
        tv_type = application_data.get('tv_type')
        
        # Parse JSON if they are strings
        if tv_qty and isinstance(tv_qty, str):
            try:
                application_data['tv_qty'] = json.loads(tv_qty)
            except (json.JSONDecodeError, TypeError):
                application_data['tv_qty'] = []
        else:
            application_data['tv_qty'] = tv_qty if tv_qty else []
            
        if tv_brand and isinstance(tv_brand, str):
            try:
                application_data['tv_brand'] = json.loads(tv_brand)
            except (json.JSONDecodeError, TypeError):
                application_data['tv_brand'] = []
        else:
            application_data['tv_brand'] = tv_brand if tv_brand else []
            
        if tv_type and isinstance(tv_type, str):
            try:
                application_data['tv_type'] = json.loads(tv_type)
            except (json.JSONDecodeError, TypeError):
                application_data['tv_type'] = []
        else:
            application_data['tv_type'] = tv_type if tv_type else []
        
        # Ensure TV arrays have same length
        max_len = max(len(application_data['tv_qty']), len(application_data['tv_brand']), len(application_data['tv_type']))
        while len(application_data['tv_qty']) < max_len:
            application_data['tv_qty'].append('')
        while len(application_data['tv_brand']) < max_len:
            application_data['tv_brand'].append('')
        while len(application_data['tv_type']) < max_len:
            application_data['tv_type'].append('')
        
        # Format full name for display
        first_name = application_data.get('first_name', '')
        last_name = application_data.get('last_name', '')
        middle_name = application_data.get('middle_name', '')
        suffix = application_data.get('suffix', '')
        
        name_parts = []
        if first_name:
            name_parts.append(first_name)
        if middle_name and middle_name != 'none':
            name_parts.append(middle_name)
        if last_name:
            name_parts.append(last_name)
        if suffix and suffix != 'none':
            name_parts.append(suffix)
        application_data['full_name'] = ' '.join(name_parts) if name_parts else 'N/A'
        
        # Format address for display
        address_parts = []
        house_number = application_data.get('house_number', '')
        address = application_data.get('address', '')
        barangay = application_data.get('barangay', '')
        city = application_data.get('city', '')
        province = application_data.get('province', '')
        zip_code = application_data.get('zip', '')
        
        if house_number and house_number != 'none':
            address_parts.append(house_number)
        if address and address != 'none':
            address_parts.append(address)
        if barangay and barangay != 'none':
            address_parts.append(f"Barangay {barangay}")
        if city and city != 'none':
            address_parts.append(city)
        if province and province != 'none':
            address_parts.append(province)
        if zip_code and zip_code != 'none':
            address_parts.append(zip_code)
        
        application_data['full_address'] = ', '.join(address_parts) if address_parts else 'N/A'
        
        # Format installation address
        installation_address = application_data.get('installation_address', '')
        if installation_address and installation_address != 'none':
            application_data['installation_address_display'] = installation_address
        else:
            application_data['installation_address_display'] = application_data.get('full_address', 'N/A')
        
        # Clean up image fields (remove None values)
        for img_field in ['profile_photo', 'signature', 'id_front', 'id_back', 'proof_billing']:
            value = application_data.get(img_field, '')
            if not value or value == 'none' or value == 'None':
                application_data[img_field] = None
        
        print(f"✅ Loaded application #{application_number} from MySQL for success page")
        print(f"📸 Profile Photo: {application_data.get('profile_photo', 'None')[:50] if application_data.get('profile_photo') else 'None'}...")
        print(f"📸 Signature: {application_data.get('signature', 'None')[:50] if application_data.get('signature') else 'None'}...")
        
        return render_template('user-application_success.html', **application_data)
        
    except Exception as e:
        print(f"❌ Error loading application #{application_number}: {e}")
        import traceback
        traceback.print_exc()
        abort(500, description=f'Error loading application details. Please contact support.')





# ===============================
# SEND VERIFICATION CODE (EMAIL) with duplicate check - MySQL VERSION
# ===============================
import random
import time
import smtplib
import mysql.connector
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Store verification codes temporarily (in production, use Redis or database)
verification_codes = {}

def is_email_duplicate_allowed(email, exclude_application_id=None):
    """
    Check if email can be used for a new application.
    Returns (is_blocked, existing_app_data)
    is_blocked = True -> bawal gamitin ang email na ito (may existing non-rejected application)
    is_blocked = False -> pwede (walang existing non-rejected application)
    
    Parameters:
    - email: string, email address to check
    - exclude_application_id: string/None, application_number to exclude (for re-apply scenario)
    """
    connection = None
    cursor = None
    try:
        # MySQL connection
        connection = get_db_connection()

        if not connection:
            print("❌ Database connection failed")
            return False, None

        cursor = connection.cursor(dictionary=True)
        
        # Base query to find applications with the given email
        if exclude_application_id:
            # Exclude the current application (for re-apply scenario)
            query = """
                SELECT application_number, status, first_name, last_name, plan, created_at 
                FROM applications 
                WHERE email = %s AND application_number != %s
                ORDER BY created_at DESC
            """
            params = (email, exclude_application_id)
        else:
            # Check all applications with this email
            query = """
                SELECT application_number, status, first_name, last_name, plan, created_at 
                FROM applications 
                WHERE email = %s
                ORDER BY created_at DESC
            """
            params = (email,)
        
        cursor.execute(query, params)
        existing_apps = cursor.fetchall()
        
        # Check each existing application
        for app in existing_apps:
            status = app.get('status')
            
            # If status is NOT "Rejected" → block the email
            if status != 'Rejected':
                return True, {
                    'application_number': app.get('application_number'),
                    'status': status,
                    'first_name': app.get('first_name'),
                    'last_name': app.get('last_name'),
                    'plan': app.get('plan'),
                    'created_at': app.get('created_at')
                }
        
        # No blocking applications found
        return False, None
        
    except Exception as e:
        print(f"❌ Error checking duplicate email: {e}")
        import traceback
        traceback.print_exc()
        return False, None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def is_email_duplicate_allowed_with_reapply_check(email, application_number):
    """
    Special version for re-apply scenario.
    Automatically excludes the current application being re-applied.
    """
    return is_email_duplicate_allowed(email, exclude_application_id=application_number)



@app.route("/send-verification-code", methods=["POST"])
def send_verification_code():
    try:
        data = request.get_json()
        email = data.get('email')
        is_reapply = data.get('is_reapply', False)
        original_application_id = data.get('original_application_id', None)
        
        if not email:
            return jsonify({"success": False, "message": "Email is required"}), 400
        
        # ========== DUPLICATE EMAIL CHECK (bago magpadala ng code) ==========
        blocked, existing = is_email_duplicate_allowed(
            email,
            exclude_application_id=original_application_id if is_reapply else None
        )
        if blocked:
            error_msg = f"This email belongs to another active application (status: {existing.get('status')}). Cannot {'re-apply' if is_reapply else 'apply'} with this email."
            print(f"❌ {error_msg}")
            return jsonify({"success": False, "message": error_msg}), 400
        
        # Generate 6-digit code
        code = str(random.randint(100000, 999999))
        
        # Store with timestamp (5 minutes expiry)
        verification_codes[email] = {
            'code': code,
            'expires_at': time.time() + 300  # 5 minutes
        }
        
        # ===== EMAIL SENDER =====
        subject = "Cablevision Application - Email Verification Code"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification</title>
        </head>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <div style="background-color: #0047ab; padding: 20px; text-align: center;">
                    <img src="https://cablevision.com/static/logo.png" alt="Cablevision Logo" style="max-width: 150px;" onerror="this.style.display='none'">
                    <h2 style="color: #ffffff; margin: 10px 0 0 0;">Email Verification</h2>
                </div>
                <div style="padding: 30px;">
                    <p style="font-size: 16px; color: #333;">Hello,</p>
                    <p style="font-size: 16px; color: #333;">Thank you for applying for Cablevision internet service. Please use the verification code below to complete your application:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #0047ab; background: #f0f7ff; padding: 20px; border-radius: 8px; display: inline-block; font-family: monospace;">
                            {code}
                        </div>
                    </div>
                    
                    <p style="font-size: 14px; color: #666;">This code will expire in <strong>5 minutes</strong>.</p>
                    <p style="font-size: 14px; color: #666;">If you did not request this verification, please ignore this email.</p>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #999; text-align: center;">Cablevision Systems Corporation<br>Sta. Cruz, Laguna, Philippines</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_body = f"CableVision Verification Code: {code}\n\nThis code expires in 5 minutes.\n\nIf you did not request this, please ignore this email."
        
        gmail_user = "cablevision.cableinternet@gmail.com"
        gmail_app_password = "gbkbembhkfmsoxsx"
        
        msg = MIMEMultipart('alternative')
        msg['From'] = gmail_user
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(plain_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_app_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Verification code sent to {email}: {code}")
        
        return jsonify({
            "success": True, 
            "message": "Verification code sent to your email",
            "expires_in": 300
        })
        
    except Exception as e:
        print(f"Error sending verification email: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/verify-email-code", methods=["POST"])
def verify_email_code():
    try:
        data = request.get_json()
        email = data.get('email')
        code = data.get('code')
        
        if not email or not code:
            return jsonify({"success": False, "message": "Email and code are required"}), 400
        
        stored_data = verification_codes.get(email)
        
        if not stored_data:
            return jsonify({"success": False, "message": "No verification code found. Please request a new code."}), 400
        
        if time.time() > stored_data['expires_at']:
            # Code expired
            del verification_codes[email]
            return jsonify({"success": False, "message": "Verification code has expired. Please request a new code."}), 400
        
        if stored_data['code'] != code:
            return jsonify({"success": False, "message": "Invalid verification code. Please try again."}), 400
        
        # Code is valid - mark as verified
        session['email_verified'] = email
        session['email_verified_time'] = time.time()
        
        # Remove used code
        del verification_codes[email]
        
        return jsonify({"success": True, "message": "Email verified successfully"})
        
    except Exception as e:
        print(f"Error verifying code: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/download/pdf/<application_number>')
def download_pdf(application_number):
    import io, base64
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from flask import send_file
    import requests

    # ========== GET APPLICATION DATA FROM MYSQL ==========
    query = """
        SELECT 
            application_number, plan, plan_speed, plan_price,
            date_submitted, time_submitted, timestamp,
            first_name, middle_name, last_name, suffix,
            email, mobile, secondary_mobile, phone,
            birthdate, place_of_birth, mother_maiden_name, father_name,
            sex, civil_status, citizenship, occupation,
            home_ownership, address, billing_address,
            barangay, city, province, zip,
            house_number, landmark, employer, business_address, business_phone,
            spouse_name, spouse_occupation, spouse_employer, spouse_phone,
            service_type, tv_qty, tv_brand, tv_type,
            installation_address, installation_phone, installation_fee,
            signature, id_front, id_back, proof_billing, profile_photo,
            latitude, longitude, status, reapplied_count,
            rejection_reason
        FROM applications 
        WHERE application_number = %s
        LIMIT 1
    """
    
    data = execute_query(query, (application_number,), fetch_one=True)
    
    if not data:
        return "Application not found", 404
    
    # Convert None values to empty strings
    data = {k: (v if v is not None else '') for k, v in data.items()}
    
    # Parse TV details if they are JSON strings
    import json
    tv_qty = data.get('tv_qty', '')
    tv_brand = data.get('tv_brand', '')
    tv_type = data.get('tv_type', '')
    
    try:
        data['tv_qty'] = json.loads(tv_qty) if tv_qty and isinstance(tv_qty, str) else []
    except:
        data['tv_qty'] = []
    
    try:
        data['tv_brand'] = json.loads(tv_brand) if tv_brand and isinstance(tv_brand, str) else []
    except:
        data['tv_brand'] = []
    
    try:
        data['tv_type'] = json.loads(tv_type) if tv_type and isinstance(tv_type, str) else []
    except:
        data['tv_type'] = []

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # ================= MAX PAGES =================
    MAX_PAGES = 4
    current_page = 1
    y = height - 120

    # Helper function to get image data from URL or base64
    def get_image_reader(image_value):
        """Get ImageReader from file path URL or base64 string"""
        if not image_value or image_value == 'none':
            return None
        
        try:
            # Check if it's a file path URL (starts with /shared-uploads/)
            if image_value.startswith('/shared-uploads/'):
                # Construct full file path
                import os
                # Map URL to file path
                # URL: /shared-uploads/application_uploads/1234567890/profile_photo_1234567890.jpg
                # Path: C:\xampp\htdocs\cablevision_uploads\application_uploads\1234567890\profile_photo_1234567890.jpg
                relative_path = image_value.replace('/shared-uploads/', '')
                full_path = os.path.join(SHARED_UPLOADS_BASE, relative_path)
                
                if os.path.exists(full_path):
                    return ImageReader(full_path)
                else:
                    print(f"Image file not found: {full_path}")
                    return None
                    
            # Check if it's a base64 string
            elif 'base64' in image_value or image_value.startswith('data:image'):
                if 'base64' in image_value or ',' in image_value:
                    # Extract base64 part
                    if ',' in image_value:
                        image_value = image_value.split(',', 1)[1]
                    img_data = base64.b64decode(image_value)
                    return ImageReader(io.BytesIO(img_data))
            else:
                # Try as direct base64
                img_data = base64.b64decode(image_value)
                return ImageReader(io.BytesIO(img_data))
                
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

    # ================= HEADER =================
    def draw_header():
        nonlocal y
        try:
            logo = ImageReader("static/logo1.png")
            p.drawImage(logo, 40, height - 90, width=60, height=60, mask='auto')
        except:
            pass

        p.setFont("Helvetica-Bold", 16)
        p.drawString(110, height - 60, "APPLICATION FORM")

        p.setFont("Helvetica-Bold", 10)
        p.drawRightString(width - 50, height - 60, f"Application No: {application_number}")

        p.setFont("Helvetica", 8)
        p.drawString(110, height - 75, "Sitio Sampaguita, Brgy. Pagsawitan, Santa Cruz, 4009 Laguna")
        p.drawString(110, height - 87, "Tel: (049) 501-1495 | Fax: (049) 501-0229 | Mobile: 0917 501 0341")

        y = height - 110

    def draw_page_number():
        p.setFont("Helvetica-Bold", 10)
        p.setFillColorRGB(0.4, 0.4, 0.4)
        p.drawRightString(width - 25, 20, str(current_page))
        p.setFillColorRGB(0, 0, 0)

    def new_page():
        nonlocal y, current_page
        if current_page >= MAX_PAGES:
            return False
        p.showPage()
        current_page += 1
        draw_header()
        draw_page_number()
        y = height - 110
        return True

    def ensure_space(required):
        nonlocal y
        if y - required < 50:
            return new_page()
        return True

    def draw_section_title(title):
        nonlocal y
        ensure_space(30)
        p.setFont("Helvetica-Bold", 12)
        p.setFillColorRGB(0, 0.4, 0.6)
        p.drawString(50, y, title)
        p.setFillColorRGB(0, 0, 0)
        y -= 22

    def draw_section_title_centered(title):
        nonlocal y
        ensure_space(30)
        p.setFont("Helvetica-Bold", 14)
        p.setFillColorRGB(0, 0.4, 0.6)
        p.drawCentredString(width / 2, y, title)
        p.setFillColorRGB(0, 0, 0)
        y -= 25

    # Two-column field drawer with tighter spacing
    def draw_two_columns(fields):
        nonlocal y
        col1_x = 50
        col2_x = 310
        label_width = 120
        value_x = col1_x + label_width + 5
        
        for i in range(0, len(fields), 2):
            ensure_space(20)
            # Left column
            label1, value1 = fields[i]
            p.setFont("Helvetica-Bold", 9)
            p.drawString(col1_x, y, f"{label1}:")
            p.setFont("Helvetica", 9)
            val1_str = str(value1) if value1 and value1 not in ['-', 'none', ''] else "___________________"
            if len(val1_str) > 35:
                val1_str = val1_str[:32] + "..."
            p.drawString(value_x, y, val1_str)
            
            # Right column
            if i + 1 < len(fields):
                label2, value2 = fields[i + 1]
                p.setFont("Helvetica-Bold", 9)
                p.drawString(col2_x, y, f"{label2}:")
                p.setFont("Helvetica", 9)
                val2_str = str(value2) if value2 and value2 not in ['-', 'none', ''] else "___________________"
                if len(val2_str) > 30:
                    val2_str = val2_str[:27] + "..."
                p.drawString(col2_x + label_width + 5, y, val2_str)
            
            y -= 18
        y -= 5

    # Draw images top and bottom (front then back)
    def draw_images_top_bottom(label1, img1_value, label2, img2_value, img_width=280, img_height=190):
        nonlocal y
        
        # Front ID
        ensure_space(img_height + 60)
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(width / 2, y, label1)
        y -= 22
        
        img1 = get_image_reader(img1_value)
        if img1:
            try:
                x_center = (width - img_width) / 2
                p.drawImage(img1, x_center, y - img_height, img_width, img_height, preserveAspectRatio=True, mask='auto')
                y -= img_height + 35
            except:
                p.drawCentredString(width / 2, y, "[Image error]")
                y -= 25
        else:
            p.drawCentredString(width / 2, y, "Not provided")
            y -= 25
        
        # Back ID
        ensure_space(img_height + 60)
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(width / 2, y, label2)
        y -= 22
        
        img2 = get_image_reader(img2_value)
        if img2:
            try:
                x_center = (width - img_width) / 2
                p.drawImage(img2, x_center, y - img_height, img_width, img_height, preserveAspectRatio=True, mask='auto')
                y -= img_height + 35
            except:
                p.drawCentredString(width / 2, y, "[Image error]")
                y -= 25
        else:
            p.drawCentredString(width / 2, y, "Not provided")
            y -= 25

    # Signature section
    def draw_signature_section(signature_value, full_name):
        nonlocal y
        
        # Add space before signature section
        y -= 15
        
        # Signature image (centered, smaller to fit)
        sig_width = 250
        sig_height = 85
        sig_img = get_image_reader(signature_value)
        
        if sig_img:
            try:
                x_center = (width - sig_width) / 2
                p.drawImage(sig_img, x_center, y - sig_height, sig_width, sig_height, preserveAspectRatio=True, mask='auto')
            except:
                p.setFont("Helvetica", 9)
                p.drawCentredString(width / 2, y, "[Signature not displayable]")
        else:
            p.setFont("Helvetica", 9)
            p.drawCentredString(width / 2, y, "No signature provided")
        
        y -= sig_height + 20
        
        # Printed Name (centered)
        p.setFont("Helvetica", 10)
        p.drawCentredString(width / 2, y, full_name if full_name else "_________________________")
        y -= 20
        
        # "signature over printed name" text
        p.setFont("Helvetica", 8)
        p.setFillColorRGB(0.4, 0.4, 0.4)
        p.drawCentredString(width / 2, y, "signature over printed name")
        p.setFillColorRGB(0, 0, 0)
        y -= 30

    # ================= START BUILDING =================
    draw_header()
    draw_page_number()

    # ================= PAGE 1: ALL INFORMATION WITH SIGNATURE AT THE BOTTOM =================
    # SECTION 1: PERSONAL INFORMATION
    draw_section_title("I. PERSONAL INFORMATION")
    draw_two_columns([
        ("Last Name", data.get("last_name")),
        ("First Name", data.get("first_name")),
        ("Middle Name", data.get("middle_name")),
        ("Suffix", data.get("suffix")),
        ("Date of Birth", data.get("birthdate")),
        ("Place of Birth", data.get("place_of_birth")),
        ("Sex", data.get("sex")),
        ("Civil Status", data.get("civil_status")),
        ("Citizenship", data.get("citizenship")),
        ("Occupation", data.get("occupation")),
    ])

    # SECTION 2: FAMILY BACKGROUND
    draw_section_title("II. FAMILY DETAILS")
    draw_two_columns([
        ("Mother's Maiden Name", data.get("mother_maiden_name")),
        ("Father's Name", data.get("father_name")),
    ])

    # SECTION 3: CONTACT & ADDRESS
    draw_section_title("III. CONTACT & ADDRESS")

    draw_two_columns([
        ("Mobile Number", data.get("mobile")),
        ("Email Address", data.get("email")),
        ("Home Ownership", data.get("home_ownership")),
        ("House No./Unit", data.get("house_number")),
        ("Nearest Landmark", data.get("landmark")),
        ("Street/Village", data.get("address")),
    ])

    # ================= BILLING ADDRESS (FULL WIDTH) =================
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, y, "Billing Address:")
    p.setFont("Helvetica", 9)

    billing_address = data.get("billing_address", "")
    if not billing_address or billing_address in ['-', 'none', '']:
        billing_address = "_________________________"

    from reportlab.pdfbase.pdfmetrics import stringWidth

    max_width = 400
    words = billing_address.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if stringWidth(test_line, "Helvetica", 9) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        p.drawString(170, y, line)
        y -= 14
    y -= 5

    # SECTION 4: EMPLOYMENT DETAILS
    draw_section_title("IV. EMPLOYMENT DETAILS")
    draw_two_columns([
        ("Employer / Company", data.get("employer")),
        ("Business Phone", data.get("business_phone")),
        ("Business Address", data.get("business_address")),
    ])

    # SECTION 5: SPOUSE INFORMATION
    if data.get("civil_status") in ["Married", "married"]:
        draw_section_title("V. SPOUSE INFORMATION")
        draw_two_columns([
            ("Spouse Full Name", data.get("spouse_name")),
            ("Spouse Occupation", data.get("spouse_occupation")),
            ("Spouse Employer", data.get("spouse_employer")),
            ("Spouse Phone", data.get("spouse_phone")),
        ])

    # SECTION 6: SERVICE PLAN
    draw_section_title("VI. SERVICE PLAN")

    draw_two_columns([
        ("Service Type / Plan", data.get("service_type")),
        ("Installation Fee", data.get("installation_fee")),
    ])

    # ================= INSTALLATION PHONE (FULL WIDTH) =================
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, y, "Installation Phone:")
    p.setFont("Helvetica", 9)

    installation_phone = data.get("installation_phone", "")
    if not installation_phone or installation_phone in ['-', 'none', '']:
        installation_phone = "_________________________"

    p.drawString(170, y, installation_phone)
    y -= 18
    y -= 5

    # ================= INSTALLATION ADDRESS (FULL WIDTH) =================
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, y, "Installation Address:")
    p.setFont("Helvetica", 9)

    installation_address = data.get("installation_address", "")
    if not installation_address or installation_address in ['-', 'none', '']:
        installation_address = "_________________________"

    words = installation_address.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if stringWidth(test_line, "Helvetica", 9) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        p.drawString(170, y, line)
        y -= 14
    y -= 5

    # SECTION 7: TV SET DETAILS
    tv_qty_list = data.get("tv_qty", [])
    tv_brand_list = data.get("tv_brand", [])
    tv_type_list = data.get("tv_type", [])
    
    if tv_qty_list and any(tv_qty_list):
        draw_section_title("VII. TV SET DETAILS")
        ensure_space(40)
        
        # Table header
        p.setFont("Helvetica-Bold", 9)
        p.drawString(50, y, "QTY")
        p.drawString(120, y, "BRAND / MODEL")
        p.drawString(320, y, "TYPE (HD/REGULAR)")
        y -= 15
        
        # Table data
        p.setFont("Helvetica", 9)
        max_rows = min(len(tv_qty_list), 3)
        for i in range(max_rows):
            if y < 120:
                break
            qty = str(tv_qty_list[i]) if i < len(tv_qty_list) and tv_qty_list[i] not in ['none', ''] else "-"
            brand = tv_brand_list[i] if i < len(tv_brand_list) and tv_brand_list[i] not in ['none', ''] else "-"
            if len(brand) > 25:
                brand = brand[:22] + "..."
            tv_t = tv_type_list[i] if i < len(tv_type_list) and tv_type_list[i] not in ['none', ''] else "-"
            
            p.drawString(50, y, qty)
            p.drawString(120, y, brand)
            p.drawString(320, y, tv_t)
            y -= 16
        y -= 5

    # SECTION 8: SUBMISSION DETAILS
    draw_section_title("VIII. SUBMISSION DETAILS")
    draw_two_columns([
        ("Date Submitted", data.get("date_submitted")),
        ("Time Submitted", data.get("time_submitted")),
    ])

    # SIGNATURE SECTION AT THE BOTTOM OF PAGE 1
    full_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    draw_signature_section(data.get("signature"), full_name)

    # ================= PAGE 2: LOCATION MAP =================
    new_page()
    draw_section_title_centered("INSTALLATION LOCATION MAP")

    lat = data.get("latitude")
    lng = data.get("longitude")
    google_maps_url = None
    google_maps_direction_url = None
    map_img = None

    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
        
        if lat and lng:
            # Regular map URL
            google_maps_url = f"https://www.google.com/maps?q={lat},{lng}"
            # Directions URL
            google_maps_direction_url = f"https://www.google.com/maps/dir//{lat},{lng}"
            
            map_url = f"https://maps.locationiq.com/v3/staticmap?key=pk.0fdad07272d959e4de881139988b0883&center={lat},{lng}&zoom=17&size=600x400&markers=icon:large-red-cutout|{lat},{lng}"
            response = requests.get(map_url)
            if response.status_code == 200:
                map_img = ImageReader(io.BytesIO(response.content))
    except Exception as e:
        print("Map error:", e)

    # Location details
    draw_two_columns([
        ("Street/Village", data.get("address")),
        ("Barangay/City", f"{data.get('barangay', '-')}, {data.get('city', '-')}"),
        ("Latitude", str(lat) if lat else "-"),
        ("Longitude", str(lng) if lng else "-"),
    ])

    # Google Maps Direction Link
    if google_maps_direction_url:
        ensure_space(25)
        p.setFont("Helvetica-Bold", 12)
        p.setFillColorRGB(0, 0.5, 0)
        p.drawCentredString(width / 2, y, "📍 GET DIRECTIONS from your current location to this address")
        text_width = p.stringWidth("📍 GET DIRECTIONS from your current location to this address", "Helvetica-Bold", 12)
        p.linkURL(google_maps_direction_url, ((width - text_width) / 2, y - 2, (width + text_width) / 2, y + 12), relative=0)
        p.setFillColorRGB(0, 0, 0)
        y -= 20
        
        # Subtext instruction
        p.setFont("Helvetica", 8)
        p.setFillColorRGB(0.5, 0.5, 0.5)
        p.drawCentredString(width / 2, y, "👉 Click above to see distance from YOUR location, travel time, and turn-by-turn directions")
        p.setFillColorRGB(0, 0, 0)
        y -= 20

    # Regular Google Maps link
    if google_maps_url:
        p.setFont("Helvetica", 9)
        p.setFillColorRGB(0, 0, 1)
        p.drawCentredString(width / 2, y, "Or click here to view location on Google Maps")
        text_width = p.stringWidth("Or click here to view location on Google Maps", "Helvetica", 9)
        p.linkURL(google_maps_url, ((width - text_width) / 2, y - 2, (width + text_width) / 2, y + 8), relative=0)
        p.setFillColorRGB(0, 0, 0)
        y -= 30

    # Static map image
    if map_img:
        ensure_space(380)
        img_width = 500
        img_height = 320
        x_center = (width - img_width) / 2
        p.drawImage(map_img, x_center, y - img_height, img_width, img_height)
        y -= img_height + 20
        
        p.setFont("Helvetica", 8)
        p.setFillColorRGB(0.5, 0.5, 0.5)
        p.drawCentredString(width / 2, y, "💡 Tip: Click the green 'GET DIRECTIONS' link above to see distance from your current location")
        p.setFillColorRGB(0, 0, 0)
        y -= 15
    else:
        draw_two_columns([("Map Status", "Not available")])

    # ================= PAGE 3: FRONT AND BACK ID =================
    new_page()
    draw_section_title_centered("VALID IDENTIFICATION")
    
    draw_images_top_bottom(
        "VALID ID (FRONT)", data.get("id_front"),
        "VALID ID (BACK)", data.get("id_back"),
        img_width=320, img_height=220
    )

    # ================= PAGE 4: PROOF OF BILLING =================
    new_page()
    draw_section_title_centered("PROOF OF BILLING")
    
    proof_img = get_image_reader(data.get("proof_billing"))
    if proof_img:
        try:
            img_width = 500
            img_height = 580
            x_center = (width - img_width) / 2
            p.drawImage(proof_img, x_center, y - img_height, img_width, img_height, preserveAspectRatio=True, mask='auto')
            y -= img_height + 30
        except:
            p.drawCentredString(width / 2, y, "Image not renderable")
            y -= 30
    else:
        p.drawCentredString(width / 2, y, "No proof of billing provided")
        y -= 30

    # ================= SAVE PDF =================
    p.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=f"Application_{application_number}.pdf")


# ===============================
# LOGIN REQUIRED DECORATOR - WITH TAB ID SUPPORT
# ===============================
from functools import wraps
from flask import session, redirect, url_for, request

def is_login_history_token_active(user_id, session_token):
    if not user_id or not session_token:
        return False
    try:
        record = execute_query(
            "SELECT 1 FROM login_history WHERE user_id = %s AND session_token = %s LIMIT 1",
            (user_id, session_token),
            fetch_one=True
        )
        return bool(record)
    except Exception as e:
        print(f"[SESSION VALIDATION ERROR] {e}")
        return False


def get_session_tab_for_user(user_id):
    active_tab = session.get("active_tab")
    if active_tab:
        return active_tab

    for key, value in session.items():
        if isinstance(key, str) and key.startswith("user_") and isinstance(value, dict):
            if value.get("user_id") == user_id:
                return key.replace("user_", "")
    return None


def clear_user_sessions(user_id):
    session.pop("user_id", None)
    session.pop("active_tab", None)

    for key in list(session.keys()):
        if isinstance(key, str) and key.startswith("user_"):
            user_sess = session.get(key)
            if isinstance(user_sess, dict) and user_sess.get("user_id") == user_id:
                session.pop(key, None)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 👇 UNA, CHECK KUNG MAY TAB ID SA URL
        tab_id = request.args.get("tab_id")
        
        # 👇 KUNG MAY TAB ID, CHECK KUNG MAY SESSION NA MAY TAB ID
        if tab_id:
            user_session = session.get(f"user_{tab_id}")
            if user_session and user_session.get("user_id"):
                if is_login_history_token_active(user_session.get("user_id"), tab_id):
                    session["user_id"] = user_session.get("user_id")
                    session["active_tab"] = tab_id
                    return f(*args, **kwargs)
                clear_user_sessions(user_session.get("user_id"))
                flash("Your session has ended. Please login again.", "warning")
                return redirect(url_for("login"))
        
        # 👇 CHECK KUNG MAY REGULAR SESSION
        if "user_id" in session:
            current_user_id = session.get("user_id")
            active_tab = get_session_tab_for_user(current_user_id)

            if active_tab and is_login_history_token_active(current_user_id, active_tab):
                session["active_tab"] = active_tab
                return f(*args, **kwargs)

            clear_user_sessions(current_user_id)
            flash("Your session has ended. Please login again.", "warning")
            return redirect(url_for("login"))
        
        # ❌ WALANG SESSION - REDIRECT SA LOGIN
        flash("Please login first.", "warning")
        return redirect(url_for("login"))
    return decorated_function


def generate_ga_secret(length=20):
    return base64.b32encode(os.urandom(length)).decode("utf-8").rstrip("=")


def generate_ga_provisioning_uri(username, secret):
    safe_username = quote(str(username), safe="")
    return f"otpauth://totp/Cablevision:{safe_username}?secret={secret}&issuer=Cablevision"


def verify_ga_code(secret, code):
    """
    Verify Google Authenticator code with proper time sync handling
    """
    import time
    import base64
    import hashlib
    import hmac
    import struct
    
    if not secret or not code:
        print(f"❌ GA verify: Missing secret or code - secret: {bool(secret)}, code: {bool(code)}")
        return False
    
    try:
        # Clean the code - remove any non-numeric characters
        code = ''.join(filter(str.isdigit, str(code)))
        if len(code) != 6:
            print(f"❌ GA verify: Invalid code length - {len(code)}")
            return False
        
        # Clean the secret
        secret = str(secret).strip().replace(" ", "").upper()
        if not secret:
            return False
        
        # Add padding if needed
        missing_padding = (-len(secret)) % 8
        if missing_padding:
            secret += "=" * missing_padding
        
        # Decode secret
        decoded_key = base64.b32decode(secret.encode("utf-8"), casefold=True)
        print(f"🔐 GA verify: Secret decoded successfully, length: {len(decoded_key)}")
        
        # Get current time window (30 seconds)
        current_timestamp = int(time.time()) // 30
        print(f"🔐 GA verify: Current time window: {current_timestamp}")
        
        # Check wider time windows for time sync issues
        # Range -3 to 3 gives 7 windows (210 seconds or 3.5 minutes)
        for offset in range(-3, 4):
            timestamp = current_timestamp + offset
            msg = struct.pack(">Q", timestamp)
            digest = hmac.new(decoded_key, msg, hashlib.sha1).digest()
            digest_offset = digest[-1] & 0x0F
            binary_code = struct.unpack(">I", digest[digest_offset:digest_offset + 4])[0] & 0x7FFFFFFF
            expected = str(binary_code % 1000000).zfill(6)
            
            print(f"   Window {offset}: expected={expected}, entered={code}")
            
            if expected == code:
                print(f"✅ GA code matched at offset {offset}")
                return True
        
        print(f"❌ GA verify: No match found for code {code}")
        return False
        
    except Exception as e:
        print(f"❌ GA verification error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ===============================
# LOGIN ROUTE (XAMPP/MYSQL VERSION) - WITH PROPER TAB ID SUPPORT
# ===============================
@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_user_security_columns()
    ensure_temp_reset_table()

    if request.method == "POST":
        # Check if JSON request (AJAX)
        if request.is_json:
            data = request.get_json()
            user_id = data.get("user_id", "").strip()
            password = data.get("password", "").strip()
            ga_code = data.get("ga_code", "").strip()
            tab_id = data.get("tab_id", "").strip()
        else:
            user_id = request.form.get("user_id", "").strip()
            password = request.form.get("password", "").strip()
            ga_code = request.form.get("ga_code", "").strip()
            tab_id = request.form.get("tab_id", "").strip()

        # ========== HANDLE 2FA VERIFICATION ==========
        pending_user_id = session.get("pending_ga_user_id")
        
        if pending_user_id and ga_code:
            print(f"🔐 2FA verification attempt for user_id: {pending_user_id}")
            
            user_query = """
                SELECT user_id, customer_id, application_number, email, username, password, role,
                       connection_status, contract_number, status, ga_secret, ga_enabled,
                       first_name, last_name, middle_name, suffix, contact_number, address
                FROM users
                WHERE user_id = %s
                LIMIT 1
            """
            user_data = execute_query(user_query, (pending_user_id,), fetch_one=True)
            
            if not user_data:
                print(f"❌ User not found for pending_user_id: {pending_user_id}")
                session.pop("pending_ga_user_id", None)
                if request.is_json:
                    return jsonify({"success": False, "error": "User not found. Please login again.", "requires_2fa": False}), 401
                flash("User not found. Please login again.", "danger")
                return redirect(url_for("login"))
            
            ga_secret = user_data.get("ga_secret")
            is_valid = verify_ga_code(ga_secret, ga_code)
            print(f"🔐 Verification result: {is_valid}")
            
            if is_valid:
                # ✅ GA CODE IS CORRECT - LOGIN THE USER
                session.pop("pending_ga_user_id", None)
                
                # 👇 STORE SESSION WITH TAB ID AS KEY - DITO ANG IMPORTANTE!
                if tab_id:
                    session[f"user_{tab_id}"] = {
                        "user_id": user_data.get("user_id"),
                        "customer_id": user_data.get("customer_id"),
                        "role": user_data.get("role"),
                        "email": user_data.get("email"),
                        "userType": "user",
                        "contract_number": user_data.get("contract_number"),
                        "status": user_data.get("status", "Active")
                    }
                    # 👇 I-STORE DIN ANG ACTIVE TAB ID
                    session["active_tab"] = tab_id
                else:
                    # Fallback: use regular session if no tab_id
                    session["user_id"] = user_data.get("user_id")
                    session["customer_id"] = user_data.get("customer_id")
                    session["role"] = user_data.get("role")
                    session["email"] = user_data.get("email")
                    session["userType"] = "user"
                    session["contract_number"] = user_data.get("contract_number")
                    session["ga_verified"] = True
                    session["user_status"] = user_data.get("status", "Active")
                
                # Update connection status
                execute_query(
                    "UPDATE users SET connection_status = 'Connected' WHERE user_id = %s AND status != 'Terminated'",
                    (user_data.get('user_id'),)
                )
                record_login_history(user_data.get("user_id"), tab_id)
                
                # Sa login route, pagkatapos mag-store ng session:
                print(f"✅ Login successful: {user_data.get('user_id')}")
                print(f"   Tab ID: {tab_id}")
                print(f"   Session key: user_{tab_id}")
                print(f"   Session data: {session.get(f'user_{tab_id}')}")  # 👈 I-PRINT ANG SESSION DATA
                print(f"   All session keys: {list(session.keys())}")  # 👈 I-PRINT LAHAT NG SESSION KEYS
                
                if request.is_json:
                    return jsonify({
                        "success": True, 
                        "redirect": url_for("dashboard") + "?tab_id=" + tab_id if tab_id else url_for("dashboard"), 
                        "username": user_data.get("username"), 
                        "user_id": user_data.get("user_id"),
                        "user_status": session.get("user_status"),
                        "tab_id": tab_id
                    })
                return redirect(url_for("dashboard") + "?tab_id=" + tab_id if tab_id else url_for("dashboard"))
            else:
                # ❌ GA CODE IS INVALID
                print(f"❌ Invalid GA code for user: {pending_user_id}")
                
                if request.is_json:
                    return jsonify({
                        "success": False, 
                        "error": "Invalid Google Authenticator code. Please try again.", 
                        "requires_2fa": True
                    }), 401
                flash("Invalid Google Authenticator code. Please try again.", "danger")
                return render_template("user-login.html", require_ga_code=True, pending_ga_user_id=pending_user_id)

        # ========== INITIAL LOGIN (NO 2FA YET) ==========
        query = """
            SELECT user_id, customer_id, application_number, email, username,
                   password, role, connection_status, contract_number, status,
                   ga_secret, ga_enabled, first_name, last_name, middle_name,
                   suffix, contact_number, address
            FROM users 
            WHERE user_id = %s OR email = %s OR username = %s
            LIMIT 1
        """
        user_data = execute_query(query, (user_id, user_id, user_id), fetch_one=True)

        if user_data:
            stored_password = user_data.get("password")
            # Support plain and hashed passwords
            if stored_password == password or check_password_hash(stored_password, password):
                
                user_status = user_data.get("status", "Active")
                session["user_status"] = user_status

                # ========== CHECK IF 2FA IS ENABLED ==========
                if user_data.get("ga_enabled"):
                    # Store user ID in session for 2FA verification
                    session["pending_ga_user_id"] = user_data.get("user_id")
                    print(f"🔐 2FA required for user: {user_data.get('user_id')}")
                    
                    if request.is_json:
                        return jsonify({
                            "success": False, 
                            "requires_2fa": True, 
                            "user_id": user_data.get("user_id"),
                            "tab_id": tab_id
                        }), 401
                    
                    flash("Enter the 6-digit code from Google Authenticator to continue.", "info")
                    return render_template("user-login.html", require_ga_code=True, pending_ga_user_id=user_data.get("user_id"))
                
                # ========== NO 2FA - LOGIN DIRECTLY ==========
                
                # 👇 STORE SESSION WITH TAB ID AS KEY - DITO ANG IMPORTANTE!
                if tab_id:
                    session[f"user_{tab_id}"] = {
                        "user_id": user_data.get("user_id"),
                        "customer_id": user_data.get("customer_id"),
                        "role": user_data.get("role"),
                        "email": user_data.get("email"),
                        "userType": "user",
                        "contract_number": user_data.get("contract_number"),
                        "status": user_data.get("status", "Active")
                    }
                    # 👇 I-STORE DIN ANG ACTIVE TAB ID
                    session["active_tab"] = tab_id
                else:
                    # Fallback: use regular session if no tab_id
                    session["user_id"] = user_data.get("user_id")
                    session["customer_id"] = user_data.get("customer_id")
                    session["role"] = user_data.get("role")
                    session["email"] = user_data.get("email")
                    session["userType"] = "user"
                    session["contract_number"] = user_data.get("contract_number")
                    session.pop("pending_ga_user_id", None)
                    session["ga_verified"] = True
                
                execute_query(
                    "UPDATE users SET connection_status = 'Connected' WHERE user_id = %s AND status != 'Terminated'",
                    (user_data.get('user_id'),)
                )
                record_login_history(user_data.get("user_id"), tab_id)
                
                print(f"✅ Login successful: {user_data.get('user_id')}")
                print(f"   Tab ID: {tab_id}")
                print(f"   Session key: user_{tab_id}")
                
                if request.is_json:
                    return jsonify({
                        "success": True, 
                        "redirect": url_for("dashboard") + "?tab_id=" + tab_id if tab_id else url_for("dashboard"),
                        "username": user_data.get("username"),
                        "user_id": user_data.get("user_id"),
                        "user_status": user_status,
                        "tab_id": tab_id
                    })
                return redirect(url_for("dashboard") + "?tab_id=" + tab_id if tab_id else url_for("dashboard"))

        # Invalid credentials
        print(f"❌ Login failed: Invalid credentials for {user_id}")
        if request.is_json:
            return jsonify({"success": False, "error": "Invalid User ID or Password"}), 401
        else:
            flash("Invalid User ID or Password", "danger")
            return redirect(url_for("login"))

    return render_template("user-login.html")

    
# ===============================
# OTP EMAIL SENDER (KEEP AS IS - gumagana naman)
# ===============================

def send_otp_email(to_email, otp_code):
    """
    Sends an OTP email to the given recipient using Gmail SMTP with App Password.
    Returns True if successful, False otherwise.
    """
    gmail_user = "cablevision.cableinternet@gmail.com"
    gmail_app_password = "gbkbembhkfmsoxsx"

    subject = "Your OTP Verification Code - CableVision"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f0f4f8; padding: 20px;">
            <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; max-width: 500px; margin: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h2 style="color: #003d73;">CableVision OTP Verification</h2>
                <p>Hello,</p>
                <p>Your One-Time Password (OTP) is:</p>
                <p style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #001f3f;">{otp_code}</p>
                <p>This code expires in 5 minutes.</p>
                <p>If you did not request this, please ignore this email.</p>
                <hr>
                <p style="font-size: 12px; color: #666;">&copy; 2026 CableVision Systems Corp. All rights reserved.</p>
            </div>
        </body>
    </html>
    """

    plain_body = f"CableVision OTP Verification\n\nYour OTP is: {otp_code}\nExpires in 5 minutes.\nIgnore if you didn't request this."

    msg = MIMEMultipart('alternative')
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(plain_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(gmail_user, gmail_app_password)
        server.send_message(msg)
        server.quit()
        print(f"✅ OTP sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending OTP email: {e}")
        traceback.print_exc()
        return False
    
# ===============================
# USER FORGOT PASSWORD (SEND OTP) - XAMPP/MYSQL VERSION
# ===============================
@app.route("/api/user/forgot-password", methods=["POST"])
def user_forgot_password():
    data = request.json
    user_email = data.get("user_email")

    if not user_email:
        return jsonify({"error": "Email required"}), 400

    # ========== FIND USER BY EMAIL IN MYSQL ==========
    query = """
        SELECT user_id, email, username, first_name, last_name 
        FROM users 
        WHERE email = %s 
        LIMIT 1
    """
    user_data = execute_query(query, (user_email,), fetch_one=True)

    if not user_data:
        return jsonify({"error": "Email not found"}), 404

    user_id = user_data.get("user_id")
    username = user_data.get("username") or user_data.get("user_id")
    first_name = user_data.get("first_name", "")
    last_name = user_data.get("last_name", "")
    name = f"{first_name} {last_name}".strip() or username
    
    # Generate OTP
    otp_code = str(random.randint(100000, 999999))
    expiry = datetime.now().timestamp() + 300
    
    # ✅ SAVE TO temp_reset TABLE (HINDI SA users table)
    insert_query = """
        INSERT INTO temp_reset (email, otp, expiry, user_type, area, username)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    result = execute_query(insert_query, (user_email, otp_code, expiry, "user", "", username))
    
    print(f"✅ OTP saved to temp_reset for user {username}: {otp_code}")
    print(f"   Insert result: {result}")

    # Send email
    if not send_otp_email(user_email, otp_code):
        return jsonify({"error": "Failed to send OTP"}), 500

    return jsonify({
        "message": "OTP sent successfully",
        "username": username
    })

# ===============================
# USER RESET PASSWORD - XAMPP/MYSQL VERSION
# ===============================
@app.route("/api/user/reset-password", methods=["POST"])
def user_reset_password():
    data = request.json
    username = data.get("username")
    code = data.get("code")
    new_password = data.get("new_password")
    tab_id = data.get("tab_id", "")

    print("======= USER RESET PASSWORD DEBUG =======")
    print(f"Username: {username}")
    print(f"Code: {code}")
    print(f"Tab ID: {tab_id}")
    print("====================================")

    if not username or not code or not new_password:
        return jsonify({"error": "All fields are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    # ========== FIND OTP IN temp_reset ==========
    temp_query = """
        SELECT * FROM temp_reset
        WHERE (username = %s OR email = %s) AND otp = %s
        ORDER BY id DESC LIMIT 1
    """
    temp_data = execute_query(temp_query, (username, username, code), fetch_one=True)

    if not temp_data:
        return jsonify({"error": "Invalid verification code"}), 400

    print(f"✅ Found temp_data: {temp_data}")

    current_time = datetime.now().timestamp()
    expiry_time = temp_data.get('expiry', 0)

    if current_time > expiry_time:
        execute_query("DELETE FROM temp_reset WHERE id = %s", (temp_data.get('id'),))
        return jsonify({"error": "Verification code expired"}), 400

    user_type = temp_data.get('user_type')
    actual_username = temp_data.get('username')
    user_email = temp_data.get('email')

    hashed_new_password = generate_password_hash(new_password)
    
    # ✅ STEP 1: SAVE new_password TO temp_reset
    update_temp_query = """
        UPDATE temp_reset 
        SET new_password = %s 
        WHERE id = %s
    """
    update_result = execute_query(update_temp_query, (hashed_new_password, temp_data.get('id')))
    print(f"✅ new_password saved to temp_reset: {update_result}")

    # 🔍 I-VERIFY KUNG NA-SAVE ANG new_password
    verify_temp = execute_query("SELECT new_password FROM temp_reset WHERE id = %s", (temp_data.get('id'),), fetch_one=True)
    print(f"🔍 Verified new_password: {verify_temp.get('new_password') if verify_temp else 'NULL'}")

    # ✅ STEP 2: UPDATE USER PASSWORD
    update_query = """
        UPDATE users 
        SET password = %s, reset_code = NULL 
        WHERE user_id = %s OR username = %s OR email = %s
    """
    update_rows = execute_query(update_query, (hashed_new_password, actual_username, actual_username, user_email))
    print(f"✅ User password updated: {update_rows} rows affected")

    if update_rows is None or update_rows == 0:
        return jsonify({"error": "Failed to update password. Please try again."}), 400

    # ✅ STEP 3: KUNIN ANG USER DATA
    user_query = """
        SELECT user_id, customer_id, application_number, email, username,
               role, contract_number, status, first_name, last_name
        FROM users 
        WHERE user_id = %s OR username = %s OR email = %s
        LIMIT 1
    """
    user_data = execute_query(user_query, (actual_username, actual_username, user_email), fetch_one=True)
    
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # ✅ STEP 4: CLEAR OLD SESSION, THEN AUTO-LOGIN THE USER WITH THE NEW PASSWORD
    session.clear()

    if tab_id:
        session[f"user_{tab_id}"] = {
            "user_id": user_data.get("user_id"),
            "customer_id": user_data.get("customer_id"),
            "role": user_data.get("role"),
            "email": user_data.get("email"),
            "userType": "user",
            "contract_number": user_data.get("contract_number"),
            "status": user_data.get("status", "Active")
        }
        session["active_tab"] = tab_id
    else:
        session["user_id"] = user_data.get("user_id")
        session["customer_id"] = user_data.get("customer_id")
        session["role"] = user_data.get("role")
        session["email"] = user_data.get("email")
        session["userType"] = "user"
        session["contract_number"] = user_data.get("contract_number")
        session["ga_verified"] = True

    print(f"✅ Reset password successful. Auto-login for user: {user_data.get('user_id')}, tab_id: {tab_id}")

    redirect_url = url_for("dashboard") + ("?tab_id=" + tab_id if tab_id else "")

    return jsonify({
        "message": "Password updated successfully! Redirecting to your dashboard...",
        "redirect": redirect_url,
        "tab_id": tab_id,
        "username": actual_username,
        "user_id": user_data.get("user_id")
    }), 200



@app.route("/api/get-user-status")
def get_user_status():
    """Get the current user's status"""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    user_id = session["user_id"]
    
    query = "SELECT status FROM users WHERE user_id = %s LIMIT 1"
    user = execute_query(query, (user_id,), fetch_one=True)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({"status": user.get("status", "Active")})



# ===============================
# USER DASHBOARD (XAMPP/MYSQL VERSION) - WITH PROPER TAB ID SUPPORT
# ===============================
@app.route("/user/dashboard")
@login_required
def dashboard():
    # 👇 KUNIN ANG TAB ID MULA SA URL PARAMETER
    tab_id = request.args.get("tab_id")
    
    # 👇 KUNG WALANG TAB ID SA URL, TINGNAN KUNG NASA SESSION
    if not tab_id:
        tab_id = session.get("active_tab")
    
    # 👇 KUNG WALANG TAB ID, REDIRECT SA LOGIN
    if not tab_id:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))
    
    # 👇 KUNIN ANG USER DATA GAMIT ANG TAB ID
    user_session = session.get(f"user_{tab_id}")
    
    if user_session:
        user_id = user_session.get("user_id")
    else:
        # FALLBACK: USE REGULAR SESSION
        user_id = session.get("user_id")
    
    # 👇 KUNG WALANG USER_ID, REDIRECT SA LOGIN
    if not user_id:
        flash("Session expired. Please login again.", "warning")
        return redirect(url_for("login"))
    
    print(f"DEBUG: Dashboard - User ID: {user_id}")
    print(f"DEBUG: Dashboard - Tab ID: {tab_id}")
    print(f"DEBUG: Session keys: {list(session.keys())}")

    # ========== GET USER DATA FIRST ==========
    user_query = "SELECT application_number, ga_enabled, ga_secret FROM users WHERE user_id = %s"
    user_data = execute_query(user_query, (user_id,), fetch_one=True)
    
    application_number = user_data.get("application_number") if user_data else None
    ga_enabled = bool(user_data.get("ga_enabled")) if user_data else False
    ga_secret = user_data.get("ga_secret") if user_data else None
    if not ga_enabled and not ga_secret:
        ga_secret = session.get("ga_setup_secret")
    if not ga_secret and not ga_enabled:
        ga_secret = generate_ga_secret()
        session["ga_setup_secret"] = ga_secret
    ga_setup_uri = generate_ga_provisioning_uri(user_id, ga_secret) if ga_secret else ""
    
    # ========== GET APPLICATIONS USING application_number ==========
    if application_number:
        query = "SELECT * FROM applications WHERE application_number = %s ORDER BY timestamp DESC"
        app_list = execute_query(query, (application_number,), fetch_all=True) or []
    else:
        app_list = []
    
    # Convert None to empty string for template
    for app in app_list:
        app = {k: (v if v is not None else '') for k, v in app.items()}

    return render_template("user-dashboard.html", 
                         applications=app_list,
                         user_id=user_id,
                         application_number=application_number,
                         ga_enabled=ga_enabled,
                         ga_setup_uri=ga_setup_uri,
                         ga_secret=ga_secret,
                         tab_id=tab_id)


# ===============================
# SERVER TIME ROUTE
# ===============================
@app.route("/api/server-time")
def server_time():
    from datetime import datetime
    return jsonify({
        "server_time": datetime.now().isoformat()
    })


# ===============================
# GET ANNOUNCEMENTS (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/api/get-announcements")
def get_announcements():
    try:
        # Get current time for expiration check
        current_time = datetime.now().isoformat()
        
        query = """
            SELECT id, title, message, image_path, date, timestamp, expirationDate
            FROM announcements 
            WHERE expirationDate IS NULL OR expirationDate > %s
            ORDER BY timestamp DESC
        """
        announcements_data = execute_query(query, (current_time,), fetch_all=True) or []
        
        announcements = []
        for ann in announcements_data:
            announcements.append({
                "id": ann.get("id"),
                "title": ann.get("title", ""),
                "message": ann.get("message", ""),
                "imageBase64": ann.get("image_path"),
                "image_path": ann.get("image_path"),
                "date": ann.get("date", ""),
                "timestamp": ann.get("timestamp", 0),
                "expirationDate": ann.get("expirationDate")
            })
        
        return jsonify(announcements)
        
    except Exception as e:
        print(f"Error getting announcements: {e}")
        return jsonify([])


@app.route("/api/get-user-connection")
def get_user_connection():
    if "user_id" not in session:
        return jsonify([])

    user_id = session["user_id"]

    try:
        # ===== GET USER FROM MYSQL - KASAMA ANG BALANCE =====
        user_query = """
            SELECT user_id, application_number, email, username,
                   connection_status, contract_number, first_name, last_name, 
                   middle_name, suffix, contact_number, address, 
                   status as user_status, balance  # ← IDAGDAG ANG BALANCE
            FROM users 
            WHERE user_id = %s
            LIMIT 1
        """
        user = execute_query(user_query, (user_id,), fetch_one=True)

        if not user:
            return jsonify([])

        connection_status = user.get("connection_status", "Disconnected")
        contract_number = user.get("contract_number", "No Contract")
        application_number = user.get("application_number")
        email = user.get("email")
        user_status = user.get("user_status", "Active")
        balance = user.get("balance", 0)  # 🔥 KUNIN ANG BALANCE

        if not application_number:
            return jsonify([{
                "firstname": user.get("first_name", ""),
                "middlename": user.get("middle_name", ""),
                "lastname": user.get("last_name", ""),
                "suffix": user.get("suffix", ""),
                "plan_name": "No Active Plan",
                "mbps": "0",
                "status": user_status,
                "connection_status": connection_status,
                "contract_number": contract_number,
                "balance": float(balance) if balance else 0  # ← IDAGDAG
            }])

        # ===== GET CUSTOMER DATA =====
        customer_query = """
            SELECT first_name, last_name, middle_name, suffix, 
                   plan, plan_speed, plan_price, contract_number, 
                   status, installation_status, billing_date
            FROM customers 
            WHERE application_number = %s
            LIMIT 1
        """
        customer = execute_query(customer_query, (application_number,), fetch_one=True)

        if customer:
            plan_name = customer.get("plan", "Basic Package")
            plan_speed = customer.get("plan_speed", "0")
            app_status = customer.get("status", "Pending")
            installation_status = customer.get("installation_status", "Pending")
            contract_number = customer.get("contract_number", contract_number)
            
            # 🔥 CRITICAL: Kung ang user_status ay "Active", gamitin yun
            if user_status == "Active":
                display_status = "Active"
            elif user_status in ["Terminated", "Inactive"]:
                display_status = user_status
            else:
                # Fallback: gamitin ang app_status logic
                if app_status == "Pending":
                    display_status = "Pending Approval"
                elif app_status == "Approved" and installation_status == "Pending":
                    display_status = "Installation Pending"
                elif app_status == "Approved" and installation_status == "Ongoing":
                    display_status = "Installation Ongoing"
                elif app_status == "Approved" and installation_status == "Installed":
                    display_status = "Active"
                elif app_status == "Rejected":
                    display_status = "Rejected"
                else:
                    display_status = app_status
            
            # Extract mbps from plan_speed
            mbps = "0"
            import re
            if plan_speed:
                speed_match = re.search(r'(\d+)', str(plan_speed))
                if speed_match:
                    mbps = speed_match.group(1)
            
            first_name = customer.get("first_name")
            last_name = customer.get("last_name")
            middle_name = customer.get("middle_name")
            suffix = customer.get("suffix")
            
        else:
            # Fallback: gamitin ang applications table
            app_query = """
                SELECT plan, plan_speed, status, installation_status, plan_price
                FROM applications 
                WHERE application_number = %s
                LIMIT 1
            """
            application = execute_query(app_query, (application_number,), fetch_one=True)
            
            if not application:
                return jsonify([{
                    "firstname": user.get("first_name", ""),
                    "middlename": user.get("middle_name", ""),
                    "lastname": user.get("last_name", ""),
                    "suffix": user.get("suffix", ""),
                    "plan_name": "No Active Plan",
                    "mbps": "0",
                    "status": user_status,
                    "connection_status": connection_status,
                    "contract_number": contract_number,
                    "balance": float(balance) if balance else 0  # ← IDAGDAG
                }])
            
            plan_name = application.get("plan", "Basic Package")
            plan_speed = application.get("plan_speed", "0")
            app_status = application.get("status", "Pending")
            installation_status = application.get("installation_status", "Pending")
            
            # 🔥 CRITICAL: Same logic para sa applications table
            if user_status == "Active":
                display_status = "Active"
            elif user_status in ["Terminated", "Inactive"]:
                display_status = user_status
            else:
                if app_status == "Pending":
                    display_status = "Pending Approval"
                elif app_status == "Approved" and installation_status == "Pending":
                    display_status = "Installation Pending"
                elif app_status == "Approved" and installation_status == "Ongoing":
                    display_status = "Installation Ongoing"
                elif app_status == "Approved" and installation_status == "Installed":
                    display_status = "Active"
                elif app_status == "Rejected":
                    display_status = "Rejected"
                else:
                    display_status = app_status
            
            # Extract mbps from plan_speed
            mbps = "0"
            import re
            if plan_speed:
                speed_match = re.search(r'(\d+)', str(plan_speed))
                if speed_match:
                    mbps = speed_match.group(1)
            
            first_name = user.get("first_name")
            last_name = user.get("last_name")
            middle_name = user.get("middle_name")
            suffix = user.get("suffix")

        # ===== FINAL RESULT - KASAMA ANG BALANCE =====
        result = [{
            "firstname": first_name or "",
            "middlename": middle_name or "",
            "lastname": last_name or "",
            "suffix": suffix or "",
            "plan_name": plan_name,
            "mbps": mbps,
            "status": display_status,
            "connection_status": connection_status,
            "contract_number": contract_number,
            "balance": float(balance) if balance else 0  # ← IDAGDAG ANG BALANCE
        }]

        return jsonify(result)

    except Exception as e:
        print(f"ERROR in get_user_connection: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])



# ===============================
# GET RECONNECT MODAL DATA (prefill + current plan + full name + full address)
# ===============================
@app.route("/api/get-reconnect-info")
@login_required
def get_reconnect_info():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["user_id"]

    user_query = """
        SELECT first_name, last_name, middle_name, suffix,
               contact_number, email, address, application_number,
               has_pending_reconnect
        FROM users
        WHERE user_id = %s
        LIMIT 1
    """
    user = execute_query(user_query, (user_id,), fetch_one=True)

    if not user:
        return jsonify({"error": "User not found"}), 404

    application_number = user.get("application_number")
    already_requested = bool(user.get("has_pending_reconnect"))

    plan_name, plan_speed, plan_price = "No Active Plan", "0", "0"
    
    # ✅ FULL NAME
    first_name = user.get("first_name") or ""
    middle_name = user.get("middle_name") or ""
    last_name = user.get("last_name") or ""
    suffix = user.get("suffix") or ""
    
    # ✅ BUMUO NG FULL NAME
    full_name = " ".join(filter(None, [first_name, middle_name, last_name, suffix]))
    
    # ✅ ADDRESS FIELDS
    address = ""
    barangay = ""
    city = ""
    province = ""
    zip_code = ""
    full_address = ""

    if application_number:
        # Get current plan and address from customers table
        customer_query = """
            SELECT plan, plan_speed, plan_price, address, barangay, city, province, zip
            FROM customers
            WHERE application_number = %s
            LIMIT 1
        """
        customer = execute_query(customer_query, (application_number,), fetch_one=True)

        if customer and customer.get("plan"):
            plan_name = customer.get("plan") or plan_name
            plan_speed = customer.get("plan_speed") or plan_speed
            plan_price = customer.get("plan_price") or plan_price
            
            # ✅ KUNIN ANG ADDRESS
            address = customer.get("address") or ""
            barangay = customer.get("barangay") or ""
            city = customer.get("city") or ""
            province = customer.get("province") or ""
            zip_code = customer.get("zip") or ""
            
            # ✅ BUMUO NG FULL ADDRESS
            full_address = " ".join(filter(None, [
                address, 
                barangay, 
                city, 
                province, 
                zip_code
            ]))
        else:
            # Fallback to applications table
            app_query = """
                SELECT plan, plan_speed, plan_price, address, barangay, city, province, zip
                FROM applications
                WHERE application_number = %s
                LIMIT 1
            """
            application = execute_query(app_query, (application_number,), fetch_one=True)
            if application and application.get("plan"):
                plan_name = application.get("plan") or plan_name
                plan_speed = application.get("plan_speed") or plan_speed
                plan_price = application.get("plan_price") or plan_price
                
                address = application.get("address") or ""
                barangay = application.get("barangay") or ""
                city = application.get("city") or ""
                province = application.get("province") or ""
                zip_code = application.get("zip") or ""
                
                # ✅ BUMUO NG FULL ADDRESS
                full_address = " ".join(filter(None, [
                    address, 
                    barangay, 
                    city, 
                    province, 
                    zip_code
                ]))

    return jsonify({
        "full_name": full_name,  # ✅ ITO ANG GAGAMITIN SA FRONTEND
        "contact_number": user.get("contact_number") or "",
        "email": user.get("email") or "",
        "application_number": application_number,
        "already_requested": already_requested,
        "full_address": full_address,  # ✅ ITO ANG GAGAMITIN SA FRONTEND
        "current_plan": {
            "name": plan_name,
            "speed": plan_speed,
            "price": plan_price
        }
    })


# ===============================
# GET AVAILABLE PLANS (para sa reconnect change-plan dropdown)
# ===============================
@app.route("/api/get-plans-for-reconnect")
def get_plans_for_reconnect():
    try:
        query = "SELECT id, name, speed, price FROM plans ORDER BY price ASC"
        plans = execute_query(query, (), fetch_all=True) or []
        print(f"📋 Retrieved {len(plans)} plans from database")
        
        # ✅ I-PRINT ANG MGA PLANS PARA MAKITA
        for plan in plans:
            print(f"  - ID: {plan.get('id')}, Name: {plan.get('name')}, Speed: {plan.get('speed')}, Price: {plan.get('price')}")
        
        return jsonify(plans)
    except Exception as e:
        print(f"❌ Error fetching plans: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch plans"}), 500


# ===============================
# GENERATE RANDOM REQUEST NUMBER (format: REQ20260723-ABCDE)
# ===============================
def generate_request_number():
    import random
    import string
    from datetime import datetime
    
    date_str = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    candidate = f"REQ{date_str}-{random_part}"
    
    # ✅ I-CHECK KUNG EXISTING NA
    existing = execute_query(
        "SELECT request_id FROM reconnect_requests WHERE request_id = %s LIMIT 1",
        (candidate,), fetch_one=True
    )
    
    attempts = 0
    while existing and attempts < 20:
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        candidate = f"REQ{date_str}-{random_part}"
        existing = execute_query(
            "SELECT request_id FROM reconnect_requests WHERE request_id = %s LIMIT 1",
            (candidate,), fetch_one=True
        )
        attempts += 1
    
    return candidate


# ===============================
# SUBMIT RECONNECT REQUEST
# ===============================
@app.route("/api/submit-reconnect-request", methods=["POST"])
@login_required
def submit_reconnect_request():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    print(f"📥 Received data: {data}")

    # ✅ I-HANDLE ANG change_plan
    change_plan = data.get("change_plan", False)
    if isinstance(change_plan, bool):
        change_plan = change_plan
    else:
        change_plan = bool(change_plan) or change_plan == 1

    # ✅ KUNG WALANG CHANGE PLAN, I-SET ANG new_plan_id SA None
    if not change_plan:
        new_plan_id = None
    else:
        new_plan_id = data.get("new_plan_id")
        if new_plan_id is None or new_plan_id == '' or new_plan_id == 0:
            return jsonify({"error": "Please select a plan."}), 400
        try:
            new_plan_id = int(new_plan_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid plan selected."}), 400
    
    print(f"📥 change_plan: {change_plan}, new_plan_id: {new_plan_id}")

    first_name = (data.get("first_name") or "").strip()
    middle_name = (data.get("middle_name") or "").strip() or None
    last_name = (data.get("last_name") or "").strip() or None
    suffix = (data.get("suffix") or "").strip() or None
    contact_number = (data.get("contact_number") or "").strip()
    email = (data.get("email") or "").strip()
    address = (data.get("address") or "").strip()

    # --- VALIDATION ---
    if not first_name:
        return jsonify({"error": "First name is required."}), 400
    if not contact_number:
        return jsonify({"error": "Contact number is required."}), 400
    if not email:
        return jsonify({"error": "Email is required."}), 400
    if not address:
        return jsonify({"error": "Address is required."}), 400
    if change_plan and not new_plan_id:
        return jsonify({"error": "Please select a plan."}), 400

    # --- CHECK USER ---
    user_row = execute_query(
        "SELECT application_number, has_pending_reconnect FROM users WHERE user_id = %s LIMIT 1",
        (user_id,), fetch_one=True
    )
    if not user_row:
        return jsonify({"error": "User not found"}), 404

    # ✅ BAGONG CHECK: kasama na ang "approved but awaiting slot reassignment" state
    if user_row.get("has_pending_reconnect"):
        return jsonify({"error": "You already have a reconnect request on file. Please wait for slot reassignment or admin approval."}), 409

    # ✅ CHECK: KUNG MAY PENDING REQUEST (safety net, existing check)
    pending = execute_query(
        "SELECT request_id, status FROM reconnect_requests WHERE user_id = %s AND status = 'Pending' LIMIT 1",
        (user_id,), fetch_one=True
    )
    if pending:
        return jsonify({"error": "You already have a pending reconnect request. Please wait for admin approval."}), 409

    application_number = user_row.get("application_number")

    # --- GET CURRENT PLAN ---
    current_plan_name, current_plan_speed, current_plan_price = None, None, None
    if application_number:
        customer_row = execute_query(
            "SELECT plan, plan_speed, plan_price FROM customers WHERE application_number = %s LIMIT 1",
            (application_number,), fetch_one=True
        )
        if customer_row:
            current_plan_name = customer_row.get("plan")
            current_plan_speed = customer_row.get("plan_speed")
            current_plan_price = customer_row.get("plan_price")

    # --- GET NEW PLAN NAME ---
    new_plan_name = None
    new_plan_speed = None
    new_plan_price = None
    
    if change_plan and new_plan_id:
        plan_row = execute_query(
            "SELECT name, speed, price FROM plans WHERE id = %s LIMIT 1",
            (new_plan_id,), fetch_one=True
        )
        if plan_row:
            new_plan_name = plan_row.get("name")
            new_plan_speed = plan_row.get("speed")
            new_plan_price = plan_row.get("price")

    # ✅ GENERATE REQUEST NUMBER
    request_id = generate_request_number()
    print(f"🆕 Generated new request_id: {request_id}")

    # ✅ INSERT RECONNECT REQUEST
    try:
        insert_query = """
            INSERT INTO reconnect_requests
                (request_id, user_id, application_number, change_plan, new_plan_id, new_plan_name,
                 current_plan_name, current_plan_speed, current_plan_price,
                 first_name, middle_name, last_name, suffix,
                 contact_number, email, address, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending', NOW())
        """
        execute_query(insert_query, (
            request_id, 
            user_id, 
            application_number, 
            int(change_plan),
            new_plan_id,
            new_plan_name,
            current_plan_name, 
            current_plan_speed, 
            current_plan_price,
            first_name, 
            middle_name, 
            last_name, 
            suffix,
            contact_number, 
            email, 
            address
        ))
        print(f"✅ Inserted NEW request {request_id} for user {user_id}")

    except Exception as e:
        print(f"❌ ERROR saving reconnect_requests: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to submit reconnect request. Please try again."}), 500

    # ✅ UPDATE USER
    try:
        execute_query(
            "UPDATE users SET has_pending_reconnect = 1, reconnect_requested_at = NOW() WHERE user_id = %s",
            (user_id,)
        )
        print(f"✅ Updated user {user_id} has_pending_reconnect = 1")
    except Exception as e:
        print(f"⚠️ WARNING: User update failed: {e}")

    # ✅ INSERT NOTIFICATION - GAYA NG TERMINATION REQUEST
    try:
        from datetime import datetime
        
        full_name = " ".join(filter(None, [first_name, middle_name, last_name, suffix]))
        
        # ✅ GUMAMIT NG CUSTOM ID (timestamp * 1000) tulad ng termination
        notification_id = int(datetime.now().timestamp() * 1000)
        
        # ✅ BUUIN ANG MESSAGE - GAYA NG TERMINATION FORMAT
        notif_message = f"[{request_id}] {full_name} requested reconnection"
        if change_plan and new_plan_name:
            notif_message += f" with plan change to {new_plan_name}"
        notif_message += f" - Application #{application_number}"

        print(f"🔔 Inserting notification:")
        print(f"   ID: {notification_id}")
        print(f"   Title: Reconnect Request")
        print(f"   Message: {notif_message}")
        print(f"   Type: reconnect_request")
        print(f"   relatedId: {application_number}")

        # ✅ INSERT SA notifications TABLE
        notif_query = """
            INSERT INTO notifications (id, title, message, type, relatedId, timestamp, read_status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # ✅ I-TRAP ANG EXECUTION PARA MAKITA KUNG MAY ERROR
        try:
            result = execute_query(notif_query, (
                notification_id,
                "Reconnect Request",
                notif_message,
                "reconnect_request",
                application_number,
                datetime.now().isoformat(),
                0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            print(f"✅ execute_query result: {result}")
            
            # ✅ VERIFY NA NA-INSERT
            verify_query = "SELECT id, message FROM notifications WHERE id = %s"
            verify_result = execute_query(verify_query, (notification_id,), fetch_one=True)
            
            if verify_result:
                print(f"✅ VERIFIED: Notification exists - ID: {verify_result['id']}")
                print(f"   Message: {verify_result['message']}")
            else:
                print(f"❌ NOT FOUND: Notification {notification_id} not in database!")
                
        except Exception as insert_error:
            print(f"❌ NOTIFICATION INSERT FAILED: {insert_error}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ NOTIFICATION PREPARATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        # ✅ Huwag mag-fail ang buong request dahil sa notification

    # ✅ RETURN RESPONSE
    return jsonify({
        "success": True,
        "request_id": request_id,
        "message": f"Your reconnect request has been submitted. Reference #: {request_id}",
        "current_plan": {
            "name": current_plan_name or "No Active Plan",
            "speed": current_plan_speed or "0",
            "price": current_plan_price or "0"
        },
        "new_plan": {
            "name": new_plan_name if change_plan else None,
            "speed": new_plan_speed if change_plan else None,
            "price": new_plan_price if change_plan else None
        },
        "change_plan": change_plan
    })



# ===============================
# GET USER NOTIFICATIONS (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/api/user/notifications", methods=["GET"])
def get_user_notifications():
    try:
        user_id = request.args.get("user_id")
        tab_id = request.args.get("tab_id")  # 👈 KUNIN ANG TAB ID
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        # 👇 KUNG MAY TAB ID, I-VERIFY NA TAMA ANG USER
        if tab_id:
            user_session = session.get(f"user_{tab_id}")
            if user_session and user_session.get("user_id") != user_id:
                return jsonify({"error": "Unauthorized"}), 401
        
        # Query notifications from MySQL
        query = """
            SELECT id, title, message, type, relatedId, user_id, user_email, user_name,
                   connection_status, timestamp, read_status
            FROM user_notifications 
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT 50
        """
        notifications = execute_query(query, (user_id,), fetch_all=True) or []
        
        # Format response
        result = []
        for notif in notifications:
            result.append({
                "id": notif.get("id"),
                "title": notif.get("title", ""),
                "message": notif.get("message", ""),
                "type": notif.get("type", "info"),
                "relatedId": notif.get("relatedId"),
                "user_id": notif.get("user_id"),
                "user_email": notif.get("user_email"),
                "user_name": notif.get("user_name"),
                "connection_status": notif.get("connection_status"),
                "timestamp": notif.get("timestamp", ""),
                "read": notif.get("read_status") == 1
            })
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error getting user notifications: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

# ===============================
# MARK USER NOTIFICATION AS READ (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/api/user/notifications/<int:notification_id>/read", methods=["PUT"])
def mark_user_notification_read(notification_id):
    try:
        tab_id = request.args.get("tab_id")  # 👈 KUNIN ANG TAB ID
        
        # 👇 KUNG MAY TAB ID, I-VERIFY NA TAMA ANG USER
        if tab_id:
            user_session = session.get(f"user_{tab_id}")
            if not user_session:
                return jsonify({"error": "Unauthorized"}), 401
        
        # Check if notification exists
        check_query = "SELECT id FROM user_notifications WHERE id = %s"
        exists = execute_query(check_query, (notification_id,), fetch_one=True)
        
        if not exists:
            return jsonify({"error": "Notification not found"}), 404
        
        # Update read_status to 1
        update_query = "UPDATE user_notifications SET read_status = 1 WHERE id = %s AND read_status = 0"
        rows_affected = execute_query(update_query, (notification_id,))
        
        if rows_affected > 0:
            print(f" Notification {notification_id} marked as read")
        
        return jsonify({"message": "Notification marked as read"})
    
    except Exception as e:
        print(f"Error marking notification as read: {e}")
        return jsonify({"error": str(e)}), 500

# ===============================
# MARK ALL USER NOTIFICATIONS AS READ (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/api/user/notifications/read-all", methods=["PUT"])
def mark_all_user_notifications_read():
    try:
        user_id = request.args.get("user_id")
        tab_id = request.args.get("tab_id")  # 👈 KUNIN ANG TAB ID
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        # 👇 KUNG MAY TAB ID, I-VERIFY NA TAMA ANG USER
        if tab_id:
            user_session = session.get(f"user_{tab_id}")
            if not user_session or user_session.get("user_id") != user_id:
                return jsonify({"error": "Unauthorized"}), 401
        
        # Update all unread notifications for this user
        update_query = "UPDATE user_notifications SET read_status = 1 WHERE user_id = %s AND read_status = 0"
        rows_affected = execute_query(update_query, (user_id,))
        
        print(f" Marked {rows_affected} notifications as read for user {user_id}")
        return jsonify({"message": f"Marked {rows_affected} notifications as read", "count": rows_affected})
    
    except Exception as e:
        print(f"Error marking all notifications as read: {e}")
        return jsonify({"error": str(e)}), 500


# ===============================
# USER LOGIN HISTORY ROUTES
# ===============================
def get_current_user_from_session(req=None):
    tab_id = None
    if req:
        tab_id = req.args.get("tab_id")
        if not tab_id and req.is_json:
            data = req.get_json(silent=True) or {}
            tab_id = data.get("tab_id")

    if not tab_id:
        tab_id = session.get("active_tab")

    if tab_id:
        user_sess = session.get(f"user_{tab_id}")
        if user_sess and user_sess.get("user_id"):
            return user_sess.get("user_id"), tab_id

    if "user_id" in session:
        return session.get("user_id"), tab_id or session.get("active_tab") or "main"

    for k, v in session.items():
        if isinstance(k, str) and k.startswith("user_") and isinstance(v, dict) and v.get("user_id"):
            extracted_tab = k.replace("user_", "")
            return v.get("user_id"), extracted_tab

    if req:
        username = req.args.get("username")
        if username:
            user_data = execute_query(
                "SELECT user_id FROM users WHERE user_id = %s OR username = %s OR email = %s LIMIT 1",
                (username, username, username),
                fetch_one=True
            )
            if user_data:
                return user_data.get("user_id"), tab_id or "main"

    return None, None


@app.route("/user/login-history")
@login_required
def user_login_history():
    return render_template("user-login-history.html")


@app.route("/api/user/login-history", methods=["GET"])
def get_user_login_history_api():
    try:
        user_id, current_token = get_current_user_from_session(request)

        if not user_id:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        ensure_login_history_table()

        if current_token:
            record_login_history(user_id, current_token)

        rows = execute_query(
            "SELECT id, user_id, session_token, device_info, browser, os, ip_address, location, "
            "DATE_FORMAT(login_time, '%b %d, %Y %h:%i %p') as formatted_login_time, "
            "DATE_FORMAT(last_active, '%b %d, %Y %h:%i %p') as formatted_last_active, "
            "status FROM login_history WHERE user_id = %s ORDER BY id DESC",
            (user_id,),
            fetch_all=True
        ) or []

        current_device = None
        other_devices = []

        for row in rows:
            is_curr = (row.get("session_token") == current_token) or (current_token is None and current_device is None)
            row["is_current"] = is_curr
            if is_curr and not current_device:
                current_device = row
            else:
                other_devices.append(row)

        if not current_device and rows:
            current_device = rows[0]
            current_device["is_current"] = True
            other_devices = [r for r in rows if r["id"] != current_device["id"]]

        return jsonify({
            "success": True,
            "current_device": current_device,
            "other_devices": other_devices,
            "all_history": rows
        })
    except Exception as e:
        print(f"[API LOGIN HISTORY ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/check-new-devices", methods=["GET"])
def check_new_devices():
    try:
        user_id, current_tab = get_current_user_from_session(request)
        if not user_id:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        tab_id = request.args.get("tab_id") or current_tab
        last_check = request.args.get("last_check", "0")

        try:
            last_check_ts = float(last_check)
        except (TypeError, ValueError):
            last_check_ts = 0

        rows = execute_query(
            """
            SELECT id, user_id, session_token, device_info, browser, os, ip_address, location,
                   login_time,
                   DATE_FORMAT(login_time, '%b %d, %Y %h:%i %p') AS formatted_login_time,
                   status
            FROM login_history
            WHERE user_id = %s AND session_token != %s
            ORDER BY login_time DESC
            """,
            (user_id, tab_id or ""),
            fetch_all=True
        ) or []

        new_devices = []
        for row in rows:
            try:
                login_ts = datetime.strptime(str(row.get("login_time") or "1970-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S").timestamp()
            except Exception:
                continue

            if login_ts <= last_check_ts:
                continue

            row_data = {
                "id": row.get("id"),
                "user_id": row.get("user_id"),
                "session_token": row.get("session_token"),
                "device_info": row.get("device_info") or "Unknown Device",
                "device_brand": row.get("device_info") or "Unknown Device",
                "browser": row.get("browser") or "Unknown Browser",
                "os": row.get("os") or "Unknown OS",
                "ip_address": row.get("ip_address") or "Unknown",
                "location": row.get("location") or "Unknown Location",
                "login_time": row.get("login_time"),
                "formatted_login_time": row.get("formatted_login_time") or "Just now",
                "status": row.get("status") or "Active"
            }
            new_devices.append(row_data)

        return jsonify({
            "success": True,
            "new_devices": new_devices,
            "current_timestamp": int(time.time())
        })
    except Exception as e:
        print(f"[CHECK NEW DEVICES ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/logout-device", methods=["POST"])
def logout_device_api():
    try:
        data = request.get_json(silent=True) or {}
        device_id = data.get("device_id") or request.args.get("device_id")
        user_id, current_tab = get_current_user_from_session(request)

        if not user_id:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        if not device_id:
            return jsonify({"success": False, "error": "No device selected"}), 400

        execute_query(
            "DELETE FROM login_history WHERE user_id = %s AND id = %s",
            (user_id, device_id)
        )

        return jsonify({
            "success": True,
            "message": "Device logged out successfully"
        })
    except Exception as e:
        print(f"[LOGOUT DEVICE API ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/user/login-history/logout", methods=["POST"])
def logout_user_device():
    try:
        data = request.get_json() or {}
        device_ids = data.get("device_ids", [])
        user_id, current_token = get_current_user_from_session(request)

        if isinstance(device_ids, (int, str)):
            device_ids = [device_ids]

        if not user_id:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        if not device_ids:
            return jsonify({"success": False, "error": "No devices specified"}), 400

        current_rec = None
        if current_token:
            current_rec = execute_query(
                "SELECT id FROM login_history WHERE user_id = %s AND session_token = %s LIMIT 1",
                (user_id, current_token),
                fetch_one=True
            )
        current_id = current_rec.get("id") if current_rec else None

        logout_current = any(str(did) == str(current_id) for did in device_ids)

        format_strings = ','.join(['%s'] * len(device_ids))
        query_params = [user_id] + device_ids
        execute_query(
            f"DELETE FROM login_history WHERE user_id = %s AND id IN ({format_strings})",
            query_params
        )

        tab_id = request.args.get("tab_id") or data.get("tab_id") or current_token
        if logout_current:
            if tab_id and f"user_{tab_id}" in session:
                session.pop(f"user_{tab_id}", None)
            else:
                for key in list(session.keys()):
                    if isinstance(key, str) and key.startswith("user_"):
                        user_sess = session.get(key)
                        if isinstance(user_sess, dict) and user_sess.get("user_id") == user_id:
                            session.pop(key, None)
            session.pop("user_id", None)
            session.pop("active_tab", None)

        return jsonify({
            "success": True,
            "message": "Device(s) logged out and record deleted successfully",
            "logout_current": logout_current
        })
    except Exception as e:
        print(f"[LOGOUT DEVICE ERROR] {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/user/login-history/logout-all", methods=["POST"])
def logout_all_user_devices():
    try:
        data = request.get_json() or {}
        include_current = data.get("include_current", False)
        user_id, current_token = get_current_user_from_session(request)

        if not user_id:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        tab_id = request.args.get("tab_id") or data.get("tab_id") or current_token

        if include_current:
            execute_query("DELETE FROM login_history WHERE user_id = %s", (user_id,))
            if tab_id and f"user_{tab_id}" in session:
                session.pop(f"user_{tab_id}", None)
            else:
                for key in list(session.keys()):
                    if isinstance(key, str) and key.startswith("user_"):
                        user_sess = session.get(key)
                        if isinstance(user_sess, dict) and user_sess.get("user_id") == user_id:
                            session.pop(key, None)
            session.pop("user_id", None)
            logout_current = True
        else:
            if current_token:
                execute_query("DELETE FROM login_history WHERE user_id = %s AND session_token != %s", (user_id, current_token))
            else:
                execute_query("DELETE FROM login_history WHERE user_id = %s", (user_id,))
            logout_current = False

        return jsonify({
            "success": True,
            "message": "All other devices logged out and records deleted",
            "logout_current": logout_current
        })
    except Exception as e:
        print(f"[LOGOUT ALL ERROR] {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ===============================
# USER PROFILE - XAMPP/MYSQL VERSION
# ===============================
@app.route("/user/profile")
@login_required
def user_profile():
    # 👇 KUNIN ANG TAB ID MULA SA URL
    tab_id = request.args.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
            customer_id = user_session.get("customer_id")
        else:
            flash("Invalid session. Please login again.", "warning")
            return redirect(url_for("login"))
    else:
        # Fallback sa regular session
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        user_id = session.get("user_id")
        customer_id = session.get("customer_id")
    
    # Retrieve from session or get from DB
    if not customer_id:
        # Get customer_id from users table
        user_query = "SELECT customer_id FROM users WHERE user_id = %s"
        user_data_db = execute_query(user_query, (user_id,), fetch_one=True)
        if user_data_db:
            customer_id = user_data_db.get("customer_id")
            session["customer_id"] = customer_id

    print(f"DEBUG: Profile - User ID: {user_id}, Customer ID: {customer_id}")

    # ========== GET USER DATA FROM MYSQL ==========
    user_query = """
        SELECT user_id, email, first_name, last_name, middle_name, suffix, 
               contact_number, address, role, profile_photo, contract_number,
               connection_status, status, created_at, ga_enabled, ga_secret
        FROM users 
        WHERE user_id = %s
        LIMIT 1
    """
    user_data = execute_query(user_query, (user_id,), fetch_one=True)
    
    if not user_data:
        flash("User not found.", "danger")
        return redirect(url_for("dashboard"))

    # ========== GET APPLICATION DATA USING customer_id (application_number) ==========
    application_data = None
    application_id = None

    if customer_id:
        app_query = """
            SELECT * FROM applications 
            WHERE application_number = %s
            LIMIT 1
        """
        application_data = execute_query(app_query, (customer_id,), fetch_one=True)
        if application_data:
            application_id = customer_id
            print(f"DEBUG: Found application via application_number: {customer_id}")
        else:
            print(f"DEBUG: No application found for application_number: {customer_id}")
    else:
        print("DEBUG: customer_id is missing in session")

    # ========== FALLBACK: Get application by email ==========
    if not application_data and user_data.get("email"):
        email = user_data["email"]
        app_query = "SELECT * FROM applications WHERE email = %s ORDER BY timestamp DESC LIMIT 1"
        application_data = execute_query(app_query, (email,), fetch_one=True)
        if application_data:
            application_id = application_data.get("application_number")
            print(f"DEBUG: Found application via email: {application_id}")

    # ========== CLEAN VALUE HELPER ==========
    def clean_value(value):
        """Remove 'none' string and empty values"""
        if not value:
            return ""
        value_str = str(value).strip()
        if value_str.lower() == "none" or value_str == "":
            return ""
        return value_str

    # ========== CONSTRUCT FULL NAME ==========
    full_name = ""
    if application_data:
        first = clean_value(application_data.get("first_name", ""))
        middle = clean_value(application_data.get("middle_name", ""))
        last = clean_value(application_data.get("last_name", ""))
        suffix = clean_value(application_data.get("suffix", ""))
        
        name_parts = []
        if first:
            name_parts.append(first)
        if middle:
            name_parts.append(middle)
        if last:
            name_parts.append(last)
        if suffix:
            name_parts.append(suffix)
        
        full_name = " ".join(name_parts)
        
    if not full_name:
        full_name = clean_value(user_data.get("first_name", user_id))

    # ========== OTHER FIELDS ==========
    contact_number = application_data.get("mobile", "") if application_data else user_data.get("contact_number", "")
    address = application_data.get("installation_address", "") if application_data else user_data.get("address", "")
    role = user_data.get("role", "customer")

    # Profile photo
    profile_photo = user_data.get("profile_photo")
    if not profile_photo and application_data:
        profile_photo = application_data.get("profile_photo")
    if not profile_photo:
        profile_photo = url_for("static", filename="profile.jpg")

    # TV sets (parse JSON if stored as string)
    import json
    tv_brands = []
    tv_qtys = []
    tv_types = []
    
    if application_data:
        tv_brands_str = application_data.get("tv_brand")
        tv_qtys_str = application_data.get("tv_qty")
        tv_types_str = application_data.get("tv_type")
        
        if tv_brands_str and isinstance(tv_brands_str, str):
            try:
                tv_brands = json.loads(tv_brands_str)
            except:
                tv_brands = []
        elif tv_brands_str and isinstance(tv_brands_str, list):
            tv_brands = tv_brands_str
            
        if tv_qtys_str and isinstance(tv_qtys_str, str):
            try:
                tv_qtys = json.loads(tv_qtys_str)
            except:
                tv_qtys = []
        elif tv_qtys_str and isinstance(tv_qtys_str, list):
            tv_qtys = tv_qtys_str
            
        if tv_types_str and isinstance(tv_types_str, str):
            try:
                tv_types = json.loads(tv_types_str)
            except:
                tv_types = []
        elif tv_types_str and isinstance(tv_types_str, list):
            tv_types = tv_types_str
    
    tv_brands_str = ','.join(tv_brands) if tv_brands else ''
    tv_qtys_str = ','.join(str(qty) for qty in tv_qtys) if tv_qtys else ''
    tv_types_str = ','.join(tv_types) if tv_types else ''

    # Installation data
    installation_address_value = application_data.get("installation_address", "") if application_data else ""
    installation_phone_value = application_data.get("installation_phone", "") if application_data else ""
    installation_fee_value = application_data.get("installation_fee", "") if application_data else ""

    ga_enabled = bool(user_data.get("ga_enabled"))
    ga_secret = session.get("ga_setup_secret") or user_data.get("ga_secret")
    if not ga_enabled and not ga_secret:
        ga_secret = generate_ga_secret()
        session["ga_setup_secret"] = ga_secret
    ga_setup_uri = generate_ga_provisioning_uri(user_data.get("email") or user_id, ga_secret) if ga_secret else ""

    # ========== RENDER TEMPLATE ==========
    return render_template(
        "user-profile.html",
        # User info
        user_name=full_name,
        user_email=user_data.get("email", "No Email"),
        contact_number=contact_number,
        address=address,
        user_id=user_id,
        customer_id=customer_id,
        role=role,
        profile_photo=profile_photo,
        contract_number=user_data.get("contract_number", ""),

        # ========== APPLICATION DATA ==========
        first_name=application_data.get("first_name", "") if application_data else "",
        middle_name=application_data.get("middle_name", "") if application_data else "",
        last_name=application_data.get("last_name", "") if application_data else "",
        suffix=application_data.get("suffix", "") if application_data else "",
        email=application_data.get("email", "") if application_data else "",
        mobile=application_data.get("mobile", "") if application_data else "",
        secondary_mobile=application_data.get("secondary_mobile", "") if application_data else "",
        phone=application_data.get("phone", "") if application_data else "",
        birthdate=application_data.get("birthdate", "") if application_data else "",
        place_of_birth=application_data.get("place_of_birth", "") if application_data else "",
        sex=application_data.get("sex", "") if application_data else "",
        civil_status=application_data.get("civil_status", "") if application_data else "",
        citizenship=application_data.get("citizenship", "") if application_data else "",
        occupation=application_data.get("occupation", "") if application_data else "",
        home_ownership=application_data.get("home_ownership", "") if application_data else "",
        installation_fee=installation_fee_value,
        installation_address=installation_address_value,
        billing_address=application_data.get("billing_address", "") if application_data else "",
        house_number=application_data.get("house_number", "") if application_data else "",
        landmark=application_data.get("landmark", "") if application_data else "",
        barangay=application_data.get("barangay", "") if application_data else "",
        city=application_data.get("city", "") if application_data else "",
        province=application_data.get("province", "") if application_data else "",
        zip=application_data.get("zip", "") if application_data else "",
        employer=application_data.get("employer", "") if application_data else "",
        business_address=application_data.get("business_address", "") if application_data else "",
        business_phone=application_data.get("business_phone", "") if application_data else "",
        spouse_name=application_data.get("spouse_name", "") if application_data else "",
        spouse_occupation=application_data.get("spouse_occupation", "") if application_data else "",
        spouse_employer=application_data.get("spouse_employer", "") if application_data else "",
        spouse_phone=application_data.get("spouse_phone", "") if application_data else "",
        mother_maiden_name=application_data.get("mother_maiden_name", "") if application_data else "",
        father_name=application_data.get("father_name", "") if application_data else "",
        service_type=application_data.get("service_type", "") if application_data else "",
        plan=application_data.get("plan", "") if application_data else "",
        tv_brand_str=tv_brands_str,
        tv_qty_str=tv_qtys_str,
        tv_type_str=tv_types_str,
        installation_phone=installation_phone_value,
        signature=application_data.get("signature", "") if application_data else "",
        id_front=application_data.get("id_front", "") if application_data else "",
        id_back=application_data.get("id_back", "") if application_data else "",
        proof_billing=application_data.get("proof_billing", "") if application_data else "",
        date_submitted=application_data.get("date_submitted", "") if application_data else "",
        time_submitted=application_data.get("time_submitted", "") if application_data else "",
        application_number=application_id if application_id else "",
        latitude=application_data.get("latitude", "0") if application_data else "0",
        longitude=application_data.get("longitude", "0") if application_data else "0",
        ga_enabled=ga_enabled,
        ga_secret=ga_secret,
        ga_setup_uri=ga_setup_uri
    )


@app.route("/user/ga/enable", methods=["POST"])
@login_required
def enable_google_auth():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    code = request.form.get("ga_code", "").strip()
    
    # Get secret from session first, then from database
    secret = session.get("ga_setup_secret")
    
    if not secret:
        # Try to get from database
        user_row = execute_query(
            "SELECT ga_secret FROM users WHERE user_id = %s LIMIT 1",
            (user_id,),
            fetch_one=True,
        )
        secret = user_row.get("ga_secret") if user_row else None

    if not secret:
        # Generate new secret if none exists
        secret = generate_ga_secret()
        session["ga_setup_secret"] = secret
        print(f"🔐 Generated new GA secret for user {user_id}")

    if not code:
        flash("Please enter the 6-digit code from Google Authenticator.", "danger")
        return redirect(url_for("user_profile"))

    # Verify the code with debug logging
    print(f"🔐 Verifying GA code for user {user_id}")
    print(f"🔐 Secret: {secret[:10]}... (truncated)")
    print(f"🔐 Code entered: {code}")
    
    is_valid = verify_ga_code(secret, code)
    print(f"🔐 Verification result: {is_valid}")
    
    if is_valid:
        # Save the secret to database
        execute_query(
            "UPDATE users SET ga_secret = %s, ga_enabled = 1 WHERE user_id = %s", 
            (secret, user_id)
        )
        session.pop("ga_setup_secret", None)
        flash(" Google Authenticator is now enabled. Your next login will require a code.", "success")
        print(f" GA enabled for user {user_id}")
    else:
        flash(" The code did not match. Please make sure your phone's time is synced correctly and try again.", "danger")
        print(f" GA enable failed for user {user_id}")

    return redirect(url_for("user_profile"))


@app.route("/user/ga/disable", methods=["POST"])
@login_required
def disable_google_auth():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    execute_query("UPDATE users SET ga_secret = NULL, ga_enabled = 0 WHERE user_id = %s", (user_id,))
    session.pop("ga_setup_secret", None)
    flash("Google Authenticator has been disabled.", "info")
    return redirect(url_for("user_profile"))


# ===============================
# GET USER APPLICATION DATA (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/user/get-application-data")
def get_user_application_data():
    """Get application data for logged in user (for contract generation)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    user_id = session.get('user_id')  # "CV-3614"
    customer_id = session.get('customer_id')  # "4698881482" - application number
    email = session.get('email')
    
    print(f"DEBUG: get-application-data - user_id: {user_id}, customer_id: {customer_id}, email: {email}")
    
    try:
        application_data = None
        application_id = None
        
        # ========== METHOD 1: Use customer_id as application_number ==========
        if customer_id:
            app_query = """
                SELECT * FROM applications 
                WHERE application_number = %s
                LIMIT 1
            """
            application_data = execute_query(app_query, (customer_id,), fetch_one=True)
            if application_data:
                application_id = customer_id
                print(f"DEBUG: Found application using customer_id as application_number: {customer_id}")
        
        # ========== METHOD 2: Search by email ==========
        if not application_data and email:
            app_query = """
                SELECT * FROM applications 
                WHERE email = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            application_data = execute_query(app_query, (email,), fetch_one=True)
            if application_data:
                application_id = application_data.get("application_number")
                print(f"DEBUG: Found application by email: {application_id}")
        
        # ========== METHOD 3: Search by user_id in applications ==========
        if not application_data:
            app_query = """
                SELECT * FROM applications 
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            application_data = execute_query(app_query, (user_id,), fetch_one=True)
            if application_data:
                application_id = application_data.get("application_number")
                print(f"DEBUG: Found application by user_id: {application_id}")
        
        if not application_data:
            print(f"DEBUG: No application found for user_id: {user_id}, customer_id: {customer_id}")
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Convert None values to empty strings
        application_data = {k: (v if v is not None else '') for k, v in application_data.items()}
        
        # Parse JSON fields (TV details)
        import json
        for field in ['tv_qty', 'tv_brand', 'tv_type']:
            value = application_data.get(field)
            if value and isinstance(value, str):
                try:
                    application_data[field] = json.loads(value)
                except:
                    application_data[field] = []
            elif not value:
                application_data[field] = []
        
        # Ensure application_number is set
        application_data['application_number'] = application_id
        
        return jsonify({
            'success': True,
            **application_data
        })
        
    except Exception as e:
        print(f"ERROR in get_user_application_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ===============================
# USER GET CONTRACT NUMBER (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/user/get-contract-number")
def get_user_contract_number():
    """Get contract number for logged in user"""
    # 👇 KUNIN ANG TAB ID MULA SA URL
    tab_id = request.args.get("tab_id")
    
    user_id = None
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
    
    # 👇 FALLBACK: CHECK REGULAR SESSION
    if not user_id and 'user_id' in session:
        user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        # Get contract_number from users table
        query = """
            SELECT contract_number FROM users 
            WHERE user_id = %s
            LIMIT 1
        """
        user_data = execute_query(query, (user_id,), fetch_one=True)
        
        if user_data:
            contract_number = user_data.get('contract_number')
            print(f"DEBUG: Found contract_number for {user_id}: {contract_number}")
            
            if contract_number and contract_number != 'none':
                return jsonify({
                    'success': True,
                    'contract_number': contract_number
                })
        
        return jsonify({'success': False, 'contract_number': None})
        
    except Exception as e:
        print(f"ERROR in get_user_contract_number: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ===============================
# USER GET CONTRACT DETAILS (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/user/get-contract-details/<contract_number>")
def get_user_contract_details(contract_number):
    """Get contract details for logged in user"""
    # 👇 KUNIN ANG TAB ID MULA SA URL
    tab_id = request.args.get("tab_id")
    
    user_id = None
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
    
    # 👇 FALLBACK: CHECK REGULAR SESSION
    if not user_id and 'user_id' in session:
        user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        # Verify that the contract belongs to the user
        verify_query = """
            SELECT contract_number FROM users 
            WHERE user_id = %s AND contract_number = %s
            LIMIT 1
        """
        user_verify = execute_query(verify_query, (user_id, contract_number), fetch_one=True)
        
        if not user_verify:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Get contract details from contracts table
        contract_query = """
            SELECT contract_number, billing_date, first_installment_date, last_installment_date,
                   plan, status, full_name, address, barangay, city, province,
                   installation_fee, is_installment_plan, created_at
            FROM contracts 
            WHERE contract_number = %s
            LIMIT 1
        """
        contract_data = execute_query(contract_query, (contract_number,), fetch_one=True)
        
        if contract_data:
            return jsonify({
                'success': True,
                'billing_date': contract_data.get('billing_date', '15th'),
                'first_installment_date': contract_data.get('first_installment_date'),
                'last_installment_date': contract_data.get('last_installment_date'),
                'plan': contract_data.get('plan'),
                'status': contract_data.get('status'),
                'full_name': contract_data.get('full_name'),
                'address': contract_data.get('address'),
                'installation_fee': contract_data.get('installation_fee'),
                'is_installment_plan': contract_data.get('is_installment_plan', 0),
                'created_at': contract_data.get('created_at')
            })
        else:
            # Fallback: Get from users table if contract not found in contracts table
            user_query = """
                SELECT contract_number, billing_date 
                FROM users 
                WHERE user_id = %s
                LIMIT 1
            """
            user_data = execute_query(user_query, (user_id,), fetch_one=True)
            
            return jsonify({
                'success': True,
                'billing_date': user_data.get('billing_date', '15th') if user_data else '15th',
                'first_installment_date': None,
                'last_installment_date': None,
                'plan': None,
                'status': 'Active'
            })
            
    except Exception as e:
        print(f"ERROR in get_user_contract_details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ===============================
# GET SIGNATURE IMAGE FUNCTION (MOVE THIS OUTSIDE, BEFORE THE ROUTE)
# ===============================
def get_signature_image(signature_data, width=180, height=50):
    """Get signature image from file path or base64"""
    import os
    import io
    import base64
    import requests
    from reportlab.platypus import Image
    
    try:
        if not signature_data:
            print("❌ No signature data provided")
            return None
        
        if isinstance(signature_data, str):
            print(f"🔍 Processing signature: {signature_data[:100]}...")
            
            # Case 1: File path URL (starts with /shared-uploads/)
            if signature_data.startswith('/shared-uploads/'):
                # Base directory for uploaded files
                base_dir = SHARED_UPLOADS_BASE  # Use the global variable
                # Remove the /shared-uploads/ prefix to get relative path
                relative_path = signature_data.replace('/shared-uploads/', '')
                full_path = os.path.join(base_dir, relative_path)
                
                print(f"🔍 Looking for signature at: {full_path}")
                
                # Check also alternative paths
                alt_paths = [
                    full_path,
                    full_path.replace('\\application\\', '\\application_uploads\\'),
                    full_path.replace('\\application_uploads\\', '\\application\\'),
                    full_path.replace('application_uploads', 'application'),
                    full_path.replace('application', 'application_uploads'),
                ]
                
                for path in alt_paths:
                    print(f"🔍 Checking alternative path: {path}")
                    if os.path.exists(path):
                        print(f"✅ Found signature at: {path}")
                        img = Image(path, width=width, height=height)
                        img.drawWidth = width
                        img.drawHeight = height
                        return img
                
                print(f"❌ Signature file not found in any path")
                return None
            
            # Case 2: Base64 string
            elif 'base64,' in signature_data or ('data:image' in signature_data[:50] if len(signature_data) > 50 else False):
                print("🔍 Processing base64 signature...")
                if 'base64,' in signature_data:
                    signature_data = signature_data.split('base64,')[1]
                elif 'data:image' in signature_data:
                    signature_data = signature_data.split(',', 1)[1]
                
                image_bytes = base64.b64decode(signature_data)
                img = Image(io.BytesIO(image_bytes), width=width, height=height)
                img.drawWidth = width
                img.drawHeight = height
                print(f"✅ Signature loaded from base64")
                return img
            
            # Case 3: HTTP/HTTPS URL
            elif signature_data.startswith(('http://', 'https://')):
                print(f"🔍 Loading signature from URL: {signature_data}")
                resp = requests.get(signature_data, timeout=10)
                if resp.status_code == 200:
                    img = Image(io.BytesIO(resp.content), width=width, height=height)
                    img.drawWidth = width
                    img.drawHeight = height
                    print(f"✅ Signature loaded from URL")
                    return img
            else:
                # Case 4: Direct file path (without /shared-uploads/)
                print(f"🔍 Trying direct file path: {signature_data}")
                if os.path.exists(signature_data):
                    img = Image(signature_data, width=width, height=height)
                    img.drawWidth = width
                    img.drawHeight = height
                    print(f"✅ Signature loaded from direct path")
                    return img
        
        return None
    except Exception as e:
        print(f"❌ Signature error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ===============================
# USER DOWNLOAD CONTRACT PDF (XAMPP/MYSQL VERSION - CORRECTED)
# ===============================
@app.route("/user/download-contract/<contract_number>")
def user_download_contract(contract_number):
    """Generate and download contract PDF - with Addendum and Installment on second page (FULL VERSION)"""
    try:
        # ========== 1. CHECK AUTHENTICATION - WITH TAB ID SUPPORT ==========
        # 👇 KUNIN ANG TAB ID MULA SA URL
        tab_id = request.args.get("tab_id")
        
        user_id = None
        
        # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
        if tab_id:
            user_session = session.get(f"user_{tab_id}")
            if user_session:
                user_id = user_session.get("user_id")
        
        # 👇 FALLBACK: CHECK REGULAR SESSION
        if not user_id and 'user_id' in session:
            user_id = session.get('user_id')
        
        # 👇 KUNG WALANG USER_ID, UNAUTHORIZED
        if not user_id:
            print(f"❌ Unauthorized: No user_id found in session")
            return "Unauthorized - Please login again", 401
        
        print(f"✅ Authorized: user_id: {user_id}, contract: {contract_number}, tab_id: {tab_id}")
        
        # ========== 2. VERIFY CONTRACT BELONGS TO USER ==========
        verify_query = """
            SELECT contract_number, application_number, email, first_name, last_name 
            FROM users 
            WHERE user_id = %s AND contract_number = %s
            LIMIT 1
        """
        user_data = execute_query(verify_query, (user_id, contract_number), fetch_one=True)
        
        if not user_data:
            return f"Unauthorized: Contract {contract_number} does not belong to user {user_id}", 403
        
        # ========== 3. GET APPLICATION NUMBER ==========
        app_id = user_data.get('application_number')
        user_email = user_data.get('email')
        
        if not app_id:
            # Try to find application by email
            app_query = """
                SELECT application_number FROM applications 
                WHERE email = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            app_result = execute_query(app_query, (user_email,), fetch_one=True)
            if app_result:
                app_id = app_result.get('application_number')
        
        if not app_id:
            return "Application ID not found", 404
        
        print(f"DEBUG: Found application_id: {app_id}")
        
        # ========== 4. FETCH APPLICATION DATA FROM MYSQL ==========
        app_query = "SELECT * FROM applications WHERE application_number = %s LIMIT 1"
        application_data = execute_query(app_query, (app_id,), fetch_one=True)
        
        if not application_data:
            return "Application not found", 404
        
        # ========== 5. FETCH CONTRACT DATA FROM MYSQL ==========
        contract_query = """
            SELECT contract_number, billing_date, first_installment_date, last_installment_date,
                   status, full_name, address, barangay, city, province,
                   installation_fee, is_installment_plan, created_at
            FROM contracts 
            WHERE contract_number = %s
            LIMIT 1
        """
        contract_data = execute_query(contract_query, (contract_number,), fetch_one=True)
        
        # ========== 6. GET SIGNATURE FROM APPLICATION ==========
        signature_data = application_data.get('signature')
        
        # Debug: Print the signature data to see what's stored
        print(f"📸 SIGNATURE DATA from DB: {signature_data}")
        
        # ========== 7. BUILD CONTRACT DATA (with fallbacks) ==========
        plan_name = application_data.get('plan', '')
        plan_speed = application_data.get('plan_speed', '')
        
        if not contract_data:
            first_name = application_data.get('first_name', '')
            middle_name = application_data.get('middle_name', '')
            last_name = application_data.get('last_name', '')
            full_name = ' '.join(filter(None, [first_name, middle_name, last_name])).strip()
            
            contract_data = {
                'full_name': full_name,
                'age': calculate_age(application_data.get('birthdate', '')),
                'civil_status': application_data.get('civil_status', ''),
                'address': f"{application_data.get('barangay', '')}, {application_data.get('city', '')}, {application_data.get('province', '')}".strip(', '),
                'billing_date': application_data.get('billing_date', '15th'),
                'date_submitted': application_data.get('date_submitted', ''),
                'installation_fee': application_data.get('installation_fee', ''),
                'first_installment_date': application_data.get('first_installment_date', ''),
                'last_installment_date': application_data.get('last_installment_date', '')
            }
        
        # ========== 8. EXTRACT VALUES ==========
        full_name = contract_data.get('full_name', '')
        if not full_name:
            full_name = "Customer Name Not Available"
        
        age = contract_data.get('age', '') or calculate_age(application_data.get('birthdate', ''))
        civil_status = contract_data.get('civil_status', '') or application_data.get('civil_status', '')
        address = contract_data.get('address', '') or f"{application_data.get('barangay', '')}, {application_data.get('city', '')}, {application_data.get('province', '')}".strip(', ')
        billing_date = contract_data.get('billing_date', '15th') or application_data.get('billing_date', '15th')
        date_submitted = contract_data.get('date_submitted', '') or application_data.get('date_submitted', '')
        installation_fee = contract_data.get('installation_fee', '') or application_data.get('installation_fee', '')
        first_installment = contract_data.get('first_installment_date', '') or application_data.get('first_installment_date', '')
        last_installment = contract_data.get('last_installment_date', '') or application_data.get('last_installment_date', '')
        
        # Check if installment plan
        is_installment = False
        if installation_fee:
            fee_lower = installation_fee.lower()
            if 'installment' in fee_lower:
                is_installment = True
        
        # Format dates
        def format_month_year(date_str):
            if not date_str:
                return '_____________'
            try:
                parts = date_str.split('-')
                if len(parts) == 2:
                    year, month = parts
                else:
                    year, month = parts[0], parts[1]
                month_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
                return f"{month_names[int(month) - 1]} {year}"
            except:
                return '_____________'
        
        first_installment_formatted = format_month_year(first_installment)
        last_installment_formatted = format_month_year(last_installment)
        approval_date = datetime.now().strftime('%B %d, %Y')
        
        # ========== 9. PDF SETUP ==========
        from reportlab.lib.pagesizes import LEGAL
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import io, base64, requests, os
        from flask import current_app, send_file
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=LEGAL,
                                rightMargin=36, leftMargin=36,
                                topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []
        
        # ========== 10. STYLES ==========
        header_style = ParagraphStyle(
            'HeaderStyle', parent=styles['Normal'], fontSize=11, alignment=1,
            spaceAfter=2, fontName='Times-Bold'
        )
        heading_style = ParagraphStyle(
            'HeadingStyle', parent=styles['Normal'], fontSize=11, alignment=1,
            spaceBefore=8, spaceAfter=6, fontName='Times-Bold'
        )
        contract_style = ParagraphStyle(
            'ContractStyle', parent=styles['Normal'], fontSize=8.5, leading=10,
            alignment=4, spaceAfter=2
        )
        addendum_style = ParagraphStyle(
            'AddendumStyle', parent=styles['Normal'], fontSize=9, leading=12,
            alignment=4, spaceAfter=4
        )
        signature_name_style = ParagraphStyle(
            'SignatureNameStyle', parent=styles['Normal'], fontSize=9, alignment=1,
            fontName='Helvetica', textDecoration='underline'
        )
        signature_label_style = ParagraphStyle(
            'SignatureLabelStyle', parent=styles['Normal'], fontSize=7, alignment=1,
            fontName='Helvetica', textColor=colors.grey
        )
        
        # Use the external get_signature_image function (not the internal one)
        signature_img = get_signature_image(signature_data, 180, 50)
        
        # ========== 11. PAGE 1: HEADER AND MAIN CONTRACT ==========
        left_logo_path = os.path.join(current_app.root_path, 'static', 'logo.png')
        right_logo_path = os.path.join(current_app.root_path, 'static', 'logo_right.png')
        
        left_logo_exists = os.path.exists(left_logo_path)
        right_logo_exists = os.path.exists(right_logo_path)
        
        left_logo = None
        right_logo = None
        
        if left_logo_exists:
            left_logo = Image(left_logo_path, width=60, height=60)
        if right_logo_exists:
            right_logo = Image(right_logo_path, width=60, height=60)
        
        title_1 = Paragraph("CABLE TELEVISION/CABLE ONLY/OR", header_style)
        title_2 = Paragraph("CABLE &amp; INTERNET SERVICE CONTRACT", header_style)
        title_3 = Paragraph(f"NO. <u>{contract_number}</u>", header_style)
        
        center_text = Table(
            [[title_1], [title_2], [Spacer(1, 2)], [title_3]],
            colWidths=[360]
        )
        center_text.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]))
        
        if left_logo_exists and right_logo_exists:
            header_table = Table([[left_logo, center_text, right_logo]], colWidths=[70, 360, 70])
        elif left_logo_exists and not right_logo_exists:
            header_table = Table([[left_logo, center_text, '']], colWidths=[70, 360, 70])
        elif not left_logo_exists and right_logo_exists:
            header_table = Table([['', center_text, right_logo]], colWidths=[70, 360, 70])
        else:
            header_table = Table([[center_text]], colWidths=[500])
        
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 12))
        story.append(Paragraph("CONTRACT TERMS AND CONDITIONS", heading_style))
        story.append(Spacer(1, 3))
        
        # Opening statement
        story.append(Paragraph(
            f"I, <strong>{full_name}</strong>, legal age, <strong>{age}</strong> years old, {civil_status} "
            f"and residing at <strong>{address}</strong> hereby apply and subscribed for the service of "
            f"CABLE &amp; INTERNET and agree to the following terms and conditions:",
            contract_style
        ))
        story.append(Spacer(1, 4))
        
        # Payment section
        payment_text = (
            f"<strong>Payment:</strong> The subscriber shall pay a Non-Refundable connection fee of P 1800 and "
            f"cable in excess of 100 meters at P10.00 per meter. For CABLE/INTERNET BUNDLE subscriber, a one (1) "
            f"month subscription fee of P800 shall be paid upon installation and activation of the service. "
            f"Succeeding monthly subscription fee is due and payable every <strong>{billing_date}</strong> of each month. "
            f"Failure to pay the monthly subscription fee on due date and after the grace period of 7 days will mean "
            f"automatic disconnection of cable/internet service. "
            f"The company shall have the right to discontinue/terminate/cancel and effect disconnection of Cable TV services "
            f"in case of default or non-payment of accounts for two (2) succeeding payments."
        )
        story.append(Paragraph(payment_text, contract_style))
        story.append(Spacer(1, 2))
        
        # Deposit section
        story.append(Paragraph(
            "<strong>Deposit:</strong> Subscriber, who leases his/her house or does not own the house where service "
            "will be installed, shall pay a DEPOSIT upon installation. A deposit equivalent to one (1) month subscription fee "
            "for CABLE/INTERNET BUNDLE subscriber while two (2) months subscription fee for CABLE SUBSCRIBER ONLY. "
            "The said deposit cannot be applied to the monthly fee and shall only be refunded upon termination of the contract "
            "and upon pull out of all equipment installed in the premises of the subscriber. Should the subscriber wishes to apply "
            "for reconnection, a reconnection fee of P500.00 shall be paid plus the Deposit and the one (1) month advance "
            "subscription fee for CABLE/INTERNET BUNDLE subscriber. For CABLE SUBSCRIBER ONLY, a reconnection fee of P300.00 "
            "plus the DEPOSIT shall be paid.",
            contract_style
        ))
        story.append(Spacer(1, 2))
        
        # Access to the Premises
        story.append(Paragraph(
            "<strong>Access to the Premises:</strong> The subscriber authorizes our employees, contractors and "
            "representatives to enter your premise in order to install, maintain, inspect, repair, remove and replace "
            "Equipment at a time mutually agreeable upon by both parties.",
            contract_style
        ))
        story.append(Spacer(1, 2))
        
        # Subscriber Usage
        story.append(Paragraph(
            "<strong>Subscriber Usage:</strong> The subscriber shall not in any way use his subscription for commercial purposes. "
            "Transmission of any Internet content which violates national or international law is prohibited. This includes but "
            "not limited to copyrighted materials, those legally adjudged to be threat to national security, or intruding into the "
            "privacy of individuals, offensive on moral, religious, racial or political grounds; abusive, indecent, obscene or "
            "menacing nature of material or information, infringement of intellectual property rights of any person as well as trade secrets.",
            contract_style
        ))
        story.append(Spacer(1, 2))
        
        # Relocating Equipment
        story.append(Paragraph(
            "<strong>Relocating Equipment:</strong> The subscriber is not allowed to relocate equipment installed in their premises. "
            "However, equipment may be relocated by the company's authorized representatives upon the request of the subscriber at a time "
            "mutually agreeable to both parties. Applicable fees and charges may apply.",
            contract_style
        ))
        story.append(Spacer(1, 2))
        
        # Cable Modem and Setup Box
        story.append(Paragraph(
            "<strong>Cable Modem and Setup Box:</strong> The subscriber will be given FREE USE of a Cable Modem and Set Top Box. "
            "This equipment will remain the property of CABLEVISION SYSTEMS CORP. For any Cable TV Extension the subscriber will have to pay "
            "for the cost of the SET TOP BOX amounting to 1400 and a HUB amounting to 420. There will be no additional cost on the monthly "
            "subscription. All equipment has one (1) year warranty against factory defects. If the defect was due to improper use and mishandling "
            "by the user during the warranty period, the cost of replacement will be chargeable to the account of the subscriber. If cable modem "
            "or Set Top Box becomes defective after the warranty period, cost of the new equipment is chargeable to the subscriber.",
            contract_style
        ))
        story.append(Spacer(1, 2))
        
        # Termination/Suspension
        story.append(Paragraph(
            "<strong>Termination/Suspension of Service:</strong> The company reserves the right to suspend or terminate this contract without "
            "prior notice and pull out equipment provided at the subscriber's premises due to non-payment of all applicable fees and charges within "
            "the period and shall not be held liable for any damage; or loss which the Subscriber may incur by reason of suspension and/or termination "
            "of services based on this agreement.",
            contract_style
        ))
        story.append(Spacer(1, 2))
        
        # Disclaimer
        disclaimer_text = (
            "<strong>Disclaimer:</strong> Cablevision Systems Corp./MyCv Broadband shall not be held liable for any damages or delay in business transaction "
            "or communication of the subscriber or whatsoever, the subscriber may suffer or may have suffered due to the use of myCv Broadband Services. "
            "This includes but not limited to any loss of profits, incidental or consequential damages arising out of the Costumer's use of or inability to use; "
            "any loss of information howsoever caused whether as a result of any interruption, suspension, or termination of the Service or otherwise, or for the "
            "contents, accuracy or quality of information available, received or transmitted through the Service; or for failure of the Subscriber to comply with "
            "applicable laws, rules and regulations and all the terms prescribed by the Philippine National Telecommunications Commission for the use of any "
            "telecommunication systems, service or equipment. myCv Broadband shall not be liable for any delay or failure in the performance of service under "
            "this agreement resulting from acts beyond its control, including without limitation, acts of God, acts or regulations of any government or national authority, "
            "war or national emergency, accident, fire, electric power failure, temporary loss of signal not attributed to myCv Broadband, lightning, strikes, lock-outs, "
            "industrial disputes whether or not involving myCv Broadband employees."
        )
        story.append(Paragraph(disclaimer_text, contract_style))
        story.append(Spacer(1, 2))
        
        # Right to modify
        story.append(Paragraph(
            "myCv Broadband reserves the right to adjust, modify, amend or supplements these terms and condition as the service may require. "
            "myCv Broadband will advise SUBSCRIBER of any change by sending him notice setting out these changes.",
            contract_style
        ))
        story.append(Spacer(1, 2))
        
        # Governing Law
        story.append(Paragraph(
            "<strong>Governing Law and Jurisdiction:</strong> The Laws of the Republic of the Philippines governs this Agreement and the Subscriber and myCv Broadband "
            "hereby submit to the exclusive jurisdiction of the courts of Sta. Cruz, Laguna, Philippines.",
            contract_style
        ))
        story.append(Spacer(1, 6))
        
        # Acknowledgment
        story.append(Paragraph(
            "I hereby acknowledge that I have read and understood all the terms and conditions herein and that I voluntarily sign this agreement with full knowledge "
            "and consent of everything this Agreement contains, implies and entails.",
            contract_style
        ))
        story.append(Spacer(1, 10))
        
        # Top Signature Section
        if signature_img:
            top_left_data = [
                [signature_img],
                [Spacer(1, 3)],
                [Paragraph(f"<u>{full_name}</u>", signature_name_style)],
                [Spacer(1, 2)],
                [Paragraph("Subscriber's Signature Over Printed Name", signature_label_style)]
            ]
        else:
            top_left_data = [
                [Paragraph("_________________________", signature_label_style)],
                [Spacer(1, 3)],
                [Paragraph(f"<u>{full_name}</u>", signature_name_style)],
                [Spacer(1, 2)],
                [Paragraph("Subscriber's Signature Over Printed Name", signature_label_style)]
            ]
        
        top_right_data = [
            [Spacer(1, 50)],
            [Paragraph(f"<u>{date_submitted}</u>", signature_name_style)],
            [Spacer(1, 2)],
            [Paragraph("Date", signature_label_style)]
        ]
        
        top_left_table = Table(top_left_data, colWidths=[220])
        top_left_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        
        top_right_table = Table(top_right_data, colWidths=[220])
        top_right_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        
        top_signature_table = Table([[top_left_table, top_right_table]], colWidths=[220, 220])
        story.append(top_signature_table)
        
        # ========== PAGE BREAK ==========
        story.append(PageBreak())
        
        # ========== PAGE 2: ADDENDUM AND INSTALLMENT ==========
        story.append(Spacer(1, 30))
        story.append(Paragraph("<strong>CABLEVISION SYSTEMS CORPORATION</strong>", heading_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<strong>ADDENDUM TO CONTRACT NUMBER {contract_number}</strong>", heading_style))
        story.append(Spacer(1, 15))
        
        addendum_text = (
            f"That I, <strong>{full_name}</strong> holder of CONTRACT Number <strong>{contract_number}</strong> dated <strong>{approval_date}</strong> "
            f"wishes to avail of your INTERNET SERVICE under <strong>{plan_name} ({plan_speed})</strong>. To take effect on <strong>_________________________</strong>."
        )
        story.append(Paragraph(addendum_text, addendum_style))
        story.append(Spacer(1, 8))
        
        story.append(Paragraph(
            "This is also to acknowledge that I have to pay in advance the monthly dues corresponding to the plan that I choose and it is understood that the "
            "TERMS AND CONDITIONS on the original contract remain.",
            addendum_style
        ))
        story.append(Spacer(1, 25))
        
        # ========== INSTALLMENT SECTION ==========
        story.append(Paragraph("<strong>AGREEMENT TO PAY ON INSTALLMENT</strong>", heading_style))
        story.append(Paragraph("<strong>FOR THE INSTALLATION FEE AND/OR SET TOP BOX FOR TV EXTENSION</strong>", heading_style))
        story.append(Spacer(1, 15))
        
        if is_installment:
            display_full_name = full_name
            display_contract_number = contract_number
            display_first_date = first_installment_formatted
            display_last_date = last_installment_formatted
        else:
            display_full_name = '_____________'
            display_contract_number = '_____________'
            display_first_date = '_____________'
            display_last_date = '_____________'
        
        installment_text = (
            f"That I, <strong>{display_full_name}</strong> holder of contract no. <strong>{display_contract_number}</strong> wishes to avail of the INSTALLMENT PLAN "
            f"for the INSTALLATION FEE starting <strong>{display_first_date}</strong> up to <strong>{display_last_date}</strong> "
            f"and the SET TOP BOX for our <strong>_________</strong> TV Extension/s for five (5) months."
        )
        
        story.append(Paragraph(installment_text, addendum_style))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph(
            "<strong>NOTE:</strong> In the event that the account is disconnected during the said period, the remaining installment shall be paid in full.",
            addendum_style
        ))
        story.append(Spacer(1, 40))
        
        # Bottom Signature Section
        if signature_img:
            bottom_signature_data = [
                [signature_img],
                [Spacer(1, 5)],
                [Paragraph(f"<u>{full_name}</u>", signature_name_style)],
                [Paragraph("Signature over printed name", signature_label_style)]
            ]
        else:
            bottom_signature_data = [
                [Paragraph("_________________________", signature_label_style)],
                [Spacer(1, 5)],
                [Paragraph(f"<u>{full_name}</u>", signature_name_style)],
                [Paragraph("Signature over printed name", signature_label_style)]
            ]
        
        bottom_signature_table = Table(bottom_signature_data, colWidths=[250])
        bottom_signature_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        
        right_aligned_table = Table([[bottom_signature_table]], colWidths=[500])
        right_aligned_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'RIGHT')]))
        
        story.append(right_aligned_table)
        
        # ========== BUILD PDF ==========
        doc.build(story)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Service_Contract_{contract_number}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error generating contract PDF: {e}")
        import traceback
        traceback.print_exc()
        return f"Error generating PDF: {str(e)}", 500


def calculate_age(birthdate):
    if not birthdate:
        return ''
    try:
        from datetime import datetime
        birth = datetime.strptime(birthdate, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth.year
        if (today.month, today.day) < (birth.month, birth.day):
            age -= 1
        return str(age)
    except:
        return ''
     


# ===============================
# SYNC SESSION (XAMPP/MYSQL VERSION) - WITH TAB ID
# ===============================
@app.route("/user/sync-session", methods=['POST'])
def sync_user_session():
    """Sync session from frontend sessionStorage to Flask session"""
    try:
        data = request.get_json()
        username = data.get('username')
        tab_id = data.get('tab_id')  # 👈 KUNIN ANG TAB ID
        
        print(f"DEBUG: Syncing session - username: {username}, tab_id: {tab_id}")
        
        # Do not trust client-provided userType. Always fetch role from DB.
        if username and tab_id:
            # ========== FIND USER IN MYSQL ==========
            user_query = """
                SELECT user_id, customer_id, application_number, email, username,
                       role, contract_number, first_name, last_name
                FROM users 
                WHERE user_id = %s OR email = %s OR username = %s
                LIMIT 1
            """
            user_data = execute_query(user_query, (username, username, username), fetch_one=True)
            
            if user_data:
                # 👇 STORE SESSION WITH TAB ID AS KEY (role derived server-side)
                server_role = (user_data.get('role') or 'customer').lower()
                server_usertype = 'admin' if server_role in ('admin', 'administrator') else 'user'
                session[f"user_{tab_id}"] = {
                    "user_id": user_data.get('user_id'),
                    "customer_id": user_data.get('customer_id'),
                    "application_number": user_data.get('application_number'),
                    "role": user_data.get('role', 'customer'),
                    "email": user_data.get('email'),
                    "userType": server_usertype,
                    "contract_number": user_data.get('contract_number'),
                    "username": user_data.get('username')
                }
                session["active_tab"] = tab_id
                
                print(f"DEBUG: Session synced for {username} (user_id: {user_data.get('user_id')})")
                return jsonify({
                    'success': True,
                    'message': 'Session synced successfully',
                    'user_id': user_data.get('user_id'),
                    'email': user_data.get('email'),
                    'tab_id': tab_id
                })
            else:
                print(f"DEBUG: User not found for identifier: {username}")
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid session data'
            }), 400
            
    except Exception as e:
        print(f"ERROR syncing session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===============================
# CHECK SESSION (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/user/check-session")
def check_user_session():
    """Check if user session exists (for debugging)"""
    if 'user_id' in session:
        # Optionally verify that the user still exists in the database
        user_id = session.get('user_id')
        verify_query = "SELECT user_id FROM users WHERE user_id = %s LIMIT 1"
        user_exists = execute_query(verify_query, (user_id,), fetch_one=True)
        
        if not user_exists:
            # Session exists but user no longer in database - clear session
            session.clear()
            return jsonify({
                'logged_in': False,
                'message': 'Session invalid - user not found',
                'session_keys': list(session.keys())
            })
        
        return jsonify({
            'logged_in': True,
            'user_id': session.get('user_id'),
            'customer_id': session.get('customer_id'),
            'application_number': session.get('application_number'),
            'userType': session.get('userType'),
            'role': session.get('role'),
            'contract_number': session.get('contract_number'),
            'email': session.get('email'),
            'username': session.get('username')
        })
    else:
        return jsonify({
            'logged_in': False,
            'session_keys': list(session.keys())
        })


@app.route("/my-application")
def my_application():
    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    # kunin user
    user_ref = db.reference(f"users/{user_id}")
    user_data = user_ref.get()

    if not user_data:
        return "User not found", 404

    customer_id = user_data.get("customer_id")

    # kunin application gamit application_number
    app_data = db.reference("applications").child(customer_id).get()

    if not app_data:
        return "Application not found", 404

    return render_template("user-my-application.html", **app_data) 


# ===============================
# GET USER PROFILE (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/api/get-user-profile")
def get_user_profile():
    # 👇 KUNIN ANG TAB ID MULA SA REQUEST
    tab_id = request.args.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session.get("user_id")
    
    # ========== GET USER DATA FROM MYSQL ==========
    user_query = """
        SELECT user_id, username, email, first_name, last_name, middle_name, suffix,
               contact_number, address, profile_photo, role, contract_number,
               connection_status, application_number, customer_id
        FROM users 
        WHERE user_id = %s
        LIMIT 1
    """
    user_data = execute_query(user_query, (user_id,), fetch_one=True)

    if not user_data:
        return jsonify({"error": "User not found"}), 404

    # ========== GET PROFILE PHOTO (fallback to application if needed) ==========
    profile_photo = user_data.get("profile_photo")
    
    if not profile_photo or profile_photo == 'none':
        # Try to get from applications table using application_number
        app_number = user_data.get("application_number")
        if app_number:
            app_query = "SELECT profile_photo FROM applications WHERE application_number = %s LIMIT 1"
            app_data = execute_query(app_query, (app_number,), fetch_one=True)
            if app_data and app_data.get('profile_photo'):
                profile_photo = app_data.get('profile_photo')
    
    if not profile_photo or profile_photo == 'none':
        profile_photo = url_for("static", filename="profile.jpg")
    
    # Build full name
    first_name = user_data.get('first_name', '')
    last_name = user_data.get('last_name', '')
    middle_name = user_data.get('middle_name', '')
    suffix = user_data.get('suffix', '')
    
    name_parts = []
    if first_name:
        name_parts.append(first_name)
    if middle_name and middle_name != 'none':
        name_parts.append(middle_name)
    if last_name:
        name_parts.append(last_name)
    if suffix and suffix != 'none':
        name_parts.append(suffix)
    
    display_name = ' '.join(name_parts) if name_parts else user_data.get('username', user_id)

    return jsonify({
        "user_id": user_id,
        "id": user_id,
        "username": user_data.get("username") or display_name,
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name,
        "suffix": suffix,
        "email": user_data.get("email", ""),
        "contact_number": user_data.get("contact_number", ""),
        "address": user_data.get("address", ""),
        "photo_url": profile_photo,
        "profile_photo": profile_photo,
        "role": user_data.get("role", "customer"),
        "contract_number": user_data.get("contract_number", ""),
        "connection_status": user_data.get("connection_status", "Disconnected"),
        "application_number": user_data.get("application_number", ""),
        "customer_id": user_data.get("customer_id", "")
    })


# ===============================
# USER UPDATE PROFILE (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/user/profile/update", methods=["POST"])
def update_profile():
    # 👇 KUNIN ANG TAB ID MULA SA FORM
    tab_id = request.form.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            flash("Invalid session. Please login again.", "warning")
            return redirect(url_for("login"))
    else:
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        user_id = session["user_id"]
    
    # ========== VERIFY USER EXISTS ==========
    check_query = "SELECT user_id FROM users WHERE user_id = %s LIMIT 1"
    user_exists = execute_query(check_query, (user_id,), fetch_one=True)
    
    if not user_exists:
        flash("User not found.", "danger")
        return redirect(url_for("dashboard"))

    # ========== GET POST DATA ==========
    full_name = request.form.get("full_name", "").strip()
    contact = request.form.get("contact_number", "").strip()
    address = request.form.get("address", "").strip()
    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()
    
    # Split full_name into first_name and last_name (if needed)
    first_name = ""
    last_name = ""
    if full_name:
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

    # ========== PASSWORD VALIDATION ==========
    password_error = None

    # Validate password-change flow whenever any password field is touched.
    if current_password or new_password or confirm_password:
        if not current_password:
            password_error = "Please enter your current password before changing your password."
        elif not new_password or not confirm_password:
            password_error = "Please set your new password and confirm it after entering your current password."
        else:
            user_password_data = execute_query("SELECT password FROM users WHERE user_id = %s LIMIT 1", (user_id,), fetch_one=True)
            stored_password = user_password_data.get("password", "") if user_password_data else ""
            password_matches = stored_password == current_password or check_password_hash(stored_password, current_password)

            if not stored_password or not password_matches:
                password_error = "Current password is incorrect."
            elif new_password != confirm_password:
                password_error = "Passwords do not match!"
            elif len(new_password) < 8:
                password_error = "Password must be at least 8 characters long."
            elif new_password.isdigit():
                password_error = "Password cannot be all numbers."
            elif not re.search(r"[A-Za-z]", new_password) or not re.search(r"\d", new_password):
                password_error = "Password must contain both letters and numbers."
    
    if password_error:
        flash(password_error, "danger")
        return redirect(url_for("user_profile"))

    # ========== BUILD UPDATE FIELDS ==========
    update_fields = []
    update_params = []
    
    if first_name:
        update_fields.append("first_name = %s")
        update_params.append(first_name)
    
    if last_name:
        update_fields.append("last_name = %s")
        update_params.append(last_name)
    
    if contact:
        # Validate contact number (should be 11 digits starting with 09)
        contact_clean = re.sub(r'\D', '', contact)
        if len(contact_clean) == 11 and contact_clean.startswith('09'):
            update_fields.append("contact_number = %s")
            update_params.append(contact_clean)
        else:
            flash("Please enter a valid contact number (11 digits starting with 09)", "warning")
    
    if address:
        update_fields.append("address = %s")
        update_params.append(address)
    
    if new_password:
        # Hash the password
        hashed_password = generate_password_hash(new_password)
        update_fields.append("password = %s")
        update_params.append(hashed_password)
    
    # ========== ALSO UPDATE APPLICATIONS TABLE IF NEEDED ==========
    if update_fields:
        # Update users table
        update_params.append(user_id)
        update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s"
        execute_query(update_query, update_params)
        
        # Also try to update applications table (for consistency)
        try:
            app_fields = []
            app_params = []
            if first_name:
                app_fields.append("first_name = %s")
                app_params.append(first_name)
            if last_name:
                app_fields.append("last_name = %s")
                app_params.append(last_name)
            if contact:
                app_fields.append("mobile = %s")
                app_params.append(contact_clean)
            
            if app_fields:
                # Get application_number from user
                app_num_query = "SELECT application_number FROM users WHERE user_id = %s"
                app_num_data = execute_query(app_num_query, (user_id,), fetch_one=True)
                if app_num_data and app_num_data.get('application_number'):
                    app_params.append(app_num_data.get('application_number'))
                    app_update_query = f"UPDATE applications SET {', '.join(app_fields)} WHERE application_number = %s"
                    execute_query(app_update_query, app_params)
                    print(f"✅ Updated applications table for user {user_id}")
        except Exception as app_err:
            print(f"⚠️ Could not update applications table: {app_err}")
        
        flash("Profile updated successfully!", "success")
    else:
        flash("No changes were made to your profile.", "info")

    return redirect(url_for("user_profile"))


# ===============================
# USER UPLOAD PROFILE PHOTO (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/user/profile/upload-photo", methods=["POST"])
def upload_profile_photo():
    """Upload profile photo for the logged in user"""
    # 👇 KUNIN ANG TAB ID MULA SA FORM
    tab_id = request.form.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session["user_id"]
    
    if 'profile_photo' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['profile_photo']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Check file type
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return jsonify({"error": "Invalid file type. Only PNG, JPG, JPEG, GIF allowed"}), 400
    
    try:
        from PIL import Image
        import io
        import os
        
        # Create upload directory if not exists
        upload_dir = os.path.join(current_app.root_path, 'static', 'profile_photos')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # Generate unique filename
        timestamp = int(time.time())
        filename = f"{user_id}_{timestamp}.jpg"
        filepath = os.path.join(upload_dir, filename)
        
        # Process and save image
        img = Image.open(file)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.thumbnail((300, 300), Image.Resampling.LANCZOS)
        img.save(filepath, 'JPEG', quality=85)
        
        # Update database with the file path
        photo_url = url_for('static', filename=f'profile_photos/{filename}')
        update_query = "UPDATE users SET profile_photo = %s WHERE user_id = %s"
        execute_query(update_query, (photo_url, user_id))
        
        return jsonify({
            "success": True,
            "photo_url": photo_url,
            "message": "Profile photo updated successfully"
        })
        
    except Exception as e:
        print(f"Error uploading profile photo: {e}")
        return jsonify({"error": str(e)}), 500


# ===============================
# VERIFY CURRENT PASSWORD (WITHOUT CHANGING)
# ===============================
@app.route("/user/verify-current-password", methods=["POST"])
def verify_current_password():
    data = request.get_json(silent=True) or {}
    tab_id = data.get("tab_id") or request.form.get("tab_id")

    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session["user_id"]

    current_password = (data.get("current_password") or "").strip()
    if not current_password:
        return jsonify({"error": "Current password is required"}), 400

    user_data = execute_query("SELECT password FROM users WHERE user_id = %s LIMIT 1", (user_id,), fetch_one=True)
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    stored_password = user_data.get("password", "")
    password_matches = stored_password == current_password or check_password_hash(stored_password, current_password)

    if not password_matches:
        return jsonify({"error": "Current password is incorrect"}), 401

    return jsonify({"success": True, "message": "Current password verified"})


# ===============================
# USER CHANGE PASSWORD (XAMPP/MYSQL VERSION)
# ===============================
@app.route("/user/change-password", methods=["POST"])
def change_password():
    """Change user password"""
    data = request.get_json()
    
    # 👇 KUNIN ANG TAB ID MULA SA REQUEST
    tab_id = data.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session["user_id"]
    
    data = request.get_json()
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    
    # Get current user data
    user_query = "SELECT password FROM users WHERE user_id = %s LIMIT 1"
    user_data = execute_query(user_query, (user_id,), fetch_one=True)
    
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    stored_password = user_data.get('password', '')
    
    # Verify current password (support both plain-text and hashed legacy records)
    password_matches = stored_password == current_password or check_password_hash(stored_password, current_password)
    if not password_matches:
        return jsonify({"error": "Current password is incorrect"}), 401
    
    # Validate new password
    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400
    
    if new_password.isdigit():
        return jsonify({"error": "Password cannot be all numbers"}), 400
    
    if not re.search(r"[A-Za-z]", new_password) or not re.search(r"\d", new_password):
        return jsonify({"error": "Password must contain both letters and numbers"}), 400
    
    if new_password != confirm_password:
        return jsonify({"error": "New passwords do not match"}), 400
    
    # Update password
    hashed_password = generate_password_hash(new_password)
    update_query = "UPDATE users SET password = %s WHERE user_id = %s"
    execute_query(update_query, (hashed_password, user_id))
    
    return jsonify({
        "success": True,
        "message": "Password changed successfully"
    })



# ===============================
# LOGOUT ROUTE - WITH TAB ID SUPPORT
# ===============================
@app.route("/api/logout", methods=['POST'])
def logout():
    try:
        data = request.get_json()
        tab_id = data.get('tab_id') if data else None
        
        if tab_id:
            # 👇 I-REMOVE ANG SPECIFIC TAB SESSION
            session.pop(f"user_{tab_id}", None)
            print(f"✅ Logout: Removed session for tab_id: {tab_id}")
        else:
            # 👇 FALLBACK: CLEAR ALL SESSION
            session.clear()
            print("✅ Logout: Cleared all session")
        
        return jsonify({"success": True, "message": "Logged out successfully"})
    except Exception as e:
        print(f"❌ Logout error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ================= API LOGOUT ROUTE (for AJAX calls) =================
@app.route("/api/logout", methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'redirect': '/'})


# ===============================
# CHATBOT ROUTES - XAMPP/MYSQL VERSION (COMPLETE)
# ===============================

from groq import Groq
from dotenv import load_dotenv
import os
from flask import request, jsonify
import time

# Load .env
load_dotenv()

# Get API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ================= CACHE SYSTEM =================
response_cache = {}
MAX_CACHE_SIZE = 100

# Store conversation history per session
chat_conversations = {}

# ================= FUNCTIONS TO GET DATA FROM MYSQL =================

def get_dynamic_barangay_data():
    """Get barangay data dynamically from MySQL areas table (service coverage areas)"""
    try:
        conn = get_db_connection()

        if not conn:
            print("❌ Database connection failed")
            return get_fallback_barangays()

        cursor = conn.cursor(dictionary=True)
        
        # Get ALL barangays from areas table (service coverage areas)
        query = """
            SELECT DISTINCT city, barangay, province 
            FROM areas 
            WHERE barangay IS NOT NULL AND barangay != ''
            ORDER BY city, barangay
        """
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        barangays_by_city = {}
        for row in results:
            city = row.get("city", "").strip()
            barangay = row.get("barangay", "").strip()
            province = row.get("province", "").strip()
            
            if city and barangay:
                city = to_proper_case(city)
                barangay = to_proper_case(barangay)
                province = to_proper_case(province)
                
                if city not in barangays_by_city:
                    barangays_by_city[city] = {
                        'province': province or 'Laguna',
                        'barangays': []
                    }
                if barangay not in barangays_by_city[city]['barangays']:
                    barangays_by_city[city]['barangays'].append(barangay)
        
        for city in barangays_by_city:
            barangays_by_city[city]['barangays'].sort()
        
        total_barangays = sum(len(v['barangays']) for v in barangays_by_city.values())
        print(f"✅ Loaded {total_barangays} barangays from areas table across {len(barangays_by_city)} cities")
        
        return barangays_by_city
        
    except Exception as e:
        print(f"❌ Error getting barangays from areas table: {e}")
        import traceback
        traceback.print_exc()
        return get_fallback_barangays()

def get_fallback_barangays():
    """Fallback barangay data (based on areas table data)"""
    return {
        "Santa Cruz": {
            'province': 'Laguna',
            'barangays': ["Bagumbayan", "Bubukal", "Calios", "Duhat", "Gatid", "Labuin", "Oogong", "Pagsawitan", "Patimbao", "Barangay I", "Barangay II", "Barangay III", "Barangay IV", "Barangay V", "San Jose", "San Juan", "San Pablo Norte", "San Pablo Sur", "Santisima Cruz", "Santo Angel Central", "Santo Angel Norte", "Santo Angel Sur"]
        },
        "Pagsanjan": {
            'province': 'Laguna',
            'barangays': ["Barangay Uno", "Barangay Dos", "Biñan", "Buboy", "Cabanbanan", "Layugan", "Magdapio", "Maulawin", "Pinagsanjan", "Sabang", "Sampaloc", "San Isidro"]
        },
        "Magdalena": {
            'province': 'Laguna',
            'barangays': ["Malaking Ambling", "Munting Ambling", "Bucal", "Buenavista", "Cigaras", "Ibabang Atingay", "Ibabang Butnong", "Ilayang Atingay", "Ilayang Butnong", "Poblacion", "Sabang", "Salasad", "Tipunan"]
        },
        "Pila": {
            'province': 'Laguna',
            'barangays': ["Aplaya", "Bagong Pook", "Bulilan Norte", "Bulilan Sur", "Concepcion", "Labuin", "Linga", "Mojon", "Pansol", "Pinagbayanan", "San Antonio", "San Miguel", "Santa Clara Norte", "Santa Clara Sur", "Tubuan"]
        }
    }

_cached_barangays = None
_cached_timestamp = 0
BARANGAY_CACHE_DURATION = 300

def get_cached_barangays():
    global _cached_barangays, _cached_timestamp
    now = time.time()
    if _cached_barangays is None or (now - _cached_timestamp) > BARANGAY_CACHE_DURATION:
        _cached_barangays = get_dynamic_barangay_data()
        _cached_timestamp = now
    return _cached_barangays

def to_proper_case(text):
    """Convert text to Proper Case"""
    if not text:
        return text
    words = text.split()
    proper_words = []
    for word in words:
        if word.isupper() and len(word) > 2:
            proper_words.append(word.capitalize())
        else:
            proper_words.append(word[0].upper() + word[1:].lower() if word else word)
    return ' '.join(proper_words)

# ================= LOCAL RESPONSES (COMPLETE) =================

local_responses = {
    # Plans
    'magkano ang plan premium': """Good day, Ka-CV! Plan Premium costs 1,600 pesos per month with 500 Mbps speed. It is best for gaming and 4K streaming. Would you like to know more, Ka-CV?""",
    'magkano ang plan basic': """Good day, Ka-CV! Plan Basic costs 800 pesos per month with 98 Mbps speed. It is best for family browsing and streaming. Would you like to know more, Ka-CV?""",
    'magkano ang plan standard': """Good day, Ka-CV! Plan Standard costs 1,260 pesos per month with 300 Mbps speed. It is best for heavy streaming and work from home. Would you like to know more, Ka-CV?""",
    'magkano ang plan ultimate': """Good day, Ka-CV! Plan Ultimate costs 2,100 pesos per month with 800 Mbps speed. It is best for businesses and heavy internet users. Would you like to know more, Ka-CV?""",
    'magkano ang plan budget friendly': """Good day, Ka-CV! Plan Budget Friendly costs 550 pesos per month with 50 Mbps speed. It is best for light internet usage. Would you like to know more, Ka-CV?""",
    'list of plans': """Good day, Ka-CV! Here are our available internet plans:

• Plan Budget Friendly - ₱550/month (50 Mbps)
• Plan Basic - ₱800/month (98 Mbps)
• Plan Standard - ₱1,260/month (300 Mbps)
• Plan Premium - ₱1,600/month (500 Mbps)
• Plan Ultimate - ₱2,100/month (800 Mbps)

Which plan interests you, Ka-CV?""",
    'plans': """Good day, Ka-CV! Here are our available internet plans:

• Plan Budget Friendly - ₱550/month (50 Mbps)
• Plan Basic - ₱800/month (98 Mbps)
• Plan Standard - ₱1,260/month (300 Mbps)
• Plan Premium - ₱1,600/month (500 Mbps)
• Plan Ultimate - ₱2,100/month (800 Mbps)

Would you like more details about any specific plan, Ka-CV?""",
    'what are your plans': """Good day, Ka-CV! Here are our available internet plans:

• Plan Budget Friendly: ₱550/month (50 Mbps)
• Plan Basic: ₱800/month (98 Mbps)
• Plan Standard: ₱1,260/month (300 Mbps)
• Plan Premium: ₱1,600/month (500 Mbps)
• Plan Ultimate: ₱2,100/month (800 Mbps)

Which plan interests you, Ka-CV?""",

    # Hours
   'office hours': """Good day, Ka-CV! Office hours are Monday to Saturday, 8:00 AM to 5:00 PM. Closed on Sundays and holidays. You can contact us anytime for technical support. How may I help you, Ka-CV?""",

    # Requirements
    'requirements': """Good day, Ka-CV! To apply for our services, please prepare:
• 1 Valid ID
• 1 Proof of Billing

Would you like to know how to apply, Ka-CV?""",

    # Installation Fee
    'installation fee': """Good day, Ka-CV! Installation fee is 1,800 pesos.
Installment options:
• 2 months: 900 pesos/month
• 3 months: 600 pesos/month
• 4 months: 450 pesos/month
• 5 months: 360 pesos/month
• 6 months: 300 pesos/month

Would you like to proceed with application, Ka-CV?""",

    # How to Apply
    'how to apply': """Good day, Ka-CV! To apply:
Step 1: Go to Plans Page
Step 2: Select your preferred plan
Step 3: Click Apply
Step 4: Fill out and submit the application form

Would you like to know the requirements, Ka-CV?""",
    'paano mag apply': """Good day, Ka-CV! To apply:
Step 1: Go to Plans Page
Step 2: Select your plan
Step 3: Click Apply
Step 4: Fill out and submit the form

Would you like to know the requirements, Ka-CV?""",
    'application process': """Good day, Ka-CV! Application process:
Step 1: Go to Plans Page
Step 2: Select your plan
Step 3: Click Apply
Step 4: Fill out and submit the form

Would you like to know the requirements, Ka-CV?""",

    # Contact numbers
    'contact numbers': """Good day, Ka-CV! Our contact numbers:
Main Office (Santa Cruz):
• Billing: 09175010341 / (049) 501-1495

Extension Offices:
• Pila Poblacion: +639176293796 / (049) 559-0701
• Pila Labuin: +639173107948 / (049) 559-5082
• Santa Cruz Extension: (049) 501-0922
• Magdalena Extension: (049) 503-6819

How may I help you further, Ka-CV?""",

    # Coverage
    'coverage': """Good day, Ka-CV! We serve:
• Santa Cruz
• Pagsanjan
• Magdalena
• Pila

Would you like to know the barangays in your area, Ka-CV?""",

    # Barangay Lists
    'barangay list': """Good day, Ka-CV! Here is the complete list of barangays per municipality:

Santa Cruz, Laguna (22 barangays):
• Bagumbayan
• Bubukal
• Calios
• Duhat
• Gatid
• Labuin
• Oogong
• Pagsawitan
• Patimbao
• Barangay I
• Barangay II
• Barangay III
• Barangay IV
• Barangay V
• San Jose
• San Juan
• San Pablo Norte
• San Pablo Sur
• Santisima Cruz
• Santo Angel Central
• Santo Angel Norte
• Santo Angel Sur

Pagsanjan, Laguna (12 barangays):
• Barangay Uno
• Barangay Dos
• Biñan
• Buboy
• Cabanbanan
• Layugan
• Magdapio
• Maulawin
• Pinagsanjan
• Sabang
• Sampaloc
• San Isidro

Magdalena, Laguna (13 barangays):
• Malaking Ambling
• Munting Ambling
• Bucal
• Buenavista
• Cigaras
• Ibabang Atingay
• Ibabang Butnong
• Ilayang Atingay
• Ilayang Butnong
• Poblacion
• Sabang
• Salasad
• Tipunan

Pila, Laguna (15 barangays):
• Aplaya
• Bagong Pook
• Bulilan Norte
• Bulilan Sur
• Concepcion
• Labuin
• Linga
• Mojon
• Pansol
• Pinagbayanan
• San Antonio
• San Miguel
• Santa Clara Norte
• Santa Clara Sur
• Tubuan

Is your barangay listed above, Ka-CV?""",

    'barangay santa cruz': """Good day, Ka-CV! Barangays in Santa Cruz:
• Bagumbayan
• Bubukal
• Calios
• Duhat
• Gatid
• Labuin
• Oogong
• Pagsawitan
• Patimbao
• Barangay I
• Barangay II
• Barangay III
• Barangay IV
• Barangay V
• San Jose
• San Juan
• San Pablo Norte
• San Pablo Sur
• Santisima Cruz
• Santo Angel Central
• Santo Angel Norte
• Santo Angel Sur

Is your barangay in Santa Cruz, Ka-CV?""",

    'barangay pagsanjan': """Good day, Ka-CV! Barangays in Pagsanjan:
• Barangay Uno
• Barangay Dos
• Biñan
• Buboy
• Cabanbanan
• Layugan
• Magdapio
• Maulawin
• Pinagsanjan
• Sabang
• Sampaloc
• San Isidro

Is your barangay in Pagsanjan, Ka-CV?""",

    'barangay magdalena': """Good day, Ka-CV! Barangays in Magdalena:
• Malaking Ambling
• Munting Ambling
• Bucal
• Buenavista
• Cigaras
• Ibabang Atingay
• Ibabang Butnong
• Ilayang Atingay
• Ilayang Butnong
• Poblacion
• Sabang
• Salasad
• Tipunan

Is your barangay in Magdalena, Ka-CV?""",

    'barangay pila': """Good day, Ka-CV! Barangays in Pila:
• Aplaya
• Bagong Pook
• Bulilan Norte
• Bulilan Sur
• Concepcion
• Labuin
• Linga
• Mojon
• Pansol
• Pinagbayanan
• San Antonio
• San Miguel
• Santa Clara Norte
• Santa Clara Sur
• Tubuan

Is your barangay in Pila, Ka-CV?""",

    # Thank you
    'thank you': "You're welcome, Ka-CV! We are happy to help. Have a great day!",
    'salamat': "You're welcome, Ka-CV! We are happy to help. Have a great day!",

    # Greetings
    'hello': "Good day, Ka-CV! Welcome to CableVision Customer Support. How may I assist you today?",
    'hi': "Good day, Ka-CV! Welcome to CableVision Customer Support. How may I help you today? You can ask about plans, coverage, requirements, installation, or how to apply.",
    'good morning': "Good morning, Ka-CV! Welcome to CableVision Customer Support. How may I assist you today?",
    'good afternoon': "Good afternoon, Ka-CV! Welcome to CableVision Customer Support. How may I assist you today?",
    'good evening': "Good evening, Ka-CV! Welcome to CableVision Customer Support. How may I assist you today?",
}

def get_local_response(message):
    message_lower = message.lower().strip()
    
    # Plan checks
    if 'premium' in message_lower and ('magkano' in message_lower or 'how much' in message_lower):
        return local_responses['magkano ang plan premium']
    if 'basic' in message_lower and ('magkano' in message_lower or 'how much' in message_lower):
        return local_responses['magkano ang plan basic']
    if 'standard' in message_lower and ('magkano' in message_lower or 'how much' in message_lower):
        return local_responses['magkano ang plan standard']
    if 'ultimate' in message_lower and ('magkano' in message_lower or 'how much' in message_lower):
        return local_responses['magkano ang plan ultimate']
    if 'budget' in message_lower and ('magkano' in message_lower or 'how much' in message_lower):
        return local_responses['magkano ang plan budget friendly']
    
    # Barangay checks
    if 'barangay' in message_lower or 'barangays' in message_lower:
        if 'santa cruz' in message_lower:
            return local_responses['barangay santa cruz']
        if 'pagsanjan' in message_lower:
            return local_responses['barangay pagsanjan']
        if 'magdalena' in message_lower:
            return local_responses['barangay magdalena']
        if 'pila' in message_lower:
            return local_responses['barangay pila']
        if 'list' in message_lower or 'lahat' in message_lower:
            return local_responses['barangay list']
    
    # Municipalities
    if 'municipalities' in message_lower or 'bayan' in message_lower:
        return """Good day, Ka-CV! We serve:
• Santa Cruz
• Pagsanjan
• Magdalena
• Pila

Would you like the list of barangays in any of these municipalities, Ka-CV?"""
    
    # Other checks
    for key, response in local_responses.items():
        if key in message_lower:
            return response
    
    return None


def fetch_current_plans():
    try:
        plans = execute_query(
            "SELECT id, name, speed, price FROM plans ORDER BY price ASC",
            fetch=True
        )

        return plans or []

    except Exception as e:
        print(f"Fetch current plans error: {e}")
        return []


def parse_speed_to_mbps(speed_text):
    if not speed_text:
        return 0
    text = speed_text.lower().strip().replace(' ', '')
    import re

    # Standardize separators like /s or per second
    text = text.replace('/s', '')
    text = text.replace('ps', '')

    # Extract numeric value
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        return 0

    value = float(match.group(1))
    if 'gbps' in text or text.endswith('gb') or 'gbit' in text:
        return int(value * 1000)
    if 'mbps' in text or text.endswith('mb') or 'mbit' in text:
        return int(value)

    # Fallback: treat plain numbers as Mbps
    return int(value)


def get_highest_speed_plan(plans):
    best_plan = None
    best_speed = -1
    for plan in plans:
        speed_value = parse_speed_to_mbps(plan.get('speed', ''))
        if speed_value > best_speed:
            best_speed = speed_value
            best_plan = plan
    return best_plan


def get_dynamic_plan_response(message):
    message_lower = message.lower().strip()
    plan_query_phrases = [
        'available internet plans',
        'available plans',
        'internet plans',
        'plans and pricing',
        'plan pricing',
        'show plans',
        'see plans',
        'what are your plans',
        'what are your available plans',
        'latest plans',
        'latest plan',
        'new plans',
        'new plan',
        'latest package',
        'new package',
        'ano ang mga plano',
        'mga plano',
        'mga plan',
        'ano ang mga plan',
        'internet plan',
        'plans today',
        'plan details',
        'plano',
        'pinaka malakas',
        'fastest plan',
        'strongest plan',
        'highest speed',
        'pinakamabilis',
        'pinaka mabilis',
        'pinaka malakas na plan'
    ]

    if not any(phrase in message_lower for phrase in plan_query_phrases):
        return None

    plans = fetch_current_plans()
    if not plans:
        return "Good day, Ka-CV! Our plan list is currently being updated. Please check the Plans page shortly."

    # Exact plan detail requests
    price_request_words = ['magkano', 'how much', 'price', 'presyo', 'details', 'ano ang']
    for plan in plans:
        plan_name = plan.get('name', '').lower()
        if plan_name and plan_name in message_lower:
            if any(word in message_lower for word in price_request_words) or 'details' in message_lower or 'ano ang' in message_lower:
                price = plan.get('price', 0) or 0
                price_str = f"₱{int(price):,}" if isinstance(price, (int, float)) else f"₱{price}"
                speed = plan.get('speed', 'N/A')
                return (
                    f"Good day, Ka-CV! Here are the details for {plan.get('name', 'this plan')}:\n\n"
                    f"• Monthly Fee: {price_str}\n"
                    f"• Speed: {speed}\n"
                    f"• Plan Name: {plan.get('name', '')}\n\n"
                    "For more details or to apply, please visit /plans, Ka-CV."
                )

    if 'pinaka' in message_lower or 'fastest' in message_lower or 'highest speed' in message_lower or 'strongest plan' in message_lower or 'pinaka malakas' in message_lower or 'pinaka mabilis' in message_lower:
        best_plan = get_highest_speed_plan(plans)
        if best_plan:
            price = best_plan.get('price', 0) or 0
            price_str = f"₱{int(price):,}" if isinstance(price, (int, float)) else f"₱{price}"
            speed = best_plan.get('speed', 'N/A')
            return (
                f"Good day, Ka-CV! The fastest available plan is {best_plan.get('name', 'this plan')}:\n\n"
                f"• Speed: {speed}\n"
                f"• Monthly Fee: {price_str}\n\n"
                "This is the highest speed plan, Ka-CV."
            )

    # Generic plan list response
    if any(phrase in message_lower for phrase in plan_query_phrases):
        response = "Good day, Ka-CV! Here are our current internet plans:\n\n"
        for plan in plans:
            name = plan.get('name', 'Unknown Plan')
            speed = plan.get('speed', 'N/A')
            price = plan.get('price', 0) or 0
            price_str = f"₱{int(price):,}" if isinstance(price, (int, float)) else f"₱{price}"
            response += f"• {name}: {price_str} / month ({speed})\n"

        response += "\nFor more details or to apply, please visit /plans, Ka-CV."
        return response

    return None

def to_proper_case(text):
    """Convert text to Proper Case"""
    if not text:
        return text
    # Handle special cases for Poblacion
    text = text.replace('(POB.)', '(Poblacion)')
    text = text.replace('(POBLACION)', '(Poblacion)')
    
    words = text.split()
    proper_words = []
    for word in words:
        if word.isupper() and len(word) > 2:
            proper_words.append(word.capitalize())
        else:
            proper_words.append(word[0].upper() + word[1:].lower() if word else word)
    return ' '.join(proper_words)

def get_dynamic_barangay_response(message):
    message_lower = message.lower().strip()
    barangays_by_city = get_cached_barangays()
    municipalities = list(barangays_by_city.keys())
    municipalities.sort()
    
    # Handle "list of municipalities" or "mga bayan"
    if message_lower in ['municipalities', 'bayan', 'list of municipalities', 'mga bayan', 'what are your service areas', 'service areas']:
        if not municipalities:
            return "Good day, Ka-CV! We are currently setting up our service areas. Please check back later, Ka-CV!"
        
        response = "Good day, Ka-CV! Here are the municipalities we serve:\n\n"
        for city in municipalities:
            count = len(barangays_by_city[city]['barangays'])
            response += f"• {city} ({count} barangay{'s' if count != 1 else ''})\n"
        response += "\nWould you like the complete list of barangays in any municipality, Ka-CV?"
        return response
    
    # Handle specific city barangay list
    for city in municipalities:
        if city.lower() in message_lower and ('barangay' in message_lower or 'barangays' in message_lower or 'list' in message_lower):
            barangays = barangays_by_city[city]['barangays']
            if not barangays:
                continue
            
            response = f"Good day, Ka-CV! Here are the barangays in {city}, Laguna:\n\n"
            for b in barangays:
                response += f"• {b}\n"
            response += f"\nIs your barangay in {city}, Ka-CV? You can apply if your barangay is listed above."
            return response
    
    # Handle complete barangay list for all cities
    if message_lower in ['barangay list', 'lahat ng barangay', 'complete barangay list', 'all barangays']:
        if not municipalities:
            return "Good day, Ka-CV! No coverage areas available at the moment. Please check back later, Ka-CV!"
        
        response = "Good day, Ka-CV! Here is the complete list of barangays per municipality:\n\n"
        for city in municipalities:
            barangays = barangays_by_city[city]['barangays']
            response += f"\n📌 {city}, Laguna ({len(barangays)} barangay{'s' if len(barangays) != 1 else ''}):\n"
            # Show all barangays (not just first 10)
            for b in barangays:
                response += f"• {b}\n"
        response += "\nIs your barangay listed above, Ka-CV? You can apply if your barangay is in the list!"
        return response
    
    return None


# ================= CHAT ROUTE =================

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default')
    
    if not user_message:
        return jsonify({'response': "Please enter a question, Ka-CV.", 'success': False})

    # 🔥 I-HARDCODE ANG TECH SUPPORT HOURS 🔥
    message_lower = user_message.lower()
    
    tech_support_keywords = [
        'tech support hours',
        'technical support hours',
        'tech support schedule',
        'technical support schedule',
        'tech support time',
        'technical support time',
        'kailan pwedeng tumawag sa tech support',
        'tech support availability',
        'technical support availability',
        'tech support office hours',
        'technical support office hours',
        'tech support contact hours',
        '24/7 tech support',
        'tech support 24',
        'technical support 24',
        'tech support anytime',
        'technical support anytime',
        'support hours',
        'support schedule',
        'support time',
        'tech support operating hours',
        'tech support days',
        'technical support days',
        'what time is tech support',
        'what time is technical support',
        'tech support open',
        'technical support open',
        'kailan bukas ang tech support',
        'tech support contact time',
        'technical support contact time',
        'tech support business hours',
        'technical support business hours'
    ]
    
    if any(keyword in message_lower for keyword in tech_support_keywords):
        return jsonify({
            'response': "You can contact us anytime for technical support, Ka-CV.",
            'success': True
        })

    # Cache check for identical queries
    cache_key = user_message.lower()
    if cache_key in response_cache:
        return jsonify({'response': response_cache[cache_key], 'success': True})
    
    # Dynamic database knowledge context
    plans = fetch_current_plans()
    plans_text = ""
    if plans:
        for p in plans:
            price = p.get('price', 0) or 0
            price_str = f"₱{int(price):,}" if isinstance(price, (int, float)) else f"₱{price}"
            plans_text += f"• {p.get('name', 'Plan')}: {price_str} / month ({p.get('speed', 'N/A')})\n"
    else:
        plans_text = "• Plan Budget Friendly: ₱550/month (50 Mbps)\n• Plan Basic: ₱800/month (98 Mbps)\n• Plan Standard: ₱1,260/month (300 Mbps)\n• Plan Premium: ₱1,600/month (500 Mbps)\n• Plan Ultimate: ₱2,100/month (800 Mbps)\n"

    barangays_by_city = get_cached_barangays()
    coverage_text = ""
    if barangays_by_city:
        for city, info in barangays_by_city.items():
            b_list = ", ".join(info.get('barangays', []))
            coverage_text += f"• {city}, Laguna: {b_list}\n"
    else:
        coverage_text = "• Santa Cruz, Pagsanjan, Magdalena, Pila (Laguna)\n"

    system_prompt = f"""You are Ka-CV Assistant, the official virtual AI support assistant for Cablevision (Cable Television & Fiber Internet Service Provider).

STRICT LANGUAGE REQUIREMENT:
- ALWAYS RESPOND IN ENGLISH ONLY.
- User questions may be written in Tagalog, Taglish, English, or Spanish. Regardless of the question's language, your answer MUST be written 100% in clear English.
- Address the user as "Ka-CV".

RELEVANCE RULES & SCOPE:
- ALLOWED TOPICS: Internet plans, pricing, speeds, coverage areas, online application process, requirements, installation fees, office hours, contact numbers, billing/payments, account concerns, and technical support (e.g. LOS light).
- If the question is about Cablevision (even if written in Tagalog or Taglish), you MUST answer the question in English with accurate information based on the database data below.

STRICT REFUSAL RULE FOR UNRELATED TOPICS:
- If and ONLY if the question is COMPLETELY UNRELATED to Cablevision (such as food recipes, sports, coding/programming, weather, trivia), respond with EXACTLY this refusal sentence and NOTHING ELSE:
  "I am Cablevision's AI Support Assistant. I can only assist with questions related to Cablevision services, plans, coverage, billing, and support. How can I help you with your Cablevision service today, Ka-CV?"
- DO NOT write "However, I can provide..." when refusing an unrelated topic.
- DO NOT list plans, coverage, or any extra text after refusing.

PROHIBITED RESPONSES:
- DO NOT write "Please note that our coverage areas are subject to change" or any disclaimer.
- DO NOT write "However, I can provide..." when refusing an unrelated question.
- DO NOT tell users to visit an office in person to apply.

HOW TO APPLY (ONLINE ONLY):
When asked how to apply or for application steps, provide these step-by-step instructions in English:
• Step 1: Go to the Plans page (/plans) on our website
• Step 2: Select your preferred plan
• Step 3: Click "Apply"
• Step 4: Fill out the online application form, upload your valid ID & proof of billing, and submit

CLEAN RESPONSE FORMATTING & LAYOUT:
- Structure your output cleanly and neatly so it is pleasant and easy to read.
- Use bold section titles ending with a colon (e.g. **Main Office:**, **Extension Offices:**, **Available Plans:**).
- Place every list item on a separate new line starting with a bullet point (`• `).
- Avoid huge walls of unformatted text. Keep paragraphs brief, organized, and clean.

OFFICIAL CONTACT NUMBERS RULE:
When asked for contact numbers, contact details, or office numbers, list ALL available contact numbers for the Main Office and all Extension Offices (Santa Cruz Extension, Pila Poblacion, Pila Labuin, Magdalena Extension) using clear bullet points.

CABLEVISION DATABASE & SYSTEM DATA:
[AVAILABLE PLANS]
{plans_text}

[INSTALLATION FEE]
• Installation Fee: ₱1,800 total (Installment: 2-6 months)

[APPLICATION REQUIREMENTS]
• 1 Valid Government-Issued ID
• 1 Proof of Billing Address

[OFFICE HOURS]
• Main Office: Monday to Saturday, 8:00 AM - 5:00 PM (Closed Sundays & Holidays)
• Tech Support: You can contact us anytime.

[OFFICIAL CONTACT NUMBERS & OFFICES]
Main Office:
• Main Office (Santa Cruz / Billing): 0917-501-0341 / (049) 501-1495

Extension Offices:
• Santa Cruz Extension: (049) 501-0922
• Pila Poblacion Extension: +639176293796 / (049) 559-0701
• Pila Labuin Extension: +639173107948 / (049) 559-5082
• Magdalena Extension: (049) 503-6819

[SERVICE COVERAGE AREAS]
{coverage_text}
"""

    if groq_client:
        try:
            if session_id not in chat_conversations:
                chat_conversations[session_id] = []
            
            messages = [{"role": "system", "content": system_prompt}]
            for msg in chat_conversations[session_id][-6:]:
                messages.append(msg)
            messages.append({"role": "user", "content": user_message})
            
            # 🔥 ITO ANG BAGONG CODE GAMIT ANG GPT-OSS-120B 🔥
            stream = groq_client.chat.completions.create(
                messages=messages,
                model="openai/gpt-oss-120b",  # <-- Pinalitan na
                temperature=0.2,               # Mas mababa para sa consistent na sagot
                max_completion_tokens=2048,    # Mas mataas para sa mahahabang sagot
                top_p=1,
                reasoning_effort="medium",     # <-- Bagong parameter para sa OSS models
                stream=True,
                stop=None
            )
            
            # I-process ang streaming response
            full_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            
            response = full_response.strip()
            
            response_cache[cache_key] = response
            if len(response_cache) > MAX_CACHE_SIZE:
                oldest_key = next(iter(response_cache))
                del response_cache[oldest_key]
            
            chat_conversations[session_id].append({"role": "user", "content": user_message})
            chat_conversations[session_id].append({"role": "assistant", "content": response})
            if len(chat_conversations[session_id]) > 14:
                chat_conversations[session_id] = chat_conversations[session_id][-14:]
            
            return jsonify({'response': response, 'success': True})
            
        except Exception as e:
            print(f"Groq API error: {e}")
            import traceback
            traceback.print_exc()
    
    # Fallback response in English if Groq client fails or is offline
    fallback = (
        "Good day, Ka-CV! We are currently experiencing a brief technical connection issue with our AI service. "
        "Please call us directly at 0917-501-0341 or (049) 501-1495 for immediate assistance, Ka-CV."
    )
    return jsonify({'response': fallback, 'success': False})


# ===============================
# NAP BOX SLOTS FOR USER APPLICATION (PUBLIC READ-ONLY)
# ===============================
@app.route("/api/user/napbox-slots", methods=["GET"])
def get_user_napbox_slots():
    """Get all NAP boxes and slots for user application"""
    try:
        connection = get_db_connection()

        if not connection:
            return jsonify({
                'success': False,
                'error': 'Database connection failed',
                'napboxes': [],
                'slots': []
            }), 500

        cursor = connection.cursor(dictionary=True)
        
        # Get all napboxes
        napboxes_query = """
            SELECT 
                id, 
                napbox_name as name, 
                location, 
                latitude, 
                longitude, 
                area, 
                barangay, 
                coverage_radius 
            FROM napboxes 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY area, napbox_name
        """
        cursor.execute(napboxes_query)
        napboxes = cursor.fetchall() or []
        
        # Get all slots
        slots_query = """
            SELECT 
                ns.id, 
                ns.napbox_id, 
                ns.slot_number, 
                ns.status, 
                ns.customer_name, 
                ns.customer_phone, 
                ns.barangay, 
                ns.updated_at,
                n.napbox_name as napbox_name, 
                n.area
            FROM napbox_slots ns
            LEFT JOIN napboxes n ON ns.napbox_id = n.id
            ORDER BY n.area, n.napbox_name, CAST(ns.slot_number AS UNSIGNED)
        """
        cursor.execute(slots_query)
        slots = cursor.fetchall() or []
        
        cursor.close()
        connection.close()
        
        # Format napboxes for response
        napboxes_list = []
        for nb in napboxes:
            lat = nb.get('latitude')
            lng = nb.get('longitude')
            
            if lat is not None:
                try:
                    lat = float(lat)
                except (ValueError, TypeError):
                    lat = None
            if lng is not None:
                try:
                    lng = float(lng)
                except (ValueError, TypeError):
                    lng = None
            
            if lat and lng:
                napboxes_list.append({
                    "id": nb.get('id'),
                    "name": nb.get('name'),
                    "location": nb.get('location') or nb.get('name'),
                    "latitude": lat,
                    "longitude": lng,
                    "area": nb.get('area'),
                    "barangay": nb.get('barangay'),
                    "coverage_radius": nb.get('coverage_radius') or 500
                })
        
        # Format slots for response
        slots_list = []
        for slot in slots:
            slots_list.append({
                "id": slot.get('id'),
                "napbox_id": slot.get('napbox_id'),
                "slot_number": slot.get('slot_number'),
                "status": slot.get('status'),
                "customer_name": slot.get('customer_name'),
                "customer_phone": slot.get('customer_phone'),
                "barangay": slot.get('barangay'),
                "updated_at": str(slot.get('updated_at')) if slot.get('updated_at') else None,
                "napbox_name": slot.get('napbox_name'),
                "area": slot.get('area')
            })
        
        return jsonify({
            'success': True,
            'napboxes': napboxes_list,
            'slots': slots_list
        })
        
    except Exception as e:
        print(f"Error in get_user_napbox_slots: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'napboxes': [], 'slots': []}), 500



# ===============================
# USER PLAN CHANGE PAGE - GET CURRENT PLAN & AVAILABLE PLANS
# ===============================
@app.route("/user/change-plan")
def user_change_plan():
    if "user_id" not in session:
        return redirect("/")
    return render_template("user-change-plan.html")


# ===============================
# GET USER'S CURRENT PLAN (for display)
# ===============================
@app.route("/api/user/current-plan", methods=["GET"])
def get_user_current_plan():
    """Get user's current plan from customers table"""
    # 👇 KUNIN ANG TAB ID MULA SA REQUEST
    tab_id = request.args.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER SESSION
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        # Fallback sa regular session
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session["user_id"]
    
    try:
        query = """
            SELECT c.plan, c.plan_speed, c.plan_price, c.contract_number, 
                   c.billing_date, c.application_number
            FROM users u
            JOIN customers c ON u.application_number = c.application_number
            WHERE u.user_id = %s
        """
        result = execute_query(query, (user_id,), fetch_one=True)
        
        if not result:
            return jsonify({"error": "No active plan found"}), 404
        
        # Check if there's a pending request
        pending_query = """
            SELECT id, request_id, requested_plan, requested_speed, requested_price, status, requested_at
            FROM plan_change_requests
            WHERE application_number = %s AND status = 'Pending'
            ORDER BY requested_at DESC LIMIT 1
        """
        pending = execute_query(pending_query, (result.get("application_number"),), fetch_one=True)
        
        response = {
            "plan": result.get("plan"),
            "speed": result.get("plan_speed"),
            "price": result.get("plan_price"),
            "contract_number": result.get("contract_number"),
            "billing_date": result.get("billing_date"),
            "application_number": result.get("application_number")
        }
        
        if pending:
            response["pending_request"] = {
                "id": pending.get("id"),
                "request_id": pending.get("request_id"),
                "plan": pending.get("requested_plan"),
                "speed": pending.get("requested_speed"),
                "price": pending.get("requested_price"),
                "status": pending.get("status"),
                "requested_at": pending.get("requested_at")
            }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in get_user_current_plan: {e}")
        return jsonify({"error": str(e)}), 500


# ===============================
# GET AVAILABLE PLANS (for upgrade/downgrade)
# ===============================
@app.route("/api/user/available-plans", methods=["GET"])
def get_available_plans():
    """Get all available plans from plans table"""
    # 👇 KUNIN ANG TAB ID PARA I-VERIFY ANG SESSION
    tab_id = request.args.get("tab_id")
    
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if not user_session:
            return jsonify({"error": "Invalid session"}), 401
    else:
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT id, name, speed, price 
            FROM plans 
            ORDER BY CAST(speed AS UNSIGNED) ASC
        """
        cursor.execute(query)
        plans = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert Decimal to float para ma-JSON
        for plan in plans:
            if plan.get('price'):
                plan['price'] = float(plan['price'])
        
        print(f"📊 Found {len(plans)} plans")
        return jsonify(plans)
        
    except Exception as e:
        print(f"Error in get_available_plans: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ===============================
# USER SUBMIT PLAN CHANGE REQUEST (WITH REQUEST ID)
# ===============================
@app.route("/api/user/submit-plan-change", methods=["POST"])
def submit_plan_change():
    """User submits a plan upgrade/downgrade request"""
    data = request.get_json()
    
    # 👇 KUNIN ANG TAB ID MULA SA REQUEST
    tab_id = data.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER SESSION
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        # Fallback sa regular session
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session["user_id"]
    
    new_plan_name = data.get("plan_name")
    new_plan_speed = data.get("plan_speed")
    new_plan_price = data.get("plan_price")
    
    if not all([new_plan_name, new_plan_speed, new_plan_price]):
        return jsonify({"error": "Missing plan details"}), 400
    
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user's application number and current plan
        user_query = """
            SELECT u.application_number, u.first_name, u.last_name, u.email,
                   c.plan as current_plan, c.plan_speed as current_speed, 
                   c.plan_price as current_price, c.city, c.contract_number, c.billing_date
            FROM users u
            JOIN customers c ON u.application_number = c.application_number
            WHERE u.user_id = %s
        """
        cursor.execute(user_query, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        application_number = user.get("application_number")
        current_plan = user.get("current_plan")
        current_speed = user.get("current_speed")
        current_price = user.get("current_price")
        
        # Check if trying to change to the same plan
        if current_plan == new_plan_name:
            return jsonify({"error": "You are already on this plan"}), 400
        
        # Check if there's already a pending request
        pending_check = """
            SELECT id FROM plan_change_requests 
            WHERE application_number = %s AND status = 'Pending'
        """
        cursor.execute(pending_check, (application_number,))
        pending_request = cursor.fetchone()
        
        if pending_request:
            return jsonify({
                "error": "You already have a pending plan change request. Please wait for admin approval."
            }), 400
        
        # ========== GENERATE REQUEST ID ==========
        import random
        import string
        from datetime import datetime
        
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.digits, k=5))
        generated_request_id = f"PCR-{date_part}-{random_part}"
        
        # ========== SAVE PLAN CHANGE REQUEST WITH REQUEST ID ==========
        insert_request = """
            INSERT INTO plan_change_requests (
                request_id, application_number, 
                current_plan, current_speed, current_price,
                requested_plan, requested_speed, requested_price, 
                status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_request, (
            generated_request_id,
            application_number,
            current_plan,
            current_speed,
            current_price,
            new_plan_name,
            new_plan_speed,
            new_plan_price,
            'Pending'
        ))
        conn.commit()
        
        applicant_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        application_city = user.get('city', 'Unknown')
        
        # ========== CREATE NOTIFICATION FOR SUPERADMIN (with request_id) ==========
        notification_id = int(datetime.now().timestamp() * 1000)
        notif_query = """
            INSERT INTO notifications (id, title, message, type, relatedId, timestamp, read_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(notif_query, (
            notification_id,
            "Plan Change Request",
            f"[{generated_request_id}] {applicant_name} requested to change plan from {current_plan or 'N/A'} to {new_plan_name} ({new_plan_speed}) - Application #{application_number}",
            "plan_change_request",
            application_number,
            datetime.now().isoformat(),
            0
        ))
        conn.commit()
        print(f"🔔 Superadmin notification created for plan change request {generated_request_id}")
        
        # ========== CREATE NOTIFICATION FOR ADMIN (BY CITY) ==========
        admin_notif_id = notification_id + 1
        admin_notif_query = """
            INSERT INTO admin_notifications (
                id, title, message, type, relatedId, timestamp, read_status,
                admin_city, application_city, application_id, requested_by, requested_status,
                contract_number, billing_date, request_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(admin_notif_query, (
            admin_notif_id,
            "Plan Change Request in Your Area",
            f"[{generated_request_id}] {applicant_name} requested to change plan from {current_plan or 'N/A'} to {new_plan_name} ({new_plan_speed})",
            "plan_change_request",
            application_number,
            datetime.now().isoformat(),
            0,  # read_status
            application_city,  # admin_city
            application_city,  # application_city
            application_number,  # application_id
            None,  # requested_by
            "Pending",  # requested_status
            user.get('contract_number'),  # contract_number
            user.get('billing_date'),  # billing_date
            generated_request_id  # request_id
        ))
        conn.commit()
        print(f"🔔 Admin notification created for plan change request {generated_request_id} in {application_city}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Your plan change request has been submitted. Request ID: {generated_request_id}",
            "request_id": generated_request_id,
            "requested_plan": {
                "name": new_plan_name,
                "speed": new_plan_speed,
                "price": new_plan_price
            }
        })
        
    except Exception as e:
        print(f"Error in submit_plan_change: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ===============================
# CHECK IF USER HAS PENDING REQUEST
# ===============================
@app.route("/api/user/pending-request", methods=["GET"])
def check_pending_request():
    """Check if user has a pending plan change request"""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    user_id = session["user_id"]
    
    try:
        query = """
            SELECT u.application_number
            FROM users u
            WHERE u.user_id = %s
        """
        user = execute_query(query, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({"has_pending": False})
        
        pending_query = """
            SELECT id, request_id, requested_plan, requested_speed, requested_price, requested_at
            FROM plan_change_requests
            WHERE application_number = %s AND status = 'Pending'
            ORDER BY requested_at DESC LIMIT 1
        """
        pending = execute_query(pending_query, (user.get("application_number"),), fetch_one=True)
        
        if pending:
            return jsonify({
                "has_pending": True,
                "request": {
                    "id": pending.get("id"),
                    "request_id": pending.get("request_id"),
                    "plan": pending.get("requested_plan"),
                    "speed": pending.get("requested_speed"),
                    "price": pending.get("requested_price"),
                    "requested_at": pending.get("requested_at")
                }
            })
        
        return jsonify({"has_pending": False})
        
    except Exception as e:
        print(f"Error in check_pending_request: {e}")
        return jsonify({"has_pending": False}), 200


# ===============================
# USER TERMINATION PAGE
# ===============================
@app.route("/user/request-termination")
def user_request_termination():
    # 👇 KUNIN ANG TAB ID MULA SA URL
    tab_id = request.args.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, I-VERIFY ANG SESSION
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if not user_session:
            return redirect("/")
    else:
        # Fallback sa regular session
        if "user_id" not in session:
            return redirect("/")
    
    return render_template("user-request-termination.html")


# ===============================
# GET USER'S CURRENT PLAN FOR TERMINATION
# ===============================
@app.route("/api/user/termination-info", methods=["GET"])
def get_user_termination_info():
    """Get user's current plan info for termination request"""
    # 👇 KUNIN ANG TAB ID MULA SA REQUEST
    tab_id = request.args.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session["user_id"]
    
    try:
        query = """
            SELECT u.user_id, u.first_name, u.last_name, u.email, u.contact_number,
                   c.plan, c.plan_speed, c.plan_price, c.contract_number, 
                   c.application_number, c.city, c.billing_date
            FROM users u
            JOIN customers c ON u.application_number = c.application_number
            WHERE u.user_id = %s
        """
        result = execute_query(query, (user_id,), fetch_one=True)
        
        if not result:
            return jsonify({"error": "No active plan found"}), 404
        
        # Check if there's already a pending termination request
        pending_query = """
            SELECT id, request_id, status, created_at
            FROM termination_requests
            WHERE application_number = %s AND status = 'Pending'
            ORDER BY created_at DESC LIMIT 1
        """
        pending = execute_query(pending_query, (result.get("application_number"),), fetch_one=True)
        
        response = {
            "user_id": result.get("user_id"),
            "first_name": result.get("first_name"),
            "last_name": result.get("last_name"),
            "email": result.get("email"),
            "contact_number": result.get("contact_number"),
            "plan": result.get("plan"),
            "speed": result.get("plan_speed"),
            "price": result.get("plan_price"),
            "contract_number": result.get("contract_number"),
            "application_number": result.get("application_number"),
            "city": result.get("city"),
            "billing_date": result.get("billing_date")
        }
        
        if pending:
            response["pending_request"] = {
                "id": pending.get("id"),
                "request_id": pending.get("request_id"),
                "status": pending.get("status"),
                "created_at": pending.get("created_at")
            }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in get_user_termination_info: {e}")
        return jsonify({"error": str(e)}), 500
    

    # ===============================
# GET TERMINATION INFO FOR USER
# ===============================
@app.route("/api/user/termination-info", methods=["GET"])
def get_termination_info():
    """Get user's current plan and check for pending termination request"""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    user_id = session["user_id"]
    username = request.args.get('username') or session.get('username')
    
    try:
        # Get user's current plan from customers table
        customer_query = """
            SELECT plan, plan_speed, plan_price, contract_number
            FROM customers 
            WHERE user_id = %s AND status = 'Approved'
            ORDER BY created_at DESC
            LIMIT 1
        """
        customer = execute_query(customer_query, (user_id,), fetch_one=True)
        
        # If no customer record, try applications table
        if not customer:
            app_query = """
                SELECT plan, plan_speed, plan_price, contract_number
                FROM applications 
                WHERE user_id = %s AND status = 'Approved'
                ORDER BY created_at DESC
                LIMIT 1
            """
            customer = execute_query(app_query, (user_id,), fetch_one=True)
        
        # Check for pending termination request
        pending_query = """
            SELECT request_id, created_at, status
            FROM termination_requests 
            WHERE user_id = %s AND status = 'Pending'
            ORDER BY created_at DESC
            LIMIT 1
        """
        pending = execute_query(pending_query, (user_id,), fetch_one=True)
        
        result = {
            "plan": customer.get('plan') if customer else None,
            "speed": customer.get('plan_speed') if customer else None,
            "price": customer.get('plan_price') if customer else None,
            "contract_number": customer.get('contract_number') if customer else None,
            "pending_termination": pending if pending else None
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in get_termination_info: {e}")
        return jsonify({"error": str(e)}), 500

# ===============================
# GET PENDING TERMINATION REQUEST
# ===============================
@app.route("/api/user/pending-termination", methods=["GET"])
def get_pending_termination():
    """Check if user has a pending termination request"""
    # 👇 KUNIN ANG TAB ID MULA SA REQUEST
    tab_id = request.args.get("tab_id")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session["user_id"]
    
    try:
        pending_query = """
            SELECT request_id, created_at, status, termination_reason
            FROM termination_requests 
            WHERE user_id = %s AND status = 'Pending'
            ORDER BY created_at DESC
            LIMIT 1
        """
        pending = execute_query(pending_query, (user_id,), fetch_one=True)
        
        return jsonify({
            "pending_termination": pending if pending else None
        })
        
    except Exception as e:
        print(f"Error checking pending termination: {e}")
        return jsonify({"error": str(e)}), 500

# ===============================
# USER SUBMIT TERMINATION REQUEST
# ===============================
@app.route("/api/user/submit-termination", methods=["POST"])
def submit_termination_request():
    """User submits a termination request"""
    data = request.get_json()
    
    # 👇 KUNIN ANG TAB ID MULA SA REQUEST
    tab_id = data.get("tab_id")
    username = data.get("username")
    
    # 👇 KUNG MAY TAB ID, GAMITIN ITO PARA MAKUHA ANG USER
    if tab_id:
        user_session = session.get(f"user_{tab_id}")
        if user_session:
            user_id = user_session.get("user_id")
        else:
            return jsonify({"error": "Invalid session"}), 401
    else:
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session["user_id"]
    
    termination_reason = data.get("termination_reason", "").strip()
    termination_date = data.get("termination_date")
    
    if not termination_reason:
        return jsonify({"error": "Please provide a reason for termination"}), 400
    
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user's information
        user_query = """
            SELECT u.user_id, u.first_name, u.last_name, u.email, u.contact_number,
                   c.application_number, c.plan, c.plan_speed, c.plan_price, 
                   c.contract_number, c.city, c.billing_date
            FROM users u
            JOIN customers c ON u.application_number = c.application_number
            WHERE u.user_id = %s
        """
        cursor.execute(user_query, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        application_number = user.get("application_number")
        
        # Check if there's already a pending termination request
        pending_check = """
            SELECT id FROM termination_requests 
            WHERE application_number = %s AND status = 'Pending'
        """
        cursor.execute(pending_check, (application_number,))
        pending_request = cursor.fetchone()
        
        if pending_request:
            return jsonify({
                "error": "You already have a pending termination request. Please wait for admin approval."
            }), 400
        
        # Generate Request ID
        import random
        import string
        from datetime import datetime
        
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.digits, k=5))
        generated_request_id = f"TR-{date_part}-{random_part}"
        
        # Save termination request
        insert_request = """
            INSERT INTO termination_requests (
                request_id, application_number, user_id,
                first_name, last_name, email, contact_number,
                city, contract_number,
                current_plan, current_speed, current_price,
                termination_reason, termination_date,
                status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_request, (
            generated_request_id,
            application_number,
            user_id,
            user.get("first_name"),
            user.get("last_name"),
            user.get("email"),
            user.get("contact_number"),
            user.get("city"),
            user.get("contract_number"),
            user.get("plan"),
            user.get("plan_speed"),
            user.get("plan_price"),
            termination_reason,
            termination_date,
            'Pending'
        ))
        conn.commit()
        
        applicant_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        application_city = user.get('city', 'Unknown')
        
        # ========== CREATE NOTIFICATION FOR SUPERADMIN ==========
        notification_id = int(datetime.now().timestamp() * 1000)
        notif_query = """
            INSERT INTO notifications (id, title, message, type, relatedId, timestamp, read_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(notif_query, (
            notification_id,
            "Termination Request",
            f"[{generated_request_id}] {applicant_name} requested to terminate plan: {user.get('plan') or 'N/A'} - Application #{application_number}",
            "termination_request",
            application_number,
            datetime.now().isoformat(),
            0
        ))
        conn.commit()
        print(f"🔔 Superadmin notification created for termination request {generated_request_id}")
        
        # ========== CREATE NOTIFICATION FOR ADMIN (BY CITY) ==========
        admin_notif_id = notification_id + 1
        admin_notif_query = """
            INSERT INTO admin_notifications (
                id, title, message, type, relatedId, timestamp, read_status,
                admin_city, application_city, application_id, requested_by, requested_status,
                contract_number, billing_date, request_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(admin_notif_query, (
            admin_notif_id,
            "Termination Request in Your Area",
            f"[{generated_request_id}] {applicant_name} requested to terminate plan: {user.get('plan') or 'N/A'}",
            "termination_request",
            application_number,
            datetime.now().isoformat(),
            0,  # read_status
            application_city,  # admin_city
            application_city,  # application_city
            application_number,  # application_id
            None,  # requested_by
            "Pending",  # requested_status
            user.get('contract_number'),  # contract_number
            user.get('billing_date'),  # billing_date
            generated_request_id  # request_id
        ))
        conn.commit()
        print(f"🔔 Admin notification created for termination request {generated_request_id} in {application_city}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Your termination request has been submitted. Request ID: {generated_request_id}",
            "request_id": generated_request_id
        })
        
    except Exception as e:
        print(f"Error in submit_termination_request: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ===============================
# RUN APP
# ===============================
if __name__ == "__main__":
    app.run(debug=True, port=5001)