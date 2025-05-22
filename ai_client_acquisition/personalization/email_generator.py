import openai
from typing import Dict, List, Optional
import logging
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailGenerator:
    def __init__(self):
        self.system_prompt = """You are an expert sales professional specializing in digital marketing and SEO services. 
        Your task is to write personalized, compelling email pitches that highlight specific opportunities for improvement 
        based on the target company's website analysis. Focus on being professional, specific, and value-driven."""

    def generate_pitch(self, company_data: Dict, seo_analysis: Dict) -> Dict:
        """
        Generate a personalized email pitch based on company data and SEO analysis.
        """
        try:
            # Prepare the prompt with company-specific information
            prompt = self._prepare_prompt(company_data, seo_analysis)
            
            # Generate the email using OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",  # or "gpt-3.5-turbo" for a more cost-effective option
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract the generated email
            email_content = response.choices[0].message.content
            
            return {
                'subject': self._generate_subject(company_data, seo_analysis),
                'body': email_content,
                'personalization_points': self._extract_personalization_points(email_content)
            }
            
        except Exception as e:
            logger.error(f"Error generating email pitch: {str(e)}")
            return {
                'subject': "Error generating email",
                'body': "There was an error generating the personalized email. Please try again.",
                'personalization_points': []
            }

    def _prepare_prompt(self, company_data: Dict, seo_analysis: Dict) -> str:
        """
        Prepare the prompt for the AI model with company-specific information.
        """
        # Extract key information
        company_name = company_data.get('company_name', 'the company')
        website_url = company_data.get('website_url', '')
        platform_type = company_data.get('platform_type', '')
        
        # Extract SEO issues and recommendations
        seo_issues = []
        if 'title' in seo_analysis:
            if not seo_analysis['title']['is_optimal_length']:
                seo_issues.append("title tag optimization")
            if not seo_analysis['title']['has_keywords']:
                seo_issues.append("keyword optimization in title")
        
        if 'meta_description' in seo_analysis:
            if not seo_analysis['meta_description']['is_optimal_length']:
                seo_issues.append("meta description optimization")
            if not seo_analysis['meta_description']['has_keywords']:
                seo_issues.append("keyword optimization in meta description")
        
        if 'headers' in seo_analysis:
            if not seo_analysis['headers']['has_h1']:
                seo_issues.append("missing H1 tags")
            if seo_analysis['headers']['multiple_h1']:
                seo_issues.append("multiple H1 tags")
        
        if 'images' in seo_analysis:
            if seo_analysis['images']['images_without_alt'] > 0:
                seo_issues.append("missing alt text on images")
        
        if 'content_analysis' in seo_analysis:
            if not seo_analysis['content_analysis']['is_optimal_length']:
                seo_issues.append("content length optimization")
        
        # Prepare the prompt
        prompt = f"""Write a personalized email pitch for {company_name} ({website_url}) that addresses the following SEO issues:
        
        Platform: {platform_type}
        SEO Issues: {', '.join(seo_issues)}
        
        The email should:
        1. Be professional and concise
        2. Reference specific issues found on their website
        3. Explain how our services can help improve their online presence
        4. Include a clear call to action
        5. Be personalized to their specific situation
        
        Focus on the most critical issues first and maintain a helpful, consultative tone."""
        
        return prompt

    def _generate_subject(self, company_data: Dict, seo_analysis: Dict) -> str:
        """
        Generate a compelling email subject line.
        """
        try:
            prompt = f"""Generate a compelling email subject line for {company_data.get('company_name', 'the company')} 
            based on their SEO issues: {', '.join(self._get_top_issues(seo_analysis))}
            
            The subject line should:
            1. Be attention-grabbing but professional
            2. Reference their specific situation
            3. Be under 60 characters
            4. Avoid spam trigger words"""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at writing email subject lines that get high open rates."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating subject line: {str(e)}")
            return "Improving Your Website's Online Presence"

    def _get_top_issues(self, seo_analysis: Dict) -> List[str]:
        """
        Extract the top 3 most critical SEO issues.
        """
        issues = []
        
        if 'title' in seo_analysis and not seo_analysis['title']['has_keywords']:
            issues.append("missing keywords in title")
        
        if 'meta_description' in seo_analysis and not seo_analysis['meta_description']['has_keywords']:
            issues.append("missing keywords in meta description")
        
        if 'headers' in seo_analysis and not seo_analysis['headers']['has_h1']:
            issues.append("missing H1 tags")
        
        if 'images' in seo_analysis and seo_analysis['images']['images_without_alt'] > 0:
            issues.append("missing image alt text")
        
        if 'content_analysis' in seo_analysis and not seo_analysis['content_analysis']['is_optimal_length']:
            issues.append("suboptimal content length")
        
        return issues[:3]  # Return top 3 issues

    def _extract_personalization_points(self, email_content: str) -> List[str]:
        """
        Extract key personalization points from the generated email.
        """
        try:
            prompt = f"""Extract the key personalization points from this email:
            
            {email_content}
            
            Return the points as a JSON array of strings."""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing email content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            points = json.loads(response.choices[0].message.content)
            return points
            
        except Exception as e:
            logger.error(f"Error extracting personalization points: {str(e)}")
            return [] 