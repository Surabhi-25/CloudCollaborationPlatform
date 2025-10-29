import json
import os
import uuid
from datetime import datetime, timedelta, timezone
import jwt # Requires PyJWT installed in Lambda environment
import boto3 # Standard AWS SDK

# --- CONFIGURATION ---
# IMPORTANT: These environment variables MUST be set in your Lambda configuration.
JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-key-for-signing-tokens-12345")
TOKEN_EXPIRATION_MINUTES = 60 * 24 # 24 hours
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "document-management-files-bucket-1234")

# RDS Data API Configuration (Aurora Serverless recommended)
# You must provision an RDS database and enable the Data API.
RDS_SECRET_ARN = os.environ.get("RDS_SECRET_ARN", "arn:aws:secretsmanager:REGION:ACCOUNT:secret:rds-doc-manager-secret")
RDS_CLUSTER_ARN = os.environ.get("RDS_CLUSTER_ARN", "arn:aws:rds:REGION:ACCOUNT:cluster:rds-doc-manager-cluster")
RDS_DATABASE = os.environ.get("RDS_DATABASE", "doc_manager_db")

# Initialize AWS clients
s3 = boto3.client('s3')
rds_data = boto3.client('rds-data')

# --- RDS DATA API HELPER ---

def execute_sql(sql: str, parameters: list = None, fetch_results: bool = True):
    """
    Executes SQL via the RDS Data API and handles parameter substitution.
    Assumes all fields are handled as STRING or numeric types in parameters.
    """
    try:
        response = rds_data.execute_statement(
            resourceArn=RDS_CLUSTER_ARN,
            secretArn=RDS_SECRET_ARN,
            database=RDS_DATABASE,
            sql=sql,
            parameters=parameters if parameters else [],
            includeResultMetadata=fetch_results,
        )
        
        if fetch_results:
            # Simple conversion from RDS Data API format to a list of dictionaries
            column_names = [col['label'] for col in response['columnMetadata']]
            results = []
            for record in response.get('records', []):
                item = {}
                for i, field in enumerate(record):
                    # Extract the value from the specific type key (stringValue, longValue, etc.)
                    key = list(field.keys())[0] if field else None
                    if key and field[key] is not None:
                        item[column_names[i]] = field[key]
                results.append(item)
            return results
        
        return response.get('numberOfRecordsUpdated', 0)
        
    except Exception as e:
        print(f"RDS Data API Error: {e}")
        # In a real application, you'd handle specific DB errors (e.g., duplicate key)
        raise

# --- JWT HANDLING HELPERS (NO CHANGE REQUIRED) ---

def generate_jwt(user_id: str, team_id: str):
    """Generates a signed JWT token."""
    now = datetime.now(timezone.utc)
    expiration = now + timedelta(minutes=timedelta.min)
    payload = {
        'exp': int(expiration.timestamp()),
        'iat': int(now.timestamp()),
        'user_id': user_id,
        'team_id': team_id,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str):
    """Decodes and validates a JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        print(f"Token decoding error: {e}")
        return None

# ==============================================================================
# 2.1 Develop and Deploy Auth Service (Lambda Handler)
# Handles: Registration, Login, Team Management (using RDS)
# ==============================================================================

def auth_service_handler(event, context):
    try:
        path = event.get('path')
        method = event.get('httpMethod')
        body = json.loads(event.get('body', '{}'))

        if path == '/register' and method == 'POST':
            return handle_register(body)
        elif path == '/login' and method == 'POST':
            return handle_login(body)
        # Note: Team management logic would also use execute_sql
        
        return {'statusCode': 404, 'body': json.dumps({'message': 'Not Found'})}

    except Exception as e:
        print(f"Auth Service Error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error'})}

def handle_register(data):
    """Registers a new user using an RDS INSERT query."""
    user_id = str(uuid.uuid4())
    username = data.get('username')
    password_hash = data.get('password') 
    
    if not username or not password_hash:
        return {'statusCode': 400, 'body': json.dumps({'message': 'Missing username or password'})}

    # SQL Insert statement
    sql = """
        INSERT INTO users (user_id, username, password_hash, created_at)
        VALUES (:user_id, :username, :password_hash, :created_at);
    """
    
    # Parameters for the Data API
    params = [
        {'name': 'user_id', 'value': {'stringValue': user_id}},
        {'name': 'username', 'value': {'stringValue': username}},
        {'name': 'password_hash', 'value': {'stringValue': password_hash}},
        {'name': 'created_at', 'value': {'stringValue': datetime.now(timezone.utc).isoformat()}},
    ]
    
    execute_sql(sql, params, fetch_results=False)
    
    return {
        'statusCode': 201,
        'body': json.dumps({'user_id': user_id, 'message': 'User registered successfully. Proceed to login.'})
    }

def handle_login(data):
    """Authenticates a user using an RDS SELECT query and generates a JWT token."""
    username = data.get('username')
    password = data.get('password')
    
    # 1. Retrieve user data
    sql = """
        SELECT user_id, password_hash, team_id
        FROM users
        WHERE username = :username;
    """
    params = [{'name': 'username', 'value': {'stringValue': username}}]
    
    users = execute_sql(sql, params)
    
    if not users:
        return {'statusCode': 401, 'body': json.dumps({'message': 'Invalid credentials'})}
        
    user = users[0]
    
    # 2. Check password (Placeholder: In production, compare securely hashed passwords)
    if user['password_hash'] != password: 
        return {'statusCode': 401, 'body': json.dumps({'message': 'Invalid credentials'})}

    # 3. Generate and sign the JWT
    token = generate_jwt(user_id=user['user_id'], team_id=user['team_id'])
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'user_id': user['user_id'],
            'team_id': user['team_id'],
            'token': token,
            'expires_in_minutes': TOKEN_EXPIRATION_MINUTES
        })
    }
# Team management functions removed for brevity, they would follow the same pattern.

# ==============================================================================
# 2.2 Develop and Deploy Custom Authorizer (Lambda Handler)
# Handles: JWT Validation and IAM Policy Generation (NO CHANGE REQUIRED)
# ==============================================================================

def custom_authorizer_handler(event, context):
    """
    AWS API Gateway Custom Authorizer Lambda handler.
    Receives JWT, validates it, and returns an IAM policy.
    """
    token = event.get('authorizationToken', '').split(' ')[-1]
    
    if not token:
        print("Authorization header missing or invalid format.")
        return generate_policy('user', 'Deny', event['methodArn'])
    
    payload = decode_jwt(token)
    
    if not payload:
        print("JWT Validation failed.")
        return generate_policy('user', 'Deny', event['methodArn'])

    user_id = payload.get('user_id', 'unknown')
    team_id = payload.get('team_id', 'none')
    
    return generate_policy(
        principal_id=user_id,
        effect='Allow',
        resource=event['methodArn'],
        context={'user_id': user_id, 'team_id': team_id}
    )

def generate_policy(principal_id, effect, resource, context=None):
    """Generates the IAM policy document structure required by API Gateway."""
    auth_response = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource,
            }]
        }
    }
    if context:
        auth_response['context'] = context
    return auth_response

# ==============================================================================
# 2.3 Develop and Deploy Metadata Service (Lambda Handler)
# Handles: CRUD for files, versions, and ACLs in RDS
# ==============================================================================

def metadata_service_handler(event, context):
    """Main handler for the Metadata Service."""
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('user_id')
    team_id = event.get('requestContext', {}).get('authorizer', {}).get('team_id')
    
    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'message': 'Access denied: User context missing.'})}

    try:
        path = event.get('path')
        method = event.get('httpMethod')
        body = json.loads(event.get('body', '{}'))
        
        if path == '/files' and method == 'POST':
            return handle_create_file(user_id, team_id, body)
        elif path.startswith('/files/') and method == 'GET':
            file_id = path.split('/')[-1]
            return handle_get_file_metadata(file_id)
        elif path.startswith('/versions') and method == 'POST':
            return handle_create_new_version(user_id, team_id, body)
        
        return {'statusCode': 404, 'body': json.dumps({'message': 'Metadata endpoint not found'})}
        
    except Exception as e:
        print(f"Metadata Service Error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error'})}


def handle_create_file(user_id, team_id, data):
    """Creates a new file metadata record and initial version entry using RDS."""
    file_id = str(uuid.uuid4())
    file_name = data.get('file_name', 'untitled')
    mime_type = data.get('mime_type', 'application/octet-stream')
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Default ACL (JSON field in RDS table)
    acl = json.dumps({
        user_id: ['READ', 'WRITE'],
        f'TEAM:{team_id}': ['READ']
    })
    
    # 1. Insert into files table
    sql_file = """
        INSERT INTO files (file_id, current_version_id, team_id, owner_user_id, file_name, created_at, updated_at, acl)
        VALUES (:file_id, 1, :team_id, :owner_user_id, :file_name, :created_at, :updated_at, :acl_json);
    """
    params_file = [
        {'name': 'file_id', 'value': {'stringValue': file_id}},
        {'name': 'team_id', 'value': {'stringValue': team_id}},
        {'name': 'owner_user_id', 'value': {'stringValue': user_id}},
        {'name': 'file_name', 'value': {'stringValue': file_name}},
        {'name': 'created_at', 'value': {'stringValue': now_iso}},
        {'name': 'updated_at', 'value': {'stringValue': now_iso}},
        {'name': 'acl_json', 'value': {'stringValue': acl}}, # Stored as JSON string/TEXT
    ]
    execute_sql(sql_file, params_file, fetch_results=False)
    
    # 2. Insert into versions table
    sql_version = """
        INSERT INTO versions (file_id, version_id, s3_key, mime_type, uploaded_by, created_at)
        VALUES (:file_id, 1, :s3_key, :mime_type, :uploaded_by, :created_at);
    """
    s3_key = f"{file_id}/v1/{file_name}"
    params_version = [
        {'name': 'file_id', 'value': {'stringValue': file_id}},
        {'name': 's3_key', 'value': {'stringValue': s3_key}},
        {'name': 'mime_type', 'value': {'stringValue': mime_type}},
        {'name': 'uploaded_by', 'value': {'stringValue': user_id}},
        {'name': 'created_at', 'value': {'stringValue': now_iso}},
    ]
    execute_sql(sql_version, params_version, fetch_results=False)

    return {
        'statusCode': 201,
        'body': json.dumps({
            'message': 'File created successfully.',
            'file_id': file_id,
            'version_id': 1,
            's3_key': s3_key
        })
    }

def handle_get_file_metadata(file_id):
    """Retrieves the latest metadata for a given file ID using RDS SELECT query."""
    sql = """
        SELECT file_id, current_version_id, team_id, owner_user_id, file_name, created_at, updated_at, acl
        FROM files
        WHERE file_id = :file_id;
    """
    params = [{'name': 'file_id', 'value': {'stringValue': file_id}}]
    
    items = execute_sql(sql, params)
    
    if not items:
        return {'statusCode': 404, 'body': json.dumps({'message': 'File not found'})}
        
    return {
        'statusCode': 200,
        'body': json.dumps(items[0])
    }

def handle_create_new_version(user_id, team_id, data):
    """Creates a new version record for an existing file using RDS."""
    file_id = data.get('file_id')
    file_name = data.get('file_name')
    mime_type = data.get('mime_type', 'application/octet-stream')
    
    # 1. Get current version ID
    sql_select = "SELECT current_version_id FROM files WHERE file_id = :file_id;"
    params_select = [{'name': 'file_id', 'value': {'stringValue': file_id}}]
    results = execute_sql(sql_select, params_select)
    
    if not results:
        return {'statusCode': 404, 'body': json.dumps({'message': 'File not found for versioning.'})}
        
    current_version_id = results[0]['current_version_id']
    new_version_id = current_version_id + 1
    now_iso = datetime.now(timezone.utc).isoformat()
    new_s3_key = f"{file_id}/v{new_version_id}/{file_name}"

    # 2. Update the file's current_version_id
    sql_update = """
        UPDATE files
        SET current_version_id = :new_version_id, updated_at = :now_iso
        WHERE file_id = :file_id;
    """
    params_update = [
        {'name': 'new_version_id', 'value': {'longValue': new_version_id}},
        {'name': 'now_iso', 'value': {'stringValue': now_iso}},
        {'name': 'file_id', 'value': {'stringValue': file_id}},
    ]
    execute_sql(sql_update, params_update, fetch_results=False)

    # 3. Create the new version record
    sql_insert_version = """
        INSERT INTO versions (file_id, version_id, s3_key, mime_type, uploaded_by, created_at)
        VALUES (:file_id, :version_id, :s3_key, :mime_type, :uploaded_by, :created_at);
    """
    params_insert = [
        {'name': 'file_id', 'value': {'stringValue': file_id}},
        {'name': 'version_id', 'value': {'longValue': new_version_id}},
        {'name': 's3_key', 'value': {'stringValue': new_s3_key}},
        {'name': 'mime_type', 'value': {'stringValue': mime_type}},
        {'name': 'uploaded_by', 'value': {'stringValue': user_id}},
        {'name': 'created_at', 'value': {'stringValue': now_iso}},
    ]
    execute_sql(sql_insert_version, params_insert, fetch_results=False)

    return {
        'statusCode': 201,
        'body': json.dumps({
            'message': 'New version record created.',
            'file_id': file_id,
            'version_id': new_version_id,
            's3_key': new_s3_key
        })
    }
    
# ==============================================================================
# 2.4 Develop and Deploy File Handler Service (Lambda Handler)
# Handles: Generating S3 Presigned URLs (Minimal Change)
# ==============================================================================

def file_handler_service_handler(event, context):
    """
    Main handler for the File Handler Service.
    Generates time-limited S3 Presigned URLs for upload or download.
    """
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('user_id')
    
    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'message': 'Access denied: User context missing.'})}

    try:
        body = json.loads(event.get('body', '{}'))
        
        action = body.get('action') # 'upload' or 'download'
        s3_key = body.get('s3_key') # The S3 path, e.g., 'file_id/v1/document.docx'
        
        if not action or not s3_key:
            return {'statusCode': 400, 'body': json.dumps({'message': 'Missing action or s3_key'})}

        # --- GENERATE PRESIGNED URL ---
        if action == 'upload':
            presigned_url = s3.generate_presigned_url(
                ClientMethod='put_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=300 # 5 minutes
            )
        elif action == 'download':
            presigned_url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=3600 # 1 hour
            )
        else:
            return {'statusCode': 400, 'body': json.dumps({'message': 'Invalid action. Must be upload or download.'})}
            
        return {
            'statusCode': 200,
            'body': json.dumps({'url': presigned_url, 'key': s3_key})
        }

    except Exception as e:
        print(f"File Handler Service Error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error'})}
