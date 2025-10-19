"""
Сервис для отправки email уведомлений
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime

from ...config.settings import settings
from ...infrastructure.logging.hybrid_logger import hybrid_logger


class EmailService:
    """Сервис для отправки email уведомлений"""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.is_configured = bool(self.smtp_host and self.smtp_user and self.smtp_password)
    
    async def send_password_reset_email(self, email: str, token: str) -> bool:
        """Отправка email для восстановления пароля"""
        if not self.is_configured:
            await self._log_simulation_email(email, token)
            return True
        
        try:
            reset_url = f"{settings.base_url}/admin/reset-password?token={token}"
            
            subject = "Восстановление пароля - AI RAG Bot"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #007bff;">Восстановление пароля</h2>
                    
                    <p>Вы запросили восстановление пароля для системы AI RAG Bot.</p>
                    
                    <p>Для сброса пароля нажмите на ссылку ниже:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" 
                           style="background-color: #007bff; color: white; padding: 12px 24px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Восстановить пароль
                        </a>
                    </div>
                    
                    <p><strong>Ссылка действительна в течение 1 часа.</strong></p>
                    
                    <p>Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.</p>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    
                    <p style="font-size: 12px; color: #666;">
                        Это автоматическое сообщение, пожалуйста, не отвечайте на него.
                    </p>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Восстановление пароля - AI RAG Bot
            
            Вы запросили восстановление пароля для системы AI RAG Bot.
            
            Для сброса пароля перейдите по ссылке:
            {reset_url}
            
            Ссылка действительна в течение 1 часа.
            
            Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.
            
            ---
            Это автоматическое сообщение, пожалуйста, не отвечайте на него.
            """
            
            return await self._send_email(email, subject, html_body, text_body)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка отправки email восстановления пароля: {e}")
            return False
    
    async def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Отправка email"""
        try:
            # Создаем сообщение
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            
            # Добавляем текстовую и HTML версии
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Отправляем email
            with smtplib.SMTP(self.smtp_host, 587) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            await hybrid_logger.info(f"Email успешно отправлен на {to_email}")
            return True
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка отправки email: {e}")
            return False
    
    async def _log_simulation_email(self, email: str, token: str) -> None:
        """Логирование симуляции email (когда SMTP не настроен)"""
        reset_url = f"{settings.base_url}/admin/reset-password?token={token}"
        
        await hybrid_logger.info(f"[EMAIL SIMULATION] Восстановление пароля для {email}")
        await hybrid_logger.info(f"[EMAIL SIMULATION] Ссылка: {reset_url}")
        await hybrid_logger.info(f"[EMAIL SIMULATION] Токен: {token}")
        await hybrid_logger.info(f"[EMAIL SIMULATION] SMTP не настроен - email не отправлен")


# Глобальный экземпляр сервиса
email_service = EmailService()
