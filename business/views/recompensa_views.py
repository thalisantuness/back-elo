from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
import logging

from business.repositories import recompensa_repo, usuario_repo
from business.serializers import RecompensaSerializer
from business.services.image_upload import image_upload_service
from .base_view import BaseView

logger = logging.getLogger(__name__)


class RecompensaViewSet(ViewSet, BaseView):

    def list(self, request):
        """Listar recompensas baseado na role do usuário"""
        try:
            user = request.user
            filters = {}

            if user.role == 'admin':
                # Admin vê todas
                pass

            elif user.role in ['empresa', 'cdl']:
                filters['usuario_id'] = user.usuario_id

            elif user.role == 'empresa-funcionario':
                if user.cdl:
                    filters['usuario_id'] = user.cdl.usuario_id
                else:
                    return Response([])

            elif user.role == 'cliente':
                if user.cdl:
                    # Cliente vê recompensas das empresas da sua CDL
                    lojas = usuario_repo.get_lojas_por_cdl(user.cdl.usuario_id)
                    ids_lojas = [l.usuario_id for l in lojas]
                    filters['usuario_id__in'] = ids_lojas if ids_lojas else [-1]
                else:
                    return Response([])

            else:
                return Response([])

            recompensas = recompensa_repo.get_all(filters)
            serializer = RecompensaSerializer(recompensas, many=True)

            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao listar recompensas: {str(e)}")
            return self.error_response("Erro ao listar recompensas")

    def retrieve(self, request, pk=None):
        """Buscar recompensa por ID"""
        try:
            recompensa = recompensa_repo.get_by_id(pk)
            if not recompensa:
                return self.not_found_response("Recompensa não encontrada")

            # Verificar permissão
            user = request.user
            if user.role not in ['admin']:
                if user.role in ['empresa', 'cdl'] and recompensa.usuario_id != user.usuario_id:
                    return self.forbidden_response()

                if user.role == 'empresa-funcionario':
                    if not user.cdl or recompensa.usuario_id != user.cdl.usuario_id:
                        return self.forbidden_response()

                if user.role == 'cliente':
                    if not user.cdl:
                        return self.forbidden_response()

                    lojas = usuario_repo.get_lojas_por_cdl(user.cdl.usuario_id)
                    ids_lojas = [l.usuario_id for l in lojas]
                    if recompensa.usuario_id not in ids_lojas:
                        return self.forbidden_response()

            serializer = RecompensaSerializer(recompensa)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao buscar recompensa: {str(e)}")
            return self.error_response("Erro ao buscar recompensa")

    def create(self, request):
        """Criar recompensa"""
        try:
            # Verificar permissão
            if request.user.role not in ['empresa', 'cdl', 'admin']:
                return self.forbidden_response("Apenas empresas, CDLs e administradores podem criar recompensas")

            data = request.data

            # Validar campos obrigatórios
            if 'nome' not in data:
                return self.error_response("Nome da recompensa é obrigatório")

            # Determinar usuario_id
            usuario_id = data.get('usuario_id', request.user.usuario_id)

            # Processar imagem
            imagem_base64 = data.get('imagem_base64')
            imagem_url = None

            if imagem_base64:
                imagem_url = image_upload_service.upload_base64_image(
                    imagem_base64,
                    'recompensas',
                    {'max_width': 500, 'max_height': 500, 'quality': 85}
                )

            # Criar recompensa
            recompensa = recompensa_repo.create(
                usuario_id=usuario_id,
                nome=data['nome'],
                descricao=data.get('descricao'),
                imagem_url=imagem_url,
                pontos=data.get('pontos', 0),
                estoque=data.get('estoque', 0)
            )

            serializer = RecompensaSerializer(recompensa)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao criar recompensa: {str(e)}")
            return self.error_response("Erro ao criar recompensa")

    def update(self, request, pk=None):
        """Atualizar recompensa"""
        try:
            recompensa = recompensa_repo.get_by_id(pk)
            if not recompensa:
                return self.not_found_response()

            # Verificar permissão
            user = request.user
            if user.role not in ['admin']:
                if user.role in ['empresa', 'cdl'] and recompensa.usuario_id != user.usuario_id:
                    return self.forbidden_response("Você só pode atualizar suas próprias recompensas")

                if user.role == 'empresa-funcionario':
                    if not user.cdl or recompensa.usuario_id != user.cdl.usuario_id:
                        return self.forbidden_response()

            data = request.data

            # Processar nova imagem se fornecida
            imagem_base64 = data.get('imagem_base64')
            if imagem_base64:
                # Deletar imagem antiga
                if recompensa.imagem_url:
                    image_upload_service.delete_from_s3(recompensa.imagem_url)

                # Upload nova imagem
                data['imagem_url'] = image_upload_service.upload_base64_image(
                    imagem_base64,
                    'recompensas',
                    {'max_width': 500, 'max_height': 500, 'quality': 85}
                )
            elif imagem_base64 is None and 'imagem_base64' in data:
                # Remover imagem
                if recompensa.imagem_url:
                    image_upload_service.delete_from_s3(recompensa.imagem_url)
                data['imagem_url'] = None

            # Atualizar campos
            for field in ['nome', 'descricao', 'pontos', 'estoque', 'imagem_url']:
                if field in data:
                    setattr(recompensa, field, data[field])

            recompensa.save()

            serializer = RecompensaSerializer(recompensa)
            return Response(serializer.data)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao atualizar recompensa: {str(e)}")
            return self.error_response("Erro ao atualizar recompensa")

    def destroy(self, request, pk=None):
        """Excluir recompensa"""
        try:
            recompensa = recompensa_repo.get_by_id(pk)
            if not recompensa:
                return self.not_found_response()

            # Verificar permissão
            user = request.user
            if user.role not in ['admin']:
                if user.role in ['empresa', 'cdl'] and recompensa.usuario_id != user.usuario_id:
                    return self.forbidden_response("Você só pode excluir suas próprias recompensas")

                if user.role == 'empresa-funcionario':
                    if not user.cdl or recompensa.usuario_id != user.cdl.usuario_id:
                        return self.forbidden_response()

            # Deletar imagem do S3
            if recompensa.imagem_url:
                image_upload_service.delete_from_s3(recompensa.imagem_url)

            recompensa.delete()

            return self.success_response(message="Recompensa excluída com sucesso")

        except Exception as e:
            logger.error(f"Erro ao excluir recompensa: {str(e)}")
            return self.error_response("Erro ao excluir recompensa")