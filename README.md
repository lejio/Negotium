# Negotium

An extensible job alert bot that monitors multiple platforms for new postings and sends notifications (macOS desktop + Discord) when listings match your criteria. Optionally ranks jobs against your resume using an LLM.

## Features

- Scrapes LinkedIn's public jobs API (no login required)
- Sorts results by **most recent** so you see new listings first
- **Experience level filters** — Internship, Entry-Level, Associate, Mid-Senior, Director, Executive
- **Location filter** — target a specific city or enable remote-only
- **Time filter** — past hour, 24 hours, week, or month
- **macOS desktop notifications** with sound for new postings
- **Discord webhook notifications** — rich embeds with job details sent to a channel
- **LLM job ranking** — scores each job 0-100 against your resume (OpenAI, optional)
- Tracks seen jobs in `seen_jobs.json` to avoid duplicate alerts
- Runs on a configurable polling interval (default: every 15 minutes)
- **Visitor pattern architecture** — cleanly extensible for new platforms and operations

## Installation

```bash
# Clone the repo
git clone <repo-url> Negotium
cd Negotium

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

All settings are in `main.py` at the top:

### Search Options

```python
SearchConfig(
    keywords="software engineer",
    experience_levels=[ExperienceLevel.ENTRY_LEVEL],     # see all options below
    posted_within=PostedWithin.PAST_24H,
    location="San Francisco, CA",                        # or "" for any
    remote_only=False,
)
```

**Experience levels:** `INTERNSHIP`, `ENTRY_LEVEL`, `ASSOCIATE`, `MID_SENIOR`, `DIRECTOR`, `EXECUTIVE`

**Time filters:** `PAST_HOUR`, `PAST_24H`, `PAST_WEEK`, `PAST_MONTH`

### Discord Notifications

1. Create a webhook in your Discord channel (Channel Settings → Integrations → Webhooks)
2. Paste the URL in `main.py`:

```python
discord=DiscordConfig(
    webhook_url="https://discord.com/api/webhooks/...",
)
```

The bot only sends messages when **new** jobs are found — it stays silent otherwise.

### LLM Job Ranking

1. Place your resume at `resume.txt` in the project root
2. Enable in `main.py`:

**OpenAI:**

```python
llm=LLMConfig(
    enabled=True,
    provider="openai",
    model="gpt-4o-mini",
    api_key="sk-...",                    # or set OPENAI_API_KEY env var
    resume_path=Path("resume.txt"),
    min_score_to_notify=50,              # only alert for jobs scoring >= 50
)
```

**Local LLM** (Ollama, LM Studio, llama.cpp, vLLM, LocalAI, Jan, etc.):

```python
llm=LLMConfig(
    enabled=True,
    provider="local",
    model="llama3.2",                    # model name on your local server
    base_url="http://localhost:11434/v1", # Ollama default
    resume_path=Path("resume.txt"),
    min_score_to_notify=50,
)
```

Common `base_url` defaults:

| Server | Default URL |
|--------|-------------|
| Ollama | `http://localhost:11434/v1` |
| LM Studio | `http://localhost:1234/v1` |
| llama.cpp | `http://localhost:8080/v1` |
| vLLM | `http://localhost:8000/v1` |

Each job gets a **0-100 match score** comparing the listing against your resume.

## Usage

```bash
python3 main.py
```

The bot will immediately run a check, then repeat every 15 minutes. Press `Ctrl+C` to stop.

## Project Structure

```
Negotium/
├── main.py                                  # Entry point & configuration
├── requirements.txt                         # Python dependencies
├── seen_jobs.json                           # Auto-generated seen-job tracker
├── resume.txt                               # Your resume (for LLM ranking)
└── negotium/                                # Core package
    ├── __init__.py
    ├── config.py                            # SearchConfig, ExperienceLevel, etc.
    ├── notification.py                      # macOS desktop notifications
    ├── discord_notifier.py                  # Discord webhook integration
    ├── persistence.py                       # Seen-jobs load/save
    ├── ranker.py                            # LLM job-resume matching (0-100)
    ├── models/
    │   ├── __init__.py
    │   └── job.py                           # Job dataclass (shared model)
    ├── sources/                             # Elements (Visitor pattern)
    │   ├── __init__.py
    │   ├── base.py                          # JobSource ABC → 3 categories
    │   ├── search_engines/
    │   │   ├── __init__.py
    │   │   └── linkedin.py                  # LinkedIn source (implemented)
    │   ├── company_sites/
    │   │   └── __init__.py                  # Stub — direct career pages
    │   └── ats_platforms/
    │       └── __init__.py                  # Stub — Workday, Oracle Cloud, etc.
    └── visitors/                            # Visitors (Visitor pattern)
        ├── __init__.py
        ├── base.py                          # JobSourceVisitor ABC
        └── scraping.py                      # ScrapingVisitor (concrete)
```

### Architecture

The project uses the **Visitor pattern** with two axes of extension:

| Axis | How to extend | What to implement |
|------|--------------|-------------------|
| **New source** | Add a class in `sources/` | Subclass `JobSearchEngine`, `CompanyWebsite`, or `ATSPlatform` and implement `fetch_jobs()` |
| **New operation** | Add a class in `visitors/` | Subclass `JobSourceVisitor` and implement `visit_search_engine()`, `visit_company_site()`, `visit_ats_platform()` |

**Source categories:**

- **JobSearchEngine** — Aggregator boards (LinkedIn, Indeed, Glassdoor)
- **CompanyWebsite** — First-party career pages (e.g. apple.com/careers)
- **ATSPlatform** — Hosted ATS portals (Workday, Oracle Cloud, Greenhouse)
- **CompanyWebsite** — First-party career pages (e.g. apple.com/careers)
- **ATSPlatform** — Hosted ATS portals (Workday, Oracle Cloud, Greenhouse)