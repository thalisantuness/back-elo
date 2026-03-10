from business.models import Produto, Foto
from business.services.image_upload import image_upload_service
from django.db import transaction
from .base_repository import BaseRepository


class ProdutoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Produto)

    def get_all_with_fotos(self, filters=None):
        """Lista produtos com fotos"""
        queryset = Produto.objects.prefetch_related('fotos').select_related('empresa')
        if filters:
            queryset = queryset.filter(**filters)
        return queryset.order_by('-data_cadastro')

    def get_by_id_with_fotos(self, id):
        """Busca produto com fotos"""
        try:
            return Produto.objects.prefetch_related('fotos').select_related('empresa').get(pk=id)
        except Produto.DoesNotExist:
            return None

    @transaction.atomic
    def create_with_foto_principal(self, produto_data, foto_principal_base64=None):
        """Cria produto com foto principal"""
        if foto_principal_base64:
            url = image_upload_service.upload_base64_image(
                foto_principal_base64,
                'produtos/principal'
            )
            produto_data['foto_principal'] = url

        return Produto.objects.create(**produto_data)

    @transaction.atomic
    def add_foto(self, produto_id, foto_base64):
        """Adiciona foto secundária"""
        url = image_upload_service.upload_base64_image(
            foto_base64,
            'produtos/secundarias'
        )

        return Foto.objects.create(
            produto_id=produto_id,
            imageData=url
        )

    @transaction.atomic
    def remove_foto(self, foto_id):
        """Remove foto secundária"""
        try:
            foto = Foto.objects.get(photo_id=foto_id)
            image_upload_service.delete_from_s3(foto.imageData)
            foto.delete()
            return True
        except Foto.DoesNotExist:
            return False