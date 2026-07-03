# InvestMind MCP Server

**InvestMind** is a secure, privacy-first Model Context Protocol (MCP) server that empowers AI clients (like ChatGPT, Claude Desktop, or Cursor) to act as a universal investment assistant. It securely parses Indian Consolidated Account Statements (CAS), extracts and normalizes holdings, fetches live market data, and offers advanced portfolio intelligence—all while maintaining a zero-trust privacy architecture.

---

## 🔒 Privacy & Zero-Knowledge Architecture

We treat financial data with the highest security standards. The platform is designed so that even the developers cannot view your investment details:

1. **RAM-Only Processing:** CAS PDF decryption, parsing, and normalization occur strictly in-memory. Decrypted files or plain text passwords are never written to disk or logged.
2. **Zero PDF Storage:** The uploaded PDF byte stream is discarded immediately after parsing.
3. **AES-256-GCM Encryption:** Portfolios are encrypted using AES-256-GCM before database insertion. The database only contains unreadable encrypted blobs.
4. **Zero-Knowledge Key Derivation:** The decryption key is derived on-the-fly using a user-provided passphrase.
5. **Secure In-Memory Session Cache:** Decryption keys are **never** stored in the JWT or sent back to the client. Keys live purely in-memory in a server-side session cache (`_active_sessions`) mapped to a temporary UUID session ID.
6. **Query Traffic Blending (Decoy Mixing):** Queries to external APIs (Yahoo Finance for quotes and news) mix user tickers with random decoy tickers to make it harder to infer your exact portfolio composition from network traffic. **Note:** This is a basic traffic blending technique, not a cryptographic anonymization mechanism. It does not meaningfully anonymize your holdings against a determined network observer.

---

## 🧠 Killer Feature: Portfolio Intelligence

InvestMind MCP is designed for **AI-first** portfolio management. Rather than relying on rigid dashboards or complex technical tools, it exposes a high-level **Portfolio Intelligence** module that empowers ChatGPT, Claude, and other LLMs to act as your personal wealth manager.

Instead of calling raw data APIs, the AI can seamlessly answer natural language questions like:

* *"Why is my portfolio down today?"*
* *"Am I overexposed to one sector?"*
* *"Which of my holdings have negative news or technical breakdowns?"*
* *"How much dividend income can I expect this year?"*
* *"What are the largest risks in my portfolio right now?"*

### Key AI-Native Tools Exposed:
* `ask_portfolio(query)`
* `why_portfolio_down()`
* `largest_risks()`
* `largest_opportunities()`
* `portfolio_health()`
* `rebalance_portfolio()`
* `dividend_projection()`
* `upcoming_events()`

*(Under the hood, these tools automatically aggregate granular technicals like RSI, MACD, fundamental valuations, and live market data so the LLM doesn't have to piece them together manually.)*

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* MongoDB instance (Local or Atlas cloud connection string)

### 1. Local Setup

Clone this repository to your system, create a virtual environment, and install dependencies:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```env
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/investmind
MONGO_DB_NAME=investmind
JWT_SECRET_KEY=generate-a-secure-random-secret-for-production
```

---

## 🖥️ Running the Server

### Stdio Transport (Local CLI/IDE Clients like Claude Desktop)

Stdio transport is stateful for the lifecycle of the process. You can configure automatic authentication on startup by providing the credentials in the environment:

```bash
# On Windows (PowerShell):
$env:INVESTMIND_USER_ID="my_username"
$env:INVESTMIND_PASSWORD="my_secure_password"
$env:INVESTMIND_PASSPHRASE="my_portfolio_passphrase"
python src/main.py --transport stdio

# On Linux/macOS:
INVESTMIND_USER_ID="my_username" INVESTMIND_PASSWORD="my_secure_password" INVESTMIND_PASSPHRASE="my_portfolio_passphrase" python src/main.py --transport stdio
```

Alternatively, you can call the `login(user_id, password_plain, passphrase)` tool directly over the stdio session after launching the server.

### SSE Transport (Remote/Web/ChatGPT Connectors)

To run the server as an HTTP/SSE service for remote connections:

```bash
python src/main.py --transport sse --port 8000 --host 0.0.0.0
```

Authenticating requests in SSE mode requires exchanging your username, password, and passphrase for an access token:
1. POST `/api/auth/token` with `{"user_id": "...", "password": "...", "passphrase": "..."}` to obtain a JWT.
2. Authenticate subsequent `/sse` and `/messages` requests by passing the token in the `Authorization: Bearer <token>` header or as a `?token=...` query parameter.
