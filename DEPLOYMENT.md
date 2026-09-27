# Deployment

Live at: **https://infera-five.vercel.app**

## How it's actually hosted

Every genuinely free, no-credit-card cloud host we checked (Render, Railway,
Fly.io, Google Cloud Run, HuggingFace Spaces, Koyeb, Glitch, PythonAnywhere)
either caps free RAM at ~512MB — not enough to hold the NLI model + embedder
in memory even with a much smaller model (measured: ~718MB RSS just for a
270MB model, since PyTorch's own runtime baseline is the real constraint,
not model size) — or restricts outbound network calls in ways that would
break live OpenAlex/arXiv retrieval. Oracle Cloud's Always Free tier has
enough RAM (12GB) but requires a credit card on file. See the design
tradeoffs discussion in this project's history for the full comparison.

Given that, the backend runs on Ananya's own Mac — full local resources, no
compromises, the actual fine-tuned model and Ollama exactly as tested —
exposed to the public internet via a free ngrok tunnel with a permanent
static domain. The frontend is a normal static deploy on Vercel.

**Consequence: the backend is only reachable while `serve-public.sh` is
running on that Mac.** This isn't a 24/7 hosted service — it's the real app,
live, whenever it's running.

## Architecture

- **Frontend**: `frontend/` deployed on Vercel (free Hobby plan).
  `VITE_API_BASE` is set to the ngrok URL below. `vercel.json` adds the SPA
  rewrite rule Vercel needs to serve client-side routes like `/verify`
  directly (without it, a direct link or page refresh on any route other
  than `/` 404s).
- **Backend**: runs locally via `backend/serve-public.sh`, which starts
  uvicorn and an ngrok tunnel together, pointed at the permanent domain
  `tingly-swapping-backless.ngrok-free.dev` (free ngrok static domain, tied
  to the ngrok account, doesn't change across restarts).
- **NLI model**: `INFERA_NLI_MODEL` in `backend/.env` points at the local
  fine-tuned checkpoint (`./data/scifact-nli-weighted`) — the same one
  verified in training, not a downgraded version. A smaller model
  (`ananya24s/scifact-nli-weighted` vs. the small `cross-encoder` variant
  trained during this deployment's design phase) was considered specifically
  to fit a free host's RAM limit, but since the backend runs locally instead,
  there's no need to trade quality for hosting — the small model still
  exists as `backend/data/scifact-nli-xsmall/` if ever needed for a real
  cloud deployment later.

## Bringing the site up

```bash
cd backend
./serve-public.sh
```

This starts the backend, waits for model warmup, then starts the ngrok
tunnel. Leave it running — closing the terminal or sleeping the Mac takes
the site down until it's started again. Ctrl+C stops both cleanly.

## One-time setup (already done, for reference)

- `ngrok config add-authtoken <token>` — from https://dashboard.ngrok.com,
  free account, no card.
- Static domain claimed at https://dashboard.ngrok.com/domains (free, one
  per account).
- Vercel project created from this repo, root directory `frontend`,
  `VITE_API_BASE` set to the ngrok URL.
- `backend/.env`: `INFERA_NLI_MODEL` set to the local checkpoint path,
  `INFERA_ALLOWED_ORIGINS` set to `https://infera-five.vercel.app` (plus
  localhost for local dev) so the deployed frontend's CORS requests aren't
  rejected.

## If the ngrok domain ever needs to change

Update `VITE_API_BASE` in Vercel's project settings (Settings ->
Environment Variables) to the new URL and redeploy, and update
`INFERA_ALLOWED_ORIGINS` in `backend/.env` to match the new Vercel URL if
that ever changes too.
