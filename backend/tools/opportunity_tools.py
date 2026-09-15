from typing import List, Dict, Any
from adk import tool
from backend.providers.opportunity_provider import JobOpportunitiesProvider
import json

opportunity_provider = JobOpportunitiesProvider()

@tool
async def search_opportunities_tool(query: str, location: str = "") -> str:
    """
    Search for real-world job opportunities from the JobOpportunitiesAPI.
    Returns structured JSON data with opportunities matching the query.
    
    Args:
        query: The search term (e.g. "software engineer", "cricket coach")
        location: Optional location filter (e.g. "Wien", "India")
    """
    # Fetch from real API
    opps = await opportunity_provider.fetch_opportunities(role_filter=query, geography=location)
    
    # Return as JSON string for the LLM
    if not opps:
        return json.dumps({"status": "no_results", "opportunities": []})
        
    data = []
    for opp in opps[:10]: # Limit to top 10 to save token space
        data.append({
            "title": opp.title,
            "organization": opp.organization,
            "location": opp.location,
            "type": opp.opportunity_type,
            "url": opp.source_url
        })
        
    return json.dumps({"status": "success", "opportunities": data}, indent=2)
