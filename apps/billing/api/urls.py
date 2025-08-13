from django.urls import path
from .views import CreateCheckoutSessionView, StripeWebhookView, QuotasView

urlpatterns = [
    path('checkout/<str:product_key>/', CreateCheckoutSessionView.as_view(), name='billing_checkout'),
    path('webhook/', StripeWebhookView.as_view(), name='billing_webhook'),
    path('quotas/', QuotasView.as_view(), name='billing_quotas'),
]
