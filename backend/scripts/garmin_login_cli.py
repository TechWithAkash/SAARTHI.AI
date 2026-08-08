"""
Garmin Connect — one-time interactive login (run this yourself, in a terminal).

WHY THIS EXISTS SEPARATELY FROM THE API
----------------------------------------
garmin_service.py's login path runs inside a FastAPI request. If your account
has MFA, Garmin will ask for a 6-digit code — and a web request has no
terminal to read it from, so the API deliberately REFUSES rather than hang a
worker thread waiting on stdin. That's what you'd see if you clicked
"Sync Garmin" before ever running this script: a clear error telling you to
run this first.

This script runs interactively, so it CAN prompt for the MFA code. It uses
`backend.config.settings` for both credentials and the token store path —
the exact same settings object the running API reads — so tokens cached here
are found automatically by garmin_service.py on its very next request. No
separate/mismatched token file, no re-entering anything.

WHAT IT DOES
------------
  1. Tries cached tokens first (in case you've already done this once).
  2. If none, attempts ONE fresh login (prompting for MFA if asked),
     capped at settings.garmin_max_login_attempts (default 2) — same cap
     the API enforces, so this script can't blow through it either.
  3. On success: caches OAuth tokens to disk, then makes a couple of tiny
     READ calls (name, today's stats) purely to prove the token actually
     works — this is NOT a backfill. Run a real sync afterward via the
     dashboard's "Sync Garmin" button or POST /garmin/sync.

Run from the repo root:
    /opt/anaconda3/envs/darpanai/bin/python3 backend/scripts/garmin_login_cli.py

Your password is read from .env and is never printed, logged, or written
anywhere by this script — only the OAuth tokens garth negotiates are cached.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `backend.*` imports

from backend.config import settings  # noqa: E402


def main() -> int:
    if not settings.garmin_configured:
        print(
            "GARMIN_EMAIL / GARMIN_PASSWORD are not set (or still the setup-doc "
            "placeholders) in .env. Add real values, save the file, then run this "
            "script again. Nothing has been attempted."
        )
        return 2

    import garminconnect

    store = settings.garmin_token_store
    email = settings.garmin_email
    masked = f"{email[:3]}***{email[-10:]}" if len(email) > 13 else "***"
    print(f"Token store: {store}")
    print(f"Account:     {masked}\n")

    # ── 1. Cached tokens first — zero risk, zero attempts spent ────────────────
    if Path(store).exists():
        try:
            client = garminconnect.Garmin()
            client.login(store)
            print("LOGIN OK — resumed from cached tokens, no SSO hit, no attempt spent.")
            return _verify(client)
        except Exception as e:
            print(f"Cached tokens didn't work ({type(e).__name__}: {e}) — falling back to SSO.\n")

    # ── 2. Fresh SSO login, capped attempts, interactive MFA ────────────────────
    max_attempts = settings.garmin_max_login_attempts
    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts}...")
        try:
            client = garminconnect.Garmin(
                email=email,
                password=settings.garmin_password,
                prompt_mfa=lambda: input("  Garmin sent an MFA code — enter it here: ").strip(),
            )
            client.login()
            print("LOGIN OK.")
            try:
                # NOT client.garth — that attribute doesn't exist on
                # garminconnect 0.3.2 (verified: hasattr returns False).
                # Token persistence lives on client.client (the underlying
                # garminconnect.client.Client), not a garth wrapper.
                client.client.dump(store)
                print(f"Tokens cached -> {store}")
                print("The running API will pick these up automatically on its next request —")
                print("no restart needed for the Garmin login itself. (You still need to have")
                print("restarted the API once already so it re-read GARMIN_EMAIL/PASSWORD from .env.)")
            except Exception as e:
                print(f"WARNING: login worked but caching tokens failed: {e}")
                print("You'll need to log in again next time — sync will still work today.")
            return _verify(client)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}\n")

    print(
        f"\nLOGIN FAILED after {max_attempts} attempts. Stopping here — do not re-run "
        "immediately. Repeated failed logins can get this network's IP temporarily "
        "blocked by Garmin. Common causes: wrong password, an MFA code that expired "
        "before you entered it, or a CAPTCHA challenge (rare, but if Garmin shows one "
        "in-browser you may need to log into garmin.com once manually first)."
    )
    return 1


def _verify(client) -> int:
    """Prove the token actually works with two harmless read calls."""
    from datetime import date
    print("\nVerifying with a couple of real reads...")
    try:
        name = client.get_full_name()
        print(f"  Account name from Garmin: {name}")
    except Exception as e:
        print(f"  Could not fetch name: {e}")
    try:
        stats = client.get_stats(date.today().isoformat())
        steps = stats.get("totalSteps") if isinstance(stats, dict) else None
        print(f"  Today's step count from Garmin: {steps}")
    except Exception as e:
        print(f"  Could not fetch today's stats: {e}")

    print(
        "\nDone. Next: hit 'Sync Garmin' on the dashboard (or POST /garmin/sync) to "
        "pull real history into the app — that call reuses these cached tokens and "
        "will not need to log in again."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
