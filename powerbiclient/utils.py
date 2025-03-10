#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pandas.api.types import is_numeric_dtype
import re

from .authentication import DeviceCodeLoginAuthentication, AuthenticationResult
from .models import DataType

MODULE_NAME = "powerbi-jupyter-client"
data_types_map = {
    'string': DataType.TEXT.value,
    'int32': DataType.INT32.value,
    'bool': DataType.LOGICAL.value,
    'datetime64[ns]': DataType.DATE_TIME.value,
    'object': DataType.TEXT.value  # default
}


def get_dataset_config(df, locale='en-US'):
    """ Utility method to get the dataset create configuration dict from a pandas. To be used as input for instantiating a quick visualization object.

    Args:
        df (object): Required.
            Pandas DataFrame instance
        locale (string): Optional.
            This value is used to evaluate the data and parse values of the given DataFrame. 
            Supported locales can be found here: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lcid/a9eac961-e77d-41a6-90a5-ce1a8b0cdb9c?redirectedfrom=MSDN

    Returns: 
        dict: dataset_create_config
    """
    if df is None:
        raise Exception("Parameter df is required")

    table_name = 'Table'
    columns_schema = []

    # NA values should be considered as empty strings
    df = df.fillna('')

    for col in df.columns:
        # Find the correct DataType according to Pandas dtype
        dtype_key = str(df[col].dtype)
        if dtype_key in data_types_map:
            data_type = data_types_map[dtype_key]
        elif is_numeric_dtype(df[col]):
            data_type = DataType.NUMBER.value
        elif re.search(r"datetime64\[ns, .*\]", dtype_key):
            data_type = DataType.DATE_TIME_ZONE.value
        else:
            data_type = DataType.TEXT.value

        # Logical values should be with lower case: true / false
        if data_type == DataType.LOGICAL.value:
            df[col] = df[col].astype('string').str.lower()

        columns_schema.append({'name': col, 'dataType': data_type})

    return {
        'locale': locale,
        'tableSchemaList': [
            {
                'name': table_name,
                'columns': columns_schema
            }
        ],
        'data': [
            {
                'name': table_name,
                'rows': df.astype('string').values.tolist()
            }
        ]
    }


def is_dataset_create_config_valid(dataset_create_config):
    """ Validate dataset_create_config

    Args:
        dataset_create_config (dict): Required.
            A dict representing the data used to create the report, formatted as IDatasetCreateConfiguration
            (See: https://learn.microsoft.com/en-us/javascript/api/overview/powerbi/embed-quick-report#step-11---create-a-dataset-without-a-data-source)

    Returns:
        bool: True if dataset_create_config is valid, False otherwise
    """
    if dataset_create_config is None or type(dataset_create_config) is not dict:
        return False

    if len(dataset_create_config.keys()) != 3:
        return False

    # Validate locale
    locale = dataset_create_config.get('locale')
    if not locale or type(locale) != str:
        return False

    # Validate table schema list
    table_schema_list = dataset_create_config.get('tableSchemaList')
    if not is_dataset_create_config_items_valid(table_schema_list, ['name', 'columns']):
        return False

    # Validate data
    data = dataset_create_config.get('data')
    if not is_dataset_create_config_items_valid(data, ['name', 'rows']):
        return False

    return True


def is_dataset_create_config_items_valid(lst, expected_item_fields):
    if not lst or type(lst) != list or len(lst) != 1:
        return False

    for field in expected_item_fields:
        if not lst[0].get(field):
            return False

    return True


def get_access_token_details(powerbi_widget, auth=None):
    """ Get an access token
    Args:
        powerbi_widget (Report | QuickVisulize): Required.
            One of Power BI widget classes, can be Report or QuickVisualize
        auth (string or object): Optional.
            We have 3 authentication options to embed a Power BI report:
                - Access token (string)
                - Authentication object (object) - instance of AuthenticationResult (DeviceCodeLoginAuthentication or InteractiveLoginAuthentication)
                - If not provided, Power BI user will be authenticated using Device Flow authentication

    Returns:
        string: access_token
    """

    # auth is the access token string
    if isinstance(auth, str):
        # In this authentication way we cannot refresh the access token so token_expiration should be None
        return auth

    try:
        if auth is None:
            # Use DeviceCodeLoginAuthentication if no authentication is provided
            if not powerbi_widget._auth:
                powerbi_widget._auth = DeviceCodeLoginAuthentication()
            auth = powerbi_widget._auth
        elif not isinstance(auth, AuthenticationResult):
            raise Exception("Given auth parameter is invalid")
        else:
            powerbi_widget._auth = auth

        access_token = auth.get_access_token()
        return access_token

    except Exception as ex:
        raise Exception("Could not get access token: {0}".format(ex))
