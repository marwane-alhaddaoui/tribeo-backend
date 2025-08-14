import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.billing.models import BillingProfile
from .webhooks import _apply_subscription_state  # réutilise ta logique centrale

stripe.api_key = settings.STRIPE_SECRET_KEY

class VerifyCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        session_id = request.data.get("session_id")
        if not session_id:
            return Response({"error": "session_id is required"}, status=400)

        try:
            sess = stripe.checkout.Session.retrieve(
                session_id,
                expand=["subscription", "customer"]
            )
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

        # sécurité: la session doit appartenir à l’utilisateur connecté
        ref_id = str(sess.get("client_reference_id") or sess.get("metadata", {}).get("user_id"))
        if str(request.user.id) != ref_id:
            return Response({"error": "Session does not belong to this user"}, status=403)

        sub = sess.get("subscription")
        cust = sess.get("customer")
        if not sub:
            return Response({"error": "No subscription on this session"}, status=400)

        bp, _ = BillingProfile.objects.get_or_create(user=request.user)
        if isinstance(cust, dict) and cust.get("id"):
            bp.stripe_customer_id = cust["id"]

        _apply_subscription_state(bp, sub)
        return Response({
            "status": bp.status,
            "plan": bp.plan,
            "subscription_id": bp.stripe_subscription_id
        }, status=200)
