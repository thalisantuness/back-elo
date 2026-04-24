from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
import logging

from business.repositories import usuario_repo, regra_repo
from business.serializers import UsuarioSerializer, UsuarioDetailSerializer
from business.models import Usuario
from .base_view import BaseView

logger = logging.getLogger(__name__)


class UsuarioViewSet(ViewSet, BaseView):

    def get_permissions(self):
        """Permissões baseadas na ação"""
        if self.action in ['login', 'create', 'list_cdls', 'list_lojas_cdl']:
            return []  # Público
        return [IsAuthenticated()]

    # POST /login
    @action(detail=False, methods=['post'], permission_classes=[])
    def login(self, request):
        """Login de usuário"""
        email = request.data.get('email')
        senha = request.data.get('senha')

        if not email or not senha:
            return self.error_response("Email e senha são obrigatórios")

        user = authenticate(request, username=email, password=senha)

        if not user:
            return self.error_response("Credenciais inválidas", status.HTTP_401_UNAUTHORIZED)

        if user.status == 'bloqueado':
            return self.error_response("Usuário bloqueado", status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)

        # Dados do usuário
        serializer = UsuarioSerializer(user)
        user_data = serializer.data
        user_data.pop('password', None)

        return Response({
            'usuario': user_data,
            'token': str(refresh.access_token),
            'refresh': str(refresh)
        })

    # POST /usuarios
    def create(self, request):
        """Registro de usuário - POST /usuarios"""
        try:
            with transaction.atomic():
                data = request.data.copy()
                foto_base64 = data.pop('foto_perfil', None)

                # Validações básicas
                required_fields = ['nome', 'email', 'senha', 'role']
                for field in required_fields:
                    if field not in data:
                        return self.error_response(f"Campo {field} é obrigatório")

                # Validar role
                roles_validas = ['cliente', 'empresa', 'admin', 'cdl', 'empresa-funcionario']
                if data['role'] not in roles_validas:
                    return self.error_response(f"Role inválida. Use: {', '.join(roles_validas)}")

                # Verificar email duplicado
                if usuario_repo.get_by_email(data['email']):
                    return self.error_response("Email já cadastrado")

                # Para cliente, cliente_endereco é o campo usado (não endereco)
                if data['role'] == 'cliente' and 'endereco' in data and 'cliente_endereco' not in data:
                    data['cliente_endereco'] = data.pop('endereco')

                # Para empresa/cdl, manter compatibilidade
                if data['role'] in ['empresa', 'cdl'] and 'endereco' in data:
                    # Mapear endereco para cliente_endereco temporariamente
                    data['cliente_endereco'] = data.pop('endereco')

                # Determinar cdl_id baseado no contexto
                user = self.get_user(request) if request.user.is_authenticated else None

                if user and user.role == 'cdl' and data['role'] in ['empresa', 'cliente']:
                    data['cdl_id'] = user.usuario_id
                elif user and user.role == 'empresa' and data['role'] in ['empresa-funcionario', 'cliente']:
                    data['cdl_id'] = user.usuario_id
                elif data['role'] == 'cliente' and not data.get('cdl_id'):
                    return self.error_response("Cliente deve informar cdl_id")
                elif data['role'] == 'empresa' and not data.get('cdl_id') and (not user or user.role != 'cdl'):
                    return self.error_response("Empresa deve informar cdl_id ou ser criada por uma CDL")

                # Definir status inicial
                data['status'] = 'ativo'

                # Mapeia cdl_id para cdl para o DRF ModelSerializer
                if 'cdl_id' in data:
                    data['cdl'] = data.pop('cdl_id')

                # Criar usuário
                usuario = usuario_repo.create_usuario(data, foto_base64)

                serializer = UsuarioSerializer(usuario)
                user_data = serializer.data
                user_data.pop('password', None)

                return Response({
                    'message': 'Usuário cadastrado com sucesso',
                    'usuario': user_data
                }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro no registro: {str(e)}")
            return self.error_response("Erro interno ao cadastrar usuário")

    # GET /usuarios
    def list(self, request):
        """Listar usuários baseado na role"""
        try:
            usuarios = usuario_repo.listar_por_role(request.user)
            serializer = UsuarioSerializer(usuarios, many=True)

            # Remover senha
            data = serializer.data
            for item in data:
                item.pop('password', None)

            return Response(data)
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {str(e)}")
            return self.error_response("Erro ao listar usuários")

    # GET /usuarios/:id
    def retrieve(self, request, pk=None):
        """Buscar usuário por ID"""
        try:
            usuario = usuario_repo.get_by_id_with_regra(pk)
            if not usuario:
                return self.not_found_response("Usuário não encontrado")

            serializer = UsuarioDetailSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return Response(data)
        except Exception as e:
            logger.error(f"Erro ao buscar usuário: {str(e)}")
            return self.error_response("Erro ao buscar usuário")

    # PUT /usuarios/:id e PATCH /usuarios/:id/perfil
    def update_perfil(self, request, pk=None):
        """Atualizar perfil do usuário"""
        try:
            # Verificar permissão
            if int(pk) != request.user.usuario_id and request.user.role != 'admin':
                return self.forbidden_response()

            usuario = usuario_repo.get_by_id(pk)
            if not usuario:
                return self.not_found_response()

            # Campos permitidos
            allowed_fields = ['nome', 'telefone', 'cliente_endereco', 'cidade', 'estado', 'email']
            update_data = {}

            for field in allowed_fields:
                if field in request.data:
                    update_data[field] = request.data[field]

            # Verificar email duplicado
            if 'email' in update_data and update_data['email'] != usuario.email:
                if usuario_repo.get_by_email(update_data['email']):
                    return self.error_response("Este e-mail já está em uso por outro usuário")

            # Validar telefone
            if 'telefone' in update_data:
                telefone = update_data['telefone'].replace(r'\D', '')
                if not (10 <= len(telefone) <= 11):
                    return self.error_response("Telefone inválido")
                update_data['telefone'] = telefone

            # Atualizar
            for key, value in update_data.items():
                setattr(usuario, key, value)
            usuario.save()

            serializer = UsuarioSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return self.success_response(data, "Perfil atualizado com sucesso")

        except Exception as e:
            logger.error(f"Erro ao atualizar perfil: {str(e)}")
            return self.error_response("Erro ao atualizar perfil")

    # PATCH /usuarios/:id/foto
    @action(detail=True, methods=['patch'], url_path='foto')
    def update_foto(self, request, pk=None):
        """Atualizar foto de perfil"""
        try:
            if int(pk) != request.user.usuario_id:
                return self.forbidden_response()

            foto_base64 = request.data.get('foto_perfil')
            if not foto_base64:
                return self.error_response("Foto é obrigatória")

            usuario = usuario_repo.update_foto_perfil(pk, foto_base64)

            serializer = UsuarioSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return self.success_response(data, "Foto atualizada com sucesso")

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao atualizar foto: {str(e)}")
            return self.error_response("Erro ao atualizar foto")

    # PATCH /usuarios/:id/senha
    @action(detail=True, methods=['patch'], url_path='senha')
    def change_password(self, request, pk=None):
        """Alterar senha"""
        try:
            if int(pk) != request.user.usuario_id:
                return self.forbidden_response()

            senha_atual = request.data.get('senhaAtual')
            nova_senha = request.data.get('novaSenha')

            if not senha_atual or not nova_senha:
                return self.error_response("Senha atual e nova senha são obrigatórias")

            usuario = request.user

            # Verificar senha atual
            if not usuario.check_password(senha_atual):
                return self.error_response("Senha atual incorreta", status.HTTP_401_UNAUTHORIZED)

            # Alterar senha
            usuario.set_password(nova_senha)
            usuario.save()

            return self.success_response(message="Senha alterada com sucesso")

        except Exception as e:
            logger.error(f"Erro ao alterar senha: {str(e)}")
            return self.error_response("Erro ao alterar senha")

    # GET /cdls (público)
    @action(detail=False, methods=['get'], permission_classes=[])
    def list_cdls(self, request):
        """Listar CDLs ativas"""
        try:
            cdls = usuario_repo.get_cdls_ativas()
            data = [{
                'usuario_id': c.usuario_id,
                'nome': c.nome,
                'cidade': c.cidade,
                'estado': c.estado,
                'foto_perfil': c.foto_perfil,
                'telefone': c.telefone,
                'email': c.email
            } for c in cdls]

            return Response(data)
        except Exception as e:
            logger.error(f"Erro ao listar CDLs: {str(e)}")
            return self.error_response("Erro ao listar CDLs")

    # GET /cdls/:cdl_id/lojas (público)
    @action(detail=False, methods=['get'], url_path='cdls/(?P<cdl_id>[^/.]+)/lojas', permission_classes=[])
    def list_lojas_cdl(self, request, cdl_id=None):
        """Listar lojas de uma CDL"""
        try:
            lojas = usuario_repo.get_lojas_por_cdl(cdl_id)
            data = [{
                'usuario_id': l.usuario_id,
                'nome': l.nome,
                'telefone': l.telefone,
                'foto_perfil': l.foto_perfil,
                'cidade': l.cidade,
                'status': l.status
            } for l in lojas]

            return Response(data)
        except Exception as e:
            logger.error(f"Erro ao listar lojas: {str(e)}")
            return self.error_response("Erro ao listar lojas")

    # GET /minha-cdl/dashboard
    @action(detail=False, methods=['get'], url_path='dashboard/cdl')
    def dashboard_cdl(self, request):
        """Dashboard da CDL"""
        try:
            if request.user.role not in ['cdl', 'admin']:
                return self.forbidden_response()

            cdl_id = request.query_params.get('cdl_id', request.user.usuario_id)

            total_lojas = Usuario.objects.filter(
                role='empresa',
                cdl_id=cdl_id,
                status='ativo'
            ).count()

            total_clientes = Usuario.objects.filter(
                role='cliente',
                cdl_id=cdl_id
            ).count()

            lojas_recentes = Usuario.objects.filter(
                role='empresa',
                cdl_id=cdl_id
            ).order_by('-data_cadastro')[:10].values(
                'usuario_id', 'nome', 'status', 'data_cadastro', 'foto_perfil'
            )

            return Response({
                'cdl_id': cdl_id,
                'totalLojas': total_lojas,
                'totalClientes': total_clientes,
                'lojasRecentes': list(lojas_recentes)
            })

        except Exception as e:
            logger.error(f"Erro no dashboard CDL: {str(e)}")
            return self.error_response("Erro ao carregar dashboard")

    # PUT /cliente/:id/trocar-cdl
    @action(detail=True, methods=['put'], url_path='trocar-cdl')
    def trocar_cdl(self, request, pk=None):
        """Cliente trocar de CDL"""
        try:
            if request.user.role != 'cliente' or request.user.usuario_id != int(pk):
                return self.forbidden_response()

            nova_cdl_id = request.data.get('nova_cdl_id')
            if not nova_cdl_id:
                return self.error_response("nova_cdl_id é obrigatório")

            # Verificar se CDL existe
            cdl = Usuario.objects.filter(
                usuario_id=nova_cdl_id,
                role='cdl',
                status='ativo'
            ).first()

            if not cdl:
                return self.error_response("CDL não encontrada ou inativa")

            usuario = request.user
            usuario.cdl_id = nova_cdl_id
            usuario.save()

            serializer = UsuarioSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return self.success_response(data, "CDL alterada com sucesso")

        except Exception as e:
            logger.error(f"Erro ao trocar CDL: {str(e)}")
            return self.error_response("Erro ao trocar CDL")

    # GET /empresas
    @action(detail=False, methods=['get'], url_path='empresas')
    def list_empresas(self, request):
        """Listar empresas ativas"""
        try:
            filters = {}

            if request.user.role == 'cdl':
                filters['cdl_id'] = request.user.usuario_id
            elif request.user.role == 'cliente':
                if request.user.cdl:
                    filters['cdl_id'] = request.user.cdl.usuario_id
                else:
                    return Response([])

            empresas = usuario_repo.get_empresas_ativas(filters)

            serializer = UsuarioSerializer(empresas, many=True)
            data = serializer.data
            for item in data:
                item.pop('password', None)

            return Response(data)

        except Exception as e:
            logger.error(f"Erro ao listar empresas: {str(e)}")
            return self.error_response("Erro ao listar empresas")

    # PUT /minha-empresa
    @action(detail=False, methods=['put'], url_path='minha-empresa')
    def atualizar_dados_empresa(self, request):
        """Atualizar dados da empresa logada"""
        try:
            if request.user.role != 'empresa':
                return self.forbidden_response("Apenas empresas podem atualizar dados comerciais")

            usuario = usuario_repo.atualizar_dados_empresa(request.user.usuario_id, request.data)

            serializer = UsuarioSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return self.success_response(data, "Dados da empresa atualizados com sucesso")

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao atualizar dados da empresa: {str(e)}")
            return self.error_response("Erro ao atualizar dados da empresa")

    # ==================== ROTAS ADMINISTRATIVAS ====================

    # GET /admin/usuarios
    @action(detail=False, methods=['get'], url_path='admin/usuarios')
    def visualizar_usuario(self, request):
        """Listar todos os usuários (admin only)"""
        if request.user.role != 'admin':
            return self.forbidden_response()

        try:
            usuarios = Usuario.objects.all()
            serializer = UsuarioSerializer(usuarios, many=True)
            data = serializer.data
            for item in data:
                item.pop('password', None)
            return Response(data)
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {str(e)}")
            return self.error_response("Erro ao listar usuários")

    # PUT /admin/tornar-admin
    @action(detail=False, methods=['put'], url_path='admin/tornar-admin')
    def tornar_admin(self, request):
        """Tornar usuário admin"""
        if request.user.role != 'admin':
            return self.forbidden_response()

        user_id = request.data.get('id')
        if not user_id:
            return self.error_response("ID do usuário é obrigatório")

        try:
            usuario = usuario_repo.get_by_id(user_id)
            if not usuario:
                return self.not_found_response("Usuário não encontrado")

            usuario.role = 'admin'
            usuario.status = 'ativo'
            usuario.save()

            serializer = UsuarioSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return self.success_response(data, f"Usuário {user_id} agora é admin")

        except Exception as e:
            logger.error(f"Erro ao tornar admin: {str(e)}")
            return self.error_response("Erro ao promover usuário")

    # PUT /admin/tornar-cdl
    @action(detail=False, methods=['put'], url_path='admin/tornar-cdl')
    def tornar_cdl(self, request):
        """Tornar usuário CDL"""
        if request.user.role != 'admin':
            return self.forbidden_response()

        user_id = request.data.get('id')
        if not user_id:
            return self.error_response("ID do usuário é obrigatório")

        try:
            usuario = usuario_repo.get_by_id(user_id)
            if not usuario:
                return self.not_found_response("Usuário não encontrado")

            usuario.role = 'cdl'
            usuario.status = 'pendente'
            usuario.save()

            serializer = UsuarioSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return self.success_response(data, f"Usuário {user_id} agora é CDL (pendente aprovação)")

        except Exception as e:
            logger.error(f"Erro ao tornar CDL: {str(e)}")
            return self.error_response("Erro ao promover usuário")

    # PUT /admin/aprovar-cdl/:id
    @action(detail=True, methods=['put'], url_path='admin/aprovar-cdl')
    def aprovar_cdl(self, request, pk=None):
        """Aprovar CDL"""
        if request.user.role != 'admin':
            return self.forbidden_response()

        try:
            usuario = usuario_repo.get_by_id(pk)
            if not usuario:
                return self.not_found_response()

            if usuario.role != 'cdl':
                return self.error_response("Usuário não é uma CDL")

            usuario.status = 'ativo'
            usuario.save()

            serializer = UsuarioSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return self.success_response(data, f"CDL {pk} aprovada com sucesso")

        except Exception as e:
            logger.error(f"Erro ao aprovar CDL: {str(e)}")
            return self.error_response("Erro ao aprovar CDL")

    # PUT /admin/usuarios/pontos/:id
    @action(detail=True, methods=['put'], url_path='admin/usuarios/pontos')
    def give_points(self, request, pk=None):
        """Adicionar pontos (admin only)"""
        if request.user.role != 'admin':
            return self.forbidden_response()

        try:
            pontos = request.data.get('pontos')
            if not pontos or not isinstance(pontos, int) or pontos <= 0:
                return self.error_response("Pontos deve ser um número positivo")

            usuario = usuario_repo.give_points(pk, pontos)

            serializer = UsuarioSerializer(usuario)
            data = serializer.data
            data.pop('password', None)

            return self.success_response(data, f"Pontos adicionados com sucesso")

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao adicionar pontos: {str(e)}")
            return self.error_response("Erro ao adicionar pontos")

    # DELETE /usuarios/:id
    def destroy(self, request, pk=None):
        """Deletar usuário (admin only)"""
        if request.user.role != 'admin':
            return self.forbidden_response()

        try:
            usuario = usuario_repo.get_by_id(pk)
            if not usuario:
                return self.not_found_response()

            # Deletar foto do S3
            if usuario.foto_perfil:
                from business.services.image_upload import image_upload_service
                image_upload_service.delete_from_s3(usuario.foto_perfil)

            usuario.delete()

            return self.success_response(message="Usuário excluído com sucesso")

        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {str(e)}")
            return self.error_response("Erro ao deletar usuário")