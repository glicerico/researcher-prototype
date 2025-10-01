## Qwestor – Prototype Overview (High-Level)

Qwestor is an AI assistant that chats with users and autonomously researches topics for them in the background. It continuously discovers, summarizes, and organizes new information from multiple sources, then presents the most relevant findings back to the user.

This document summarizes what the current prototype can do today, in non-technical terms, for product, marketing, and leadership audiences.

---

### What Qwestor Does Today

- **Conversational Assistant**: Natural-language chat for questions, planning, and follow-ups.
- **On‑Demand Multi‑Source Research**: When a question needs facts, Qwestor fetches information from multiple source types in parallel and returns a concise, sourced summary.
  - Web (current information and news)
  - Academic (research papers)
  - Social/tech discussions (community perspectives)
  - Medical literature (health topics)
- **Autonomous Background Research**: Users can mark topics they care about; Qwestor will periodically research them without being asked, and surface fresh findings.
- **Personalization**: Learns preferred tone, length, and sources based on how each user interacts with results, remaining privacy‑first by design.
- **Knowledge Graph View (optional)**: Visual map of entities and relationships extracted from research and chats, helping users “see the big picture.”
- **Topic Management**: Create, enable/disable, and review research topics; prioritize what matters.
- **Admin Tools (optional)**: Internal console for monitoring status, editing system prompts, and viewing flow diagrams.

---

### How It Works (At a Glance)

- **Smart Routing**: Qwestor decides whether a user needs a simple answer, an analysis, or a fact‑gathering search.
- **Parallel Sources**: For searches, it queries several source types at once, then synthesizes a clear answer with links.
- **Autonomous Engine**: In the background, a lightweight “motivation model” decides when to run new research cycles based on freshness, user engagement, and recent quality of results.
- **Topic Capacity Guardrails**: To prevent overload, Qwestor keeps active background topics under a configurable cap (default: 5 per user). When at capacity, related suggestions are saved as inactive for later review.
- **Related Topic Suggestions (optional)**: When enabled with a knowledge graph provider, Qwestor proposes related topics. If you’re at the active limit, these arrive as inactive suggestions you can enable later.

Why this matters: Qwestor saves users time by (1) answering questions with multi‑angle evidence and (2) proactively watching what they care about, so useful updates arrive even when they’re busy.

---

### What Users Experience

- **Simple Chat UI**: Type a question; get an answer with citations. If research was needed, Qwestor explains what it looked at.
- **Research Topics Dashboard**: See all topics (active/inactive), enable or pause background research, and trigger a “research now” action for immediate updates.
- **Results Feed**: New findings appear with summaries, quality indicators, and links. Users can mark items as read or remove them.
- **Knowledge Graph (optional)**: An interactive view to explore people, organizations, concepts, and how they connect.
- **Personalization Controls**: Adjust style and tone; Qwestor adapts responses and prioritizes sources that you tend to value.

---

### Privacy & Data Handling

- **Local‑first**: By default, user data (profiles, chats, and research findings) is stored locally in simple files; no external database is required for the prototype.
- **Transparent Personalization**: Users can see and override how Qwestor adapts to them.
- **Optional Knowledge Graph Provider**: Some advanced features (related topic discovery) require an external memory/graph service; when disabled, core chat and research still work.

---

### Integrations & Cost Drivers (High-Level)

- **Language Model (LLM)**: Used for reasoning, summarization, and topic selection. Cost scales with usage (tokens processed).
- **Search & Data APIs**: Web/academic/social/medical lookups power the factual layer. These may have per‑request limits or fees depending on vendor.
- **Optional Graph/Memory Service**: Needed for automatic related‑topic suggestions and graph visualization. Can be turned off to reduce cost/complexity.

What this means for budgets: The main variable costs are LLM tokens and search/API calls. Background research frequency and topic limits are configurable to control spend.

---

### Current Status (Prototype)

- **Maturity**: Working end‑to‑end demo for local use. Stable for internal pilots and user testing; not yet production‑hardened.
- **Core Capabilities Verified**:
  - Chat + multi‑source research with parallel querying and synthesis
  - Background research with configurable topic caps (default 5)
  - Research findings review workflow (summaries, links, quality badges)
  - Personalization controls with privacy‑first defaults
  - Optional knowledge graph visualization and related‑topic suggestions
- **Setup**: Runs locally with a browser front end and a Python back end. No external database required.

Known limitations (before a production launch):

- Single‑machine prototype; not tuned for high traffic or multi‑tenant scale
- Requires API keys for the LLM and some data sources
- Advanced topic expansion depends on an external graph/memory service
- No enterprise auth/SSO or role‑based permissions yet
- Not security‑hardened for internet exposure (designed for local/demo use)

---

### Near‑Term Roadmap (Indicative)

- Improve evidence cards (consistent citation metadata, preview snippets)
- Notification options (email/in‑app) when new, high‑value findings arrive
- Team workspaces (shared topics, shared findings, permissions)
- Tunable research cadence (per‑topic priority, quiet hours)
- Broader sources (finance, patents, code/search, domain‑specific feeds)
- Cloud deployment guide (containerization, logging, monitoring, secrets)
- Security hardening (auth, rate limiting, audit trails) for external pilots

---

### How to Evaluate Success

- **Time Saved**: Reduction in manual searching for a given topic or project
- **Adoption**: Number of active topics per user; frequency of “research now” actions
- **Engagement**: % of findings read; saves/bookmarks; follow‑up questions from findings
- **Quality**: User‑rated usefulness of findings; source diversity per answer
- **Freshness**: Average time from publication to surfacing in Qwestor for monitored topics

---

### Bottom Line

Qwestor already demonstrates the key value proposition: faster answers with credible sources and proactive, ongoing discovery on the user’s behalf. With modest engineering investment, it can evolve from a robust prototype into a pilot‑ready product focused on reliability, manageability, and team features—while keeping costs controllable through configurable research cadence and topic limits.



