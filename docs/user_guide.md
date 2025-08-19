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

• **User menu (top-right)** – click the avatar to open the user manager.  
• **Create** – give a display name and press *Create*.  
• **Switch** – select any user from the dropdown; each user has isolated chat history, personality and research topics.  

---

## 3. Personalising the Assistant

Click the **User Settings** button, to display the current settings.
Click Edit to modify:

| Setting | Description |
|---------|-------------|
| Style   | *helpful*, *concise*, *expert*, *creative*, *friendly* |
| Tone    | *friendly*, *professional*, *casual*, *enthusiastic*, *direct* |
| Presets | One-click combos such as *Friendly Helper* |

Changes apply instantly and are stored in your profile.

---

## 4. Chatting

1. Type your message and hit **Enter**.  
2. A typing indicator shows the assistant is thinking.  
3. Messages are saved automatically; scroll to review.  
4. Click **Show RoutingInfo** next to any assistant reply to see which module (chat / search / analyzer) handled the request, the router's reason, complexity score and the lightweight model it used.  

---

### Web search behavior

When your question needs web search, the assistant automatically optimizes the query and selects search settings:

- Decides whether recency is important (e.g., “latest”, “today”, “updates”).
- Chooses search mode: academic (for scholarly results) or web.
- Sets context size (low/medium/high). If uncertain, it falls back to your research depth preference.

## 5. Research Topics & Findings

### Suggestion sidebar

After each message the system may suggest **Topics** related to your conversation (right-hand sidebar).

* **🔬 Research this topic** – subscribes the topic for autonomous research.  
* **🗑️ Dismiss** – removes it from the list.

### Topics dashboard

Click **Research Topics** in the **Dashboard** dropdown to open a full dashboard where you can:

* **▶️ Enable Engine** – Enable/disable the autonomous researcher.
* **🚀 Research Now** – trigger immediate research; ignores motivation threshold.
* **💡 View Drives** -  Monitor the real-time values for the **boredom**, **curiosity**, **tiredness** and **satisfaction** parameters.  When boredom + curiosity ≥ threshold a new research cycle is launched automatically.
* **⏰ Research timing** – See the current estimated research frequency, or select a quick preset to change it.

* View all topics (active + inactive) per user.
* **Toggle switch** – start/stop research for a topic.

### Reviewing Findings

Click **Research Results** in the **Dashboard** dropdown to open a full dashboard where findings appear underneath each topic with:

* **Summary**
* Quality score
* Source link (if available)
* Mark-as-read / delete buttons

---
## 7. Knowledge Graph Visualization

Click **Knowledge Graph** in the **Dashboard** dropdown.

The Knowledge Graph shows your personal knowledge network stored in Zep as an interactive visualization. The graph automatically arranges itself naturally and remembers your viewing preferences.

**Navigation:**
* **Zoom**: Mouse wheel or pinch gesture (your zoom level is remembered!)
* **Pan**: Click and drag on background
* **Move nodes**: Click and drag individual nodes
* **Reset view**: Double-click background to auto-fit graph

**Exploration:**
* **Highlight connections**: Single-click any node to see what it connects to
* **View details**: Double-click any node to open detailed information
* **Edge details**: Single-click any connection line
* **Clear selection**: Single-click empty background

**Modal Controls:**
* **Close details**: Click outside the modal
* **Full information**: Modals show complete entity/relationship details

The Knowledge Graph builds from your conversations and research, displaying:

* **Entities**: People, places, organizations, concepts from your chats
* **Relationships**: How these entities connect and relate
* **Facts**: Specific information about connections
* **Attributes**: Detailed properties of each entity
* **Timeline**: When information was created/updated

> **Note**: The graph grows over time as you chat and research. New users start with empty graphs that populate through conversations.

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
| **Double-click background** | Reset Knowledge Graph zoom to fit |

---

## 10. Logout & Clearing Data

User data lives in `backend/storage_data/` (JSON).  Deleting a user or the directory will permanently erase associated chats, settings and research findings.  There is no cloud backup.

---

## 11. Getting Help

* Hover tooltips explain most buttons.  
* Logs appear in the terminal running the backend.  
* Still stuck? Check `docs/troubleshooting.md`.

Enjoy exploring and let the autonomous researcher surface new insights while you chat! 🧠🔬 