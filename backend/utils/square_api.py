import os
import logging
from square.client import Client

logger = logging.getLogger(__name__)

def check_square_integration(business):
    """
    Check Business status using Square API.
    Args:
        business (Business): The business object to check.
    """
    result = {
        "hasPOSIntegration": False,
        "hasSalesData": False,
        "hasItemsInfo": False,
        "items": [],
    }

    square_access_token = get_square_access_token(business)
    if not square_access_token:
        logger.warning(f"No Square access token found for business: {business.id}")
        return result
    
    try:
        clint = Client(
            access_token=square_access_token,
            environment="production",  # or "sandbox"
        )

        location_api = clint.locations
        location_response = location_api.list_locations()
        if location_response.is_success():
            locations = location_response.body.get("locations", [])
            logger.debug(f"Locations fetched: {locations}")
            if locations:
                result["hasPOSIntegration"] = True
            
            location_id = locations[0]["id"] if locations else None
            logger.debug(f"Using location ID: {location_id}")
            
            if location_id:
                # Check if there are any orders in the location
                orders_api = clint.orders
                search_body  = {
                    "location_ids":[location_id],
                    "limit":1
                }
                order_response = orders_api.search_orders(body=search_body)
                if order_response.is_success():
                    orders = order_response.body.get("orders", [])
                    logger.debug(f"Orders fetched: {orders}")
                    # Check if there are any orders in the location
                    if orders:
                        result["hasSalesData"] = True
                
                catalog_api = clint.catalog
                catalog_response = catalog_api.list_catalog(
                    cursor=None,
                    types=["ITEM"]
                )
                if catalog_response.is_success():
                    items = catalog_response.body.get("objects", [])
                    logger.debug(f"Items fetched: {items}")
                    # Check if there are any items in the catalog
                    if items:
                        result["hasItemsInfo"] = True
                        filtered_items = [
                            {
                                "name": item["item_data"].get("name", ""),
                                "description": item["item_data"].get("description", ""),
                                "price": ", ".join(
                                    f"{variation.get('item_variation_data', '').get('name', '')}{' ' if variation.get('item_variation_data', '').get('name', '') else ''}${variation.get('item_variation_data', {}).get('price_money', {}).get('amount', 0) / 100}"
                                    for variation in item["item_data"].get("variations", [])
                                    if "item_variation_data" in variation
                                )
                            }
                            for item in items
                            if item.get("type") == "ITEM" and "item_data" in item
                        ]
                        result["items"] = filtered_items
        else:
            logger.warning("No location ID found in Square response")
        return result
    except Exception as e:
        logger.error(f"Error checking Square integration: {e}")
        return result
    
def get_square_access_token(business):
    """
    Get the Square access token for the business.
    Args:
        business (Business): The business object to check.
    """
    # try:
    #     linked_POS = business.linked_POS.get(platform="Square")
    #     return linked_POS.access_token
    # except linked_POS.DoesNotExist:
    #     logger.warning(f"No Square linked platform found for business: {business.id}")
    #     return None
    return os.getenv("SQUARE_ACCESS_TOKEN")