"""Stripe integration service for ptv-investing.net (Payments, Billing, Invoicing)."""

from __future__ import annotations

import os
import uuid
from typing import Any

import stripe
from dotenv import load_dotenv

load_dotenv()


def _configure_stripe() -> str:
    """Configure the Stripe SDK with the API key from the environment."""
    load_dotenv(override=True)
    api_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "STRIPE_SECRET_KEY is not set. Add it to your .env file or environment."
        )
    stripe.api_key = api_key
    return api_key


def _default_url(env_var: str, fallback: str) -> str:
    return os.getenv(env_var, "").strip() or fallback


def _field(obj: Any, name: str, default: Any = None) -> Any:
    """Safely read a field from either a StripeObject or a plain dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def list_active_prices(limit: int = 20) -> list[dict[str, Any]]:
    """Return active Stripe prices expanded with their parent product."""
    _configure_stripe()
    prices = stripe.Price.list(active=True, limit=limit, expand=["data.product"])
    results: list[dict[str, Any]] = []
    for price in prices.auto_paging_iter():
        product = _field(price, "product")
        is_product_obj = product is not None and not isinstance(product, str)
        product_name = _field(product, "name") if is_product_obj else str(product)
        product_desc = _field(product, "description") if is_product_obj else None
        recurring = _field(price, "recurring")
        results.append(
            {
                "price_id": price["id"],
                "product_id": _field(product, "id") if is_product_obj else product,
                "product_name": product_name,
                "description": product_desc,
                "currency": price["currency"],
                "unit_amount": _field(price, "unit_amount"),
                "type": _field(price, "type"),
                "interval": _field(recurring, "interval") if recurring else None,
            }
        )
        if len(results) >= limit:
            break
    return results


def get_or_create_customer(
    email: str,
    name: str | None = None,
    metadata: dict[str, str] | None = None,
) -> stripe.Customer:
    """Find an existing Stripe customer by email or create a new one."""
    _configure_stripe()
    existing = stripe.Customer.list(email=email, limit=1)
    if existing.data:
        return existing.data[0]
    params: dict[str, Any] = {"email": email}
    if name:
        params["name"] = name
    if metadata:
        params["metadata"] = metadata
    return stripe.Customer.create(**params)


def create_one_time_checkout_session(
    *,
    price_id: str | None = None,
    amount_cents: int | None = None,
    product_name: str = "PTV Investing Data Report",
    currency: str = "usd",
    quantity: int = 1,
    customer_email: str | None = None,
    customer_id: str | None = None,
    success_url: str | None = None,
    cancel_url: str | None = None,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a Stripe-hosted Checkout Session for a one-time payment."""
    _configure_stripe()
    if not price_id and (amount_cents is None or amount_cents <= 0):
        raise ValueError("Provide either price_id or a positive amount_cents.")

    if price_id:
        line_item: dict[str, Any] = {"price": price_id, "quantity": quantity}
    else:
        line_item = {
            "price_data": {
                "currency": currency,
                "unit_amount": amount_cents,
                "product_data": {"name": product_name},
            },
            "quantity": quantity,
        }

    params: dict[str, Any] = {
        "mode": "payment",
        "line_items": [line_item],
        "success_url": success_url
        or _default_url(
            "STRIPE_SUCCESS_URL",
            "http://localhost:8000/checkout/success?session_id={CHECKOUT_SESSION_ID}",
        ),
        "cancel_url": cancel_url
        or _default_url("STRIPE_CANCEL_URL", "http://localhost:8000/checkout/cancel"),
    }
    if customer_id:
        params["customer"] = customer_id
    elif customer_email:
        params["customer_email"] = customer_email
    if metadata:
        params["metadata"] = metadata

    session = stripe.checkout.Session.create(**params)
    return {"session_id": session["id"], "url": session["url"]}


def create_subscription_checkout_session(
    *,
    price_id: str,
    quantity: int = 1,
    customer_email: str | None = None,
    customer_id: str | None = None,
    trial_period_days: int | None = None,
    success_url: str | None = None,
    cancel_url: str | None = None,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a Stripe-hosted Checkout Session for a recurring subscription."""
    _configure_stripe()
    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": quantity}],
        "success_url": success_url
        or _default_url(
            "STRIPE_SUCCESS_URL",
            "http://localhost:8000/checkout/success?session_id={CHECKOUT_SESSION_ID}",
        ),
        "cancel_url": cancel_url
        or _default_url("STRIPE_CANCEL_URL", "http://localhost:8000/checkout/cancel"),
    }
    if customer_id:
        params["customer"] = customer_id
    elif customer_email:
        params["customer_email"] = customer_email

    sub_data: dict[str, Any] = {}
    if trial_period_days and trial_period_days > 0:
        sub_data["trial_period_days"] = trial_period_days
    if metadata:
        sub_data["metadata"] = metadata
    if sub_data:
        params["subscription_data"] = sub_data

    session = stripe.checkout.Session.create(**params)
    return {"session_id": session["id"], "url": session["url"]}


def create_customer_portal_session(
    customer_id: str,
    return_url: str | None = None,
) -> dict[str, Any]:
    """Create a Stripe Customer Portal session so subscribers can self-manage plans."""
    _configure_stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url
        or _default_url("STRIPE_PORTAL_RETURN_URL", "http://localhost:8000/"),
    )
    return {"session_id": session["id"], "url": session["url"]}


def create_and_send_invoice(
    *,
    customer_id: str,
    items: list[dict[str, Any]],
    days_until_due: int = 30,
    auto_advance: bool = True,
    memo: str | None = None,
    idempotency_key: str | None = None,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create invoice items, roll them into an invoice, and optionally finalize/send it."""
    _configure_stripe()
    if not items:
        raise ValueError("At least one invoice item is required.")

    base_key = idempotency_key or str(uuid.uuid4())
    for idx, item in enumerate(items):
        stripe.InvoiceItem.create(
            customer=customer_id,
            amount=int(item["amount_cents"]),
            currency=item.get("currency", "usd"),
            description=item.get("description", "PTV Investing Analysis"),
            idempotency_key=f"{base_key}-item-{idx}",
        )

    invoice_params: dict[str, Any] = {
        "customer": customer_id,
        "collection_method": "send_invoice",
        "days_until_due": days_until_due,
        "auto_advance": auto_advance,
        "pending_invoice_items_behavior": "include",
    }
    if memo:
        invoice_params["description"] = memo
    if metadata:
        invoice_params["metadata"] = metadata

    invoice = stripe.Invoice.create(
        **invoice_params,
        idempotency_key=f"{base_key}-invoice",
    )
    if auto_advance:
        invoice = stripe.Invoice.send_invoice(invoice["id"])

    return {
        "invoice_id": invoice["id"],
        "status": _field(invoice, "status"),
        "hosted_invoice_url": _field(invoice, "hosted_invoice_url"),
        "invoice_pdf": _field(invoice, "invoice_pdf"),
    }


def verify_and_handle_webhook(
    payload: bytes,
    sig_header: str,
    logger: Any = None,
) -> dict[str, Any]:
    """Verify a Stripe webhook signature and dispatch key billing/invoicing events."""
    _configure_stripe()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise RuntimeError(
            "STRIPE_WEBHOOK_SECRET is not set. Run `stripe listen` or set it in .env."
        )

    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    event_type = event["type"]
    data_obj = event["data"]["object"]

    if logger:
        logger.info(f"Received Stripe webhook event: {event_type} ({event['id']})")

    handled = True
    if event_type == "checkout.session.completed":
        # Provision access for one-time purchase or initial subscription checkout.
        pass
    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        # Sync subscription status (active, past_due, canceled) with your user store.
        pass
    elif event_type in ("invoice.paid", "invoice.payment_failed", "charge.refunded"):
        # Reconcile invoice settlement, failed payments, or refunds.
        pass
    else:
        handled = False

    return {
        "received": True,
        "handled": handled,
        "event_id": event["id"],
        "event_type": event_type,
        "object_id": _field(data_obj, "id"),
    }
