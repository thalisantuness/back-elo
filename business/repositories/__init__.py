from .usuario_repository import UsuarioRepository
from .regra_repository import RegraRepository
from .produto_repository import ProdutoRepository
from .campanha_repository import CampanhaRepository
from .recompensa_repository import RecompensaRepository
from .compra_repository import CompraRepository
from .conversa_repository import ConversaRepository
from .solicitacao_repository import SolicitacaoRepository

usuario_repo = UsuarioRepository()
regra_repo = RegraRepository()
produto_repo = ProdutoRepository()
campanha_repo = CampanhaRepository()
recompensa_repo = RecompensaRepository()
compra_repo = CompraRepository()
conversa_repo = ConversaRepository()
solicitacao_repo = SolicitacaoRepository()

__all__ = [
    'usuario_repo',
    'regra_repo',
    'produto_repo',
    'campanha_repo',
    'recompensa_repo',
    'compra_repo',
    'conversa_repo',
    'solicitacao_repo',
]