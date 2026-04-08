#!/bin/bash
# Mini-AI Voice Pipeline Launcher
# Runs voice_pipeline.py in the venv with friendly error handling.
# Called by ~/Desktop/Mini-AI Voice.desktop on the Pi.

set -u

PROJECT_DIR="$HOME/mini-ai"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
PIPELINE="$PROJECT_DIR/voice_pipeline.py"
PANEL="$PROJECT_DIR/mini_ai_panel.py"
PICKER="$PROJECT_DIR/desktop/mini-ai-pick-model.py"
CONFIG_FILE="$HOME/.config/mini-ai/config.json"

# Pretty header
clear
echo "================================================================"
echo "  Mini-AI Voice Pipeline"
echo "================================================================"
echo ""
echo "  Speak after you see 'Listening... (5 seconds)'"
echo ""
echo "  Try:"
echo "    \"What is two plus two?\""
echo "    \"What is the capital of France?\""
echo "    \"What do you see?\"           (vision - first call slow)"
echo ""
echo "  Press Ctrl+C to quit, then close this window."
echo "================================================================"
echo ""

# First-run model picker: if no config saved yet, ask the user.
# (Subsequent runs use the saved preset and skip the picker.)
if [ ! -f "$CONFIG_FILE" ] && [ -x "$PICKER" ]; then
    echo "First run — choose a model preset..."
    "$VENV_PYTHON" "$PICKER" || true
    echo ""
fi

# Sanity checks
if [ ! -x "$VENV_PYTHON" ]; then
    echo "ERROR: venv python not found at $VENV_PYTHON"
    echo "Did setup_all.py finish successfully?"
    read -p "Press Enter to close..."
    exit 1
fi

if [ ! -f "$PIPELINE" ]; then
    echo "ERROR: voice_pipeline.py not found at $PIPELINE"
    read -p "Press Enter to close..."
    exit 1
fi

if [ ! -f "$PANEL" ]; then
    echo "ERROR: mini_ai_panel.py not found at $PANEL"
    read -p "Press Enter to close..."
    exit 1
fi

# Verify Ollama is running before we start (the pipeline will hang otherwise)
if ! curl -fsS --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "WARNING: Ollama API at localhost:11434 is not responding."
    echo "Trying to start the service..."
    sudo systemctl start ollama 2>&1 || true
    sleep 3
    if ! curl -fsS --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "ERROR: Could not reach Ollama. Run: sudo systemctl status ollama"
        read -p "Press Enter to close..."
        exit 1
    fi
    echo "Ollama is up."
    echo ""
fi

# Run the control panel (Tk GUI + voice loop in background thread).
# The terminal stays open and prints stderr from any uncaught exceptions.
exec "$VENV_PYTHON" "$PANEL"
