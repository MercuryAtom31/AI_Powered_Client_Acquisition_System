import os
from typing import Dict, Optional
from hubspot import HubSpot
from dotenv import load_dotenv

class HubSpotClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("HUBSPOT_API_KEY")
        if not self.api_key:
            raise ValueError("HUBSPOT_API_KEY not found in environment variables")
        self.client = HubSpot(access_token=self.api_key)

    def create_or_update_contact(self, contact_info: Dict) -> Optional[str]:
        """Create or update a contact in HubSpot."""
        try:
            # Prepare contact properties
            properties = {
                "email": contact_info.get("email", ""),
                "firstname": contact_info.get("first_name", ""),
                "lastname": contact_info.get("last_name", ""),
                "phone": contact_info.get("phone", ""),
                "company": contact_info.get("company", ""),
                "website": contact_info.get("website", ""),
                "seo_analysis": contact_info.get("seo_analysis", ""),
                "recommendations": contact_info.get("recommendations", "")
            }

            # Check if contact exists
            if contact_info.get("email"):
                search_response = self.client.crm.contacts.search_api.do_search(
                    query=contact_info["email"],
                    properties=["email"]
                )
                
                if search_response.total > 0:
                    # Update existing contact
                    contact_id = search_response.results[0].id
                    self.client.crm.contacts.basic_api.update(
                        contact_id=contact_id,
                        simple_public_object_input={"properties": properties}
                    )
                    return contact_id

            # Create new contact
            response = self.client.crm.contacts.basic_api.create(
                simple_public_object_input={"properties": properties}
            )
            return response.id

        except Exception as e:
            print(f"Error in HubSpot integration: {str(e)}")
            return None

    def create_deal(self, contact_id: str, deal_info: Dict) -> Optional[str]:
        """Create a deal in HubSpot associated with a contact."""
        try:
            properties = {
                "dealname": deal_info.get("name", "SEO Analysis Opportunity"),
                "pipeline": "default",
                "dealstage": "appointmentscheduled",
                "amount": deal_info.get("amount", "0"),
                "description": deal_info.get("description", "")
            }

            response = self.client.crm.deals.basic_api.create(
                simple_public_object_input={"properties": properties}
            )

            # Associate deal with contact
            self.client.crm.deals.associations_api.create(
                deal_id=response.id,
                to_object_type="contacts",
                to_object_id=contact_id,
                association_type="deal_to_contact"
            )

            return response.id

        except Exception as e:
            print(f"Error creating deal in HubSpot: {str(e)}")
            return None 