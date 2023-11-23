import json
import s3_manager
import botocore
from constants import *
from url_methods import url_request

# Singleton Class
class Geolocator():
    """
    Create one single instance to read and keep in memory the schemas for
    input/output as well as all the services available

    Params:
      object: Required to create the class

    Return: A single instance containing all the
    schemas, each readable through its own key
    """
    # Attributes
    _instance = None
    _schemas = {}
    _tables = {}

    # Methods
    def __new__(cls):
        """
        Create a single instance and read the schemas

        Return: the only instance of this object
        """
        if cls._instance is None:
            cls._instance = super(Geolocator, cls).__new__(cls)
            try:
                cls.read_schemas(cls)
                cls.read_tables(cls)
            except botocore.exceptions.ClientError as error:
                print(error)
        return cls._instance

    def read_schemas(self):
        """
        Read the schemas from S3 service

        Return: the schemas once they are read from the bucket
        """
        bucket = s3_manager.get_s3_bucket()
        #schemas
        _paths = s3_manager.get_schemas_paths(bucket)
        _apis_dict = _paths.get(APIS)
        _services_dict = _paths.get(SERVICES)
        # IN schema
        _in_api_schema = s3_manager.read_file(bucket,_apis_dict[IN_API])
        self._schemas[IN_API] = json.loads(_in_api_schema)
        # OUT schema
        _out_api_schema = s3_manager.read_file(bucket,_apis_dict[OUT_API])
        self._schemas[OUT_API] = json.loads(_out_api_schema)
        # schemas of all services provided
        _out_api_properties = self._schemas.get(OUT_API).get(PROPERTIES)
        for key in _out_api_properties:
            service_schema = s3_manager.read_file(bucket,_services_dict[key])
            #_schemas list of objects instead of string.json
            self._schemas[key] = json.loads(service_schema)

    def read_tables(self):
        """
        Read the tables from S3 service

        Return: the tables required for scpecific fields in schemas
        """
        bucket = s3_manager.get_s3_bucket()
        self._tables = s3_manager.get_tables(bucket, TABLES_PATH)
        for table in self._tables:
            content_table = self._tables.get(table)

    def write_table(self, table_name, tables):
        """
        Write the tables to S3 service
        Return:
        """
        bucket = s3_manager.get_s3_bucket()
        s3_manager.write_table(bucket, table_name, tables)

    def get_schemas(self):
        """
        Method to get access to the schemas

        Return: A dictionary with all the read schemas
        """
        return self._schemas

    def get_tables(self):
        """
        Method to get access to the tables

        Return: The selected table from the dictionary
        """
        return self._tables
