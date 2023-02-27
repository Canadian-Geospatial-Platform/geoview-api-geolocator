def validate_required_parameters_with_schema(schema, parameters):
    """
    Identifies the required parameters and Return child schema and params

    Params:
      schema: The rules required to validate the parameters
      parameters: The parameters to be validated

    Return: The child parameters and child schema properties once the ones
             at this level are validated against each other
    """
    schema_properties = schema["properties"]
    schema_required = schema["required"]
    for require in schema_required:
        if not parameters.get(require):
            error_message = f"inexistent parameter '{require}'"
            raise Exception(error_message)
        schema_params = schema_properties[require]
        url_params = parameters[require]
    return url_params, schema_params

def get_params_default(params, schema):
    """
    Find and add the absent parameters wiht their default values.

    Params:
      params: The original dictionary of parameters
      schema: The rules and default values for each parameter

    Return: The parameters including those found absents with default values
    """
    for key in schema:
        param_schema = schema[key]
        if not params.get(key):
            if param_schema.get("type") == "array":
                items = param_schema.get("items")
                params[key] = items.get("enum")
            else:
                if param_schema.get("default"):
                    params[key] = param_schema.get("default")

def validate_param_with_schema(param, schema):
    """
    Validate the parameters against the schema's valid values

    Params:
      param: parameter value or list to be evaluated
      schema: The rules to validate the parameter

    Return: Raises error in case of invalid value
    """
    if schema.get("type") == "string":
        enum = schema.get("enum")
        if enum:
            if param not in enum:
                error_message = f"invalid parameter value '{param}'"
                raise Exception(error_message)
        else:
            param = param.replace(" ","+")
    else:
        if not isinstance(param, list):
            param = param.split(",")
        items = schema.get("items")
        enum = items.get("enum")
        invalid=[item_param for item_param in param if item_param not in enum]
        if len(invalid) > 0:
            error_message = f"invalid parameter value(s) '{invalid}'"
            raise Exception(error_message)

    return param

def validate_querystring_against_schema(parameters, schema):
    """
    Validate the parameters against the schema to get the complete set
    required

    Params:
      parameters: The tree containg the parameters from the query
      schema: The rules to extract and modify the parameters from the tree

    Return: The full list of normalized and valid parameters
    """
    url_params, new_schema = validate_required_parameters_with_schema(
        schema,
        parameters
    )
    query_params, new_schema = validate_required_parameters_with_schema(
        new_schema,
        url_params
    )
    properties = new_schema["properties"]
    validate_required_parameters_with_schema(
        new_schema,
        query_params
    )
    # Fill the absent parameters with defaults
    get_params_default(query_params, properties)
    # Loop though the properties in schema
    for key in properties:
        # match the parameter against valid values from schema or services
        property_dict = properties.get(key)
        parameter = query_params.get(key)
        query_params[key] = validate_param_with_schema(parameter,
                                                       property_dict)

    return query_params
