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

• **User dropdown (top-right)** – click the user button (👤) to open the user manager.  
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
4. Click **Show Routing Info** next to any assistant reply to see which module was used, the reasoning, and the router model used.  

---

### Multi-Source Search Behavior

When your question needs information gathering, the assistant automatically:

- **Classifies Intent**: Determines if you need chat, search, or analysis
- **Selects Sources**: For search queries, intelligently chooses up to 3 relevant sources:
  - **Web Search**: Current information, news, general topics
  - **Academic Search**: Scholarly articles and research papers  
  - **Social Search**: Community discussions from Hacker News
  - **Medical Search**: Medical literature and health information
- **Parallel Execution**: Queries multiple sources simultaneously for comprehensive results
- **Smart Integration**: Synthesizes information from successful sources while handling any failures gracefully

## 5. Research Topics & Findings

### Suggestion sidebar

After each message the system may suggest **Topics** related to your conversation (right-hand sidebar).

* **🔬 Research this topic** – subscribes the topic for autonomous research.  
* **🗑️ Dismiss** – removes it from the list.

### Topics dashboard

Click **📊 Dashboards** then **🔍 Research Topics** to open a full dashboard where you can:

* **▶️ Enable Engine** – Enable/disable the autonomous researcher.
* **🚀 Research Now** – trigger immediate research; ignores motivation threshold.
* **💡 View Drives** -  Monitor the real-time values for the **boredom**, **curiosity**, **tiredness** and **satisfaction** parameters.  When boredom + curiosity ≥ threshold a new research cycle is launched automatically.
* **⏰ Research timing** – See the current estimated research frequency, or select a quick preset to change it.

* View all topics (active + inactive) per user.
* **Toggle switch** – start/stop research for a topic.
* **➕ Add Topic** – Create custom research topics manually.

### Creating Custom Topics

In addition to system-suggested topics, you can create your own custom research topics:

1. **Open Topics Dashboard** – Click **📊 Dashboards** then **🔍 Research Topics**
2. **Click ➕ Add Topic** – Opens the custom topic creation form  
3. **Fill in Details**:
   - **Topic Name** (1-100 characters) – Clear, descriptive name for your research topic
   - **Description** (10-500 characters) – Detailed explanation of what you want researched
   - **Confidence Score** (0.0-1.0, default 0.8) – How confident you are this topic is worth researching
   - **Enable Research Immediately** (optional) – Start autonomous research right away

4. **Create Topic** – Your custom topic will appear in the topics list and can be managed like any system-suggested topic

**Examples of good custom topics:**
- "Sustainable urban farming techniques for small spaces"
- "Recent advances in quantum error correction algorithms" 
- "Impact of remote work on team collaboration tools"

### Reviewing Findings

Click **📊 Dashboards** then **📊 Research Results** to open a full dashboard where findings appear underneath each topic with:

* **Summary**
* Quality score
* Source link (if available)
* Mark-as-read / delete buttons

---
## 7. Knowledge Graph Visualization

Click **📊 Dashboards** then **🕸️ Knowledge Graph**.

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