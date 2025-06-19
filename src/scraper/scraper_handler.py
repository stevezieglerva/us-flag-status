import json
import boto3
import os
import re
from datetime import datetime, timedelta

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')
BUCKET_NAME = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    """
    Main Lambda handler for scraping flag status using Bedrock
    """
    try:
        print("Starting flag status scraping...")
        
        # Use Bedrock to search for flag proclamations
        flag_data = search_flag_proclamations()
        
        if not flag_data:
            print("No flag data retrieved from Bedrock")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to retrieve flag data'})
            }
        
        # Update S3 files
        update_current_status(flag_data)
        update_index(flag_data)
        
        # Save individual proclamation if half-staff
        if flag_data.get('status') == 'half_staff':
            save_proclamation(flag_data)
        
        print(f"Successfully updated flag status: {flag_data.get('status')}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully updated flag status',
                'status': flag_data.get('status'),
                'reason': flag_data.get('reason'),
                'last_updated': flag_data.get('last_updated')
            })
        }
        
    except Exception as e:
        print(f"Error in scraper: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def search_flag_proclamations():
    """
    Use Bedrock Claude to search for flag proclamations
    """
    search_prompt = """
    Search for recent US presidential proclamations about flag half-staff status from whitehouse.gov.
    Look for any current or recent orders to lower flags to half-staff.
    
    Return a JSON response with this exact structure:
    {
      "status": "half_staff" or "full_staff",
      "reason": "brief description of why flags are at half-staff",
      "trigger_type": "death|memorial_day|tragedy|state_funeral",
      "person_honored": {
        "name": "Full Name",
        "title": "Official Title", 
        "birth_date": "YYYY-MM-DD or null",
        "death_date": "YYYY-MM-DD or null"
      } or null,
      "event_details": {
        "event_name": "Event Name",
        "event_date": "YYYY-MM-DD", 
        "description": "Description"
      } or null,
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "duration_days": number,
      "proclamation_id": "unique-id-based-on-content",
      "proclamation_url": "https://whitehouse.gov/..."
    }
    
    If no active half-staff proclamations found, return status as "full_staff" with reason "No active proclamations".
    Make sure the proclamation_id is unique and based on the content (like "2025-01-carter-death").
    """

    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": search_prompt}],
                "tools": [{
                    "name": "web_search",
                    "description": "Search the web for information",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }]
            })
        )
        
        result = json.loads(response['body'].read())
        return extract_flag_data(result)
        
    except Exception as e:
        print(f"Error calling Bedrock: {str(e)}")
        return None

def extract_flag_data(bedrock_response):
    """
    Extract structured flag data from Bedrock response
    """
    try:
        # Parse the response content
        content = bedrock_response.get('content', [])
        
        # Look for JSON in the response
        json_data = None
        for item in content:
            if item.get('type') == 'text':
                text = item.get('text', '')
                # Try to extract JSON from the text
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group())
                    break
        
        if not json_data:
            # Fallback: try to parse entire response as JSON
            json_data = json.loads(str(bedrock_response))
        
        # Add timestamp
        json_data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        # Validate required fields
        if 'status' not in json_data:
            json_data['status'] = 'full_staff'
        if 'reason' not in json_data:
            json_data['reason'] = 'No active proclamations'
            
        return json_data
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing Bedrock response: {str(e)}")
        # Return safe default
        return {
            'status': 'full_staff',
            'reason': 'Unable to parse flag status',
            'proclamation_url': None,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }

def update_current_status(flag_data):
    """
    Update current.json in S3
    """
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='current.json',
            Body=json.dumps(flag_data, indent=2),
            ContentType='application/json'
        )
        print("Updated current.json")
    except Exception as e:
        print(f"Error updating current status: {str(e)}")
        raise

def update_index(flag_data):
    """
    Update index.json in S3
    """
    try:
        # Get existing index or create new one
        try:
            response = s3.get_object(Bucket=BUCKET_NAME, Key='index.json')
            index_data = json.loads(response['Body'].read())
        except s3.exceptions.NoSuchKey:
            index_data = {
                'active_proclamations': [],
                'recent_proclamations': []
            }
        
        proclamation_id = flag_data.get('proclamation_id')
        
        # Update active proclamations
        if flag_data.get('status') == 'half_staff' and proclamation_id:
            if proclamation_id not in index_data['active_proclamations']:
                index_data['active_proclamations'].append(proclamation_id)
        else:
            index_data['active_proclamations'] = []
        
        # Update recent proclamations
        if proclamation_id and proclamation_id not in index_data['recent_proclamations']:
            index_data['recent_proclamations'].insert(0, proclamation_id)
            # Keep only last 10 recent proclamations
            index_data['recent_proclamations'] = index_data['recent_proclamations'][:10]
        
        index_data['last_updated'] = flag_data.get('last_updated')
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='index.json',
            Body=json.dumps(index_data, indent=2),
            ContentType='application/json'
        )
        print("Updated index.json")
        
    except Exception as e:
        print(f"Error updating index: {str(e)}")
        raise

def save_proclamation(flag_data):
    """
    Save individual proclamation file
    """
    proclamation_id = flag_data.get('proclamation_id')
    if not proclamation_id:
        print("No proclamation ID, skipping individual save")
        return
    
    try:
        year = datetime.now().year
        key = f"proclamations/{year}/{proclamation_id}.json"
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(flag_data, indent=2),
            ContentType='application/json'
        )
        print(f"Saved proclamation: {key}")
        
    except Exception as e:
        print(f"Error saving proclamation: {str(e)}")
        # Don't raise - this is not critical