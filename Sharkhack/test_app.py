# Import necessary libraries
from flask import Flask, request, jsonify, render_template, redirect, session, flash
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import json # For parsing potential JSON responses from AI
import logging # For better logging
import datetime
import pytz # For timezone handling

# --- Helper Function ---
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

# Import your custom AI Service
from ai_service import AIService

# --- Configuration ---
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = "TestKey"
ai_service = AIService()

uri = "mongodb+srv://hetony2005:1111@users.jdmvwvu.mongodb.net/?appName=Users"
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


@app.route("/")
def check_user():
    if "user" in session:
        username = session["user"]
        user = users_collection.find_one({"username": username})
        age = calculate_age(user.get("dob",""))
        return render_template("index.html", h_username=username, h_email=user.get("email", ""), h_age=age, h_weight=user.get("weight"), h_sex=user.get("sex")) 
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

        # Basic validation (add more robust validation as needed)
        if not all([username, email, password, dob, sex, weight]):
            flash("Please fill out all fields.")
            return render_template('register.html')

        now = datetime.datetime.now()
        formatted_date = now.strftime("%m%d%y")

        newUser = {
            "username": username,
            "email": email,
            "password": password,
            "dob": dob,
            "sex": sex,
            "weight": weight,
            "join_date": formatted_date
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
@app.route("/login", methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        existingUser = users_collection.find_one({"username": username})
        if existingUser:
            existingUserPass = existingUser["password"]
            if existingUserPass == password:
                session["user"] = username
                return redirect("/")
            else:
                flash("Incorrect Password, Try Again.")
                return redirect("/login")  
        else:
            return redirect("/register") #User doesn't exist, go to the signup page
    return render_template('login.html')

#Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.")
    return redirect("/login")
# --- AI Endpoints ---


@app.route('/api/ai/assist', methods=['GET', 'POST'])
def ai_assist():
    """
    General AI assistance endpoint. Handles user messages, incorporating context.
    Adapted to include empathetic response if venting is detected (inspired by process_venting_message).
    """
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'Missing message in request body'}), 400

    user_input = data.get('message')
    # Extract individual context variables from the request
    level = data.get('level', 'beginner')
    goal = data.get('goal', 'general fitness')
    performance = data.get('performance', 'average')
    # Get any additional context that might be provided
    additional_context = {k: v for k, v in data.items() if k not in ['message', 'level', 'goal', 'performance']}

    # Build a fitness-specific prompt, now with added empathy instruction
    prompt = f"""
    You are GymBro, a friendly and supportive fitness AI assistant. The user is interacting with you through a fitness app.

    Context Provided:
    - User's Stated Experience Level: {level}
    - User's Stated Fitness Goal: {goal}
    - User's Reported Recent Workout Performance: {performance}
    - Additional User Profile Data (if available): {additional_context}

    User's Message: "{user_input}"

    Your Task:
    1. Analyze the user's message and context.
    2. If the user seems to be venting, expressing frustration, or feeling down (especially if mood is low), respond empathetically and supportively *first*. Acknowledge their feelings. Keep it concise and encouraging. Do not give medical advice.
    3. Address the user's specific question or statement with scientifically accurate fitness advice relevant to their context (level, goal, etc.).
    4. Maintain a supportive, encouraging, and friendly tone throughout.
    5. Keep responses concise but helpful (aim for 1-3 paragraphs).
    6. Avoid promoting unrealistic fitness standards. Focus on consistency, health, and well-being.
    7. **IMPORTANT: Format your entire response using simple HTML tags.** Use `<p>` for paragraphs, `<b>` or `<strong>` for bold text, `<i>` or `<em>` for italics, and `<ul>` with `<li>` for bullet points if needed. Use `<br>` for line breaks where appropriate *within* text blocks, but prefer `<p>` for separating distinct ideas. **Do not use Markdown formatting like *, **, or backticks.** Do not include `<html>`, `<head>`, or `<body>` tags.
    
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
                 ts = entry.get('timestamp', 'Unknown time')
                 feedback = entry.get('feedback', {})
                 plan_name = entry.get('workout_plan', {}).get('plan_name', 'Unnamed Plan')
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
    height = data.get('height', 'N/A') # Assuming height isn't stored currently

    # --- Construct the AI Prompt with fetched data ---
    prompt = f"""
    Generate a personalized workout plan for a user with the following profile:
    - Age: {user_age}
    - Sex: {user_sex}
    - Weight: {weight} lbs
    - Height: {height} ft'in"
    - Experience Level: {experience_level}
    - Goals: {goals}
    - Desired Focus Area: {focus_area}
    - Desired Duration: Approximately {duration} minutes
    - Available Category/Equipment: {category}
    - Current Mood (1-10, 1=very bad, 10=very good): {current_mood if current_mood is not None else 'Not specified'}
    - Mood Context: {mood_context if mood_context else 'None'}

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

    Required Output Format (JSON only):
    {{
      "plan_name": "Personalized Workout for {focus_area}",
      "estimated_duration_minutes": {duration},
      "focus": "{focus_area}",
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

    # Extract necessary info from request
    # 'current_plan' is the JSON of the workout the user *just finished*
    current_plan = data.get('current_plan', None)
    # 'feedback' contains user's input about the completed workout
    feedback = data.get('feedback', None)

    # Validate input
    if not current_plan or not isinstance(current_plan, dict):
         return jsonify({'error': 'Missing or invalid "current_plan" in request body'}), 400
    if not feedback or not isinstance(feedback, dict):
        return jsonify({'error': 'Missing or invalid "feedback" in request body'}), 400

    # Expected feedback keys (adjust as needed based on your frontend)
    completed_status = feedback.get('completed', 'Not specified')
    difficulty_rating = feedback.get('difficulty_rating', 'Not specified')
    notes = feedback.get('notes', '')

    # --- Save Workout History ---
    history_entry = {
        "timestamp": datetime.datetime.now(pytz.utc), # Use timezone-aware UTC time
        "workout_plan": current_plan, # The plan that was just done
        "feedback": { # Standardize feedback structure
            "completed": completed_status,
            "difficulty_rating": difficulty_rating,
            "notes": notes
        }
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
    # Fetch user profile data again for the AI prompt context if needed
    # Or use context sent with the request (e.g., user's current stated level/goal)
    user_profile_context = {
        'level': data.get('level', 'Beginner'), # Use level sent with feedback request
        'goal': data.get('goal', 'General Fitness'),
    }
    current_plan_str = json.dumps(current_plan, indent=2) # Pretty print for the prompt

    prompt = f"""
    Task: Evolve the user's workout approach based on their recent performance feedback.

    User Profile Context (provided with feedback):
    - Experience Level: {user_profile_context.get('level')}
    - Goal: {user_profile_context.get('goal')}

    Workout Plan Just Completed:
    ```json
    {current_plan_str}
    ```

    User's Feedback on Completed Workout:
    - Completed?: {completed_status}
    - Difficulty Rating (1-10, 1=easy, 10=very hard): {difficulty_rating}
    - User Notes/Feelings: {notes}

    Instructions:
    1. Analyze the completed plan and the user's feedback.
    2. Suggest specific progressions or regressions for the *next* workout. Consider difficulty, completion status, and user notes.
    3. Keep suggestions aligned with the user's goal and experience level.
    4. **Output Format:** Generate a JSON object with two keys: "explanation" and "updated_plan".
       - "explanation": String with brief reasoning for the suggestions (use simple HTML: <p>, <b>, <ul>, <li>).
       - "updated_plan": This should be the *complete updated workout plan JSON* for the *next* session, following the same structure as the generate-workout output. If generating a full plan isn't feasible based only on feedback (e.g., need more user input), provide clear modification suggestions as an HTML string within this key.
    5. Ensure valid JSON output. No text outside the main JSON object.

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
      "explanation": "<p>Since you found the {feedback.get('notes', 'exercise')} challenging, let's try modifying it next time.</p>",
      "updated_plan": "<p><b>Next Workout Suggestions:</b></p><ul><li>Reduce reps for [Exercise] to X-Y.</li><li>Consider substituting [Exercise] with [Alternative Exercise].</li><li>Keep other parts the same.</li></ul>"
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

@app.route('/api/ai/analyze-meal', methods=['POST'])
def analyze_meal():
    """
    Estimates nutritional content of a meal using the simpler, focused prompt.
    """
    data = request.json
    if not data or 'meal_description' not in data:
        return jsonify({'error': 'Missing meal_description in request body'}), 400

    meal_description = data.get('meal_description')

    # Use the simplified prompt for estimation
    prompt = f"""
    Estimate the approximate calories (kcal) and protein (g) content for the following meal. Provide the results in a simple, clear format. Emphasize that these are *estimates*.

    Meal Description: "{meal_description}"

    Required HTML Output Format:
    <p>Estimated Calories: <b>[Number] kcal</b></p>
    <p>Estimated Protein: <b>[Number] g</b></p>
    <p><i>Note: These are rough estimates based on typical ingredients and portion sizes. Actual values can vary significantly.</i></p>
    Use only these simple HTML tags. Do not use Markdown or other tags like <html>, <body>.
    """
    logging.info(f"Sending prompt to AI for /analyze-meal: {prompt[:200]}...")
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

# TODO: Implement endpoints for summarize_text, design_placement_test, interpret_placement_results if needed.


# --- Run the Application ---
if __name__ == '__main__':
    # Run the Flask app in debug mode for development (auto-reloads, more detailed errors)
    # Disable debug mode in production!
    # Consider specifying host='0.0.0.0' to make it accessible on your network
    app.run(debug=True, port=5000) # Using port 5000 is common for Flask dev