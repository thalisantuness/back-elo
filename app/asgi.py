"""
ASGI config for app project.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

# from business.consumers import ChatConsumer

application = get_asgi_application()

# application = ProtocolTypeRouter({
#     'http': get_asgi_application(),
#     'websocket': AuthMiddlewareStack(
#         URLRouter([
#             path('ws/chat/', ChatConsumer.as_asgi()),
#         ])
#     ),
# })