import boto3
import json
import time
import os
import sys
import traceback

# Configuration
REGION = "us-east-1"
AWS_ACCOUNT_ID = "688567279995"  # Your AWS account ID
LAMBDA_FUNCTION_NAME = "RockPaperScissorsAI"
API_NAME = "RockPaperScissorsAPI"
S3_BUCKET_NAME = "rpsgame-bucket"  # S3 bucket names must be lowercase and can't contain underscores
LAMBDA_ZIP_FILE = "lambda.zip"

print("Setting up AWS resources for Rock Paper Scissors AI deployment...")

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=REGION)
iam_client = boto3.client('iam', region_name=REGION)
dynamodb_client = boto3.client('dynamodb', region_name=REGION)
apigateway_client = boto3.client('apigateway', region_name=REGION)
s3_client = boto3.client('s3', region_name=REGION)

# Step 1: Create DynamoDB table
print("Creating DynamoDB table...")
try:
    response = dynamodb_client.create_table(
        TableName='GameHistory',
        KeySchema=[
            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    print("DynamoDB table created.")
    # Wait for table to be active
    print("Waiting for table to become active...")
    dynamodb_client.get_waiter('table_exists').wait(TableName='GameHistory')
except dynamodb_client.exceptions.ResourceInUseException:
    print("DynamoDB table already exists, skipping...")
except Exception as e:
    print(f"Error creating DynamoDB table: {str(e)}")
    traceback.print_exc()

# Step 2: Create IAM role for Lambda
print("Creating IAM role...")
try:
    # Create trust policy JSON
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    role_response = iam_client.create_role(
        RoleName='RockPaperScissorsLambdaRole',
        AssumeRolePolicyDocument=json.dumps(trust_policy)
    )
    
    role_arn = role_response['Role']['Arn']
    print(f"Role created: {role_arn}")
    
    # Attach policies to the role
    iam_client.attach_role_policy(
        RoleName='RockPaperScissorsLambdaRole',
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    )
    
    iam_client.attach_role_policy(
        RoleName='RockPaperScissorsLambdaRole',
        PolicyArn='arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess'
    )
    print("Policies attached to role.")
    
    # Wait a bit for role propagation
    print("Waiting for role propagation...")
    time.sleep(10)
except iam_client.exceptions.EntityAlreadyExistsException:
    print("IAM role already exists, using existing role.")
    role_response = iam_client.get_role(RoleName='RockPaperScissorsLambdaRole')
    role_arn = role_response['Role']['Arn']
except Exception as e:
    print(f"Error creating IAM role: {str(e)}")
    traceback.print_exc()
    role_arn = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/RockPaperScissorsLambdaRole"

# Step 3: Create Lambda function
print("Creating Lambda function...")
try:
    with open(LAMBDA_ZIP_FILE, 'rb') as zip_file:
        lambda_response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime='python3.10',
            Role=role_arn,
            Handler='RockPaperScissor.app.handler',
            Code={'ZipFile': zip_file.read()},
            Timeout=30,
            MemorySize=256,
            Environment={
                'Variables': {
                    'USE_DYNAMODB': 'true'
                }
            }
        )
    lambda_arn = lambda_response['FunctionArn']
    print(f"Lambda function created: {lambda_arn}")
except lambda_client.exceptions.ResourceConflictException:
    print("Lambda function already exists, updating code...")
    with open(LAMBDA_ZIP_FILE, 'rb') as zip_file:
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_file.read()
        )
    # Get the Lambda function ARN after update
    lambda_func = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
    lambda_arn = lambda_func['Configuration']['FunctionArn']
    print(f"Lambda function updated: {lambda_arn}")
except Exception as e:
    print(f"Error with Lambda function: {str(e)}")
    traceback.print_exc()
    lambda_arn = f"arn:aws:lambda:{REGION}:{AWS_ACCOUNT_ID}:function:{LAMBDA_FUNCTION_NAME}"

# Step 4: Create API Gateway
print("Creating API Gateway...")
try:
    api_response = apigateway_client.create_rest_api(
        name=API_NAME,
        endpointConfiguration={'types': ['REGIONAL']}
    )
    api_id = api_response['id']
    print(f"API Gateway created: {api_id}")

    # Get the root resource ID
    resources = apigateway_client.get_resources(restApiId=api_id)
    root_id = resources['items'][0]['id']
    
    # Create a proxy resource
    proxy_resource = apigateway_client.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='{proxy+}'
    )
    resource_id = proxy_resource['id']
    
    # Set up ANY method
    apigateway_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='ANY',
        authorizationType='NONE'
    )
    
    # Construct the proper Lambda URI
    uri = f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
    print(f"Using Lambda URI: {uri}")
    
    # Integrate with Lambda
    apigateway_client.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='ANY',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=uri
    )
    
    # Create a deployment
    apigateway_client.create_deployment(
        restApiId=api_id,
        stageName='prod'
    )
    
    # Add Lambda permission for API Gateway
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId='apigateway-prod',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{REGION}:{AWS_ACCOUNT_ID}:{api_id}/prod/ANY/*'
        )
    except lambda_client.exceptions.ResourceConflictException:
        print("Lambda permission already exists, skipping...")
    
    # Print the API endpoint URL
    api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
    print(f"API Gateway URL: {api_url}")
    
    # Save URL to a file for reference
    with open("api_url.txt", "w") as f:
        f.write(api_url)
except Exception as e:
    print(f"Error creating API Gateway: {str(e)}")
    traceback.print_exc()

# Step 5: Create S3 bucket for frontend
print("Creating S3 bucket for frontend...")
try:
    # Create bucket - us-east-1 requires special handling
    if REGION == 'us-east-1':
        s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
    else:
        s3_client.create_bucket(
            Bucket=S3_BUCKET_NAME,
            CreateBucketConfiguration={'LocationConstraint': REGION}
        )
    print(f"S3 bucket created: {S3_BUCKET_NAME}")
    
    # Configure bucket for static website hosting
    s3_client.put_bucket_website(
        Bucket=S3_BUCKET_NAME,
        WebsiteConfiguration={
            'IndexDocument': {'Suffix': 'index.html'}
        }
    )
    
    s3_website_url = f"http://{S3_BUCKET_NAME}.s3-website-{REGION}.amazonaws.com"
    print(f"S3 website URL: {s3_website_url}")
    print("NOTE: The S3 bucket is private. To access the website, log into the AWS Console and:")
    print("1. Go to S3 > Buckets > rpsgame-bucket")
    print("2. Go to the 'Permissions' tab")
    print("3. Scroll down to 'Block public access (bucket settings)' and click 'Edit'")
    print("4. Uncheck 'Block all public access' and save changes")
    print("5. Scroll down to 'Bucket policy' and click 'Edit'")
    print("6. Paste the following policy (replacing YOUR_BUCKET_NAME):")
    print("""
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
            }
        ]
    }
    """.replace("YOUR_BUCKET_NAME", S3_BUCKET_NAME))
    
    # Save URL to a file for reference
    with open("s3_website_url.txt", "w") as f:
        f.write(s3_website_url)
except Exception as e:
    print(f"Error creating S3 bucket: {str(e)}")
    import traceback
    traceback.print_exc()

print("AWS setup complete!")