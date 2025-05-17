import logging
import os
import requests

from django.conf import settings

logger = logging.getLogger(__name__)

def get_discord_webhook_url():
    """
    Get the Discord webhook URL from environment variables.
    """
    return settings.DISCORD_WEBHOOK_URL

def upload_image_file_to_discord(image_file):
    """
    Upload an image file to a Discord channel using a webhook URL.
    """
    webhook_url = get_discord_webhook_url()
    if not webhook_url:
        raise ValueError("Discord webhook URL is not set.")
    
    message_id = None
    image_url = None
    
    temp_file_path = f"/tmp/{image_file.name}"
    with open(temp_file_path, 'wb+') as temp_file:
        for chunk in image_file.chunks():
            temp_file.write(chunk)


    with open(temp_file_path, 'rb') as image_file:
        files = {'file': image_file}
        response = requests.post(webhook_url, files=files)
    
    os.remove(temp_file_path)
    
    if response.status_code == 200:
        message_data = response.json()
        message_id = message_data.get('id')
        
        image_url = message_data['attachments'][0].get('url')

        return {
            'message_id': message_id,
            'image_url': image_url
        }
    else:
        raise Exception(f"Failed to upload image: {response.status_code} - {response.text}")
    
    
def delete_discord_message(message_id):
    """
    Delete a message from a Discord channel using a webhook URL.

    Args:
        message_id (str): ID of the message to be deleted.

    Returns:
        str: The response from the Discord API.
    """
    webhook_url = get_discord_webhook_url()
    if not webhook_url:
        raise ValueError("Discord webhook URL is not set.")
    
    parts = webhook_url.split("/")
    webhook_id = parts[-2]
    webhook_token = parts[-1]

    delete_url = f"https://discord.com/api/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}"

    response = requests.delete(delete_url)
    
    if response.status_code in [200, 204]:
        # Discord API returns 204 No Content on successful deletion
        return True
    else:
        logger.error(f"Failed to delete message: {response.status_code} - {response.text}")
        return False