# --- START OF FILE app.py ---

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash
from dotenv import load_dotenv   
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
try:
    import google.generativeai as genai
except Exception:
    genai = None
from datetime import datetime
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

app.secret_key = secrets.token_hex(24)

load_dotenv()

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "shadowx_db"

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
    try:
        genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
        print("Gemini API configured.")
    except Exception as e:
        print(f"WARNING: Could not configure Gemini API: {e}")
elif GOOGLE_GEMINI_API_KEY and not genai:
    print("WARNING: GOOGLE_GEMINI_API_KEY is set but 'google.generativeai' package is not installed. Fix Code feature will not work.")
else:
    print("WARNING: GOOGLE_GEMINI_API_KEY environment variable not set. Fix Code feature will not work.")


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
    
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('admin/admin_login.html', current_page='admin_login')

        # Check if admin exists in database, if not create one
        admin = users_collection.find_one({'username': 'admin', 'role': 'admin'})
        if not admin:
            # Create admin user if it doesn't exist
            from werkzeug.security import generate_password_hash
            admin_doc = {
                'username': 'admin',
                'email': 'admin@shadowx.com',
                'password_hash': generate_password_hash('adminpass'),
                'role': 'admin',
                'created_at': datetime.now()
            }
            admin_id = users_collection.insert_one(admin_doc).inserted_id
            admin = users_collection.find_one({'_id': admin_id})

        # Hardcoded admin credentials for development (should use proper password hashing in production)
        if username == 'admin' and password == 'adminpass':
            session['logged_in'] = True
            session['role'] = 'admin'
            session['username'] = admin['username']
            session['email'] = admin['email']
            session['user_id'] = str(admin['_id'])  # Convert ObjectId to string

            flash('Welcome back, Admin!', 'success')
            return redirect(next_url or url_for('admin_dashboard'))
        
        flash('Invalid Credentials. Please try again.', 'error')
        
    return render_template('admin/admin_login.html', current_page='admin_login')

@app.route('/admin/logout')
def admin_logout():
    """Logs out admin user and clears session."""
    session.clear()  # Clear all session data for security
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))



@app.route('/auth', methods=['GET', 'POST'])
def auth():
    """Handle both login and registration in one route"""
    if 'user_id' in session:
        return redirect(url_for('index'))

    form_type = request.args.get('form_type', 'login')
    next_url = request.args.get('next')

    if request.method == 'POST':
        form_type = request.form.get('form_type', 'login')
        
        if form_type == 'register':
            # Handle Registration
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            # Validation
            if not all([email, username, password, confirm_password]):
                return redirect_to_auth('All fields are required.', 'register')
            elif password != confirm_password:
                return redirect_to_auth('Passwords do not match.', 'register')
            elif len(password) < 8:
                return redirect_to_auth('Password must be at least 8 characters long.', 'register')
            elif users_collection.find_one({'email': email}):
                return redirect_to_auth('Email already registered.', 'register')

            # Create new user
            from werkzeug.security import generate_password_hash
            user_doc = {
                'email': email,
                'username': username,
                'password_hash': generate_password_hash(password),
                'created_at': datetime.now(),
                'role': 'user'
            }
            user_id = users_collection.insert_one(user_doc).inserted_id

            # Log the user in
            session['user_id'] = str(user_id)
            session['username'] = username
            session['email'] = email
            session['role'] = 'user'
            flash('Registration successful!', 'success')
            return redirect(next_url or url_for('index'))

        elif form_type == 'login':
            # Handle Login
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()

            if not username or not password:
                return redirect_to_auth('All fields are required.', 'login')

            from werkzeug.security import check_password_hash
            user = users_collection.find_one({'username': username})

            if user and check_password_hash(user.get('password_hash', ''), password):
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                session['email'] = user['email']
                session['role'] = user.get('role', 'user')
                flash('Welcome back!', 'success')
                return redirect(next_url or url_for('index'))
            else:
                return redirect_to_auth('Invalid username or password.', 'login')

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

@app.route('/fix_code', methods=['GET', 'POST'])
def user_fix_code():
    fixed_code = None
    error_message = None
    code_to_fix = None
    language = "Python"

    if request.method == 'POST':
        code_to_fix = request.form.get('code_input', '').strip()
        language = request.form.get('language', 'Python').strip()

        if not GOOGLE_GEMINI_API_KEY or not genai:
            # Ensure both the API key and the library are available
            error_message = "Google Gemini API key or library not configured. Cannot fix code."
        elif not code_to_fix:
            error_message = "Please provide code to fix."
        else:
            try:
                # 🛑 OLD LINE: model = genai.GenerativeModel('gemini-pro')
                # ✅ NEW LINE: Use the correct, simplified model name.
                # 'gemini-2.5-flash' is the recommended model for chat/text tasks.
                model = genai.GenerativeModel('gemini-2.5-flash') 
                
                # Craft a clear prompt for debugging and explanation
                prompt = f"You are a helpful coding assistant. Fix the following {language} code, make it runnable, and provide a clear, concise explanation of the bug and the changes you made. Format the response with the fixed code in a separate code block, followed by the explanation.\n\nCode to Fix:\n```\n{code_to_fix}\n```"

                response = model.generate_content(prompt)
                fixed_code = response.text
                # Optional: log the request to the database
                if 'user_id' in session:
                    fixcode_collection.insert_one({
                        'user_id': session['user_id'],
                        'input_code': code_to_fix,
                        'language': language,
                        'fixed_code_response': fixed_code,
                        'created_at': datetime.now()
                    })

            except Exception as e:
                error_message = f"AI Service Error: Could not process request. Details: {e}"

    return render_template('user/fix_code.html', fixed_code=fixed_code, error_message=error_message, code_input=code_to_fix, language=language, current_page='fix_code')

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

@app.route('/admin/delete/<item_type>/<id>')
@login_required(role="admin")
def admin_delete_item(item_type, id):
    collection_map = {
        'challenge': challenges_collection,
        'mcq': mcqs_collection,
        'user': users_collection
    }

    collection = collection_map.get(item_type)

    if collection:
        try:
            collection.delete_one({'_id': ObjectId(id)})
        except:
            pass # Invalid ID

    # Determine where to redirect back
    if item_type == 'challenge':
        return redirect(url_for('admin_challenges_list'))
    elif item_type == 'mcq':
        return redirect(url_for('admin_mcqs_list'))
    elif item_type == 'user':
        return redirect(url_for('admin_users_list'))

    return redirect(url_for('admin_dashboard'))


# MCQ Management (List, Add)

@app.route('/admin/mcqs')
@login_required(role="admin")
def admin_mcqs_list():
   
    mcqs_collection.delete_many({'topic': {'$in': ['Flask', 'MongoDB', 'HTML/CSS']}})
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

# User Management (List)

@app.route('/admin/users')
@login_required(role="admin")
def admin_users_list():
    users = list(users_collection.find())
    return render_template('admin/admin_item_list.html', items=users, item_type='user', current_page='admin_users')

@app.route('/admin/users/delete/<id>')
@login_required(role="admin")
def admin_delete_user(id):
    """Redirect to the generic delete function for users"""
    return redirect(url_for('admin_delete_item', item_type='user', id=id))

@app.errorhandler(404)
def page_not_found(e):
  
    return render_template('404.html', current_page='404'), 404


import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')

if __name__ == '__main__':
 
    app.run(host='0.0.0.0', debug=True,port=8000)