from sales.models import SalesDataPoint
from config import settings
from businesses.serializers import SquareItemSerializer
from square.client import Client
from datetime import datetime, timedelta
from pytz import timezone
from django.db import transaction 
from collections import defaultdict
from decimal import Decimal
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

def format_square_item(item):
    """Format a Square catalog item for the API response."""
    if not item or item.get("type") != "ITEM" or "item_data" not in item:
        return None
    
    item_data = item["item_data"]
    
    variations = []
    for variation in item_data.get("variations", []):
        if "item_variation_data" in variation:
            var_data = variation["item_variation_data"]
            price_money = var_data.get("price_money", {})
            variations.append({
                "id": variation["id"],
                "name": var_data.get("name", ""),
                "price_money": price_money,
            })

    categories = [cat.get("id") for cat in item_data.get("categories", []) if "id" in cat]
    
    return {
        "id": item["id"],
        "name": item_data.get("name", ""),
        "description": item_data.get("description", ""),
        "variations": variations,
        "categories": categories
    }

def fetch_and_save_square_sales_data(business):
    """
    Fetch sales data from Square API and save it to the database.
    Args:
        business (Business): The business object for which to fetch sales data.
    """
    method = 'orders' # 'payments' or 'orders'

    # Calculate the date range
    end_date = datetime.now(timezone('UTC')).isoformat()
    
    # Check if last_square_sync_at is set, otherwise default to 30 days ago
    if business.last_square_sync_at:
        start_date = business.last_square_sync_at.isoformat()
    else:
        start_date = (datetime.now(timezone('UTC')) - timedelta(days=30)).isoformat()

    # Get location id
    client = get_square_client(business)
    locations = get_square_locations(client)
    if not locations:
        logger.error("No Square location found.")
        return
    location_id = locations[0].get("id") if locations else None
    
    headers = {
        "Authorization": f"Bearer {business.square_access_token}",
        "Content-Type": "application/json"
    }

    if method == 'payments':
        url = f"{settings.SQUARE_BASE_URL}/v2/payments"
        params = {
            "begin_time": start_date,
            "end_time": end_date,
            "sort_field": "CREATED_AT",
            "sort_order": "DESC",
            "location_id": location_id,
        }
        response = requests.get(url, headers=headers, params=params)
    elif method == 'orders':
        url = f"{settings.SQUARE_BASE_URL}/v2/orders/search"
        body = {
            "location_ids": [location_id],
            "query": {
                "filter": {
                    "date_time_filter": {
                        "created_at": {
                            "start_at": start_date,
                            "end_at": end_date
                        }
                    }
                }
            },
            "sort": {
                "sort_field": "CREATED_AT",
                "sort_order": "DESC"
            },
            "limit": 1000 # Default: 500 Max: 1000
        }
        response = requests.post(url, headers=headers, json=body)
    else:
        raise Exception(f"Wrong method is selected: {method}")

    if response.status_code != 200:
        logger.error(f"Error fetching sales data: {response.status_code}, {response.text}")
        raise Exception(f"Square API error: {response.status_code}, {response.text}")

    sales_data = response.json()
    logger.info(f"Sales data fetched successfully: {sales_data}")

    if sales_data:
        # Prepare the sales data for saving
        business_timezone = timezone('Australia/Brisbane')
        daily_revenue = defaultdict(Decimal)
        if method == 'payments':
            items = sales_data['payments']
            for record in items:
                date = record['created_at']
                revenue = Decimal(record['amount_money']['amount']) / Decimal(100)
                date_obj = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
                date_obj_local = date_obj.astimezone(business_timezone).date()
                daily_revenue[date_obj_local] += revenue
        elif method == 'orders':
            items = sales_data['orders']
            for record in items:
                date = record['created_at']
                money_info = record.get('total_money')
                if not money_info:
                    continue
                revenue = Decimal(money_info['amount']) / Decimal(100)
                date_obj = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
                date_obj_local = date_obj.astimezone(business_timezone).date()
                daily_revenue[date_obj_local] += revenue

        logger.debug(f"Daily revenue calculated: {daily_revenue}")
        
        # Prepare the sales data points for saving or updating
        sales_points = []
        for day, amount in daily_revenue.items():
            # Check if the sales data point already exists
            existing_point = SalesDataPoint.objects.filter(
                business=business, date=day, source='square'
            ).first()

            if existing_point:
                # Update the existing record
                existing_point.revenue += amount
                sales_points.append(existing_point)
            else:
                # Create a new record
                sales_points.append(SalesDataPoint(business=business, date=day, revenue=amount, source='square'))

        logger.debug(f"Prepared {sales_points} sales data points for saving.")

        # Save the sales data to the database within a transaction
        if sales_points:
            with transaction.atomic():
                # Bulk create or update
                SalesDataPoint.objects.bulk_update(
                    [point for point in sales_points if point.pk is not None], ['revenue']
                )
                SalesDataPoint.objects.bulk_create(
                    [point for point in sales_points if point.pk is None]
                )
                logger.debug(f"Saved {len(sales_points)} sales data points to the database.")
    
    business.last_square_sync_at = datetime.now(timezone('UTC'))
    business.save()
    logger.debug(f"Updated last_square_sync_at for business {business.id} to {business.last_square_sync_at}")
