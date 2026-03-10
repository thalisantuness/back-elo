from .usuario_views import UsuarioViewSet
from .produto_views import ProdutoViewSet
from .campanha_views import CampanhaViewSet
from .recompensa_views import RecompensaViewSet
from .compra_views import CompraViewSet
from .conversa_views import ConversaViewSet
from .solicitacao_views import SolicitacaoViewSet

__all__ = [
    'UsuarioViewSet',
    'ProdutoViewSet',
    'CampanhaViewSet',
    'RecompensaViewSet',
    'CompraViewSet',
    'ConversaViewSet',
    'SolicitacaoViewSet',
]