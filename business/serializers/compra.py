from rest_framework import serializers
from business.models import Compra
from .usuario import UsuarioSerializer
from .campanha import CampanhaSerializer


class CompraSerializer(serializers.ModelSerializer):
    cliente_info = UsuarioSerializer(source='cliente', read_only=True)
    empresa_info = UsuarioSerializer(source='empresa', read_only=True)
    campanha_info = CampanhaSerializer(source='campanha', read_only=True)

    class Meta:
        model = Compra
        fields = '__all__'