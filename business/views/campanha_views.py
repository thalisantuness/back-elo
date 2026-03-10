from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from datetime import datetime
import logging

from business.models import Campanha
from business.repositories import campanha_repo, usuario_repo
from business.serializers import CampanhaSerializer
from business.services.image_upload import image_upload_service
from .base_view import BaseView

logger = logging.getLogger(__name__)


class CampanhaViewSet(ViewSet, BaseView):

    def get_permissions(self):
        """Permissões baseadas na ação"""
        if self.action in ['list', 'retrieve']:
            return []  # Público para leitura
        return [IsAuthenticated()]

    def list(self, request):
        """Listar campanhas baseado na role do usuário"""
        try:
            campanhas = []

            if not request.user.is_authenticated:
                # Usuário não autenticado vê apenas campanhas ativas
                agora = datetime.now()
                campanhas = Campanha.objects.filter(
                    ativa=True,
                    data_inicio__lte=agora,
                    data_fim__gte=agora
                ).select_related('empresa').order_by('-data_cadastro')
            else:
                user = request.user

                if user.role == 'admin':
                    campanhas = campanha_repo.get_all_with_empresa()

                elif user.role == 'cdl':
                    campanhas = campanha_repo.get_by_cdl(user.usuario_id)

                elif user.role == 'empresa':
                    campanhas = campanha_repo.get_by_empresa(user.usuario_id)

                elif user.role == 'cliente' and user.cdl:
                    campanhas = campanha_repo.get_ativas_para_cliente(user.cdl.usuario_id)

            serializer = CampanhaSerializer(campanhas, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao listar campanhas: {str(e)}")
            return self.error_response("Erro ao listar campanhas")

    def retrieve(self, request, pk=None):
        """Buscar campanha por ID"""
        try:
            campanha = campanha_repo.get_by_id(pk)
            if not campanha:
                return self.not_found_response("Campanha não encontrada")

            # Verificar acesso
            if request.user.is_authenticated:
                user = request.user
                if user.role == 'cliente' and user.cdl:
                    # Cliente só vê campanhas ativas da sua CDL
                    lojas = usuario_repo.get_lojas_por_cdl(user.cdl.usuario_id)
                    ids_lojas = [l.usuario_id for l in lojas]
                    ids_lojas.append(user.cdl.usuario_id)

                    if campanha.empresa_id not in ids_lojas:
                        return self.forbidden_response()

                    agora = datetime.now()
                    if not (campanha.ativa and
                            campanha.data_inicio <= agora <= campanha.data_fim):
                        return self.forbidden_response("Campanha não está ativa")

            serializer = CampanhaSerializer(campanha)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao buscar campanha: {str(e)}")
            return self.error_response("Erro ao buscar campanha")

    def create(self, request):
        """Criar campanha"""
        try:
            # Verificar permissão
            if request.user.role not in ['empresa', 'cdl', 'admin']:
                return self.forbidden_response("Apenas empresas, CDLs e administradores podem criar campanhas")

            data = request.data

            # Validar campos obrigatórios
            required = ['titulo', 'data_inicio', 'data_fim']
            for field in required:
                if field not in data:
                    return self.error_response(f"Campo {field} é obrigatório")

            # Determinar empresa_id
            if request.user.role == 'admin':
                empresa_id = data.get('empresa_id')
                if not empresa_id:
                    return self.error_response("Admin deve informar empresa_id")
            else:
                empresa_id = request.user.usuario_id

            # Criar campanha
            campanha = campanha_repo.create_with_image(
                empresa_id=empresa_id,
                titulo=data['titulo'],
                data_inicio=data['data_inicio'],
                data_fim=data['data_fim'],
                descricao=data.get('descricao'),
                imagem_base64=data.get('imagem_base64'),
                produtos=data.get('produtos', []),
                recompensas=data.get('recompensas', []),
                ativa=data.get('ativa', True)
            )

            serializer = CampanhaSerializer(campanha)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao criar campanha: {str(e)}")
            return self.error_response("Erro ao criar campanha")

    def update(self, request, pk=None):
        """Atualizar campanha"""
        try:
            campanha = campanha_repo.get_by_id(pk)
            if not campanha:
                return self.not_found_response()

            # Verificar permissão
            user = request.user
            if user.role == 'empresa' and campanha.empresa_id != user.usuario_id:
                return self.forbidden_response("Você só pode atualizar suas próprias campanhas")

            if user.role == 'cdl':
                # Verificar se a campanha é da CDL ou de uma loja dela
                if campanha.empresa_id != user.usuario_id:
                    empresa = usuario_repo.get_by_id(campanha.empresa_id)
                    if not empresa or empresa.cdl_id != user.usuario_id:
                        return self.forbidden_response()

            data = request.data

            # Atualizar campanha
            update_kwargs = {}
            fields = ['titulo', 'descricao', 'produtos', 'recompensas',
                      'data_inicio', 'data_fim', 'ativa']

            for field in fields:
                if field in data:
                    update_kwargs[field] = data[field]

            if 'imagem_base64' in data:
                update_kwargs['imagem_base64'] = data['imagem_base64']

            campanha_atualizada = campanha_repo.update_with_image(pk, **update_kwargs)

            serializer = CampanhaSerializer(campanha_atualizada)
            return Response(serializer.data)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao atualizar campanha: {str(e)}")
            return self.error_response("Erro ao atualizar campanha")

    def destroy(self, request, pk=None):
        """Excluir campanha"""
        try:
            campanha = campanha_repo.get_by_id(pk)
            if not campanha:
                return self.not_found_response()

            # Verificar permissão
            user = request.user
            if user.role == 'empresa' and campanha.empresa_id != user.usuario_id:
                return self.forbidden_response("Você só pode excluir suas próprias campanhas")

            if user.role == 'cdl':
                if campanha.empresa_id != user.usuario_id:
                    empresa = usuario_repo.get_by_id(campanha.empresa_id)
                    if not empresa or empresa.cdl_id != user.usuario_id:
                        return self.forbidden_response()

            # Deletar imagem do S3
            if campanha.imagem_url:
                from business import image_upload_service
                image_upload_service.delete_from_s3(campanha.imagem_url)

            campanha.delete()

            return self.success_response(message="Campanha excluída com sucesso")

        except Exception as e:
            logger.error(f"Erro ao excluir campanha: {str(e)}")
            return self.error_response("Erro ao excluir campanha")