from rest_framework import serializers
from business.models import Produto, Foto


class FotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Foto
        fields = ['photo_id', 'imageData']


class ProdutoSerializer(serializers.ModelSerializer):
    fotos = FotoSerializer(many=True, read_only=True)
    empresa_nome = serializers.CharField(source='empresa.nome', read_only=True)

    class Meta:
        model = Produto
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Padronizar campos de imagem
        data['imageData'] = data.get('foto_principal')
        data['photos'] = data.get('fotos', [])
        return data