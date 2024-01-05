import json
import asyncio
import lambda_multiprocessing
from url_methods import *
from constants import *

# tables from json service url
service_tables = {'generic': {}, 'province': {}}

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

def get_from_table(table_params, field, lookup, item):
    """
    Get the data value asociated with an specific field from a table inside the
    model

    Params:
      table_params:
        tables: The lookup tables for specific fields in schema
        lang: The lang for the search
        table_update: missing codes to update
      field: the nested fields to access the code
      lookup: type and field source to update (description or term)
      item: the data record
    Return:
        The string corresponding to that table, code, language
    """
    tables, lang, table_update = table_params
    table_name = field.split('.')[0]
    code = get_from_schema(field, item)
    if code is None:
        return 'undefined'
    # category table lookup french only (nominatim key)
    if table_name == 'category' and lang == 'en':
        return code.capitalize()

    codes = code.split(',') # in rare cases 2 values
    for code in codes:
        if code in tables.get(table_name):
           return tables.get(table_name).get(code).get(lang)

    # missing code in table
    print('missing code=', code, ' lang=', lang, 'field=', field, 'item=', item)
    term_en = get_table_code(tables, table_name, lookup, code, 'en')
    term_fr = get_table_code(tables, table_name, lookup, code, 'fr')
    term = {'en' : term_en, 'fr' : term_fr}

    # add missing code to table
    if term_en != 'undefined' and term_fr != 'undefined':
        tables[table_name][code] = term
        table_update[table_name][code] = term

    return term.get(lang)

def get_table_code(tables, table_name, lookup, code, lang):
    """
    get missing code definition from service url
    Params:
      tables: The lookup tables
      table_name: name of table, generic, province or tableurl
      lookup: type and field source (description or term)
      code: The missing code
      lang: The lang of the missing code
    Return:
        The term or description of the missing code for the lang 
    """

    if table_name not in service_tables:
        return 'undefined'

    if lang not in service_tables[table_name]:
        if 'tableurl' in tables:
            table_url = tables.get('tableurl').get(table_name).get(lang)
            print(table_name, 'table', lang, 'update url=', table_url)
            try:
                params = None
                service_tables[table_name][lang] = url_request(table_url, params)
            except Exception as error:
                print("An exception occurred:", type(error).__name__)
                print('Error=', error, ' url:', table_url)
                return 'undefined'
        else: 
            print('tableurl.csv missing from S3 bucket')
            return 'undefined'

    if 'definitions' in service_tables[table_name][lang]:
        definitions = service_tables[table_name][lang].get('definitions')
        for definition in definitions:
            if definition.get('code') == code:
                return definition.get(lookup.get('field'))

    return 'undefined'

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

def get_from_search(field, search_field, contains, return_field, item):
    """
    Get the data value asociated with an specific field from an array of items
    where the item has the searched value 

    Params:
      field: The field where the list is placed in the data item
      search_field: the field to search on
      contains. The value to match the search with
      return_field. the field containg the returning value
      item: the data record
    Return:
        The 'field' value from the sub-item containing the matching string in
        the search field.
    """
    sub_items = get_from_schema(field, item)
    for sub_item in sub_items:
        if contains in get_from_schema(search_field, sub_item):
            return sub_item.get(return_field)
    return None

def get_average(schema, index_list, item):
    """
    Get the average of a set of values from a numeric array

    Params:
      schema: The schema or field name
      indexes: A list with positions of each value for the addition
      item: the data record
    Return:
        The average of the specified values inside the list
    """
    total = 0.0
    addends = len(index_list)
    if addends < 1:
        return total
    item_array = get_from_schema(schema, item)
    for ndx in index_list:
        total += item_array[ndx]
    return total/addends

def get_from_csv(table_params, field, lookup, item):
    """
    Search for province or location name in csv string

    Params:
      table_params:
        tables: The lookup tables for specific fields in schema
        lang: The lang for the search
        table_update: missing codes to update
      field: The schema or field name
      lookup: the number of fields in the csv string to search
      item: the data record
    Return:
        The province or location name
    """
    tables, lang, table_update = table_params
    item_value = get_from_schema(field, item)
    item_list = item_value.split(',')
    search_field =  lookup.get("field")
    search_range =  int(lookup.get("range"))

    if search_field == 'province':
        if 'component' in tables:
            item_list.reverse() # search from end of csv string
            provinces = tables.get('component')
            for province in provinces:
                province_name = provinces.get(province).get(lang)
                if province_name:
                    for key in range(search_range):
                        if key < len(item_list):
                            if province_name in item_list[key]:
                                return province_name

    if search_field == 'name':
        if search_range <= len(item_list):
            name_list = item_list[:search_range]  # list slice
            name = ','.join(name_list)
            return name

    return 'undefined'

def get_from_type(table_params, field, lookup, item):
    """
    Get name or tag depending on type field for locate key (Geoname, street, intersection, etc)

    Params:
      table_params:
        tables: The lookup tables for specific fields in schema
        lang: The lang for the search
        table_update: missing codes to update
      field: The schema or field name
      lookup: the lookup type (name or tag)
      item: the data record
    Return:
        The location name or tag
    """
    tables, lang, table_update = table_params
    lookup_field = lookup.get("field")
    item_type_list = get_from_schema('type', item).split('.')
    item_type = item_type_list[-1] # determine type from last element of type field

    if lookup_field == 'name':
        if item_type == 'Geoname':
            return get_from_schema(field, item)
        elif item_type == "NTS":
            return get_from_schema('title', item)
        else:
            streetname = get_from_schema('component.streetname', item)
            placename = get_from_schema('component.placename', item)
            if placename is not None:
                streetname = streetname + ', ' + placename
            return streetname

    # tag type
    if item_type == 'Geoname':
    # component.generic use generic lookup table
        code = get_from_schema(field, item)
        if code in tables.get('generic'):
            return tables.get('generic').get(code).get(lang)
        else:
            return 'undefined'
    else:
        # category table lookup french only
        if lang == 'fr':
            if item_type.lower() in tables.get('category'):
                item_type = tables.get('category').get(item_type.lower()).get(lang)
        return item_type


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
    schema_type = lookup.get("type")
    if schema_type == "table":
        return get_from_table
    elif schema_type == "array":
        return get_from_array
    elif schema_type == "search":
        return get_from_search
    elif schema_type == "average":
        return get_average
    elif schema_type == "url":
        return get_from_url
    elif schema_type == "csv":
        return get_from_csv
    elif schema_type == "type":
        return get_from_type
    else:
        return function_error

def get_results(table_params, function_field, item):
    """
    Apply the function asociated for each field to the item to
    extract the return value

    Params:
      table_params:
        tables: The lookup tables for specific fields in schema
        lang: The lang for the search
      function_field: Contains the function and the section of the schema
                      with the rules to obtain the value for that field
      item: the data item to obtain the value from
    Return: The return value for the piece of data either original or altered
             and an error string where None or empty means no error
    """
    function, item_schema = function_field
    if "get_from_schema" in function.__name__:
        return function(item_schema.get("field"), item)
    elif "get_from_table" in function.__name__:
        lookup = item_schema.get("lookup")
        return function(table_params,
                        item_schema.get("field"),
                        lookup,
                        item)
    elif "get_from_array" in function.__name__:
        field = item_schema.get("field")
        lookup = item_schema.get("lookup")
        return function(field, lookup, item)
    elif "get_from_search" in function.__name__:
        field = item_schema.get("field")
        search_field = item_schema.get("lookup").get("search_field")
        contains = item_schema.get("lookup").get("contains")
        return_field = item_schema.get("lookup").get("return_field")
        return function(field,
                        search_field,
                        contains,
                        return_field,
                        item)
    elif "get_average" in function.__name__:
        field = item_schema.get("field")
        ndx_list = item_schema.get("lookup").get("at")
        return function(field, ndx_list, item)
    elif "get_from_csv" in function.__name__:
        field = item_schema.get("field")
        lookup = item_schema.get("lookup")
        return function(table_params, field, lookup, item)
    elif "get_from_type" in function.__name__:
        field = item_schema.get("field")
        lookup = item_schema.get("lookup")
        return function(table_params, field, lookup, item)
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
                if isinstance(value, int):
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
            error = ERR_UNEXPECTED_SCHEMA_TYPE

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

async def apply_service_schema(service,
                               table_params,
                               functions_by_field,
                               data_item):
    """
    Extract the required information from each item based on the service model

    Params:
      service: The name of the service to be added at the begging of each item
      table_params:
        tables: The lookup tables for specific fields in schema
        lang: The lang for the search
      function_by_field: the list of field functions
      data_item: The item to be affected by the functions

    Return: A restructured new item matching the output requirements
    """
    item = {'key': service}
    for key in functions_by_field:
        functions = functions_by_field.get(key)
        if len(functions) == 1:
            item[key] = get_results(table_params, functions[0], data_item)
        else:
            result_list = []
            for function_field in functions:
                result_list.append(get_results(table_params,
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
    output_schema, item = parameters_tuple
    output_fields = output_schema.get("properties")
    output_required = output_schema.get("required")

    for key in output_fields:
        value = item.get(key)
        # Validate required parameters
        if (key in output_required) and (value is None):
            try:
                if key == "lat":
                    item[key] = get_average("bbox", [1, 3], item)
                if key == "lng":
                    item[key] = get_average("bbox", [0, 2], item)
            except:
                item[key] = ERR_ATTRIBUTE_NOT_FOUND
        else:
            # Validate value against schema
            key_definition = output_fields.get(key)
            val, schema_error = validate_against_schema(value,
                                                        key_definition)
            if schema_error:
                item[key] = f"{value} - {schema_error}"
            else:
                item[key] = val

    return item

def items_from_service(service,
                       table_params,
                       service_schema,
                       output_schema,
                       load,
                       item_keys):
    """
    Based on the output schema and api-out schema, return the formated
    data using multiprocessing to accelerate the task

    Params:
      service: The name of the service to put it ahead of the item's data
      table_params:
        tables: The lookup tables for specific fields in schema
        lang: The lang for the search
      schema_items: the section of the out-api schema to process the data layer
      schema_required: The section of the out-api schema to validate the
                       prescence of 'required' fields in the data layer
      load: The input set of data items
      item_keys: name, province and tag for each output item

    Return: A set of output items standarized and validated
    """
    list_to_process = []
    loads = []
    #schema = model.get_schema()
    schema_layer, data_layer = get_data_layer(service_schema, load)
    # Identify the process by field
    if len(data_layer) > 0:
        functions_by_field = get_functions(schema_layer, data_layer[0])
        # Readjust the item's data based on the service's schema
        for data_item in data_layer:
            item = asyncio.run(
                apply_service_schema(service,
                                     table_params,
                                     functions_by_field,
                                     data_item))

            # check for duplicate item (name, province and tag)
            item_name = item['name']
            if item_name in item_keys:
                if item_keys[item_name]['province'] == item['province'] and \
                   item_keys[item_name]['tag'] == item['tag'] :
                    continue
            item_keys[item_name] = {'province': item['province'], 'tag': item['tag']}

            # Add the item to the list for the next process
            list_to_process.append((output_schema, item))
        num =len(list_to_process)
        # Apply the 'generic' out-api-schema to the item
        with lambda_multiprocessing.Pool(num) as process:
            loads = process.map(apply_out_schema, list_to_process)
    return loads
