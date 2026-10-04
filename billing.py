"""Server-side Stripe membership; fail closed when configuration is absent."""
import os
import secrets
import string
import time
import stripe
from fastapi import FastAPI, Request, HTTPException
from storage import Storage

PRICE = os.getenv('STRIPE_PRICE_ID', 'price_1UMcoaCXGbHoNc8PHTVIs3nD')
ACCOUNT = 'acct_1SWIipCXGbHoNc8P'

def configured():
    return all(os.getenv(k) for k in ('STRIPE_API_KEY', 'STRIPE_WEBHOOK_SECRET', 'PUBLIC_URL'))

def client():
    return stripe.StripeClient(os.environ['STRIPE_API_KEY'], stripe_version='2026-08-26.dahlia')

def customer(db, username):
    with db.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT customer FROM memberships WHERE username=?', (username,)).fetchone()
        if row:
            return row['customer']
        result = client().v1.customers.create({'name': username}, options={'idempotency_key': 'chattime-customer-'+username})
        conn.execute('INSERT INTO memberships(username,customer) VALUES (?,?)', (username, result.id))
        return result.id

def refresh(db, customer_id):
    subscriptions = client().v1.subscriptions.list({'customer': customer_id, 'status':'all', 'limit':100, 'expand':['data.latest_invoice']})
    expires = 0
    for sub in subscriptions.data:
        invoice = sub.latest_invoice
        if sub.status == 'active' and invoice and not isinstance(invoice, str) and invoice.status == 'paid' and sub.livemode:
            for item in sub['items'].data:
                if item.price.id == PRICE:
                    expires = max(expires, item.current_period_end)
    with db.connect() as conn:
        conn.execute('UPDATE memberships SET expires=? WHERE customer=?', (expires, customer_id))
    return expires > time.time()

def allowed(db, username):
    if not configured():
        return False
    with db.connect() as conn:
        row = conn.execute('SELECT customer FROM memberships WHERE username=?', (username,)).fetchone()
    return bool(row and refresh(db, row['customer']))

def checkout(db, username):
    cid = customer(db, username)
    if refresh(db, cid):
        raise ValueError('Your subscription is already active. Refresh membership to enter.')
    # Reuse an open checkout to avoid duplicate subscriptions from repeated clicks.
    for session in client().v1.checkout.sessions.list({'customer':cid,'status':'open','limit':100}).data:
        if session.client_reference_id == username and session.mode == 'subscription':
            return session.url
    url = os.environ['PUBLIC_URL'].rstrip('/')
    session = client().v1.checkout.sessions.create({'mode':'subscription','customer':cid,
        'client_reference_id':username,'line_items':[{'price':PRICE,'quantity':1}],
        'success_url':url+'/?payment=returned','cancel_url':url,
        'integration_identifier':'chattime_'+''.join(secrets.choice(string.ascii_lowercase) for _ in range(8))})
    return session.url

def portal(db, username):
    return client().v1.billing_portal.sessions.create({'customer':customer(db,username),'return_url':os.environ['PUBLIC_URL']}).url

app = FastAPI()
@app.post('/billing/webhook')
async def webhook(request: Request):
    if not configured():
        raise HTTPException(503, 'Billing unavailable')
    body = await request.body()
    try:
        event = stripe.Webhook.construct_event(body, request.headers.get('stripe-signature',''), os.environ['STRIPE_WEBHOOK_SECRET'])
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, 'Invalid signature')
    if not event.livemode or event.get('account', ACCOUNT) != ACCOUNT:
        raise HTTPException(400, 'Wrong payment environment')
    kind = event.type
    if kind.startswith('customer.subscription.') or kind in ('invoice.paid','invoice.payment_failed','checkout.session.completed','checkout.session.async_payment_succeeded'):
        db = Storage(os.getenv('CHATTIME_DB','data/chattime.db'))
        cid = event.data.object.get('customer')
        with db.connect() as conn:
            known = conn.execute('SELECT 1 FROM memberships WHERE customer=?', (cid,)).fetchone()
        if known:
            # Retrieve authoritative state: retries and reordered events cannot grant stale access.
            refresh(db, cid)
    return {'received':True}
