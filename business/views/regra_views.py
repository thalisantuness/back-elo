from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
import logging

from business.repositories import regra_repo
from business.serializers import RegraSerializer
from .base_view import BaseView

logger = logging.getLogger(__name__)


class RegraViewSet(ViewSet, BaseView):

    def get_permissions(self):
        """Permissões baseadas na ação"""
        if self.action in ['list_por_empresa']:
            return []  # Público para visualizar regras de empresas
        return [IsAuthenticated()]

    # POST /regras
    def create(self, request):
        """Criar regra para empresa logada"""
        try:
            if request.user.role not in ['empresa', 'admin']:
                return self.forbidden_response("Apenas empresas podem criar regras")

            data = request.data
            data['empresa_id'] = request.user.usuario_id

            regra = regra_repo.set_regra_unica(**data)

            serializer = RegraSerializer(regra)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao criar regra: {str(e)}")
            return self.error_response("Erro ao criar regra")

    # GET /minhas-regras
    @action(detail=False, methods=['get'], url_path='minhas-regras')
    def list_minhas(self, request):
        """Listar regras da empresa logada"""
        try:
            if request.user.role not in ['empresa', 'admin']:
                return self.forbidden_response()

            regra = regra_repo.get_by_empresa(request.user.usuario_id)
            
            if regra:
                serializer = RegraSerializer(regra)
                return Response([serializer.data])
            return Response([])

        except Exception as e:
            logger.error(f"Erro ao listar regras: {str(e)}")
            return self.error_response("Erro ao listar regras")

    # GET /empresas/:empresa_id/regras
    @action(detail=False, methods=['get'], url_path='empresas/(?P<empresa_id>[^/.]+)/regras', permission_classes=[])
    def list_por_empresa(self, request, empresa_id=None):
        """Listar regras de uma empresa específica (público)"""
        try:
            regra = regra_repo.get_by_empresa(empresa_id)
            
            if regra:
                serializer = RegraSerializer(regra)
                return Response([serializer.data])
            return Response([])

        except Exception as e:
            logger.error(f"Erro ao listar regras da empresa: {str(e)}")
            return self.error_response("Erro ao listar regras")

    # POST /regras-padrao
    @action(detail=False, methods=['post'], url_path='regras-padrao')
    def criar_padrao(self, request):
        """Criar regra padrão para empresa"""
        try:
            if request.user.role not in ['empresa', 'admin']:
                return self.forbidden_response("Apenas empresas podem criar regras")

            regra_data = {
                'empresa_id': request.user.usuario_id,
                'nome': 'Regra Padrão por Compra',
                'tipo': 'por_compra',
                'pontos': 1,
                'ativa': True
            }

            regra = regra_repo.set_regra_unica(**regra_data)

            serializer = RegraSerializer(regra)
            return Response({
                'message': 'Regra padrão criada com sucesso',
                'regra': serializer.data
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao criar regra padrão: {str(e)}")
            return self.error_response("Erro ao criar regra padrão")