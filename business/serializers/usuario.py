from rest_framework import serializers
from business.models import Usuario, Regra


class RegraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regra
        fields = '__all__'


class UsuarioSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(write_only=True)
    regra = RegraSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'usuario_id', 'uuid', 'role', 'nome', 'telefone', 'email',
            'foto_perfil', 'cliente_endereco', 'cidade', 'estado', 'pontos',
            'cnpj', 'status', 'regra', 'modalidade_pontuacao', 'cdl',
            'data_cadastro', 'data_atualizacao', 'senha', 'is_active', 'is_staff'
        ]
        read_only_fields = ['usuario_id', 'uuid', 'pontos', 'data_cadastro', 'data_atualizacao']

    def create(self, validated_data):
        password = validated_data.pop('senha')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        if 'senha' in validated_data:
            password = validated_data.pop('senha')
            instance.set_password(password)
        return super().update(instance, validated_data)


class UsuarioDetailSerializer(UsuarioSerializer):
    cdl_info = serializers.SerializerMethodField()
    regra_info = serializers.SerializerMethodField()

    class Meta(UsuarioSerializer.Meta):
        fields = UsuarioSerializer.Meta.fields + ['cdl_info', 'regra_info']

    def get_cdl_info(self, obj):
        if obj.cdl:
            return {
                'usuario_id': obj.cdl.usuario_id,
                'nome': obj.cdl.nome,
                'cidade': obj.cdl.cidade,
                'estado': obj.cdl.estado
            }
        return None

    def get_regra_info(self, obj):
        try:
            regra = Regra.objects.get(usuario=obj, ativa=True)
            return RegraSerializer(regra).data
        except Regra.DoesNotExist:
            return None