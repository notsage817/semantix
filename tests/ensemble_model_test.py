import tritonclient.http as httpclient
import numpy as np
from elasticsearch import Elasticsearch 
import json
import ast
import fitz

# Create the client connection
client = httpclient.InferenceServerClient(url="localhost:8000")

# Prepare the input data
# text_to_embed = ["Find all machine leaning related positions at Google."]
# k=30

# Read a pdf file as query
file = "/home/hjx/workspace/semantix/tests/test_resume.pdf"
doc = fitz.open(file)

content = []
for page in doc:
    content += page.get_text()
print(content[0])
k=10
es_query={}
text_to_embed=[''.join(content)]
inputs = [
    httpclient.InferInput("Query", [1,1], "BYTES"),
    httpclient.InferInput("ElasticsearchQuery", [1], "BYTES"),
    httpclient.InferInput("K",[1],"INT32")
]

inputs[0].set_data_from_numpy(np.asarray([text_to_embed], dtype=object))
inputs[1].set_data_from_numpy(np.array([json.dumps(es_query).encode('utf-8')], dtype=object))
inputs[2].set_data_from_numpy(np.array([k], dtype=np.int32))

response=client.infer(model_name='searcher', inputs=inputs)
responses=response.as_numpy('Responses')

results=[json.loads(f) for f in responses]
print([job for job in results])