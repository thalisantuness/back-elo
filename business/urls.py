from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Importações corretas das views
from business.views.usuario_views import UsuarioViewSet
from business.views.produto_views import ProdutoViewSet
from business.views.campanha_views import CampanhaViewSet
from business.views.recompensa_views import RecompensaViewSet
from business.views.compra_views import CompraViewSet
from business.views.conversa_views import ConversaViewSet
from business.views.solicitacao_views import SolicitacaoViewSet

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'produtos', ProdutoViewSet, basename='produto')
router.register(r'campanhas', CampanhaViewSet, basename='campanha')
router.register(r'recompensas', RecompensaViewSet, basename='recompensa')
router.register(r'compras', CompraViewSet, basename='compra')
router.register(r'conversas', ConversaViewSet, basename='conversa')
router.register(r'solicitacoes', SolicitacaoViewSet, basename='solicitacao')

urlpatterns = [
    # Rotas do router
    path('', include(router.urls)),

    # Refresh token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # URLs específicas
    path('login/', UsuarioViewSet.as_view({'post': 'login'}), name='login'),
    path('register/', UsuarioViewSet.as_view({'post': 'register'}), name='register'),

    # CDLs públicas
    path('cdls/', UsuarioViewSet.as_view({'get': 'list_cdls'}), name='cdls-list'),
    path('cdls/<int:cdl_id>/lojas/', UsuarioViewSet.as_view({'get': 'list_lojas_cdl'}), name='cdls-lojas'),

    # Dashboard
    path('minha-cdl/dashboard/', UsuarioViewSet.as_view({'get': 'dashboard_cdl'}), name='cdl-dashboard'),
    path('minhas-estatisticas/', CompraViewSet.as_view({'get': 'estatisticas'}), name='estatisticas'),
    path('big-numbers/', CompraViewSet.as_view({'get': 'big_numbers'}), name='big-numbers'),

    # QR Code
    path('qr-code/gerar/', CompraViewSet.as_view({'post': 'gerar_qrcode'}), name='gerar-qrcode'),
    path('compra/claim/', CompraViewSet.as_view({'post': 'claim_compra'}), name='claim-compra'),

    # Chat
    path('conversas/enviar/', ConversaViewSet.as_view({'post': 'enviar_mensagem'}), name='enviar-mensagem'),
    path('conversas/<int:pk>/mensagens/', ConversaViewSet.as_view({'get': 'mensagens'}), name='conversa-mensagens'),
    path('conversas/<int:pk>/mensagens/<int:mensagem_id>/ler/', ConversaViewSet.as_view({'patch': 'marcar_lida'}),
         name='marcar-lida'),
]