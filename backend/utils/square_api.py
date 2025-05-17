# backend/utils/square_api.py
import base64
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import secrets
import requests

from django.conf import settings
from django.db import transaction 
from pytz import timezone
from square.client import Client

from businesses.serializers import SquareItemSerializer
from sales.models import SalesDataPoint

logger = logging.getLogger(__name__)

def get_square_client(business):
    """Initialize Square client from business token."""
    access_token = business.square_access_token
    if not access_token:
        logger.warning(f"No Square access token for business {business.id}")
        return None
    return Client(access_token=access_token, environment=settings.SQUARE_ENV)

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

def process_square_item(item, output_format="detail"):
    """
    Process a Square catalog item with flexible output formats.
    
    Args:
        item: Square catalog item data
        output_format: 
            - "detail": Complete details with IDs (for API responses)
            - "display": Formatted for display with pricing details
            - "summary": Simple name->description mapping
    
    Returns:
        Processed item in requested format or None if invalid
    """
    if not item or item.get("type") != "ITEM" or "item_data" not in item:
        return None
    
    item_data = item["item_data"]
    item_name = item_data.get("name", "")
    item_description = item_data.get("description", "")
    
    # Process variations consistently
    variations = []
    for variation in item_data.get("variations", []):
        if "item_variation_data" not in variation:
            continue
            
        var_data = variation["item_variation_data"]
        price_money = var_data.get("price_money", {})
        price_cents = price_money.get("amount", 0)
        
        # Ensure variation name is never blank
        var_name = var_data.get("name", "").strip() or "Default"
        
        var_info = {
            "name": var_name,
            "price_cents": price_cents,
            "price_money": price_money
        }
        
        # Include ID only for detail format
        if output_format == "detail":
            var_info["id"] = variation["id"]
            
        variations.append(var_info)
    
    # Skip items without valid variations
    if not variations:
        return None
    
    # Return data based on requested format
    if output_format == "summary":
        # Create price description string
        price_descriptions = []
        for variation in variations:
            price = variation["price_cents"]
            currency = variation["price_money"].get("currency", "USD")
            
            price_str = f"${price/100:.2f}" if currency == "USD" else f"{price/100:.2f} {currency}"
            if variation["name"] != "Default":
                price_descriptions.append(f"{variation['name']}: {price_str}")
            else:
                price_descriptions.append(price_str)
        
        price_text = ", ".join(price_descriptions)
        description = f"[{price_text}] {item_description}" if item_description else f"[{price_text}]"
        
        # Return mapping from lowercase name to description
        return {item_name.lower(): description}
        
    elif output_format == "display":
        # Use serializer for display formatting
        serializer_data = {
            "name": item_name,
            "description": item_description,
            "variations": [
                {"name": v["name"], "price_cents": v["price_cents"]} 
                for v in variations
            ]
        }
        
        serializer = SquareItemSerializer(data=serializer_data)
        if serializer.is_valid():
            return serializer.data
        else:
            logger.warning(f"Error with {item_name}: {serializer.errors}")
            return None
            
    else:  # "detail" format - full API response
        categories = [cat.get("id") for cat in item_data.get("categories", []) if "id" in cat]
        
        return {
            "id": item["id"],
            "name": item_name,
            "description": item_description,
            "variations": variations,
            "categories": categories
        }

def get_square_menu_items(business):
    """
    Get processed Square menu items with prices and descriptions.
    
    Returns:
        dict: {
            "square_connected": bool,
            "items": {item_name: description_with_price, ...}
        }
    """
    client = get_square_client(business)
    if client is None:
        return {"square_connected": False, "items": {}}
    
    locations = get_square_locations(client)    
    if not locations:
        return {"square_connected": False, "items": {}}
    
    items = get_square_items(client)
    if not items:
        return {"square_connected": True, "items": {}}
    
    # Process items into a name->description mapping
    items_summary = {}
    for item in items:
        result = process_square_item(item, output_format="summary")
        if result:
            items_summary.update(result)
    
    return {
        "square_connected": True,
        "items": items_summary
    }

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
    """Exchange authorization code for access token"""
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

def fetch_and_save_square_sales_data(business):

    """
    Fetch sales data from Square API and save it to the database.
    """
    # Calculate the date range
    end_date = datetime.now(timezone('UTC')).isoformat()
    
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
    
    # Fetch order data
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
        "limit": 1000  # Default: 500 Max: 1000
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        logger.error(f"Error fetching sales data: {response.status_code}, {response.text}")
        raise Exception(f"Square API error: {response.status_code}, {response.text}")

    sales_data = response.json()

    # Prepare the sales data for saving
    if sales_data:
        business_timezone = timezone('Australia/Brisbane')
        
        sales_points = []
                
        items = sales_data.get('orders', [])
        
        for order in items:
            # Skip orders with no line items
            if not order.get('line_items'):
                continue
            
            order_date = order.get('created_at')
            date_obj = datetime.strptime(order_date, '%Y-%m-%dT%H:%M:%S.%fZ')
            date_obj_local = date_obj.astimezone(business_timezone).date()
            
            for line_item in order.get('line_items', []):
                name = line_item.get('name', 'Unknown Product')

                quantity = int(line_item.get('quantity', 1))
                
                # Get the price from the line item
                base_price_money = line_item.get('base_price_money', {})
                price_amount = base_price_money.get('amount', 0)
                price = Decimal(price_amount) / Decimal(100)

                revenue = price * quantity
                
                # Skip items with zero revenue
                if revenue <= 0:
                    continue
                
                # Look for existing data point to update
                existing = SalesDataPoint.objects.filter(
                    business=business,
                    date=date_obj_local,
                    product_name=name,
                    product_price=price,
                    source='square'
                ).first()
                
                if existing:
                    # Update existing record
                    existing.units_sold += quantity
                    existing.revenue = existing.revenue + revenue
                    sales_points.append(existing)
                else:
                    # Create new record
                    sales_point = SalesDataPoint(
                        business=business,
                        date=date_obj_local,
                        product_name=name,
                        product_price=price,
                        units_sold=quantity,
                        revenue=revenue,
                        source='square'
                    )
                    sales_points.append(sales_point)

        # Save the sales data to the database within a transaction
        if sales_points:
            try:
                with transaction.atomic():
                    # Bulk update & create
                    SalesDataPoint.objects.bulk_update(
                        [point for point in sales_points if point.pk is not None], 
                        ['units_sold', 'revenue', 'product_name']
                    )
                    SalesDataPoint.objects.bulk_create(
                        [point for point in sales_points if point.pk is None]
                    )

                business.last_square_sync_at = datetime.now(timezone('UTC'))
                business.save()

            except Exception as e:
                logger.error(f"Error during saving sales data or updating promotions: {e}")
                raise

    