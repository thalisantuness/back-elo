from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.db import transaction
from datetime import datetime
import logging

from business.models import SolicitacaoRecompensa, Recompensa, Usuario
from business.repositories import solicitacao_repo
from business.serializers import SolicitacaoSerializer
from .base_view import BaseView

logger = logging.getLogger(__name__)


class SolicitacaoViewSet(ViewSet, BaseView):

    def list(self, request):
        """Listar solicitações"""
        try:
            user = request.user

            if user.role == 'admin':
                solicitacoes = SolicitacaoRecompensa.objects.all()
            elif user.role in ['empresa', 'cdl']:
                # Empresa vê solicitações de suas recompensas
                solicitacoes = SolicitacaoRecompensa.objects.filter(
                    recompensa__usuario_id=user.usuario_id
                )
            elif user.role == 'empresa-funcionario' and user.cdl:
                solicitacoes = SolicitacaoRecompensa.objects.filter(
                    recompensa__usuario_id=user.cdl.usuario_id
                )
            elif user.role == 'cliente':
                solicitacoes = SolicitacaoRecompensa.objects.filter(usuario=user)
            else:
                return Response([])

            solicitacoes = solicitacoes.select_related(
                'usuario', 'recompensa'
            ).order_by('-data_solicitacao')

            serializer = SolicitacaoSerializer(solicitacoes, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao listar solicitações: {str(e)}")
            return self.error_response("Erro ao listar solicitações")

    def retrieve(self, request, pk=None):
        """Buscar solicitação por ID"""
        try:
            solicitacao = SolicitacaoRecompensa.objects.select_related(
                'usuario', 'recompensa'
            ).filter(pk=pk).first()

            if not solicitacao:
                return self.not_found_response("Solicitação não encontrada")

            # Verificar permissão
            user = request.user
            if user.role == 'cliente' and solicitacao.usuario_id != user.usuario_id:
                return self.forbidden_response()

            if user.role in ['empresa', 'cdl'] and solicitacao.recompensa.usuario_id != user.usuario_id:
                return self.forbidden_response()

            if user.role == 'empresa-funcionario' and (
                    not user.cdl or solicitacao.recompensa.usuario_id != user.cdl.usuario_id):
                return self.forbidden_response()

            serializer = SolicitacaoSerializer(solicitacao)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao buscar solicitação: {str(e)}")
            return self.error_response("Erro ao buscar solicitação")

    def create(self, request):
        """Criar solicitação de recompensa"""
        try:
            if request.user.role != 'cliente':
                return self.forbidden_response("Apenas clientes podem criar solicitações")

            recom_id = request.data.get('recom_id')
            if not recom_id:
                return self.error_response("recom_id é obrigatório")

            # Verificar se recompensa existe
            recompensa = Recompensa.objects.filter(pk=recom_id).first()
            if not recompensa:
                return self.error_response("Recompensa não encontrada")

            # Verificar se já existe solicitação pendente
            existe_pendente = SolicitacaoRecompensa.objects.filter(
                usuario=request.user,
                recompensa=recompensa,
                status='pendente'
            ).exists()

            if existe_pendente:
                return self.error_response("Você já tem uma solicitação pendente para esta recompensa")

            # Criar solicitação
            solicitacao = SolicitacaoRecompensa.objects.create(
                usuario=request.user,
                recompensa=recompensa,
                status='pendente'
            )

            serializer = SolicitacaoSerializer(solicitacao)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Erro ao criar solicitação: {str(e)}")
            return self.error_response("Erro ao criar solicitação")

    @action(detail=True, methods=['post'], url_path='processar')
    def processar(self, request, pk=None):
        """Processar solicitação (aceitar/rejeitar)"""
        try:
            if request.user.role not in ['empresa', 'cdl', 'admin']:
                return self.forbidden_response("Apenas empresas e administradores podem processar solicitações")

            decisao = request.data.get('decisao')
            if decisao not in ['aceita', 'rejeitada']:
                return self.error_response("Decisão deve ser 'aceita' ou 'rejeitada'")

            with transaction.atomic():
                solicitacao = SolicitacaoRecompensa.objects.select_related(
                    'usuario', 'recompensa'
                ).filter(pk=pk).first()

                if not solicitacao:
                    return self.not_found_response("Solicitação não encontrada")

                if solicitacao.status != 'pendente':
                    return self.error_response("Esta solicitação já foi processada")

                # Verificar permissão da empresa
                if request.user.role in ['empresa', 'cdl']:
                    if solicitacao.recompensa.usuario_id != request.user.usuario_id:
                        return self.forbidden_response("Você só pode processar recompensas da sua empresa")

                if request.user.role == 'empresa-funcionario':
                    if not request.user.cdl or solicitacao.recompensa.usuario_id != request.user.cdl.usuario_id:
                        return self.forbidden_response()

                if decisao == 'aceita':
                    # Verificar pontos
                    if solicitacao.usuario.pontos < solicitacao.recompensa.pontos:
                        return self.error_response("Pontos insuficientes")

                    # Verificar estoque
                    if solicitacao.recompensa.estoque <= 0:
                        return self.error_response("Recompensa fora de estoque")

                    # Deduzir pontos
                    solicitacao.usuario.pontos -= solicitacao.recompensa.pontos
                    solicitacao.usuario.save()

                    # Reduzir estoque
                    solicitacao.recompensa.estoque -= 1
                    solicitacao.recompensa.save()

                    solicitacao.status = 'aceita'

                else:  # rejeitada
                    solicitacao.status = 'rejeitada'

                solicitacao.data_resposta = datetime.now()
                solicitacao.save()

                return self.success_response(
                    message=f"Solicitação {decisao} com sucesso"
                )

        except Exception as e:
            logger.error(f"Erro ao processar solicitação: {str(e)}")
            return self.error_response("Erro ao processar solicitação")

    @action(detail=False, methods=['get'], url_path='pendentes')
    def pendentes(self, request):
        """Listar solicitações pendentes"""
        try:
            if request.user.role not in ['empresa', 'cdl', 'admin']:
                return self.forbidden_response()

            filters = {'status': 'pendente'}

            if request.user.role in ['empresa', 'cdl']:
                filters['recompensa__usuario_id'] = request.user.usuario_id

            if request.user.role == 'empresa-funcionario' and request.user.cdl:
                filters['recompensa__usuario_id'] = request.user.cdl.usuario_id

            solicitacoes = SolicitacaoRecompensa.objects.filter(
                **filters
            ).select_related('usuario', 'recompensa').order_by('data_solicitacao')

            serializer = SolicitacaoSerializer(solicitacoes, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao listar solicitações pendentes: {str(e)}")
            return self.error_response("Erro ao listar solicitações")