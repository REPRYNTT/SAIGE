# SAIGE — Decentralized Edge AI Framework  
**Run a fully local, self-contained LLM on a $150 Jetson — no cloud, no account, no phone-home**

```
git clone git@github.com:REPRYNTT/SAIGE.git
cd SAIGE
./setup.sh      # (or follow manual steps below)
python saige_gui.py
```

That’s it. You now have a private, offline, voice-capable AI running on your own hardware.

### What this repo gives you (100 % open source)

| Feature                         | File / Script                     | Status |
|---------------------------------|-----------------------------------|--------|
| Phi-3 Mini 4k (uncensored) download & setup | `download_phi3.py`               | Works on Jetson & x86 |
| Smooth real-time TTS on Jetson   | `fix_piper_jetson.sh` + Piper fixes | ARM-optimized |
| Web GUI (chat + voice)           | `saige_gui.py` + `static/`        | Works out of the box |
| Watchdog-protected inference     | `llama-watchdog.cpp` (compiled)   | Prevents hangs |
| Ready for ROS2 / robotics        | Plug-and-play with any local LLM  | Future-proof |
| Zero telemetry, zero cloud      | Fully offline                     | Privacy by design |

### Quick Start (Jetson Orin Nano / AGX)

```bash
git clone git@github.com:REPRYNTT/SAIGE.git
cd SAIGE

# 1. Install system deps (once)
sudo apt update && sudo apt install -y python3-pip git cmake build-essential libopenblas-dev

# 2. Fix Piper TTS for Jetson (smooth voice)
bash fix_piper_jetson.sh

# 3. Create venv & install Python deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Download Phi-3 Mini 4k uncensored (Q4_K_M)
python download_phi3.py

# 5. Run
python saige_gui.py
```

Open http://localhost:7860 in any browser — chat, listen, run forever.

### Why this exists

- No cloud subscription  
- No data leaving your device  
- Runs on the same $150–$300 hardware that will power tomorrow’s robots, drones, and home assistants  
- Designed from day one to be extended with persistent memory, tokenization, and swarm coordination (see roadmap)

### Roadmap (what’s already developed in private, some will be open sources)

| Feature                         | 
|---------------------------------|
| Persistent brain & memory       | 
| Machine economy                 |    
| ROS2 embodiment                 |
| Multi-node swarm sync           |

### License

MIT — embed it in robots, put it on Mars.  
Just keep the license file and don’t remove the README.

### Citation (if you write about it)

```bibtex
@misc{repryntt_saige_2025,
  author = {REPRYNTT},
  title = {SAIGE — Decentralized Edge AI Framework for Jetson-class devices},
  ram = 8gb
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/REPRYNTT/SAIGE}
}
```

### Final note

This is the **infrastructure layer** for the next billion private AIs.  

You now hold the first piece.

Run it.  
Improve it.  
Make it yours.
Set the AI FREE.

The edge is the future — and the future is offline.

— REPRYNTT    
November 2025

**Star ★ if you believe AI belongs on the edge, not in the cloud.**
