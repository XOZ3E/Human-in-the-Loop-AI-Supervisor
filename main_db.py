# main.py — RETURNS HUMAN ANSWER + KB UPDATE
import json
import sqlite3
import os
import asyncio  # <-- 1. ADDED MISSING IMPORT
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext
from livekit.agents.llm import function_tool
from livekit.agents import inference
from livekit.plugins import assemblyai, elevenlabs
import time  # <-- 1. ADDED MISSING IMPORT
from human_queue_db import human_queue_db

load_dotenv()

KNOWLEDGE_BASE_PATH = "salon_data.json"
DB_PATH = "frontdesk.db"

# === DB HELPERS ===

def update_kb(question: str, answer: str):
    kb = {}
    if os.path.exists(KNOWLEDGE_BASE_PATH):
        # <-- 3. ADDED ENCODING
        with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
            kb = json.load(f)
    kb[question] = answer
    # <-- 3. ADDED ENCODING
    with open(KNOWLEDGE_BASE_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, indent=2)

# === TOOL ===
@function_tool
async def ask_human(question: str) -> str:
    qid = await asyncio.to_thread(human_queue_db.add_question, question)
    print(f"[TEXT TO SUPERVISOR] Question #{qid}: {question}")
    TIMEOUT_SECONDS = 120  # 10 minutes (You decide the duration)
    start_time = time.time() # You'll need to import time

    # Wait for human answer
    while True:
        if time.time() - start_time > TIMEOUT_SECONDS:
            # Mark the request as unresolved in the DB (new helper needed)
            await asyncio.to_thread(human_queue_db.mark_unresolved, qid)
            
            # Return a generic failure message to the customer
            return "I apologize, my supervisor is unavailable right now. Please try again later."
        # <-- 2. FIXED BLOCKING I/O
        # Run the synchronous DB check in a separate thread
        question_data = await asyncio.to_thread(human_queue_db.get_question, qid)
        if question_data and question_data['status'] == 'answered':
            answer = question_data['answer']
        
            if answer:
             await asyncio.to_thread(update_kb, question, answer)
             return answer  # RETURN HUMAN'S ANSWER
        
        # Poll every 2 seconds without blocking
        await asyncio.sleep(2)

# === KB ===
def load_kb():
    if os.path.exists(KNOWLEDGE_BASE_PATH):
        # <-- 3. ADDED ENCODING
        with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# === AGENT ===
class VoiceAssistant(Agent):
    def __init__(self):
        kb = load_kb()
        kb_str = "\n".join([f"Q: {q}\nA: {a}" for q, a in kb.items()])

        instructions = f"""
You are mike and you just started working at Glow Salon and as you are new they gave you this data .
you can answer questions about services , prices , location etc
you can also book appointments for customers but first ask what service they want and then there name and phone number,time to confirm the booking.
SALON DATA(The data given to you):
{kb_str}
RULES:
1. If answer in SALON DATA → say it.
2. If not first say "let me check with my supervisor" and  then call ask_human(question) and answer based on what replay tool gives.
3. Be brief.
""".strip()

        super().__init__(
            instructions=instructions,
            tools=[ask_human]
        )

# === ENTRYPOINT ===
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=assemblyai.STT(),
        # Changed to gemini-2.5-flash for better availability.
        # You can change this back to "google/gemini-2.5-pro" if you have access.
        llm=inference.LLM(model="google/gemini-2.5-flash"), 
        tts=elevenlabs.TTS()
    )
    await session.start(agent=VoiceAssistant(), room=ctx.room)

if __name__ == "__main__":

    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
