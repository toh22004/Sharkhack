# Import necessary libraries
from flask import Flask, request, jsonify, render_template, redirect, session, flash
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import json # For parsing potential JSON responses from AI
import logging # For better logging
import datetime
#import pytz # For timezone handling
import math # For math operations
import re # For regex operations
import os # For environment variables (if needed)
import hashlib
import binascii

# Import your custom AI Service
from ai_service import AIService

# --- Constants for Normalization ---
ALLOWED_HEALTH_KEYWORDS = [
    "hypertension", "diabetes_type1", "diabetes_type2", "high_cholesterol",
    "kidney_disease", "ibs", "celiac_disease", "gerd", "acid_reflux",
    "knee_pain", "back_pain", "shoulder_injury", "hip_pain", "wrist_pain",
    "arthritis", "osteoporosis", "asthma", "copd", "heart_disease",
    "arrhythmia", "post_surgery_recovery", "pregnancy", "postpartum",
    "migraine", "anemia", "thyroid_issue", "autoimmune_disorder", "chronic_fatigue",
    "other_joint_pain", "other_cardiovascular", "other_metabolic", "other_respiratory",
    "other_musculoskeletal", "other_digestive" # Catch-all categories
]

ALLOWED_DIETARY_KEYWORDS = [
    "vegetarian", "vegan", "pescatarian", "gluten_free", "lactose_intolerant",
    "dairy_free", "low_carb", "keto", "paleo", "low_fodmap", "low_sodium",
    "low_sugar", "halal", "kosher", "fasting", "intermittent_fasting",
    "nutrient_deficiency", # e.g., iron, B12
    "other_restriction"
]

ALLOWED_ALLERGY_KEYWORDS = [
    "peanuts", "tree_nuts", "milk", "eggs", "soy", "wheat", "fish", "shellfish",
    "sesame", "mustard", "celery", "sulfites", "lupin", "molluscs",
    "corn", "nightshades", "citrus", "seeds", # Common groups
    "other_allergy"
]
# --- End Constants ---

# --- Helper Functions ---
def calculate_age(dob_str):
    """Calculates age from a MMDDYY string."""
    if not dob_str or len(dob_str) != 6:
        return 'N/A'
    try:
        # Parse the MMDDYY string
        birth_month = int(dob_str[0:2])
        birth_day = int(dob_str[2:4])
        birth_year_short = int(dob_str[4:6])

        # Estimate the full year (assume 20xx if short year <= current year short, else 19xx)
        current_year_short = datetime.datetime.now().year % 100
        if birth_year_short <= current_year_short:
            birth_year = 2000 + birth_year_short
        else:
            birth_year = 1900 + birth_year_short
            
        birth_date = datetime.datetime(birth_year, birth_month, birth_day)
        today = datetime.datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except ValueError:
        logging.error(f"Could not parse DOB string: {dob_str}")
        return 'N/A'

def normalize_user_text_input(ai_service, raw_text_list, input_type, allowed_keywords):
    """
    Uses AI to normalize free-form user text into standardized keywords.

    Args:
        ai_service: The AI service instance.
        raw_text_list: A list of strings containing the user's raw input.
        input_type: String describing the type ('health concerns', 'dietary restrictions', 'allergies').
        allowed_keywords: A list of standardized keywords the AI should map to.

    Returns:
        A list of matched standardized keywords, or an empty list if error/no match.
    """
    if not isinstance(raw_text_list, list) or not raw_text_list:
        return [] # Return empty if no input

    # Filter out empty strings
    filtered_raw_text = [text.strip() for text in raw_text_list if text.strip()]
    if not filtered_raw_text:
        return []

    # Create a numbered list of allowed keywords for the prompt
    keyword_list_str = "\n".join([f"{i+1}. {kw}" for i, kw in enumerate(allowed_keywords)])

    prompt = f"""
    Analyze the following user-provided text describing their {input_type}.
    Identify any conditions/restrictions/allergies mentioned that are relevant to diet or exercise planning.
    Map the user's description to the *most appropriate* keywords from the provided standardized list ONLY.
    Output *only* a valid JSON list containing the matched standardized keywords.
    If no relevant keywords from the list match the user's description, or if the description is too vague or unrelated (e.g., "feeling tired"), output an empty JSON list: [].
    Do not include keywords that are not explicitly supported by the user's text.

    Allowed Standardized Keywords:
    {keyword_list_str}

    User Text Input List:
    {json.dumps(filtered_raw_text)}

    Required Output Format: Valid JSON list of strings (e.g., ["keyword1", "keyword2"])
    JSON Output:
    """
    logging.info(f"Sending prompt to AI for normalizing {input_type}...")
    response_text = ai_service.generate_response(prompt)
    logging.info(f"Received normalization response for {input_type}.")

    try:
        # Clean potential markdown ```json ... ``` or just ``` around the JSON
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
        elif cleaned_response.startswith("```"):
             cleaned_response = cleaned_response[3:]
             if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

        # Further cleaning: Remove potential leading/trailing non-JSON characters just in case
        # Find the first '{' or '[' and the last '}' or ']'
        start_index = -1
        end_index = -1
        for i, char in enumerate(cleaned_response):
            if char in '[{':
                start_index = i
                break
        for i in range(len(cleaned_response) - 1, -1, -1):
            if cleaned_response[i] in ']}':
                end_index = i
                break

        if start_index != -1 and end_index != -1 and start_index <= end_index:
            json_str = cleaned_response[start_index : end_index + 1]
        else:
             # If we can't find valid JSON delimiters, assume it's not JSON
             raise json.JSONDecodeError("Could not find JSON delimiters", cleaned_response, 0)


        normalized_list = json.loads(json_str)

        # Validate: Ensure it's a list and all items are in the allowed list
        if isinstance(normalized_list, list):
            # Filter out any keywords the AI might have hallucinated
            valid_normalized_list = [kw for kw in normalized_list if isinstance(kw, str) and kw in allowed_keywords]
            logging.info(f"Successfully normalized {input_type}: {valid_normalized_list}")
            return valid_normalized_list
        else:
            logging.warning(f"Normalization AI for {input_type} did not return a list. Raw response: {response_text}")
            return []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON from AI normalization for {input_type}. Error: {e}. Raw response: {response_text}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error during AI normalization for {input_type}: {e}. Raw response: {response_text}")
        return []

def calculate_dietary_goals(user_data):
    """
    Calculates estimated dietary goals based on user profile.
    Requires: weight (lbs), height_inches, dob (MMDDYY), sex ('male'/'female'),
              activity_level, fitness_goal.
    Returns a dictionary with calculated goals or None if the data is insufficient.
    """
    # Required fields now include normalized data implicitly if needed for calc
    required_fields = ['weight', 'height_inches', 'dob', 'sex', 'activity_level', 'fitness_goal']
    # Check basic fields first
    if not user_data or not all(field in user_data and user_data[field] is not None for field in required_fields):
        logging.warning(f"Insufficient base data to calculate dietary goals for user {user_data.get('username')}.")
        return None
    
    try:
        weight_lbs = float(user_data['weight'])
        height_inches = float(user_data['height_inches'])
        dob = user_data['dob']
        sex = user_data['sex'].lower()
        activity_level = user_data['activity_level'] 
        fitness_goal = user_data['fitness_goal']
        health_conditions = user_data.get('health_conditions', [])

        age = calculate_age(dob)
        if age is None:
            logging.warning("Could not calculate age without valid age.")
            return None
        
        # --- Get NORMALIZED health concerns ---
        health_concerns_normalized = user_data.get('health_concerns_normalized', [])

        # --- Conversions ---
        weight_kg = weight_lbs * 0.453592
        height_cm = height_inches * 2.54

        # --- BMR (Mifflin-St Jeor Equation) ---
        if sex == 'male':
            bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
        elif sex == 'female':
            bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
        else:
            # Use an average if sex is not specified or different
            bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) -78 # Midpoint 
            logging.warning(f"Sex specified as '{sex}'. Using average BMR calculation.")
        
        # --- TDEE (Total Daily Energy Expenditure) ---
        activity_multiplier = {
            'sedentary': 1.2,
            'lightly_active': 1.375,
            'moderately_active': 1.55,
            'very_active': 1.725,
            'extra_active': 1.9
        }
        tdee = bmr * activity_multiplier.get(activity_level, 1.2) # Default to sedentary if not found

        # --- Calorie Goal Adjustment ---
        calorie_goal = tdee
        if fitness_goal == 'lose_weight':
            calorie_goal -= 500 # Aim for ~1lb loss per week
            # Safety net: Don't go below BMR or general minimums
            min_calories = 1500 if sex == 'male' else 1200
            calorie_goal = max(calorie_goal, bmr * 0.9, min_calories)
        elif fitness_goal == 'gain_muscle':
            calorie_goal += 300

        # --- Protein Goal ---
        # Adjust protein based on goal (g/kg of body weight)
        if fitness_goal == 'gain_muscle':
            protein_factor = 1.8 # Higher end for muscle gain
        elif activity_level in ['very_active', 'extra_active']:
            protein_factor = 1.6 # Higher end for very active
        else:
            protein_factor = 1.2 # General active population
        protein_grams = protein_factor * weight_kg

        # --- Sodium Goal ---
        # Basic guideline, lower if high blood pressure is a concern
        sodium_mg = 2300
        # Check the normalized list for relevant keywords
        if "hypertension" in health_concerns_normalized or "heart_disease" in health_concerns_normalized or "kidney_disease" in health_concerns_normalized:
             sodium_mg = 1500
             logging.info(f"Adjusting sodium goal lower due to normalized health concerns for {user_data.get('username')}: {health_concerns_normalized}")

        # --- Water Goal ---
        # Guideline: ~half body weight (lbs) in oz, convert to liters
        water_liters = (weight_lbs / 2) * 0.0295735 # oz to liters conversion factor

        goals = {
            "calories": int(round(calorie_goal)),
            "protein_grams": int(round(protein_grams)),
            "sodium_mg": int(round(sodium_mg)),
            "water_liters": round(water_liters, 1),
            #"last_calculated": datetime.datetime.now(pytz.utc)
        }
        logging.info(f"Calculated dietary goals for {user_data.get('username')}: {goals}")
        return goals

    except (ValueError, TypeError, KeyError) as e:
        logging.error(f"Error calculating dietary goals for {user_data.get('username')}: {e}. User data subset: {{'weight': user_data.get('weight'), 'height': user_data.get('height_inches')}}")
        return None

def get_user_context_for_ai(username):
    """Helper to fetch user data relevant for AI prompts, including raw and normalized."""
    user_data = users_collection.find_one({"username": username})
    if not user_data:
        return None

    context = {
        'username': username,
        'age': calculate_age(user_data.get('dob')),
        'sex': user_data.get('sex', 'N/A'),
        'weight': user_data.get('weight', 'N/A'),
        'height_inches': user_data.get('height_inches', 'N/A'),
        'activity_level': user_data.get('activity_level', 'N/A'),
        'fitness_goal': user_data.get('fitness_goal', 'N/A'),
        # Raw Data
        'health_concerns_raw': user_data.get('health_concerns_raw', []),
        'dietary_restrictions_raw': user_data.get('dietary_restrictions_raw', []),
        'allergies_raw': user_data.get('allergies_raw', []),
        # Normalized Data
        'health_concerns_normalized': user_data.get('health_concerns_normalized', []),
        'dietary_restrictions_normalized': user_data.get('dietary_restrictions_normalized', []),
        'allergies_normalized': user_data.get('allergies_normalized', []),
        # Other data
        'dietary_goals': user_data.get('dietary_goals'),
        'workout_history': user_data.get('workout_history', [])
    }
    # ... (calculate height_str as before) ...
    return context

# --- Configuration ---
# Configure logging
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message))s')

app = Flask(__name__)
app.secret_key = "TestKey"
ai_service = AIService()

uri = "mongodb+srv://hetony2005:1111@users.jdmvwvu.mongodb.net/?appName=Users"

# --- Configuration ---
SALT_LENGTH = 16  # Length of the salt in bytes (16 is common)
HASH_ALGORITHM = 'sha256' # Algorithm for PBKDF2
ITERATIONS = 1000

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# --- Routes ---
db = client["GymBro"]
users_collection = db["Users"]

#The Main Page
# --- Password Hashing Function ---
def hash_password(passw):
    """Hashes a password using PBKDF2 with a random salt, returns hex strings."""
    salt_bytes = os.urandom(SALT_LENGTH)
    # PBKDF2 HMAC needs bytes for password and salt
    hashed_password_bytes = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        passw.encode('utf-8'), # Password as bytes
        salt_bytes,               # Salt as bytes
        ITERATIONS
    )
    # Convert salt and hash bytes to hex strings for storage
    salt_hex = salt_bytes.hex()
    hashed_password_hex = hashed_password_bytes.hex()
    return salt_hex, hashed_password_hex

# --- Password Verification Function ---
def check_password(username, input_password):
    """Checks if the input password matches the stored hash for the username."""
    user = users_collection.find_one({"username": username})
    if user:
        # Retrieve stored salt and hash (now expected to be hex strings)
        stored_salt_hex = user.get("salt")
        stored_hash_hex = user.get("hashed_password")

        if not stored_salt_hex or not stored_hash_hex:
             print(f"Error: User '{username}' record is missing salt or hashed_password.")
             return False

        try:
            # Convert the stored hex salt back to bytes
            stored_salt_bytes = bytes.fromhex(stored_salt_hex)
        except (ValueError, TypeError) as e:
             print(f"Error: Could not decode salt for user '{username}'. Invalid hex stored? Error: {e}")
             return False

        # Hash the input password using the *retrieved and decoded* salt
        input_hash_bytes = hashlib.pbkdf2_hmac(
            HASH_ALGORITHM,
            input_password.encode('utf-8'),
            stored_salt_bytes, # Use the salt converted back to bytes
            ITERATIONS
        )

        # Convert the newly calculated hash to hex to compare with the stored hex string
        input_hash_hex = input_hash_bytes.hex()

        # Compare the hex strings
        if input_hash_hex == stored_hash_hex:
            print(f"Password correct for user '{username}'!")
            return True
        else:
            print(f"Incorrect password for user '{username}'!")
            return False
    else:
        print(f"User '{username}' not found!")
        return False
#This is the default page, it will check if the user is logged in and will redirect to dashboard and if not, redirect to the login screen.
@app.route("/")
def check_user():
    if "user" in session:
        return redirect("/dashboard")
    else:
        return redirect("/login")

#The Register page, should be an option from the main page. Upon successful signup, redirects to main page
@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST': #Upon a submission of form
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        dob = request.form.get('dob')#dateofbirth
        sex = request.form.get('sex')
        weight = request.form.get('weight')#lb
        height_inches = request.form.get('height_inches') # New field for height
        
        activity_level = request.form.get('activity_level') # 5 options: sedentary, lightly_active, moderately_active, very_active, extra_active
        fitness_goal = request.form.get('fitness_goal')# gain_muscle, lose_weight, maintain_weight
        # --- get RAW free text input ---
        health_concerns_raw_text = request.form.get('health_concerns_raw', '')
        dietary_restrictions_raw_text = request.form.get('dietary_restrictions_raw', '')
        allergies_raw_text = request.form.get('allergies_raw','')

        health_concerns_raw = [line.strip() for line in health_concerns_raw_text.splitlines() if line.strip()]
        dietary_restrictions_raw = [line.strip() for line in dietary_restrictions_raw_text.splitlines() if line.strip()]
        allergies_raw = [line.strip() for line in allergies_raw_text.splitlines() if line.strip()]
        
        salt_hex, hashed_pass = hash_password(password)

        now = datetime.datetime.now()
        formatted_date = now.strftime("%m%d%y")

        newUser = {
            "username": username,
            "email": email,
            "salt": salt_hex,
            "hashed_password": hashed_pass,
            "dob": dob,
            "sex": sex,
            "weight": weight,
            "join_date": formatted_date,
            "max_streak":0,
            "height_inches":height_inches, 
            "fitness_goal": fitness_goal,
            "activity_level": activity_level
        
            # --- Store RAW text ---
      #      "health_concerns_raw": health_concerns_raw,
      #      "dietary_restrictions_raw": dietary_restrictions_raw,
      #      "allergies_raw": allergies_raw,
            # --- Initalize Normalized fields as empty ---
      #      "health_conditions_normalized": [],
      #      "dietary_restrictions_normalized": [],
      #      "allergies_normalized": []
        }
        
        existingUser = users_collection.find_one({"username": newUser["username"]})
        if existingUser:
            flash("Username already exists. Please choose a different one.")
            return redirect("/login")
        else:
            users_collection.insert_one(newUser)#inserts this into the mongo database
        return redirect("/login") #return to main
    return render_template('register.html')


#The signin page, should be an option from the main page. Upon successful signin, redirect to ??? page
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Use the check_password function for validation
        if check_password(username, password):
            session["user"] = username  # Store username in session
            flash("Login successful!", "success")
            return redirect("/dashboard")  # Redirect to a protected page
        else:
            # Determine why check_password failed
            user = users_collection.find_one({"username": username})
            if user:
                # User exists, but password was wrong
                flash("Incorrect password. Try again.", "error")
                return redirect('/login')
            else:
                # User doesn't exist
                flash("User not found. Please register.", "error")
                return redirect('/register')

    return render_template('login.html')

#Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.")
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    # Optionally, fetch any common data for the dashboard
    return render_template("dashboard.html")

@app.route("/dashboard/profile")
def dashboard_profile():
    if "user" not in session:
        flash("You need to log in first.", "error")
        return redirect("/login")
    username = session["user"]
    user = users_collection.find_one({"username": username})
    if not user:
        flash("User not found.", "error")
        session.pop("user", None)  # Clear session if user not found
        return redirect("/login")
    if request.method == 'POST':
        pass
    return render_template("dashboard_profile.html", user=user)

@app.route("/dashboard/workout")
def dashboard_workout():
    if "user" not in session:
        return redirect("/login")
    # Add logic to fetch workout data if needed
    return render_template("dashboard_workout.html")

@app.route("/dashboard/diet")
def dashboard_diet():
    if "user" not in session:
        return redirect("/login")
    # Add logic to fetch diet info if needed
    return render_template("dashboard_diet.html")

@app.route("/dashboard/about")
def dashboard_about():
    if "user" not in session:
        return redirect("/login")
    # Add logic for about information if needed
    return render_template("dashboard_about.html")


@app.route('/api/ai/assist', methods=['GET', 'POST'])
def ai_assist():
    """
    General AI assistance endpoint. Handles user messages, incorporating context.
    Adapted to include empathetic response if venting is detected (inspired by process_venting_message).
    """
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'Missing message in request body'}), 400
    
    username = session["user"]

    # --- Get Full User Context ---
    user_context = get_user_context_for_ai(username)
    # Use profile context primarily, override from request if needed
    level = data.get('level', user_context.get('activity_level', 'beginner'))
    goal = data.get('goal', user_context.get('fitness_goal', 'general fitness'))
    performance = data.get('performance', 'average') # Example additional context from request
    user_input = data.get('message')

    '''
    # Old code
    # Extract individual context variables from the request
    level = data.get('level', 'beginner')
    goal = data.get('goal', 'general fitness')
    performance = data.get('performance', 'average')
    # Get any additional context that might be provided
    additional_context = {k: v for k, v in data.items() if k not in ['message', 'level', 'goal', 'performance']}
    '''
    
    # Build a fitness-specific prompt, now with added empathy instruction
    prompt = f"""
    You are GymBro, a friendly and supportive fitness AI assistant. The user is interacting with you through a fitness app.

    User Profile & Context:
    - Username: {user_context['username']}
    - Age: {user_context['age']}
    - Sex: {user_context['sex']}
    - Weight: {user_context['weight']} lbs
    - Height: {user_context['height_str']}
    - Stated Activity Level/Experience: {level}
    - Stated Fitness Goal: {goal}
    - Reported Recent Workout Performance: {performance}

    --- Critical Constraints (Processed from User Input) ---
    - Normalized Health Conditions: {', '.join(user_context['health_concerns_normalized']) if user_context['health_concerns_normalized'] else 'None'}
    - Normalized Dietary Restrictions: {', '.join(user_context['dietary_restrictions_normalized']) if user_context['dietary_restrictions_normalized'] else 'None'}
    - Normalized Allergies: {', '.join(user_context['allergies_normalized']) if user_context['allergies_normalized'] else 'None'}

    --- Original User Input (For Nuance/Context Only) ---
    - Raw Health Input: {'; '.join(user_context['health_concerns_raw']) if user_context['health_concerns_raw'] else 'None'}
    - Raw Dietary Input: {'; '.join(user_context['dietary_restrictions_raw']) if user_context['dietary_restrictions_raw'] else 'None'}
    - Raw Allergy Input: {'; '.join(user_context['allergies_raw']) if user_context['allergies_raw'] else 'None'}
    -------------------------------------------------------

    - Calculated Dietary Goals (Optional Ref): {user_context.get('dietary_goals', 'Not calculated')}

    User's Message: "{user_input}"

    Your Task:
    1. Analyze the user's message and their full context (profile, goals, health info).
    2. If the user seems to be venting, expressing frustration, or feeling down (especially if mood is low), respond empathetically and supportively *first*. Acknowledge their feelings. Keep it concise and encouraging. Do not give medical advice.
    3. Address the user's specific question or statement with scientifically accurate fitness advice relevant to their context (level, goal, etc.).
    4. Maintain a supportive, encouraging, and friendly tone throughout.
    5. Keep responses concise but helpful (aim for 1-3 paragraphs).
    6. Avoid promoting unrealistic fitness standards. Focus on consistency, health, and well-being.
    7. **CRITICAL SAFETY/ADHERENCE:** Your response MUST strictly adhere to the constraints listed under "Normalized Health Conditions", "Normalized Dietary Restrictions", and "Normalized Allergies".
        - **Health:** Do NOT suggest exercises conflicting with normalized conditions (e.g., no high-impact for 'knee_pain', modify for 'back_pain', consider intensity for 'hypertension'/'heart_disease').
        - **Diet/Allergies:** Do NOT suggest foods/ingredients conflicting with normalized restrictions or allergies (e.g., no meat if 'vegetarian'/'vegan', no gluten if 'celiac_disease'/'gluten_free', strictly avoid listed 'allergies').
    8. **IMPORTANT: Format your entire response using simple HTML tags.** Use `<p>` for paragraphs, `<b>` or `<strong>` for bold text, `<i>` or `<em>` for italics, and `<ul>` with `<li>` for bullet points if needed. Use `<br>` for line breaks where appropriate *within* text blocks, but prefer `<p>` for separating distinct ideas. **Do not use Markdown formatting like *, **, or backticks.** Do not include `<html>`, `<head>`, or `<body>` tags.
    
    
    Example HTML structure:
    <p>It sounds like you're feeling a bit frustrated, and that's totally understandable!</p>
    <p>Regarding your question about squats for a <b>{level}</b> focusing on <b>{goal}</b>, here are a few tips:</p>
    <ul>
        <li>Focus on keeping your chest up.</li>
        <li>Ensure your knees track over your toes.</li>
    </ul>
    <p>Keep up the great work, consistency is key!</p>
    """
    logging.info(f"Sending prompt to AI for /assist: {prompt[:200]}...") # Log start of prompt
    response_text = ai_service.generate_response(prompt)
    logging.info("Received response from AI for /assist.")
    return jsonify({'response': response_text})

@app.route('/api/ai/generate-workout', methods=['POST'])
def generate_workout():
    """
    Generates a personalized workout plan using the detailed prompt structure.
    Attempts to return structured JSON if the AI provides it.
    """

    # --- Authentication Check ---
    if "user" not in session:
        return jsonify({'error': 'User not logged in'}), 401
    username = session["user"]
    # --- End Authentication Check ---

    user_context = get_user_context_for_ai(username)

    data = request.json
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    # --- Fetch User Data from DB ---
    user_data = users_collection.find_one({"username": username})
    user_age = 'N/A'
    user_sex = 'N/A'
    workout_history_summary = 'None available'

    if user_data:
        user_dob = user_data.get('dob')
        user_sex = user_data.get('sex', 'N/A')
        user_age = calculate_age(user_dob) # Use the helper function

        # Fetch and format workout history
        history_list = user_data.get('workout_history', [])
        if history_list: # Should be sorted newest first if using $push/$slice correctly
            summary_parts = []
            # Take the most recent few (e.g., last 3) for the summary to keep prompt concise
            
            for entry in history_list[:3]: # Limit summary to last 3 workouts
                 if not entry or not isinstance(entry, dict): 
                    continue
                 ts = entry.get('timestamp', 'Unknown time')
                 feedback = entry.get('feedback', {})

                 # First, get the workout plan data, handling if it's None or missing
                 workout_plan_data = entry.get('workout_plan') or {}
                 # Now, safely get the plan name from the workout_plan_data (which is now guaranteed to be a dict)
                 plan_name = workout_plan_data.get('plan_name', 'Unnamed Plan')

                 difficulty = feedback.get('difficulty_rating', 'N/A')
                 completed = feedback.get('completed', 'N/A')
                 notes = feedback.get('notes', '')

                 # Format timestamp nicely
                 ts_str = ts.strftime('%Y-%m-%d') if isinstance(ts, datetime.datetime) else str(ts)

                 summary_parts.append(
                     f"- {ts_str}: '{plan_name}' (Completed: {completed}, Difficulty: {difficulty}/10). Notes: '{notes[:50]}{'...' if len(notes)>50 else ''}'"
                 )
            if summary_parts:
                workout_history_summary = "\n".join(summary_parts)
            else:
                workout_history_summary = "No recent workout feedback recorded."

    else:
        logging.warning(f"Could not find profile data for user: {username}")
        # Proceed with defaults or return error? Let's proceed with defaults from request.

    # --- Extract goal/preferences from the current request ---
    experience_level = data.get('level', 'Beginner')
    goals = data.get('goal', 'General Fitness')
    category = data.get('equipment', 'Bodyweight')
    current_mood = data.get('mood', None)
    mood_context = data.get('mood_context', '')
    focus_area = data.get('focus', 'Full Body')
    duration = data.get('duration', 30)
    # Use weight/height from request if provided, otherwise try DB (optional)
    weight = data.get('weight', user_data.get('weight', 'N/A') if user_data else 'N/A')
    height_inches = data.get('height_inches', 'N/A') # Assuming height isn't stored currently

    # --- Construct the AI Prompt with fetched data ---
    prompt = f"""
    Generate a personalized workout plan for a user with the following profile:
    - Age: {user_age}
    - Sex: {user_sex}
    - Weight: {weight} lbs
    - Height: {height_inches} inches"
    - Experience Level: {experience_level}
    - Goals: {goals}
    - Desired Focus Area: {focus_area}
    - Desired Duration: Approximately {duration} minutes
    - Available Category/Equipment: {category}
    - Current Mood (1-10, 1=very bad, 10=very good): {current_mood if current_mood is not None else 'Not specified'}
    - Mood Context: {mood_context if mood_context else 'None'}
    - Interpreted Health Conditions (Normalized): {', '.join(user_context['health_concerns_normalized']) if user_context['health_concerns_normalized'] else 'None'}
    - Original Health Input (Raw): {'; '.join(user_context['health_concerns_raw']) if user_context['health_concerns_raw'] else 'None'}
    # --- Add similar lines for DIET and ALLERGIES (Normalized/Raw) if relevant for workout ---
    - Interpreted Dietary Restrictions (Normalized): {', '.join(user_context['dietary_restrictions_normalized']) if user_context['dietary_restrictions_normalized'] else 'None'}
    - Interpreted Allergies (Normalized): {', '.join(user_context['allergies_normalized']) if user_context['allergies_normalized'] else 'None'}

    Recent Workout History Summary (Last 3 Sessions, Newest First):
    {workout_history_summary}

    Constraints & Instructions:
    - Generate the workout plan in the specified JSON format ONLY.
    - The workout MUST be suitable for the user's profile (age, sex, experience), goals, equipment, focus, duration, and mood.
    - Leverage the recent workout history: If the user found recent workouts too easy/hard, adjust accordingly. If they skipped workouts or noted issues, consider that.
    - If mood is low (e.g., < 5), suggest a slightly less strenuous or shorter workout. Acknowledge this in 'mood_adjustment_note'.
    - Provide exercises with sets, reps/duration, rest periods, and concise form tips, especially for beginners.
    - Structure the output strictly according to the JSON format provided below.
    - Ensure the total estimated duration aligns roughly with the user's request.
    - **CRITICAL: Base safety modifications PRIMARILY on the 'Interpreted Health Conditions (Normalized)' list.** This list has been processed for reliability. Examples:
        - If 'knee_pain' or 'arthritis' (knee) is listed, AVOID high-impact (jumping, running), deep squats/lunges. Suggest alternatives like swimming, cycling (if appropriate), modified bodyweight exercises.
        - If 'back_pain' is listed, AVOID heavy spinal loading (heavy deadlifts/squats), high-impact, excessive twisting. Emphasize core stability (planks, bird-dog), controlled movements.
        - If 'hypertension' or 'heart_disease' is listed, AVOID holding breath (Valsalva), suggest gradual warm-ups/cool-downs, moderate intensity, monitor perceived exertion. Consult physician disclaimer is vital.
        - If 'shoulder_injury' is listed, AVOID overhead presses, push-ups (initially), suggest rows, band work, check range of motion.
    - Use the 'Original Health Input (Raw)' text for additional nuance or context if needed, but the *normalized list dictates the core safety constraints*.
    - Also consider 'Interpreted Dietary Restrictions' if relevant (e.g., potential energy level impacts of keto/fasting). Acknowledge allergies ('Interpreted Allergies') mainly for cross-contamination awareness if suggesting group classes, not typically direct workout modification.

    Required Output Format (JSON only):
    {{
      "plan_name": "Personalized Workout for {focus_area}",
      "estimated_duration_minutes": {duration},
      "focus": "{focus_area}",
      "health_consideration_note": "string (e.g., 'Modified exercise X due to normalized condition: knee_pain.' or 'Low-impact plan based on profile.')", # Emphasize it's based on normalized data
      "mood_adjustment_note": "string (e.g., 'Adjusted for lower energy based on mood.' or 'Slightly increased intensity based on recent feedback.' or '')",
      "warm_up": [
        {{"exercise": "string", "duration": "string (e.g., 60 seconds)", "reps": "string (optional)", "sets": "integer (optional)", "form_tip": "string (optional)"}}
      ],
      "main_workout": [
        {{"exercise": "string", "sets": "integer", "reps": "string (e.g., '10-12' or 'AMRAP')", "rest_seconds": "integer", "form_tip": "string (concise)"}}
      ],
      "cool_down": [
        {{"exercise": "string", "duration": "string (e.g., 30 seconds per side)", "form_tip": "string (optional)"}}
      ]
    }}
    """
    logging.info(f"Sending prompt to AI for /generate-workout: {prompt[:200]}...") # Log start of prompt
    response_text = ai_service.generate_response(prompt)
    logging.info("Received response from AI for /generate-workout.")

    # Attempt to parse if response looks like JSON, otherwise return text
    try:
        # Basic check if the response seems like JSON
        if response_text.strip().startswith("{"):
             # Attempt to remove markdown if present
            if response_text.strip().startswith("```json"):
                 response_text = response_text.strip()[7:-3].strip()

            update_json = json.loads(response_text)
            return jsonify({'updated_plan': update_json})
        else:
             # Return as plain text within the structure if not JSON
             return jsonify({'updated_plan': {'raw_response': response_text}})
    except json.JSONDecodeError:
        logging.warning("AI response for plan update was not valid JSON. Returning as text.")
        return jsonify({'updated_plan': {'error': 'Failed to parse plan update as JSON', 'raw_response': response_text}})
    except Exception as e:
        logging.error(f"Error processing AI response for plan update: {e}")
        return jsonify({'error': 'An unexpected error occurred processing the plan update'}), 500

@app.route('/api/ai/update-workout-plan', methods=['POST'])
def update_workout_plan():
    """
    Receives feedback on a completed workout, SAVES it to history,
    and asks the AI to suggest modifications for the next workout.
    """
    # --- Authentication Check ---
    if "user" not in session:
        return jsonify({'error': 'User not logged in'}), 401
    username = session["user"]
    # --- End Authentication Check ---

    data = request.json
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    # --- Get Full User Context ---
    user_context = get_user_context_for_ai(username)
    if not user_context:
         # Log warning but proceed with minimal context if profile fetch fails mid-session
         logging.warning(f"Could not retrieve full profile for {username} during workout update. Using defaults.")
         user_context = { # Minimal fallback
             'username': username, 'activity_level': 'Beginner', 'fitness_goal': 'General Fitness',
             'health_concerns_normalized': [], 'health_concerns_raw': [],
             # Include others if necessary for the prompt logic below
         }

    # Extract necessary info from request
    # 'current_plan' is the JSON of the workout the user *just finished*
    current_plan = data.get('current_plan', None)
    # 'feedback' contains user's input about the completed workout

    # Validate input
    #if not current_plan or not isinstance(current_plan, dict):
    #     return jsonify({'error': 'Missing or invalid "current_plan" in request body'}), 400
    #if not feedback or not isinstance(feedback, dict):
    #    return jsonify({'error': 'Missing or invalid "feedback" in request body'}), 400

    # Expected feedback keys (adjust as needed based on your frontend)
    completed_status = data.get('completed', 'Not specified')
    difficulty_rating = data.get('difficulty_rating', 'Not specified')
    notes = data.get('notes', '')

    # --- Save Workout History ---
    history_entry = {
        "timestamp": datetime.datetime.now(), # Use timezone-aware UTC time
        "workout_plan": current_plan, # The plan that was just done
        "completed": completed_status,
        "difficulty_rating": difficulty_rating,
        "notes": notes
        # Optionally add user context at the time of workout if needed
        # "user_context": {"level": data.get('level'), "goal": data.get('goal')}
    }

    try:
        result = users_collection.update_one(
            {"username": username},
            {
                "$push": {
                    "workout_history": {
                        "$each": [history_entry],
                        "$slice": -7 # Keep only the last 7 elements
                    }
                }
            }
        )
        if result.matched_count == 0:
             logging.warning(f"Attempted to save history for non-existent user: {username}")
             # Don't proceed if user doesn't exist
             return jsonify({'error': 'User profile not found for saving history'}), 404
        elif result.modified_count == 0 and result.upserted_id is None:
             # This might happen if the update didn't change anything, which is unlikely with $push
             # unless the document structure is wrong or there's a concurrent modification issue.
             logging.warning(f"Workout history might not have been saved for user {username}. Result: {result.raw_result}")
        else:
             logging.info(f"Saved workout history for user: {username}")

    except Exception as e:
        logging.error(f"Error saving workout history for {username}: {e}")
        # Decide if you should still proceed to get AI feedback or return an error
        return jsonify({'error': f'Failed to save workout history: {e}'}), 500
    # --- End Save Workout History ---


    # --- Prepare Prompt for AI (Suggesting next steps/plan) ---
    current_plan_str = json.dumps(current_plan, indent=2) # Pretty print for the prompt

    prompt = f"""
    Task: Evolve the user's workout approach based on their recent performance feedback.

    User Profile Context (provided with feedback):
    - Experience Level: {user_context.get('activity_level', 'Beginner')}
    - Goal: {user_context.get('fitness_goal', 'General Fitness')}

    --- Critical Health Constraints (Processed from User Input) ---
    - Normalized Health Conditions: {', '.join(user_context['health_concerns_normalized']) if user_context['health_concerns_normalized'] else 'None'}

    --- Original Health Input (For Nuance/Context Only) ---
    - Raw Health Input: {'; '.join(user_context['health_concerns_raw']) if user_context['health_concerns_raw'] else 'None'}
    -----------------------------------------------------------

    Workout Plan Just Completed:
    ```json
    {current_plan_str}
    ```

    User's Feedback on Completed Workout:
    - Completed?: {data.get('completed', 'N/A')}
    - Difficulty Rating (1-10, 1=easy, 10=very hard): {data.get('difficulty_rating', 'N/A')}
    - User Notes/Feelings: {data.get('notes', '')}

    Instructions:
    1. Analyze the completed plan and the user's feedback.
    2. Suggest specific progressions or regressions for the *next* workout. Consider difficulty, completion status, and user notes.
    3. Keep suggestions aligned with the user's goal and experience level.
    4. **CRITICAL SAFETY:** Ensure ALL suggestions (progressions, regressions, alternative exercises) are safe and appropriate considering the "Normalized Health Conditions".
        - If feedback indicates pain or difficulty possibly related to a normalized condition (e.g., user note "knee hurt during lunges" and 'knee_pain' is normalized), suggest specific modifications (e.g., shorter range of motion, lighter weight, different exercise) or regressions.
        - Do NOT suggest exercises known to be risky for the listed normalized conditions, even as a progression.
    5. Use the "Raw Health Input" only for context if the notes are ambiguous, but the normalized list dictates safety rules.
    6. **Output Format:** Generate a JSON object with two keys: "explanation" and "updated_plan".
       - "explanation": String with brief reasoning for the suggestions (use simple HTML: <p>, <b>, <ul>, <li>).
       - "updated_plan": This should be the *complete updated workout plan JSON* for the *next* session, following the same structure as the generate-workout output. If generating a full plan isn't feasible based only on feedback (e.g., need more user input), provide clear modification suggestions as an HTML string within this key.
    7. Ensure valid JSON output. No text outside the main JSON object.

    Example Output (Full Plan Update):
    ```json
    {{
      "explanation": "<p>Based on your feedback (difficulty: {difficulty_rating}), I've adjusted your next workout. Since you found it manageable, I've slightly increased reps.</p>",
      "updated_plan": {{
          "plan_name": "Progressed Workout for [Focus]",
          "estimated_duration_minutes": ...,
          "focus": "...",
          "mood_adjustment_note": "",
          "warm_up": [ ... ],
          "main_workout": [ ... updated exercises ... ],
          "cool_down": [ ... ]
        }}
    }}
    ```
    Example Output (Modification Suggestions):
    ```json
    {{
      "explanation": "<p>Based on your feedback (difficulty: {data.get('difficulty_rating')}) and noting your normalized condition '[Example Condition if Any]', I recommend modifying [Exercise].</p>", # <<< FIXED LINE
      "updated_plan": "<p><b>Next Workout Suggestions:</b></p><ul><li>Reduce reps for [Exercise] to X-Y.</li><li>Substitute [Exercise] with [Safer Alternative like X].</li><li>Focus on controlled movement for [...].</li></ul>"
    }}
    ```
    """

    logging.info(f"Sending prompt to AI for /update-workout-plan for user {username}: {prompt[:200]}...")
    response_text = ai_service.generate_response(prompt)
    logging.info(f"Received response from AI for /update-workout-plan for user {username}.")

    # --- Process AI Response ---
    try:
        # Clean potential markdown
        if response_text.strip().startswith("```json"):
             response_text = response_text.strip()[7:-3].strip()
        elif response_text.strip().startswith("{"):
            response_text = response_text.strip()
        else:
            logging.error(f"AI response for plan update was not JSON for user {username}. Response: {response_text[:100]}")
            # Return explanation but indicate plan couldn't be parsed
            return jsonify({
                'explanation': '<p>AI response received, but the updated plan format was invalid.</p>',
                'updated_plan': {'error': 'Failed to parse plan update as JSON', 'raw_response': response_text}
            })

        update_json = json.loads(response_text)
        # Validate the structure of the AI response if possible
        if "explanation" not in update_json or "updated_plan" not in update_json:
             logging.warning(f"AI response for plan update missing required keys for user {username}. Response: {update_json}")
             return jsonify({
                'explanation': '<p>AI response is missing expected structure.</p>',
                'updated_plan': {'error': 'AI response format incorrect', 'raw_response': update_json}
            })

        # Return the structured JSON from the AI
        return jsonify(update_json)

    except json.JSONDecodeError:
        logging.warning(f"AI response for plan update was not valid JSON for user {username}. Returning raw. Response: {response_text[:500]}")
        return jsonify({
             'explanation': '<p>AI response received, but it was not valid JSON.</p>',
             'updated_plan': {'error': 'Failed to parse plan update as JSON', 'raw_response': response_text}
         })
    except Exception as e:
        logging.error(f"Error processing AI response for plan update for user {username}: {e}")
        return jsonify({'error': 'An unexpected error occurred processing the plan update'}), 500

@app.route('/api/ai/generate-meal-suggestion', methods=['POST'])
def generate_meal_suggestion():
    """Generates a meal suggestion strictly adhering to normalized diet/allergy constraints."""
    if "user" not in session:
        return jsonify({'error': 'User not logged in'}), 401
    username = session["user"]

    # --- Get Full User Context ---
    user_context = get_user_context_for_ai(username)
    if not user_context: return jsonify({'error': 'Could not retrieve user profile'}), 404
    if not user_context.get('dietary_goals'): return jsonify({'error': 'Dietary goals not calculated.'}), 400

    # Extract goals and constraints
    goals = user_context['dietary_goals']
    # --- Use Normalized Data ---
    health_concerns = user_context['health_concerns_normalized']
    restrictions = user_context['dietary_restrictions_normalized']
    allergies = user_context['allergies_normalized']
    # --- Also get Raw Data for context ---
    health_raw = user_context['health_concerns_raw']
    restrictions_raw = user_context['dietary_restrictions_raw']
    allergies_raw = user_context['allergies_raw']

    data = request.json
    meal_type = data.get('meal_type', 'any')

    prompt = f"""
    Generate a simple meal suggestion for a user.

    User Profile Highlights:
    - Goal: {user_context.get('fitness_goal', 'N/A')}

    --- Critical Dietary Constraints (Processed from User Input) ---
    - Normalized Dietary Restrictions: {', '.join(restrictions) if restrictions else 'None'}
    - Normalized Allergies: {', '.join(allergies) if allergies else 'None'}
    - Normalized Health Conditions (Consider for Diet): {', '.join(health_concerns) if health_concerns else 'None'}

    --- Original User Input (For Nuance/Context Only) ---
    - Raw Dietary Input: {'; '.join(restrictions_raw) if restrictions_raw else 'None'}
    - Raw Allergy Input: {'; '.join(allergies_raw) if allergies_raw else 'None'}
    - Raw Health Input: {'; '.join(health_raw) if health_raw else 'None'}
    -------------------------------------------------------

    Approximate Daily Targets (for context):
    - Calories: {goals.get('calories', 'N/A')} kcal
    - Protein: {goals.get('protein_grams', 'N/A')} g
    - Sodium: < {goals.get('sodium_mg', 'N/A')} mg

    Request:
    - Suggest one meal idea suitable for: {meal_type.capitalize()}
    - **CRITICAL ADHERENCE:** The meal MUST strictly respect ALL "Normalized Dietary Restrictions" and "Normalized Allergies". Do NOT include ingredients related to these lists (e.g., avoid peanuts if 'peanuts' allergy, avoid dairy if 'lactose_intolerant'/'dairy_free' restriction).
    - **HEALTH CONSIDERATIONS:** The meal should also be appropriate for relevant "Normalized Health Conditions" (e.g., lower sugar/simple carbs if 'diabetes_type2', lower sodium if 'hypertension'/'kidney_disease', low fat if 'high_cholesterol' - check common dietary advice for these).
    - Use the "Original User Input" sections *only* for context if needed, but the *normalized lists dictate the absolute food constraints*.
    - Provide meal name, brief description/ingredients, rough estimates for calories/protein per serving.
    - Keep it simple and practical.

    Required Output Format (Simple HTML):
    <h4>Suggested Meal ({meal_type.capitalize()}): [Meal Name]</h4>
    <p><b>Description:</b> [Brief description, key ingredients, simple prep idea].</p>
    <p><b>Why it fits Constraints:</b> [1 sentence confirming adherence, e.g., 'This option is vegan and gluten-free, avoiding listed restrictions/allergies.']</p>
    <p><b>Approx. Nutrition (per serving):</b></p>
    <ul><li>Calories: ~ [Number] kcal</li><li>Protein: ~ [Number] g</li></ul>
    <p><i>Note: Nutritional values are estimates. Adjust portions as needed.</i></p>
    Use only simple HTML tags: <h4>, <p>, <b>, <ul>, <li>, <i>. No Markdown.
    """

    logging.info(f"Sending prompt to AI for /generate-meal-suggestion for {username} ({meal_type})...")
    response_text = ai_service.generate_response(prompt)
    logging.info(f"Received response from AI for /generate-meal-suggestion for {username}.")

    return jsonify({'suggestion': response_text})

@app.route('/api/ai/analyze-meal', methods=['POST'])
def analyze_meal():
    """Estimates nutrition, uses normalized context to flag potential issues."""
    user_context = {} # Default for anonymous
    if "user" in session:
        username = session["user"]
        full_user_context = get_user_context_for_ai(username)
        if full_user_context:
            user_context = full_user_context # Use full context if available
            logging.info(f"Analyzing meal for user: {username}")
        else:
             logging.warning(f"Could not get profile for {username}, analyzing meal without context.")
             user_context['username'] = username # Keep username if possible
    else:
        logging.info("Analyzing meal for anonymous user.")

    data = request.json
    if not data or 'meal_description' not in data:
        return jsonify({'error': 'Missing meal_description'}), 400
    meal_description = data.get('meal_description')

    # Get normalized constraints from context
    restrictions_norm = user_context.get('dietary_restrictions_normalized', [])
    allergies_norm = user_context.get('allergies_normalized', [])
    # Optional: Raw text for better AI understanding of the description itself
    restrictions_raw = user_context.get('dietary_restrictions_raw', [])
    allergies_raw = user_context.get('allergies_raw', [])


    prompt = f"""
    Estimate approximate calories (kcal) and protein (g) for the meal described below.
    Also, check if the meal description seems to contain ingredients that conflict with the user's known dietary constraints provided for context.

    Meal Description: "{meal_description}"

    --- User's Dietary Constraints (Processed/Normalized) ---
    - Restrictions: {', '.join(restrictions_norm) if restrictions_norm else 'None'}
    - Allergies: {', '.join(allergies_norm) if allergies_norm else 'None'}
    ---------------------------------------------------------
    --- Original User Dietary Input (Raw Context) ---
    - Raw Restrictions: {'; '.join(restrictions_raw) if restrictions_raw else 'None'}
    - Raw Allergies: {'; '.join(allergies_raw) if allergies_raw else 'None'}
    ---------------------------------------------------------


    Instructions:
    1. Provide estimates for calories and protein.
    2. **Analyze the "Meal Description"** against the **"Normalized Restrictions"** and **"Normalized Allergies"** lists.
    3. If the description clearly mentions an ingredient that conflicts with a normalized constraint (e.g., "cheese sandwich" when 'dairy_free' or 'lactose_intolerant' is listed; "peanut butter" when 'peanuts' allergy is listed), add a concise warning in the specified format. Use common sense for related ingredients (e.g., bread likely contains 'wheat'/'gluten').
    4. Do *not* add a warning if there's no clear conflict based on the description and normalized lists.
    5. Base the warning *only* on the normalized lists, not the raw input.

    Required HTML Output Format:
    <p>Estimated Calories: <b>[Number] kcal</b></p>
    <p>Estimated Protein: <b>[Number] g</b></p>
    <!-- Optional: Add ONE warning paragraph IF a conflict is detected -->
    <p><b>Potential Conflict Warning:</b> This meal description appears to contain [Ingredient/Type, e.g., 'Dairy', 'Gluten', 'Peanuts'] which may conflict with your listed normalized restriction/allergy: '[Matching Normalized Keyword]'.</p>
    <!-- End Optional Warning -->
    <p><i>Note: Estimates are approximate. Ingredient analysis depends on description accuracy.</i></p>
    Use only simple HTML tags. No Markdown.
    """
    logging.info(f"Sending prompt to AI for /analyze-meal: {prompt[:300]}...")
    response_text = ai_service.generate_response(prompt)
    logging.info("Received response from AI for /analyze-meal.")
    return jsonify({'analysis': response_text})

@app.route('/api/ai/check-form', methods=['POST'])
def check_form():
    """
    Provides feedback on exercise form based on user description.
    Uses a prompt inspired by 'explain_exercise_form'.
    """
    data = request.json
    if not data or 'exercise' not in data or 'form_description' not in data:
        return jsonify({'error': 'Missing exercise or form_description in request body'}), 400

    exercise_name = data.get('exercise')
    form_description = data.get('form_description')
    user_level = data.get('level', 'Beginner') # Include user level for context

    prompt = f"""
    Task: Analyze the user's description of their form for a specific exercise and provide constructive feedback.

    Exercise: {exercise_name}
    User's Experience Level: {user_level}
    User's Description of Their Form: "{form_description}"

    Instructions:
    1. Based *only* on the user's description, provide specific, actionable feedback. Identify potential issues mentioned or implied.
    2. List 2-3 common mistakes people make when performing '{exercise_name}', especially relevant to a {user_level}.
    3. Offer clear tips for improvement focusing on proper technique and body mechanics for '{exercise_name}'.
    4. Briefly mention key safety considerations for this exercise.
    5. Keep the response encouraging, concise, and easy to understand. Avoid jargon where possible.
    6. Remind the user that text-based feedback is limited and cannot replace visual assessment by a professional.
    7. **IMPORTANT: Format your entire response using simple HTML tags.** Use `<p>` for paragraphs, `<b>` or `<strong>` for emphasis (like exercise names, key terms), `<ul>` and `<li>` for bullet points, and potentially `<h4>` or `<h5>` for section headings (e.g., <h4>Feedback on Your Description:</h4>, <h4>Common Mistakes:</h4>, <h4>Tips for Improvement:</h4>, <h4>Safety Note:</h4>). **Do not use Markdown (*, **, `\\n`, etc.).** Do not include `<html>`, `<head>`, or `<body>` tags.
    
    Example HTML Structure:
    <h4>Feedback on Your Description:</h4>
    <p>Thanks for describing your {exercise_name} form! Based on what you wrote about [...], it sounds like [...]. One thing to watch out for might be [...].</p>
    <h4>Common Mistakes for {exercise_name} ({user_level}):</h4>
    <ul>
        <li>Mistake 1...</li>
        <li>Mistake 2...</li>
    </ul>
    <h4>Tips for Improvement:</h4>
    <ul>
        <li>Tip 1...</li>
        <li>Tip 2...</li>
    </ul>
    <h4>Safety Note:</h4>
    <p>Always remember to [...]. Listen to your body!</p>
    <p><i>Please note: This feedback is based solely on your text description. For precise form checks, consider consulting a qualified trainer.</i></p>
    """

    logging.info(f"Sending prompt to AI for /check-form: {prompt[:200]}...")
    response_text = ai_service.generate_response(prompt)
    logging.info("Received response from AI for /check-form.")
    return jsonify({'feedback': response_text})


# --- Run the Application ---
if __name__ == '__main__':
    # Run the Flask app in debug mode for development (auto-reloads, more detailed errors)
    # Disable debug mode in production!
    # Consider specifying host='0.0.0.0' to make it accessible on your network
    app.run(debug=True, port=5050) # Using port 5000 is common for Flask dev