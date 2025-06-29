import os
import sys
import shutil
from langchain.document_loaders.pdf import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from langchain.vectorstores.chroma import Chroma

from rag_app.get_embedding_function import get_embedding_function
from rag_app.get_chroma_db import get_chroma_db, get_runtime_chroma_path


CHROMA_PATH = os.environ.get("CHROMA_PATH", "data/chroma")
DATA_SOURCE_PATH = os.environ.get("DATA_SOURCE_PATH", "data/source")
IS_USING_IMAGE_RUNTIME = bool(os.environ.get("IS_USING_IMAGE_RUNTIME", False))


def main():

    clear_database()

    # Create (or update) the data store.
    documents = load_documents()
    chunks = split_documents(documents)
    add_to_chroma(chunks)


def load_documents():
    document_loader = PyPDFDirectoryLoader(f"/{DATA_SOURCE_PATH}")
    return document_loader.load()


def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=120,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)


def add_to_chroma(chunks: list[Document]):
    # Load the existing database.


    db = get_chroma_db()

    # Calculate Page IDs.
    chunks_with_ids = calculate_chunk_ids(chunks)
    for chunk in chunks:
        print(f"Chunk Page Sample: {chunk.metadata['id']}\n{chunk.page_content}\n\n")

    # Add or Update the documents.
    existing_items = db.get(include=[])  # IDs are always included by default
    existing_ids = set(existing_items["ids"])
    print(f"Number of existing documents in DB: {len(existing_ids)}")

    # Only add documents that don't exist in the DB.
    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    if len(new_chunks):
        print(f"👉 Adding new documents: {len(new_chunks)}")
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids, persist_directory=get_runtime_chroma_path())
        print(f"contents of {get_runtime_chroma_path()} path are : ", os.listdir(get_runtime_chroma_path()))
        for item in os.listdir(get_runtime_chroma_path()):
            item_path = os.path.join(get_runtime_chroma_path(), item)
            # print(item)
            if os.path.isdir(item_path) and len(item)>25:
                print(os.listdir(item_path))
                break

        # db.persist()

    else:
        print("✅ No new documents to add")


def calculate_chunk_ids(chunks):

    # This will create IDs like "data/monopoly.pdf:6:2"
    # Page Source : Page Number : Chunk Index

    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        # If the page ID is the same as the last one, increment the index.
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Calculate the chunk ID.
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Add it to the chunk meta-data.
        chunk.metadata["id"] = chunk_id

    return chunks


def clear_database():

    path = get_runtime_chroma_path()
    if os.path.exists(path):
        shutil.rmtree(path)


if __name__ == "__main__":
    main()
