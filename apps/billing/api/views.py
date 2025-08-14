# apps/billing/views.py

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from apps.billing.models import BillingProfile

stripe.api_key = settings.STRIPE_SECRET_KEY

# mapping inverse price_id -> plan_key
PRICE_TO_PLAN = {
    (cfg.get("price_id") or "").strip(): key
    for key, cfg in settings.STRIPE_PRODUCTS.items()
    if (cfg.get("price_id") or "").strip()
}


class CreateCheckoutSessionView(APIView):
    """Crée une session Stripe Checkout pour un plan donné"""
    permission_classes = [IsAuthenticated]

    def post(self, request, product_key, *args, **kwargs):
        product_cfg = settings.STRIPE_PRODUCTS.get(product_key)
        if not product_cfg or not product_cfg.get("price_id"):
            return Response(
                {"error": f"Unknown or unconfigured product '{product_key}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        price_id = product_cfg["price_id"]

        # Associer un customer Stripe si inexistant
        bp, _ = BillingProfile.objects.get_or_create(user=request.user)
        if not bp.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={"app_user_id": str(request.user.id)},
            )
            bp.stripe_customer_id = customer.id
            bp.save(update_fields=["stripe_customer_id"])

        # Créer la session Checkout
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=bp.stripe_customer_id,
            client_reference_id=str(request.user.id),
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            # aligne avec la route front /billing/cancel (évite /cancelled si elle n'existe pas)
            cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",
            automatic_tax={"enabled": False},
            allow_promotion_codes=True,
        )

        # Réponse standardisée (contrat API stable)
        return Response(
            {"checkout_url": session.url, "session_id": session.id},
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """Reçoit et traite les événements Stripe"""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except Exception:
            return HttpResponse(status=400)

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data)
        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            self._handle_subscription_update(data)

        return HttpResponse(status=200)

    def _apply_subscription_state(self, bp: BillingProfile, sub_obj):
        bp.stripe_subscription_id = sub_obj["id"]
        bp.status = sub_obj["status"]
        bp.cancel_at = sub_obj.get("cancel_at")
        bp.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)

        if sub_obj.get("items", {}).get("data"):
            bp.stripe_price_id = sub_obj["items"]["data"][0]["price"]["id"]

        plan_key = PRICE_TO_PLAN.get(bp.stripe_price_id)
        if plan_key == "coach_month":
            bp.plan = BillingProfile.PLAN_COACH
        elif plan_key == "premium_month":
            bp.plan = BillingProfile.PLAN_PREMIUM
        else:
            bp.plan = BillingProfile.PLAN_FREE

        bp.save()

    def _handle_checkout_completed(self, data):
        user_id = data.get("client_reference_id")
        sub_id = data.get("subscription")
        if user_id and sub_id:
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                sub = stripe.Subscription.retrieve(sub_id)
                self._apply_subscription_state(user.billing, sub)
            except User.DoesNotExist:
                pass

    def _handle_subscription_update(self, data):
        sub_id = data["id"]
        try:
            bp = BillingProfile.objects.get(stripe_subscription_id=sub_id)
            self._apply_subscription_state(bp, data)
        except BillingProfile.DoesNotExist:
            pass


class VerifyCheckoutSessionView(APIView):
    """
    Dev/test: consomme session_id pour appliquer l'abonnement
    sans dépendre du Stripe CLI / webhook.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        session_id = request.data.get("session_id")
        if not session_id:
            return Response(
                {"error": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sess = stripe.checkout.Session.retrieve(
                session_id,
                expand=["subscription", "customer"],
            )
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Sécurité: la session doit appartenir à l’utilisateur
        ref_id = str(sess.get("client_reference_id") or sess.get("metadata", {}).get("user_id"))
        if str(request.user.id) != ref_id:
            return Response(
                {"error": "Session does not belong to this user"},
                status=status.HTTP_403_FORBIDDEN,
            )

        sub = sess.get("subscription")
        cust = sess.get("customer")
        if not sub:
            return Response(
                {"error": "No subscription on this session"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bp, _ = BillingProfile.objects.get_or_create(user=request.user)
        if isinstance(cust, dict) and cust.get("id"):
            bp.stripe_customer_id = cust["id"]
            bp.save(update_fields=["stripe_customer_id"])

        # Réutilise la logique centrale du webhook
        helper = StripeWebhookView()
        helper._apply_subscription_state(bp, sub)

        return Response(
            {
                "status": bp.status,
                "plan": bp.plan,
                "subscription_id": bp.stripe_subscription_id,
            },
            status=status.HTTP_200_OK,
        )


class QuotasView(APIView):
    """Retourne les quotas en fonction du plan actuel"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        bp, _ = BillingProfile.objects.get_or_create(user=request.user)
        if bp.plan == BillingProfile.PLAN_COACH:
            quotas = {"max_sessions": 999, "max_groups": 999, "max_participations": 999}
        elif bp.plan == BillingProfile.PLAN_PREMIUM:
            quotas = {"max_sessions": 10, "max_groups": 5, "max_participations": 20}
        else:  # free
            quotas = {"max_sessions": 2, "max_groups": 1, "max_participations": 5}

        return Response({"plan": bp.plan, "quotas": quotas})
