import requests
import json
from typing import Dict, List, Optional

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "gemma:2b"  # Using Gemma 2B model

    def generate_seo_analysis(self, url: str, content: Dict) -> Dict:
        """Generate SEO analysis using local LLM."""
        prompt = f"""Analyze the following website content and provide SEO recommendations:
        URL: {url}
        Content: {json.dumps(content, indent=2)}
        
        Please provide:
        1. Key SEO issues
        2. Content quality assessment
        3. Technical SEO recommendations
        4. Content improvement suggestions
        """

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def generate_outreach_email(self, company_info: Dict) -> str:
        """Generate a personalized outreach email based on company information."""
        prompt = f"""Generate a professional outreach email based on this company information:
        {json.dumps(company_info, indent=2)}
        
        The email should:
        1. Be personalized based on their business
        2. Reference specific SEO issues found
        3. Offer concrete solutions
        4. Be professional but conversational
        """

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            return f"Error generating email: {str(e)}" 