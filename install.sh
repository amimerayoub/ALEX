#!/bin/bash
# NEXUS Installer

echo ""
echo "  ██╗███╗   ██╗███████╗████████╗ █████╗ ██╗     ██╗     "
echo "  ██║████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██║     ██║     "
echo "  ██║██╔██╗ ██║███████╗   ██║   ███████║██║     ██║     "
echo "  ██║██║╚██╗██║╚════██║   ██║   ██╔══██║██║     ██║     "
echo "  ██║██║ ╚████║███████║   ██║   ██║  ██║███████╗███████╗"
echo "  ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝"
echo ""
echo "  Installing NEXUS AI CLI Chatbot..."
echo ""

INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

# Copy main script
cp nexus.py "$INSTALL_DIR/nexus"
chmod +x "$INSTALL_DIR/nexus"

# Add shebang check
head -1 "$INSTALL_DIR/nexus" | grep -q "python3" || sed -i '1s|^|#!/usr/bin/env python3\n|' "$INSTALL_DIR/nexus"

# Check PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "  Adding $INSTALL_DIR to PATH..."
    echo "" >> ~/.bashrc
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> ~/.bashrc
    echo "  ✓ Added to ~/.bashrc (restart terminal or run: source ~/.bashrc)"
else
    echo "  ✓ $INSTALL_DIR already in PATH"
fi

echo ""
echo "  ✓ NEXUS installed at: $INSTALL_DIR/nexus"
echo ""
echo "  Quick start:"
echo "    nexus                           # Start chat"
echo "    nexus --help                    # Show help"
echo ""
echo "  Set your API keys:"
echo "    export ANTHROPIC_API_KEY='...'  # Claude"
echo "    export OPENAI_API_KEY='...'     # GPT"  
echo "    export GEMINI_API_KEY='...'     # Gemini"
echo "  Or set inside NEXUS with: /keys"
echo ""
