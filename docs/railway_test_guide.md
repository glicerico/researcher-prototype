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

## 3. Enable the Research Engine (it's OFF by default)

Railway starts the backend with the autonomous researcher disabled to conserve CPU.

1. Click the **Topics** button in the top bar to open the *Topics Dashboard*.
2. At the top you'll see **Research Engine: Inactive** with a grey dot.
3. Press the **Enable Engine ▶️** button.  The dot turns green and status switches to *Active*.
4. The engine stays on as long as the container is running; you can pause it with the same button.

> The global engine must be active before any individual topic can be researched.

---

## 4. Autonomous Research & Motivation Drives

Once the engine is active you can:

* Click **🔬 Research this topic** on a suggestion to subscribe it.
* Use **🚀 Run Now** in the dashboard to trigger immediate research.

### What motivates the engine?

The system models four internal "drives":

| Drive | Increases | Decreases |
|-------|-----------|-----------|
| **Boredom**      | Time since last research | Each research run |
| **Curiosity**    | User activity (chatting) | Gradual decay |
| **Tiredness**    | Each research run | Time / rest |
| **Satisfaction** | High-quality findings | Time / rest |

Research is launched when **boredom + curiosity ≥ threshold** (default 1.0).

You can inspect and tweak these in real time:

1. **💡 View Drives** – shows current values.
2. **⏰ Research Timing** – open presets or fine-tune parameters.

Key parameters (Engine Settings modal):

* **Threshold** – motivation required to start a run (lower = more frequent).
* **Boredom rate** – speed boredom rises (per second).
* **Curiosity decay** – how fast curiosity fades when idle.
* **Tiredness & Satisfaction decay** – recovery rates after research.

Preset buttons (*Aggressive*, *Balanced*, *Conservative*, *Very Patient*) apply sensible combos.

---

## 5. Using the Admin Console

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
     1. Click **Flows** in the left sidebar.
     2. Two tabs are shown: **Main Chat Flow** and **Research Flow**.
     3. The diagram renders inline; use the download buttons to save PNG/SVG or **Regenerate** to rebuild if you changed the graph.
   * **Status** – backend health, research engine state, OpenAI key check.
   * **Traces** – Your LangSmith API key was set at deploy time, so every chat and research run is traced automatically.  Log messages include a link, or you can open https://smith.langchain.com, sign in with your key and select the **researcher-prototype** project to view detailed graphs and timings.

---

## 6. Known Limits on Railway Free Tier

* The container sleeps after 30 min idle; first request will take longer.
* Cold starts reset in-memory drives but user data persists (stored on disk).
* OpenAI rate limits still apply.

---

Enjoy testing, and feel free to leave feedback! 