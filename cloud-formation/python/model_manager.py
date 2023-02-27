import json
import lambda_multiprocessing
import asyncio
from url_methods import *
from constants import *

def get_from_schema(schema, item):
    """
    Get the data value asociated with an specific field from a data item

    Params:
      schema: The schema or field name
      item: the data record
    Return:
        The field value from the record if the field exists in the data item.
    """
    if schema is None:
        return None
    fields=schema.split(".")
    while len(fields) > 0:
        field = fields.pop(0)
        if field not in item:
            return None
        item = item.get(field)
        if item == "":
            return None
    return item

def get_from_model_table(model, field, item):
    """
    Get the data value asociated with an specific field from a table inside the
    model

    Params:
      schema: The schema or field name
      lookup: the section of schema that defines the rules to extract the value
              from item
      item: the data record
    Return:
        The field value from the array
    """
    return model.get_from_table(field ,item)

def get_from_array(schema, lookup, item):
    """
    Get the data value asociated with an specific field from an array of items

    Params:
      schema: The schema or field name
      lookup: the section of schema that defines the rules to extract the value
              from item
      item: the data record
    Return:
        The field value from the array
    """
    item_array = get_from_schema(schema, item)
    ndx = int(lookup.get("field"))
    return item_array[ndx]

def function_error():
    """
    Return:
        Error string when the schema doesn't matches
        any expected type
    """
    return ERR_UNEXPECTED_SCHEMA_TYPE

def function_null():
    """
    Return:
        Null value 
    """
    return NULL

def get_function_from_schema(schema, item):
    """
    Provide the specific function based on the schema section provided

    Params:
        schema: The section of the schema with the definition of the field
        item: The data item to be used along with schema to identify which
              function required

    Return: The function that matches the schema for that specific item field
    """
    field = schema.get("field")
    lookup = schema.get("lookup")
    if field == "":
        return function_null
    if not lookup:
        return get_from_schema
    else:
        schema_type = lookup.get("type")
        if schema_type == "table":
            return get_from_model_table
        elif schema_type == "array":
            return get_from_array
        elif schema_type == "url":
            return get_from_url
        else:
            return function_error

def get_results(model, function_field, item):
    """
    Apply the function asociated for each field to the item to
    extract the return value

    Params:
      model: The model schema with tables to extract from
      function_field: Contains the function and the section of the schema
                      with the rules to obtain the value for that field
      item: the data item to obtain the value from
    Return: The return value for the piece of data either original or altered
             and an error string where None or empty means no error
    """
    function, item_schema = function_field
    if "get_from_schema" in function.__name__:
        return function(item_schema.get("field"), item)
    elif "get_from_model_table" in function.__name__:
        return function(model, item_schema.get("field"), item)
    elif "get_from_array" in function.__name__:
        field = item_schema.get("field")
        lookup = item_schema.get("lookup")
        return function(field, lookup, item)
    elif "function_null" in function.__name__:
        return function()
    else:
        return function_error()

def validate_against_schema(value, definition):
    """
    Validate a piece of data with its asociated section in the schema

    Params:
      value: The data value to be evaluated
      definition: The specific schema section to validatethe value

    Return: The return value for the piece of data either original or altered
             and an error string where None or empty means no error
    """
    if value is not None and value != NULL:
        data_type = definition.get("type")
        if data_type == "string":
            if not isinstance(value, str):
                if not isinstance(value, int):
                    return value, ERR_INVALID_STRING
                else:
                    value = str(value)
        elif data_type == "number":
            try:
                val = float(value)
            except:
                return value, ERR_INVALID_NUMBER
            minimum = definition.get("minimum")
            maximum = definition.get("maximum")
            if (val < minimum) or (val > maximum):
                return val, ERR_NUMBER_OUT_OF_RANGE
            return val, ""
        elif data_type == "array":
            if not isinstance(value,list):
                if type(value) == int:
                    value = str(value)
                value = value.split(",")
            min_items = definition.get("minItems")
            items = definition.get("items")
            try:
                m_items = int(min_items)
            except:
                m_items = 0
            # Match each item in the data list against the list in schema
            if isinstance(items, list):
                for i in range(m_items):
                    val, error = validate_against_schema(value[i], items[i])
                    if error != "":
                        value[i] = f"{value[i]} - {error}"
                    else:
                        value[i] = val
            else:
                # Match the data list against the type of list in
                for i in range(len(value)):
                    val, error = validate_against_schema(value[i], items)
                    if error != "":
                        value[i] = f"{value[i]} - {error}"
                    else:
                        value[i] = val
        else:
            error = ERR_UNEXPECTED_TYPE

    return value, ""

def get_data_layer(schema, data):
    """
    Go down through the layers of data to reach the data level
    based on the schema on each service

    Params:
      schema: The schema with the data structure needed
      data: The raw data read from the service

    Return: The the section of the schema for the data transformation and
             the layer of data where is the required information 
    """
    schema_out = schema.get("lookup").get("out")
    structure = schema_out.get("structure")
    if structure.get("type")=="dict":
        key = structure.get("key")
        data_fields_layer = data.get(key)
    else:
        data_fields_layer = data
    schema_fields_layer = schema_out.get("data")
    return schema_fields_layer, data_fields_layer

def get_functions(schema, item):
    """
    Based on the schema and one item from the load, get the set of 
    functions to be applied to each field

    Params:
      schema: The schema (or part of it) that applies to the field
      item: An item to match the schema with, to identify the function that
            applies for each field

    Return: the set of functions and schemas to apply on each field
    """
    #  in schema from first data item
    functions_by_field = {}
    for key in schema:
        schema_field = schema.get(key)
        if isinstance(schema_field, dict):
            schema_function = get_function_from_schema(schema_field, item)
            functions_by_field[key] = [(schema_function, schema_field)]
        else:
            functions_by_field[key] = []
            for item_schema in schema_field:
                schema_function = get_function_from_schema(item_schema, item)
                functions_by_field[key].append((schema_function, item_schema))
    return functions_by_field

async def apply_service_schema(service, model, functions_by_field, data_item):
    """
    Extract the required information from each item based on the service model

    Params:
      service: The name of the service to be added at the begging of each item
      model: The model schema with tables to extract from
      function_by_field: the list of field functions
      data_item: The item to be affected by the functions

    Return: A restructured new item matching the output requirements
    """
    item = {'key': service}
    for key in functions_by_field:
        functions = functions_by_field.get(key)
        if len(functions) == 1:
            item[key] = get_results(model, functions[0], data_item)
        else:
            result_list = []
            for function_field in functions:
                result_list.append(get_results(model, 
                                   function_field, 
                                   data_item))
            item[key] = result_list
    return item

def apply_out_schema(parameters_tuple):
    """
    Validate the data item against the output-api-schema

    Params:
      parameters_tuple:
        schema_items: list with all the output items
        schema_required: list with all required items
        item: the item item data to be validated

    Return: The item affected by the model where either absent default values
             or data errors are point out 
    """
    schema_items, schema_required, item = parameters_tuple
    for key in schema_items:
        value = item.get(key)
        # Validate required parameters
        if (key in schema_required) and (value is None):
            value = ERR_ATTRIBUTE_NOT_FOUND
            item[key] = value
        else:
            # Validate value against schema
            key_definition = schema_items.get(key)
            val, schema_error = validate_against_schema(value,
                                                        key_definition)
            if schema_error:
                item[key] = f"{value} - {schema_error}"
            else:
                item[key] = val
    return item

def items_from_service(service, model, schema_items, schema_required, load):
    """
    Based on the output schema and api-out schema, return the formated
    data using multiprocessing to accelerate the task

    Params:
      service: The name of the service to put it ahead of the item's data
      model: The model schema with tables to extract from
      schema_items: the section of the out-api schema to process the data layer
      schema_required: The section of the out-api schema to validate the
                       prescence of 'required' fields in the data layer
      load: The input set of data items

    Return: A set of output items standarized and validated
    """
    list_to_process = []
    loads = []
    schema = model.get_schema()
    schema_layer, data_layer = get_data_layer(schema, load)
    # Identify the process by field
    if len(data_layer) > 0:
        functions_by_field = get_functions(schema_layer, data_layer[0])
        # Readjust the item's data based on the service's schema
        for data_item in data_layer:
            item = asyncio.run(
                apply_service_schema(service, model,
                                     functions_by_field,
                                     data_item))
            # Add the item to the list for the next process
            list_to_process.append((schema_items, schema_required, item))
        num =len(list_to_process)
        # Apply the 'generic' out-api-schema to the item
        with lambda_multiprocessing.Pool(num) as process:
            loads = process.map(apply_out_schema, list_to_process)
    return loads
