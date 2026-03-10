from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
import logging

from business.models import Conversa, Mensagem, Usuario
from business.repositories import conversa_repo, usuario_repo
from business.serializers import ConversaSerializer, MensagemSerializer
from .base_view import BaseView

logger = logging.getLogger(__name__)


class ConversaViewSet(ViewSet, BaseView):

    def list(self, request):
        """Listar conversas do usuário"""
        try:
            user = request.user
            usuario_id = user.usuario_id

            if user.role == 'cliente':
                # Cliente vê conversas onde ele é usuario1
                conversas = Conversa.objects.filter(usuario1_id=usuario_id)

            elif user.role == 'empresa' and not user.cdl:
                # Empresa pai vê conversas onde ela é usuario2
                conversas = Conversa.objects.filter(usuario2_id=usuario_id)

            elif user.role == 'empresa-funcionario' and user.cdl:
                # Funcionário vê conversas da empresa pai
                conversas = Conversa.objects.filter(usuario2_id=user.cdl.usuario_id)

            elif user.role == 'empresa' and user.cdl:
                # Empresa filha vê conversas da empresa pai
                conversas = Conversa.objects.filter(usuario2_id=user.cdl.usuario_id)

            else:
                return Response([])

            # Ordenar por última mensagem
            conversas = conversas.prefetch_related(
                'mensagens', 'usuario1', 'usuario2'
            ).order_by('-ultima_mensagem')

            serializer = ConversaSerializer(conversas, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao listar conversas: {str(e)}")
            return self.error_response("Erro ao listar conversas")

    def retrieve(self, request, pk=None):
        """Buscar conversa com mensagens"""
        try:
            conversa = Conversa.objects.prefetch_related(
                'mensagens__remetente'
            ).filter(pk=pk).first()

            if not conversa:
                return self.not_found_response("Conversa não encontrada")

            # Verificar acesso
            user = request.user
            tem_acesso = False

            if user.role == 'cliente':
                tem_acesso = conversa.usuario1_id == user.usuario_id
            elif user.role == 'empresa' and not user.cdl:
                tem_acesso = conversa.usuario2_id == user.usuario_id
            elif user.role in ['empresa-funcionario', 'empresa'] and user.cdl:
                tem_acesso = conversa.usuario2_id == user.cdl.usuario_id

            if not tem_acesso:
                return self.forbidden_response()

            serializer = ConversaSerializer(conversa)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao buscar conversa: {str(e)}")
            return self.error_response("Erro ao buscar conversa")

    @action(detail=True, methods=['get'], url_path='mensagens')
    def mensagens(self, request, pk=None):
        """Listar mensagens de uma conversa"""
        try:
            conversa = Conversa.objects.filter(pk=pk).first()
            if not conversa:
                return self.not_found_response("Conversa não encontrada")

            # Verificar acesso
            user = request.user
            tem_acesso = False

            if user.role == 'cliente':
                tem_acesso = conversa.usuario1_id == user.usuario_id
            elif user.role == 'empresa' and not user.cdl:
                tem_acesso = conversa.usuario2_id == user.usuario_id
            elif user.role in ['empresa-funcionario', 'empresa'] and user.cdl:
                tem_acesso = conversa.usuario2_id == user.cdl.usuario_id

            if not tem_acesso:
                return self.forbidden_response()

            mensagens = Mensagem.objects.filter(
                conversa_id=pk
            ).select_related('remetente').order_by('data_envio')

            serializer = MensagemSerializer(mensagens, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao listar mensagens: {str(e)}")
            return self.error_response("Erro ao listar mensagens")

    @action(detail=False, methods=['post'], url_path='enviar')
    def enviar_mensagem(self, request):
        """Enviar mensagem (via REST, não via WebSocket)"""
        try:
            destinatario_id = request.data.get('destinatario_id')
            conteudo = request.data.get('conteudo')

            if not destinatario_id or not conteudo:
                return self.error_response("destinatario_id e conteudo são obrigatórios")

            # Buscar destinatário
            destinatario = Usuario.objects.filter(pk=destinatario_id).first()
            if not destinatario:
                return self.error_response("Destinatário não encontrado")

            # Validar permissões de conversa
            user = request.user
            pode_conversar = False

            # Admin pode conversar com qualquer um
            if user.role == 'admin':
                pode_conversar = True
            # Cliente pode conversar com empresa ou funcionário
            elif user.role == 'cliente' and destinatario.role in ['empresa', 'empresa-funcionario']:
                pode_conversar = True
            # Empresa pode conversar com cliente
            elif user.role == 'empresa' and destinatario.role == 'cliente':
                pode_conversar = True
            # Funcionário pode conversar com cliente
            elif user.role == 'empresa-funcionario' and destinatario.role == 'cliente':
                pode_conversar = True

            if not pode_conversar:
                return self.forbidden_response("Conversa não permitida entre estes tipos de usuário")

            # Determinar IDs da conversa (cliente sempre usuario1, empresa pai sempre usuario2)
            if user.role == 'cliente':
                usuario1_id = user.usuario_id

                # Buscar empresa pai do destinatário
                empresa_pai_id = usuario_repo.get_empresa_pai_id(destinatario_id)
                if not empresa_pai_id:
                    return self.error_response("Destinatário não é uma empresa válida")

                usuario2_id = empresa_pai_id

            elif user.role in ['empresa', 'empresa-funcionario']:
                # Empresa/funcionário enviando: cliente é usuario1
                usuario1_id = destinatario_id

                # Empresa pai é usuario2
                empresa_pai_id = usuario_repo.get_empresa_pai_id(user.usuario_id)
                if not empresa_pai_id:
                    return self.error_response("Empresa não encontrada")

                usuario2_id = empresa_pai_id

            else:
                return self.error_response("Tipo de usuário não pode enviar mensagens")

            # Criar ou buscar conversa
            conversa = Conversa.objects.filter(
                usuario1_id=usuario1_id,
                usuario2_id=usuario2_id
            ).first()

            if not conversa:
                conversa = Conversa.objects.create(
                    usuario1_id=usuario1_id,
                    usuario2_id=usuario2_id
                )

            # Criar mensagem
            mensagem = Mensagem.objects.create(
                conversa=conversa,
                remetente=user,
                conteudo=conteudo
            )

            # Atualizar última mensagem da conversa
            conversa.ultima_mensagem = mensagem.data_envio
            conversa.save()

            serializer = MensagemSerializer(mensagem)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return self.error_response("Erro ao enviar mensagem")

    @action(detail=True, methods=['patch'], url_path='mensagens/(?P<mensagem_id>[^/.]+)/ler')
    def marcar_lida(self, request, pk=None, mensagem_id=None):
        """Marcar mensagem como lida"""
        try:
            conversa = Conversa.objects.filter(pk=pk).first()
            if not conversa:
                return self.not_found_response("Conversa não encontrada")

            # Verificar acesso
            user = request.user
            tem_acesso = False

            if user.role == 'cliente':
                tem_acesso = conversa.usuario1_id == user.usuario_id
            elif user.role == 'empresa' and not user.cdl:
                tem_acesso = conversa.usuario2_id == user.usuario_id
            elif user.role in ['empresa-funcionario', 'empresa'] and user.cdl:
                tem_acesso = conversa.usuario2_id == user.cdl.usuario_id

            if not tem_acesso:
                return self.forbidden_response()

            mensagem = Mensagem.objects.filter(
                mensagem_id=mensagem_id,
                conversa_id=pk
            ).first()

            if not mensagem:
                return self.not_found_response("Mensagem não encontrada")

            mensagem.lida = True
            mensagem.save()

            return self.success_response(message="Mensagem marcada como lida")

        except Exception as e:
            logger.error(f"Erro ao marcar mensagem: {str(e)}")
            return self.error_response("Erro ao processar mensagem")