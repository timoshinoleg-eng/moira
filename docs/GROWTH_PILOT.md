# Moira: invite-only growth pilot

## What is live in the code

- Every share action receives stable caption A or B for its referrer.
- The share deep link carries the caption variant.
- A new referred user records one `referral_signup` event; their first saved
  reading records `referral_first_reading` with the same variant.
- Feedback immediately opens contextual follow-up actions and a share action.
- Events contain only pseudonymous IDs, funnel stage and safe properties; they
  never contain the question, transcript, name or Telegram ID.

## Operating the experiment

1. Apply the database migration and start a single polling process.
2. Invite users with the normal share flow; do not manually change A/B captions.
3. Wait for 20 attributed referral signups, then run:

   ```powershell
   .venv\Scripts\python.exe scripts\growth_pilot_report.py --min-signups 20
   ```

4. Compare `signup_per_share` first. Confirm that the same variant does not
   materially underperform on `reading_per_signup` before changing the caption.
5. Keep the losing caption out of new shares only after the report reaches
   `ready_for_directional_review`; existing deep links remain valid.

The report is aggregate-only and may be run against a copied SQLite database
with `--db <path>` for offline review.

## Voice-input gate

Voice input appears in the question flow only when both are present in the
runtime environment:

```dotenv
DEEPGRAM_API_KEY=<project key>
DEEPGRAM_STT_ENABLED=true
```

The consent, edit/confirm step and typed-question fallback are already in the
bot. Without the key, the button is hidden rather than leading users to an
unavailable action. After adding the key, run the RU and EN voice acceptance
path described in `DEEPGRAM_VOICE_POC.md` before widening the pilot.
