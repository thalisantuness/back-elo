from business.models import Recompensa
from business.services.image_upload import image_upload_service
from django.db import transaction
from .base_repository import BaseRepository


class RecompensaRepository(BaseRepository):
    def __init__(self):
        super().__init__(Recompensa)

    def get_by_usuario(self, usuario_id):
        """Lista recompensas de um usuário"""
        return Recompensa.objects.filter(usuario_id=usuario_id).order_by('-data_cadastro')

    def get_available_for_cliente(self, cdl_id):
        """Lista recompensas disponíveis para clientes de uma CDL"""
        from business.models import Usuario
        lojas = Usuario.objects.filter(
            role='empresa',
            cdl_id=cdl_id,
            status='ativo'
        ).values_list('usuario_id', flat=True)

        return Recompensa.objects.filter(
            usuario_id__in=list(lojas) if lojas else [-1],
            estoque__gt=0
        ).order_by('-data_cadastro')

    @transaction.atomic
    def create_with_image(self, usuario_id, nome, **kwargs):
        """Cria recompensa com opção de imagem"""
        imagem_base64 = kwargs.pop('imagem_base64', None)
        imagem_url = None

        if imagem_base64:
            imagem_url = image_upload_service.upload_base64_image(
                imagem_base64,
                'recompensas',
                {'max_width': 500, 'max_height': 500, 'quality': 85}
            )

        return Recompensa.objects.create(
            usuario_id=usuario_id,
            nome=nome,
            imagem_url=imagem_url,
            **kwargs
        )

    @transaction.atomic
    def update_with_image(self, recompensa_id, **kwargs):
        """Atualiza recompensa com opção de imagem"""
        recompensa = self.get_by_id(recompensa_id)
        if not recompensa:
            raise ValueError(f"Recompensa {recompensa_id} não encontrada")

        imagem_base64 = kwargs.pop('imagem_base64', None)

        if imagem_base64:
            # Deletar imagem antiga
            if recompensa.imagem_url:
                image_upload_service.delete_from_s3(recompensa.imagem_url)

            # Upload nova imagem
            kwargs['imagem_url'] = image_upload_service.upload_base64_image(
                imagem_base64,
                'recompensas',
                {'max_width': 500, 'max_height': 500, 'quality': 85}
            )
        elif imagem_base64 is None and 'imagem_base64' in kwargs:
            # Remover imagem
            if recompensa.imagem_url:
                image_upload_service.delete_from_s3(recompensa.imagem_url)
            kwargs['imagem_url'] = None

        for key, value in kwargs.items():
            setattr(recompensa, key, value)
        recompensa.save()

        return recompensa

    def check_estoque(self, recompensa_id):
        """Verifica se há estoque disponível"""
        recompensa = self.get_by_id(recompensa_id)
        if not recompensa:
            return False
        return recompensa.estoque > 0

    def reduzir_estoque(self, recompensa_id, quantidade=1):
        """Reduz o estoque de uma recompensa"""
        recompensa = self.get_by_id(recompensa_id)
        if not recompensa:
            raise ValueError("Recompensa não encontrada")

        if recompensa.estoque < quantidade:
            raise ValueError("Estoque insuficiente")

        recompensa.estoque -= quantidade
        recompensa.save()
        return recompensa