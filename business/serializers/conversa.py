from rest_framework import serializers
from business.models import Conversa, Mensagem
from .usuario import UsuarioSerializer


class MensagemSerializer(serializers.ModelSerializer):
    remetente_info = UsuarioSerializer(source='remetente', read_only=True)

    class Meta:
        model = Mensagem
        fields = '__all__'


class ConversaSerializer(serializers.ModelSerializer):
    usuario1_info = UsuarioSerializer(source='usuario1', read_only=True)
    usuario2_info = UsuarioSerializer(source='usuario2', read_only=True)
    ultima_mensagem_info = serializers.SerializerMethodField()
    mensagens = MensagemSerializer(many=True, read_only=True)

    class Meta:
        model = Conversa
        fields = '__all__'

    def get_ultima_mensagem_info(self, obj):
        ultima = obj.mensagens.order_by('-data_envio').first()
        if ultima:
            return MensagemSerializer(ultima).data
        return None