import boto3
import csv
from constants import *
import os
import io

def get_s3_bucket():
    """
    Get the name of the bucket

    Return: The name of the bucket in S3
           # This name is just for developping and testing purposes
    """
    return os.environ.get('S3_BUCKET_NAME')

def get_substring(string, start, end):
    """
    Return: The string between two substrings
    """
    return (string.split(start))[1].split(end)[0]

def get_objects(bucket_name):
    """
    Read and return the content in the Bucket

    Param:
      bucket_name: The name of the bucket to read from
    Return: List of objects in the bucket
    """
    list_obj = []
    try:
        # find list of files from S3 buckets
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket_name)
        for obj in bucket.objects.all():
            list_obj.append(obj.key)
        return list_obj

    except ClientError as e:
        logging.error(e)
        return False

def get_tables(bucket_name, tables_path):
    """
    Read and return the content in bucket's tables path 

    Param:
      bucket_name: The name of the bucket to read from
      table_path: The path to the csv files inside the bucket
    Return: The content of the csv files transformed into dictionaries
    """
    tables = {}
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=TABLES_PATH):
        table_path = obj.key
        if table_path.endswith(CSV):
            key = get_substring(table_path, TABLES_PATH, CSV)
            file_body = read_file(bucket_name, table_path)
            data = file_body.splitlines()
            records = csv.reader(data)
            headers = next(records)
            codes = {}
            headerCount = len(headers)
            for eachRecord in records:
                descr = {}
                
                for count in range(1,headerCount):
                    descr[headers[count]] = eachRecord[count]
                codes[eachRecord[0]] = descr
            tables[key] = codes
    return tables

def write_table(bucket_name, table_name, tables):
    """
    write table content to csv file in bucket's tables path
    Param:
      bucket_name: The name of the bucket to write to
      table_name: generic or province
      tables: tables to create csv from
    Return:
    """
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name).name
    table = tables.get(table_name)
    csv_columns = ['code','en','fr']

    csv_string = io.StringIO()  # create csv to string
    writer = csv.DictWriter(csv_string, fieldnames=csv_columns)
    writer.writeheader()
    for num,val in sorted(table.items(), key=lambda num: int(num[0])):  # sort by code as integer
        row = {'code': num, 'en': val.get('en'), 'fr': val.get('fr')}
        writer.writerow(row)

    content = csv_string.getvalue()
    filename = TABLES_PATH + table_name + '.csv'
    try:
        content_object = s3.Object(bucket, filename).put(Body=content)
        print('csv file updated:', filename)
    except Exception as error:
        print("content_object write error to S3 bucket", type(error).__name__)
        print('error=', error)

    return

def get_schemas_paths(bucket_name):
    """
    Get the path to access all the objects in the bucket

    Param:
      bucket_name: The name of the bucket to read from
    Return: The paths to the objects in the bucket
    """
    apis, services = {}, {}

    objects = get_objects(bucket_name)

    for item in objects:
        # identification des services
        if item.endswith(SCHEMA_JSON):
            if item.startswith(API_PATH):
                key = get_substring(item, API_PATH, SCHEMA_JSON)
                apis[key] = item
            elif item.startswith(SERVICES_PATH):
                key = get_substring(item, SERVICES_PATH, SCHEMA_JSON)
                services[key] = item
            else:
                raise Exception(ERR_UNKNOWN_ITEM_IN_BUCKET + item)

    paths = {
        APIS: apis,
        SERVICES: services
    }

    return paths

def read_file(bucket, filename):
    """
    Read the content of the object in the bucket

    Params:
      bucket: The name of the bucket to read from
      filename: the path to the object

    Return: The content of the object as string
    """
    s3 = boto3.resource('s3')
    try:
        content_object = s3.Object(bucket, filename)
    except:
        print(f"content_object read error extracting: {filename}")

    file_body= content_object.get()['Body'].read().decode('utf-8')

    return str(file_body)
