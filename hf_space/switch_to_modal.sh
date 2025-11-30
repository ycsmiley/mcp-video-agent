#!/bin/bash

# Switch to Modal backend version with security

echo "🔄 Switching to Modal backend with security..."
echo ""

# Backup current app.py
if [ -f "app.py" ]; then
    echo "💾 Backing up current app.py → app_standalone.py"
    mv app.py app_standalone.py
fi

# Use Modal version
if [ -f "app_with_modal.py" ]; then
    echo "✅ Activating app_with_modal.py → app.py"
    cp app_with_modal.py app.py
else
    echo "❌ app_with_modal.py not found!"
    exit 1
fi

# Show what needs to be done
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Switched to Modal backend version!"
echo ""
echo "📝 Before pushing, you need to:"
echo ""
echo "1️⃣  Deploy Modal backend:"
echo "   cd ../backend"
echo "   modal deploy modal_app.py"
echo ""
echo "2️⃣  Get Modal tokens:"
echo "   modal token new"
echo ""
echo "3️⃣  Set HF Space Secrets:"
echo "   - MODAL_TOKEN_ID"
echo "   - MODAL_TOKEN_SECRET"
echo "   - GRADIO_PASSWORD (for authentication)"
echo "   - MAX_REQUESTS_PER_HOUR (optional, default: 10)"
echo ""
echo "4️⃣  Push to HF Space:"
echo "   git add app.py requirements.txt"
echo "   git commit -m 'Switch to Modal backend with security'"
echo "   git push hf main --force"
echo ""
echo "📖 Full guide: SECURITY_SETUP.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

