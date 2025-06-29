from dataclasses import dataclass
from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
import boto3
from rag_app.get_chroma_db import get_chroma_db, get_runtime_chroma_path
from langchain_community.vectorstores import Chroma

from dotenv import load_dotenv 
import os 

load_dotenv() 

os.environ['AWS_ACCESS_KEY_ID'] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ['AWS_DEFAULT_REGION'] = os.getenv("AWS_DEFAULT_REGION")

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"


@dataclass
class QueryResponse:
    query_text: str
    response_text: str
    sources: List[str]


def query_rag(query_text: str, chroma_db: Chroma) -> QueryResponse:

    db = chroma_db
    print(f"contents of {get_runtime_chroma_path()} are : ", os.listdir(get_runtime_chroma_path()))
    for item in os.listdir(get_runtime_chroma_path()):
        item_path = os.path.join(get_runtime_chroma_path(), item)
        # print(item)
        if os.path.isdir(item_path) and len(item)>25:
            print(os.listdir(item_path))
            break
    # Search the DB.
    results = db.similarity_search_with_score(query_text, k=3)
    print("----------", results)
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    print(prompt)

    bedrock = boto3.client(service_name='bedrock-runtime')
    model = ChatBedrock(model_id=BEDROCK_MODEL_ID, client = bedrock)
    response = model.invoke(prompt)
    response_text = response.content

    sources = [doc.metadata.get("id", None) for doc, _score in results]
    print(f"Response: {response_text}\nSources: {sources}")

    return QueryResponse(
        query_text=query_text, response_text=response_text, sources=sources
    )


# if __name__ == "__main__":
#     query_rag("How much does a landing page cost to develop?")
