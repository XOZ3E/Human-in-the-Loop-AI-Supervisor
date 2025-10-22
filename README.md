# Frontdesk Human-in-the-Loop Voice Agent

This project delivers the foundational version of a **Human-in-the-Loop (HITL) system** for AI agents, built on the LiveKit platform. The goal is to create a self-improving AI receptionist that can intelligently escalate unanswerable customer questions to a human supervisor, prevent AI hallucination, and automatically update its knowledge base.

## ✨ Core Features & Functionality

| Feature | Description | Implementation Detail |
| :--- | :--- | :--- |
| **Intelligent Escalation** | The LLM detects when a query is outside its knowledge base and invokes a custom function tool to halt the automated response. | Gemini LLM with **`@function_tool ask_human(question)`** |
| **Concurrency Safety** | Ensures the database remains consistent even when multiple agents or supervisor UIs interact with it simultaneously. | All DB operations in `human_queue_db.py` are protected by a **`threading.Lock()`**. |
| **Asynchronous Handoff** | The agent places the customer on hold while it waits for a human answer, guaranteeing a non-blocking experience for the live voice call. | The agent polls the DB using **`asyncio.to_thread(get_question)`** and **`asyncio.sleep(2)`**. |
| **Automatic Learning Loop** | The supervisor's text response is fed back into the system to be permanently stored for future use. | The answer is used to call **`update_kb()`**, writing to `salon_data.json`. |
| **Real-time Voice** | Full, low-latency, two-way audio streaming for a natural conversational experience. | Implemented using **LiveKit AgentSession** with AssemblyAI (STT) and OpenAI (TTS). |

## 📐 Architectural & Design Decisions

The following key decisions were made to prioritize **reliability, modularity, and future scalability**:

### 1. Concurrency Management (The Thread-Safe DB)
The LiveKit Agents SDK runs in an asynchronous event loop, but standard Python SQLite operations are synchronous and blocking. To prevent corruption and ensure the agent can handle high load:
* **Solution:** All synchronous database access in `human_queue_db.py` is wrapped with a global `threading.Lock()`.
* **Result:** This guarantees that only one thread can access the SQLite file (`frontdesk.db`) at a time, making the core data access layer robust for multi-user/multi-agent environments.

### 2. Non-Blocking Polling (UX Focus)
While waiting for a human response, the agent must not freeze the main asynchronous thread that manages the live audio stream.
* **Solution:** The polling mechanism inside `ask_human` uses `await asyncio.to_thread(HumanQueueDB.get_question, qid)` to offload the synchronous DB query to a separate worker thread.
* **Result:** The agent remains responsive, allowing it to provide a periodic 'hold message' (though currently a single wait loop) without disrupting the LiveKit connection.

### 3. Modular Separation of Concerns
The system is cleanly divided into three distinct responsibilities:
* **LLM Instructions:** Responsible only for the *decision* (when to call the tool).
* **`ask_human` Tool:** Responsible only for the *workflow* (queueing, polling, KB update).
* **`HumanQueueDB`:** Responsible only for *thread-safe data access*.

## 📂 Project Structure & Components

| File Name | Role in the System | Key Data Interaction |
| :--- | :--- | :--- |
| `main_db.py` | **Agent Entrypoint & Logic** | Defines AgentSession and the `ask_human` tool. |
| `human_queue_db.py` | **Database Wrapper (Thread-Safe)** | Manages all `frontdesk.db` interactions with `threading.Lock`. |
| `human_gui_simple.py` | **Supervisor Interface** | Tkinter GUI for supervisors to answer pending questions. |
| `salon_data.json` | **Runtime Knowledge Base (KB)** | Flat-file storage for Q&A pairs; read at startup, updated by the human loop. |
| `frontdesk.db` | **SQLite Database** | Stores the `help_requests` table (ID, question, answer, status). |
| `.env` | **Configuration** | Stores API credentials (LiveKit, Gemini, OpenAI, etc.). |
| `requirements.txt` | **Dependencies** | Lists all required Python packages. |

## 🛠️ Setup and Execution

### Prerequisites
* Python 3.8+
* Valid API Keys for: **LiveKit**, **Gemini**, **AssemblyAI**, and **OpenAI (for TTS)**.

### Step-by-Step Guide

1.  **Clone the Repository:**
    ```bash
    git clone [your-repo-link]
    cd frontdesk-voice-agent
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Create a file named **`.env`** in the root directory and populate it with your credentials:
    ```env
    LIVEKIT_URL="wss://..."
    LIVEKIT_API_KEY="..."
    LIVEKIT_API_SECRET="..."
    GEMINI_API_KEY="..."
    ASSEMBLYAI_API_KEY="..."
    OPENAI_API_KEY="..."
    ```

4.  **Start the Supervisor GUI:**
    The human supervisor needs to be ready to receive requests. This window will instantly show pending questions.
    ```bash
    python human_gui_simple.py
    ```

5.  **Start the LiveKit Agent:**
    This command runs the `main_db.py` worker and connects it to the LiveKit server.
    ```bash
    python main_db.py dev
    ```

6.  **Test the Agent:**
    Open the [LiveKit Agents Playground](https://playground.livekit.io/) (or your LiveKit client URL), connect to the room, and interact with the agent's voice.

## 📈 Future Improvements (Phase 2 Readiness)

For a production environment, the following enhancements would be prioritized:

1.  **Phase 2: Live Agent Handoff:** Implement a status check for the human supervisor. If the supervisor is online, use LiveKit's **room capabilities** to bridge the customer's audio stream directly to the supervisor, fulfilling the real-time handoff requirement.
2.  **Scalable Knowledge Base (RAG):** Replace the flat-file `salon_data.json` with a **Vector Database (RAG)**. This would allow the agent to answer *semantic variations* of a learned question, dramatically improving generalization and reducing the reliance on the human loop.
3.  **Real-Time Notification:** Replace the database polling mechanism (`asyncio.sleep`) with a server-side **Webhook** or WebSocket notification. The Supervisor GUI's 'Submit' action should instantly push an update to the waiting agent thread, eliminating the 2-second latency delay.
