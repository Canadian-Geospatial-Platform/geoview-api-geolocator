import boto3
from constants import *

def get_s3_bucket():
    """
    Get the name of the bucket

    Return: The name of the bucket in S3
           # This name is just for developping and testing purposes
    """
    return "dev-app-geolocator"

def get_substring(string, start, end):
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

def get_schemas_paths(bucket_name):
    """
    Get the path to access all the objects in the bucket

    Param:
      bucket_name: The name of the bucket to read from
    Return: The paths to the objects in the bucket
    """
    apis, services = {}, {}
    api_starts = 'api/'
    service_starts = 'services/'
    ends = '-schema.json'

    objects = get_objects(bucket_name)

    for item in objects:
        # identification des services
        if item.endswith(ends):
            if item.startswith(api_starts):
                key = get_substring(item, api_starts, ends)
                apis[key] = item
            elif item.startswith('services'):
                key = get_substring(item, service_starts, ends)
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
