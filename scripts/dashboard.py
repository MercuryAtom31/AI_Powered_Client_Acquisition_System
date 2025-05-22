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
    platform_counts = Counter()
    try:
        for platform in db_session.query(Company.platform_type).all():
            if hasattr(platform, 'value'):
                platform_counts[platform.value] += 1
            elif isinstance(platform, tuple) and hasattr(platform[0], 'value'):
                platform_counts[platform[0].value] += 1
            else:
                platform_counts[str(platform)] += 1
    except Exception as e:
        logger.error(f"Error processing platform distribution: {str(e)}")
    
    # Get outreach status distribution
    status_counts = Counter()
    try:
        for status in db_session.query(OutreachHistory.status).all():
            if hasattr(status, 'value'):
                status_counts[status.value] += 1
            elif isinstance(status, tuple) and hasattr(status[0], 'value'):
                status_counts[status[0].value] += 1
            else:
                status_counts[str(status)] += 1
    except Exception as e:
        logger.error(f"Error processing outreach status distribution: {str(e)}")
    
    # Get recent activity
    try:
        recent_outreach = db_session.query(OutreachHistory)\
            .filter(OutreachHistory.sent_date >= datetime.now(UTC) - timedelta(days=7))\
            .count()
    except Exception as e:
        logger.error(f"Error processing recent outreach: {str(e)}")
        recent_outreach = 0
    
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
    try:
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
    except Exception as e:
        logger.error(f"Error processing SEO issues: {str(e)}")
    return issues[:limit]

def get_recent_outreach(db_session, limit: int = 10) -> List[Dict]:
    """
    Get recent outreach activity.
    """
    try:
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
        result = []
        for r in recent:
            try:
                status_value = r.status.value if hasattr(r.status, 'value') else str(r.status)
                sent_date_str = r.sent_date.isoformat() if hasattr(r.sent_date, 'isoformat') else str(r.sent_date)
                result.append({
                    'website': r.website_url,
                    'email': r.email,
                    'status': status_value,
                    'sent_date': sent_date_str
                })
            except Exception as e:
                logger.error(f"Error processing recent outreach row: {str(e)}")
        return result
    except Exception as e:
        logger.error(f"Error processing recent outreach: {str(e)}")
        return []

def display_dashboard(stats: Dict, top_issues: List[Dict], recent_outreach: List[Dict]):
    """
    Display the dashboard in a formatted way.
    """
    print("\n=== Client Acquisition Dashboard ===\n")
    
    # Summary Statistics
    print("Summary Statistics:")
    summary_table = [
        ["Total Companies", stats.get('total_companies', 0)],
        ["Total Contacts", stats.get('total_contacts', 0)],
        ["Total Outreach", stats.get('total_outreach', 0)],
        ["Recent Outreach (7 days)", stats.get('recent_outreach', 0)]
    ]
    print(tabulate(summary_table, tablefmt="grid"))
    
    # Platform Distribution
    print("\nPlatform Distribution:")
    platform_dist = stats.get('platform_distribution', {})
    if platform_dist:
        platform_table = [[k, v] for k, v in platform_dist.items()]
        print(tabulate(platform_table, headers=["Platform", "Count"], tablefmt="grid"))
    else:
        print("No platform data available.")
    
    # Outreach Status
    print("\nOutreach Status:")
    outreach_status = stats.get('outreach_status', {})
    if outreach_status:
        status_table = [[k, v] for k, v in outreach_status.items()]
        print(tabulate(status_table, headers=["Status", "Count"], tablefmt="grid"))
    else:
        print("No outreach status data available.")
    
    # Top SEO Issues
    print("\nTop SEO Issues:")
    if top_issues:
        issues_table = [[i['issue'], i['count']] for i in top_issues]
        print(tabulate(issues_table, headers=["Issue", "Count"], tablefmt="grid"))
    else:
        print("No SEO issues data available.")
    
    # Recent Outreach
    print("\nRecent Outreach Activity:")
    if recent_outreach:
        outreach_table = [
            [r['website'], r['email'], r['status'], r['sent_date']]
            for r in recent_outreach
        ]
        print(tabulate(
            outreach_table,
            headers=["Website", "Email", "Status", "Sent Date"],
            tablefmt="grid"
        ))
    else:
        print("No recent outreach activity available.")

def get_stats_from_analysis_file(file_path: str = 'analysis_results.json') -> Dict:
    """
    Get statistics from the analysis results file.
    """
    try:
        with open(file_path, 'r') as f:
            results = json.load(f)
        
        # Count total companies
        total_companies = len(results)
        
        # Count total contacts
        total_contacts = sum(
            len(r.get('contact_info', {}).get('emails', []))
            for r in results
        )
        
        # Get platform distribution
        platform_counts = Counter(
            r.get('platform_type', 'unknown')
            for r in results
        )
        
        # Get SEO issues
        issues = []
        missing_meta = sum(
            1 for r in results
            if not r.get('seo_analysis', {}).get('meta_description', {}).get('text')
        )
        issues.append({'issue': 'Missing Meta Description', 'count': missing_meta})
        
        missing_h1 = sum(
            1 for r in results
            if not r.get('seo_analysis', {}).get('headers', {}).get('has_h1')
        )
        issues.append({'issue': 'Missing H1 Tags', 'count': missing_h1})
        
        missing_alt = sum(
            r.get('seo_analysis', {}).get('images', {}).get('images_without_alt', 0)
            for r in results
        )
        issues.append({'issue': 'Images Missing Alt Text', 'count': missing_alt})
        
        return {
            'total_companies': total_companies,
            'total_contacts': total_contacts,
            'total_outreach': 0,
            'platform_distribution': dict(platform_counts),
            'outreach_status': {},
            'recent_outreach': 0,
            'top_issues': issues
        }
    except Exception as e:
        logger.error(f"Error reading analysis file: {str(e)}")
        return {
            'total_companies': 0,
            'total_contacts': 0,
            'total_outreach': 0,
            'platform_distribution': {},
            'outreach_status': {},
            'recent_outreach': 0,
            'top_issues': []
        }

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
        
        # If database is empty, try to read from analysis file
        if stats['total_companies'] == 0:
            logger.info("Database is empty, reading from analysis results file...")
            file_stats = get_stats_from_analysis_file()
            stats.update(file_stats)
            top_issues = file_stats.get('top_issues', [])
            recent_outreach = []
        else:
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