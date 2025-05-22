import sys
import os
import argparse
from pathlib import Path
import logging
from typing import List, Dict
import json
from datetime import datetime

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from ai_client_acquisition.database.connection import get_db
from ai_client_acquisition.database.models import Company, ContactInfo, SEOAnalysis, OutreachHistory, OutreachStatus
from ai_client_acquisition.personalization.email_generator import EmailGenerator
from ai_client_acquisition.outreach.email_sender import EmailSender

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_companies_to_contact(db_session, limit: int = 10) -> List[Company]:
    """
    Get companies that haven't been contacted yet.
    """
    return db_session.query(Company)\
        .outerjoin(OutreachHistory)\
        .filter(OutreachHistory.id == None)\
        .limit(limit)\
        .all()

def generate_and_send_emails(companies: List[Company], db_session) -> List[Dict]:
    """
    Generate and send personalized emails to companies.
    """
    email_generator = EmailGenerator()
    email_sender = EmailSender()
    results = []
    
    for company in companies:
        try:
            # Get company data
            contact_info = db_session.query(ContactInfo).filter_by(company_id=company.id).first()
            seo_analysis = db_session.query(SEOAnalysis).filter_by(company_id=company.id).first()
            
            if not contact_info or not contact_info.email:
                logger.warning(f"No contact email found for company {company.id}")
                continue
            
            # Generate email
            company_data = {
                'company_name': company.company_name,
                'website_url': company.website_url,
                'platform_type': company.platform_type.value
            }
            
            email_content = email_generator.generate_pitch(company_data, seo_analysis.__dict__)
            
            # Send email
            send_result = email_sender.send_email(
                to_email=contact_info.email,
                subject=email_content['subject'],
                content=email_content['body'],
                company_id=company.id
            )
            
            # Record outreach
            outreach = OutreachHistory(
                company_id=company.id,
                status=OutreachStatus.PITCHED,
                email_content=email_content['body'],
                sent_date=datetime.utcnow()
            )
            db_session.add(outreach)
            db_session.commit()
            
            results.append({
                'company_id': company.id,
                'email': contact_info.email,
                'send_result': send_result
            })
            
        except Exception as e:
            logger.error(f"Error processing company {company.id}: {str(e)}")
            results.append({
                'company_id': company.id,
                'error': str(e)
            })
    
    return results

def main():
    """
    Main function to run the outreach process.
    """
    parser = argparse.ArgumentParser(description='Run outreach campaign')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of companies to contact')
    parser.add_argument('--output', default='outreach_results.json', help='Output file for results')
    args = parser.parse_args()
    
    try:
        # Get database session
        db = next(get_db())
        
        # Get companies to contact
        companies = get_companies_to_contact(db, args.limit)
        logger.info(f"Found {len(companies)} companies to contact")
        
        # Generate and send emails
        results = generate_and_send_emails(companies, db)
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
        
        # Print summary
        successful = sum(1 for r in results if r.get('send_result', {}).get('status') == 'success')
        logger.info(f"Successfully sent {successful} out of {len(results)} emails")
        
    except Exception as e:
        logger.error(f"Error in outreach process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 