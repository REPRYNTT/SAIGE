#!/bin/bash
# Piper TTS ARM64 Jetson Fix Script
# Run this on your Jetson to properly install Piper TTS

echo "=== SAIGE Piper TTS ARM64 Setup ==="
echo "Fixing ARM64/Jetson compatibility issues..."

# 1. Fix espeak-ng data paths (ARM64 Ubuntu issue)
echo "Step 1: Fixing espeak-ng data paths..."
sudo apt update
sudo apt install -y espeak espeak-data libespeak-dev libespeak1

# Create the expected data path symlink
if [ ! -d "/usr/share/espeak-ng-data" ]; then
    sudo ln -sf /usr/lib/aarch64-linux-gnu/espeak-ng-data /usr/share/espeak-ng-data
    echo "✓ Created espeak-ng data path symlink"
fi

# 2. Install ONNX Runtime for ARM64 (Jetson-specific)
echo "Step 2: Installing ONNX Runtime for ARM64..."
pip3 install --upgrade pip
# Use ARM64-compatible ONNX Runtime
pip3 install onnxruntime==1.15.1  # Known working version for ARM64

# 3. Install Piper TTS with proper dependencies
echo "Step 3: Installing Piper TTS..."
pip3 install piper-tts

# 4. Download a working voice model (MIT licensed)
echo "Step 4: Downloading MIT-licensed voice model..."
mkdir -p ~/SAIGE/models/piper
cd ~/SAIGE/models/piper

# Download fast, MIT-licensed model
wget -O "en_US-lessac-medium.onnx" \
    "https://github.com/rhasspy/piper/releases/download/v1.2.0/voice-en-us-lessac-medium.tar.gz"
tar -xzf voice-en-us-lessac-medium.tar.gz

# 5. Test Piper installation
echo "Step 5: Testing Piper TTS..."
echo "Hello from SAIGE!" | piper \
    --model ~/SAIGE/models/piper/en_US-lessac-medium.onnx \
    --output_file ~/SAIGE/test_piper.wav

if [ -f ~/SAIGE/test_piper.wav ] && [ -s ~/SAIGE/test_piper.wav ]; then
    echo "✅ Piper TTS working! Playing test audio..."
    aplay ~/SAIGE/test_piper.wav
    rm ~/SAIGE/test_piper.wav
else
    echo "❌ Piper TTS still not working. Check logs above."
fi

echo "=== Piper TTS ARM64 Setup Complete ==="