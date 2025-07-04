# hubspot.py

import datetime
import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import hashlib

import requests
from integrations.integration_item import IntegrationItem

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# HubSpot OAuth Configuration
# Replace with your actual HubSpot app credentials
CLIENT_ID = '3645f374-a386-4c6f-ae42-c6a8cd163be5'
CLIENT_SECRET = '2fde517c-c526-446e-b6c2-92187e397614'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'

# HubSpot OAuth URLs
AUTHORIZATION_URL = 'https://app.hubspot.com/oauth/authorize'
TOKEN_URL = 'https://api.hubapi.com/oauth/v1/token'

# Scopes for HubSpot API access
SCOPES = 'crm.objects.contacts.read crm.objects.companies.read crm.objects.deals.read'

# ---
# Step 1: Start OAuth flow by generating the authorization URL
async def authorize_hubspot(user_id, org_id):
    """
    Initiates HubSpot OAuth flow by generating authorization URL.
    Stores state and PKCE code verifier in Redis for security.
    """
    # Generate state for CSRF protection
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')

    # PKCE: Generate code verifier and challenge
    code_verifier = secrets.token_urlsafe(32)
    m = hashlib.sha256()
    m.update(code_verifier.encode('utf-8'))
    code_challenge = base64.urlsafe_b64encode(m.digest()).decode('utf-8').replace('=', '')

    # Construct the authorization URL
    auth_url = f'{AUTHORIZATION_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}&state={encoded_state}&code_challenge={code_challenge}&code_challenge_method=S256'

    # Store state and verifier in Redis (expire after 10 min)
    await asyncio.gather(
        add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=600),
        add_key_value_redis(f'hubspot_verifier:{org_id}:{user_id}', code_verifier, expire=600),
    )

    return auth_url

# ---
# Step 2: Handle OAuth callback and exchange code for tokens
async def oauth2callback_hubspot(request: Request):
    """
    Handles the OAuth callback from HubSpot.
    Validates state, exchanges code for access token, and stores credentials in Redis.
    """
    # Check for OAuth errors
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))
    
    # Get authorization code and state
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    
    if not code or not encoded_state:
        raise HTTPException(status_code=400, detail='Missing code or state parameter')
    
    # Decode state
    state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    # Retrieve stored state and verifier
    saved_state, code_verifier = await asyncio.gather(
        get_value_redis(f'hubspot_state:{org_id}:{user_id}'),
        get_value_redis(f'hubspot_verifier:{org_id}:{user_id}'),
    )

    # Validate state
    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': REDIRECT_URI,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'code_verifier': code_verifier.decode('utf-8'),
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f'Token exchange failed: {response.text}')

        # Clean up stored state and verifier
        await asyncio.gather(
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
            delete_key_redis(f'hubspot_verifier:{org_id}:{user_id}'),
        )

        # Store credentials in Redis (expire after 1 hour)
        await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=3600)
    
    # Return HTML to close popup window
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

# ---
# Step 3: Retrieve stored credentials for the user
async def get_hubspot_credentials(user_id, org_id):
    """
    Retrieves stored HubSpot credentials for a user from Redis.
    Credentials are deleted after retrieval for security (one-time use).
    """
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No HubSpot credentials found.')
    
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

# ---
# Helper: Convert HubSpot API response to IntegrationItem
# (Not strictly needed for minimal demo, but matches project pattern)
def create_integration_item_metadata_object(
    response_json: dict, item_type: str, parent_id=None, parent_name=None
) -> IntegrationItem:
    """
    Creates an IntegrationItem object from HubSpot API response.
    Used for standardizing data structure across integrations.
    """
    integration_item_metadata = IntegrationItem(
        id=response_json.get('id', '') + '_' + item_type,
        name=response_json.get('properties', {}).get('name') or response_json.get('properties', {}).get('firstname', '') + ' ' + response_json.get('properties', {}).get('lastname', ''),
        type=item_type,
        parent_id=parent_id,
        parent_path_or_name=parent_name,
        creation_time=datetime.datetime.fromtimestamp(response_json.get('createdAt', 0) / 1000) if response_json.get('createdAt') else None,
        last_modified_time=datetime.datetime.fromtimestamp(response_json.get('updatedAt', 0) / 1000) if response_json.get('updatedAt') else None,
    )
    return integration_item_metadata

# ---
# Step 4: Fetch items from HubSpot using the access token
async def get_items_hubspot(credentials) -> list[dict]:
    """
    Fetches items from HubSpot using the provided credentials.
    Calls the HubSpot API for contacts, companies, and deals.
    Returns a list of dicts for frontend display.
    """
    if isinstance(credentials, str):
        credentials = json.loads(credentials)
    
    access_token = credentials.get('access_token')
    if not access_token:
        raise HTTPException(status_code=400, detail='No access token found in credentials')

    list_of_integration_item_metadata = []
    
    # Fetch contacts
    try:
        contacts_response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/contacts',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'limit': 100}
        )
        
        if contacts_response.status_code == 200:
            contacts_data = contacts_response.json()
            for contact in contacts_data.get('results', []):
                list_of_integration_item_metadata.append(
                    create_integration_item_metadata_object(contact, 'Contact').__dict__
                )
    except Exception as e:
        print(f"Error fetching contacts: {e}")

    # Fetch companies
    try:
        companies_response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/companies',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'limit': 100}
        )
        
        if companies_response.status_code == 200:
            companies_data = companies_response.json()
            for company in companies_data.get('results', []):
                list_of_integration_item_metadata.append(
                    create_integration_item_metadata_object(company, 'Company').__dict__
                )
    except Exception as e:
        print(f"Error fetching companies: {e}")

    # Fetch deals
    try:
        deals_response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/deals',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'limit': 100}
        )
        
        if deals_response.status_code == 200:
            deals_data = deals_response.json()
            for deal in deals_data.get('results', []):
                list_of_integration_item_metadata.append(
                    create_integration_item_metadata_object(deal, 'Deal').__dict__
                )
    except Exception as e:
        print(f"Error fetching deals: {e}")

    print(f'HubSpot integration items: {list_of_integration_item_metadata}')
    return list_of_integration_item_metadata