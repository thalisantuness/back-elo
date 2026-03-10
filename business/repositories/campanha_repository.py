from django.db import transaction
from django.db.models import Q
from datetime import datetime
from business.models import Campanha, Usuario
from business.services.image_upload import image_upload_service
from .base_repository import BaseRepository


class CampanhaRepository(BaseRepository):
    def __init__(self):
        super().__init__(Campanha)

    def get_by_empresa(self, empresa_id):
        """Lista campanhas de uma empresa"""
        return Campanha.objects.filter(empresa_id=empresa_id).select_related('empresa').order_by('-data_cadastro')

    def get_all_with_empresa(self):
        """Lista todas com dados da empresa"""
        return Campanha.objects.select_related('empresa').order_by('-data_cadastro')

    def get_by_cdl(self, cdl_id):
        """Lista campanhas de uma CDL e suas lojas"""
        lojas = Usuario.objects.filter(
            role='empresa',
            cdl_id=cdl_id
        ).values_list('usuario_id', flat=True)

        return Campanha.objects.filter(
            Q(empresa_id=cdl_id) | Q(empresa_id__in=list(lojas))
        ).select_related('empresa').order_by('-data_cadastro')

    def get_ativas_para_cliente(self, cdl_id):
        """Lista campanhas ativas para clientes de uma CDL"""
        lojas = Usuario.objects.filter(
            role='empresa',
            cdl_id=cdl_id,
            status='ativo'
        ).values_list('usuario_id', flat=True)

        agora = datetime.now()

        return Campanha.objects.filter(
            Q(empresa_id=cdl_id) | Q(empresa_id__in=list(lojas)),
            ativa=True,
            data_inicio__lte=agora,
            data_fim__gte=agora
        ).select_related('empresa').order_by('-data_cadastro')

    @transaction.atomic
    def create_with_image(self, empresa_id, titulo, data_inicio, data_fim, **kwargs):
        """Cria campanha com opção de imagem"""
        imagem_base64 = kwargs.pop('imagem_base64', None)
        imagem_url = None

        if imagem_base64:
            imagem_url = image_upload_service.upload_base64_image(
                imagem_base64,
                'campanhas',
                {'max_width': 1200, 'max_height': 630, 'quality': 85}
            )

        return Campanha.objects.create(
            empresa_id=empresa_id,
            titulo=titulo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            imagem_url=imagem_url,
            **kwargs
        )

    @transaction.atomic
    def update_with_image(self, campanha_id, **kwargs):
        """Atualiza campanha com opção de imagem"""
        campanha = self.get_by_id(campanha_id)
        if not campanha:
            raise ValueError(f"Campanha {campanha_id} não encontrada")

        imagem_base64 = kwargs.pop('imagem_base64', None)

        if imagem_base64:
            # Deletar imagem antiga
            if campanha.imagem_url:
                image_upload_service.delete_from_s3(campanha.imagem_url)

            # Upload nova imagem
            kwargs['imagem_url'] = image_upload_service.upload_base64_image(
                imagem_base64,
                'campanhas',
                {'max_width': 1200, 'max_height': 630, 'quality': 85}
            )
        elif imagem_base64 is None and 'imagem_base64' in kwargs:
            # Remover imagem
            if campanha.imagem_url:
                image_upload_service.delete_from_s3(campanha.imagem_url)
            kwargs['imagem_url'] = None

        for key, value in kwargs.items():
            setattr(campanha, key, value)
        campanha.save()

        return campanha