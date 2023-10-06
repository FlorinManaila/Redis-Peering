import boto3
import cfnresponse
import time
import json
import requests
import os
from os import environ

accept = "application/json"
content_type = "application/json"

def lambda_handler (event, context):
    
    print (event)
    
    global stack_name
    global base_url
    global x_api_key
    global x_api_secret_key 
    base_url = event['ResourceProperties']['baseURL']
    x_api_key =  RetrieveSecret("redis/x_api_key")["x_api_key"]
    x_api_secret_key =  RetrieveSecret("redis/x_api_secret_key")["x_api_secret_key"]
    stack_name = str(event['StackId'].split("/")[1])
    responseData = {}
    
    responseStatus = 'SUCCESS'
    responseURL = event['ResponseURL']
    responseBody = {'Status': responseStatus,
                    'PhysicalResourceId': context.log_stream_name,
                    'StackId': event['StackId'],
                    'RequestId': event['RequestId'],
                    'LogicalResourceId': event['LogicalResourceId']
                    }
    
   # if event['RequestType'] == "Create":
   #     try:
   #         responseValue = PostPeering(callEvent, subscription_id)
   #         print (responseValue) 
                    
def RetrieveSecret(secret_name):
    headers = {"X-Aws-Parameters-Secrets-Token": os.environ.get('AWS_SESSION_TOKEN')}

    secrets_extension_endpoint = "http://localhost:2773/secretsmanager/get?secretId=" + str(secret_name)
    r = requests.get(secrets_extension_endpoint, headers=headers)
    secret = json.loads(r.text)["SecretString"]
    secret = json.loads(secret)

    return secret
    
def PostPeering (event, subscription_id):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings"
    
    response = requests.post(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key, "Content-Type":content_type}, json = event)
    response_json = response.json()
    return response_json
    Logs(response_json)
    
def GetPeering (subscription_id):
    # If subscription_id string is empty, GET verb will print all Flexible Subscriptions
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings"
    
    response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response_json = response.json()
    return response_json
    Logs(response_json)
    
def PutPeering (subscription_id, event):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings" + str()
    print (event)
    
    update_dict = {}
    for key in list(event):
    	if key == "name":
    	    update_dict['name'] = event[key]
    	elif key == "paymentMethodId":
    	    update_dict['paymentMethodId'] = event[key]
    
    response = requests.put(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key, "Content-Type":content_type}, json = update_dict)
    print ("PutSubscription response is:")
    print(response)
    response_json = response.json()
    return response_json
    Logs(response_json)

#Deleting Subscription requires deleting the Database underneath it first    
def DeleteSubscription (subscription_id, database_id):
    db_url   = base_url + "/v1/subscriptions/" + subscription_id + "/databases/" + database_id
    subs_url = base_url + "/v1/subscriptions/" + subscription_id
    
    response_db   = requests.delete(db_url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response_subs = requests.delete(subs_url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    Logs(response_db.json())
    Logs(response_subs.json())
    
def Logs(response_json):
    error_url = response_json['links'][0]['href']
    error_message = requests.get(error_url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    error_message_json = error_message.json()
    if 'description' in error_message_json:
        while response_json['description'] == error_message_json['description']:
            error_message = requests.get(error_url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
            error_message_json = error_message.json()
        print(error_message_json)
    else:
        print ("No errors")
