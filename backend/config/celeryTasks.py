from datetime import datetime
import logging

from celery import shared_task
import requests

logger = logging.getLogger(__name__)

def get_facebook_page_id(access_token):
    #Retrieve facebook page id data from Meta's API
    url = f'https://graph.facebook.com/v22.0/me/accounts?access_token={access_token}'
    response = requests.get(url)
    #return Response({'message':response,'access_token':access_token,'status':status.HTTP_200_OK})
    if response.status_code != 200:
        # Handle error response    
        return None
    metasData = response.json()
    if not metasData.get("data"):
        return None
    #else return the page id
    return metasData.get("data")[0]["id"]

def returnInstagramDetails(facebookPageID,access_token):
    url = f'https://graph.facebook.com/v22.0/{facebookPageID}?fields=instagram_business_account&access_token={access_token}'
    response = requests.get(url)
    data=response.json()
    if response.status_code != 200:
        # Handle error retrieving insta account id   
        return None
    insta_account_data = data.get("instagram_business_account")
    if not insta_account_data:
        return None #return error if no instagram account found
    return insta_account_data.get("id") #return the instagram account id

def publishToMeta(platform, caption, image_url, token_decoded):
    facebookPageID=get_facebook_page_id(token_decoded)
    if not facebookPageID:
        return {"error": "Unable to retrieve Facebook Page ID! Maybe reconnect your Facebook or Instagram account in Settings!", "status": False}

    #For Facebook
    if platform == 'facebook':
        #Get page access token
        url = f'https://graph.facebook.com/v22.0/me/accounts?access_token={token_decoded}'
        response = requests.get(url)
        if response.status_code != 200:
            # Handle error response
            return {"error": f"Unable to retrieve page access token. {response.text}", "status": False}
        metasData = response.json()
        if not metasData.get("data"):
            return {"error": "Unable to retrieve page access token 2", "status": False}
        #Get the page access token
        page_access_token = metasData.get("data")[0]["access_token"]
        # Create media object for Facebook
        url = f'https://graph.facebook.com/v22.0/{facebookPageID}/photos'
        data = {
            "url": image_url,
            "message": caption,
            "access_token": page_access_token
        }
        # if scheduled_at:
        #     dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        #     unix_timestamp = int(dt.timestamp())
        #     data.update({"published": 'false',"scheduled_publish_time": unix_timestamp})

        response = requests.post(url, data=data)
        if response.status_code != 200:
            # Handle error response
            return {"error": f"Unable to create Media Obj for Facebook. {response.text}", "status": False}
        media_data = response.json()
        if not media_data.get("post_id"):
            return {"error": "Unable to retrieve post ID", "status": False}
        post_id = media_data.get("post_id")

        #Get URL to the post
        url = f'https://graph.facebook.com/v22.0/{post_id}?fields=permalink_url&access_token={page_access_token}'
        response = requests.get(url)
        if response.status_code != 200:
            # Handle error response
            return {"error": "Unable to get post url", "status": False}
        post_data = response.json()
        if not post_data.get("permalink_url"):
            return {"error": "Unable to retrieve post url from json", "status": False}
        post_url = post_data.get("permalink_url")
        
        return {"message": post_url, "status": True}

    #For Instagram
    #Create media object
    # Get the Instagram account ID
    instagram_account_id = returnInstagramDetails(facebookPageID,token_decoded)
    if not instagram_account_id:    
        return {"error": "Unable to retrieve Insta ID", "status": False}
    
    url = f'https://graph.facebook.com/v22.0/{instagram_account_id}/media'
    data = {
        "image_url": image_url,
        "caption": caption,
        "alt_text": "This is the alt text for the image",
        "access_token": token_decoded
    }

    response = requests.post(url, data=data)
    if response.status_code != 200:
        # Handle error response
        return {"error": f"Unable to create Media Obj. {response.text}", "status": False}
    media_data = response.json()
    if not media_data.get("id"):
        return {"error": "Unable to retrieve media ID", "status": False}
    media_id = media_data.get("id")

    #Publish the media object
    url = f'https://graph.facebook.com/v22.0/{instagram_account_id}/media_publish?creation_id={media_id}&access_token={token_decoded}'
    response = requests.post(url)
    if response.status_code != 200:
        # Handle error response
        return {"error": "Unable to publish media obj", "status": False}
    publish_data = response.json()
    if not publish_data.get("id"):
        return {"error": "Unable to retrieve publish ID", "status": False}
    post_id = publish_data.get("id")
    #Get the link to the post
    url = f'https://graph.facebook.com/v22.0/{post_id}?fields=permalink&access_token={token_decoded}'
    response = requests.get(url)
    if response.status_code != 200:
        # Handle error response
        return {"error": "Unable to get post url", "status": False}
    post_data = response.json()
    if not post_data.get("permalink"):
        return {"error": "Unable to retrieve post url from json", "status": False}
    post_url = post_data.get("permalink")
    # Return the post ID
    return {"message": post_url, "status": True}

@shared_task
def publish_to_meta_task(platform,caption,image,token):
    logger.error("Scheduled task recieved!")
    error=publishToMeta(platform,caption,image,token)
    if(error.get('error')):
        logger.error(error.get('error'))
    logger.error(f"Scheduled task ran at: {datetime.now()}")