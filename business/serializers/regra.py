from rest_framework import serializers
from business.models import Regra


class RegraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regra
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['descricao'] = self.get_descricao(instance)
        return data

    def get_descricao(self, instance):
        if instance.tipo == 'por_compra':
            return f"{instance.pontos} pontos por compra"
        else:
            return f"{instance.multiplicador} pontos por real gasto"