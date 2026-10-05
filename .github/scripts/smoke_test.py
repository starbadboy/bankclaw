"""Read-only deployment check: health/version, dashboard rendering, and sign-in form."""
# ruff: noqa: INP001, T201

import argparse
from http import HTTPStatus


def check_dashboard(page, app_url: str, expected_version: str = "") -> None:
    response = page.request.get(f"{app_url.rstrip('/')}/api/health", timeout=60_000)
    if response.status != HTTPStatus.OK:
        message = f"Health endpoint returned HTTP {response.status}"
        raise ValueError(message)
    health = response.json()
    if health.get("status") != "ok":
        message = "Health endpoint did not report ok"
        raise ValueError(message)
    if expected_version and health.get("version") != expected_version.removeprefix("v"):
        message = "Deployed version differs from the expected version"
        raise ValueError(message)
    page.goto(app_url, wait_until="domcontentloaded", timeout=60_000)
    page.get_by_role("button", name="Sign in", exact=True).first.click(timeout=60_000)
    page.get_by_placeholder("you@example.com").wait_for(state="visible", timeout=60_000)
    page.locator('input[type="password"]').wait_for(state="visible")
    print("Health, dashboard rendering, and sign-in form passed.")


def main() -> int:
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-url", required=True, help="Bankclaw dashboard URL")
    parser.add_argument("--expected-version", default="")
    args = parser.parse_args()
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            check_dashboard(page, args.app_url, args.expected_version)
            if errors:
                message = "Browser reported JavaScript errors: " + "; ".join(errors)
                raise ValueError(message)  # noqa: TRY301 — CLI reports browser errors
        except Exception as error:  # noqa: BLE001 — CLI returns a failed check for any browser error
            print(f"Smoke test failed: {error}")
            return 1
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
