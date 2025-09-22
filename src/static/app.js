let messages = [];
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const chatLogs = document.getElementById('chatLogs');
const inferenceLogs = document.getElementById('inferenceLogs');
const cmdInput = document.getElementById('cmdInput');
const cmdOutput = document.getElementById('cmdOutput');

sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
userInput.addEventListener('input', () => { userInput.style.height = 'auto'; userInput.style.height = userInput.scrollHeight + 'px'; });

function openTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
    if (tabName === 'logs') fetchLogs();
}

function addMessage(content, isUser) {
    const div = document.createElement('div');
    div.classList.add('message', isUser ? 'user-message' : 'ai-message');
    div.innerHTML = marked.parse(content);
    hljs.highlightAll();
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    addMessage(message, true);
    userInput.value = '';
    messages.push({ role: 'user', content: message });

    const eventSource = new EventSource('/api/chat?stream=true');  // Wait, no: Use fetch for stream
    let aiResponse = '';
    addMessage('', false);  // Placeholder for streaming
    const aiDiv = chatMessages.lastChild;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            aiResponse += decoder.decode(value);
            aiDiv.innerHTML = marked.parse(aiResponse);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        messages.push({ role: 'assistant', content: aiResponse });
    } catch (e) {
        addMessage('Error: ' + e, false);
    }
}

async function fetchLogs() {
    const resp = await fetch('/api/logs');
    const data = await resp.json();
    chatLogs.textContent = data.chat_logs || 'No logs';
    inferenceLogs.textContent = data.inference_logs || 'No inference logs';
}

async function verifyBlockchain() {
    // Stub: Get last log entry/signature from logs, verify
    const lastLog = chatLogs.textContent.split('---').pop().trim();
    const [entry, sigLine] = lastLog.split('Signature: ');
    const signature = sigLine.split('\n')[0];
    const resp = await fetch('/api/verify_blockchain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log_entry: entry, signature })
    });
    const data = await resp.json();
    alert(data.valid ? 'Blockchain valid' : 'Invalid: ' + data.error);
}

async function runCommand() {
    const cmd = cmdInput.value.trim();
    if (!cmd) return;
    const resp = await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
    });
    const data = await resp.json();
    cmdOutput.textContent = data.output || data.error;
}
