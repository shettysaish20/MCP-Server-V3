# MCP Server AI Chrome Extension

A lightweight AI-powered Chrome Extension connected to a Flask-based MCP Server, enabling users to perform **complex BODMAS (Bracket, Order, Division, Multiplication, Addition, Subtraction)** operations directly from the browser.

---

## ✨ Features

- 📚 Solve complex mathematical expressions with full BODMAS hierarchy.
- ⚡ Instant real-time computation via a backend AI MCP server.
- 🧠 Server processes user input with decision-making and memory modules.
- 🌐 Simple and clean Chrome Extension interface.
- 🔌 Easy communication between Chrome Extension and Flask API server.

---

## 🏗️ Project Structure

```
MCP-Server-V3/
│
├── flask-api/
│   ├── action.py           # Handles mathematical operations
│   ├── decision.py         # Decides actions based on parsed user input
│   ├── memory.py           # Maintains session memory and history
│   ├── mcp_server.py       # Main Flask server running the API
│   ├── mcp_client.py       # Client utilities (if needed)
│   ├── models.py           # Defines data models for input/output
│   ├── perception.py       # Parses and understands user queries
│   └── requirements.txt    # Python dependencies
│
├── chrome-extension/
│   ├── manifest.json       # Chrome extension manifest
│   ├── popup.html          # Extension popup frontend
│   ├── popup.js            # JS logic to interact with backend server
│
├── requirements.txt        # Top-level requirements
│
└── README.md               # 📄 (You are here!)
```

---

## 🚀 How It Works

1. **User Interaction:**  
   - User opens the Chrome Extension popup.
   - Enters a math expression (e.g., `5 * (3 + 2) - 4 / 2`).

2. **Chrome Extension (Frontend):**  
   - Captures the user input.
   - Sends a `POST` request to the Flask MCP Server API.

3. **Flask API (Backend Server):**  
   - Parses the input via `perception.py`.
   - Uses `decision.py` and `action.py` to compute the correct BODMAS result.
   - Returns the final output back to the Chrome Extension.

4. **Result Display:**  
   - Extension receives the response.
   - Displays the computed answer to the user in the popup.

---

## 🛠️ Installation Guide

### 1. Set Up the MCP Server

```bash
# Clone the repo
git clone https://github.com/shettysaish20/MCP-Server-V3.git
cd MCP-Server-V3/flask-api

# Install Python dependencies
pip install -r requirements.txt

# Run the server
python mcp_client.py
```

By default, server runs at: `http://localhost:5000/`

---

### 2. Set Up the Chrome Extension

- Open `chrome://extensions/` in Chrome.
- Enable **Developer Mode**.
- Click **Load unpacked** and select the `chrome-extension/` folder.
- Extension will appear in the browser toolbar.

---

### 3. Usage

- Click on the MCP extension icon.
- Type a BODMAS-based math query.
- View instant computed results!

---

## 📦 Dependencies

- **Backend (Python):**
  - Flask
  - Flask-Cors

> *(All backend libraries are listed in `requirements.txt`.)*

- **Frontend (Extension):**
  - Pure JavaScript + HTML/CSS (no external libraries).
  
---

## 📄 License

MIT License.  
Feel free to modify, extend, and enhance as you wish!

---

## 👨‍💻 Author

Built with ❤️ by [Saish Shetty](https://github.com/shettysaish20)

---