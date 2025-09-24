### SAIGE Setup Guide: GitHub SSH, Repo Sync, and API Servers

Save this as `saige_setup.md` in your `~/SAIGE` folder (e.g., `nano saige_setup.md`, paste, save). It's a self-contained guide for re-establishing GitHub connection, syncing the repo, and starting the chat AI servers (llama-server + Flask GUI). Run commands in a new terminal on Jetson. Assumes Git/SSH installed, key pair (`saige_ssh`/`saige_ssh.pub`) in `~/.ssh/`, and repo at `~/SAIGE`.

#### 1. **GitHub SSH Connection (Re-Auth & Test)**
This reloads your SSH key and tests auth. Run every session or add to `~/.bashrc` for auto.

- Start SSH agent:
  ```
  eval "$(ssh-agent -s)"
  ```

- Add private key:
  ```
  ssh-add ~/.ssh/saige_ssh
  ```
  - Enter passphrase if prompted.

- Test connection:
  ```
  ssh -T git@github.com
  ```
  - Expected: "Hi REPRYNTT! You've successfully authenticated..."

- Git config (run once):
  ```
  git config --global user.name "repryntt"
  git config --global user.email "nateturkeyman@gmail.com"
  ```

#### 2. **Repo Sync (Pull/Push Scripts)**
Navigate to repo and sync changes. For startup workflow, add to `~/.bashrc`: `cd ~/SAIGE && git pull origin main`.

- Navigate & pull updates:
  ```
  cd ~/SAIGE
  git pull origin main
  ```
  - Expected: "Already up to date" or merges changes.

- To push new scripts (e.g., after editing):
  ```
  git add .
  git commit -m "Update scripts for SAIGE"
  git push origin main
  ```
  - Expected: Uploads to GitHub repo.

#### 3. **Start API Servers (Chat AI)**
This launches llama-server (inference) via watchdog (auto-restart) and Flask GUI (proxy/UI on :5000). Run in separate terminals. Check logs: `tail -f logs/saige_inference.log` and `tail -f logs/saige_chat.log`.

- **Terminal 1: Start Llama-Server (Inference)**:
  ```
  cd ~/SAIGE
  ./bin/llama-watchdog &
  ```
  - Expected: PID, then logs show "model loaded" and "listening on 0.0.0.0:8080". If not built: `g++ -o bin/llama-watchdog src/llama_extensions/llama-watchdog.cpp -std=c++11`.

- **Terminal 2: Start Flask GUI (Proxy/UI)**:
  ```
  cd ~/SAIGE
  python src/saige_gui.py
  ```
  - Expected: "Running on http://10.0.0.19:5000". Access from laptop: `http://10.0.0.19:5000`.

- **Test End-to-End** (From laptop browser or Jetson curl):
  ```
  curl http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{
    "messages": [{"role": "user", "content": "Hello SAIGE!"}]
  }'
  ```
  - Expected: Streams JSON response from Phi-3.

#### 4. **Optional: Voice TTS (If Enabled)**
If Piper CLI built (`~/piper/build/piper`), it plays responses via Waveshare.

- Test CLI:
  ```
  ~/piper/build/piper --model /usr/local/share/piper/models/voice.onnx --output_file test.wav "Test voice."
  aplay -D hw:0,0 test.wav
  rm test.wav
  ```
  - Expected: Audio plays.

- In Flask, TTS triggers automatically after response.

#### 5. **Troubleshooting**
- SSH fail: `ssh -T git@github.com` → Check key added to GitHub (Settings > SSH keys).
- Pull error: `git remote -v` → Ensure `origin git@github.com:REPRYNTT/SAIGE.git`.
- Server crash: `tail logs/saige_inference.log` → OOM? Lower -c in watchdog.cpp.
- No sound: `aplay -l` → Use -D hw:0,0 for Waveshare.

#### 6. **Automate Startup (Optional)**
Add to `~/.bashrc` for auto on login:
```
echo 'eval "$(ssh-agent -s)"' >> ~/.bashrc
echo 'ssh-add ~/.ssh/saige_ssh' >> ~/.bashrc
echo 'cd ~/SAIGE && ./bin/llama-watchdog &' >> ~/.bashrc
echo 'python src/saige_gui.py &' >> ~/.bashrc
source ~/.bashrc
```
- Reboot: `sudo reboot` → Auto-starts servers.

Run `git pull` to sync this guide. Questions? Paste errors!