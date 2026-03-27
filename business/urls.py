from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Importações das views
from business.views.usuario_views import UsuarioViewSet
from business.views.produto_views import ProdutoViewSet
from business.views.campanha_views import CampanhaViewSet
from business.views.recompensa_views import RecompensaViewSet
from business.views.compra_views import CompraViewSet
from business.views.conversa_views import ConversaViewSet
from business.views.solicitacao_views import SolicitacaoViewSet
from business.views.regra_views import RegraViewSet

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'produtos', ProdutoViewSet, basename='produto')
router.register(r'campanhas', CampanhaViewSet, basename='campanha')
router.register(r'recompensas', RecompensaViewSet, basename='recompensa')
router.register(r'compras', CompraViewSet, basename='compra')
router.register(r'conversas', ConversaViewSet, basename='conversa')
router.register(r'solicitacoes', SolicitacaoViewSet, basename='solicitacao')

urlpatterns = [
    # Rotas do router (já inclui list, create, retrieve, update, destroy)
    path('', include(router.urls)),
    
    # ==================== ROTAS PÚBLICAS ====================
    # Autenticação
    path('login/', UsuarioViewSet.as_view({'post': 'login'}), name='login'),
    path('usuarios/', UsuarioViewSet.as_view({'post': 'create'}), name='usuarios-create'),  # POST /usuarios
    path('cdls/', UsuarioViewSet.as_view({'get': 'list_cdls'}), name='cdls-list'),
    path('cdls/<int:cdl_id>/lojas/', UsuarioViewSet.as_view({'get': 'list_lojas_cdl'}), name='cdls-lojas'),
    
    # Produtos públicos (com optional auth)
    path('produtos/', ProdutoViewSet.as_view({'get': 'list'}), name='produtos-list'),
    path('produtos/<int:pk>/', ProdutoViewSet.as_view({'get': 'retrieve'}), name='produtos-detail'),
    
    # ==================== ROTAS DE USUÁRIOS ====================
    path('usuarios/<int:pk>/', UsuarioViewSet.as_view({
        'get': 'retrieve',
        'put': 'update_perfil',
        'delete': 'destroy'
    }), name='usuario-detail'),
    
    path('usuarios/<int:pk>/perfil/', UsuarioViewSet.as_view({'patch': 'update_perfil'}), name='usuario-perfil'),
    path('usuarios/<int:pk>/senha/', UsuarioViewSet.as_view({'patch': 'change_password'}), name='usuario-senha'),
    path('usuarios/<int:pk>/foto/', UsuarioViewSet.as_view({'patch': 'update_foto'}), name='usuario-foto'),
    
    # Cliente trocar CDL
    path('cliente/<int:pk>/trocar-cdl/', UsuarioViewSet.as_view({'put': 'trocar_cdl'}), name='cliente-trocar-cdl'),
    
    # Dashboard CDL
    path('minha-cdl/dashboard/', UsuarioViewSet.as_view({'get': 'dashboard_cdl'}), name='cdl-dashboard'),
    path('minha-cdl/graficos/', CompraViewSet.as_view({'get': 'graficos_cdl'}), name='cdl-graficos'),
    
    # ==================== ROTAS ADMINISTRATIVAS ====================
    path('admin/usuarios/', UsuarioViewSet.as_view({'get': 'visualizar_usuario'}), name='admin-usuarios'),
    path('admin/tornar-admin/', UsuarioViewSet.as_view({'put': 'tornar_admin'}), name='admin-tornar-admin'),
    path('admin/tornar-cdl/', UsuarioViewSet.as_view({'put': 'tornar_cdl'}), name='admin-tornar-cdl'),
    path('admin/aprovar-cdl/<int:pk>/', UsuarioViewSet.as_view({'put': 'aprovar_cdl'}), name='admin-aprovar-cdl'),
    path('admin/usuarios/pontos/<int:pk>/', UsuarioViewSet.as_view({'put': 'give_points'}), name='admin-pontos'),
    
    # ==================== ROTAS DE EMPRESAS ====================
    path('minha-empresa/', UsuarioViewSet.as_view({'put': 'atualizar_dados_empresa'}), name='minha-empresa'),
    path('empresas/', UsuarioViewSet.as_view({'get': 'list_empresas'}), name='empresas-list'),
    
    # ==================== ROTAS DE PRODUTOS ====================
    path('produtos/', ProdutoViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='produtos'),
    
    path('produtos/<int:pk>/', ProdutoViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='produto-detail'),
    
    path('produtos/<int:pk>/fotos/', ProdutoViewSet.as_view({'post': 'add_foto'}), name='produto-fotos'),
    path('produtos/<int:pk>/fotos/<int:foto_id>/', ProdutoViewSet.as_view({'delete': 'remove_foto'}), name='produto-foto-delete'),
    
    # ==================== ROTAS DE RECOMPENSAS ====================
    path('recompensas/', RecompensaViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='recompensas'),
    
    path('recompensas/<int:pk>/', RecompensaViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='recompensa-detail'),
    
    path('editar-recompensa/<int:pk>/', RecompensaViewSet.as_view({
        'get': 'retrieve',
        'put': 'update'
    }), name='editar-recompensa'),
    
    # ==================== ROTAS DE SOLICITAÇÕES ====================
    path('solicitacoes/', SolicitacaoViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='solicitacoes'),
    
    path('solicitacoes/processar/<int:pk>/', SolicitacaoViewSet.as_view({'put': 'processar'}), name='solicitacoes-processar'),
    
    # ==================== ROTAS DE REGRAS ====================
    path('regras/', RegraViewSet.as_view({'post': 'create'}), name='regras-create'),
    path('minhas-regras/', RegraViewSet.as_view({'get': 'list_minhas'}), name='minhas-regras'),
    path('empresas/<int:empresa_id>/regras/', RegraViewSet.as_view({'get': 'list_por_empresa'}), name='empresa-regras'),
    path('regras-padrao/', RegraViewSet.as_view({'post': 'criar_padrao'}), name='regras-padrao'),
    
    # ==================== ROTAS DE CAMPANHAS ====================
    path('campanhas/', CampanhaViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='campanhas'),
    
    path('campanhas/<int:pk>/', CampanhaViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='campanha-detail'),
    
    path('editar-campanha/<int:pk>/', CampanhaViewSet.as_view({
        'get': 'retrieve',
        'put': 'update'
    }), name='editar-campanha'),
    
    # ==================== ROTAS DE COMPRAS ====================
    path('compras/', CompraViewSet.as_view({'get': 'list'}), name='compras'),
    path('compras/<int:pk>/', CompraViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='compra-detail'),
    
    path('qr-code/', CompraViewSet.as_view({'post': 'gerar_qrcode'}), name='gerar-qrcode'),
    path('compra/', CompraViewSet.as_view({'post': 'claim_compra'}), name='claim-compra'),
    # Accept POST without trailing slash (needed for clients that omit the slash)
    path('compra', CompraViewSet.as_view({'post': 'claim_compra'}), name='claim-compra-no-slash'),
    path('minhas-estatisticas/', CompraViewSet.as_view({'get': 'estatisticas'}), name='estatisticas'),
    path('big-numbers/', CompraViewSet.as_view({'get': 'big_numbers'}), name='big-numbers'),
    
    # ==================== ROTAS DE CHAT ====================
    path('conversas/', ConversaViewSet.as_view({'get': 'list'}), name='conversas'),
    path('conversas/<int:pk>/mensagens/', ConversaViewSet.as_view({'get': 'mensagens'}), name='conversa-mensagens'),
    path('mensagens/<int:pk>/lida/', ConversaViewSet.as_view({'put': 'marcar_lida'}), name='mensagem-lida'),
    
    # Refresh token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]