# LinkedIn Agent

A terminal-based AI agent that automates LinkedIn profile management. Talk to it naturally in the terminal — it logs into LinkedIn and updates your profile description based on your instructions or your profile's existing content.

## How it works

The agent uses Claude (Anthropic) as its brain and Playwright to control a real browser. You interact with it in a conversational loop, and it decides which actions to take on your behalf.

## Project structure

```
linkedin/
├── main.py               # Agent entry point — conversational loop + tool execution
├── linkedin_browser.py   # Playwright browser: login, verification handling
├── requirements.txt
└── .env.example
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Add your Anthropic API key to `.env`:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```

## Usage

```bash
python3 main.py
```

Then just talk to it:

```
You: log me in, my email is foo@example.com and password is mypassword
Agent: [opens browser, logs in, reports back]
```

If LinkedIn asks for identity verification, a browser window will open so you can complete it manually.

## Current capabilities (Step 1)

- Log into LinkedIn via a real Chromium browser
- Handle identity verification challenges

## Roadmap

- **Step 2** — Scrape current profile info (bio, headline, experience)
- **Step 3** — Conversational intent: tell the agent how to update your profile
- **Step 4** — Generate a new description using Claude based on your profile or your input
- **Step 5** — Automatically fill in and save the new description on LinkedIn
