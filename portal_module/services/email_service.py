"""
Email service for sending temporary passwords
"""

import smtplib
import subprocess
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', '').strip()
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '').strip()
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '').strip()
        self.smtp_tls = os.environ.get('SMTP_TLS', 'true').lower() == 'true'
        self.from_email = os.environ.get('FROM_EMAIL', 'noreply@waddlebot.com')
        self.from_name = os.environ.get('FROM_NAME', 'WaddleBot Community Portal')
        
        # Determine if we should use SMTP or sendmail
        self.use_smtp = bool(self.smtp_host)
    
    def _send_via_smtp(self, msg: MIMEMultipart) -> Dict[str, Any]:
        """Send email via SMTP"""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
                
            return {"success": True, "message": "Email sent via SMTP"}
            
        except Exception as e:
            logger.error(f"SMTP send failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _send_via_sendmail(self, msg: MIMEMultipart) -> Dict[str, Any]:
        """Send email via sendmail"""
        try:
            # Use sendmail command
            sendmail_cmd = ["/usr/sbin/sendmail", "-t", "-i"]
            
            process = subprocess.Popen(
                sendmail_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(msg.as_string())
            
            if process.returncode == 0:
                return {"success": True, "message": "Email sent via sendmail"}
            else:
                logger.error(f"Sendmail failed: {stderr}")
                return {"success": False, "error": f"Sendmail failed: {stderr}"}
                
        except Exception as e:
            logger.error(f"Sendmail send failed: {str(e)}")
            return {"success": False, "error": str(e)}
        
    def send_temp_password(self, email: str, user_id: str, display_name: str, 
                          temp_password: str, expires_at: str) -> Dict[str, Any]:
        """Send temporary password email"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = email
            msg['Subject'] = "WaddleBot Community Portal - Temporary Password"
            
            # Email body
            body = f"""
Hello {display_name},

You have requested access to the WaddleBot Community Portal. Here are your login details:

User ID: {user_id}
Temporary Password: {temp_password}

This temporary password will expire in 24 hours.

You can access the portal at: {os.environ.get('PORTAL_URL', 'http://localhost:8000')}

If you did not request this access, please ignore this email.

Best regards,
The WaddleBot Team
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            if self.use_smtp:
                result = self._send_via_smtp(msg)
                if result['success']:
                    logger.info(f"Temporary password email sent to {email} via SMTP")
                return result
            else:
                result = self._send_via_sendmail(msg)
                if result['success']:
                    logger.info(f"Temporary password email sent to {email} via sendmail")
                return result
                
        except Exception as e:
            logger.error(f"Error sending temp password email: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_welcome_email(self, email: str, user_id: str, display_name: str, 
                          community_name: str) -> Dict[str, Any]:
        """Send welcome email for new portal users"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = email
            msg['Subject'] = f"Welcome to {community_name} Community Portal"
            
            # Email body
            body = f"""
Hello {display_name},

Welcome to the WaddleBot Community Portal for {community_name}!

Your portal access has been set up with User ID: {user_id}

You can access the portal at: {os.environ.get('PORTAL_URL', 'http://localhost:8000')}

As a community owner, you can:
- View and manage community members
- Monitor user roles and reputation
- Manage installed modules
- View community statistics

If you have any questions, please contact the community administrators.

Best regards,
The WaddleBot Team
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            if self.use_smtp:
                result = self._send_via_smtp(msg)
                if result['success']:
                    logger.info(f"Welcome email sent to {email} via SMTP")
                return result
            else:
                result = self._send_via_sendmail(msg)
                if result['success']:
                    logger.info(f"Welcome email sent to {email} via sendmail")
                return result
                
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return {"success": False, "error": str(e)}