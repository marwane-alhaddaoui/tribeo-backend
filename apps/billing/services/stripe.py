import stripe
from django.conf import settings
from django.utils import timezone
from django.http import HttpRequest
from apps.users.models import CustomUser  # adapte si nom différent

def create_checkout_session(user: CustomUser, product_key: str, request: HttpRequest):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    product = settings.STRIPE_PRODUCTS.get(product_key)
    if not product or not product.get("price_id"):
        raise ValueError("Produit inconnu")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": product["price_id"], "quantity": 1}],
        success_url=request.build_absolute_uri("/billing/success"),
        cancel_url=request.build_absolute_uri("/billing/cancel"),
        customer_email=user.email,
        metadata={"user_id": user.id, "product_key": product_key},
    )
    return session

def verify_and_handle_webhook(payload: bytes, sig_header: str):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)

    if event["type"] == "checkout.session.completed":
        data = event["data"]["object"]
        user_id = data["metadata"].get("user_id")
        product_key = data["metadata"].get("product_key")
        try:
            u = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return  # ignore

        if product_key == "premium_month":
            u.plan = CustomUser.Plan.PREMIUM
        elif product_key == "coach_month":
            u.plan = CustomUser.Plan.COACH

        u.plan_expires_at = timezone.now() + timezone.timedelta(days=30)
        u.save()

    return event  # utile pour log/debug
