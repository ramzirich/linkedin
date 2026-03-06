from playwright.async_api import async_playwright, Browser, Page


class LinkedInBrowser:
    def __init__(self):
        self._playwright = None
        self._browser: Browser = None
        self.page: Page = None

    async def start(self, headless: bool = False):
        """Launch the browser. headless=False so user can solve any verification challenges."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        self.page = await context.new_page()

    async def login(self, email: str, password: str) -> dict:
        """Navigate to LinkedIn login page and sign in."""
        if not self.page:
            return {"success": False, "message": "Browser not started. Call start() first."}

        await self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        await self.page.fill("#username", email)
        await self.page.fill("#password", password)
        await self.page.click('[type="submit"]')

        try:
            await self.page.wait_for_url(
                lambda url: "feed" in url or "checkpoint" in url or "challenge" in url or "login" in url,
                timeout=15000,
            )
        except Exception:
            pass

        current_url = self.page.url

        if "feed" in current_url or "mynetwork" in current_url:
            return {"success": True, "message": "Logged in successfully."}

        if "checkpoint" in current_url or "challenge" in current_url or "verification" in current_url:
            return {
                "success": False,
                "needs_verification": True,
                "message": (
                    "LinkedIn requires identity verification. "
                    "Please complete it in the browser window, then let me know when done."
                ),
            }

        if "login" in current_url:
            return {"success": False, "message": "Login failed. Please check your credentials."}

        return {"success": False, "message": f"Unexpected state. Current URL: {current_url}"}

    async def wait_for_manual_verification(self) -> dict:
        """Wait until the user completes a LinkedIn verification challenge."""
        try:
            await self.page.wait_for_url(
                lambda url: "feed" in url or "mynetwork" in url,
                timeout=120000,  # 2 minutes for the user to verify
            )
            return {"success": True, "message": "Verification complete. Logged in successfully."}
        except Exception:
            return {"success": False, "message": "Verification timed out. Please try again."}

    async def get_profile(self) -> dict:
        """Navigate to the user's own profile and scrape key info."""
        if not self.page:
            return {"success": False, "message": "Browser not started."}

        await self.page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded")

        # Wait for the main profile content to load
        try:
            await self.page.wait_for_selector("h1", timeout=10000)
        except Exception:
            return {"success": False, "message": "Profile page did not load in time."}

        # Give dynamic sections a moment to render
        await self.page.wait_for_timeout(2000)

        profile = {}

        # Name
        try:
            profile["name"] = await self.page.locator("h1").first.inner_text()
        except Exception:
            profile["name"] = None

        # Headline
        try:
            profile["headline"] = await self.page.locator(
                ".text-body-medium.break-words"
            ).first.inner_text()
        except Exception:
            profile["headline"] = None

        # Location
        try:
            profile["location"] = await self.page.locator(
                ".text-body-small.inline.t-black--light.break-words"
            ).first.inner_text()
        except Exception:
            profile["location"] = None

        # About / bio
        try:
            about_section = self.page.locator("#about").locator("..")
            profile["about"] = await about_section.locator(
                "span[aria-hidden='true']"
            ).first.inner_text()
        except Exception:
            profile["about"] = None

        # Clean up whitespace
        for key in profile:
            if isinstance(profile[key], str):
                profile[key] = profile[key].strip()

        profile["success"] = True
        return profile

    async def update_about(self, new_bio: str) -> dict:
        """Open the About edit modal on the user's profile and save the new bio."""
        if not self.page:
            return {"success": False, "message": "Browser not started."}

        # Make sure we're on the profile page
        if "/in/" not in self.page.url or "edit" in self.page.url:
            await self.page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded")
            await self.page.wait_for_selector("h1", timeout=10000)
            await self.page.wait_for_timeout(2000)

        # Click the edit pencil button in the About section
        try:
            about_edit_btn = self.page.locator("#about").locator("..").locator(
                "a[aria-label*='Edit'], button[aria-label*='Edit']"
            ).first
            await about_edit_btn.click()
        except Exception:
            # Fallback: click the general profile intro edit button
            try:
                await self.page.locator("a[href*='edit/intro']").first.click()
            except Exception as e:
                return {"success": False, "message": f"Could not find the About edit button: {e}"}

        # Wait for the edit modal to appear
        try:
            await self.page.wait_for_selector(".artdeco-modal", timeout=8000)
        except Exception:
            return {"success": False, "message": "Edit modal did not open."}

        await self.page.wait_for_timeout(1000)

        # Find the summary/about textarea inside the modal
        try:
            textarea = self.page.locator(".artdeco-modal textarea").first
            await textarea.click()
            # Select all and replace
            await textarea.press("Control+a")
            await textarea.fill(new_bio)
        except Exception as e:
            return {"success": False, "message": f"Could not fill the bio textarea: {e}"}

        # Click the Save button
        try:
            save_btn = self.page.locator(".artdeco-modal button.artdeco-button--primary").last
            await save_btn.click()
        except Exception as e:
            return {"success": False, "message": f"Could not click Save: {e}"}

        # Wait for modal to close
        try:
            await self.page.wait_for_selector(".artdeco-modal", state="hidden", timeout=8000)
        except Exception:
            pass

        await self.page.wait_for_timeout(1500)
        return {"success": True, "message": "About section updated successfully."}

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self.page = None
        self._browser = None
        self._playwright = None
