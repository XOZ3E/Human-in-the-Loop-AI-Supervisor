# human_gui_simple.py
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import json
import threading
import time

DB_PATH = "frontdesk.db"
KB_PATH = "salon_data.json"

class SupervisorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Frontdesk Supervisor")
        self.setup_ui()
        self.refresh()
        threading.Thread(target=self.auto_refresh, daemon=True).start()

    def setup_ui(self):
        # Pending
        tk.Label(self.root, text="Pending Requests", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.pending_tree = ttk.Treeview(self.root, columns=("id", "q"), show="headings", height=5)
        self.pending_tree.heading("id", text="ID")
        self.pending_tree.heading("q", text="Question")
        self.pending_tree.pack(padx=10, fill=tk.X)

        # Answer
        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        tk.Label(frame, text="Answer:").pack(side=tk.LEFT)
        self.answer_entry = tk.Text(frame, height=3, width=50)
        self.answer_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Submit", command=self.submit).pack(side=tk.LEFT)

        # History
        tk.Label(self.root, text="History (Resolved/Unresolved)", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.history_tree = ttk.Treeview(self.root, columns=("id", "q", "a", "status"), show="headings", height=8)
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("q", text="Question")
        self.history_tree.heading("a", text="Answer")
        self.history_tree.heading("status", text="Status")
        self.history_tree.pack(padx=10, fill=tk.BOTH, expand=True)

    def refresh(self):
        # Pending
        for i in self.pending_tree.get_children():
            self.pending_tree.delete(i)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, question FROM help_requests WHERE status = 'pending'")
        for row in cur.fetchall():
            self.pending_tree.insert("", "end", values=row)

        # History
        for i in self.history_tree.get_children():
            self.history_tree.delete(i)
        cur.execute("SELECT id, question, answer, status FROM help_requests WHERE status != 'pending' ORDER BY answered_at DESC")
        for row in cur.fetchall():
            self.history_tree.insert("", "end", values=row)
        conn.close()

    def submit(self):
        selected = self.pending_tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Choose a pending question.")
            return
        qid = self.pending_tree.item(selected[0])["values"][0]
        answer = self.answer_entry.get("1.0", tk.END).strip()
        if not answer:
            messagebox.showwarning("Empty", "Type an answer.")
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE help_requests SET answer = ?, status = 'answered', answered_at = CURRENT_TIMESTAMP WHERE id = ?", (answer, qid))
        conn.commit()
        conn.close()

        # Update KB
        kb = json.load(open(KB_PATH)) if os.path.exists(KB_PATH) else {}
        question = [q[1] for q in self.pending_tree.get_children() if self.pending_tree.item(q)["values"][0] == qid][0]
        kb[question] = answer
        json.dump(kb, open(KB_PATH, 'w'), indent=2)

        self.answer_entry.delete("1.0", tk.END)
        self.refresh()

    def auto_refresh(self):
        while True:
            self.root.after(0, self.refresh)
            time.sleep(3)

if __name__ == "__main__":
    #init_db()  # Ensure DB exists
    root = tk.Tk()
    app = SupervisorGUI(root)
    root.mainloop()