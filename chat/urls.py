from django.urls import path

from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),
    path('api/messages/', views.send_message, name='send_message'),
]
