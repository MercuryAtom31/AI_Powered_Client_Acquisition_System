import sys
import os
import argparse
from pathlib import Path
import logging
from typing import Dict, List
from datetime import datetime, timedelta, UTC
import json
from tabulate import tabulate
from collections import Counter

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from ai_client_acquisition.database.connection import get_db
from ai_client_acquisition.database.models import Company, ContactInfo, SEOAnalysis, OutreachHistory, OutreachStatus, PlatformType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_summary_stats(db_session) -> Dict:
    """
    Get summary statistics from the database.
    """
    total_companies = db_session.query(Company).count()
    total_contacts = db_session.query(ContactInfo).count()
    total_outreach = db_session.query(OutreachHistory).count()
    
    # Get platform distribution
    platform_counts = Counter(
        platform.value for platform in db_session.query(Company.platform_type).all()
    )
    
    # Get outreach status distribution
    status_counts = Counter(
        status.value for status in db_session.query(OutreachHistory.status).all()
    )
    
    # Get recent activity
    recent_outreach = db_session.query(OutreachHistory)\
        .filter(OutreachHistory.sent_date >= datetime.now(UTC) - timedelta(days=7))\
        .count()
    
    return {
        'total_companies': total_companies,
        'total_contacts': total_contacts,
        'total_outreach': total_outreach,
        'platform_distribution': dict(platform_counts),
        'outreach_status': dict(status_counts),
        'recent_outreach': recent_outreach
    }

def get_top_seo_issues(db_session, limit: int = 5) -> List[Dict]:
    """
    Get the most common SEO issues found.
    """
    issues = []
    
    # Get companies with missing meta descriptions
    missing_meta = db_session.query(Company)\
        .join(SEOAnalysis)\
        .filter(SEOAnalysis.meta_description == None)\
        .count()
    issues.append({'issue': 'Missing Meta Description', 'count': missing_meta})
    
    # Get companies with missing H1 tags
    missing_h1 = db_session.query(Company)\
        .join(SEOAnalysis)\
        .filter(SEOAnalysis.header_structure == None)\
        .count()
    issues.append({'issue': 'Missing H1 Tags', 'count': missing_h1})
    
    # Get companies with images missing alt text
    missing_alt = db_session.query(Company)\
        .join(SEOAnalysis)\
        .filter(SEOAnalysis.images_without_alt > 0)\
        .count()
    issues.append({'issue': 'Images Missing Alt Text', 'count': missing_alt})
    
    # Sort by count and get top issues
    issues.sort(key=lambda x: x['count'], reverse=True)
    return issues[:limit]

def get_recent_outreach(db_session, limit: int = 10) -> List[Dict]:
    """
    Get recent outreach activity.
    """
    recent = db_session.query(
        Company.website_url,
        ContactInfo.email,
        OutreachHistory.status,
        OutreachHistory.sent_date
    )\
    .join(ContactInfo)\
    .join(OutreachHistory)\
    .order_by(OutreachHistory.sent_date.desc())\
    .limit(limit)\
    .all()
    
    return [
        {
            'website': r.website_url,
            'email': r.email,
            'status': r.status.value,
            'sent_date': r.sent_date.isoformat()
        }
        for r in recent
    ]

def display_dashboard(stats: Dict, top_issues: List[Dict], recent_outreach: List[Dict]):
    """
    Display the dashboard in a formatted way.
    """
    print("\n=== Client Acquisition Dashboard ===\n")
    
    # Summary Statistics
    print("Summary Statistics:")
    summary_table = [
        ["Total Companies", stats['total_companies']],
        ["Total Contacts", stats['total_contacts']],
        ["Total Outreach", stats['total_outreach']],
        ["Recent Outreach (7 days)", stats['recent_outreach']]
    ]
    print(tabulate(summary_table, tablefmt="grid"))
    
    # Platform Distribution
    print("\nPlatform Distribution:")
    platform_table = [[k, v] for k, v in stats['platform_distribution'].items()]
    print(tabulate(platform_table, headers=["Platform", "Count"], tablefmt="grid"))
    
    # Outreach Status
    print("\nOutreach Status:")
    status_table = [[k, v] for k, v in stats['outreach_status'].items()]
    print(tabulate(status_table, headers=["Status", "Count"], tablefmt="grid"))
    
    # Top SEO Issues
    print("\nTop SEO Issues:")
    issues_table = [[i['issue'], i['count']] for i in top_issues]
    print(tabulate(issues_table, headers=["Issue", "Count"], tablefmt="grid"))
    
    # Recent Outreach
    print("\nRecent Outreach Activity:")
    outreach_table = [
        [r['website'], r['email'], r['status'], r['sent_date']]
        for r in recent_outreach
    ]
    print(tabulate(
        outreach_table,
        headers=["Website", "Email", "Status", "Sent Date"],
        tablefmt="grid"
    ))

def main():
    """
    Main function to run the dashboard.
    """
    parser = argparse.ArgumentParser(description='View client acquisition dashboard')
    parser.add_argument('--output', help='Save dashboard to JSON file')
    args = parser.parse_args()
    
    try:
        # Get database session
        db = next(get_db())
        
        # Get dashboard data
        stats = get_summary_stats(db)
        top_issues = get_top_seo_issues(db)
        recent_outreach = get_recent_outreach(db)
        
        # Display dashboard
        display_dashboard(stats, top_issues, recent_outreach)
        
        # Save to file if requested
        if args.output:
            data = {
                'stats': stats,
                'top_issues': top_issues,
                'recent_outreach': recent_outreach
            }
            with open(args.output, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Dashboard data saved to {args.output}")
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 