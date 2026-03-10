from django.db import transaction
from django.db.models import Q
from business.models import Conversa, Mensagem, Usuario
from .base_repository import BaseRepository


class ConversaRepository(BaseRepository):
    def __init__(self):
        super().__init__(Conversa)

    def get_or_create_conversa(self, usuario1_id, usuario2_id):
        """Busca ou cria uma conversa entre dois usuários"""
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

    def get_conversas_usuario(self, usuario_id, role, cdl_id=None):
        """Lista conversas de um usuário baseado na role"""
        if role == 'cliente':
            return Conversa.objects.filter(usuario1_id=usuario_id)
        elif role == 'empresa' and not cdl_id:
            return Conversa.objects.filter(usuario2_id=usuario_id)
        elif role in ['empresa-funcionario', 'empresa'] and cdl_id:
            return Conversa.objects.filter(usuario2_id=cdl_id)
        return Conversa.objects.none()

    def add_mensagem(self, conversa_id, remetente_id, conteudo):
        """Adiciona mensagem a uma conversa"""
        with transaction.atomic():
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

    def get_mensagens(self, conversa_id):
        """Lista mensagens de uma conversa"""
        return Mensagem.objects.filter(
            conversa_id=conversa_id
        ).select_related('remetente').order_by('data_envio')

    def marcar_como_lida(self, mensagem_id):
        """Marca mensagem como lida"""
        Mensagem.objects.filter(pk=mensagem_id).update(lida=True)

    def count_nao_lidas(self, conversa_id, usuario_id):
        """Conta mensagens não lidas em uma conversa"""
        return Mensagem.objects.filter(
            conversa_id=conversa_id,
            lida=False
        ).exclude(remetente_id=usuario_id).count()