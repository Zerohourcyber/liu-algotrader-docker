from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
import os

# 1) Create FastAPI app and serve your static folder under /static
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2) Instantiate a real OpenAI client (reads OPENAI_API_KEY from env)
client = OpenAI()

# 3) Pydantic model for your POST body
class Cmd(BaseModel):
    cmd: str

# 4) UI entry-point: serve your HTML chat page
@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")

# 5) Chat endpoint: forward user text into gpt-3.5-turbo chat
@app.post("/run")
async def run(cmd: Cmd):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": cmd.cmd}],
        )
        # grab the assistant’s reply
        reply = completion.choices[0].message.content.strip()
        return {"response": reply}

    except Exception as e:
        # bubble up any errors
        return JSONResponse(status_code=500, content={"error": str(e)})
