from rest_framework import serializers
from business.models import SolicitacaoRecompensa
from .usuario import UsuarioSerializer
from .recompensa import RecompensaSerializer


class SolicitacaoSerializer(serializers.ModelSerializer):
    usuario_info = UsuarioSerializer(source='usuario', read_only=True)
    recompensa_info = RecompensaSerializer(source='recompensa', read_only=True)

    class Meta:
        model = SolicitacaoRecompensa
        fields = '__all__'