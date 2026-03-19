# Project Memory

## What this project is
Terminal-based AI agent that automates LinkedIn profile updates. Uses Claude (claude-sonnet-4-6) via the Anthropic API for conversational intelligence and Playwright for headed browser automation.

## Core workflow
Login to LinkedIn -> scrape user profile (name, headline, location, about) -> generate a new bio based on user intent -> update the About section after confirmation.

## Key files
- `main.py` — Agentic loop with tool definitions, system prompt, and a code-improvement sub-agent loaded from `.claude/agents/`.
- `linkedin_browser.py` — `LinkedInBrowser` class wrapping async Playwright for login, profile scraping, and About section editing.
- `requirements.txt` — anthropic, playwright, python-dotenv, pyyaml.

## Notable details
- Browser runs headed (headless=False) so users can manually complete 2FA/CAPTCHA.
- Bio limit enforced at 2600 characters.
- Requires `ANTHROPIC_API_KEY` in `.env`.
- No tests or CI configured.
