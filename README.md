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

## Paid membership deployment

Chattime has a separate live Stripe price `price_1UMcoaCXGbHoNc8PHTVIs3nD` for $9.99 USD/month in the Family International Home Builders LLC merchant account. No existing subscriptions are changed.

Set Railway secrets `STRIPE_API_KEY` (a restricted key with Customers read/write, Checkout Sessions read/write, Subscriptions read, Invoices read, Prices read, and Customer Portal write), `STRIPE_WEBHOOK_SECRET`, and `OPENAI_API_KEY`. Set `PUBLIC_URL` to the app HTTPS URL and `STRIPE_PRICE_ID` to the price above. Never commit credentials.

Register `/billing/webhook` in Stripe for customer.subscription.created, updated, deleted; invoice.paid, invoice.payment_failed; checkout.session.completed and checkout.session.async_payment_succeeded. Use the endpoint's signing secret. The app stays locked while payment configuration is missing. Paid access requires an active live subscription, a paid latest invoice, and the exact Chattime price. Server-side subscription checks on each rerun protect returning customers and handle delayed events. Signed webhook events retrieve current state so retries and event ordering cannot grant stale access. Configure the Stripe customer portal for subscription cancellation and payment method changes.

Nginx listens on port 8501 and routes the UI and signed webhook handler to internal services. Persist `/app/data`; use one replica with this SQLite baseline. This is not the entire enterprise blueprint: no strict monthly token quota, OAuth, RAG, or enterprise integrations are provided yet. New Chattime checkouts use Stripe Managed Payments for applicable indirect tax. The confirmed product tax code is txcd_10105002 (cloud-based AI for business use). Tax is calculated by Stripe at checkout and may be added to the $9.99 base price. No existing Family products or subscriptions are modified.

Run all tests with `python -m unittest discover -v`.
