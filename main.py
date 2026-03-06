import asyncio
import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from linkedin_browser import LinkedInBrowser

load_dotenv()

client = Anthropic()
browser = LinkedInBrowser()

# ─── Tool definitions ────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "login_to_linkedin",
        "description": (
            "Open a browser and log into LinkedIn with the user's email and password. "
            "Returns whether login succeeded or if manual verification is needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "LinkedIn email address"},
                "password": {"type": "string", "description": "LinkedIn password"},
            },
            "required": ["email", "password"],
        },
    },
    {
        "name": "wait_for_verification",
        "description": (
            "Wait for the user to complete a LinkedIn identity verification challenge "
            "in the browser window. Call this after login returns needs_verification=true."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_profile_info",
        "description": (
            "Navigate to the user's LinkedIn profile and scrape their name, headline, "
            "location, and about/bio section. Call this after a successful login."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]

# ─── Tool execution ───────────────────────────────────────────────────────────

async def run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "login_to_linkedin":
        if not browser._browser:
            await browser.start(headless=False)
        result = await browser.login(tool_input["email"], tool_input["password"])
        return json.dumps(result)

    if tool_name == "wait_for_verification":
        result = await browser.wait_for_manual_verification()
        return json.dumps(result)

    if tool_name == "get_profile_info":
        result = await browser.get_profile()
        return json.dumps(result)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})

# ─── Agent loop ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a LinkedIn automation agent running in the terminal. Your goal is to help the user \
manage their LinkedIn profile — starting with logging in.

Guidelines:
- Be concise and conversational, like a smart CLI assistant.
- When the user provides credentials, immediately use the login tool — do not ask for confirmation.
- Never repeat or echo passwords back to the user.
- If login requires verification, instruct the user to complete it in the browser window \
  and then call wait_for_verification.
- Keep the user informed of what you are doing at each step.

Current capabilities:
- Login to LinkedIn
- Scrape the user's profile (name, headline, location, about/bio)

After a successful login, proactively offer to fetch the profile info.
When profile info is retrieved, summarize it clearly for the user.
More capabilities (update description) will be added in future steps.\
"""

async def agent_loop():
    print("\nLinkedIn Agent ready.")
    print("To get started, provide your LinkedIn credentials.")
    print("Example: 'log me in, my email is you@example.com and my password is yourpassword'")
    print("Type 'quit' to exit.\n")

    messages = []

    while True:
        try:
            user_input = input("You (type your message): ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.lower() in {"quit", "exit", "q"}:
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # Inner agentic loop — keeps going until the model stops calling tools
        while True:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Append assistant turn
            messages.append({"role": "assistant", "content": response.content})

            # Print any text blocks
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    print(f"\nAgent: {block.text}\n")

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"[tool: {block.name}]")
                        result = await run_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                messages.append({"role": "user", "content": tool_results})
            else:
                break

    await browser.close()
    print("Goodbye.")


if __name__ == "__main__":
    asyncio.run(agent_loop())
