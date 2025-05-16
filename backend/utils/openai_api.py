import json
import logging

from django.conf import settings
from openai import OpenAI
from openai import OpenAIError

logger = logging.getLogger(__name__)

def generate_promotions(payload):
    """
    Generate multiple social media promotion suggestions based on business context, product performance, and pricing data using OpenAI's GPT model.
    """
    api_key = settings.OPENAI_API_KEY
    client = OpenAI(api_key=api_key)

    products_performance = payload['products_performance']
    context_data = payload['context_data']
    feedback_history = payload['feedback_history']
    start_date = products_performance['start_date']
    end_date = products_performance['end_date']

    # Build feedback context if available
    feedback_context = ""
    if feedback_history:
        feedback_context = "\n\nFeedback History (Use this to imporve suggestions):\n"
        for idx, item in enumerate(feedback_history):
            product_list = ", ".join(item["product_names"]) if item["product_names"] else "N/A"
            feedback_context += f"{idx+1}. Products: {product_list} - Feedback: \"{item['feedback']}\"\n"

    prompt = f"""
    Based on the provided business context, product performance (from {start_date} to {end_date}), and general consumer insights, generate 3 distinct promotion suggestions for each of the top 10 best-selling and bottom 10 low-performing products (exclude average-performing ones entirely).
    
    Each suggestion must follow this structure:
    [
        {{
            "product_name": [<product_name_1>, <product_name_2>, ...],  # List ALL products mentioned in the description
            "category": ["discount", "bundle", "social"],  // Select ALL applicable categories (not just one).
            "title": <suggestion_title>,
            "description": <suggestion_description>
                # Clearly state which product is best-selling or low-performing
                # Include actual confirmed numbers: original prices, discounted rates, new prices, bundle totals, sold quantities during n-days, happy hour time etc. (e.g, “sold 120 in the recent {(end_date - start_date).days}days”)
                # Explain why the promotion works for this product (e.g., bundling a low-performer with a top-seller to increase exposure)
                # Support reasoning with general customer insights (e.g., popular combinations, taste profiles, typical behavior)
        }}
    ]

    After generating all suggestions, return only a single JSON array containing the top 5 most promising promotions (out of all generated) that are most likely to increase revenue, based on product performance, customer behavior, and general insights.
    
    Business Information:
    - Business Name: {context_data['name']}
    - Business Type: {context_data['type']}
    - Target Customers: {context_data['target_customers']}
    - Business Vibe: {context_data['vibe']}

    Products Performance: {products_performance}
    {feedback_context}
    """

    # Construct the input for the API
    input_data = [
        {
            "role": "system",
            "content": "You are a data-driven marketing strategist."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
          ],
        }
    ]

    # Filter out None values from the content list
    input_data[1]['content'] = [x for x in input_data[1]['content'] if x is not None]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=input_data,
            temperature=0.5,
        )
        
        # Parse the result into a structured format
        promotions = []
        for choice in response.choices:
            result = choice.message.content.strip('```json\n').strip('```')
            try:
                promotion_list = json.loads(result)
                promotions.extend(promotion_list)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding response: {e}")
                raise Exception(f"Error parsing promotion response: {e}")
        return promotions
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
        raise Exception(f"Error generating promotion suggestions: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise Exception(f"Unexpected error: {str(e)}")

def generate_captions(
        categories,
        business_info,
        item_info,
        additional_prompt="",
    ):
    """
    Generate captions using OpenAI API.
    
    Args:
        categories (List[str]): List of post categories
        business_info (Dict): Business target customers and vibe
        item_info (List[Dict]): List of items with name and description
        additional_prompt (str, optional): Additional context for caption
    
    Returns:
        List[str]: List of generated captions
    """
    api_key = settings.OPENAI_API_KEY
    client = OpenAI(api_key=api_key)

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

    {f'Additional Context: {additional_prompt}' if additional_prompt else ''}
    """

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
        
        # Extract captions from response
        captions = [choice.message.content.strip() for choice in response.choices]
        return captions
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
        raise Exception(f"Error generating captions: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise Exception(f"Unexpected error: {str(e)}")

