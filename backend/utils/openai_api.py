import os
import logging
from openai import OpenAI
from openai import OpenAIError

logger = logging.getLogger(__name__)

def get_openai_api_key():
    """
    Get the OpenAI API key from environment variables.
    """
    return os.getenv("OPENAI_API_KEY")

def generate_captions(
        categories,
        business_info,
        item_info,
        additional_prompt="",
        include_sales_data=False,
        detected_items=None,
        image_url=None,
    ):
    """
    Generate captions using OpenAI API.
    
    Args:
        categories (List[str]): List of post categories
        business_info (Dict): Business target customers and vibe
        item_info (List[Dict]): List of items with name and description
        additional_prompt (str, optional): Additional context for caption
        include_sales_data (bool): Whether to include sales data
        detected_items (List[str], optional): List of detected items from image
        image (File, optional): Image file for analysis
    
    Returns:
        List[str]: List of generated captions
    """
    api_key = get_openai_api_key()

    client = OpenAI(
        api_key=api_key,
    )

    prompt = f"""
    Generate one engaging and creative social media captions for a business post.
    Do not include any additional text like "1.", "2.", or conversational phrases.
    Do not use quotes ("") around the captions.


    Business Information:
    - Business Name: {business_info['name']}
    - Business Type: {business_info['type']}
    - Target Customers: {business_info['target_customers']}
    - Business Vibe: {business_info['vibe']}

    Post Purposes: {', '.join(categories)}

    Featured Items:
    {', '.join([f"{item['name']}: {item['description']}" for item in item_info]) if item_info else 'No featured items'}

    {f'Detected in Image: {", ".join(detected_items)}' if detected_items else ''}
    {f'Additional Context: {additional_prompt}' if additional_prompt else ''}
    """

    logger.info(f"Generated prompt: {prompt}")

    # Construct the input for the API
    input_data = [
        {
            "role": "system",
            "content": "You are a professional social media marketer."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": "low"
                    }
                } if image_url else None,
          ],
        }
    ]

    # Filter out None values from the content list
    input_data[1]['content'] = [x for x in input_data[1]['content'] if x is not None]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=input_data,
            n=5,  # Number of captions to generate
            temperature=0.5,
            max_tokens=150,
        )
        
        logger.info(response)
        # Extract captions from response
        captions = [choice.message.content.strip() for choice in response.choices]
        return captions
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
        raise Exception(f"Error generating captions: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise Exception(f"Unexpected error: {str(e)}")

