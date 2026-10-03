# Chattime Assistant — working baseline

This package replaces the pasted, disconnected snippets with one executable Streamlit app.
Includes OpenAI/Ollama switching, bounded multi-step tools, decimal area calculation,
optional Tavily search, salted scrypt password hashing, per-user/per-engine SQLite
history, reset, TXT export, feedback, and provider-reported token totals.

## Run on your computer

Requires Python 3.11+.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Windows: copy .env.example .env
# Edit .env with your server-side credentials; never commit it.
streamlit run app.py
```

For local mode, install Ollama and run `ollama pull llama3.1` on the SAME machine
as the Python server. In Docker, configure OLLAMA_HOST to a reachable Ollama
service; localhost inside a container is the container itself. A hosted Streamlit
app cannot automatically connect to each visitor's laptop Ollama instance.
Cloud mode requires separately billed OpenAI API access. Search is opt-in and
requires Tavily credentials; it sends the search query outside the local machine.

## Docker

```sh
docker compose up -d --build
```

Visit http://localhost:8501. Compose binds only to loopback; use an HTTPS reverse
proxy for public access. Persist `/app/data` on the host/platform. Ephemeral app
filesystems are unsuitable for this SQLite deployment. One app instance only.

## Deployment status and scope

NOT publicly deployed. No live API calls or real Ollama inference were verified
in the build environment. Tests use fake model clients to verify both tool loops.
Do not label this enterprise-tested or production complete.

Google OAuth, PostgreSQL, vector document retrieval, image uploads, messaging
webhooks, CI/CD deployment, billing, streaming and fine-tuning are NOT implemented
in this baseline. Do not copy the original placeholder URLs or webhook handlers
into a public service. Public scaling also needs persistent shared storage,
centrally enforced login throttling, account recovery, usage reservation/budget
controls, monitoring, backups and a complete security review. The current login
delay is session-local and is not a distributed rate limit.

No automatic external actions are available to the AI. Only explicitly registered
read-only search and area tools can execute. Tokens shown are returned by the
provider for completed requests; failed requests may still incur charges.

## Tests

```sh
python -m unittest discover -s tests -v
```
