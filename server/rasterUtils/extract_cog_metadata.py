from http.client import HTTPResponse
import rasterio

def extractmetadata(rasterfile:str):
    src = rasterio.open(rasterfile)

    raster_crs, raster_bounds = src.crs, src.bounds
    
    return raster_crs, raster_bounds
   
