import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from business import Conversa, Mensagem, Usuario
from business import usuario_repo

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Conexão WebSocket"""
        self.user = None

        # Autenticar via token na query string
        query_string = self.scope['query_string'].decode()
        token = None

        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break

        if not token:
            await self.close()
            return

        try:
            # Validar token
            access_token = AccessToken(token)
            user_id = access_token['user_id']

            # Buscar usuário
            self.user = await self.get_user(user_id)

            if not self.user:
                await self.close()
                return

            # Adicionar ao grupo do usuário
            self.user_group_name = f'user_{self.user.usuario_id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )

            await self.accept()
            logger.info(f"WebSocket conectado: {self.user.email}")

        except Exception as e:
            logger.error(f"Erro na autenticação WebSocket: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        """Desconexão"""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        logger.info("WebSocket desconectado")

    async def receive(self, text_data):
        """Receber mensagem"""
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'send_message':
                await self.handle_send_message(data)
            elif action == 'mark_read':
                await self.handle_mark_read(data)
            else:
                await self.send_error("Ação desconhecida")

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            await self.send_error(str(e))

    async def handle_send_message(self, data):
        """Enviar mensagem via WebSocket"""
        destinatario_id = data.get('destinatario_id')
        conteudo = data.get('conteudo')

        if not destinatario_id or not conteudo:
            await self.send_error("destinatario_id e conteudo são obrigatórios")
            return

        # Buscar destinatário
        destinatario = await self.get_user(destinatario_id)
        if not destinatario:
            await self.send_error("Destinatário não encontrado")
            return

        # Validar permissões
        if not await self.pode_conversar(self.user, destinatario):
            await self.send_error("Conversa não permitida entre estes tipos de usuário")
            return

        # Determinar IDs da conversa
        if self.user.role == 'cliente':
            usuario1_id = self.user.usuario_id
            empresa_pai_id = await self.get_empresa_pai_id(destinatario_id)
            if not empresa_pai_id:
                await self.send_error("Destinatário não é uma empresa válida")
                return
            usuario2_id = empresa_pai_id

        elif self.user.role in ['empresa', 'empresa-funcionario']:
            usuario1_id = destinatario_id
            empresa_pai_id = await self.get_empresa_pai_id(self.user.usuario_id)
            if not empresa_pai_id:
                await self.send_error("Empresa não encontrada")
                return
            usuario2_id = empresa_pai_id

        else:
            await self.send_error("Tipo de usuário não pode enviar mensagens")
            return

        # Criar ou buscar conversa
        conversa = await self.get_or_create_conversa(usuario1_id, usuario2_id)

        # Criar mensagem
        mensagem = await self.create_mensagem(
            conversa.conversa_id,
            self.user.usuario_id,
            conteudo
        )

        # Preparar dados da mensagem
        mensagem_data = {
            'mensagem_id': mensagem.mensagem_id,
            'conversa_id': conversa.conversa_id,
            'remetente_id': self.user.usuario_id,
            'remetente_nome': self.user.nome,
            'conteudo': conteudo,
            'data_envio': mensagem.data_envio.isoformat(),
            'lida': False
        }

        # Enviar para os participantes
        if self.user.role == 'cliente':
            # Cliente enviando: enviar para empresa pai e funcionários
            await self.channel_layer.group_send(
                f'user_{usuario2_id}',
                {
                    'type': 'chat_message',
                    'message': mensagem_data
                }
            )

            # Enviar para funcionários
            funcionarios = await self.get_funcionarios_empresa(usuario2_id)
            for func_id in funcionarios:
                await self.channel_layer.group_send(
                    f'user_{func_id}',
                    {
                        'type': 'chat_message',
                        'message': mensagem_data
                    }
                )
        else:
            # Empresa/funcionário enviando: enviar apenas para o cliente
            await self.channel_layer.group_send(
                f'user_{usuario1_id}',
                {
                    'type': 'chat_message',
                    'message': mensagem_data
                }
            )

        # Confirmar para o remetente
        await self.send(text_data=json.dumps({
            'type': 'message_sent',
            'message': mensagem_data
        }))

    async def handle_mark_read(self, data):
        """Marcar mensagem como lida"""
        mensagem_id = data.get('mensagem_id')

        if not mensagem_id:
            await self.send_error("mensagem_id é obrigatório")
            return

        mensagem = await self.get_mensagem(mensagem_id)
        if not mensagem:
            await self.send_error("Mensagem não encontrada")
            return

        # Verificar se usuário tem permissão
        conversa = await self.get_conversa(mensagem.conversa_id)
        if not conversa:
            return

        tem_acesso = await self.tem_acesso_conversa(self.user, conversa)
        if not tem_acesso:
            await self.send_error("Acesso negado")
            return

        # Marcar como lida
        await self.marcar_mensagem_lida(mensagem_id)

        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'mensagem_id': mensagem_id
        }))

    async def chat_message(self, event):
        """Enviar mensagem para o cliente WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))

    async def send_error(self, error_message):
        """Enviar erro"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'error': error_message
        }))

    # Métodos auxiliares assíncronos
    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None

    @database_sync_to_async
    def get_empresa_pai_id(self, usuario_id):
        return usuario_repo.get_empresa_pai_id(usuario_id)

    @database_sync_to_async
    def get_funcionarios_empresa(self, empresa_pai_id):
        return list(usuario_repo.get_funcionarios_empresa(empresa_pai_id))

    @database_sync_to_async
    def pode_conversar(self, remetente, destinatario):
        if remetente.role == 'admin':
            return True
        if remetente.role == 'cliente' and destinatario.role in ['empresa', 'empresa-funcionario']:
            return True
        if remetente.role == 'empresa' and destinatario.role == 'cliente':
            return True
        if remetente.role == 'empresa-funcionario' and destinatario.role == 'cliente':
            return True
        return False

    @database_sync_to_async
    def get_or_create_conversa(self, usuario1_id, usuario2_id):
        conversa = Conversa.objects.filter(
            usuario1_id=usuario1_id,
            usuario2_id=usuario2_id
        ).first()

        if not conversa:
            conversa = Conversa.objects.create(
                usuario1_id=usuario1_id,
                usuario2_id=usuario2_id
            )

        return conversa

    @database_sync_to_async
    def create_mensagem(self, conversa_id, remetente_id, conteudo):

        mensagem = Mensagem.objects.create(
            conversa_id=conversa_id,
            remetente_id=remetente_id,
            conteudo=conteudo
        )

        # Atualizar última mensagem da conversa
        Conversa.objects.filter(conversa_id=conversa_id).update(
            ultima_mensagem=mensagem.data_envio
        )

        return mensagem

    @database_sync_to_async
    def get_mensagem(self, mensagem_id):
        try:
            return Mensagem.objects.get(pk=mensagem_id)
        except Mensagem.DoesNotExist:
            return None

    @database_sync_to_async
    def get_conversa(self, conversa_id):
        try:
            return Conversa.objects.get(pk=conversa_id)
        except Conversa.DoesNotExist:
            return None

    @database_sync_to_async
    def tem_acesso_conversa(self, user, conversa):
        if user.role == 'cliente':
            return conversa.usuario1_id == user.usuario_id
        if user.role == 'empresa' and not user.cdl:
            return conversa.usuario2_id == user.usuario_id
        if user.role in ['empresa-funcionario', 'empresa'] and user.cdl:
            return conversa.usuario2_id == user.cdl.usuario_id
        return False

    @database_sync_to_async
    def marcar_mensagem_lida(self, mensagem_id):
        Mensagem.objects.filter(pk=mensagem_id).update(lida=True)