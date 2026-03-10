# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A terminal-based AI agent that automates LinkedIn profile updates. Uses Claude (Anthropic API) for conversational intelligence and Playwright for browser automation. The agent follows a multi-step conversational flow: login → scrape profile → generate bio based on user intent → update the About section.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run the agent
python main.py
```

There are no tests, linting, or build steps configured.

## Architecture

Two-file Python codebase:

- **main.py** — Agentic loop using `claude-sonnet-4-6`. Defines 4 tools as JSON schemas (`login_to_linkedin`, `wait_for_verification`, `get_profile_info`, `update_about_section`), sends them to Claude, and executes tool calls in a loop until `end_turn`. Reads user input from stdin.

- **linkedin_browser.py** — `LinkedInBrowser` class wrapping async Playwright. Manages Chromium lifecycle, LinkedIn login with 2FA/CAPTCHA detection, profile scraping via CSS selectors, and About section editing through LinkedIn's modal UI.

## Key Details

- Model: `claude-sonnet-4-6` with 1024 max tokens
- LinkedIn bio character limit: 2600 (enforced in system prompt)
- Browser runs headed (headless=False) so users can complete manual verification
- Custom User-Agent set to avoid bot detection
- Login detection: checks URL for "feed"/"mynetwork" (success), "checkpoint"/"challenge"/"verification" (needs 2FA)
- Environment: requires `ANTHROPIC_API_KEY` in `.env` (see `.env.example`)
