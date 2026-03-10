from django.db import transaction
from django.db.models import Q, Sum
from datetime import datetime
from business.models import SolicitacaoRecompensa, Usuario, Recompensa
from .base_repository import BaseRepository


class SolicitacaoRepository(BaseRepository):
    def __init__(self):
        super().__init__(SolicitacaoRecompensa)

    def get_by_usuario(self, usuario_id):
        """Lista solicitações de um usuário"""
        return SolicitacaoRecompensa.objects.filter(
            usuario_id=usuario_id
        ).select_related('recompensa').order_by('-data_solicitacao')

    def get_by_recompensa(self, recompensa_id):
        """Lista solicitações de uma recompensa"""
        return SolicitacaoRecompensa.objects.filter(
            recompensa_id=recompensa_id
        ).select_related('usuario').order_by('-data_solicitacao')

    def get_pendentes(self, usuario_id=None):
        """Lista solicitações pendentes"""
        filters = {'status': 'pendente'}
        if usuario_id:
            filters['recompensa__usuario_id'] = usuario_id
        return SolicitacaoRecompensa.objects.filter(
            **filters
        ).select_related('usuario', 'recompensa').order_by('data_solicitacao')

    @transaction.atomic
    def processar_solicitacao(self, solicitacao_id, decisao):
        """Processa uma solicitação (aceitar/rejeitar)"""
        solicitacao = self.get_by_id(solicitacao_id)
        if not solicitacao:
            raise ValueError("Solicitação não encontrada")

        if solicitacao.status != 'pendente':
            raise ValueError("Solicitação já foi processada")

        if decisao == 'aceita':
            # Verificar pontos do usuário
            if solicitacao.usuario.pontos < solicitacao.recompensa.pontos:
                raise ValueError("Pontos insuficientes")

            # Verificar estoque
            if solicitacao.recompensa.estoque <= 0:
                raise ValueError("Recompensa fora de estoque")

            # Deduzir pontos
            solicitacao.usuario.pontos -= solicitacao.recompensa.pontos
            solicitacao.usuario.save()

            # Reduzir estoque
            solicitacao.recompensa.estoque -= 1
            solicitacao.recompensa.save()

            solicitacao.status = 'aceita'

        elif decisao == 'rejeitada':
            solicitacao.status = 'rejeitada'
        else:
            raise ValueError("Decisão deve ser 'aceita' ou 'rejeitada'")

        solicitacao.data_resposta = datetime.now()
        solicitacao.save()

        return solicitacao

    def pontos_usados_periodo(self, usuario_id, data_inicio, data_fim):
        """Calcula pontos usados em um período"""
        return SolicitacaoRecompensa.objects.filter(
            usuario_id=usuario_id,
            status='aceita',
            data_resposta__gte=data_inicio,
            data_resposta__lte=data_fim
        ).aggregate(
            total=Sum('recompensa__pontos')
        )['total'] or 0

    def verificar_solicitacao_pendente(self, usuario_id, recompensa_id):
        """Verifica se já existe solicitação pendente"""
        return SolicitacaoRecompensa.objects.filter(
            usuario_id=usuario_id,
            recompensa_id=recompensa_id,
            status='pendente'
        ).exists()