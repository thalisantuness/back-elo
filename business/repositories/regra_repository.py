from business.models import Regra, Usuario
from django.db import transaction
from .base_repository import BaseRepository


class RegraRepository(BaseRepository):
    def __init__(self):
        super().__init__(Regra)

    def get_by_empresa(self, empresa_id):
        """Busca regra de uma empresa"""
        try:
            return Regra.objects.get(empresa_id=empresa_id, ativa=True)
        except Regra.DoesNotExist:
            return None

    @transaction.atomic
    def set_regra_unica(self, empresa_id, **regra_data):
        """Define regra única para empresa (cria ou atualiza)"""
        regra = self.get_by_empresa(empresa_id)

        if regra:
            # Atualizar existente
            for key, value in regra_data.items():
                setattr(regra, key, value)
            regra.save()
        else:
            # Criar nova
            regra = Regra.objects.create(empresa_id=empresa_id, **regra_data)

            # Vincular à empresa
            Usuario.objects.filter(usuario_id=empresa_id).update(regra=regra)

        return regra

    def create_regra(self, **kwargs):
        """Cria nova regra"""
        return Regra.objects.create(**kwargs)

    def update_regra(self, regra_id, **kwargs):
        """Atualiza regra existente"""
        regra = self.get_by_id(regra_id)
        if not regra:
            raise ValueError("Regra não encontrada")

        for key, value in kwargs.items():
            setattr(regra, key, value)
        regra.save()
        return regra