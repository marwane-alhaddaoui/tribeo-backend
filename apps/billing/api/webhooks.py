# apps/billing/api/webhooks.py
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from apps.billing.models import BillingProfile

stripe.api_key = settings.STRIPE_SECRET_KEY

# map inverse: price_id -> plan_key
PRICE_TO_PLAN = {
    (cfg.get("price_id") or "").strip(): plan
    for plan, cfg in settings.STRIPE_PRODUCTS.items()
    if (cfg.get("price_id") or "").strip()
}

def _apply_subscription_state(bp: BillingProfile, sub_obj):
    bp.stripe_subscription_id = sub_obj["id"]
    bp.status = sub_obj["status"]
    bp.cancel_at = sub_obj.get("cancel_at")
    bp.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)

    price_id = None
    items = sub_obj.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        bp.stripe_price_id = price_id

    # déduire le plan proprement
    plan_key = PRICE_TO_PLAN.get(price_id)
    if plan_key == "coach_month":
        bp.plan = BillingProfile.PLAN_COACH
    elif plan_key == "premium_month":
        bp.plan = BillingProfile.PLAN_PREMIUM
    else:
        bp.plan = BillingProfile.PLAN_FREE

    bp.save()

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig = request.META.get("HTTP_STRIPE_SIGNATURE")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        return HttpResponse(status=400)

    t = event["type"]
    data = event["data"]["object"]

    if t == "checkout.session.completed":
        user_id = data.get("client_reference_id")
        sub_id = data.get("subscription")
        if user_id and sub_id:
            User = get_user_model()
            try:
                u = User.objects.get(id=user_id)
                sub = stripe.Subscription.retrieve(sub_id)
                _apply_subscription_state(u.billing, sub)
            except User.DoesNotExist:
                pass

    elif t in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub_id = data["id"]
        try:
            bp = BillingProfile.objects.get(stripe_subscription_id=sub_id)
            _apply_subscription_state(bp, data)
        except BillingProfile.DoesNotExist:
            pass

    return HttpResponse(status=200)
