"""FastAPI web endpoints for ptv-investing.net Stripe Payments, Billing, and Invoicing."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from pydantic import BaseModel, Field

import gen_logging
import stripe_service

logger = gen_logging.setup_logging(logger_name="Stripe_App")
app = FastAPI(title="PTV Investing Stripe API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LANDING_HTML_PATH = Path(__file__).resolve().parent.parent / "subs" / "ptv-investing.html"


class OneTimeCheckoutRequest(BaseModel):
    price_id: str | None = None
    amount_cents: int | None = Field(default=None, gt=0)
    product_name: str = "PTV Investing Data Report"
    currency: str = "usd"
    quantity: int = Field(default=1, gt=0)
    customer_email: str | None = None
    customer_id: str | None = None
    metadata: dict[str, str] | None = None


class SubscriptionCheckoutRequest(BaseModel):
    price_id: str
    quantity: int = Field(default=1, gt=0)
    customer_email: str | None = None
    customer_id: str | None = None
    trial_period_days: int | None = Field(default=None, ge=1)
    metadata: dict[str, str] | None = None


class PortalSessionRequest(BaseModel):
    customer_id: str
    return_url: str | None = None


class InvoiceItemInput(BaseModel):
    description: str
    amount_cents: int = Field(gt=0)
    currency: str = "usd"


class InvoiceCreateRequest(BaseModel):
    customer_email: str
    customer_name: str | None = None
    items: list[InvoiceItemInput]
    days_until_due: int = Field(default=30, ge=1)
    auto_advance: bool = True
    memo: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, str] | None = None


@app.get("/", response_class=HTMLResponse)
def landing_page() -> str:
    if LANDING_HTML_PATH.exists():
        return LANDING_HTML_PATH.read_text(encoding="utf-8")
    return console()


@app.get("/console", response_class=HTMLResponse)
def console() -> str:
    load_dotenv(override=True)
    configured = bool(os.getenv("STRIPE_SECRET_KEY", "").strip())
    status_badge = (
        '<span style="color:#0a7d32;font-weight:bold;">Connected (STRIPE_SECRET_KEY found)</span>'
        if configured
        else '<span style="color:#b45309;font-weight:bold;">Not configured yet — add STRIPE_SECRET_KEY=sk_test_... to .env</span>'
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PTV Investing — Stripe Test Console</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 720px; margin: 24px auto; padding: 0 16px; color: #1f2937; }}
    h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0; }}
    label {{ display: block; font-size: 0.9rem; margin-top: 8px; font-weight: 600; }}
    input {{ width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 4px; }}
    button {{ margin-top: 12px; padding: 10px 16px; background: #635bff; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }}
    button:hover {{ background: #4f46e5; }}
    pre {{ background: #f9fafb; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>PTV Investing — Stripe Test Console</h1>
  <p>Status: {status_badge}</p>
  <p><a href="/docs">Open API Docs</a></p>

  <div class="card">
    <h2>1. One-Time Payment Checkout</h2>
    <label>Product Name <input id="ot_name" value="PTV Investing Options Report" /></label>
    <label>Amount (USD cents, e.g. 4900 = $49.00) <input id="ot_amount" type="number" value="4900" /></label>
    <label>Customer Email (optional) <input id="ot_email" placeholder="buyer@example.com" /></label>
    <button onclick="startOneTime()">Create Checkout Link</button>
  </div>

  <div class="card">
    <h2>2. Create &amp; Send Invoice</h2>
    <label>Customer Email <input id="inv_email" placeholder="client@example.com" /></label>
    <label>Description <input id="inv_desc" value="Custom Economic &amp; Stock Analysis" /></label>
    <label>Amount (USD cents, e.g. 25000 = $250.00) <input id="inv_amount" type="number" value="25000" /></label>
    <button onclick="sendInvoice()">Create &amp; Send Invoice</button>
  </div>

  <pre id="output">Results will appear here...</pre>

  <script>
    async function postJson(url, body) {{
      const out = document.getElementById('output');
      out.textContent = 'Working...';
      const resp = await fetch(url, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(body),
      }});
      const data = await resp.json();
      out.textContent = JSON.stringify(data, null, 2);
      const link = data.url || data.hosted_invoice_url;
      if (link) {{
        out.innerHTML += '\\n\\n<a href="' + link + '" target="_blank">Open Stripe Page &rarr;</a>';
      }}
    }}
    function startOneTime() {{
      const email = document.getElementById('ot_email').value.trim();
      postJson('/checkout/one-time', {{
        product_name: document.getElementById('ot_name').value,
        amount_cents: Number(document.getElementById('ot_amount').value),
        customer_email: email || null,
      }});
    }}
    function sendInvoice() {{
      postJson('/invoices', {{
        customer_email: document.getElementById('inv_email').value.trim(),
        items: [{{
          description: document.getElementById('inv_desc').value,
          amount_cents: Number(document.getElementById('inv_amount').value),
        }}],
      }});
    }}
  </script>
</body>
</html>"""


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "stripe_configured": bool(os.getenv("STRIPE_SECRET_KEY", "").strip()),
    }


@app.get("/prices")
def get_prices() -> dict[str, Any]:
    try:
        return {"prices": stripe_service.list_active_prices()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@app.post("/checkout/one-time")
def create_one_time_checkout(req: OneTimeCheckoutRequest, request: Request) -> dict[str, Any]:
    try:
        base = _base_url(request)
        return stripe_service.create_one_time_checkout_session(
            price_id=req.price_id,
            amount_cents=req.amount_cents,
            product_name=req.product_name,
            currency=req.currency,
            quantity=req.quantity,
            customer_email=req.customer_email,
            customer_id=req.customer_id,
            success_url=os.getenv("STRIPE_SUCCESS_URL") or f"{base}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=os.getenv("STRIPE_CANCEL_URL") or f"{base}/checkout/cancel",
            metadata=req.metadata,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/checkout/subscription")
def create_subscription_checkout(req: SubscriptionCheckoutRequest, request: Request) -> dict[str, Any]:
    try:
        base = _base_url(request)
        return stripe_service.create_subscription_checkout_session(
            price_id=req.price_id,
            quantity=req.quantity,
            customer_email=req.customer_email,
            customer_id=req.customer_id,
            trial_period_days=req.trial_period_days,
            success_url=os.getenv("STRIPE_SUCCESS_URL") or f"{base}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=os.getenv("STRIPE_CANCEL_URL") or f"{base}/checkout/cancel",
            metadata=req.metadata,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/billing/portal")
def create_portal(req: PortalSessionRequest, request: Request) -> dict[str, Any]:
    try:
        base = _base_url(request)
        return stripe_service.create_customer_portal_session(
            customer_id=req.customer_id,
            return_url=req.return_url or os.getenv("STRIPE_PORTAL_RETURN_URL") or f"{base}/",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/invoices")
def create_invoice(req: InvoiceCreateRequest) -> dict[str, Any]:
    try:
        customer = stripe_service.get_or_create_customer(
            email=req.customer_email,
            name=req.customer_name,
        )
        return stripe_service.create_and_send_invoice(
            customer_id=customer["id"],
            items=[item.model_dump() for item in req.items],
            days_until_due=req.days_until_due,
            auto_advance=req.auto_advance,
            memo=req.memo,
            idempotency_key=req.idempotency_key,
            metadata=req.metadata,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/checkout/success", response_class=HTMLResponse)
def checkout_success(session_id: str | None = None) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><body style="font-family:system-ui,sans-serif;max-width:560px;margin:48px auto;padding:0 16px;">
  <h1>Payment Successful</h1>
  <p>Thank you for your PTV Investing purchase. Session ID: <code>{session_id or ""}</code></p>
  <p><a href="/">Return to PTV Investing</a></p>
</body></html>"""


@app.get("/checkout/cancel", response_class=HTMLResponse)
def checkout_cancel() -> str:
    return """<!DOCTYPE html>
<html lang="en"><body style="font-family:system-ui,sans-serif;max-width:560px;margin:48px auto;padding:0 16px;">
  <h1>Checkout Canceled</h1>
  <p>No charge was made.</p>
  <p><a href="/">Return to PTV Investing</a></p>
</body></html>"""


@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
) -> dict[str, Any]:
    payload = await request.body()
    try:
        return stripe_service.verify_and_handle_webhook(
            payload, stripe_signature, logger=logger
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
