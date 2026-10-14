from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegistrationConfirmView,
    RegistrationRequestView,
    RefreshView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("register/request/", RegistrationRequestView.as_view(), name="register-request"),
    path("register/confirm/", RegistrationConfirmView.as_view(), name="register-confirm"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]

