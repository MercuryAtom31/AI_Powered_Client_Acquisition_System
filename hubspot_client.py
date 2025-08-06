import os
import time
import json
from typing import Dict, Optional
from dotenv import load_dotenv
from hubspot import HubSpot

from hubspot.crm.contacts import (
    PublicObjectSearchRequest,
    Filter,
    FilterGroup,
    SimplePublicObjectInput as ContactUpdate,              # for updates
    SimplePublicObjectInputForCreate as ContactCreate       # for creates
)
from hubspot.crm.deals import SimplePublicObjectInputForCreate as DealCreate
from hubspot.crm.objects import SimplePublicObjectInput as NoteCreateInput

class HubSpotClient:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("HUBSPOT_API_KEY")
        if not api_key:
            raise ValueError("HUBSPOT_API_KEY not found in environment variables")
        self.client = HubSpot(access_token=api_key)

    def create_or_update_contact(self, contact_info: Dict) -> Optional[str]:
        """Create or update a contact in HubSpot."""
        try:
            props = {
                "email":        contact_info.get("email", ""),
                "firstname":    contact_info.get("first_name", ""),
                "lastname":     contact_info.get("last_name", ""),
                "phone":        contact_info.get("phone", ""),
                "company":      contact_info.get("company", ""),
                "website":      contact_info.get("website", ""),
                "hubspot_owner_id": contact_info.get("hubspot_owner_id", ""),
                "seo_analysis": contact_info.get("seo_analysis", ""),
            }

            email = props["email"]
            if email:
                f = Filter(property_name="email", operator="EQ", value=email)
                group = FilterGroup(filters=[f])
                req = PublicObjectSearchRequest(
                    filter_groups=[group],
                    properties=["email"]
                )
                resp = self.client.crm.contacts.search_api.do_search(req)
                if resp.total > 0:
                    existing_id = resp.results[0].id
                    self.client.crm.contacts.basic_api.update(
                        contact_id=existing_id,
                        simple_public_object_input=ContactUpdate(properties=props)
                    )
                    return existing_id

            new_contact = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=ContactCreate(properties=props)
            )
            return new_contact.id

        except Exception as e:
            print(f"Error in HubSpot integration: {e}")
            return None

    def create_deal(self, contact_id: str, deal_info: Dict) -> Optional[str]:
        """Create a deal in HubSpot and associate it with a contact."""
        try:
            props = {
                "dealname":    deal_info.get("name", "SEO Analysis Opportunity"),
                "pipeline":    deal_info.get("pipeline", "default"),
                "dealstage":   deal_info.get("dealstage", "appointmentscheduled"),
                "amount":      deal_info.get("amount", "0"),
                "description": deal_info.get("description", ""),
            }

            deal = self.client.crm.deals.basic_api.create(
                simple_public_object_input_for_create=DealCreate(properties=props)
            )
            self.client.crm.deals.associations_api.create(
                deal_id=deal.id,
                to_object_type="contacts",
                to_object_id=contact_id,
                association_type="deal_to_contact"
            )
            return deal.id

        except Exception as e:
            print(f"Error creating deal in HubSpot: {e}")
            return None



    # def create_analysis_note(self, contact_id: str, analysis: Dict) -> Optional[str]:
    #     """
    #     Attach a Note to the given contact containing the full analysis JSON,
    #     wrapped in an HTML <pre> so HubSpot preserves formatting and non-ASCII chars.
    #     """
    #     try:
    #         # 1) Dump JSON without ASCII-escaping, indent for readability
    #         raw_json = json.dumps(analysis, indent=2, ensure_ascii=False)

    #         # 2) Wrap in <pre> so HubSpot shows it as a code block
    #         body_html = (
    #             "<pre style='white-space: pre-wrap; "
    #             "font-family: monospace; font-size: 0.85rem;'>"
    #             f"{raw_json}"
    #             "</pre>"
    #         )

    #         # 3) Build note input
    #         note_input = NoteCreateInput(properties={
    #             "hs_note_body": body_html,
    #             "hs_timestamp": str(int(time.time() * 1000))
    #         })

    #         # 4) Create the Note
    #         note_obj = self.client.crm.objects.basic_api.create(
    #             object_type="notes",
    #             simple_public_object_input_for_create=note_input
    #         )
    #         note_id = note_obj.id

    #         # 5) Associate it to the contact
    #         self.client.crm.objects.associations_api.create(
    #             object_type="notes",
    #             object_id=note_id,
    #             to_object_type="contacts",
    #             to_object_id=contact_id,
    #             association_type="note_to_contact"
    #         )

    #         return note_id

    #     except Exception as e:
    #         print(f"Error creating analysis note: {e}")
    #         return None


    def create_analysis_note(self, contact_id: str, note_text: str) -> Optional[str]:
        """
        Attach a Note to the given contact containing the pre-formatted plain text,
        wrapped in an HTML <pre> so HubSpot preserves spacing and line breaks.
        """
        try:
            # wrap your already-formatted text in a <pre>
            body_html = (
                "<pre style='white-space: pre-wrap; "
                "font-family: monospace; font-size: 0.85rem;'>"
                f"{note_text}"
                "</pre>"
            )

            note_input = NoteCreateInput(properties={
                "hs_note_body": body_html,
                # HubSpot wants a millisecond timestamp
                "hs_timestamp": str(int(time.time() * 1000))
            })

            note_obj = self.client.crm.objects.basic_api.create(
                object_type="notes",
                simple_public_object_input_for_create=note_input
            )
            note_id = note_obj.id

            # associate it with your contact
            self.client.crm.objects.associations_api.create(
                object_type="notes",
                object_id=note_id,
                to_object_type="contacts",
                to_object_id=contact_id,
                association_type="note_to_contact"
            )

            return note_id

        except Exception as e:
            print(f"Error creating analysis note: {e}")
            return None
