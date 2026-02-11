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

## 3. Run Setup Script

```bash
curl -fsSL https://raw.githubusercontent.com/KoroMind/KoroMind/local-setup-docs/scripts/setup.sh | bash
```

Or clone and run manually:
```bash
git clone -b local-setup-docs https://github.com/KoroMind/KoroMind.git
cd KoroMind
./scripts/setup.sh
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
sudo systemctl enable --now koromind-telegram
```

## 6. Verify

Send a message to your bot on Telegram. Check logs if issues:
```bash
sudo journalctl -u koromind-telegram -f
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `uv: command not found` | Run `source ~/.profile` or reconnect SSH |
| Bot not responding | Check logs: `sudo journalctl -u koromind-telegram -f` |
| Service fails to start | Verify all required keys in `.env` are set |
| Python version error | Ensure Python 3.11+ is installed |

## Common Operations

**Restart service:**
```bash
sudo systemctl restart koromind-telegram
```

**Update code:**
```bash
cd ~/KoroMind
git pull
source .venv/bin/activate
uv sync --frozen
sudo systemctl restart koromind-telegram
```

**Stop service:**
```bash
sudo systemctl stop koromind-telegram
```

---

## Optional: REST API

To run the REST API instead of (or alongside) Telegram:

1. Set in `.env`:
   ```
   KOROMIND_API_KEY=your_secret_key
   ```

2. Create API service:
   ```bash
   sudo tee /etc/systemd/system/koromind-api.service > /dev/null <<EOF
   [Unit]
   Description=KoroMind API
   After=network.target

   [Service]
   Type=simple
   User=$USER
   WorkingDirectory=$HOME/KoroMind
   EnvironmentFile=$HOME/KoroMind/.env
   ExecStart=$HOME/KoroMind/.venv/bin/python -m koro api --host 127.0.0.1 --port 8420
   Restart=on-failure
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   EOF
   ```

3. Start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now koromind-api
   ```

4. Test:
   ```bash
   curl -sS http://127.0.0.1:8420/api/v1/health
   ```

**External access:** Change `--host 0.0.0.0` and add a firewall rule for port 8420.
