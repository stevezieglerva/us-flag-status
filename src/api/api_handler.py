import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    """
    Main Lambda handler for API Gateway requests
    """
    try:
        path = event.get('path', '')
        http_method = event.get('httpMethod', 'GET')
        path_params = event.get('pathParameters') or {}
        
        print(f"Processing {http_method} request for path: {path}")
        
        if path == '/api/v1/status/current':
            return get_current_status()
        elif path == '/api/v1/proclamations':
            return get_proclamations()
        elif path.startswith('/api/v1/proclamations/'):
            proclamation_id = path_params.get('id')
            return get_proclamation(proclamation_id)
        else:
            return create_response(404, {'error': 'Not found'})
            
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})

def get_current_status():
    """
    Get current flag status from S3
    """
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key='current.json')
        data = json.loads(response['Body'].read())
        return create_response(200, data)
        
    except s3.exceptions.NoSuchKey:
        # No current status file exists, return default
        default_status = {
            'status': 'full_staff',
            'reason': 'No active proclamations',
            'proclamation_url': None,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        return create_response(200, default_status)
        
    except Exception as e:
        print(f"Error getting current status: {str(e)}")
        return create_response(500, {'error': 'Failed to retrieve current status'})

def get_proclamations():
    """
    Get index of all proclamations
    """
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key='index.json')
        data = json.loads(response['Body'].read())
        return create_response(200, data)
        
    except s3.exceptions.NoSuchKey:
        # No index file exists, return empty
        default_index = {
            'active_proclamations': [],
            'recent_proclamations': [],
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        return create_response(200, default_index)
        
    except Exception as e:
        print(f"Error getting proclamations index: {str(e)}")
        return create_response(500, {'error': 'Failed to retrieve proclamations'})

def get_proclamation(proclamation_id):
    """
    Get specific proclamation by ID
    """
    if not proclamation_id:
        return create_response(400, {'error': 'Proclamation ID required'})
    
    try:
        # Search for proclamation in year-based directories
        paginator = s3.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix='proclamations/'):
            for obj in page.get('Contents', []):
                if proclamation_id in obj['Key']:
                    response = s3.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                    data = json.loads(response['Body'].read())
                    return create_response(200, data)
        
        return create_response(404, {'error': 'Proclamation not found'})
        
    except Exception as e:
        print(f"Error getting proclamation {proclamation_id}: {str(e)}")
        return create_response(500, {'error': 'Failed to retrieve proclamation'})

def create_response(status_code, body):
    """
    Create standardized API Gateway response
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(body, indent=2)
    }