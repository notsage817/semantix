import json
import numpy as np
import triton_python_backend_utils as pb_utils
from elasticsearch import Elasticsearch

class TritonPythonModel:
    """Your Python model must inherit from TritonPythonModel to be
    instantiated by the Triton Inference Server.
    """

    def initialize(self, args):
        self.es=Elasticsearch("http://host.docker.internal:9200")
        self.index_name="jobs-json-embedding"

    def execute(self, requests):

        responses = []

        for request in requests:
            # Get input tensors
            # es_query_tensor = pb_utils.get_input_tensor_by_name(request, "ElasticsearchQuery")
            k_tensor = pb_utils.get_input_tensor_by_name(request, "K")
            embedding_tensor = pb_utils.get_input_tensor_by_name(request, "Embedding")

            # Validate inputs
            if k_tensor is None:
                return pb_utils.TritonError("Missing 'K' input.")
            if embedding_tensor is None:
                return pb_utils.TritonError("Missing 'Embedding' input.")

            # Decode inputs
            # es_queries = es_query_tensor.as_numpy().tolist()
            ks = k_tensor.as_numpy().tolist()
            embeddings = embedding_tensor.as_numpy()
            query = {"knn": {
                        "field": "qwen3_embedding", 
                        "query_vector": embeddings[0].tolist(), 
                        "k": ks[0]
                        }
                    }
            response = self.es.search(index=self.index_name, 
                                        size=ks[0],
                                        body={"query": query}
                                    )
            if response['hits']['hits']:
                jobs_found=[]
                jobs=[]
                for file in response['hits']['hits']:
                    info = file['_source']
                    score = file['_score']
                    jobs_found.append({'job_id':info['job_id'], 
                                    'title':info['title'],
                                    'company':info['company'],
                                    'score':score,
                                    'url':info['source_url']
                                    })
            else:
                return ValueError
                
            for job in jobs_found:
                jobs.append('{'+','.join(str(k)+':'+str(v) for k,v in job.items())+'}')
            results='/n'.join(jobs)
            output_data = np.array([results.encode('utf-8')], dtype=object)
            output_tensor = pb_utils.Tensor("Responses", output_data)
            response = pb_utils.InferenceResponse(output_tensors=[output_tensor])
            responses.append(response)
        return responses

    def finalize(self):
        """`finalize` is called only once when the model is being unloaded.
        Implementing `finalize` is optional. This method allows you to
        clean up any resources created in `initialize`.
        """
        print('Cleaning up es_fetcher...')
        # Close Elasticsearch client or other resources here
