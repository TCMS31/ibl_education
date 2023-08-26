from django.urls import include, path

from . import views

urlpatterns = [
    path("healthz", views.healthz, name="healthz"),
    path("signin", views.signin, name="signin"),
    path("greeting", views.greeting_endpoint, name="greeting"),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
]
