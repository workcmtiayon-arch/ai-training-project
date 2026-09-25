from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import AccountLoginView, SignUpView

app_name = 'accounts'

urlpatterns = [
    path('inscription/', SignUpView.as_view(), name='signup'),
    path('connexion/', AccountLoginView.as_view(), name='login'),
    path('deconnexion/', LogoutView.as_view(), name='logout'),
]
