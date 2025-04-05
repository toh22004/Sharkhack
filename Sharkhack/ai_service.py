import google.genai as genai

class AIService:
    def __init__(self):
        # Configure with your API key
       self.client =  genai.Client(api_key = "AIzaSyD8_Kjc9Aw-TZW6sY3N_KEP-yW3KjL5MKI")
    
    # Generate a response using the AI model
    def generate_response(self, prompt):
        try:
            # Use the Gemini model to generate a response
            response = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt)
            
            return response.text
        # Handle any exceptions that occur during the API call
        except Exception as e:
            print(f"AI Error: {e}")
            return "Sorry, I encountered an error processing your request."

# Test the AIService class
if __name__ == "__main__":
    test = AIService()
    print(test.generate_response("What is the capital of France?"))
    