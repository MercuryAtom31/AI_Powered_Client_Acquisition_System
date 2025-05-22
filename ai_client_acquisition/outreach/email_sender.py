from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Dict, List, Optional
import logging
import os
from dotenv import load_dotenv
from datetime import datetime
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_name = os.getenv('SENDER_NAME', 'Digital Marketing Expert')
        self.daily_limit = int(os.getenv('DAILY_EMAIL_LIMIT', '100'))
        self.emails_sent_today = 0
        self.last_reset_date = datetime.now().date()
        self.rate_limit_delay = int(os.getenv('RATE_LIMIT_DELAY', '2'))  # seconds between emails

    def send_email(self, to_email: str, subject: str, content: str, company_id: int) -> Dict:
        """
        Send an email using SendGrid.
        """
        try:
            # Check daily limit
            self._check_daily_limit()
            
            # Create email
            message = Mail(
                from_email=Email(self.sender_email, self.sender_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", content)
            )
            
            # Add custom headers for tracking
            message.add_header("X-Company-ID", str(company_id))
            message.add_header("X-Campaign-ID", "seo_outreach")
            
            # Send email
            response = self.sg.send(message)
            
            # Update tracking
            self.emails_sent_today += 1
            
            # Add delay to respect rate limits
            time.sleep(self.rate_limit_delay)
            
            return {
                'status': 'success',
                'message_id': response.headers.get('X-Message-Id'),
                'status_code': response.status_code
            }
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def send_bulk_emails(self, emails: List[Dict]) -> List[Dict]:
        """
        Send multiple emails with rate limiting and tracking.
        """
        results = []
        
        for email_data in emails:
            # Check if we've hit the daily limit
            if self.emails_sent_today >= self.daily_limit:
                logger.warning("Daily email limit reached")
                break
            
            result = self.send_email(
                to_email=email_data['to_email'],
                subject=email_data['subject'],
                content=email_data['content'],
                company_id=email_data['company_id']
            )
            
            results.append({
                'to_email': email_data['to_email'],
                'company_id': email_data['company_id'],
                'result': result
            })
        
        return results

    def _check_daily_limit(self) -> None:
        """
        Check and reset daily email limit if needed.
        """
        current_date = datetime.now().date()
        
        # Reset counter if it's a new day
        if current_date > self.last_reset_date:
            self.emails_sent_today = 0
            self.last_reset_date = current_date
        
        # Check if we've hit the limit
        if self.emails_sent_today >= self.daily_limit:
            raise Exception("Daily email limit reached")

    def get_sending_stats(self) -> Dict:
        """
        Get current email sending statistics.
        """
        return {
            'emails_sent_today': self.emails_sent_today,
            'daily_limit': self.daily_limit,
            'remaining_today': self.daily_limit - self.emails_sent_today,
            'last_reset_date': self.last_reset_date.isoformat()
        }

    def update_daily_limit(self, new_limit: int) -> None:
        """
        Update the daily email sending limit.
        """
        if new_limit < 0:
            raise ValueError("Daily limit cannot be negative")
        
        self.daily_limit = new_limit
        logger.info(f"Daily email limit updated to {new_limit}")

    def update_rate_limit_delay(self, new_delay: int) -> None:
        """
        Update the delay between emails.
        """
        if new_delay < 0:
            raise ValueError("Rate limit delay cannot be negative")
        
        self.rate_limit_delay = new_delay
        logger.info(f"Rate limit delay updated to {new_delay} seconds") 