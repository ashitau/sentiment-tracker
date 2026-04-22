#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# ET Now Sentiment Tracker — one-shot deployment script
#
# Prerequisites (install these first):
#   brew install railway vercel
#   npm install -g vercel
#
# Run: bash scripts/deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

step()  { echo -e "\n${BLUE}▶ $1${NC}"; }
ok()    { echo -e "${GREEN}✓ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠ $1${NC}"; }
abort() { echo -e "${RED}✗ $1${NC}"; exit 1; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# ── 0. Preflight checks ───────────────────────────────────────────────────────
step "Checking prerequisites"
command -v railway &>/dev/null || abort "railway CLI not found. Install: brew install railway"
command -v vercel  &>/dev/null || abort "vercel CLI not found.  Install: npm install -g vercel"
command -v git     &>/dev/null || abort "git not found"
ok "All CLI tools present"

# ── 1. Railway (backend) ──────────────────────────────────────────────────────
step "Deploying backend to Railway"
echo ""
echo "You'll need:"
echo "  • REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET"
echo "  • AUTH_SECRET_KEY  (run: python -c \"import secrets; print(secrets.token_hex(32))\")"
echo "  • ALLOWED_EMAILS   (comma-separated, e.g. user1@etnow.com,user2@etnow.com)"
echo "  • RESEND_API_KEY   (from https://resend.com)"
echo "  • MONGO_URI        (from MongoDB Atlas)"
echo ""
warn "Railway will open in your browser for login if not already authenticated."

railway login
railway init --name sentiment-tracker-api
railway up --detach

RAILWAY_URL=$(railway status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('deploymentUrl',''))" 2>/dev/null || echo "")
if [ -z "$RAILWAY_URL" ]; then
    warn "Could not auto-detect Railway URL. Check your Railway dashboard."
    echo -n "Enter your Railway deployment URL (e.g. https://sentiment-tracker-api.up.railway.app): "
    read -r RAILWAY_URL
fi
ok "Backend deploying at: $RAILWAY_URL"

# Update vercel.json with actual Railway URL
sed -i.bak "s|https://sentiment-tracker-api.up.railway.app|$RAILWAY_URL|g" frontend/vercel.json
rm -f frontend/vercel.json.bak

echo ""
echo -e "${YELLOW}Set these environment variables in Railway dashboard → Variables:${NC}"
echo "  REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT"
echo "  AUTH_SECRET_KEY, ALLOWED_EMAILS, RESEND_API_KEY"
echo "  MONGO_URI, MONGO_DB=sentiment_tracker"
echo "  APP_ENV=production, FRONTEND_URL=<your-vercel-url>"
echo ""
echo -n "Press Enter once you've set the Railway env vars and the backend is live..."
read -r

# ── 2. Vercel (frontend) ──────────────────────────────────────────────────────
step "Deploying frontend to Vercel"
cd frontend

vercel --prod --yes

VERCEL_URL=$(vercel ls --scope personal 2>/dev/null | grep sentiment-tracker | awk '{print $2}' | head -1 || echo "")
if [ -z "$VERCEL_URL" ]; then
    echo -n "Enter your Vercel deployment URL (e.g. https://sentiment-tracker.vercel.app): "
    read -r VERCEL_URL
fi
ok "Frontend live at: https://$VERCEL_URL"
cd "$REPO_ROOT"

# ── 3. Post-deploy ────────────────────────────────────────────────────────────
step "Post-deployment steps"
echo ""
echo "1. In Railway dashboard, set FRONTEND_URL=https://$VERCEL_URL"
echo "   (allows CORS and correct magic link redirect)"
echo ""
echo "2. In Resend (https://resend.com/domains):"
echo "   - Add and verify your sending domain (e.g. etnow-tracker.com)"
echo "   - Update the 'from' address in backend/auth/magic_link.py if needed"
echo ""
echo "3. Test the auth flow:"
echo "   - Open https://$VERCEL_URL"
echo "   - Enter one of your ALLOWED_EMAILS"
echo "   - Click the magic link in your inbox"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Deployment complete!${NC}"
echo -e "${GREEN}  Frontend: https://$VERCEL_URL${NC}"
echo -e "${GREEN}  Backend:  $RAILWAY_URL${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
