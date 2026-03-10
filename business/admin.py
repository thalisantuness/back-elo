from django.contrib import admin
from business.models import Usuario, Regra, Produto, Foto, Campanha, Recompensa, Compra, QRCode, Conversa, Mensagem, \
    SolicitacaoRecompensa


# Admin para Usuários
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario_id', 'nome', 'email', 'role', 'status', 'pontos')
    list_filter = ('role', 'status', 'cidade')
    search_fields = ('nome', 'email', 'telefone')
    readonly_fields = ('data_cadastro', 'data_atualizacao')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'email', 'telefone', 'role', 'status')
        }),
        ('Endereço', {
            'fields': ('cidade', 'estado', 'cliente_endereco'),
            'classes': ('collapse',)
        }),
        ('Empresa', {
            'fields': ('cnpj', 'cdl', 'regra', 'modalidade_pontuacao'),
            'classes': ('collapse',)
        }),
        ('Pontuação', {
            'fields': ('pontos',)
        }),
        ('Datas', {
            'fields': ('data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


# Admin para Regras
@admin.register(Regra)
class RegraAdmin(admin.ModelAdmin):
    list_display = ('regra_id', 'nome', 'tipo', 'pontos', 'multiplicador', 'ativa')
    list_filter = ('tipo', 'ativa')
    search_fields = ('nome',)


# Admin para Produtos
@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('produto_id', 'nome', 'empresa', 'valor', 'quantidade', 'data_cadastro')
    list_filter = ('tipo_produto', 'tipo_comercializacao')
    search_fields = ('nome', 'empresa__nome')
    readonly_fields = ('data_cadastro', 'data_update')


# Admin para Fotos
@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ('photo_id', 'produto', 'data_cadastro')
    list_filter = ('produto',)


# Admin para Campanhas
@admin.register(Campanha)
class CampanhaAdmin(admin.ModelAdmin):
    list_display = ('campanha_id', 'titulo', 'empresa', 'ativa', 'data_inicio', 'data_fim')
    list_filter = ('ativa', 'data_inicio', 'data_fim')
    search_fields = ('titulo', 'empresa__nome')
    readonly_fields = ('data_cadastro', 'data_update')


# Admin para Recompensas
@admin.register(Recompensa)
class RecompensaAdmin(admin.ModelAdmin):
    list_display = ('recom_id', 'nome', 'usuario', 'pontos', 'estoque', 'data_cadastro')
    list_filter = ('usuario',)
    search_fields = ('nome', 'usuario__nome')
    readonly_fields = ('data_cadastro', 'data_update')


# Admin para Compras
@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('compra_id', 'qr_code_id', 'empresa', 'cliente', 'valor', 'pontos_adquiridos', 'status',
                    'data_cadastro')
    list_filter = ('status', 'data_cadastro')
    search_fields = ('qr_code_id', 'empresa__nome', 'cliente__nome')
    readonly_fields = ('data_cadastro', 'data_update')
    date_hierarchy = 'data_cadastro'


# Admin para QR Codes
@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ('qr_code_id', 'compra', 'empresa', 'status', 'expira_em')
    list_filter = ('status',)
    search_fields = ('qr_code_id', 'empresa__nome')
    readonly_fields = ('data_cadastro',)


# Admin para Conversas
@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ('conversa_id', 'usuario1', 'usuario2', 'ultima_mensagem')
    list_filter = ('usuario1', 'usuario2')
    search_fields = ('usuario1__nome', 'usuario2__nome')


# Admin para Mensagens
@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ('mensagem_id', 'conversa', 'remetente', 'data_envio', 'lida')
    list_filter = ('lida', 'data_envio')
    search_fields = ('conteudo', 'remetente__nome')
    readonly_fields = ('data_envio',)


# Admin para Solicitações de Recompensa
@admin.register(SolicitacaoRecompensa)
class SolicitacaoRecompensaAdmin(admin.ModelAdmin):
    list_display = ('solicitacao_id', 'usuario', 'recompensa', 'status', 'data_solicitacao', 'data_resposta')
    list_filter = ('status', 'data_solicitacao')
    search_fields = ('usuario__nome', 'recompensa__nome')
    readonly_fields = ('data_solicitacao', 'data_resposta')
    actions = ['aprovar_solicitacoes', 'rejeitar_solicitacoes']

    def aprovar_solicitacoes(self, request, queryset):
        from django.utils import timezone
        for solicitacao in queryset.filter(status='pendente'):
            if solicitacao.usuario.pontos >= solicitacao.recompensa.pontos and solicitacao.recompensa.estoque > 0:
                solicitacao.usuario.pontos -= solicitacao.recompensa.pontos
                solicitacao.usuario.save()
                solicitacao.recompensa.estoque -= 1
                solicitacao.recompensa.save()
                solicitacao.status = 'aceita'
                solicitacao.data_resposta = timezone.now()
                solicitacao.save()
        self.message_user(request, "Solicitações aprovadas com sucesso!")

    def rejeitar_solicitacoes(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status='pendente').update(status='rejeitada', data_resposta=timezone.now())
        self.message_user(request, "Solicitações rejeitadas com sucesso!")

    aprovar_solicitacoes.short_description = "Aprovar solicitações selecionadas"
    rejeitar_solicitacoes.short_description = "Rejeitar solicitações selecionadas"