from fileinput import filename
import psycopg2
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContainerClient, generate_blob_sas, BlobSasPermissions, ContainerSasPermissions, generate_container_sas
from typing import List
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rasterUtils import extract_cog_metadata
from datetime import datetime, timedelta
from titiler.core.factory import TilerFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.application.routers.cog import cog


blob_container = 'cog-raster-files'
connection_string = "YOUR CONNECTION STRING HERE"

class COGModel(BaseModel):
    id: int
    image_title: str
    image_url: str
    image_crs: str
    image_bounds: str
    #is_deleted: bool

app = FastAPI(debug=True)

cog = TilerFactory(router_prefix="cog")
app.include_router(cog.router, prefix="/cog", tags=["Cloud Optimized GeoTIFF"])
add_exception_handlers(app, DEFAULT_STATUS_CODES)

origins = [
    "http://localhost:8081",
    "https://titiler.xyz",
]

#enabling CORS to allow frontend-requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_azure_public_url(blob_path_and_name: str):
    storage_account_name = 'rasterupload'
    storage_account_key = 'YOUR ACCOUNT KEY HERE'
    storage_container_name = blob_container
   
    sas_blob = generate_blob_sas(account_name=storage_account_name,
                                container_name=storage_container_name,
                                blob_name=blob_path_and_name,
                                account_key=storage_account_key,
                                permission=BlobSasPermissions(read=True),
                                expiry=datetime.utcnow() + timedelta(hours=1))
   


    url = 'https://'+storage_account_name+'.blob.core.windows.net/'+storage_container_name+'/'+blob_path_and_name+'?'+sas_blob
    return url


@app.get("/getimages", response_model=List[COGModel])
async def get_images():
    # Establishing a connection to DB
    conn = psycopg2.connect(
        database="cogdb", user="docker", password="hatfield", host="database"
    )
    cur = conn.cursor()
    # Since we 
    cur.execute("SELECT * FROM cogdb_table")
    rows = cur.fetchall()

    formatted_images = []

    for row in rows:
        formatted_images.append(
            COGModel(id=row[0],
                     image_title=row[1],
                     image_url=row[2],
                     image_crs=row[3],
                     image_bounds=row[4]
                )
        )
    cur.close()
    conn.close()
    return formatted_images

@app.get("/viewcog/{blob_name}")

async def visualize_cogs(blob_name: str):
    storage_account_name = 'rasterupload'
    storage_account_key = 'YOUR ACCOUNT KEY HERE'
    
    blob_sas = generate_blob_sas( account_name= storage_account_name, 
                                            container_name= blob_container,
                                            blob_name=blob_name, 
                                            account_key=storage_account_key, 
                                            permission= ContainerSasPermissions(list=True, read=True, write=True), 
                                            expiry= datetime.utcnow() + timedelta(hours=1))
      
    url = 'https://'+storage_account_name+'.blob.core.windows.net/'+blob_container+ '/' + blob_name +'?'+ blob_sas
    
    return url
   

@app.post("/postimages",status_code=200)
async def postimages(imagefile: UploadFile = File(...)):
    print("Create endpoint!!")

    connection_str = connection_string
    blob_service_client = BlobServiceClient.from_connection_string(connection_str)

    name = imagefile.filename
    file_type = imagefile.content_type
    print(name, file_type)

    async with blob_service_client:
        container_client = blob_service_client.get_container_client(blob_container)
        try:
            print("Container found and resources are ready for upload!!")
            blob_client = container_client.get_blob_client(name)
            f = await imagefile.read()
            try:
               await blob_client.upload_blob(f)
            except Exception as e:
                print("The file with the similar name already exits!!!!!!!")
        except Exception as e:
            print(e)
            return HTTPException(401)
    
    uploaded_file_url = get_azure_public_url(name)
    
    print("This {uploaded_file_url} is the uploaded file URL!!!!".format(uploaded_file_url=uploaded_file_url))

    image_crs, image_bounds = extract_cog_metadata.extractmetadata(uploaded_file_url)
    
    conn = psycopg2.connect(
        database="cogdb", user="docker", password="hatfield", host= "database"
    )

    cur = conn.cursor()

    # Here we need to convert image_crs into string, if not the value will be converted as "CRS.from_epsg('EPSG Code)" when read into a list
    cog_metadata = [name, uploaded_file_url, str(image_crs), image_bounds]
    
    # Using %s to prevent sql injection vulnerabilities () (More info here: https://www.psycopg.org/docs/usage.html#passing-parameters-to-sql-queries)
    cur.execute(
        "INSERT INTO cogdb_table (image_title, image_url, image_crs, image_bounds) VALUES (%s, %s , %s , %s)", 
        (cog_metadata))
        
    conn.commit()
    cur.close()
    conn.close()


@app.delete('/deletecog/{blob_name}', status_code=200)
def deletecog(blob_name:str):
    connect_string = connection_string
    container_name = blob_container
    container_client = ContainerClient.from_connection_string(connect_string, container_name)
    try:
        container_client.delete_blob(blob_name)
        print("Blob deleted!!!!!! Attempting to delete metadata record")
    except Exception as e:
        print("Looks like the blob "+ blob_name + " is already deleted!! Deleting the record from SQL.", e)

    # Delete metadata record of the image from postgres table
    conn = psycopg2.connect(
        database="cogdb", user="docker", password="hatfield", host= "database"
    )
    
    cur = conn.cursor()
    
    cog_name = [blob_name]

    # Using %s to prevent sql injection vulnerabilities () (More info here: https://www.psycopg.org/docs/usage.html#passing-parameters-to-sql-queries)
    cur.execute(
        "DELETE FROM cogdb_table WHERE (image_title = %s)", cog_name
    )

    conn.commit()
    cur.close()
    conn.close()  

#if __name__=='__main__':
 #     uvicorn.run(app, host="0.0.0.0", port=8000)#reload=True)
