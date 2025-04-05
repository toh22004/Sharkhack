from flask import Flask, request, jsonify, render_template, redirect
from flask_pymongo import PyMongo
from ai_service import AIService

from datetime import datetime

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

app = Flask(__name__)
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

db = client["GymBro"]
users_collection = db["Users"]


#The Main Page
@app.route("/")
def hello_world():
    return render_template('index.html') 
#The signup page, should be an option from the main page. Upon successful signup, redirects to main page
@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST': #Upon a submission of form
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        dob = request.form.get('dob')#dateofbirth
        sex = request.form.get('sex')
        weight = request.form.get('weight')#lb
        
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
            return redirect("/login")
        else:
            users_collection.insert_one(newUser)#inserts this into the mongo database
        return redirect("/") #return to main
    return render_template('register.html')
#The signin page, should be an option from the main page. Upon successful signin, redirect to ??? page
@app.route("/login", methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = str(request.form.get('username'))
        password = str(request.form.get('password'))

        existingUser = users_collection.find_one({"username": username})
        if existingUser:
            existingUserPass = str(existingUser["password"])
            if existingUserPass == password:
                return redirect("/")
            else:
                return redirect("/login")  
        else:
            return redirect("/register") #User doesn't exist, go to the signup page
    return render_template('login.html')



@app.route('/api/ai/assist', methods=['POST'])
def ai_assist():
    #The data in request.json file is where user info is stored
    data = request.json
    user_input = data.get('message')
    context = data.get('context', {})
    
    # Build a fitness-specific prompt
    prompt = f"""
    You are GymBro, a friendly fitness AI assistant. The user is interacting with you through a fitness app.
    
    Context:
    - User level: {context.get('level', 'beginner')}
    - Current mood: {context.get('mood', 5)}/10
    - Fitness goal: {context.get('goal', 'general fitness')}
    - Recent workout performance: {context.get('performance', 'average')}
    
    User message: {user_input}
    
    Respond in a supportive, encouraging tone while providing scientifically accurate fitness advice.
    Keep responses concise but helpful (1-2 paragraphs max).
    """
    
    response = ai_service.generate_response(prompt)
    return jsonify({'response': response})

@app.route('/api/ai/generate-workout', methods=['POST'])
def generate_workout():
    data = request.json
    prompt = f"""
    Generate a personalized workout plan based on the following parameters:
    
    - User level: {data.get('level', 'beginner')}
    - Available equipment: {data.get('equipment', 'bodyweight')}
    - Focus area: {data.get('focus', 'full body')}
    - Duration: {data.get('duration', 30)} minutes
    - Mood/energy level: {data.get('mood', 5)}/10
    - Recent progress: {data.get('progress', 'steady')}
    - Goal: {data.get('goal', 'general fitness')}
    
    Provide the workout in this JSON format:
    {{
      "warmup": [],
      "main_workout": [],
      "cooldown": [],
      "notes": ""
    }}
    """
    
    response = ai_service.generate_response(prompt)
    return jsonify({'workout': response})


@app.route('/api/ai/update-workout-plan', methods=['POST'])
def update_workout_plan():
    data = request.json
    prompt = f"""
    Adjust the user's workout plan based on their recent performance:
    
    Current plan:
    {data.get('current_plan', 'No current plan')}
    
    Recent performance:
    - Completed: {data.get('completed', False)}
    - Difficulty rating: {data.get('difficulty', 5)}/10
    - Notes: {data.get('notes', 'None')}
    
    User profile:
    - Level: {data.get('level', 'beginner')}
    - Goal: {data.get('goal', 'general fitness')}
    
    Provide the updated workout plan with adjustments for either more or less intensity.
    """
    
    response = ai_service.generate_response(prompt)
    return jsonify({'updated_plan': response})

@app.route('/api/ai/analyze-meal', methods=['POST'])
def analyze_meal():
    data = request.json
    prompt = f"""
    Analyze this meal for nutritional content and provide fitness recommendations:
    
    Meal description: {data.get('meal_description', 'Not provided')}
    
    User profile:
    - Weight: {data.get('weight', 'Not provided')}
    - Height: {data.get('height', 'Not provided')}
    - Fitness goal: {data.get('goal', 'maintenance')}
    - Activity level: {data.get('activity', 'moderate')}
    
    Estimate:
    1. Calories
    2. Protein content
    3. Carbohydrate content
    4. Fat content
    5. Fitness recommendations based on this meal
    """
    
    response = ai_service.generate_response(prompt)
    return jsonify({'analysis': response})

@app.route('/api/ai/check-form', methods=['POST'])
def check_form():
    data = request.json
    prompt = f"""
    The user is performing {data.get('exercise', 'an exercise')} and describes their form as:
    {data.get('form_description', 'No description provided')}
    
    Provide:
    1. Feedback on their form
    2. Common mistakes for this exercise
    3. Tips for improvement
    4. Safety considerations
    
    Keep the response concise but helpful.
    """
    
    response = ai_service.generate_response(prompt)
    return jsonify({'feedback': response})

# TODO: Add more endpoints for nutrition, form advice, etc.
if __name__ == '__main__':
    # Run the Flask app in debug mode. This enables auto-reloading when code or templates change.
    app.run(debug=True)

