from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from apps.billing.api.serializers import QuotasSerializer
from apps.billing.services.quotas import usage_for, get_limits_for
from apps.billing.services.stripe import create_checkout_session, verify_and_handle_webhook

class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, product_key):
        try:
            session = create_checkout_session(request.user, product_key, request)
            return Response({"checkout_url": session.url})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            verify_and_handle_webhook(request.body, sig)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_200_OK)

class QuotasView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        s = QuotasSerializer.from_user(request.user)
        return Response(s.data)
