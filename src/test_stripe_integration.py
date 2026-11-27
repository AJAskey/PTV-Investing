"""Unit tests for stripe_service and stripe_app using mocked Stripe SDK calls."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
import stripe_app

client = TestClient(stripe_app.app)


def test_health() -> None:
    home_resp = client.get("/")
    assert home_resp.status_code == 200
    assert "PTV Investing" in home_resp.text

    console_resp = client.get("/console")
    assert console_resp.status_code == 200
    assert "Stripe Test Console" in console_resp.text

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_mock"})
@patch("stripe_service.stripe.checkout.Session.create")
def test_one_time_checkout(mock_create: MagicMock) -> None:
    mock_create.return_value = {"id": "cs_test_123", "url": "https://checkout.stripe.com/pay/cs_test_123"}
    resp = client.post(
        "/checkout/one-time",
        json={"amount_cents": 4900, "product_name": "Options Report", "customer_email": "buyer@example.com"},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "session_id": "cs_test_123",
        "url": "https://checkout.stripe.com/pay/cs_test_123",
    }
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["mode"] == "payment"


@patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_mock"})
@patch("stripe_service.stripe.checkout.Session.create")
def test_subscription_checkout(mock_create: MagicMock) -> None:
    mock_create.return_value = {"id": "cs_sub_123", "url": "https://checkout.stripe.com/pay/cs_sub_123"}
    resp = client.post(
        "/checkout/subscription",
        json={"price_id": "price_pro_monthly", "customer_email": "sub@example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "cs_sub_123"
    assert mock_create.call_args.kwargs["mode"] == "subscription"


@patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_mock"})
@patch("stripe_service.stripe.billing_portal.Session.create")
def test_billing_portal(mock_portal: MagicMock) -> None:
    mock_portal.return_value = {"id": "bps_123", "url": "https://billing.stripe.com/session/bps_123"}
    resp = client.post("/billing/portal", json={"customer_id": "cus_123"})
    assert resp.status_code == 200
    assert resp.json()["url"] == "https://billing.stripe.com/session/bps_123"


@patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_mock"})
@patch("stripe_service.stripe.Invoice.send_invoice")
@patch("stripe_service.stripe.Invoice.create")
@patch("stripe_service.stripe.InvoiceItem.create")
@patch("stripe_service.stripe.Customer.list")
def test_create_and_send_invoice(
    mock_cust_list: MagicMock,
    mock_item_create: MagicMock,
    mock_inv_create: MagicMock,
    mock_inv_send: MagicMock,
) -> None:
    mock_cust_list.return_value = MagicMock(data=[{"id": "cus_abc"}])
    mock_inv_create.return_value = {"id": "in_123", "status": "draft"}
    mock_inv_send.return_value = {
        "id": "in_123",
        "status": "open",
        "hosted_invoice_url": "https://invoice.stripe.com/i/in_123",
        "invoice_pdf": "https://invoice.stripe.com/i/in_123/pdf",
    }

    resp = client.post(
        "/invoices",
        json={
            "customer_email": "corp@example.com",
            "items": [{"description": "Custom Macro Report", "amount_cents": 25000}],
            "idempotency_key": "req-1",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["invoice_id"] == "in_123"
    assert body["status"] == "open"
    assert body["hosted_invoice_url"] == "https://invoice.stripe.com/i/in_123"
    mock_item_create.assert_called_once()
    mock_inv_create.assert_called_once()
    mock_inv_send.assert_called_once_with("in_123")


@patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_mock", "STRIPE_WEBHOOK_SECRET": "whsec_mock"})
@patch("stripe_service.stripe.Webhook.construct_event")
def test_webhook(mock_construct: MagicMock) -> None:
    mock_construct.return_value = {
        "id": "evt_123",
        "type": "invoice.paid",
        "data": {"object": {"id": "in_123"}},
    }
    resp = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "t=1,v1=abc"},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "received": True,
        "handled": True,
        "event_id": "evt_123",
        "event_type": "invoice.paid",
        "object_id": "in_123",
    }


if __name__ == "__main__":
    test_health()
    test_one_time_checkout()
    test_subscription_checkout()
    test_billing_portal()
    test_create_and_send_invoice()
    test_webhook()
    print("All Stripe integration tests passed.")
