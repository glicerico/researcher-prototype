# Quick Test Guide (Railway Deployment)

Welcome!  This short guide explains how to access and test the **Researcher-Prototype** instance running on Railway.

---

## 1. Open the App

1. Point your browser to:

   **https://<YOUR-FRONTEND-URL>.railway.app**

   (replace `<YOUR-FRONTEND-URL>` with the link shared by the maintainer).

2. The chat interface should load within a few seconds.

> If the page doesn't load, wait 20-30 s – Railway may be spinning up the container.

---

## 2. First Steps

1. Start chatting straight away – the default **Guest User** is ready for you.
2. Try asking anything (e.g. *"Explain quantum entanglement in simple terms."*).
3. Observe the AI response and suggested research topics on the right-hand sidebar.

---

## 3. Using the Admin Console

The deployment includes an admin interface for deeper inspection.

1. Click on the red Admin button in the top panel.
2. Enter the password **admin123** when prompted.
3. Explore:
   * **Prompt Editor** – view & tweak system prompts.
     1. Click **Prompt Editor** in the left sidebar.
     2. Select any prompt (they are grouped by category).
     3. Make your changes in the editor pane on the right, then press **Save**.
     4. A new version is stored automatically; use the *History* button to see or restore previous versions.
         • Every save creates a timestamped backup on the server – nothing is lost.
         • Restoring simply overwrites the *active* prompt; earlier backups remain available.
         • Backups live in `backend/storage_data/prompts/` and are **not** tracked by Git, so feel free to experiment.
   * **Flows** – PNG / SVG diagrams of the LangGraph pipeline.
   * **Status** – backend health, research engine state, OpenAI key check.

---

## 4. Autonomous Research

1. After sending a few messages you'll see topic suggestions (right sidebar).
2. Click **🔬 Research this topic** to enable background research.
3. Open the **💡 Motivation** modal (top-right) to watch boredom/curiosity drives build up.
4. When motivation crosses the threshold the engine will auto-research and findings will appear.

---

## 5. Things to Try

| Feature | How |
|---------|-----|
| Change assistant personality | Click the ✨ icon |
| Trigger research instantly | Topics dashboard → **🚀 Research Now** |
| Mark findings read | Click the ✔️ icon next to a finding |
| View backend logs | (maintainer only) Railway console → Logs tab |

---

## 6. Known Limits on Railway Free Tier

* The container sleeps after 30 min idle; first request will take longer.
* Cold starts reset in-memory drives but user data persists (stored on disk).
* OpenAI rate limits still apply.

---

Enjoy testing, and feel free to leave feedback! 