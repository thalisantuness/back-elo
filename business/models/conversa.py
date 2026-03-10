from django.db import models
from .usuario import Usuario


class Conversa(models.Model):
    conversa_id = models.AutoField(primary_key=True)
    usuario1 = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='conversas_iniciadas')
    usuario2 = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='conversas_recebidas')
    ultima_mensagem = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'conversas'
        unique_together = ['usuario1', 'usuario2']

    def __str__(self):
        return f"Conversa {self.conversa_id}"


class Mensagem(models.Model):
    mensagem_id = models.AutoField(primary_key=True)
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name='mensagens')
    remetente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensagens_enviadas')
    conteudo = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)

    class Meta:
        db_table = 'mensagens'
        ordering = ['data_envio']

    def __str__(self):
        return f"Mensagem {self.mensagem_id}"