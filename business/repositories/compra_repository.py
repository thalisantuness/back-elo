from django.db import transaction, models
from django.db.models import Q, Count, Sum, Avg
from datetime import datetime, timedelta
from business.models import Compra, Usuario, SolicitacaoRecompensa, Recompensa
from .base_repository import BaseRepository
from django.utils import timezone
from business.services.qrcode import qr_code_service


class CompraRepository(BaseRepository):
    def __init__(self):
        super().__init__(Compra)

    def get_compras_with_relations(self, filters=None):
        """Lista compras com todas as relações"""
        queryset = Compra.objects.select_related(
            'cliente', 'empresa', 'campanha'
        ).order_by('-data_cadastro')

        if filters:
            queryset = queryset.filter(**filters)

        return queryset

    def get_by_empresa(self, empresa_id, status=None):
        """Lista compras de uma empresa"""
        filters = {'empresa_id': empresa_id}
        if status:
            filters['status'] = status

        return Compra.objects.filter(**filters).select_related(
            'cliente', 'campanha'
        ).order_by('-data_cadastro')

    def get_by_cliente(self, cliente_id):
        """Lista compras de um cliente"""
        return Compra.objects.filter(
            cliente_id=cliente_id
        ).select_related(
            'empresa', 'campanha'
        ).order_by('-data_cadastro')

    @transaction.atomic
    def criar_compra_pendente(self, empresa_id, valor, campanha_id=None):



        empresa = Usuario.objects.filter(
            usuario_id=empresa_id,
        role__in=['empresa', 'cdl', 'admin'],
        status='ativo'
        ).first()

        if not empresa:
            raise ValueError('Empresa não encontrada ou inativa')

        pontos = int(float(valor))

        qr_data = qr_code_service.generate_qr_data(
            compra_id=None,
            empresa_id=empresa_id,
            valor=valor,
            campanha_id=campanha_id
        )

        compra = Compra.objects.create(
            empresa_id=empresa_id,
            valor=valor,
            pontos_adquiridos=pontos,
            campanha_id=campanha_id,
            status='pendente',
            qr_code_id=qr_data['qr_code_id'],
            qr_code_data=qr_data,
            qr_code_expira_em=timezone.make_aware(datetime.fromtimestamp(qr_data['expiresAt']))
        )
        return compra

    @transaction.atomic
    def claim_compra(self, qr_code_data, cliente_id):
        """Cliente claim compra e ganha pontos"""
        # Validar QR Code
        validacao = qr_code_service.validate_qr_data(qr_code_data)
        if not validacao.get('valid'):
            raise ValueError(validacao.get('error', 'QR Code inválido'))

        qr_code_id = validacao.get('qr_code_id')

        # Buscar compra
        compra = Compra.objects.filter(
            qr_code_id=qr_code_id,
            status='pendente',
            cliente__isnull=True
        ).first()

        if not compra:
            raise ValueError('Compra não encontrada ou já processada')

        # Verificar valor
        if float(compra.valor) != float(validacao.get('valor')):
            raise ValueError('Valor da compra não corresponde')

        # Verificar cliente
        cliente = Usuario.objects.filter(
            usuario_id=cliente_id,
            role='cliente',
            status='ativo'
        ).first()

        if not cliente:
            raise ValueError('Cliente inválido')

        # Processar claim
        compra.cliente = cliente
        compra.status = 'validada'
        compra.validado_em = timezone.now()
        compra.validado_por = cliente
        compra.save()

        # Adicionar pontos
        cliente.pontos += compra.pontos_adquiridos
        cliente.save()

        return {
            'compra_id': compra.compra_id,
            'valor': compra.valor,
            'pontos_adquiridos': compra.pontos_adquiridos,
            'cliente_novo_saldo': cliente.pontos
        }

    def estatisticas_empresa(self, empresa_id):
        """Estatísticas para empresa"""
        compras_validas = Compra.objects.filter(
            empresa_id=empresa_id,
            status='validada'
        )

        stats = compras_validas.aggregate(
            total_compras=Count('compra_id'),
            total_vendido=Sum('valor'),
            total_pontos=Sum('pontos_adquiridos')
        )

        clientes_unicos = compras_validas.values('cliente_id').distinct().count()

        # Compras por mês
        from django.db.models.functions import TruncMonth
        compras_mes = compras_validas.annotate(
            mes=TruncMonth('data_cadastro')
        ).values('mes').annotate(
            total=Count('compra_id'),
            valor=Sum('valor')
        ).order_by('-mes')[:6]

        return {
            'total_compras': stats['total_compras'] or 0,
            'total_vendido': float(stats['total_vendido'] or 0),
            'total_pontos_distribuidos': stats['total_pontos'] or 0,
            'clientes_unicos': clientes_unicos,
            'compras_por_mes': [
                {
                    'mes': item['mes'].strftime('%Y-%m') if item['mes'] else None,
                    'total_compras': item['total'],
                    'total_vendido': float(item['valor'] or 0)
                }
                for item in compras_mes
            ]
        }

    def big_numbers(self, role, user_id):
        """Big numbers dashboard"""
        from django.db import connection

        # Determinar escopo
        empresa_ids = None
        cdl_id = None

        if role == 'cdl':
            cdl_id = user_id
            empresas = Usuario.objects.filter(
                role='empresa',
                cdl_id=user_id
            ).values_list('usuario_id', flat=True)
            empresa_ids = list(empresas)
        elif role == 'empresa':
            empresa_ids = [user_id]

        # Construir condições
        compra_validada_where = Q(status='validada')
        if empresa_ids is not None:
            compra_validada_where &= Q(empresa_id__in=empresa_ids if empresa_ids else [-1])
        elif role == 'cliente':
            compra_validada_where &= Q(cliente_id=user_id)

        # Queries
        compras = Compra.objects.filter(compra_validada_where)

        agregados = compras.aggregate(
            valor_escaneadas=Sum('valor'),
            pontos_gerados=Sum('pontos_adquiridos')
        )

        # Total de compras para ticket médio
        total_compras = compras.count()

        # Pontos usados
        solicitacao_where = Q(status='aceita')
        recompensa_where = Q()

        if role in ['empresa', 'cdl'] and empresa_ids:
            recompensa_where = Q(recompensa__usuario_id__in=empresa_ids)
            pontos_usados = SolicitacaoRecompensa.objects.filter(
                solicitacao_where & recompensa_where
            ).aggregate(
                total=Sum('recompensa__pontos')
            )['total'] or 0
        elif role == 'cliente':
            pontos_usados = SolicitacaoRecompensa.objects.filter(
                solicitacao_where & Q(usuario_id=user_id)
            ).aggregate(
                total=Sum('recompensa__pontos')
            )['total'] or 0
        else:
            pontos_usados = 0

        # Empresas ativas na semana
        sete_dias_atras = timezone.now() - timedelta(days=7)
        empresas_ativas = Compra.objects.filter(
            compra_validada_where & Q(validado_em__gte=sete_dias_atras)
        ).values('empresa_id').distinct().count()

        # Total empresas no escopo
        total_empresas = len(empresa_ids) if empresa_ids else 0

        # Clientes cadastrados
        clientes_cadastrados = None
        if role == 'cdl':
            clientes_cadastrados = Usuario.objects.filter(
                role='cliente',
                cdl_id=user_id
            ).count()

        # Ticket médio
        ticket_medio = (float(agregados['valor_escaneadas'] or 0) / total_compras) if total_compras > 0 else 0

        return {
            'valor_em_compras_criadas': float(agregados['valor_escaneadas'] or 0),
            'valor_em_pontos_gerados': agregados['pontos_gerados'] or 0,
            'valor_em_pontos_usados': pontos_usados,
            'taxa_atividade_associados': round((empresas_ativas / total_empresas * 100),
                                               1) if total_empresas > 0 else 0,
            'clientes_cadastrados': clientes_cadastrados,
            'empresas_cadastradas': total_empresas,
            'ticket_medio': round(ticket_medio, 2)
        }