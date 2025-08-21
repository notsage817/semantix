import triton_python_backend_utils as pb_utils
import json
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F

class TritonPythonModel:
    """Your Python model must inherit from `TritonPythonModel`."""

    def initialize(self, args):
        """`initialize` is called once when the model is loaded."""
        model_config = json.loads(args['model_config'])
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained("/models/Qwen3-Embedding-4B", trust_remote_code=True)
        self.model = AutoModel.from_pretrained("/models/Qwen3-Embedding-4B",
                                               device_map="auto",
                                               torch_dtype=torch.float16,
                                               trust_remote_code=True)
        
        self.model.eval() # Set model to evaluation mode
        self.model.to(self.device)
    

    def execute(self, requests):
        """`execute` is called by the Triton Inference Server for every inference request."""
        responses = []
        for request in requests:
            # Get the input tensor
            input_texts_tensor = pb_utils.get_input_tensor_by_name(request, "Query")
            if input_texts_tensor is None:
                return pb_utils.TritonError("Input tensor 'Query' not found.")

            # Decode bytes to strings
            input_texts = [t.decode('utf-8') for t in input_texts_tensor.as_numpy().flatten()]

            input_encoded = self.tokenizer(input_texts, padding=True, truncation=True, 
                                         max_length=self.tokenizer.model_max_length, return_tensors="pt",
                                         ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**input_encoded)

            # --- Last-Token Pooling Logic ---
            # Get the last hidden state of the model.
            last_hidden_state = outputs.last_hidden_state.to(torch.float32)

            # Find the position of the last non-padding token for each sequence in the batch.
            # `attention_mask` is a tensor of 1s (for real tokens) and 0s (for padding).
            attention_mask = input_encoded['attention_mask']

            # Get the index of the last non-padding token
            # torch.sum() along dimension 1 gives the number of real tokens for each sequence.
            # Subtracting 1 gives the index of the last token (since indexing is 0-based).
            last_token_indices = torch.sum(attention_mask, dim=1) - 1

            # Use advanced indexing to get the hidden state of the last token for each sequence
            # `torch.arange(last_hidden_state.shape[0])` creates a tensor [0, 1, 2, ...]
            # which corresponds to the batch dimension.
            batch_indices = torch.arange(last_hidden_state.shape[0])
            last_token_embeddings = last_hidden_state[batch_indices, last_token_indices, :]

            # Create a Triton output tensor
            output_tensor = pb_utils.Tensor('Embedding', last_token_embeddings.detach().cpu().numpy())

            # Create the inference response
            response = pb_utils.InferenceResponse(output_tensors=[output_tensor])
            responses.append(response)
        return responses

    def finalize(self):
        """`finalize` is called once when the model is unloaded."""
        del self.model
        print('Cleaning up...')