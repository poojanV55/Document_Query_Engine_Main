from langchain_aws import BedrockEmbeddings
from dotenv import load_dotenv 
import boto3
import os 

load_dotenv() 

os.environ['AWS_ACCESS_KEY_ID'] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ['AWS_DEFAULT_REGION'] = os.getenv("AWS_DEFAULT_REGION")


def get_embedding_function():
    bedrock = boto3.client(service_name='bedrock-runtime')
    embeddings = BedrockEmbeddings(client=bedrock)

    # embeddings = BedrockEmbeddings()
    return embeddings


