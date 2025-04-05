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
#delete all
result = users_collection.delete_many({})

testObj1 = {
    "username": "testuser",
    "password": "testpassword"
}
result = users_collection.insert_one(testObj1)
print(f"Inserted testuser with id: {result.inserted_id}")

# Insert another document for testuser2
testObj2 = {
    "username": "testuser2",
    "password": "anotherpassword"
}
result2 = users_collection.insert_one(testObj2)
print(f"Inserted testuser2 with id: {result2.inserted_id}")

existingUser = users_collection.find_one({"username": "testuser"})
if existingUser:
    print("User exists")
    print(existingUser["password"])