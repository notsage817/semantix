import json
import os
from elasticsearch import Elasticsearch, helpers

def index_json_files(dir_path):
    for root, _, files in os.walk(dir_path):
        for filename in files:
            if filename.endswith(".json"):
                filepath = os.path.join(root, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"⚠️ Skipping invalid JSON: {filepath}")
                        continue
                try:
                    response = es.index(index=INDEX_NAME, document=data)
                    # Optional: print success for each doc
                    print(f"Indexed {filepath}: {response['_id']}")
                except Exception as e:
                    print(f"Failed to index {filepath}: {e}")
    print("indexing complete.")

if __name__ == '__main__':
    es = Elasticsearch("http://localhost:9200", verify_certs=False)
    # Name of the index
    INDEX_NAME = "jobs-json-embedding"

    # Create index if it doesn't exist
    if not es.indices.exists(index=INDEX_NAME):
        print(f"Index {INDEX_NAME} does not exist. Creating it.")
        mappings={
            "mappings": {
            "properties": {
                "qwen3_embedding": {
                    "type": "dense_vector",
                    "dims": 2560  # replace with your embedding dimension
                },
                "other_field": {
                    "type": "text"
                }
            }}}
        es.indices.create(index=INDEX_NAME)

    path_to_json_dir = "/home/hjx/elasticSearch/data/embedding_json"
    index_json_files(path_to_json_dir)