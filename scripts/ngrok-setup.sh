#!/bin/bash
# scripts/ngrok-setup.sh
# Starts ngrok and prints the webhook URL to paste into GitHub

set -e

echo "🚀 Starting ngrok tunnel to port 8000..."

# Start ngrok in background
ngrok http 8000 --log=stdout > /tmp/ngrok.log &
NGROK_PID=$!

# Wait for ngrok to start
sleep 3

# Get the public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data['tunnels']:
    if t['proto'] == 'https':
        print(t['public_url'])
        break
")

if [ -z "$NGROK_URL" ]; then
    echo "❌ Could not get ngrok URL. Is ngrok installed?"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

WEBHOOK_URL="${NGROK_URL}/api/webhooks/github"

echo ""
echo "✅ ngrok running!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Webhook URL (paste into GitHub):"
echo "  ${WEBHOOK_URL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "GitHub Setup:"
echo "  1. Go to your repo → Settings → Webhooks → Add webhook"
echo "  2. Payload URL: ${WEBHOOK_URL}"
echo "  3. Content type: application/json"
echo "  4. Secret: (value from GITHUB_WEBHOOK_SECRET in .env)"
echo "  5. Events: Pull requests"
echo ""
echo "Press Ctrl+C to stop ngrok"
wait $NGROK_PID
