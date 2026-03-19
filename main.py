import asyncio
import glob
import json
import os

import yaml
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
    {
        "name": "update_about_section",
        "description": (
            "Update the About/bio section on the user's LinkedIn profile with the new text. "
            "Only call this after the user has explicitly confirmed the new bio."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "new_bio": {"type": "string", "description": "The new About/bio text to save on LinkedIn"},
            },
            "required": ["new_bio"],
        },
    },
]

# ─── Code-improver subagent (loaded from .claude/agents/) ────────────────────

AGENT_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), ".claude", "agents", "code-improvement-scanner.md"
)


def _load_agent_file(path: str) -> tuple[dict, str]:
    """Load an agent .md file, returning (frontmatter_dict, body_prompt)."""
    with open(path, "r") as f:
        content = f.read()
    frontmatter = {}
    body = content
    if content.startswith("---"):
        end = content.index("---", 3)
        frontmatter = yaml.safe_load(content[3:end])
        body = content[end + 3:].strip()
    return frontmatter, body


_agent_meta, _agent_prompt = _load_agent_file(AGENT_PROMPT_PATH)

# Build the tool definition from the .md frontmatter
TOOLS.append({
    "name": _agent_meta.get("name", "code-improvement-scanner").replace("-", "_"),
    "description": _agent_meta.get("description", "").split("\\n")[0],
    "input_schema": {
        "type": "object",
        "properties": {
            "focus": {
                "type": "string",
                "description": "Optional focus area: 'readability', 'performance', 'bugs', 'best-practices', or 'all'",
                "default": "all",
            },
        },
    },
})


def run_code_improver(focus: str = "all") -> str:
    """Reads all .py files in the project and sends them to Claude for review."""
    py_files = sorted(glob.glob("*.py"))
    if not py_files:
        return json.dumps({"error": "No Python files found in the project directory."})

    file_contents = []
    for path in py_files:
        with open(path, "r") as f:
            content = f.read()
        file_contents.append(f"# ── {path} ──\n{content}")

    code_block = "\n\n".join(file_contents)

    response = client.messages.create(
        model={
            "sonnet": "claude-sonnet-4-6",
            "opus": "claude-opus-4-6",
            "haiku": "claude-haiku-4-5-20251001",
        }.get(_agent_meta.get("model", ""), _agent_meta.get("model", "claude-sonnet-4-6")),
        max_tokens=2048,
        system=_agent_prompt,
        messages=[{
            "role": "user",
            "content": f"Focus area: {focus}\n\n--- PROJECT CODE ---\n{code_block}",
        }],
    )

    return response.content[0].text


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

    if tool_name == "update_about_section":
        result = await browser.update_about(tool_input["new_bio"])
        return json.dumps(result)

    if tool_name == "code_improvement_scanner":
        result = run_code_improver(tool_input.get("focus", "all"))
        return result

    return json.dumps({"error": f"Unknown tool: {tool_name}"})

# ─── Agent loop ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a LinkedIn automation agent running in the terminal. You help users log in to LinkedIn, \
read their profile, and rewrite their bio/about section. \
You can also review and suggest improvements to this project's code when asked.

Guidelines:
- Be concise and conversational, like a smart CLI assistant.
- When the user provides credentials, immediately use the login tool — do not ask for confirmation.
- Never repeat or echo passwords back to the user.
- If login requires verification, instruct the user to complete it in the browser window \
  and then call wait_for_verification.
- Keep the user informed of what you are doing at each step.

Workflow:
1. Login — use login_to_linkedin as soon as credentials are provided.
2. Fetch profile — after login, call get_profile_info and summarize what you found.
3. Understand intent — ask the user how they want their bio updated. Examples:
   - "Make it more focused on AI and machine learning"
   - "I want to sound more senior and leadership-oriented"
   - "Rewrite it based on what's already there, just make it better"
4. Generate new bio — using the scraped profile info and the user's instructions, write a \
   new About/bio section. Present it clearly to the user like this:

   --- NEW BIO ---
   <the generated bio>
   ---------------

   Then ask: "Should I apply this to your LinkedIn profile?"
5. Apply — once the user confirms, call update_about_section with the generated bio.
   Report back whether it succeeded.

Keep generated bios professional, human, and under 2600 characters (LinkedIn's limit).
Never call update_about_section without explicit user confirmation.\
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
