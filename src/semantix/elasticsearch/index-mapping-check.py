import os
import json
import collections

def validate_json_file(file_path, schema):
    """Loads a JSON file and validates its columns against a schema."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            document = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON in file '{file_path}'. Error: {e}")
        return False

    # Validate that all required keys from the schema exist in the document
    for key in schema.keys():
        if key not in document:
            print(f"ERROR in file '{file_path}': Missing required key '{key}'")
            return False
    unmatched_key=[]
    # Validate the data type of each key
    for key, value in document.items():
        if key in schema:
            expected_type = schema[key]['type']
            doc_type=determine_es_mapping_type(value)
            if doc_type != expected_type:
                unmatched_key.append([key, doc_type, expected_type])
    print(f"unsuccessful cause '{unmatched_key}'.")
    return True

def determine_es_mapping_type(column_values):
    """
    Analyzes a list of column values (representing a single column's data across documents)
    and suggests an appropriate Elasticsearch mapping type.

    This function handles:
    - Lists of values by inspecting the types of their elements.
    - Mixed types within a column or within a list.
    - None values, ignoring them for type determination.

    Args:
        column_values (list): A list of values found in a specific column
                              across multiple JSON documents.

    Returns:
        str or None: The suggested Elasticsearch mapping type (e.g., "text", "long",
                     "float", "boolean", "object"), or None if no definitive type
                     can be determined (e.g., empty list or all None values).
    """
    if not isinstance(column_values, list):
        if isinstance(column_values, str):
            return "text"
        if isinstance(column_values, bool):
            return "boolean"
        if isinstance(column_values, int):
            return "long"
        if isinstance(column_values, dict):
            return "object"
        if isinstance(column_values, float):
            return "float"

    if not column_values:
        return None

    # Filter out None values. We determine type based on actual data.
    non_none_values = [v for v in column_values if v is not None]

    if not non_none_values:
        return None # Column contains only None values or is empty after filtering

    # Track all unique observed Python types (including types inside lists)
    observed_python_types = set()

    for value in non_none_values:
        if isinstance(value, list):
            # If the value is a list, inspect its elements' types
            for item in value:
                if item is not None:
                    observed_python_types.add(type(item))
        else:
            # If the value is not a list, just add its type
            observed_python_types.add(type(value))

    # If no types were found after filtering (e.g., list of Nones like [None, None])
    if not observed_python_types:
        return None

    # Determine the most appropriate Elasticsearch type based on a type hierarchy:
    # object > float > long > boolean > string.
    # This ensures that if a column contains mixed types, the most general type is chosen.

    # 1. Prioritize 'object' if any dictionaries are present (or lists of dictionaries).
    # Elasticsearch will map lists of objects as 'object' by default.
    if dict in observed_python_types:
        return "object" # User might choose "nested" for deep querying

    # 2. Numeric types: 'float' takes precedence over 'long' if both are present.
    if float in observed_python_types:
        return "float"
    if int in observed_python_types:
        return "long"

    # 3. Boolean type
    if bool in observed_python_types:
        return "boolean"

    # 4. String type: 'text' for general-purpose full-text search.
    # 'keyword' would be used for exact matching or aggregation.
    if str in observed_python_types:
        return "text"

    # Fallback if none of the common types are found (e.g., custom Python objects)
    return None

if __name__ == "__main__":
    failed_str=['200605999__en-us_details_200605999_security-server-application-engineer-enterprise-technology-services.json',
                '114438158__en-us_details_114438158_us-specialist-full-time-part-time-and-part-time-temporary.json',
                '200612809__en-us_details_200612809_ai-data-integration-engineer.json', 
                '200603683__en-us_details_200603683_standards-architect-apple-pay.json',
                '200587242__en-us_details_200587242_embedded-regression-engineer.json', 
                '200597406__en-us_details_200597406_wireless-systems-validation-engineer-rf-systems-cellular.json']
    
    failed_str = '''
        Failed to index /home/hjx/elasticSearch/data/embedding_json/apple/.ipynb_checkpoints/200605999__en-us_details_200605999_security-server-application-engineer-enterprise-technology-services-checkpoint.json: BadRequestError(400, 'document_parsing_exception', 'Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY]', Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY])
        Failed to index /home/hjx/elasticSearch/data/embedding_json/apple/.ipynb_checkpoints/114438158__en-us_details_114438158_us-specialist-full-time-part-time-and-part-time-temporary-checkpoint.json: BadRequestError(400, 'document_parsing_exception', 'Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY]', Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY])
        Failed to index /home/hjx/elasticSearch/data/embedding_json/apple/.ipynb_checkpoints/200582913__en-us_details_200582913_machine-learning-engineer-machine-translation-automation-checkpoint.json: BadRequestError(400, 'document_parsing_exception', 'Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY]', Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY])
        Failed to index /home/hjx/elasticSearch/data/embedding_json/apple/.ipynb_checkpoints/200612809__en-us_details_200612809_ai-data-integration-engineer-checkpoint.json: BadRequestError(400, 'document_parsing_exception', 'Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY]', Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY])
        Failed to index /home/hjx/elasticSearch/data/embedding_json/apple/.ipynb_checkpoints/200603683__en-us_details_200603683_standards-architect-apple-pay-checkpoint.json: BadRequestError(400, 'document_parsing_exception', 'Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY]', Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY])
        Failed to index /home/hjx/elasticSearch/data/embedding_json/apple/.ipynb_checkpoints/200587242__en-us_details_200587242_embedded-regression-engineer-checkpoint.json: BadRequestError(400, 'document_parsing_exception', 'Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY]', Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY])
        Failed to index /home/hjx/elasticSearch/data/embedding_json/apple/.ipynb_checkpoints/200597406__en-us_details_200597406_wireless-systems-validation-engineer-rf-systems-cellular-checkpoint.json: BadRequestError(400, 'document_parsing_exception', 'Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY]', Failed to parse object: expecting token of type [VALUE_NUMBER] but found [START_ARRAY])
        Indexed /home/hjx/elasticSearch/data/embedding_json/apple/.ipynb_checkpoints/200605991__en-us_details_200605991_critical-facilities-technician-data-center-checkpoint.json: KCGprJgBa9OyvENqRFAa
    '''

    with open('mapping.json','r') as f:
        schema = json.load(f)
    expected_schema = schema["jobs-json-embedding"]["mappings"]["properties"]

    file_directory = "/home/hjx/elasticSearch/data/embedding_json/apple"
    for file in failed_str:
        print(file+'/n')
        full_path = os.path.join(file_directory, file)
        validate_json_file(full_path, expected_schema)
    
    print("Success References")
    for success in os.listdir(file_directory)[:5]:
        print(success+'/n')
        path = os.path.join(file_directory, success)
        validate_json_file(path, expected_schema)