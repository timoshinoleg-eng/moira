# Deepgram voice-question POC

## Product decision

Deepgram is an optional input accelerator, not a second oracle and not the
Russian TTS provider. A user chooses a spread, taps **Say your question**, sends
one short voice note, edits the transcript if needed, and explicitly opens the
same reading flow used for typed questions.

This reduces the blank-page moment without changing card logic, payment rules,
the safety filter, Journal, follow-ups, or referrals. Voice-origin readings use
a more inviting share caption that points friends to their own one-minute
question.

## Launch configuration

Keep the feature off until a Deepgram project key is present:

```dotenv
DEEPGRAM_STT_ENABLED=true
DEEPGRAM_API_KEY=...
DEEPGRAM_STT_MODEL=nova-3
DEEPGRAM_STT_ENDPOINT=https://api.deepgram.com/v1/listen
DEEPGRAM_STT_MAX_DURATION_SEC=60
DEEPGRAM_STT_MAX_BYTES=10485760
DEEPGRAM_STT_TIMEOUT_SEC=25
```

Use `DEEPGRAM_STT_ENDPOINT` to choose the approved Deepgram regional endpoint.
Do not put a key in Git, analytics, captions, or test fixtures.

## UX funnel

1. User chooses Situation, Love, or Choice and may type normally.
2. **Say your question** gives a one-time concise notice; Continue immediately
   opens recording mode.
3. Moira accepts Telegram voice or audio, shows a progress message, then offers
   **Open my reading**, **Edit**, or **Record again**.
4. Only confirmed text reaches the reading service and can consume a reading.
5. The existing share card retains the referral deep link; voice-origin cards
   use a voice-first invitation caption.

## Boundaries and recovery

- OGG/Opus and normal Telegram audio are sent as bytes; no new local audio file
  is created.
- A 60-second / 10 MiB cap keeps the flow quick and costs predictable.
- Download, quota, timeout, provider and malformed-response failures keep the
  user in voice mode or allow typing; a failed transcript never consumes a
  reading.
- Product events contain only funnel stage, spread, locale, error category and
  latency bucket, never audio or transcript text.

## Acceptance

Before enabling the flag for users: run migrations, execute the unit suite,
test synthetic RU and EN OGG/Opus files, verify edit/repeat/cancel/text fallback
and a voice-origin share card, then run a small real Telegram pilot. Review
voice-entry → transcript → confirmed-question → completed-reading → share rates
alongside provider usage; keep streaming, Voice Agent, sentiment analysis and
Deepgram TTS out of this POC.
