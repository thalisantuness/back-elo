from django.db import models
from .usuario import Usuario
from .recompensa import Recompensa


class SolicitacaoRecompensa(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aceita', 'Aceita'),
        ('rejeitada', 'Rejeitada'),
    ]

    solicitacao_id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='solicitacoes')
    recompensa = models.ForeignKey(Recompensa, on_delete=models.CASCADE, related_name='solicitacoes')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_resposta = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'solicitacao_recompensas'

    def __str__(self):
        return f"Solicitação {self.solicitacao_id}"