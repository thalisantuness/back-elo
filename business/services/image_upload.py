import boto3
import uuid
from PIL import Image
import io
from django.conf import settings
import base64
import logging

logger = logging.getLogger(__name__)


class ImageUploadService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.AWS_BUCKET_NAME

    def validate_base64_image(self, base64_string):
        """Valida string base64 de imagem"""
        if not base64_string or not isinstance(base64_string, str):
            raise ValueError('String base64 inválida')
        if not base64_string.startswith('data:image/'):
            raise ValueError('String não é uma imagem base64 válida')

        parts = base64_string.split(',')
        if len(parts) != 2:
            raise ValueError('Formato base64 inválido')

        base64_data = parts[1]
        if not base64_data or len(base64_data) < 100:
            raise ValueError('Dados de imagem muito pequenos')

        return base64_data

    def compress_image(self, image_data, max_width=800, max_height=800, quality=80):
        """Comprime e redimensiona imagem"""
        try:
            # Decodificar base64
            image_bytes = base64.b64decode(image_data)

            # Abrir imagem com PIL
            img = Image.open(io.BytesIO(image_bytes))

            # Redimensionar mantendo proporção
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Converter para RGB se necessário
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img

            # Salvar em bytes com compressão
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Erro ao comprimir imagem: {str(e)}")
            raise ValueError(f"Erro ao processar imagem: {str(e)}")

    def upload_to_s3(self, file_bytes, folder):
        """Upload de bytes para S3"""
        key = f"{folder}/{uuid.uuid4()}.jpg"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_bytes,
                ContentType='image/jpeg',
                ACL='public-read'
            )

            url = f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
            return url
        except Exception as e:
            logger.error(f"Erro no upload para S3: {str(e)}")
            raise ValueError(f"Erro no upload da imagem: {str(e)}")

    def upload_base64_image(self, base64_image, folder, options=None):
        """Upload completo de imagem base64"""
        if not options:
            options = {'max_width': 800, 'max_height': 800, 'quality': 80}

        try:
            # Validar
            base64_data = self.validate_base64_image(base64_image)

            # Comprimir
            compressed = self.compress_image(
                base64_data,
                max_width=options.get('max_width', 800),
                max_height=options.get('max_height', 800),
                quality=options.get('quality', 80)
            )

            # Upload
            url = self.upload_to_s3(compressed, folder)
            return url
        except Exception as e:
            logger.error(f"Erro no upload da imagem: {str(e)}")
            raise

    def delete_from_s3(self, file_url):
        """Deleta arquivo do S3 pela URL"""
        if not file_url or self.bucket_name not in file_url:
            return

        try:
            key = file_url.split(f"{self.bucket_name}.s3.amazonaws.com/")[-1]
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
        except Exception as e:
            logger.error(f"Erro ao deletar do S3: {str(e)}")


# Instância singleton
image_upload_service = ImageUploadService()