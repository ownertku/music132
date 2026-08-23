from pyrogram import Client

print("--- Pyrogram String Session Generator ---")
print("You can get your API_ID and API_HASH from https://my.telegram.org\n")

api_id = input("Enter your API_ID: ")
api_hash = input("Enter your API_HASH: ")

app = Client("my_session", api_id=int(api_id), api_hash=api_hash, in_memory=True)

with app:
    session_string = app.export_session_string()
    print("\n\n--- YOUR STRING SESSION ---")
    print(session_string)
    print("---------------------------\n")
    print("Copy the string above and paste it in your .env file as STRING_SESSION=...")
