# apps/billing/views.py

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.db import transaction
from django.contrib.auth.models import Group  # fallback si tu utilises les groupes
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from apps.billing.models import BillingProfile

from apps.billing.api.serializers import QuotasSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY

# mapping inverse price_id -> plan_key
PRICE_TO_PLAN = {
    (cfg.get("price_id") or "").strip(): key
    for key, cfg in settings.STRIPE_PRODUCTS.items()
    if (cfg.get("price_id") or "").strip()
}


# --------- helpers rôle/plan (safe si champs absents) ---------
def _set_if_exists(obj, field, value, fields_to_update):
    if hasattr(obj, field):
        setattr(obj, field, value)
        fields_to_update.add(field)

@transaction.atomic
def _sync_user_roles_for_plan(user, plan: str):
    """
    Simple et robuste :
    - Si tu as un système Role/RoleUser (apps.account.models), on l'utilise.
    - Sinon, fallback Groupes Django: 'coach' / 'premium'.
    - Met à jour user.role / user.is_coach / user.is_premium si ces champs existent.
    """
    plan = (plan or "").lower()
    want = ["coach"] if plan == "coach" else (["premium"] if plan == "premium" else [])

    # 1) modèle custom (si présent)
    used_custom = False
    try:
        from apps.account.models import Role, RoleUser  # adapte si besoin
        roles = {r.name: r for r in Role.objects.filter(name__in=["coach", "premium"])}
        for name in ["coach", "premium"]:
            if name not in roles:
                roles[name], _ = Role.objects.get_or_create(name=name)

        RoleUser.objects.filter(user=user).exclude(role__name__in=want).delete()
        for name in want:
            RoleUser.objects.get_or_create(user=user, role=roles[name])
        used_custom = True
    except Exception:
        # 2) fallback groupes
        for name in ["coach", "premium"]:
            grp, _ = Group.objects.get_or_create(name=name)
            if name in want:
                user.groups.add(grp)
            else:
                user.groups.remove(grp)

    # 3) flags/role basiques si dispo
    fields = set()
    _set_if_exists(user, "is_coach",   "coach" in want, fields)
    _set_if_exists(user, "is_premium", "premium" in want, fields)
    # Si tu as un champ textuel role ET que l'user n'est pas admin, on le met à jour aussi
    if hasattr(user, "role") and (getattr(user, "role", "") or "").lower() != "admin":
        _set_if_exists(user, "role", "coach" if "coach" in want else ("user" if want else "user"), fields)
    if fields:
        user.save(update_fields=list(fields))


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
            cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",  # aligne avec ton front
            automatic_tax={"enabled": False},
            allow_promotion_codes=True,
        )

        # Réponse standardisée
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
    # --- MAJ BillingProfile
        bp.stripe_subscription_id = sub_obj["id"]
        bp.status = sub_obj["status"]
        bp.cancel_at = sub_obj.get("cancel_at")
        bp.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)

        items = sub_obj.get("items", {}).get("data") or []
        bp.stripe_price_id = items[0]["price"]["id"] if items else None

        # Plan depuis price_id
        plan_key = PRICE_TO_PLAN.get(bp.stripe_price_id)

        if bp.status in ("canceled", "incomplete_expired"):
            bp.plan = BillingProfile.PLAN_FREE
            bp.stripe_price_id = None
        else:
            if plan_key == "coach_month":
                bp.plan = BillingProfile.PLAN_COACH
            elif plan_key == "premium_month":
                bp.plan = BillingProfile.PLAN_PREMIUM
            else:
                bp.plan = BillingProfile.PLAN_FREE

        bp.save()

        # --- MAJ du rôle utilisateur (SIMPLE & DIRECT)
        try:
            user = getattr(bp, "user", None) or get_user_model().objects.get(billing=bp)
        except Exception:
            user = None
        if not user:
            return

        # ne jamais écraser un admin
        current = (getattr(user, "role", "") or "").lower()
        if current == "admin":
            return

        new_role = (
            "coach" if bp.plan == BillingProfile.PLAN_COACH
            else "premium" if bp.plan == BillingProfile.PLAN_PREMIUM
            else "user"
        )

        if hasattr(user, "role") and user.role != new_role:
            user.role = new_role
            user.save(update_fields=["role"])
            # print(f"[billing] set user {user.id} role -> {new_role}")  # debug optionnel

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


class QuotasView(APIView):
    """Retourne les quotas normalisés (limits + usage)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
      ser = QuotasSerializer.from_user(request.user)
      resp = Response(ser.data)
      # 👉 force no-cache côté client/proxy
      resp["Cache-Control"] = "no-store"
      return resp