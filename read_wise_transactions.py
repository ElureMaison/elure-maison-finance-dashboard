"""
read_wise_transactions.py

Opens a real (headed) Chromium window against a persistent profile so you
can log into Wise (the window is visible on your screen - log in there
directly, including any 2FA step). Polls for up to WAIT_SECONDS for the
transactions/activity page to load, then dumps the page text + a
screenshot so recent transactions can be read out afterward. Re-run any
time - the profile keeps your session logged in after the first run.
"""

from playwright.sync_api import sync_playwright

PROFILE_DIR = "wise_browser_profile"
START_URL = "https://wise.com/all-transactions"
WAIT_SECONDS = 240
POLL_EVERY = 5


def main():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            viewport={"width": 1280, "height": 1400},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(START_URL, wait_until="domcontentloaded")

        print(f"Browser window is open. Log into Wise there if prompted (up to {WAIT_SECONDS}s).")

        waited = 0
        found = False
        while waited < WAIT_SECONDS:
            page.wait_for_timeout(POLL_EVERY * 1000)
            waited += POLL_EVERY
            body_text = page.inner_text("body")
            if "all-transactions" in page.url and ("Sent" in body_text or "Received" in body_text or "transaction" in body_text.lower()):
                found = True
                page.wait_for_timeout(2000)
                break
            print(f"  ...waiting ({waited}s elapsed, current url: {page.url})")

        # scroll a bit to load more transactions (Wise lazy-loads on scroll)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)

        text = page.inner_text("body")
        with open("wise_transactions_raw.txt", "w", encoding="utf-8") as f:
            f.write(text)
        page.screenshot(path="wise_transactions_screenshot.png", full_page=True)

        print(f"found_transactions_signal={found}")
        print("Saved wise_transactions_raw.txt and wise_transactions_screenshot.png")
        context.close()


if __name__ == "__main__":
    main()
