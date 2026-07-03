# InvestMind MCP Server

**InvestMind** is a secure, privacy-first Model Context Protocol (MCP) server that empowers AI clients (like ChatGPT, Claude Desktop, or Cursor) to act as a universal investment assistant. It securely parses Indian Consolidated Account Statements (CAS), extracts and normalizes holdings, fetches live market data, and offers advanced portfolio intelligence—all while maintaining a zero-trust privacy architecture.

---

## 🔒 Privacy by Design

We treat financial data with the highest security standards. The platform is designed so that even the developers cannot view your investment details:

1. **RAM-Only Processing:** CAS PDF decryption, parsing, and normalization occur strictly in-memory. Decrypted files or plain text passwords are never written to disk or logged.
2. **Zero PDF Storage:** The uploaded PDF byte stream is discarded immediately after parsing.
3. **AES-256-GCM Encryption:** Portfolios are encrypted using AES-256-GCM before database insertion. The database only contains unreadable encrypted blobs.
4. **Zero-Knowledge Key Derivation:** The encryption key can be derived on-the-fly using a user-provided passphrase. The server never stores the passphrase or the derived key, ensuring only the owner can decrypt the holdings.

---

## 🛠️ Exposed Tools

InvestMind registers the following tools with the MCP protocol:

* **`hello_mcp()`**: Verifies server connection.
* **`upload_cas(user_id, cas_base64, password, encryption_passphrase)`**: Parses a password-protected CAS PDF, normalizes holdings, encrypts them, and saves to MongoDB.
* **`get_holdings(user_id, encryption_passphrase)`**: Decrypts and lists the user's holdings.
* **`get_portfolio_summary(user_id, encryption_passphrase)`**: Valuates the portfolio with live prices, calculates sector weightings, and evaluates concentration risks.
* **`get_portfolio_news(user_id, encryption_passphrase)`**: Fetches corporate actions, earnings announcements, and dividend news matching the user's holdings.
* **`update_watchlist(user_id, symbols)`**: Updates the stock symbols to monitor.
* **`get_watchlist_summary(user_id)`**: Fetches live quotes for watchlisted symbols.

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
SERVER_ENCRYPTION_PASSPHRASE=use-a-strong-secret-phrase-for-fallback
```

### 3. Run Unit Tests

Execute the test suite to verify encryption, database model validation, and parsing:

```bash
python -m pytest
```

---

## 🖥️ Running the Server

### Stdio Transport (Local CLI/IDE Clients)

To use the server locally (e.g., with Claude Desktop or Cursor), run it with stdio transport:

```bash
python src/main.py --transport stdio
```

### SSE Transport (Remote/Web/ChatGPT Clients)

To run the server as an HTTP/SSE service for remote connections (such as custom apps or connectors in ChatGPT):

```bash
python src/main.py --transport sse --port 8000 --host 0.0.0.0
```

---

## 🐳 Docker Deployment

You can deploy the app along with a local MongoDB instance using Docker:

```bash
# Build and start services
docker-compose up -d
```

To use a custom cloud MongoDB (like Atlas), update the `MONGO_URI` environment variable inside `docker-compose.yml` or set it in your hosting platform (Render, Netlify, etc.) before building.

---

## 🔗 Connecting to ChatGPT

1. **Host the server:** Deploy the server to a cloud provider or expose your local port `8000` via a secure tunnel (e.g., ngrok/localtunnel):
   ```bash
   ngrok http 8000
   ```
2. **Retrieve the URL:** You will get a public HTTPS URL (e.g. `https://random-subdomain.ngrok-free.app`).
3. **Register in ChatGPT:**
   * Go to ChatGPT Connectors or Custom Actions.
   * Provide the server's endpoint: `https://your-domain.com/sse` (where ChatGPT connects to read tools) and `https://your-domain.com/messages` (for posting messages).
   * ChatGPT will automatically query your tools, and you can begin chatting about your portfolio!
