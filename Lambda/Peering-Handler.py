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
    
    callEvent = {}
    if "provider" in event['ResourceProperties']:
        callEvent["provider"] = event['ResourceProperties']["provider"]
    if "region" in event['ResourceProperties']:
        callEvent["region"] = event['ResourceProperties']["region"]
    if "awsAccountId" in event['ResourceProperties']:
        callEvent["awsAccountId"] = event['ResourceProperties']["awsAccountId"]
    if "vpcId" in event['ResourceProperties']:
        callEvent["vpcId"] = event['ResourceProperties']["vpcId"]
    if "vpcCidrs" in event['ResourceProperties']:
        callEvent["vpcCidrs"] = event['ResourceProperties']["vpcCidrs"]
        
    print ("callEvent that is used as the actual API Call is bellow:")
    print (callEvent)
        
    subscription_id = event['ResourceProperties']["subscriptionId"]
    
    print ("Subscription ID is: " + str(subscription_id))
    
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
                    
    if event['RequestType'] == "Create":
        try:
            responseValue = PostPeering(callEvent, subscription_id)
            print (responseValue)
            peer_id, peer_description = GetPeeringId (responseValue['links'][0]['href'])
            print ("New peering id is: " + str(peer_id))
            print ("Description for Peering with id " + str(peer_id) + " is: " + str(peer_description))
            
            responseData.update({"SubscriptionId":str(subscription_id), "PeeringId":str(peer_id), "PeeringDescription":str(peer_description), "PostCall":str(callEvent)})
            responseBody.update({"Data":responseData})
            GetResponse(responseURL, responseBody)
        
        except:
            peer_error = GetPeeringError (responseValue['links'][0]['href'])
            responseStatus = 'FAILED'
            reason = str(peer_error)
            if responseStatus == 'FAILED':
                responseBody.update({"Status":responseStatus})
                if "Reason" in str(responseBody):
                    responseBody.update({"Reason":reason})
                else:
                    responseBody["Reason"] = reason
                GetResponse(responseURL, responseBody)
                
    if event['RequestType'] == "Update":
        PhysicalResourceId = event['PhysicalResourceId']
        responseBody.update({"PhysicalResourceId":PhysicalResourceId})
        
        cf_sub_id, cf_event, cf_peer_id, cf_peer_description = CurrentOutputs()
        print ("There are the events:")
        print (callEvent)
        print (cf_event)
        print ("vpcCidrs:")
        print (str(callEvent["vpcCidrs"]))
        print type(cf_event["vpcCidrs"])
        print (str(cf_event["vpcCidrs"][0]))
        
        if callEvent["vpcCidrs"] != cf_event["vpcCidrs"]:
            responseValue = PutPeering(cf_sub_id, cf_peer_id, callEvent)
            cf_event = cf_event.replace("\'", "\"")
            cf_event = json.loads(cf_event)
            cf_event.update(callEvent)
            print (cf_event)
            responseData.update({"SubscriptionId":str(cf_sub_id), "PeeringId":str(cf_peer_id), "PeeringDescription":str(cf_peer_description), "PostCall":str(cf_event)})
            responseBody.update({"Data":responseData})
            GetResponse(responseURL, responseBody)
        
        else:
            responseData.update({"SubscriptionId":str(cf_sub_id), "PeeringId":str(cf_peer_id), "PeeringDescription":str(cf_peer_description), "PostCall":str(cf_event)})
            responseBody.update({"Data":responseData})
            GetResponse(responseURL, responseBody)
                
    if event['RequestType'] == "Delete":
        try:
            cf_sub_id, cf_event, cf_peer_id, cf_peer_description = CurrentOutputs()
        except:
            responseStatus = 'SUCCESS'
            responseBody.update({"Status":responseStatus})
            GetResponse(responseURL, responseBody)
            
        all_peers = GetPeering(cf_sub_id)
        if str(cf_peer_id) in str(all_peers):
            try:
                responseValue = DeletePeering(cf_sub_id, cf_peer_id)
                responseData.update({"SubscriptionId":str(cf_sub_id), "PeeringId":str(cf_peer_id), "PeeringDescription":str(cf_peer_description), "PostCall":str(cf_event)})
                print (responseData)
                responseBody.update({"Data":responseData})
                GetResponse(responseURL, responseBody)
            except:
                responseStatus = 'FAILED'
                reason = "Unable to delete peering"
                if responseStatus == 'FAILED':
                    responseBody.update({"Status":responseStatus})
                    if "Reason" in str(responseBody):
                        responseBody.update({"Reason":reason})
                    else:
                        responseBody["Reason"] = reason
                    GetResponse(responseURL, responseBody)
        else:
            print("Peering does not exists")
            GetResponse(responseURL, responseBody)

                    
def RetrieveSecret(secret_name):
    headers = {"X-Aws-Parameters-Secrets-Token": os.environ.get('AWS_SESSION_TOKEN')}

    secrets_extension_endpoint = "http://localhost:2773/secretsmanager/get?secretId=" + str(secret_name)
    r = requests.get(secrets_extension_endpoint, headers=headers)
    secret = json.loads(r.text)["SecretString"]
    secret = json.loads(secret)

    return secret
    
def CurrentOutputs():
    cloudformation = boto3.client('cloudformation')
    cf_response = cloudformation.describe_stacks(StackName=stack_name)
    for output in cf_response["Stacks"][0]["Outputs"]:
        if "SubscriptionId" in str(output): 
            cf_sub_id = output["OutputValue"]

        if "PostCall" in str(output): 
            cf_event = output["OutputValue"]

        if "PeeringId" in str(output): 
            cf_peer_id = output["OutputValue"]

        if "PeeringDescription" in str(output): 
            cf_peer_description = output["OutputValue"]
            
    print ("cf_sub_id is: " + str(cf_sub_id))
    print ("cf_event is: " + str(cf_event))
    print ("cf_peer_id is: " + str(cf_peer_id))
    print ("cf_peer_description is: " + str(cf_peer_description))
    return cf_sub_id, cf_event, cf_peer_id, cf_peer_description
    
def PostPeering (event, subscription_id):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings"
    
    response = requests.post(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key, "Content-Type":content_type}, json = event)
    response_json = response.json()
    return response_json
    Logs(response_json)
    
def GetPeering (subscription_id):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings"
    count = 0
    response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response = response.json()
    
    while "vpcPeeringId" not in str(response) and count < 30:
        time.sleep(1)
        count += 1
        print (str(response))
        response = requests.get(response['links'][0]['href'], headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
        response = response.json()
        
    print (response)
    return response
    Logs(response)
    
def GetPeeringId (url):
    response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response = response.json()
    print (str(response))
    count = 0
    
    while "resourceId" not in str(response) and count < 30:
        time.sleep(1)
        count += 1
        print (str(response))
        response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
        response = response.json()

    peer_id = response["response"]["resourceId"]
    peer_description = response["description"]
    return peer_id, peer_description
    
def PutPeering (subscription_id, peering_id, callEvent):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings/" + str(peering_id)
    
    response = requests.put(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key, "Content-Type":content_type}, json = callEvent)
    response_json = response.json()
    return response_json
    Logs(response_json)

def DeletePeering (subscription_id, peering_id):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings/" + str(peering_id)
    
    response_peer = requests.delete(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    Logs(response_peer.json())
    
def GetPeeringError (url):
    response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response = response.json()
    count = 0

    while "processing-error" not in str(response) and count < 30:
        time.sleep(1)
        count += 1
        response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
        response = response.json()

    peer_error_description = response["response"]["error"]["description"]
    return peer_error_description
    
def GetResponse(responseURL, responseBody): 
    responseBody = json.dumps(responseBody)
    req = requests.put(responseURL, data = responseBody)
    print ('RESPONSE BODY:n' + responseBody)
    
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
