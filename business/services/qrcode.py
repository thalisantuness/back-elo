import qrcode
import io
import base64
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class QRCodeService:
    def __init__(self):
        self.secret = settings.QR_CODE_SECRET

    def canonicalize(self, obj):
        """Ordena objeto para JSON determinístico"""
        return json.dumps(obj, sort_keys=True, separators=(',', ':'))

    def generate_signature(self, payload):
        """Gera assinatura HMAC do payload"""
        payload_str = self.canonicalize(payload)
        return hmac.new(
            self.secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

    def generate_qr_data(self, compra_id, empresa_id, valor, campanha_id=None):
        """Gera dados para o QR Code"""
        qr_code_id = hashlib.sha256(f"{compra_id}{datetime.now()}".encode()).hexdigest()[:32]

        payload = {
            'qr_code_id': qr_code_id,
            'compra_id': compra_id,
            'empresa_id': empresa_id,
            'valor': float(valor),
            'campanha_id': campanha_id,
            'timestamp': datetime.now().timestamp(),
            'expiresAt': (datetime.now() + timedelta(minutes=15)).timestamp()
        }

        signature = self.generate_signature(payload)
        payload['assinatura'] = signature

        return payload

    def generate_qr_code_image(self, qr_data):
        """Gera imagem QR Code a partir dos dados"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Converter para base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.error(f"Erro ao gerar QR Code: {str(e)}")
            raise ValueError(f"Erro ao gerar QR Code: {str(e)}")

    def validate_qr_data(self, qr_code_data):
        """Valida dados do QR Code"""
        try:
            if isinstance(qr_code_data, str):
                dados = json.loads(qr_code_data)
            else:
                dados = qr_code_data

            # Alguns clientes podem enviar o objeto inteiro da resposta de /qr-code
            if isinstance(dados, dict) and 'qr_code_data' in dados and isinstance(dados.get('qr_code_data'), dict):
                dados = dados['qr_code_data']

            assinatura = dados.pop('assinatura', None)
            if not assinatura:
                return {'valid': False, 'error': 'Assinatura não encontrada'}

            # Normalizar tipos para evitar mismatch de assinatura entre clientes
            # (ex.: 22 vs 22.0, timestamps como string).
            for numeric_key in ('valor', 'timestamp', 'expiresAt'):
                if numeric_key in dados and dados[numeric_key] is not None:
                    try:
                        dados[numeric_key] = float(dados[numeric_key])
                    except (ValueError, TypeError):
                        return {'valid': False, 'error': f'Campo numérico inválido: {numeric_key}'}

            for int_key in ('empresa_id', 'compra_id', 'campanha_id'):
                if int_key in dados and dados[int_key] is not None:
                    try:
                        dados[int_key] = int(dados[int_key])
                    except (ValueError, TypeError):
                        return {'valid': False, 'error': f'Campo inteiro inválido: {int_key}'}

            assinatura_esperada = self.generate_signature(dados)

            if assinatura != assinatura_esperada:
                return {'valid': False, 'error': 'Assinatura inválida'}

            if datetime.now().timestamp() > dados.get('expiresAt', 0):
                return {'valid': False, 'error': 'QR Code expirado'}

            dados['assinatura'] = assinatura
            return {'valid': True, **dados}
        except Exception as e:
            logger.error(f"Erro ao validar QR Code: {str(e)}")
            return {'valid': False, 'error': str(e)}


# Instância singleton
qr_code_service = QRCodeService()