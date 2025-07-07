# User Guide

Welcome!  This guide walks you through everyday use of the **Researcher-Prototype** chat application – no coding required.

---

## 1. Opening the App

1. Make sure the backend (`uvicorn`) and frontend (`npm start`) are running.  
2. Visit **http://localhost:3000** in your browser.  
3. A default **Guest User** is pre-created so you can try the app immediately.

> If you see a white screen, check that the backend is on port 8000 and no CORS errors appear in the browser console.

---

## 2. Managing Users

• **User menu (top-left)** – click the avatar to open the user manager.  
• **Create** – give a display name and press *Create*.  
• **Switch** – select any user from the dropdown; each user has isolated chat history, personality and research topics.  
• **Delete** – remove the selected user (cannot delete **Guest**).

---

## 3. Personalising the Assistant

Open the **Personality** panel (sparkle ✨ icon).

| Setting | Description |
|---------|-------------|
| Style   | *helpful*, *concise*, *expert*, *creative*, *friendly* |
| Tone    | *friendly*, *professional*, *casual*, *enthusiastic*, *direct* |
| Presets | One-click combos such as *Friendly Helper* |
| Extra   | Add custom traits via JSON – for power users |

Changes apply instantly and are stored in your profile.

---

## 4. Chatting

1. Type your message and hit **Enter**.  
2. A typing indicator shows the assistant is thinking.  
3. Messages are saved automatically; scroll to review.  
4. Click **Show Routing Info** next to any assistant reply to see which module (chat / search / analyzer) handled the request, the router's reason, complexity score and the lightweight model it used.  
5. Use **↑ / ↓** keys to cycle through your recent inputs (handy for editing).

---

## 5. Research Topics & Findings

### Suggestion sidebar

After each message the system may suggest **Topics** related to your conversation (right-hand sidebar).

* **🔬 Research this topic** – subscribes the topic for autonomous research.  
* **❌ Dismiss** – removes it from the list.

### Topics dashboard

Click **Topics** in the header to open a full dashboard where you can:

* View all topics (active + inactive) per user.
* **🚀 Research Now** – trigger immediate research; ignores motivation threshold.
* **Toggle switch** – start/stop research for a topic.

### Reviewing Findings

Findings appear underneath each topic with:

* **Summary**
* Quality bars (recency, relevance, depth, credibility, novelty)
* Source link (if available)
* Mark-as-read / delete buttons

---

## 6. Motivation Dashboard

Press the 💡 icon to open real-time bars for **boredom**, **curiosity**, **tiredness** and **satisfaction**.  When boredom + curiosity ≥ threshold a new research cycle is launched automatically.

---

## 7. Knowledge Graph Visualization

The Knowledge Graph shows your personal knowledge network stored in Zep as an interactive visualization.

### Accessing the Graph

1. Go to **User Settings** (click your avatar in the top-left).
2. Click the **Knowledge Graph** button.
3. The graph loads automatically showing:
   - **Nodes**: People, concepts, entities from your conversations
   - **Edges**: Relationships between entities
   - **Colors**: Different entity types (hover the legend to see)

### Interacting with the Graph

* **Zoom**: Mouse wheel or pinch gesture
* **Pan**: Click and drag on background
* **Move nodes**: Click and drag individual nodes
* **View details**: Click on nodes or edges to see information
* **Reset**: Click background to clear selection

### What the Graph Shows

The Knowledge Graph builds from your conversations and research, showing:

* **Entities**: People, places, organizations, concepts mentioned
* **Relationships**: How these entities connect
* **Facts**: Specific information about relationships
* **Context**: When and where information was discussed

> **Note**: The graph populates over time as you chat and research. New users may have empty or sparse graphs initially.

---

## 8. Admin Console (optional)

For advanced users / administrators.

1. Navigate to **http://localhost:3000/admin**.
2. Login with the password set in `backend/.env` (`ADMIN_PASSWORD`).
3. Features:
   * Prompt editor with version history.
   * Flow visualiser PNG/SVG diagrams.
   * System status panel.

---

## 9. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Enter** | Send message |
| **Shift + Enter** | New line without sending |
| **↑ / ↓** | Cycle through previous inputs |
| **Esc**   | Close modals |

---

## 10. Logout & Clearing Data

User data lives in `backend/storage_data/` (JSON).  Deleting a user or the directory will permanently erase associated chats, settings and research findings.  There is no cloud backup.

---

## 11. Getting Help

* Hover tooltips explain most buttons.  
* Logs appear in the terminal running the backend.  
* Still stuck? Check `docs/troubleshooting.md`.

Enjoy exploring and let the autonomous researcher surface new insights while you chat! 🧠🔬 