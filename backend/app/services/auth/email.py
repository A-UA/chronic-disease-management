"""邮件发送服务

支持 SMTP 发送密码重置验证码等邮件。
配置为空时仅记录日志，不实际发送（开发环境兼容）。
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.base.config import settings

logger = logging.getLogger(__name__)


async def send_reset_code_email(to_email: str, code: str) -> bool:
    """发送密码重置验证码邮件

    返回 True 表示发送成功（或 SMTP 未配置时日志记录成功）
    """
    if not settings.SMTP_HOST:
        logger.info(
            f"[SMTP 未配置] 密码重置验证码 → {to_email}: {code}（15 分钟有效）"
        )
        return True

    subject = f"【{settings.PROJECT_NAME}】密码重置验证码"
    html_body = f"""
    <div style="font-family: 'Microsoft YaHei', sans-serif; max-width: 480px; margin: 0 auto;
                padding: 32px; background: #f8f9fa; border-radius: 12px;">
        <h2 style="color: #667eea; margin-bottom: 24px;">密码重置验证码</h2>
        <p>您好，您的密码重置验证码为：</p>
        <div style="background: #667eea; color: #fff; font-size: 28px; font-weight: bold;
                    letter-spacing: 8px; text-align: center; padding: 16px; border-radius: 8px;
                    margin: 16px 0;">
            {code}
        </div>
        <p style="color: #666; font-size: 14px;">
            验证码 <strong>15 分钟</strong> 内有效，请勿将此验证码告知他人。
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 24px;">
            如非本人操作，请忽略此邮件。
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.SMTP_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.sendmail(msg["From"], [to_email], msg.as_string())
        server.quit()
        logger.info(f"密码重置邮件已发送至 {to_email}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {to_email} → {e}")
        return False
