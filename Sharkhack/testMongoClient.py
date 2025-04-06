from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import hashlib
import os
import binascii


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

db = client["GymBro"]
users_collection = db["Users"]

# --- Password Hashing Function ---
def hash_password(password):
    """Hashes a password using PBKDF2 with a random salt, returns hex strings."""
    salt_bytes = os.urandom(SALT_LENGTH)
    # PBKDF2 HMAC needs bytes for password and salt
    hashed_password_bytes = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode('utf-8'), # Password as bytes
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

# --- Create and Insert User 1 with Salted Password (Stored as Hex) ---
password_plain1 = "testpassword"
salt1_hex, hashed_pw1_hex = hash_password(password_plain1)

testObj1 = {
    "username": "testuser_salted_hex",
    "salt": salt1_hex, # Store the salt as a hex string
    "hashed_password": hashed_pw1_hex # Store the hash as a hex string
}
try:
    result1 = users_collection.insert_one(testObj1)
    print(f"Inserted testuser_salted_hex with id: {result1.inserted_id}")
    print(f"  Salt (hex): {salt1_hex}")
    print(f"  Hash (hex): {hashed_pw1_hex}")
except Exception as e:
    print(f"Error inserting user 1: {e}")


# --- Create and Insert User 2 with Salted Password (Stored as Hex) ---
password_plain2 = "anotherpassword"
salt2_hex, hashed_pw2_hex = hash_password(password_plain2)

testObj2 = {
    "username": "testuser2_salted_hex",
    "salt": salt2_hex,
    "hashed_password": hashed_pw2_hex
}
try:
    result2 = users_collection.insert_one(testObj2)
    print(f"Inserted testuser2_salted_hex with id: {result2.inserted_id}")
    print(f"  Salt (hex): {salt2_hex}")
    print(f"  Hash (hex): {hashed_pw2_hex}")
except Exception as e:
    print(f"Error inserting user 2: {e}")


# --- Test Password Verification ---
print("\n--- Verification Tests ---")
check_password("testuser_salted_hex", "testpassword")      # Should succeed
check_password("testuser_salted_hex", "wrongpassword")     # Should fail
check_password("testuser2_salted_hex", "anotherpassword")  # Should succeed
check_password("testuser2_salted_hex", "testpassword")     # Should fail
check_password("nonexistentuser", "somepassword")    # Should fail (user not found)

# --- Verify that two users with the same password have different hashes ---
password_plain3 = "testpassword" # Same as user 1
salt3_hex, hashed_pw3_hex = hash_password(password_plain3)

print("\n--- Same Password, Different Hash Test ---")
print(f"User 1 Hash (hex): {hashed_pw1_hex}") # Already hex
print(f"Hash for same password ('{password_plain3}') with new salt (hex): {hashed_pw3_hex}") # Already hex
if hashed_pw1_hex != hashed_pw3_hex:
    print("Success: Hashes are different due to different salts.")
else:
    print("Error: Hashes are the same, salting might not be working correctly.")
