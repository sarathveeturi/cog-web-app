from diagrams import Diagram, Cluster
from diagrams.programming.framework import FastAPI
from diagrams.azure.storage import BlobStorage  
from diagrams.onprem.database import Postgresql
from diagrams.onprem.container import Docker

with Diagram("COG Web App Architecture", show=True):
    
    with Cluster('Backend'):

        fastapi = FastAPI("Fast API server")
        postgres_db = Postgresql("COG Metadata") 
        container = BlobStorage("Blob Storage")
        docker_image = Docker("Postgresql, Adminer")

        fastapi >> container
        fastapi >> postgres_db
        docker_image >> postgres_db 
        
