from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.db.models import Q
from datetime import datetime, timedelta
import logging

from business.models import Compra
from business.repositories import compra_repo, usuario_repo
from business.serializers import CompraSerializer
from business.services.qrcode import qr_code_service
from .base_view import BaseView

logger = logging.getLogger(__name__)


class CompraViewSet(ViewSet, BaseView):

    def list(self, request):
        """Listar compras baseado na role"""
        try:
            user = request.user

            if user.role == 'admin':
                compras = compra_repo.get_compras_with_relations()

            elif user.role in ['empresa', 'cdl']:
                compras = compra_repo.get_by_empresa(user.usuario_id)

            elif user.role == 'cliente':
                compras = compra_repo.get_by_cliente(user.usuario_id)

            else:
                return Response([])

            serializer = CompraSerializer(compras, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao listar compras: {str(e)}")
            return self.error_response("Erro ao listar compras")

    def retrieve(self, request, pk=None):
        """Buscar compra por ID"""
        try:
            compra = compra_repo.get_by_id(pk)
            if not compra:
                return self.not_found_response("Compra não encontrada")

            # Verificar permissão
            user = request.user
            if user.role == 'cliente' and compra.cliente_id != user.usuario_id:
                return self.forbidden_response()

            if user.role in ['empresa', 'cdl'] and compra.empresa_id != user.usuario_id:
                return self.forbidden_response()

            serializer = CompraSerializer(compra)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro ao buscar compra: {str(e)}")
            return self.error_response("Erro ao buscar compra")

    @action(detail=False, methods=['post'], url_path='gerar-qrcode')
    def gerar_qrcode(self, request):
        """Gerar QR Code para nova compra"""
        try:
            # Verificar permissão
            if request.user.role not in ['admin', 'cdl', 'empresa']:
                return self.forbidden_response("Apenas administradores, CDLs e empresas podem gerar QR codes")

            valor = request.data.get('valor')
            campanha_id = request.data.get('campanha_id')

            if not valor or float(valor) <= 0:
                return self.error_response("Valor da compra é obrigatório e deve ser positivo")

            # Criar compra pendente
            compra = compra_repo.criar_compra_pendente(
                empresa_id=request.user.usuario_id,
                valor=float(valor),
                campanha_id=campanha_id
            )

            # Gerar imagem do QR Code
            qr_data = qr_code_service.generate_qr_data(
                compra_id=compra.compra_id,
                empresa_id=request.user.usuario_id,
                valor=float(valor),
                campanha_id=campanha_id
            )

            qr_image = qr_code_service.generate_qr_code_image(qr_data)

            return Response({
                'message': 'QR code gerado com sucesso',
                'compra_id': compra.compra_id,
                'qr_code_base64': qr_image,
                'qr_code_data': compra.qr_code_data,
                'expira_em': compra.qr_code_expira_em,
                'valor': compra.valor,
                'pontos_estimados': compra.pontos_adquiridos
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao gerar QR Code: {str(e)}")
            return self.error_response("Erro ao gerar QR Code")

    @action(detail=False, methods=['post'], url_path='claim')
    def claim_compra(self, request):
        """Cliente claim compra"""
        try:
            if request.user.role != 'cliente':
                return self.forbidden_response("Apenas clientes podem claimar compras")

            qr_code_data = request.data.get('qr_code_data')
            if not qr_code_data:
                return self.error_response("Dados do QR code são obrigatórios")

            resultado = compra_repo.claim_compra(qr_code_data, request.user.usuario_id)

            return Response({
                'success': True,
                'message': 'Compra claimada com sucesso! Pontos adicionados.',
                'compra': resultado
            })

        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            logger.error(f"Erro ao claimar compra: {str(e)}")
            return self.error_response("Erro ao processar compra")

    @action(detail=False, methods=['get'], url_path='estatisticas')
    def estatisticas(self, request):
        """Estatísticas para empresa"""
        try:
            if request.user.role not in ['empresa', 'cdl', 'admin']:
                return self.forbidden_response()

            empresa_id = request.query_params.get('empresa_id', request.user.usuario_id)

            stats = compra_repo.estatisticas_empresa(empresa_id)
            return Response(stats)

        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {str(e)}")
            return self.error_response("Erro ao buscar estatísticas")

    @action(detail=False, methods=['get'], url_path='big-numbers')
    def big_numbers(self, request):
        """Big numbers dashboard"""
        try:
            dados = compra_repo.big_numbers(
                role=request.user.role,
                user_id=request.user.usuario_id
            )
            return Response(dados)

        except Exception as e:
            logger.error(f"Erro ao buscar big numbers: {str(e)}")
            return self.error_response("Erro ao buscar dados")

    @action(detail=False, methods=['get'], url_path='graficos-cdl')
    def graficos_cdl(self, request):
        """Gráficos para CDL"""
        try:
            if request.user.role not in ['cdl', 'admin']:
                return self.forbidden_response()

            cdl_id = request.query_params.get('cdl_id', request.user.usuario_id)

            # Buscar empresas da CDL
            empresas = usuario_repo.get_lojas_por_cdl(cdl_id)
            empresa_ids = [e.usuario_id for e in empresas]
            empresa_ids.append(int(cdl_id))

            # Compras por mês
            from django.db.models.functions import TruncMonth
            from django.db.models import Count, Sum

            compras_mes = Compra.objects.filter(
                empresa_id__in=empresa_ids,
                data_cadastro__gte=datetime.now() - timedelta(days=365)
            ).annotate(
                mes=TruncMonth('data_cadastro')
            ).values('mes').annotate(
                criadas=Count('compra_id'),
                escaneadas=Count('compra_id', filter=Q(status='validada')),
                valor=Sum('valor', filter=Q(status='validada'))
            ).order_by('-mes')[:12]

            # Lojas mais ativas
            lojas_ativas = Compra.objects.filter(
                empresa_id__in=empresa_ids,
                status='validada'
            ).values(
                'empresa__nome'
            ).annotate(
                volume=Sum('valor')
            ).order_by('-volume')[:5]

            return Response({
                'cdl_id': cdl_id,
                'compras_por_mes': [
                    {
                        'mes': item['mes'].strftime('%Y-%m') if item['mes'] else None,
                        'criadas': item['criadas'],
                        'escaneadas': item['escaneadas'],
                        'valor': float(item['valor'] or 0)
                    }
                    for item in compras_mes
                ],
                'lojas_mais_ativas': [
                    {
                        'nome': item['empresa__nome'],
                        'volume': float(item['volume'] or 0)
                    }
                    for item in lojas_ativas
                ]
            })

        except Exception as e:
            logger.error(f"Erro ao gerar gráficos: {str(e)}")
            return self.error_response("Erro ao gerar gráficos")