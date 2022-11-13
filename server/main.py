from fileinput import filename
import psycopg2
import boto3
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


S3_BUCKET_NAME = "video-app-123"

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

@app.get("/getimages", response_model=List[COGModel])
async def get_images():
    # Establishing a connection to DB
    conn = psycopg2.connect(
        database="cogdb", user="docker", password=" ", host="database"
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
    # this URL will change for a private bucket to authorize IAM access
    url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{blob_name}"
    return url
   

@app.post("/postimages",status_code=200)
async def postimages(imagefile: UploadFile = File(...)):
    print("Create endpoint!!")

    
    name = imagefile.filename
    file_type = imagefile.content_type
    print(name, file_type)

    try: 
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(S3_BUCKET_NAME)
        bucket.upload_fileobj(name, ExtraArgs={"ACL": "public-read"})
    except Exception as e:
        print("The file with the similar name already exits!!!!!!!")

    uploaded_file_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{name}"  
    
    image_crs, image_bounds = extract_cog_metadata.extractmetadata(uploaded_file_url)
    
    conn = psycopg2.connect(
        database="cogdb", user="docker", password=" ", host= "database"
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
    try:
        client = boto3.client('s3')
        client.delete_object(Bucket=S3_BUCKET_NAME, Key=blob_name)
        print("File deleted!!!!!! Attempting to delete metadata record")
    except Exception as e:
        print("Looks like the blob "+ blob_name + " is already deleted!! Deleting the record from SQL.", e)

    # Delete metadata record of the image from postgres table
    conn = psycopg2.connect(
        database="cogdb", user="docker", password=" ", host= "database"
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
