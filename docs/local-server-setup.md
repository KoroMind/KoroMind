# Local Server Setup

Deploy KoroMind Telegram bot on a Linux server (GCP, AWS, or any VPS).

## Prerequisites

Have these ready before starting:
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- ElevenLabs API key ([elevenlabs.io](https://elevenlabs.io))
- Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Your Telegram chat ID

## 1. Create VM

**GCP Console:**
1. Go to Compute Engine > VM instances > Create
2. Settings:
   - Machine: `e2-medium` (2 vCPU, 4GB RAM)
   - Boot disk: Ubuntu 24.04 LTS, 20GB
   - Firewall: No inbound rules needed for Telegram bot
3. Create

**Other clouds:** Any Debian/Ubuntu VM with 2+ vCPU, 4GB+ RAM works.

## 2. SSH In

GCP: Use the SSH button in console, or:
```bash
gcloud compute ssh YOUR_VM_NAME --zone=YOUR_ZONE
```

## 3. Run Setup Script (Docker Compose)

For production deployment on a fresh VM, run:

```bash
curl -fsSL https://raw.githubusercontent.com/KoroMind/KoroMind/local-setup-docs/scripts/setup.sh | bash
```

Then use Docker Compose:

```bash
cd ~/KoroMind
nano ~/KoroMind/.env
docker-compose --profile telegram up -d --build
docker-compose logs -f koro
```

Update later:

```bash
cd ~/KoroMind
git pull
docker-compose --profile telegram up -d --build
```

## 4. Configure

Edit `.env` and add your keys:
```bash
nano ~/KoroMind/.env
```

**Required:**
```
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_DEFAULT_CHAT_ID=...
```

**Update paths (use absolute, not ~):**
```
KOROMIND_DATA_DIR=/home/ubuntu/.koromind
CLAUDE_WORKING_DIR=/home/ubuntu
CLAUDE_SANDBOX_DIR=/home/ubuntu/claude-sandbox
```

Create the sandbox directory:
```bash
mkdir -p ~/claude-sandbox
```

## 5. Start

```bash
cd ~/KoroMind
docker-compose --profile telegram up -d --build
```

## 6. Verify

Send a message to your bot on Telegram. Check logs if issues:
```bash
cd ~/KoroMind
docker-compose logs -f koro
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Cannot connect to the Docker daemon` | Run `sudo systemctl enable --now docker` and re-login so docker group changes apply |
| Bot not responding | Check logs: `cd ~/KoroMind && docker-compose logs -f koro` |
| Container exits repeatedly | Verify all required keys in `.env` are set |
| Docker build fails with `/.claude-settings: not found` | Run `cd ~/KoroMind && git config submodule.\".claude-settings\".url https://github.com/ToruAI/toru-claude-settings.git && git submodule sync --recursive && git submodule update --init --recursive && mkdir -p .claude-settings && docker-compose --profile telegram up -d --build` |

## Common Operations

**Restart bot:**
```bash
cd ~/KoroMind
docker-compose restart koro
```

**Update code:**
```bash
cd ~/KoroMind
git pull
docker-compose --profile telegram up -d --build
```

**Stop service:**
```bash
cd ~/KoroMind
docker-compose down
```

---

## Optional: REST API (Docker Profile)

1. Set in `.env`:
   ```
   KOROMIND_API_KEY=your_secret_key
   ```
2. Start API profile:
   ```bash
   cd ~/KoroMind
   docker-compose --profile api up -d --build koro-api
   ```
3. Test:
   ```bash
   curl -sS http://127.0.0.1:8420/api/v1/health
   ```
