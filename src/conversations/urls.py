from django.urls import path

from conversations import views

urlpatterns = [
    path("webhook/message", views.message_webhook, name="message-webhook"),
    path("api/conversations/<str:user_phone>/messages", views.conversation_messages, name="conversation-messages"),
]
