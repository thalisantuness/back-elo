from rest_framework import serializers
from business.models import Campanha


class CampanhaSerializer(serializers.ModelSerializer):
    empresa_info = serializers.SerializerMethodField()

    class Meta:
        model = Campanha
        fields = '__all__'

    def get_empresa_info(self, obj):
        if obj.empresa:
            return {
                'usuario_id': obj.empresa.usuario_id,
                'nome': obj.empresa.nome,
                'role': obj.empresa.role,
                'cdl_id': obj.empresa.cdl_id if obj.empresa.cdl else None
            }
        return None