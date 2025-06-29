
import os
import uvicorn
import boto3
import json

from fastapi import FastAPI, File, UploadFile
from mangum import Mangum
from pydantic import BaseModel
from query_model import QueryModel
from rag_app.query_rag import query_rag
from populate_database import main

from rag_app.get_embedding_function import get_embedding_function
from rag_app.get_chroma_db import get_chroma_db, get_runtime_chroma_path

from dotenv import load_dotenv 
import os 

load_dotenv() 
BUCKET_NAME = os.environ.get("BUCKET_NAME", "my-chroma-bucket226")

WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", None)
IS_USING_IMAGE_RUNTIME = bool(os.environ.get("IS_USING_IMAGE_RUNTIME", False))

app = FastAPI()
handler = Mangum(app)  # Entry point for AWS Lambda.

CHROMA_PATH = os.environ.get("CHROMA_PATH", "data/chroma")
DATA_SOURCE_PATH = os.environ.get("DATA_SOURCE_PATH", "data/source")


class SubmitQueryRequest(BaseModel):
    query_text: str


@app.get("/")
def index():
    return {"Hello": "World"}


@app.get("/get_query")
def get_query_endpoint(query_id: str) -> QueryModel:
    query = QueryModel.get_item(query_id)
    return query

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    
    pdf_content = await file.read()

    if IS_USING_IMAGE_RUNTIME:
        os.chdir('/')
        os.makedirs(f"{DATA_SOURCE_PATH}", exist_ok=True)
        dir_path = f"{DATA_SOURCE_PATH}/pdf_file.pdf"
    else: 
        dir_path = f"{DATA_SOURCE_PATH}/pdf_file.pdf"

    with open(dir_path, 'wb') as f:
        f.write(pdf_content)

    pdf_file = open(dir_path, 'rb')
    os.chdir("/var/task/")
    main()
    pdf_file.close()

    print('Done Processing pdf -----------')
    return {"status": "PDF processed"}


@app.post("/submit_query")
def submit_query_endpoint(request: SubmitQueryRequest) -> QueryModel:
    # Create the query item, and put it into the data-base.
    new_query = QueryModel(query_text=request.query_text)
    s3 = boto3.client('s3') 

    object_name = "chroma.sqlite3"
    os.chdir('/')
    file_name = f"{CHROMA_PATH}/chroma.sqlite3"
    bucket = BUCKET_NAME
    s3.upload_file(file_name, bucket, object_name)
    os.chdir("/var/task/")

    if WORKER_LAMBDA_NAME:
        # Make an async call to the worker (the RAG/AI app).
        new_query.put_item()
        invoke_worker(new_query)
    else:
        # Make a synchronous call to the worker (the RAG/AI app).
        query_response = query_rag(request.query_text, get_chroma_db())
        new_query.answer_text = query_response.response_text
        new_query.sources = query_response.sources
        new_query.is_complete = True
        new_query.put_item()

    return new_query


def invoke_worker(query: QueryModel):
    # Initialize the Lambda client
    lambda_client = boto3.client("lambda")

    # Get the QueryModel as a dictionary.
    payload = query.model_dump()

    # Invoke another Lambda function asynchronously
    response = lambda_client.invoke(
        FunctionName=WORKER_LAMBDA_NAME,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )

    print(f"✅ Worker Lambda invoked: {response}")


if __name__ == "__main__":
    # Run this as a server directly.
    port = 8000
    print(f"Running the FastAPI server on port {port}.")
    uvicorn.run("app_api_handler:app", host="0.0.0.0", port=port)

    # # Define the folder path
    # folder_path = 'image/src/data/source'

    # print(os.listdir(os.getcwd()))

    # # Check if the directory exists
    # if os.path.isdir(folder_path):
    #     print(f"The directory '{folder_path}' exists.")
    # else:
    #     print(f"The directory '{folder_path}' does not exist.")
