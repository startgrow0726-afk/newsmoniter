from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os

app = FastAPI()

# Serve static files from the 'site' directory
app.mount("/", StaticFiles(directory="./site", html=True), name="site")

@app.post("/subscribe_email")
async def subscribe_email(email: str = Body(..., embed=True)):
    email_file_path = os.path.join("./site", "subscribed_emails.txt")
    with open(email_file_path, "a") as f:
        f.write(f"{datetime.now().isoformat()}: {email}\n")
    return {"message": "Email subscribed successfully!"}

