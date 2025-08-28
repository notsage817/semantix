import os
import json
from elasticsearch import Elasticsearch

if __name__ == '__main__':
    # Get index mapping in elasticSearch
    es = Elasticsearch("http://localhost:9200")

    # mapping = es.indices.get_mapping(index="jobs-json-embedding")
    # with open('mapping.json','w') as f:
    #     json.dump(mapping.body, f, indent=4)

    result = es.search(index="jobs-json-embedding", 
                       query={"knn": {"field": vector_field, "query_vector": qwen3_embedding, "k": k}})
    hits = result['hits']['hits']
    if hits:
        print(f"{len(hits)} documents found!\n")
        # print("Document found:", hits[0]['_source'])
    else:
        print("Document not found") 