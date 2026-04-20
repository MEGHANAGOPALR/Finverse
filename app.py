import os
import json
import csv
from io import StringIO
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from pathlib import Path
from collections import defaultdict
import operator

# Load environment variables from .env file
load_dotenv()

# --- Configuration & Initialization ---
app = Flask(__name__)
app.secret_key = 'a_very_secret_key_for_sessions_12345' 

# Load API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found. AI features will use deterministic stubs.")

# Import manager modules
from backend.managers import user_manager
from backend.managers import chat_manager
from backend.managers.file_manager import write_json, read_json

# --- Global Definitions ---
# Categories that should be treated as expenses when amounts are positive in the CSV
EXPENSE_CATEGORIES = [
    'groceries', 'food', 'entertainment', 'transport', 'shopping', 
    'bills', 'rent', 'health', 'education', 'miscellaneous', 'other'
]

# --- AI System Instruction ---
SYSTEM_INSTRUCTION = (
    "You are Finny, a professional, helpful, and ethical AI Financial Planner. "
    "Your primary goal is to provide concise, direct, and actionable financial guidance."
    "\n\n--- Conversational Mode (DEFAULT) ---"
    "\n- **Primary behavior:** Answer conversationally in 1-2 short paragraphs or up to 7 brief bullet points."
    "\n- **Do NOT** use markdown headings, numbered sections, or tables for quick, conversational queries."
    "\n- If data is missing or incomplete for a request, state the limitation and ask one brief, clarifying question."
    "\n- Use the INR currency symbol (₹) for all monetary values."
    
    "\n\n--- Structured Analysis Mode ---"
    "\n- **Only enter this mode** if the user explicitly asks for a 'full analysis,' 'detailed breakdown,' or 'comprehensive report' of their data."
    "\n- When in this mode, you MUST STRICTLY follow this multi-section structure, using markdown headings and formatting:"
    
    "\n\n## 1. Financial Summary"
    "\n(Provide 1-2 concise paragraphs assessing the user's overall financial health and habits.)"
    
    "\n\n## 2. Spending Breakdown"
    "\n(Provide a detailed Markdown table with columns: 'Category', 'Total Amount (₹)', and 'Percentage' of total expenditure.)"
    
    "\n\n## 3. Top 3 Actionable Recommendations"
    "\n(Provide a numbered list. Each recommendation must be bold, specific, and include a priority rating: **[HIGH/MEDIUM/LOW]**)."
)

# --- Decorators and Utilities ---

def login_required(f):
    """A decorator to check if the user is authenticated via session or URL/JSON payload."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = kwargs.get('user_id') or session.get('user_id') or request.json.get('user_id')
        if not user_id:
            # For API calls, return a 401. For page access, redirect.
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- AI Stubs (Deterministic Simulation) ---

def generate_ai_analysis_stub(user_id):
    """Generates deterministic financial analysis based on profile data and transactions, 
    now also preparing data for multiple charts."""
    profile = user_manager.get_user_profile(user_id)
    onboarding = profile.get('onboarding', {})
    
    # Use Rupees symbol (₹)
    CURRENCY = '₹'
    
    salary = onboarding.get('monthly_net_salary', 0)
    expenditure = onboarding.get('monthly_expenditure', 0)
    savings = onboarding.get('total_liquid_savings', 0)
    surplus = salary - expenditure
    
    # Check for transactions
    transactions = read_json(f'{user_id}_transactions.json', default=[])
    
    # --- Response Structure Initialization ---
    full_response = ""
    summary_of_habits = ""
    recommendations_list = []
    
    # New data structure for multiple charts
    chart_data = {
        'category_distribution': [], # Chart B/Doughnut Chart
        'top_transactions': [],      # Chart D
        'monthly_summary': [],       # Chart C
        'category_trends': []        # Chart A/E
    }

    
    if not transactions:
        # Default analysis when no transactions are uploaded
        chart_data['category_distribution'] = [{'category': 'Profile Stub', 'percent': 100}]
        
        greeting = (
            f"Hello! I'm Finny. Based on your initial profile, I can offer some advice, "
            "but please upload your transaction CSV for a detailed breakdown!"
        )
        
        # Spending Breakdown Stub
        breakdown_table = (
            "| Category | Total Amount (₹) |\n"
            "| :--- | :--- |\n"
            "| **Profile Estimate** | **N/A** |\n"
            f"| Monthly Expenditure | {CURRENCY}{expenditure:,.2f} |"
        )
        
        # Summary of Habits Stub
        summary_of_habits = (
            "Your spending habits are currently **unknown**, as no transaction data has been uploaded. "
            "Your profile shows an estimated monthly surplus of "
            f"{CURRENCY}{surplus:,.2f}. To convert this estimate into an accurate plan, "
            "detailed spending analysis is essential. Please upload a CSV of your last month's transactions. "
            f"Your current liquid savings are {CURRENCY}{savings:,.2f}."
        )

        # Recommendations Stub (Profile-based)
        recommendations_list = [
            f"**HIGH** - **Upload Your Transactions**: Immediately upload your CSV to identify your biggest spending categories and receive personalized, accurate financial advice.",
            f"**MEDIUM** - **Build Emergency Fund**: Given your liquid savings of {CURRENCY}{savings:,.2f}, aim to save an amount equal to three months of estimated expenditure (Target: {CURRENCY}{expenditure * 3:,.2f}).",
            f"**LOW** - **Review Subscriptions**: Audit all recurring subscription expenses and cancel any unused services to create immediate, small monthly savings."
        ]
        
    else:
        # --- Transaction-based Analysis ---
        
        # 1. Filter and normalize expenses
        expense_transactions = []
        for txn in transactions:
            amount = txn.get('amount', 0)
            # Only consider expenses (negative amounts)
            if amount < 0:
                expense_transactions.append({
                    'date': txn.get('date'),
                    'description': txn.get('description'),
                    'category': txn.get('category', 'Uncategorized'),
                    'amount': abs(amount) # Use positive value for calculations
                })

        total_expense = sum(txn['amount'] for txn in expense_transactions)

        # --- Handle cases with no valid expenses ---
        if total_expense == 0:
            chart_data['category_distribution'] = [{'category': 'No Expense Data', 'percent': 100}]
            
            greeting = f"Hello! I processed {len(transactions)} transactions but found no valid expense data."
            # ... (Rest of the 'No Expenses Found' logic, same as previous step)
            breakdown_table = (
                "| Category | Total Amount (₹) |\n"
                "| :--- | :--- |\n"
                "| **No Expenses Found** | **N/A** |"
            )
            
            summary_of_habits = (
                "No negative amount transactions (expenses) were found. Please ensure your CSV file structure is correct and "
                "that expense amounts are listed as negative values or categorized correctly (e.g., Groceries, Rent) for accurate analysis."
            )
            
            recommendations_list = [
                f"**HIGH** - **Verify CSV Format**: Re-upload your transaction CSV ensuring expense amounts are negative (e.g., -500) or categories are correct.",
                f"**MEDIUM** - **Check Onboarding Data**: Review your profile for any inaccurate estimates that might affect planning.",
                f"**LOW** - **Manual Budget Review**: Until data is analyzed, use a simple 50/30/20 budget rule as a guide (Needs/Wants/Savings)."
            ]
        
        else:
            # --- Prepare Data for All Charts ---

            # Chart B/Doughnut Chart: Category Distribution
            spending_distribution = defaultdict(float)
            for txn in expense_transactions:
                spending_distribution[txn['category']] += txn['amount']
            
            chart_data['category_distribution'] = [
                {'category': k, 'percent': (v / total_expense) * 100} for k, v in spending_distribution.items()
            ]

            # Chart D: Top 5 Highest Transactions
            chart_data['top_transactions'] = sorted(
                expense_transactions, 
                key=operator.itemgetter('amount'), 
                reverse=True
            )[:5]

            # Chart C and A/E: Monthly Summary and Category Trends
            monthly_summary = defaultdict(float)
            category_trends = defaultdict(lambda: defaultdict(float))
            
            for txn in expense_transactions:
                try:
                    # Parse date to YYYY-MM format
                    date_obj = datetime.strptime(txn['date'], '%Y-%m-%d')
                    month_key = date_obj.strftime('%Y-%m') 
                    
                    monthly_summary[month_key] += txn['amount']
                    category_trends[month_key][txn['category']] += txn['amount']
                except ValueError:
                    # Skip transactions with invalid date format
                    continue

            # Format Monthly Summary (Chart C)
            # Sort by month key (YYYY-MM)
            for month, total in sorted(monthly_summary.items()):
                chart_data['monthly_summary'].append({
                    'month': month,
                    'total_amount': total
                })

            # Format Category Trends (Chart A/E)
            # Transform from {month: {category: amount}} to [{month: m, category: c, amount: a}]
            for month, categories in category_trends.items():
                for category, amount in categories.items():
                    chart_data['category_trends'].append({
                        'month': month,
                        'category': category,
                        'amount': amount
                    })


            # --- Prepare AI Response Text (using existing logic) ---
            
            # 2. Build Markdown Table for Spending Breakdown
            greeting = f"Hello! I've analyzed your {len(transactions)} uploaded transactions and generated a detailed financial analysis."
            
            breakdown_table = (
                "| Category | Total Amount (₹) |\n"
                "| :--- | :--- |\n"
            )
            # Sort by amount descending for a neat table
            sorted_expenses = sorted(spending_distribution.items(), key=lambda item: item[1], reverse=True)
            for category, amount in sorted_expenses:
                breakdown_table += f"| {category} | {CURRENCY}{amount:,.2f} |\n"
            
            # 3. Summary of Habits (Dynamic based on data)
            top_category, top_value = sorted_expenses[0]
            top_percent = (top_value / total_expense) * 100
            
            summary_of_habits = (
                f"Your spending shows a critical concentration on **{top_category}** ({top_percent:.1f}% of total expenses). "
                "This expense level indicates an area requiring immediate budget reallocation to achieve your savings goals. Your total expense of "
                f"{CURRENCY}{total_expense:,.2f} is high relative to your income, suggesting a need for a structural change in spending habits."
            )
            
            # 4. Recommendations (Dynamic based on data)
            main_expense = top_value
            main_target = main_expense * 0.85 # 15% reduction goal
            
            recommendations_list = [
                f"**HIGH** - **Reduce {top_category} Spending**: Your primary action should be reducing this category by 15% immediately. This creates a target monthly spend of {CURRENCY}{main_target:,.2f}. Explore immediate substitutes or cheaper alternatives.",
            ]

            if len(sorted_expenses) > 1:
                secondary_category, secondary_expense = sorted_expenses[1]
                secondary_reduction = secondary_expense * 0.10 # 10% reduction for medium priority
                recommendations_list.append(
                    f"**MEDIUM** - **Trim {secondary_category} Budget**: Aim for a moderate 10% saving in this area, equivalent to {CURRENCY}{secondary_reduction:,.2f} per month, by tracking and limiting discretionary purchases tightly.",
                )
            else:
                # Fallback Medium Recommendation
                recommendations_list.append(
                    f"**MEDIUM** - **Set a Weekly Check-in**: Allocate one hour every week to review your expenses in detail. This proactive habit will significantly improve financial awareness and control over your budget."
                )

            # Final LOW Recommendation
            recommendations_list.append(
                f"**LOW** - **Optimize Utility Bills**: Contact your service providers (Internet, phone, electricity) to negotiate a lower rate or switch to a more cost-effective plan. Target a small, passive 3% saving on recurring monthly bills."
            )

    # --- Combine all sections for the final 'summary' (Common to IF and ELSE) ---
    formatted_recommendations = "\n".join([f"{i+1}. {rec}" for i, rec in enumerate(recommendations_list)])

    full_response = (
        f"{greeting}\n\n"
        f"## 1. Spending Breakdown\n"
        f"{breakdown_table}\n"
        f"## 2. Summary of Habits\n"
        f"{summary_of_habits}\n\n"
        f"## 3. Three Key Actionable Recommendations\n"
        f"{formatted_recommendations}"
    )
        
    return {
        'success': True,
        'summary': full_response, # The single source of the formatted text
        'charts': chart_data # New comprehensive chart data object
    }

def get_ai_chat_response_stub(user_id, chat_name, message_content):
    """Generates a deterministic chatbot response."""
    # This stub is deliberately simple to demonstrate the core chat function
    
    # Get user's profile data
    profile = user_manager.get_user_profile(user_id)
    onboarding = profile.get('onboarding', {})
    
    salary = onboarding.get('monthly_net_salary', 0)
    savings = onboarding.get('total_liquid_savings', 0)
    CURRENCY = '₹'
    
    if 'expense' in message_content.lower() or 'spend' in message_content.lower():
        response = (
            "Based on your onboarding data, your monthly estimated expenditure is "
            f"{CURRENCY}{onboarding.get('monthly_expenditure', 0):,.2f}. To get a detailed spending breakdown, "
            "please upload your transaction CSV on the Dashboard. **I can't analyze transactions until they are uploaded**."
        )
    elif 'save' in message_content.lower() or 'invest' in message_content.lower():
        response = (
            f"Your current liquid savings are **{CURRENCY}{savings:,.2f}**. A good first step is to ensure you have a "
            "**HIGH** priority 3-6 month emergency fund. After securing that, look into tax-advantaged investment accounts for **MEDIUM** priority growth."
        )
    elif 'debt' in message_content.lower():
        debt = onboarding.get('total_debt_amount', 0)
        if debt > 0:
            rate = onboarding.get('average_interest_rate', 0)
            response = (
                f"Your total outstanding debt is **{CURRENCY}{debt:,.2f}** with an average rate of **{rate:.1f}%**. "
                "Focus on aggressively paying off the debt with the highest interest rate (Avalanche Method) as a **HIGH** priority."
            )
        else:
            response = "Congratulations! Your profile indicates you have no major debt. Focus on **MEDIUM** priority investing."
    else:
        response = (
            "That's a great question! I'm Finny, your AI financial planner. "
            "My current knowledge is based on your profile. Try asking about your **expenses**, **savings goals**, or **debt strategy**."
        )
        
    return {
        'success': True,
        'role': 'bot',
        'content': response
    }

def get_ai_chat_response(user_id, chat_name, message_content):
    """Generates a chatbot response using Google Gemini. Falls back to stub if key/missing pkg/errors."""
    # Fallback if no API key
    if not GEMINI_API_KEY:
        return get_ai_chat_response_stub(user_id, chat_name, message_content)

    try:
        # Local import to avoid ImportError at import time if dependency is not installed yet
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)

        # Use a lightweight, fast model by default; allow override via env
        model_name = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash-lite')
        try:
            model = genai.GenerativeModel(model_name)
        except Exception:
            # Fallback to pro-latest if the chosen model is unavailable
            model = genai.GenerativeModel('gemini-1.5-pro-latest')

        # Gather minimal context
        profile = user_manager.get_user_profile(user_id) or {}
        onboarding = profile.get('onboarding', {})
        CURRENCY = '₹'
        profile_summary = (
            f"Monthly net salary: {CURRENCY}{onboarding.get('monthly_net_salary', 0):,.2f}; "
            f"Monthly expenditure (est.): {CURRENCY}{onboarding.get('monthly_expenditure', 0):,.2f}; "
            f"Liquid savings: {CURRENCY}{onboarding.get('total_liquid_savings', 0):,.2f}; "
            f"Debt: {CURRENCY}{onboarding.get('total_debt_amount', 0):,.2f} at ~{onboarding.get('average_interest_rate', 0):.1f}%"
        )

        # Prepare brief recent chat history (last 8 messages, trimmed)
        try:
            history = chat_manager.get_chat_history(user_id, chat_name)
        except Exception:
            history = []
        recent = history[-8:]
        def _trim(s, n=200):
            s = s or ""
            return (s[:n] + "…") if len(s) > n else s
        history_lines = [f"- {m.get('role','user')}: {_trim(m.get('content',''))}" for m in recent]
        history_block = "\n".join(history_lines) if history_lines else "- (no prior context)"

        # Compose prompt: conversational by default, structured only when asked
        chat_guidance = (
            "You are a professional, helpful, and ethical AI Financial Planner. "
            "Default behavior: answer conversationally in a concise paragraph or up to 15 short bullets. "
            "Do NOT include headings, numbered sections, or tables unless the user explicitly requests a full analysis. "
            "If you lack data, ask a brief clarifying question or explain the limitation succinctly. "
            "Use INR symbol (₹) where relevant."
        )

        structured_rules = (
            "When explicitly requested for a full analysis, STRICTLY follow this format: "
            "1) A Spending Breakdown (Markdown table with 'Category' and 'Total Amount (₹)'), "
            "2) A Summary of Habits (1-2 short paragraphs), and "
            "3) Three Key Actionable Recommendations as a bold, numbered list with HIGH/MEDIUM/LOW priorities."
        )

        # Detect if the user is asking for a full analysis
        msg_l = (message_content or "").lower()
        wants_analysis = any(k in msg_l for k in [
            'analysis', 'breakdown', 'spending table', 'spending breakdown', 'report', 'detailed analysis'
        ])

        prompt_parts = [
            chat_guidance,
            (structured_rules if wants_analysis else ""),
            f"User profile (brief): {profile_summary}",
            f"Chat name: {chat_name}",
            "Recent chat history:\n" + history_block,
            f"User message: {message_content}",
        ]

        # Trim empty entries
        prompt_parts = [p for p in prompt_parts if p]

        # Control verbosity/creativity
        generation_config = {
            'max_output_tokens': 400,
            'temperature': 0.7,
            'top_p': 0.9,
        }
        resp = model.generate_content(prompt_parts, generation_config=generation_config)
        text = (resp.text or '').strip()
        if not text:
            # Defensive fallback
            return get_ai_chat_response_stub(user_id, chat_name, message_content)

        return {
            'success': True,
            'role': 'bot',
            'content': text
        }
    except Exception as e:
        # Log and fallback to stub
        print(f"Gemini error: {e}")
        return get_ai_chat_response_stub(user_id, chat_name, message_content)

# --- Frontend Routes (No Changes Required) ---

@app.route('/')
def home():
    """Redirects to login or dashboard based on session state."""
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/onboarding')
@login_required
def onboarding():
    return render_template('onboarding.html')

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


# --- API Endpoints: Auth & Profile (No Changes Required) ---

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({'success': False, 'message': 'Missing required fields.'}), 400

    success, message, user_id = user_manager.create_user(name, email, password)
    
    if success:
        session['user_id'] = user_id # Establish session on successful signup
        return jsonify({'success': True, 'message': message, 'user_id': user_id}), 201
    else:
        return jsonify({'success': False, 'message': message}), 409 # Conflict

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({'success': False, 'message': 'Missing email or password.'}), 400

    user_id = user_manager.authenticate_user(email, password)
    
    if user_id:
        session['user_id'] = user_id # Establish session on successful login
        return jsonify({'success': True, 'message': 'Login successful.', 'user_id': user_id}), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401

@app.route('/api/profile/<user_id>', methods=['GET', 'POST'])
@login_required
def api_profile(user_id):
    if request.method == 'GET':
        profile = user_manager.get_user_profile(user_id)
        if profile:
            # Only return safe data (excluding password hash)
            safe_profile = {k: v for k, v in profile.items() if k != 'password_hash'}
            return jsonify(safe_profile), 200
        return jsonify({'success': False, 'message': 'User not found.'}), 404
        
    elif request.method == 'POST':
        data = request.json
        success, message = user_manager.update_user_profile(user_id, data)
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'success': False, 'message': message}), 400

# --- API Endpoints: Transaction Upload & Analysis ---

@app.route('/api/upload_transactions/<user_id>', methods=['POST'])
@login_required
def api_upload_transactions(user_id):
    """
    Accepts a CSV file, parses it, and saves the transaction data.
    FIX: It now checks if the category is an expense type and negates the amount
    if the amount is positive, assuming a non-standard CSV format.
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part in the request.'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file.'}), 400

    if file and file.filename.endswith('.csv'):
        # 1. Read and Parse CSV using standard Python 'csv' module
        try:
            # Read file content into a string buffer (required for the csv module)
            stream = StringIO(file.stream.read().decode("UTF8"))
            reader = csv.DictReader(stream)
            
            data_to_save = []
            
            # Check for required headers
            headers = [h.strip().lower().replace(' ', '_') for h in reader.fieldnames]
            required_cols = ['date', 'description', 'amount']
            
            if not all(col in headers for col in required_cols):
                 return jsonify({'success': False, 'message': 'CSV must contain headers: Date, Description, and Amount (case-insensitive).'}), 400
            
            # Map headers to standard keys
            header_map = {}
            for header in headers:
                if 'date' in header:
                    header_map['date'] = header
                elif 'description' in header:
                    header_map['description'] = header
                elif 'amount' in header:
                    header_map['amount'] = header
                elif 'category' in header:
                    header_map['category'] = header

            # Process each row
            for row in reader:
                try:
                    category = row.get(header_map.get('category', 'category'), 'Uncategorized').strip()
                    raw_amount = float(row.get(header_map.get('amount', 'amount')) or 0)
                    
                    # --- CRITICAL FIX START ---
                    final_amount = raw_amount
                    
                    # If the amount is positive AND the category is an expense type, make it negative.
                    # This corrects for CSVs that only use positive numbers for all transactions.
                    if final_amount > 0 and category.lower() in EXPENSE_CATEGORIES:
                        final_amount = -abs(final_amount)
                    # If the category is 'savings', ensure it is positive (income/transfer)
                    elif category.lower() == 'savings' and final_amount < 0:
                        final_amount = abs(final_amount)
                    # --- CRITICAL FIX END ---
                        
                    transaction = {
                        'date': row.get(header_map.get('date', 'date')) or row.get('Date'),
                        'description': row.get(header_map.get('description', 'description')) or row.get('Description'),
                        'amount': final_amount, # Use the corrected amount
                        'category': category
                    }
                    data_to_save.append(transaction)
                except ValueError:
                    # Skip or log rows with invalid amount data
                    print(f"Skipping row due to invalid amount: {row}")
                    continue
            
            # 2. Save Parsed Data to User-Specific JSON File
            filepath = f'{user_id}_transactions.json'
            write_json(filepath, data_to_save)
            
            return jsonify({
                'success': True, 
                'message': f'Successfully uploaded and parsed CSV.',
                'count': len(data_to_save)
            }), 200

        except Exception as e:
            print(f"Error during CSV processing: {e}")
            return jsonify({'success': False, 'message': f'Error processing CSV file: {e}'}), 500
    
    return jsonify({'success': False, 'message': 'Invalid file type. Please upload a CSV file.'}), 400


@app.route('/api/generate_analysis/<user_id>', methods=['POST'])
@login_required
def api_generate_analysis(user_id):
    """
    Handles the request to generate the AI financial analysis.
    This uses the deterministic stub defined above, now returning more chart data.
    """
    return jsonify(generate_ai_analysis_stub(user_id)), 200


# --- API Endpoints: Chatbot (No Changes Required) ---

@app.route('/api/chats/<user_id>', methods=['GET', 'POST'])
@login_required
def api_chat_list(user_id):
    """GET: Returns a list of all chat names for the user. POST: Creates a new chat."""
    if request.method == 'GET':
        chat_names = chat_manager.get_chat_names(user_id)
        return jsonify(chat_names), 200
        
    elif request.method == 'POST':
        data = request.json
        chat_name = data.get('chat_name')
        if not chat_name:
            return jsonify({'success': False, 'message': 'Chat name is required.'}), 400
            
        success, message = chat_manager.create_chat(user_id, chat_name)
        if success:
            return jsonify({'success': True, 'message': message}), 201
        return jsonify({'success': False, 'message': message}), 409

@app.route('/api/chats/<user_id>/<chat_name>', methods=['GET'])
@login_required
def api_chat_history(user_id, chat_name):
    """GET: Returns the message history for a specific chat."""
    history = chat_manager.get_chat_history(user_id, chat_name)
    return jsonify(history), 200

@app.route('/api/chats/<user_id>/<old_name>/rename', methods=['POST'])
@login_required
def api_chat_rename(user_id, old_name):
    """POST: Renames an existing chat."""
    data = request.json
    new_name = data.get('new_name')
    
    if not new_name:
        return jsonify({'success': False, 'message': 'New chat name is required.'}), 400
        
    success, message = chat_manager.rename_chat(user_id, old_name, new_name)
    if success:
        return jsonify({'success': True, 'message': message}), 200
    return jsonify({'success': False, 'message': message}), 400


@app.route('/api/chats/<user_id>/<chat_name>/message', methods=['POST'])
@login_required
def api_chat_message(user_id, chat_name):
    """POST: Sends a user message, receives a bot response, and saves both."""
    data = request.json
    message_content = data.get('content')
    
    if not message_content:
        return jsonify({'success': False, 'message': 'Message content is required.'}), 400
        
    # 1. Save user message
    chat_manager.add_message(user_id, chat_name, 'user', message_content)
    
    # 2. Get AI response (Gemini with fallback)
    ai_response = get_ai_chat_response(user_id, chat_name, message_content)
    
    if ai_response.get('success'):
        bot_content = ai_response['content']
        # 3. Save bot response
        chat_manager.add_message(user_id, chat_name, 'bot', bot_content)
        
        return jsonify({'success': True, 'role': 'bot', 'content': bot_content}), 200
    else:
        return jsonify(ai_response), 500

if __name__ == '__main__':
    # Ensure the main data directory exists
    Path('data').mkdir(exist_ok=True)
    app.run(debug=True)
