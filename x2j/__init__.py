import logging
import azure.functions as func
import os, uuid
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import shutil
import json
import xmltodict
import tempfile
import ntpath

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
        SOURCE_FILE = req_body.get("source_file")
        srcContainer = req_body.get("source_container")
        destContainer = req_body.get("destination_container")
        kvName = req_body.get("kv_name")
        srcSecretKey = req_body.get("source_connection_str_secret_name")
        destSecretKey = req_body.get("destination_connection_str_secret_name")
    except:
        return func.HttpResponse(
            'Please pass Source File (source_file), Source Container (source_container),(OPTIONAL)Destionation Container (detination_container), Keyvault name (kv_name) ,KV secret name which contains source storage account connection string (source_connection_str_secret_name),(OPTIONAL)KV secret name which contains destination storage account connection string (destination_connection_str_secret_name) in the request body such as: \n {\n "source_file" : "<MY XML FILE>",\n "source_container" : "<MY CONTAINER>",\n "destination_container" : "<MY CONTAINER>", \n "kv_name" : "<MY KV>", \n "source_connection_str_secret_name" : "<SECRET NAME>" ,\n "destination_connection_str_secret_name" : "<SECRET NAME>" \n } ',
            status_code=400
        )
    
    ### Check all mandatory params are provide
    if not(SOURCE_FILE and srcContainer and kvName and srcSecretKey):
        return func.HttpResponse(
            'Please pass Source File (source_file), Source Container (source_container),(OPTIONAL)Destionation Container (detination_container), Keyvault name (kv_name) ,KV secret name which contains source storage account connection string (source_connection_str_secret_name),(OPTIONAL)KV secret name which contains destination storage account connection string (destination_connection_str_secret_name) in the request body such as: \n {\n "source_file" : "<MY XML FILE>",\n "source_container" : "<MY CONTAINER>",\n "destination_container" : "<MY CONTAINER>", \n "kv_name" : "<MY KV>", \n "source_connection_str_secret_name" : "<SECRET NAME>",\n "destination_connection_str_secret_name" : "<SECRET NAME>" \n } ',
            status_code=400
        )
    
    ### Check if OPTIONAL prams are PARTIALLY provide
    if not(destContainer) and destSecretKey:
        return func.HttpResponse(
             "Destionation Secret key name provided without Destination Container"
            ,status_code=400
        )
    elif not(destSecretKey) and destContainer:
        return func.HttpResponse(
           "Destination Container provided without Destionation Secret key name"
            ,status_code=400
        )
    ### If NO OPTIONAL pram provide then set dest equal to source
    else:
        destContainer =  srcContainer
        destSecretKey = srcSecretKey
    
    ## Get Source file name without suffix
    SOURCE_FILE = SOURCE_FILE.split('.')[0]
    
    ## Set source and det suffixes
    SOURCE_SUFFIX = '.xml'
    DEST_SUFFIX = '.json'    
    
    
    ## Getting secrets from Azure KV
    try:
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url="https://"+kvName+".vault.azure.net", credential=credential)
        srcSecretValue = secret_client.get_secret(srcSecretKey)
        destSecretValue = secret_client.get_secret(destSecretKey)
        src_connection_string = srcSecretValue.value
        dest_connection_string = destSecretValue.value
    except Exception as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )
    ## Downloading the file to a tempfile under /tmp
    try:
    
        blob_service_client = BlobServiceClient.from_connection_string(src_connection_string)
        container_client = blob_service_client.get_container_client(srcContainer)
        blob_client = container_client.get_blob_client(SOURCE_FILE+SOURCE_SUFFIX)
    
        fp_xml = tempfile.NamedTemporaryFile(mode="w",delete=False,suffix='.xml')
        TEMP_XML_FILE = fp_xml.name
        with open(TEMP_XML_FILE, "wb") as my_blob:
            download_stream = blob_client.download_blob()
            my_blob.write(download_stream.readall())

    except Exception as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )

    ### Converting the the tempfile using xmltodict
    try:
        with open(TEMP_XML_FILE) as xml_file:
            data_dict = xmltodict.parse(xml_file.read())

        xml_file.close()
        fp_xml.close()
        json_data = json.dumps(data_dict)

        fp_json = tempfile.NamedTemporaryFile(mode="w",delete=False,suffix='.json')
        TEMP_JSON_FILE = fp_json.name
        ## Preparing the name for tempfile to rename it to sourcefile.json 
        ## This step is not necessary as we can upload the tempfile with any name we like
        RENAMED_JSON = os.path.join(ntpath.dirname(TEMP_JSON_FILE),SOURCE_FILE+DEST_SUFFIX)
    except Exception as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )
        ## Writing the JSON dump to tempfile
    try:
        with open(TEMP_JSON_FILE, "w") as json_file:
            json_file.write(json_data)

        json_file.close()
        fp_json.close()
    except Exception as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )
    ### Renaming the tempfile to the new correct name
    ## This step is not necessary as we can upload the tempfile with any name we like
    try:
        shutil.move(TEMP_JSON_FILE,RENAMED_JSON)
    except Exception as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )
    ## Uploading to Blob storage
    try:
        blob_service_client = BlobServiceClient.from_connection_string(dest_connection_string)
        container_client = blob_service_client.get_container_client(destContainer)
        ## Using ntpath to get the file name only
        blob_client = container_client.get_blob_client(ntpath.basename(RENAMED_JSON))
        with open(RENAMED_JSON, "rb") as data:
            blob_client.upload_blob(data, blob_type="BlockBlob")

    except Exception as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )
    ## Removing temp files from /tmp
    try:    
        os.remove(RENAMED_JSON)
        os.remove(TEMP_XML_FILE)
    except Exception as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )
    ## Return success messagge
    return func.HttpResponse(f"Converted to {SOURCE_FILE}{DEST_SUFFIX} successfully!",status_code=200)
