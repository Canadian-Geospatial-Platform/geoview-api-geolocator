import re
import json
from requests import Request, Session
from requests.exceptions import RequestException, Timeout, ConnectionError
import asyncio

from typing import Optional

def get_from_field(field, item):
    """
    Get the data value asociated with an specific field from a data item

    Params:
      field: The field name
      item: the data record
    Return:
        The field value from the record if the field exists in the data item.
    """
    if field is None or field not in item:
        return None
    return item.get(field)

def get_url_from_field(schema, data):
    """
    Get the url asociated with an specific field based on the schema provided

    Params:
      schema: The schema with the path to get access to the url
      data: the data structure where the url can be found
    Return: the field value asociated with
    """
    field = schema.get("field")
    url = schema.get("lookup").get("url")
    # Modify the url with the href at the bottom of the fields
    fields_list = field.split(".")
    href = data.get(fields_list[0]). \
                get(fields_list[1]). \
                get(fields_list[2]). \
                get(fields_list[3])
    return url.replace("_URL_", href)

def get_from_url(schema, data):
    """
    Get the data value asociated with an specific field from a REST response

    Params:
      schema: The schema defintion to access to the url
      data: the data structure where the url can be found
    Return: from a valid REST response, extracts the value from the asociated
             attribute.
    """
    field = schema.get("lookup").get("field")
    url = get_url_from_field(schema, data)
    load = url_request(url, {}, '')
    return get_from_field(field, load)

def replace_url_with_params(url, params, params_list):
    """
    Replace and Return the parameters embedded in the url with a valid set
    of values

    Params:
      url: The url to be affected
      params: The list of parameters to be replace in the url
      params_list: The list of query parameters where to search for the
                   replacent to params
    Return: The url whit the original parameters are replaced with the
             asociated values.
    """
    for param in params:
        param_match = "_"+param.upper()+"_"
        replace_with = params_list.get(params.get(param))
        url = url.replace(param_match, replace_with)
    return url

def assemble_url(schema, params):
    """
    Builds the url by matching the parameters against the schema

    Params:
      schema: The schema with the rules to assemble the url and parameters
      params: The list of parameters to be used to build the url

    Return: The assembled url including parameters as is required by the
             service schema.
    """

    # urls to update province and generic code tables
    code_table_urls = {'generic': {}, 'province': {}}

    # 1. Extract url and parameters from json
    url = schema.get("url")
    url_params = schema.get("urlParams")
    url_code_tables = schema.get("urlCodeTables")
    if url_code_tables:
        province_url    = schema.get("urlCodeTables").get("province").get("url")
        generic_url     = schema.get("urlCodeTables").get("generic").get("url")
        province_field  = schema.get("urlCodeTables").get("province").get("fields").get("description")
        generic_field   = schema.get("urlCodeTables").get("generic").get("fields").get("description")
    else:
        code_table_urls = None

    # 2. Parameters to modify the url
    if url_params:
        url = replace_url_with_params(url, url_params, params)

    # modify province and generic url by language
    if url_code_tables:
        if province_url:
            lang_en = {'lang' : 'en'}
            lang_fr = {'lang' : 'fr'}
            code_table_urls['province']['en'] = replace_url_with_params(province_url, url_params, lang_en)
            code_table_urls['province']['fr'] = replace_url_with_params(province_url, url_params, lang_fr)
            code_table_urls['province']['field'] = province_field
        if generic_url:
            lang_en = {'lang' : 'en'}
            lang_fr = {'lang' : 'fr'}
            code_table_urls['generic']['en'] = replace_url_with_params(generic_url, url_params, lang_en)
            code_table_urls['generic']['fr'] = replace_url_with_params(generic_url, url_params, lang_fr)
            code_table_urls['generic']['field'] = generic_field
        code_table_urls = {'code_table_urls': code_table_urls}


    # 3. lookup in parameters to replace with
    qry_params_dict = params
    lookup_in = schema.get("lookup").get("in")
    if lookup_in:
        for in_param in lookup_in:
            if in_param in params:
                qry_params_dict[lookup_in.get(in_param)] = params.pop(in_param)

    # 4. static parameters
    static_params = schema.get("staticParams")
    if static_params:
        qry_params_dict.update(static_params)

    return url, qry_params_dict, code_table_urls

def url_request(url, params, service_id):
    """
    Calls a REST service passing the url

    Params:
      url: The url for the REST call
      params: The params to pass along with the url
      service_id: key of the service

    Return: The response from the call.
    """
    try:
        s = Session()
        request = Request('GET', url, params=params)
        #print("url_request: ", url)
        #print(params)
        prepared_request = request.prepare()
        query_response = s.send(prepared_request, timeout=3)

        #print(prepared_request)


        # check response successful (200)
        if query_response.status_code == 200:
            json_response = query_response.json()
            #custom logic for new geolocation mock api
            if service_id == "locate":
                json_response = enrich_results(json_response, params.get("lang", "en"))
        else:
            name = 'Service unavailable: ' + service_id
            category = 'Response code: ' + str(query_response.status_code)
            response_dict = {'key': 'unsuccess', 'name': name  , 'province': '', 'category': category}
            return response_dict

        return json_response
    except (Timeout, ConnectionError) as e:
        name = 'Service timeout or connection error: ' + service_id
        category = str(type(e).__name__)
        return {'key': 'unsuccess', 'name': name, 'province': '', 'category': category}
    except RequestException as e:
        name = 'Service request exception: ' + service_id
        category = str(e)
        return {'key': 'unsuccess', 'name': name, 'province': '', 'category': category}

# List of provinces/territories in English and French (kept as-is)
PROVINCES = [
    "Alberta", "British Columbia", "Colombie-Britannique", "Manitoba",
    "New Brunswick", "Nouveau-Brunswick", "Newfoundland and Labrador", "Terre-Neuve-et-Labrador",
    "Nova Scotia", "Nouvelle-Écosse", "Ontario",
    "Prince Edward Island", "Île-du-Prince-Édouard", "Ile-du-Prince-Edouard",
    "Quebec", "Québec", "Saskatchewan",
    "Northwest Territories", "Territoires du Nord-Ouest", "Territoires-du-Nord-Ouest",
    "Nunavut", "Yukon", "Territoire du Yukon",
]

CATEGORY_TRANSLATIONS_FR = {
    "Street": "Rue",
    "Intersection": "Intersection",  # same word in FR
}

def extract_province(title: str) -> Optional[str]:
    """Return province/territory exactly as found in title (EN or FR)."""
    if not title:
        return None

    for province in PROVINCES:
        if re.search(rf"\b{re.escape(province)}\b", title, flags=re.IGNORECASE):
            match = re.search(rf"\b({re.escape(province)})\b", title, flags=re.IGNORECASE)
            return match.group(1) if match else province
    return None

def extract_feature_class(title: str) -> Optional[str]:
    """Return value in parentheses from title, e.g. (Lake), (Lac), (City)."""
    if not title:
        return None
    match = re.search(r"\(([^)]+)\)\s*$", title)
    return match.group(1) if match else None

def simplify_type(type_value: str, title: str, lang: str = "en") -> Optional[str]:
    """
    Simplify the type field:
    - For Geonames, use value in parentheses from title.
    - For others, use last word of fully-qualified class.
    - Translate Street / Intersection to FR if lang=fr
    """
    if not type_value:
        return None

    # Geoname → use (Lake) / (Lac) etc.
    if "Geoname" in type_value:
        feature_class = extract_feature_class(title)
        return feature_class if feature_class else "Geoname"

    # Non-Geoname → class name
    category = type_value.split(".")[-1]

    # Translate to French if requested
    if lang == "fr":
        category = CATEGORY_TRANSLATIONS_FR.get(category, category)

    return category

def enrich_results(results: list[dict], lang: str = "en") -> list[dict]:
    """Enrich geolocation results with province and category."""
    for item in results:
        title = item.get("title", "")
        item["province"] = extract_province(title)
        item["category"] = simplify_type(item.get("type"), title, lang)
    return results