from rest_framework.routers import DefaultRouter
from sports.api.views.sport_viewset import SportViewSet

router = DefaultRouter()
router.register(r"", SportViewSet, basename="sport")

urlpatterns = router.urls
