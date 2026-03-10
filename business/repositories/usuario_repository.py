from django.db import transaction
from django.db.models import Q
from business.models import Usuario, Regra
from business.services.image_upload import image_upload_service
from .base_repository import BaseRepository


class UsuarioRepository(BaseRepository):
    def __init__(self):
        super().__init__(Usuario)

    def get_by_email(self, email):
        """Busca usuário por email"""
        try:
            return Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return None

    def get_by_id_with_regra(self, id):
        """Busca usuário com regra"""
        try:
            return Usuario.objects.select_related('regra', 'cdl').get(pk=id)
        except Usuario.DoesNotExist:
            return None

    def get_cdls_ativas(self):
        """Lista CDLs ativas"""
        return Usuario.objects.filter(
            role='cdl',
            status='ativo'
        ).order_by('nome')

    def get_lojas_por_cdl(self, cdl_id, apenas_ativas=True):
        """Lista lojas de uma CDL"""
        filters = {
            'role': 'empresa',
            'cdl_id': cdl_id
        }
        if apenas_ativas:
            filters['status'] = 'ativo'

        return Usuario.objects.filter(**filters).order_by('nome')

    def get_empresas_ativas(self, filters=None):
        """Lista empresas ativas"""
        base_filters = {
            'role': 'empresa',
            'status': 'ativo'
        }
        if filters:
            base_filters.update(filters)
        return Usuario.objects.filter(**base_filters).select_related('regra', 'cdl')

    @transaction.atomic
    def create_usuario(self, usuario_data, foto_base64=None):
        """Cria usuário com opção de foto"""
        if foto_base64:
            try:
                usuario_data['foto_perfil'] = image_upload_service.upload_base64_image(
                    foto_base64,
                    'usuarios/perfil'
                )
            except Exception as e:
                raise ValueError(f"Erro ao processar foto: {str(e)}")

        from business.serializers import UsuarioSerializer
        serializer = UsuarioSerializer(data=usuario_data)
        if serializer.is_valid():
            return serializer.save()
        raise ValueError(serializer.errors)

    @transaction.atomic
    def update_foto_perfil(self, usuario_id, foto_base64):
        """Atualiza foto de perfil"""
        usuario = self.get_by_id(usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado")

        # Deletar foto antiga
        if usuario.foto_perfil:
            try:
                image_upload_service.delete_from_s3(usuario.foto_perfil)
            except:
                pass

        # Upload nova foto
        url = image_upload_service.upload_base64_image(
            foto_base64,
            'usuarios/perfil'
        )

        usuario.foto_perfil = url
        usuario.save()
        return usuario

    def get_funcionarios_empresa(self, empresa_pai_id):
        """Busca funcionários de uma empresa"""
        return Usuario.objects.filter(
            role='empresa-funcionario',
            cdl_id=empresa_pai_id
        ).values_list('usuario_id', flat=True)

    def get_empresa_pai_id(self, usuario_id):
        """Busca ID da empresa pai"""
        try:
            usuario = Usuario.objects.get(pk=usuario_id)
            if usuario.role == 'empresa' and not usuario.cdl:
                return usuario.usuario_id
            elif usuario.role in ['empresa-funcionario', 'empresa'] and usuario.cdl:
                return usuario.cdl.usuario_id
            return None
        except Usuario.DoesNotExist:
            return None

    @transaction.atomic
    def atualizar_dados_empresa(self, usuario_id, dados):
        """Atualiza dados comerciais da empresa e sua regra"""
        usuario = self.get_by_id_with_regra(usuario_id)
        if not usuario or usuario.role != 'empresa':
            raise ValueError("Empresa não encontrada")

        # Atualizar dados básicos
        for field in ['cnpj', 'telefone', 'cidade', 'estado', 'modalidade_pontuacao']:
            if field in dados:
                setattr(usuario, field, dados[field])
        usuario.save()

        # Atualizar regra se fornecida
        if any(k in dados for k in ['nome_regra', 'tipo', 'pontos', 'multiplicador']):
            from .regra_repository import RegraRepository
            regra_repo = RegraRepository()

            regra_data = {
                'empresa_id': usuario_id,
                'nome': dados.get('nome_regra', 'Regra Padrão'),
                'tipo': dados.get('tipo', 'por_compra'),
                'valor_minimo': dados.get('valor_minimo', 0),
                'pontos': dados.get('pontos', 1),
                'multiplicador': dados.get('multiplicador', 1.0),
                'ativa': True
            }

            if usuario.regra:
                regra_repo.update_regra(usuario.regra.regra_id, regra_data)
            else:
                regra = regra_repo.create_regra(**regra_data)
                usuario.regra = regra
                usuario.save()

        return usuario

    @transaction.atomic
    def give_points(self, usuario_id, pontos):
        """Adiciona pontos a um usuário"""
        usuario = self.get_by_id(usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado")

        usuario.pontos += pontos
        usuario.save()
        return usuario

    def listar_por_role(self, usuario_logado):
        """Lista usuários baseado na role do usuário logado"""
        role = usuario_logado.role
        usuario_id = usuario_logado.usuario_id

        if role == 'admin':
            return Usuario.objects.all()

        elif role == 'cdl':
            # Empresas da CDL
            empresas = Usuario.objects.filter(role='empresa', cdl_id=usuario_id)
            empresas_ids = [e.usuario_id for e in empresas]

            # Clientes da CDL
            clientes = Usuario.objects.filter(role='cliente', cdl_id=usuario_id)

            # Funcionários das empresas
            funcionarios = Usuario.objects.filter(
                role='empresa-funcionario',
                cdl_id__in=empresas_ids if empresas_ids else [-1]
            )

            return (empresas | clientes | funcionarios).distinct()

        elif role == 'empresa':
            # Clientes que já compraram
            from business.models import Compra
            clientes_compras = Compra.objects.filter(
                empresa_id=usuario_id,
                cliente__isnull=False
            ).values_list('cliente_id', flat=True).distinct()

            return Usuario.objects.filter(
                Q(role='cliente', cdl_id=usuario_id) |
                Q(role='cliente', usuario_id__in=clientes_compras) |
                Q(role='empresa-funcionario', cdl_id=usuario_id)
            )

        elif role == 'cliente':
            if usuario_logado.cdl:
                return Usuario.objects.filter(
                    role='empresa',
                    cdl=usuario_logado.cdl,
                    status='ativo'
                )
            return Usuario.objects.none()

        return Usuario.objects.none()