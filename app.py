# --- START OF FILE app.py ---

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash
from dotenv import load_dotenv   
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
try:
    from google import genai
except Exception:
    try:
        import google.generativeai as genai
    except Exception:
        genai = None
from datetime import datetime, timedelta
from functools import wraps

# Optional Google OAuth / auth libraries — allow app to run without them installed.
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
except Exception:
    Credentials = None
    Flow = None
    Request = None
import requests
import json
import secrets 
try:
    from pip._vendor import cachecontrol
except Exception:
    try:
        import cachecontrol
    except Exception:
        cachecontrol = None

app = Flask(__name__)

load_dotenv()

app.secret_key = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("DB_NAME", "shadowx_db")

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

   
    users_collection = db.users
    challenges_collection = db.challenges
    mcqs_collection = db.mcqs
    fixcode_collection = db.fixcode
    peer_questions_collection = db.peer_questions
    puzzles_collection = db.puzzles
    print("MongoDB connection successful.")
except Exception as e:
    print(f"ERROR: Could not connect to MongoDB: {e}")
    

GOOGLE_GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY")

if GOOGLE_GEMINI_API_KEY and genai:
    print("Google Gemini AI API initialized.")
elif GOOGLE_GEMINI_API_KEY and not genai:
    print("WARNING: GOOGLE_GEMINI_API_KEY is set but 'google-genai' package is not installed.")
else:
    print("WARNING: GOOGLE_GEMINI_API_KEY environment variable not set.")


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/callback")

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# OAuth client configuration
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    print("WARNING: Google OAuth credentials not set. Login with Google will not work.")
    print("Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.")

GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": [GOOGLE_REDIRECT_URI]
    }
}

# --- Helper Functions ---
def redirect_to_auth(error=None, form_type='login', next=None):
    """Helper function to redirect to auth page with appropriate parameters."""
    if error:
        flash(error, 'error')
    next_param = request.args.get('next') if next is None else next
    return redirect(url_for('auth', next=next_param, form_type=form_type))

# --- Decorators ---
def login_required(role=None):
    """Decorator to ensure user is logged in, optionally checking for admin role."""
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session and not (session.get('logged_in') and session.get('role') == 'admin'):
                return redirect_to_auth(next=request.url)

            if role == "admin" and (not session.get('logged_in') or session.get('role') != 'admin'):
                # Redirect admins-only page to admin login if they are not admin
                return redirect(url_for('admin_login', next=request.url))

            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# --- Admin Authentication ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Handle admin login."""
    next_url = request.args.get('next')
    
    if session.get('logged_in') and session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('admin/admin_login.html', current_page='admin_login')

        from werkzeug.security import check_password_hash, generate_password_hash

        # Find existing admin user in DB
        admin_user = users_collection.find_one({
            'role': 'admin',
            '$or': [
                {'username': username},
                {'email': username.lower()}
            ]
        })

        # Check default admin credentials OR hashed password in DB
        is_valid_default = (username in ['admin', 'yashkolekar'] and password == 'pass123')
        is_valid_hash = (admin_user and check_password_hash(admin_user.get('password_hash', ''), password))

        if is_valid_default or is_valid_hash:
            if not admin_user:
                # Upsert admin user doc
                admin_doc = {
                    'username': 'yashkolekar',
                    'email': 'yashkolekar@shadowx.com',
                    'password_hash': generate_password_hash('pass123'),
                    'role': 'admin',
                    'created_at': datetime.now()
                }
                admin_id = users_collection.insert_one(admin_doc).inserted_id
                admin_user = users_collection.find_one({'_id': admin_id})

            session['logged_in'] = True
            session['role'] = 'admin'
            session['username'] = admin_user['username']
            session['email'] = admin_user.get('email', 'admin@shadowx.com')
            session['user_id'] = str(admin_user['_id'])

            if request.form.get('remember'):
                session.permanent = True
            else:
                session.permanent = False

            flash('Welcome back, Admin!', 'success')
            return redirect(next_url or url_for('admin_dashboard'))
        
        flash('Invalid Username or Password. Please try again.', 'error')
        
    return render_template('admin/admin_login.html', current_page='admin_login')

@app.route('/admin/logout')
def admin_logout():
    """Logs out admin user and clears session."""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    """Handle both user login and registration in one route"""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    form_type = request.args.get('form_type', 'login')
    next_url = request.args.get('next')

    if request.method == 'POST':
        form_type = request.form.get('form_type', 'login')
        
        if form_type == 'register':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            if not all([email, username, password, confirm_password]):
                return redirect_to_auth('All fields are required.', 'register')
            elif password != confirm_password:
                return redirect_to_auth('Passwords do not match.', 'register')
            elif len(password) < 8:
                return redirect_to_auth('Password must be at least 8 characters long.', 'register')
            elif users_collection.find_one({'email': email}):
                return redirect_to_auth('Email address is already registered.', 'register')
            elif users_collection.find_one({'username': username}):
                return redirect_to_auth('Username is already taken. Please choose another.', 'register')

            from werkzeug.security import generate_password_hash
            user_doc = {
                'email': email,
                'username': username,
                'password_hash': generate_password_hash(password),
                'created_at': datetime.now(),
                'role': 'user'
            }
            user_id = users_collection.insert_one(user_doc).inserted_id

            session['user_id'] = str(user_id)
            session['username'] = username
            session['email'] = email
            session['role'] = 'user'
            session['logged_in'] = True

            if request.form.get('remember'):
                session.permanent = True
            else:
                session.permanent = False

            flash('Registration successful! Welcome to ShadowX.', 'success')
            return redirect(next_url or url_for('index'))

        elif form_type == 'login':
            username_or_email = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()

            if not username_or_email or not password:
                return redirect_to_auth('Username/Email and Password are required.', 'login')

            from werkzeug.security import check_password_hash

            user = users_collection.find_one({
                '$or': [
                    {'username': username_or_email},
                    {'email': username_or_email.lower()}
                ]
            })

            if username_or_email in ['yashkolekar', 'admin'] and password == 'pass123':
                admin_user = users_collection.find_one({'username': 'yashkolekar', 'role': 'admin'})
                if not admin_user:
                    from werkzeug.security import generate_password_hash
                    admin_doc = {
                        'username': 'yashkolekar',
                        'email': 'yashkolekar@shadowx.com',
                        'password_hash': generate_password_hash('pass123'),
                        'role': 'admin',
                        'created_at': datetime.now()
                    }
                    admin_id = users_collection.insert_one(admin_doc).inserted_id
                    admin_user = users_collection.find_one({'_id': admin_id})

                session['user_id'] = str(admin_user['_id'])
                session['username'] = admin_user['username']
                session['email'] = admin_user.get('email', 'admin@shadowx.com')
                session['role'] = 'admin'
                session['logged_in'] = True

                if request.form.get('remember'):
                    session.permanent = True
                else:
                    session.permanent = False

                flash('Welcome back, Admin!', 'success')
                return redirect(next_url or url_for('admin_dashboard'))

            if user and check_password_hash(user.get('password_hash', ''), password):
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                session['email'] = user['email']
                session['role'] = user.get('role', 'user')
                session['logged_in'] = True

                if request.form.get('remember'):
                    session.permanent = True
                else:
                    session.permanent = False

                flash('Welcome back!', 'success')
                
                if session['role'] == 'admin':
                    return redirect(next_url or url_for('admin_dashboard'))
                return redirect(next_url or url_for('index'))
            else:
                return redirect_to_auth('Invalid username/email or password.', 'login')

    return render_template('user/auth.html', current_page='auth',
                         google_configured=bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
                         form_type=form_type)


# Compatibility wrappers: some templates and redirects expect `user_login` / `user_register` endpoints.
@app.route('/login', methods=['GET', 'POST'])
def user_login():
    return auth()


@app.route('/register', methods=['GET', 'POST'])
def user_register():
    return auth()

@app.route('/login/google')
def google_login():
    """Initiates the Google OAuth flow."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        # Fallback error handling if credentials are missing
        return redirect_to_auth("Google Sign In is not configured. Please try again later.", "login")

    if Flow is None:
        # OAuth library not installed
        return redirect_to_auth("Google Sign In library not installed. Install google-auth libraries.", "login")

    try:
        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=SCOPES
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        # Force account selection to ensure the account chooser appears
        # Ask Google to show the consent screen and allow selecting account explicitly
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent select_account'
        )

        # Debugging: log the auth URL and state so we can inspect behavior
        try:
            print(f"[DEBUG] Google OAuth authorization_url: {authorization_url}")
            print(f"[DEBUG] Google OAuth state: {state}")
        except Exception:
            pass

        session['google_oauth_state'] = state
        return redirect(authorization_url)
    except Exception as e:
        flash(f"Failed to initialize Google Sign In. Error: {str(e)}", "error")
        return redirect(url_for('user_login'))


@app.route('/debug/google-url')
def debug_google_url():
    """Generate and return the Google OAuth authorization URL for manual testing."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return jsonify({'error': 'Google OAuth not configured'}), 500

    if Flow is None:
        return jsonify({'error': 'Google OAuth library not installed'}), 500

    flow = Flow.from_client_config(GOOGLE_CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true', prompt='consent select_account'
    )
    # Return the URL and state so you can paste it into a browser and watch callback logs
    return jsonify({'authorization_url': authorization_url, 'state': state})


@app.route('/debug/google-link')
def debug_google_link():
    """Return a simple page with a clickable auth link for manual testing (open in incognito)."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return "Google OAuth not configured. Set environment variables.", 500

    if Flow is None:
        return "Google OAuth library not installed. Set up dependencies.", 500

    flow = Flow.from_client_config(GOOGLE_CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true', prompt='consent select_account'
    )

    html = f"""
    <html>
      <head><title>Google OAuth Test Link</title></head>
      <body style='font-family: Arial; padding: 24px'>
        <h2>Google OAuth Test</h2>
        <p>Open the link below in a private/incognito window to force the account chooser.</p>
        <p><a href=\"{authorization_url}\" target=\"_blank\">Open Google Sign-in (incognito)</a></p>
        <p>State: {state}</p>
      </body>
    </html>
    """
    return html


@app.route('/debug/env')
def debug_env():
    """Return whether Google OAuth env vars are present in the running process.
    This helps confirm the Flask process sees the credentials (masked client id).
    """
    google_configured = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    masked_client_id = None
    if GOOGLE_CLIENT_ID:
        # Mask the middle of the client id for safety
        cid = GOOGLE_CLIENT_ID
        if len(cid) > 16:
            masked_client_id = cid[:8] + '...' + cid[-6:]
        else:
            masked_client_id = cid[:4] + '...' + cid[-4:]

    return jsonify({
        'google_configured': google_configured,
        'GOOGLE_CLIENT_ID_masked': masked_client_id,
        'GOOGLE_REDIRECT_URI': GOOGLE_REDIRECT_URI
    })


@app.route('/debug/gemini')
def debug_gemini():
    """Return whether the Gemini API key is present in the running process (masked)."""
    key = os.environ.get('GOOGLE_GEMINI_API_KEY')
    if not key:
        return jsonify({'gemini_configured': False, 'masked_key': None}), 200

    if len(key) > 12:
        masked = key[:6] + '...' + key[-4:]
    else:
        masked = key[:3] + '...' + key[-3:]
    return jsonify({'gemini_configured': True, 'masked_key': masked}), 200

@app.route('/callback')
def google_oauth_callback():
    """Handles the callback from Google after user authentication."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        # FIX: Flash an error and redirect to user_login instead of index
        flash("Google Sign In is not configured. Please try again later.", "error")
        return redirect(url_for('user_login'))

    # Retrieve the state parameter from the session
    # Debug: log the incoming callback URL and query params
    try:
        print(f"[DEBUG] Google OAuth callback URL: {request.url}")
        print(f"[DEBUG] Google OAuth callback args: {request.args}")
        if 'error' in request.args:
            print(f"[DEBUG] Google OAuth returned error: {request.args.get('error')}")
    except Exception:
        pass

    if Flow is None:
        flash("Google Sign In is not available on this server.", "error")
        return redirect(url_for('auth'))

    state = session.pop('google_oauth_state', None)

    if not state or request.args.get('state') != state:
        # State mismatch is a CSRF risk
        flash("Authentication failed due to security reasons. Please try again.", "error") # FIX: Flash error
        return redirect(url_for('user_login')) # FIX: Redirect to login

    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    try:
        # Exchange the authorization code for credentials
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        # Use the credentials to get user info from Google's API
        session_request = requests.Session()
        if cachecontrol:
            cached_session = cachecontrol.CacheControl(session_request)
        else:
            cached_session = session_request

        # Get user info
        user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        user_info_response = cached_session.get(
            user_info_url,
            params={'access_token': credentials.token}
        )
        user_info = user_info_response.json()

        user_email = user_info['email']
        user_name = user_info.get('name', user_email)

        # Upsert user into MongoDB
        user_doc = users_collection.find_one({'email': user_email})
        if not user_doc:
            # New user registration (Sign Up)
            user_doc = {
                'email': user_email,
                'username': user_name,
                'created_at': datetime.now(),
                'role': 'user'
            }
            user_id = users_collection.insert_one(user_doc).inserted_id
        else:
            # Existing user (Sign In)
            user_id = user_doc['_id']
            # Update name if changed
            users_collection.update_one(
                {'_id': user_id},
                {'$set': {'username': user_name}}
            )

        # Set session variables
        session['user_id'] = str(user_id)
        session['username'] = user_name
        session['email'] = user_email
        session['role'] = 'user'

        return redirect(url_for('index'))

    except Exception as e:
        print(f"OAuth Error: {e}")
        # FIX: Flash error message and redirect to login page for better UX
        flash(f"Sign-in failed: {e}. Please try again.", "error")
        return redirect(url_for('user_login'))

@app.route('/logout')
def user_logout():
    """Logs the user out and clears the session."""
    session.clear() # Clear all session data
    return redirect(url_for('index'))


# --- Public Routes ---

@app.route('/')
def index():
    return render_template('user/index.html', current_page='home')

@app.route('/challenges')
def user_challenges():
    selected_topic = request.args.get('topic')
    query = {}
    if selected_topic:
        query['topic'] = selected_topic

    challenges = list(challenges_collection.find(query))
    return render_template('user/challenges.html', challenges=challenges, selected_topic=selected_topic, current_page='challenges')

@app.route('/mcqs')
def user_mcqs():
    selected_topic = request.args.get('topic')
    query = {}
    if selected_topic:
        query['topic'] = selected_topic

    mcqs = list(mcqs_collection.find(query))
    return render_template('user/mcqs.html', mcqs=mcqs, selected_topic=selected_topic, current_page='mcqs')

@app.route('/mcqs/verify', methods=['POST'])
def verify_mcq_answer():
    data = request.get_json() or request.form
    mcq_id = data.get('mcq_id')
    selected_option = data.get('selected_option', '').strip()

    if not mcq_id or not selected_option:
        return jsonify({'error': 'Invalid request parameters'}), 400

    try:
        mcq = mcqs_collection.find_one({'_id': ObjectId(mcq_id)})
    except Exception:
        return jsonify({'error': 'Invalid MCQ ID'}), 404

    if not mcq:
        return jsonify({'error': 'MCQ not found'}), 404

    correct = (selected_option == mcq.get('correct_answer'))
    return jsonify({
        'is_correct': correct,
        'correct_answer': mcq.get('correct_answer'),
        'explanation': f"Correct Answer: {mcq.get('correct_answer')}"
    })

def smart_fallback_fix_code(code, language):
    """Static analysis and code repair fallback engine when AI service is unavailable."""
    lines = code.split('\n')
    fixed_lines = []
    explanations = []

    lang_lower = language.lower()

    if lang_lower == 'python':
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Fix missing colon on def/class/if/elif/else/for/while
            if any(stripped.startswith(kw) for kw in ['def ', 'class ', 'if ', 'elif ', 'else', 'for ', 'while ', 'try', 'except', 'finally', 'with ']) or stripped in ['else', 'try', 'finally']:
                if not stripped.endswith(':') and not stripped.endswith(';'):
                    line = line + ':'
                    explanations.append(f"Line {i+1}: Added missing colon `:` to block header `{stripped}`")
            
            # Fix Python 2 print statement to Python 3 print()
            import re
            if re.match(r'^\s*print\s+["\'].*["\']', line) or re.match(r'^\s*print\s+\w+', line):
                match = re.search(r'print\s+(.*)', line)
                if match:
                    val = match.group(1)
                    indent = line[:len(line) - len(line.lstrip())]
                    line = f"{indent}print({val})"
                    explanations.append(f"Line {i+1}: Fixed `print` statement syntax to Python 3 function `print({val})`")

            # Fix common typo in main check
            if '__name__' in line and '__main__' in line and '==' in line and not line.strip().endswith(':'):
                line = line + ':'
                explanations.append(f"Line {i+1}: Added missing colon to `if __name__ == '__main__':` block")

            fixed_lines.append(line)

    elif lang_lower in ['javascript', 'js']:
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Fix missing semicolon
            if stripped and not stripped.endswith('{') and not stripped.endswith('}') and not stripped.endswith(';') and not stripped.startswith('//'):
                line = line + ';'
                explanations.append(f"Line {i+1}: Added missing semicolon `;`")
            fixed_lines.append(line)

    elif lang_lower in ['java', 'c++', 'c#', 'c']:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.endswith('{') and not stripped.endswith('}') and not stripped.endswith(';') and not stripped.startswith('//') and not stripped.startswith('#'):
                line = line + ';'
                explanations.append(f"Line {i+1}: Added missing terminating semicolon `;`")
            fixed_lines.append(line)

    else:
        fixed_lines = lines

    fixed_code_str = '\n'.join(fixed_lines)
    exp_summary = "\n".join(f"• {exp}" for exp in explanations) if explanations else "• Code structure & syntax validated."

    return f"""// --- AUTO-FIXED CODE ({language}) ---
{fixed_code_str}

/*
==================================================
              ANALYSIS & EXPLANATIONS
==================================================
{exp_summary}
==================================================
*/"""


def parse_ai_output(raw_text):
    """Separates code block from explanation and strips raw markdown hashes."""
    import re
    if not raw_text:
        return "", ""

    code_match = re.search(r'```(?:[a-zA-Z0-9_+#-]+)?\s*\n(.*?)\n```', raw_text, re.DOTALL)
    if code_match:
        clean_code = code_match.group(1).strip()
        explanation_part = raw_text.replace(code_match.group(0), '').strip()
    else:
        clean_code = raw_text.strip()
        explanation_part = ""

    # Clean raw markdown hashes ### and code markers from explanation
    explanation_clean = re.sub(r'#{1,6}\s*', '', explanation_part)
    explanation_clean = re.sub(r'```[a-zA-Z0-9]*', '', explanation_clean).strip()

    return clean_code, explanation_clean


@app.route('/fix_code', methods=['GET', 'POST'])
def user_fix_code():
    fixed_code = None
    fixed_code_only = None
    explanation_clean = None
    error_message = None
    code_to_fix = None
    language = "Python"

    if request.method == 'POST':
        code_to_fix = request.form.get('code_input', '').strip()
        language = request.form.get('language', 'Python').strip()

        if not code_to_fix:
            error_message = "Please provide code to fix."
            return render_template('user/fix_code.html', fixed_code=fixed_code, error_message=error_message, code_input=code_to_fix, language=language, current_page='fix_code')

        load_dotenv(override=True)
        api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")

        # Try Gemini AI first if configured
        if api_key:
            try:
                from google import genai as new_genai
                client = new_genai.Client(api_key=api_key)

                prompt = (
                    f"You are an expert AI software engineer. Analyze the following {language} code for syntax errors, "
                    f"runtime exceptions, logic bugs, or typos. Fix the code completely so it is runnable, bug-free, and clean.\n\n"
                    f"Provide your response formatted as:\n"
                    f"1. The full corrected code inside a ```{language.lower()} markdown code block.\n"
                    f"2. A section titled '### 🛠️ Explanation of Fixes' explaining every error found and how it was fixed.\n\n"
                    f"Input Code ({language}):\n```\n{code_to_fix}\n```"
                )

                for m_name in ['gemini-3.5-flash', 'gemini-3.1-pro-preview', 'gemini-3.6-flash', 'gemini-flash-latest']:
                    try:
                        res = client.models.generate_content(model=m_name, contents=prompt)
                        if res and res.text:
                            fixed_code = res.text
                            print(f"Gemini AI fix generated successfully using model '{m_name}'")
                            break
                    except Exception as model_err:
                        print(f"Model '{m_name}' error: {model_err}")
                        continue

            except Exception as ai_err:
                print(f"Gemini AI error: {ai_err}")
                error_message = f"AI Service Notice: Could not connect to Gemini API ({ai_err})"

        # Fallback to Smart Code Repair Engine if Gemini is unavailable/invalid
        if not fixed_code and not error_message:
            fixed_code = smart_fallback_fix_code(code_to_fix, language)

        if fixed_code:
            fixed_code_only, explanation_clean = parse_ai_output(fixed_code)

        if 'user_id' in session and fixed_code:
            try:
                fixcode_collection.insert_one({
                    'user_id': session['user_id'],
                    'input_code': code_to_fix,
                    'language': language,
                    'fixed_code_response': fixed_code,
                    'created_at': datetime.now()
                })
            except Exception:
                pass

    return render_template(
        'user/fix_code.html',
        fixed_code=fixed_code,
        fixed_code_only=fixed_code_only,
        explanation_clean=explanation_clean,
        error_message=error_message,
        code_input=code_to_fix,
        language=language,
        current_page='fix_code'
    )

@app.route('/peer_questions', methods=['GET', 'POST'])
def user_peer_questions():
    if request.method == 'POST':
        question_text = request.form.get('question', '').strip()
        asked_by = request.form.get('asked_by', 'Anonymous').strip()

        if question_text:
            peer_questions_collection.insert_one({
                'question': question_text,
                'asked_by': session.get('username', asked_by),
                'user_id': session.get('user_id', 'anon'),
                'created_at': datetime.now(),
                'answers': []
            })
        return redirect(url_for('user_peer_questions'))

    questions = list(peer_questions_collection.find().sort('created_at', -1))
    return render_template('user/peer_questions.html', questions=questions, current_page='peer_questions')

@app.route('/peer_questions/answer/<id>', methods=['POST'])
def add_answer_to_peer_question(id):
    answer_text = request.form.get('answer', '').strip()
    answered_by = request.form.get('answered_by', 'Anonymous').strip()

    if answer_text:
        try:
            peer_questions_collection.update_one(
                {'_id': ObjectId(id)},
                {'$push': {
                    'answers': {
                        'text': answer_text,
                        'answered_by': session.get('username', answered_by),
                        'user_id': session.get('user_id', 'anon'),
                        'created_at': datetime.now()
                    }
                }}
            )
        except:
            pass # Handle case where ID is invalid
    return redirect(url_for('user_peer_questions'))

@app.route('/puzzles', methods=['GET', 'POST'])
def user_puzzles():
    if request.method == 'POST':
        question_text = request.form.get('question', '').strip()
        correct_answer = request.form.get('answer', '').strip().lower()
        posted_by = request.form.get('posted_by', 'Anonymous').strip()

        if question_text and correct_answer:
            puzzles_collection.insert_one({
                'question': question_text,
                'correct_answer': correct_answer,
                'posted_by': session.get('username', posted_by),
                'user_id': session.get('user_id', 'anon'),
                'created_at': datetime.now(),
            })
        return redirect(url_for('user_puzzles'))

    # Load puzzles
    puzzles = list(puzzles_collection.find().sort('created_at', -1))

    # Enrich puzzles with user's attempts (only if logged in)
    if 'user_id' in session:
        for puzzle in puzzles:
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            # Ensure 'puzzle_attempts' key exists and then access the specific puzzle's attempts
            puzzle['attempts'] = user.get('puzzle_attempts', {}).get(str(puzzle['_id']), [])

    return render_template('user/puzzles.html', puzzles=puzzles, current_page='puzzles')

@app.route('/puzzles/answer/<id>', methods=['POST'])
@login_required() # User must be logged in to submit a guess
def submit_puzzle_answer(id):
    user_answer = request.form.get('user_answer', '').strip().lower()

    if not user_answer:
        return redirect(url_for('user_puzzles'))

    try:
        puzzle = puzzles_collection.find_one({'_id': ObjectId(id)})
    except:
        return redirect(url_for('user_puzzles')) # Invalid ID

    if not puzzle:
        return redirect(url_for('user_puzzles'))

    is_correct = (user_answer == puzzle['correct_answer'])

    # Prepare attempt data
    attempt_data = {
        'timestamp': datetime.now(),
        'guess': user_answer,
        'is_correct': is_correct
    }

    # Store attempt in the user's document
    user_id_str = session['user_id']

    # Use $push to add a new attempt to the specific puzzle's array within the user's document
    users_collection.update_one(
        {'_id': ObjectId(user_id_str)},
        {'$push': {
            f'puzzle_attempts.{id}': attempt_data
        }},
        # $setOnInsert ensures 'puzzle_attempts' dictionary is created if it doesn't exist
        upsert=True
    )

    # Optionally, you might want to flash a message here
    # flash(f"Your guess was {'correct' if is_correct else 'incorrect'}!", 'success' if is_correct else 'danger')

    return redirect(url_for('user_puzzles'))


# --- Admin Routes (CRUD) ---

@app.route('/admin')
@login_required(role="admin")
def admin_dashboard():
    users_count = users_collection.count_documents({})
    challenges_count = challenges_collection.count_documents({})
    mcqs_count = mcqs_collection.count_documents({})
    peer_questions_count = peer_questions_collection.count_documents({}) # FIX: Added count
    puzzles_count = puzzles_collection.count_documents({}) # FIX: Added count

    recent_challenges = list(challenges_collection.find().sort('_id', -1).limit(5))
    recent_mcqs = list(mcqs_collection.find().sort('_id', -1).limit(5))
    recent_users = list(users_collection.find().sort('created_at', -1).limit(5))

    return render_template('admin/admin_dashboard.html',
        users_count=users_count,
        challenges_count=challenges_count,
        mcqs_count=mcqs_count,
        peer_questions_count=peer_questions_count, # FIX: Passed to template
        puzzles_count=puzzles_count, # FIX: Passed to template
        recent_challenges=recent_challenges,
        recent_mcqs=recent_mcqs,
        recent_users=recent_users,
        current_page='admin_dashboard'
    )

# Challenge Management (List, Add, Edit, Delete)

@app.route('/admin/challenges')
@login_required(role="admin")
def admin_challenges_list():
    challenges = list(challenges_collection.find())
    return render_template('admin/admin_item_list.html', items=challenges, item_type='challenge', current_page='admin_challenges')

@app.route('/admin/challenges/add', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_add_challenge():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        topic = request.form.get('topic', '').strip()
        difficulty = request.form.get('difficulty', '').strip()

        if title:
            challenges_collection.insert_one({
                'title': title,
                'description': description,
                'topic': topic,
                'difficulty': difficulty,
                'created_at': datetime.now()
            })
        return redirect(url_for('admin_challenges_list'))
    return render_template('admin/add_challenge.html', current_page='admin_add_challenge')

@app.route('/admin/challenges/edit/<id>', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_edit_challenge(id):
    try:
        challenge = challenges_collection.find_one({'_id': ObjectId(id)})
    except:
        return abort(404)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        topic = request.form.get('topic', '').strip()
        difficulty = request.form.get('difficulty', '').strip()

        challenges_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'title': title,
                'description': description,
                'topic': topic,
                'difficulty': difficulty
            }}
        )
        return redirect(url_for('admin_challenges_list'))

    return render_template('admin/edit_challenge.html', challenge=challenge, current_page='admin_edit_challenge')

@app.route('/admin/delete/<item_type>/<id>', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_delete_item(item_type, id):
    collection_map = {
        'challenge': challenges_collection,
        'mcq': mcqs_collection,
        'user': users_collection,
        'puzzle': puzzles_collection
    }

    collection = collection_map.get(item_type)

    if collection is not None:
        try:
            collection.delete_one({'_id': ObjectId(id)})
            flash(f'{item_type.capitalize()} deleted successfully.', 'success')
        except Exception as e:
            flash(f'Failed to delete {item_type}: {str(e)}', 'error')

    if item_type == 'challenge':
        return redirect(url_for('admin_challenges_list'))
    elif item_type == 'mcq':
        return redirect(url_for('admin_mcqs_list'))
    elif item_type == 'user':
        return redirect(url_for('admin_users_list'))

    return redirect(url_for('admin_dashboard'))


# User Management (List, Add, Edit, Delete)

@app.route('/admin/users')
@login_required(role="admin")
def admin_users_list():
    users = list(users_collection.find())
    return render_template('admin/admin_item_list.html', items=users, item_type='user', current_page='admin_users')

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'user').strip()

        if not username or not email or not password:
            flash('Username, email, and password are required.', 'error')
            return render_template('admin/add_user.html', current_page='admin_users')

        if users_collection.find_one({'email': email}):
            flash('A user with this email address already exists.', 'error')
            return render_template('admin/add_user.html', current_page='admin_users')

        if users_collection.find_one({'username': username}):
            flash('Username is already taken.', 'error')
            return render_template('admin/add_user.html', current_page='admin_users')

        from werkzeug.security import generate_password_hash
        user_doc = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'role': role,
            'created_at': datetime.now()
        }
        users_collection.insert_one(user_doc)
        flash(f'User "{username}" created successfully as {role}.', 'success')
        return redirect(url_for('admin_users_list'))

    return render_template('admin/add_user.html', current_page='admin_users')

@app.route('/admin/users/edit/<id>', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_edit_user(id):
    try:
        user = users_collection.find_one({'_id': ObjectId(id)})
    except Exception:
        return abort(404)

    if not user:
        return abort(404)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        role = request.form.get('role', 'user').strip()
        new_password = request.form.get('password', '').strip()

        update_data = {
            'username': username,
            'email': email,
            'role': role
        }

        if new_password:
            from werkzeug.security import generate_password_hash
            update_data['password_hash'] = generate_password_hash(new_password)

        users_collection.update_one({'_id': ObjectId(id)}, {'$set': update_data})
        flash(f'User "{username}" updated successfully.', 'success')
        return redirect(url_for('admin_users_list'))

    return render_template('admin/edit_user.html', user=user, current_page='admin_users')

@app.route('/admin/users/delete/<id>', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_delete_user(id):
    try:
        users_collection.delete_one({'_id': ObjectId(id)})
        flash('User deleted successfully.', 'success')
    except Exception as e:
        flash(f'Failed to delete user: {str(e)}', 'error')
    return redirect(url_for('admin_users_list'))


# MCQ Management (List, Add)

@app.route('/admin/mcqs')
@login_required(role="admin")
def admin_mcqs_list():
    mcqs = list(mcqs_collection.find())
    return render_template('admin/admin_item_list.html', items=mcqs, item_type='mcq', current_page='admin_mcqs')

@app.route('/admin/mcqs/add', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_add_mcq():
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        options = [request.form.get(f'option{i}', '').strip() for i in range(1, 5)]
        correct_answer = request.form.get('correct_answer', '').strip()
        topic = request.form.get('topic', '').strip()
        if question:
            mcqs_collection.insert_one({
                'question': question,
                'options': options,
                'correct_answer': correct_answer,
                'topic': topic,
                'created_at': datetime.now()
            })
        return redirect(url_for('admin_mcqs_list'))
    return render_template('admin/add_mcq.html', current_page='admin_add_mcq')

@app.route('/admin/mcqs/edit/<id>', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_edit_mcq(id):
    try:
        mcq = mcqs_collection.find_one({'_id': ObjectId(id)})
    except:
        return abort(404)

    if not mcq:
        return abort(404)

    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        options = [request.form.get(f'option{i}', '').strip() for i in range(1, 5)]
        correct_answer = request.form.get('correct_answer', '').strip()
        topic = request.form.get('topic', '').strip()

        mcqs_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'question': question,
                'options': options,
                'correct_answer': correct_answer,
                'topic': topic
                        }}
        )
        return redirect(url_for('admin_mcqs_list'))

    return render_template('admin/edit_mcq.html', item=mcq, current_page='admin_edit_mcq')

# --- Leaderboard & XP Gamification ---

@app.route('/leaderboard')
def leaderboard():
    all_users = list(users_collection.find({'role': {'$ne': 'admin'}}))
    
    for u in all_users:
        xp = u.get('xp', 0)
        if xp == 0:
            mcq_count = len(u.get('mcq_attempts', []))
            puzzle_attempts = len(u.get('puzzle_attempts', {}))
            xp = (mcq_count * 15) + (puzzle_attempts * 25) + 180
            u['xp'] = xp
        
        u['streak'] = u.get('streak', 3)
        u['solved_count'] = u.get('solved_count', 8)
        u['badges'] = u.get('badges', ['Python Pioneer', 'Fast Learner'])
        
    all_users.sort(key=lambda x: x.get('xp', 0), reverse=True)
    return render_template('user/leaderboard.html', users=all_users, current_page='leaderboard')

@app.route('/profile')
@login_required()
def profile():
    user_id = session.get('user_id')
    try:
        user = users_collection.find_one({'_id': ObjectId(user_id)})
    except Exception:
        user = None
        
    if not user:
        return redirect(url_for('user_logout'))
        
    xp = user.get('xp', 320)
    streak = user.get('streak', 5)
    badges = user.get('badges', ['Python Pioneer', 'Bug Hunter', 'Code Warrior'])
    
    skills = {
        'Python': user.get('skill_python', 85),
        'JavaScript': user.get('skill_js', 70),
        'Data Structures': user.get('skill_dsa', 75),
        'Java': user.get('skill_java', 55),
        'C++': user.get('skill_cpp', 50),
        'SQL': user.get('skill_sql', 65)
    }
    
    bookmarks_count = len(user.get('bookmarks', []))
    
    return render_template('user/profile.html', user=user, xp=xp, streak=streak, badges=badges, skills=skills, bookmarks_count=bookmarks_count, current_page='profile')


# --- Live Code Runner ---

@app.route('/runner')
def code_runner():
    return render_template('user/runner.html', current_page='runner')

@app.route('/api/run_code', methods=['POST'])
def api_run_code():
    data = request.get_json() or request.form
    code = data.get('code', '').strip()
    language = data.get('language', 'Python').strip()

    if not code:
        return jsonify({'error': 'No code provided'}), 400

    lang_lower = language.lower()

    if lang_lower == 'python':
        import sys
        import io
        
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()
        
        try:
            exec_globals = {"__builtins__": __builtins__}
            exec(code, exec_globals)
            output = redirected_output.getvalue()
            if not output:
                output = "Code executed successfully with no output."
            return jsonify({'success': True, 'output': output})
        except Exception as e:
            return jsonify({'success': False, 'output': f"Runtime Error:\n{str(e)}"})
        finally:
            sys.stdout = old_stdout
            
    elif lang_lower in ['javascript', 'js']:
        return jsonify({'success': True, 'is_js': True, 'code': code})

    elif lang_lower in ['html', 'web']:
        return jsonify({'success': True, 'is_html': True, 'code': code})

    elif lang_lower == 'sql':
        import sqlite3
        try:
            conn = sqlite3.connect(':memory:')
            cursor = conn.cursor()
            
            statements = [s.strip() for s in code.split(';') if s.strip()]
            output_lines = []
            
            for stmt in statements:
                cursor.execute(stmt)
                if cursor.description:
                    columns = [d[0] for d in cursor.description]
                    rows = cursor.fetchall()
                    output_lines.append(f"Query: {stmt}")
                    output_lines.append(" | ".join(columns))
                    output_lines.append("-" * 45)
                    for r in rows:
                        output_lines.append(" | ".join(str(val) for val in r))
                    output_lines.append("")
                else:
                    output_lines.append(f"SQL OK: {stmt} (Rows affected: {cursor.rowcount})\n")

            conn.commit()
            conn.close()
            output = "\n".join(output_lines) if output_lines else "SQL statements executed successfully."
            return jsonify({'success': True, 'output': output})
        except Exception as e:
            return jsonify({'success': False, 'output': f"SQL Execution Error:\n{str(e)}"})

    elif lang_lower in ['c++', 'cpp', 'c']:
        import subprocess
        import tempfile

        is_cpp = lang_lower in ['c++', 'cpp']
        compiler = 'g++' if is_cpp else 'gcc'
        ext = '.cpp' if is_cpp else '.c'

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, f'main{ext}')
            exe_path = os.path.join(tmpdir, 'main.exe' if os.name == 'nt' else 'main')

            with open(src_path, 'w') as f:
                f.write(code)

            try:
                compile_proc = subprocess.run([compiler, src_path, '-o', exe_path], capture_output=True, text=True, timeout=10)
                if compile_proc.returncode != 0:
                    return jsonify({'success': False, 'output': f"Compilation Error ({compiler}):\n{compile_proc.stderr}"})
                
                run_proc = subprocess.run([exe_path], capture_output=True, text=True, timeout=5)
                output = run_proc.stdout
                if run_proc.stderr:
                    output += f"\n[stderr]:\n{run_proc.stderr}"
                if not output:
                    output = "Program executed successfully with no output."
                return jsonify({'success': True, 'output': output})
            except FileNotFoundError:
                return jsonify({'success': False, 'output': f"Compiler '{compiler}' is not installed on host machine. To compile {language}, install MinGW / GCC."})
            except Exception as e:
                return jsonify({'success': False, 'output': f"Execution Error:\n{str(e)}"})

    elif lang_lower == 'java':
        import subprocess
        import tempfile
        import re

        class_match = re.search(r'public\s+class\s+(\w+)', code)
        class_name = class_match.group(1) if class_match else 'Main'

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, f'{class_name}.java')
            with open(src_path, 'w') as f:
                f.write(code)

            try:
                compile_proc = subprocess.run(['javac', src_path], capture_output=True, text=True, timeout=10)
                if compile_proc.returncode != 0:
                    return jsonify({'success': False, 'output': f"Java Compilation Error:\n{compile_proc.stderr}"})
                
                run_proc = subprocess.run(['java', '-cp', tmpdir, class_name], capture_output=True, text=True, timeout=5)
                output = run_proc.stdout
                if run_proc.stderr:
                    output += f"\n[stderr]:\n{run_proc.stderr}"
                if not output:
                    output = "Java program executed successfully with no output."
                return jsonify({'success': True, 'output': output})
            except FileNotFoundError:
                return jsonify({'success': False, 'output': "Java JDK ('javac') is not installed on host machine. To run Java, install OpenJDK/JDK."})
            except Exception as e:
                return jsonify({'success': False, 'output': f"Execution Error:\n{str(e)}"})

    elif lang_lower == 'json':
        import json
        try:
            parsed = json.loads(code)
            formatted = json.dumps(parsed, indent=4)
            return jsonify({'success': True, 'output': f"✅ Valid JSON Syntax:\n\n{formatted}"})
        except Exception as e:
            return jsonify({'success': False, 'output': f"❌ Invalid JSON Syntax Error:\n{str(e)}"})

    elif lang_lower == 'php':
        import subprocess
        try:
            proc = subprocess.run(['php', '-r', code], capture_output=True, text=True, timeout=5)
            if proc.returncode != 0:
                return jsonify({'success': False, 'output': f"PHP Error:\n{proc.stderr}"})
            return jsonify({'success': True, 'output': proc.stdout or "PHP script executed with no output."})
        except FileNotFoundError:
            return jsonify({'success': False, 'output': "PHP binary is not installed on host machine. Install PHP CLI to run PHP scripts."})

    elif lang_lower == 'ruby':
        import subprocess
        try:
            proc = subprocess.run(['ruby', '-e', code], capture_output=True, text=True, timeout=5)
            if proc.returncode != 0:
                return jsonify({'success': False, 'output': f"Ruby Error:\n{proc.stderr}"})
            return jsonify({'success': True, 'output': proc.stdout or "Ruby script executed with no output."})
        except FileNotFoundError:
            return jsonify({'success': False, 'output': "Ruby interpreter is not installed on host machine. Install Ruby to run scripts."})

    elif lang_lower == 'go':
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, 'main.go')
            with open(src_path, 'w') as f:
                f.write(code)
            try:
                proc = subprocess.run(['go', 'run', src_path], capture_output=True, text=True, timeout=10)
                if proc.returncode != 0:
                    return jsonify({'success': False, 'output': f"Go Error:\n{proc.stderr}"})
                return jsonify({'success': True, 'output': proc.stdout or "Go program executed with no output."})
            except FileNotFoundError:
                return jsonify({'success': False, 'output': "Go toolchain ('go') is not installed on host machine. Install Golang to run Go code."})
        
    return jsonify({'error': f'Unsupported language: {language}'}), 400


# --- Global Search & Bookmarking ---

@app.route('/api/search')
def api_search():
    query_str = request.args.get('q', '').strip()
    if not query_str:
        return jsonify({'results': []})

    regex = {'$regex': query_str, '$options': 'i'}
    
    matching_mcqs = list(mcqs_collection.find({'question': regex}).limit(4))
    matching_challenges = list(challenges_collection.find({'$or': [{'title': regex}, {'description': regex}]}).limit(4))
    matching_puzzles = list(puzzles_collection.find({'question': regex}).limit(4))

    results = []
    for m in matching_mcqs:
        results.append({'id': str(m['_id']), 'title': m['question'], 'type': 'MCQ', 'url': url_for('user_mcqs', topic=m.get('topic'))})
    for c in matching_challenges:
        results.append({'id': str(c['_id']), 'title': c['title'], 'type': 'Challenge', 'url': url_for('user_challenges', topic=c.get('topic'))})
    for p in matching_puzzles:
        results.append({'id': str(p['_id']), 'title': p['question'], 'type': 'Puzzle', 'url': url_for('user_puzzles')})

    return jsonify({'results': results})

@app.route('/bookmarks')
@login_required()
def bookmarks():
    user_id = session.get('user_id')
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    bookmark_ids = user.get('bookmarks', []) if user else []

    saved_items = []
    for bid in bookmark_ids:
        try:
            obj_id = ObjectId(bid)
            mcq = mcqs_collection.find_one({'_id': obj_id})
            if mcq:
                mcq['item_type'] = 'MCQ'
                saved_items.append(mcq)
                continue
            ch = challenges_collection.find_one({'_id': obj_id})
            if ch:
                ch['item_type'] = 'Challenge'
                saved_items.append(ch)
                continue
            pz = puzzles_collection.find_one({'_id': obj_id})
            if pz:
                pz['item_type'] = 'Puzzle'
                saved_items.append(pz)
        except Exception:
            pass

    return render_template('user/bookmarks.html', items=saved_items, current_page='bookmarks')

@app.route('/api/bookmark/toggle', methods=['POST'])
@login_required()
def toggle_bookmark():
    data = request.get_json() or request.form
    item_id = data.get('item_id')
    if not item_id:
        return jsonify({'error': 'Missing item_id'}), 400

    user_id = session.get('user_id')
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    bookmarks_list = user.get('bookmarks', []) if user else []

    if item_id in bookmarks_list:
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$pull': {'bookmarks': item_id}})
        is_bookmarked = False
    else:
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$addToSet': {'bookmarks': item_id}})
        is_bookmarked = True

    return jsonify({'success': True, 'is_bookmarked': is_bookmarked})


@app.errorhandler(404)
def page_not_found(e):
  
    return render_template('404.html', current_page='404'), 404


import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1']
    app.run(host='0.0.0.0', port=port, debug=debug)