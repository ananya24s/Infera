# Deploying Infera for free (Vercel + Oracle Cloud)

Frontend on Vercel (free, static hosting). Backend on an Oracle Cloud
"Always Free" ARM VM (free, 2 OCPU / 12GB RAM — the only free tier in 2026
with enough RAM to hold the NLI model + embedder + Ollama at once). The NLI
checkpoint lives on HuggingFace Hub (free model hosting) since it's ~750MB —
too large for a plain git push (GitHub hard-rejects files over 100MB).

Do the steps in order — each one unblocks the next.

## 1. Upload the NLI checkpoint to HuggingFace Hub

Run these yourself (needs your own HF login):

```bash
cd backend
.venv/bin/pip install -U huggingface_hub
.venv/bin/huggingface-cli login
```

Paste an access token when prompted — create one at
https://huggingface.co/settings/tokens (Write access).

```bash
.venv/bin/huggingface-cli repo create scifact-nli-weighted --type model
.venv/bin/huggingface-cli upload <your-hf-username>/scifact-nli-weighted ./data/scifact-nli-weighted .
```

Leave the repo public (default) — it's model weights, not sensitive data,
and a public repo means the server doesn't need its own HF token just to
download it later. Note the repo id (`<your-hf-username>/scifact-nli-weighted`)
— you'll set `INFERA_NLI_MODEL` to exactly that string in step 4.

## 2. Create the Oracle Cloud VM

This part is all in Oracle's web console — no commands.

1. Sign up at https://cloud.oracle.com (a credit card is required at
   signup but is never charged on the Always Free tier).
2. Create a Compute instance:
   - Shape: **VM.Standard.A1.Flex** (Ampere ARM) — set it to 2 OCPUs / 12GB
     RAM, which is the full Always Free allowance.
   - Image: **Ubuntu 24.04** (or latest LTS).
   - Generate/download an SSH key pair when prompted — you'll need the
     private key to connect.
3. If instance creation fails with "Out of capacity": this is a known,
   common issue with Oracle's free ARM tier. Just retry — sometimes a
   different Availability Domain works, sometimes it just needs a few
   attempts over a bit of time.
4. Once it's running, note its **public IP address**.

## 3. Open the firewall (Oracle's Network Security List)

Oracle has its own firewall layer separate from the OS's — both need the
right ports open, or the site will be unreachable even with everything
else correct.

In the Oracle console: your instance's **Virtual Cloud Network -> Security
Lists -> Default Security List -> Add Ingress Rules**. Add rules allowing
TCP on ports **80** and **443** from source `0.0.0.0/0`. Port 22 (SSH) is
open by default.

## 4. Set up the server

SSH in (replace with your actual key path and the VM's IP):

```bash
ssh -i ~/path/to/your-key.pem ubuntu@<VM_PUBLIC_IP>
```

Everything from here runs **on the VM**, over that SSH session.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv git nginx certbot python3-certbot-nginx
```

Install Ollama (official installer supports ARM):

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b
```

Clone the repo and set up the backend:

```bash
sudo mkdir -p /opt/infera && sudo chown ubuntu:ubuntu /opt/infera
git clone https://github.com/ananya24s/Infera.git /opt/infera
cd /opt/infera/backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

If any package fails to install with a build error here, it means that
package doesn't ship a prebuilt ARM wheel yet and pip is trying to compile
it from source — note which package and we'll deal with it specifically;
most (torch, transformers, sentence-transformers, scikit-learn, faiss-cpu)
do have ARM wheels as of 2026, so this is a fallback case, not the
expected path.

Create `.env` (note: no local model path — this is the HF Hub repo id from
step 1):

```bash
cat > .env << 'EOF'
INFERA_NLI_MODEL=<your-hf-username>/scifact-nli-weighted
INFERA_OPENALEX_CONTACT_EMAIL=
# Fill this in after step 6, once you know your real Vercel URL:
INFERA_ALLOWED_ORIGINS=
EOF
```

Warm up the model cache once by hand (so the first real request isn't the
one paying for the multi-minute cold download):

```bash
.venv/bin/python3 -c "from app.ml import nli_model, hybrid_search" 2>/dev/null
.venv/bin/python3 -c "
from app.services import hybrid_search
from app.ml import nli_model
hybrid_search.warmup()
nli_model.warmup()
print('warm')
"
```

## 5. Run the backend as a service

```bash
sudo cp deploy/infera-backend.service /etc/systemd/system/infera-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now infera-backend
sudo systemctl status infera-backend
```

Check the logs if it doesn't come up clean:

```bash
sudo journalctl -u infera-backend -f
```

## 6. Put nginx in front of it, then add HTTPS

```bash
sudo cp deploy/nginx-infera.conf /etc/nginx/sites-available/infera
sudo sed -i 's/YOUR_DOMAIN_OR_IP/<VM_PUBLIC_IP_OR_YOUR_DOMAIN>/' /etc/nginx/sites-available/infera
sudo ln -s /etc/nginx/sites-available/infera /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

If you have a real domain pointed at the VM's IP (an A record), get HTTPS
for free:

```bash
sudo certbot --nginx -d your-domain.com
```

Without a domain, you can only reach the backend over plain HTTP at the
VM's IP — that's fine to test with, but browsers will block a deployed
HTTPS frontend (Vercel) from calling an HTTP-only backend (mixed content).
A real domain is effectively required for the two to actually talk in
production — a free one from something like Cloudflare/Freenom-style
registrars, or a subdomain if you already own a domain, works fine.

## 7. Deploy the frontend to Vercel

All in Vercel's dashboard at https://vercel.com:

1. Sign in with GitHub, **Import Project**, pick your `Infera` repo.
2. Set **Root Directory** to `frontend`.
3. Framework preset: Vite (should auto-detect).
4. Add an environment variable: `VITE_API_BASE` = `https://your-domain.com`
   (your backend's real HTTPS URL from step 6 — must include the scheme,
   no trailing slash).
5. Deploy. Vercel gives you a URL like `infera-xyz.vercel.app` immediately.

## 8. Wire the two together

Now that you know the real Vercel URL, go back to the VM and set it as the
allowed CORS origin:

```bash
# on the VM, in /opt/infera/backend/.env
INFERA_ALLOWED_ORIGINS=https://infera-xyz.vercel.app
```

```bash
sudo systemctl restart infera-backend
```

## 9. Verify it actually works

- Open the Vercel URL in a browser you haven't tested from before.
- Ask a real research question on `/research` and confirm a report comes
  back with real sources.
- Try `/verify` with a source + hypothesis.
- If requests fail, check the browser console for a CORS error first
  (means step 8 didn't take) — then `sudo journalctl -u infera-backend -f`
  on the VM for anything else.
