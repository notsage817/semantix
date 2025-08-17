import tritonclient.http as httpclient
import numpy as np
from elasticsearch import Elasticsearch 
import json

# Create the client connection
client = httpclient.InferenceServerClient(url="localhost:8000")

# Prepare the input data
text_to_embed = ["Find all marketing related positions."]

# Encode the string into bytes, as Triton's BYTES data type expects bytes
# The .encode('utf-8') method converts the string to a byte string
input_data = np.asarray([text_to_embed], dtype=object)

inputs = [
    httpclient.InferInput("Query", [1,1], "BYTES")
]

# Set the data from the numpy array
inputs[0].set_data_from_numpy(input_data)

# Run inference on the model
results = client.infer(model_name="Qwen3-Embedding-4B", inputs=inputs)

# Get the output and print it
# The output tensor name "OUTPUT0" must match your config.pbtxt
embedding = results.as_numpy("Embedding")
embedding_lst = embedding[0].tolist()
# print(embedding)
# print(embedding.shape)
k=5
query = {
    "knn": {
        "field": "qwen3_embedding", 
        "query_vector": embedding_lst, 
        "k": k
        }
    }
es_query = {
    'location':'Cupertion'
}

inputs = [
    httpclient.InferInput("ElasticsearchQuery", [1], "BYTES"),
    httpclient.InferInput("K",[1],"INT32"),
    httpclient.InferInput("Embedding",[1,2560],"FP32")
]
inputs[0].set_data_from_numpy(np.array([json.dumps(es_query).encode('utf-8')], dtype=object))
inputs[1].set_data_from_numpy(np.array([k], dtype=np.int32))
inputs[2].set_data_from_numpy(np.array(embedding_lst).astype(np.float32).reshape((1,2560)))
response=client.infer(model_name='es_fetcher', inputs=inputs)
responses=response.as_numpy('Responses')
print(responses[0])
# es = Elasticsearch("http://localhost:9200")
# result = es.search(index="jobs-json-embedding", body = {"query":query})
# jobs_found = []
# hits = result['hits']['hits']
# if hits:
#     for file in hits:
#         info = file['_source']
#         score = file['_score']
#         jobs_found.append({'job_id':info['job_id'], 
#                            'title':info['title'],
#                            'company':info['company'],
#                            'url':info['source_url']
#                            })
#     jobs=[]
#     for job in jobs_found:
#         jobs.append('{'+','.join(k+':'+v for k,v in job.items())+'}')
#     print('\n'.join(jobs))
# else:
#     print("Document not found") 