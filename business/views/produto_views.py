from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
import logging

from business.repositories import produto_repo, usuario_repo
from business.serializers import ProdutoSerializer
from business.services.image_upload import image_upload_service
from .base_view import BaseView

logger = logging.getLogger(__name__)


class ProdutoViewSet(ViewSet, BaseView):

    def get_permissions(self):
        """Permissões baseadas na ação"""
        if self.action in ['list', 'retrieve']:
            return []  # Público para leitura
        return [IsAuthenticated()]

    def list(self, request):
        """Listar produtos"""
        try:
            filters = {}

            # Filtrar por query params
            if 'empresa_id' in request.query_params:
                filters['empresa_id'] = request.query_params['empresa_id']

            if 'tipo_produto' in request.query_params:
                filters['tipo_produto'] = request.query_params['tipo_produto']

            # Filtros baseados no usuário autenticado
            if request.user.is_authenticated:
                user = request.user

                if user.role == 'cdl':
                    lojas = usuario_repo.get_lojas_por_cdl(user.usuario_id)
                    ids_lojas = [l.usuario_id for l in lojas]
                    ids_lojas.append(user.usuario_id)
                    filters['empresa_id__in'] = ids_lojas

                elif user.role == 'cliente' and user.cdl:
                    lojas = usuario_repo.get_lojas_por_cdl(user.cdl.usuario_id)
                    ids_lojas = [l.usuario_id for l in lojas]
                    filters['empresa_id__in'] = ids_lojas

            produtos = produto_repo.get_all_with_fotos(filters)
            serializer = ProdutoSerializer(produtos, many=True)

            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao listar produtos: {str(e)}")
            return self.error_response("Erro ao listar produtos")

    def retrieve(self, request, pk=None):
        """Buscar produto por ID"""
        try:
            produto = produto_repo.get_by_id_with_fotos(pk)
            if not produto:
                return self.not_found_response("Produto não encontrado")

            serializer = ProdutoSerializer(produto)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao buscar produto: {str(e)}")
            return self.error_response("Erro ao buscar produto")

    def create(self, request):
        """Criar produto"""
        try:
            # Verificar permissão
            if request.user.role not in ['empresa', 'cdl', 'admin']:
                return self.forbidden_response("Apenas empresas, CDLs e administradores podem criar produtos")

            data = request.data.copy()
            foto_principal = data.pop('foto_principal', None) or data.pop('imagem_base64', None)
            fotos_secundarias = data.pop('fotos_secundarias', [])

            # Validar campos obrigatórios
            required = ['nome', 'valor', 'valor_custo', 'quantidade']
            for field in required:
                if field not in data:
                    return self.error_response(f"Campo {field} é obrigatório")

            # Determinar empresa_id
            if request.user.role == 'empresa':
                data['empresa_id'] = request.user.usuario_id
            elif request.user.role == 'cdl':
                data['empresa_id'] = request.user.usuario_id
            elif request.user.role == 'admin' and not data.get('empresa_id'):
                return self.error_response("Admin deve informar empresa_id")

            # Criar produto com foto principal
            produto = produto_repo.create_with_foto_principal(data, foto_principal)

            # Adicionar fotos secundárias
            for foto_base64 in fotos_secundarias:
                try:
                    produto_repo.add_foto(produto.produto_id, foto_base64)
                except Exception as e:
                    logger.warning(f"Erro ao adicionar foto secundária: {str(e)}")

            # Buscar produto completo
            produto_completo = produto_repo.get_by_id_with_fotos(produto.produto_id)
            serializer = ProdutoSerializer(produto_completo)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao criar produto: {str(e)}")
            return self.error_response("Erro ao criar produto")

    def update(self, request, pk=None):
        """Atualizar produto"""
        try:
            produto = produto_repo.get_by_id(pk)
            if not produto:
                return self.not_found_response()

            # Verificar permissão
            if produto.empresa_id != request.user.usuario_id and request.user.role != 'admin':
                return self.forbidden_response()

            data = request.data.copy()

            # Processar nova foto principal se fornecida
            nova_foto = data.pop('foto_principal', None) or data.pop('imagem_base64', None)
            if nova_foto:
                from business import image_upload_service

                # Deletar foto antiga
                if produto.foto_principal:
                    image_upload_service.delete_from_s3(produto.foto_principal)

                # Upload nova foto
                data['foto_principal'] = image_upload_service.upload_base64_image(
                    nova_foto,
                    'produtos/principal'
                )

            # Atualizar campos
            for key, value in data.items():
                if hasattr(produto, key):
                    setattr(produto, key, value)
            produto.save()

            serializer = ProdutoSerializer(produto)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao atualizar produto: {str(e)}")
            return self.error_response("Erro ao atualizar produto")

    def destroy(self, request, pk=None):
        """Deletar produto"""
        try:
            produto = produto_repo.get_by_id_with_fotos(pk)
            if not produto:
                return self.not_found_response()

            # Verificar permissão
            if produto.empresa_id != request.user.usuario_id and request.user.role != 'admin':
                return self.forbidden_response()

            # Deletar fotos do S3
            from business import image_upload_service

            if produto.foto_principal:
                image_upload_service.delete_from_s3(produto.foto_principal)

            for foto in produto.fotos.all():
                if foto.imageData:
                    image_upload_service.delete_from_s3(foto.imageData)

            produto.delete()

            return self.success_response(message="Produto deletado com sucesso")

        except Exception as e:
            logger.error(f"Erro ao deletar produto: {str(e)}")
            return self.error_response("Erro ao deletar produto")

    @action(detail=True, methods=['post'], url_path='fotos')
    def add_foto(self, request, pk=None):
        """Adicionar foto secundária"""
        try:
            produto = produto_repo.get_by_id(pk)
            if not produto:
                return self.not_found_response()

            if produto.empresa_id != request.user.usuario_id and request.user.role != 'admin':
                return self.forbidden_response()

            foto_base64 = request.data.get('imageBase64')
            if not foto_base64:
                return self.error_response("Imagem é obrigatória")

            foto = produto_repo.add_foto(pk, foto_base64)

            return Response({
                'photo_id': foto.photo_id,
                'imageData': foto.imageData
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao adicionar foto: {str(e)}")
            return self.error_response("Erro ao adicionar foto")

    @action(detail=True, methods=['delete'], url_path='fotos/(?P<foto_id>[^/.]+)')
    def remove_foto(self, request, pk=None, foto_id=None):
        """Remover foto secundária"""
        try:
            produto = produto_repo.get_by_id(pk)
            if not produto:
                return self.not_found_response()

            if produto.empresa_id != request.user.usuario_id and request.user.role != 'admin':
                return self.forbidden_response()

            if produto_repo.remove_foto(foto_id):
                return self.success_response(message="Foto removida com sucesso")
            else:
                return self.not_found_response("Foto não encontrada")

        except Exception as e:
            logger.error(f"Erro ao remover foto: {str(e)}")
            return self.error_response("Erro ao remover foto")