from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import hashlib
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

def check_password(username, input_password):
    user = users_collection.find_one({"username": username})
    if user:
        # Hash the input password and compare
        input_hash = hashlib.sha256(input_password.encode()).hexdigest()
        if input_hash == user["password"]:
            print("Password correct!")
        else:
            print("Incorrect password!")
    else:
        print("User not found!")

#test password1 using hash256
password1 = "testpassword"
hashed_password1 = hashlib.sha256(password1.encode()).hexdigest()  # Hex digest of SHA-256 hash

testObj1 = {
    "username": "testuser",
    "password": hashed_password1
}
result = users_collection.insert_one(testObj1)
print(f"Inserted testuser with id: {result.inserted_id}")

#test password2 using hash256
password2 = "anotherpassword"
hashed_password2 = hashlib.sha256(password2.encode()).hexdigest()

# Insert another document for testuser2
testObj2 = {
    "username": "testuser2",
    "password": hashed_password2
}
result2 = users_collection.insert_one(testObj2)
print(f"Inserted testuser2 with id: {result2.inserted_id}")

check_password("testuser", "testpassword")  # Should succeed
check_password("testuser", "wrongpassword")  # Should fail