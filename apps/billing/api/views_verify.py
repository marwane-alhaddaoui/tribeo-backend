# apps/billing/views_verify.py
import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.billing.models import BillingProfile
from .views import StripeWebhookView, PRICE_TO_PLAN  

from apps.audit.utils import audit_log

stripe.api_key = settings.STRIPE_SECRET_KEY


class VerifyCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        session_id = request.data.get("session_id")
        if not session_id:
            return Response({"error": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Récupère la session Stripe + subscription + customer
            sess = stripe.checkout.Session.retrieve(
                session_id,
                expand=["subscription", "customer"]
            )
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Sécurité: la session doit appartenir à l'utilisateur connecté
        ref_id = str(sess.get("client_reference_id") or sess.get("metadata", {}).get("user_id"))
        if str(request.user.id) != ref_id:
            return Response({"error": "Session does not belong to this user"}, status=status.HTTP_403_FORBIDDEN)

        sub = sess.get("subscription")
        cust = sess.get("customer")
        if not sub:
            
            try:
                audit_log(request, "billing.verify_checkout_session",
                          meta={"error": "no_subscription", "session_id": session_id})
            except Exception:
                pass
            
            return Response({"error": "No subscription on this session"}, status=status.HTTP_400_BAD_REQUEST)

        # Assure/charge le BillingProfile
        bp, _ = BillingProfile.objects.get_or_create(user=request.user)
        if isinstance(cust, dict) and cust.get("id"):
            if bp.stripe_customer_id != cust["id"]:
                bp.stripe_customer_id = cust["id"]
                bp.save(update_fields=["stripe_customer_id"])

        # 1) Applique l'état d'abonnement (plan/status/price_id) via la logique centrale
        helper = StripeWebhookView()
        helper._apply_subscription_state(bp, sub)

        # 2) ⚡ Forcer le rôle depuis le price_id de la subscription (instantané)
        items = (sub.get("items", {}) or {}).get("data") or []
        price_id = items[0]["price"]["id"] if items else None
        plan_key_from_price = PRICE_TO_PLAN.get(price_id)  # 'coach_month' | 'premium_month' | None

        # Choix du rôle prioritaire = issu du price; fallback sur bp.plan
        if plan_key_from_price == "coach_month":
            desired_role = "coach"
        elif plan_key_from_price == "premium_month":
            desired_role = "premium"
        else:
            # fallback si jamais le mapping price -> plan ne matche pas
            if bp.plan == BillingProfile.PLAN_COACH:
                desired_role = "coach"
            elif bp.plan == BillingProfile.PLAN_PREMIUM:
                desired_role = "premium"
            else:
                desired_role = "user"

        # Admin intouchable; sinon on met à jour immédiatement
        current_role = (getattr(request.user, "role", "") or "").lower()
        if current_role != "admin" and hasattr(request.user, "role"):
            if (request.user.role or "").lower() != desired_role:
                request.user.role = desired_role
                request.user.save(update_fields=["role"])
                # print(f"[verify] role updated user_id={request.user.id} -> {desired_role} (price_id={price_id})")

            try:
                audit_log(
                request,
                "billing.verify_checkout_session",
                obj=request.user,
                meta={
                    "session_id": session_id,
                    "stripe_customer_id": bp.stripe_customer_id,
                    "stripe_subscription_id": bp.stripe_subscription_id,
                    "price_id": price_id,
                    "plan": bp.plan,
                    "role": getattr(request.user, "role", None),
                },
            )
            except Exception:
                pass
            
            
        return Response({
            "status": bp.status,
            "plan": bp.plan,
            "subscription_id": bp.stripe_subscription_id,
            "role": getattr(request.user, "role", None),  # utile pour maj immédiate côté front
        }, status=status.HTTP_200_OK)
