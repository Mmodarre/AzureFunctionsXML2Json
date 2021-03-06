# Azure XML2JSON
Azure function to convert XML file to JSON. This function can be used in conjunction with Azure Data Factory to process XML files. 

[Azure data factory XML feature request](https://feedback.azure.com/forums/270578-data-factory/suggestions/17508058-xml-file-type-in-copy-activity-along-with-xml-sc)

[Azure data factory supported file formats](https://docs.microsoft.com/en-us/azure/data-factory/supported-file-formats-and-compression-codecs)

- Current implementation expects both files to be stored on Azure Blob Storage
- Source and converted (destination) files could be on different storage accounts/containers
- Storage credentials needs to be stored on Azure Key Vault



## Usage:
1. Clone repo to you development environment.
2. Use VS code to deploy function to Azure Functions (Python 3.7 consumption or premium plan).
3. Add Managed identity of the function to Key Vault.
4. Add storage account credentials to KV secret.
5. call the HTTP endpoint with following body example
```json
{
    "source_file": "nasa.xml",
    "source_container": "<my container>",
    (OPTIONAL)"destination_container": "<my container>",
    "kv_name": "<my key vault>",
    "source_connection_str_secret_name": "<source storage account connection string secret>",
    (OPTIONAL)"destination_connection_str_secret_name": "<destination storage account connection string secret>"

}
```

## NOTES:
- If `destination container` and `destination_connection_str_secret_name` attributes are not provided in the request body the function saves the result in the same storage account and container.

- The function only accepts files with .xml suffix.

- The resulting file with be the same name as xml file with .json suffix.
- With functions consumption plan there is a limit of 240 seconds execution. This could mean for files bigger than 10MB the functions times out. In this case you will need a function in premium plan.


## To do

- [ ] Add Azure Data Factory usage instructions


