from config import settings
from businesses.serializers import SquareItemSerializer
from square.client import Client
import base64
import secrets
import requests
import logging

logger = logging.getLogger(__name__)

def get_square_summary(business):
    """
    Fetch summary data from Square API for a given business.
    """
    result = {
        "square_connected": False,
        "items": [],
    }

    client = get_square_client(business)
    locations = get_square_locations(client)    
    if locations:
        result["square_connected"] = True
    
    items = get_square_items(client)
    if items:
        result["items"] = {
            item["name"].lower(): item["description_with_price"]
            for item in reformat_square_items(items)
        }

    return result
    
def get_square_client(business):
    """Initialize Square client from business token."""
    access_token = business.square_access_token
    if not access_token:
        logger.warning(f"No Square access token for business {business.id}")
        return None
    return Client(access_token=access_token, environment="production")

def get_square_locations(client):
    """Fetch list of locations."""
    if client is None:
        logger.warning("Square client is None")
        return []
    
    try:
        location_api = client.locations
        location_response = location_api.list_locations()
        if location_response.is_success():
            locations = location_response.body.get("locations", [])
            return locations
        logger.warning("Failed to fetch Square locations")
    except Exception as e:
        logger.error(f"Square locations fetch error: {e}")
    return []

def get_square_orders(client, location_id):
    """Fetch list of orders."""
    try:
        orders_api = client.orders
        search_body = {
            "location_ids": [location_id],
            "limit": 10, # TODO
            "sort": {
                "sort_field": "CREATED_AT",
                "sort_order": "DESC"
            }
        }
        order_response = orders_api.search_orders(body=search_body)
        if order_response.is_success():
            orders = order_response.body.get("orders", [])
            logger.debug(f"Orders fetched: {orders}")
            return orders
        logger.warning("Failed to fetch Square orders")
    except Exception as e:
        logger.error(f"Square orders fetch error: {e}")
    return []

def get_square_items(client):
    """Fetch list of items."""
    try:
        catalog_api = client.catalog
        catalog_response = catalog_api.list_catalog(
            cursor=None,
            types=["ITEM"]
        )
        if catalog_response.is_success():
            items = catalog_response.body.get("objects", [])
            return items
        logger.warning("Failed to fetch Square items")
    except Exception as e:
        logger.error(f"Square items fetch error: {e}")
    return []

def reformat_square_items(items):
    """
    Reformat Square items to a more usable format using serializers.
    Args:
        items (list): List of items from Square API.
    Returns:
        list: Reformatted list of items.
    """
    reformatted_items = []
    for item in items:
        if item.get("type") == "ITEM" and "item_data" in item:
            item_data = item["item_data"]
            
            variations = []
            for variation in item_data.get("variations", []):
                if "item_variation_data" in variation:
                    var_data = variation["item_variation_data"]
                    price_cents = var_data.get("price_money", {}).get("amount", 0)
                    variations.append({
                        "name": var_data.get("name", ""),
                        "price_cents": price_cents
                    })
            
            serializer = SquareItemSerializer(data={
                "name": item_data.get("name", ""),
                "description": item_data.get("description", ""),
                "variations": variations
            })
            
            if serializer.is_valid():
                reformatted_item = serializer.data
                logger.debug(f"Item: {item_data.get('name')}, Variations: {variations}, Formatted: {reformatted_item.get('description_with_price')}")
                reformatted_items.append(reformatted_item)
            else:
                logger.warning(f"Error with {item_data.get('name')}: {serializer.errors}")
    
    return reformatted_items

def get_auth_url_values():
    """
    Generate the URL values for Square OAuth authentication.
    Returns:
        dict: Dictionary containing the URL values.
    """
    def base64_encode(data):
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip("=")
    
    state = base64_encode(secrets.token_bytes(12))

    return {
        "state": state,
        "app_id": settings.SQUARE_APP_ID,
        "redirect_uri": settings.SQUARE_REDIRECT_URI,
    }

def exchange_code_for_token(code):
    url = f"{settings.SQUARE_BASE_URL}/oauth2/token"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "client_id": settings.SQUARE_APP_ID,
        "client_secret": settings.SQUARE_APP_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.SQUARE_REDIRECT_URI 
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to exchange code for token: {response.status_code} - {response.text}"}
