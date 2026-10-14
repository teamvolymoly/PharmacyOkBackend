from django.urls import path

from .views import CurrentTenantView

urlpatterns = [path("current/", CurrentTenantView.as_view(), name="current-tenant")]

