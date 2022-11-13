<template>
  <div>
    <!-- Importing leaflet style and table style CDN-->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.1/dist/leaflet.css" integrity="sha256-sA+zWATbFveLLNqWO2gtiw3HL/lh1giY/Inf1BJ0z14=" crossorigin="" />
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">
    <file-pond
            name="imagefile"
            ref="pond"
            class-name="my-pond"
            label-idle="Drop Geotiff files here..."
            allow-multiple="true"
            accepted-file-types="image/tif, image/TIF, image/tiff, image/png, file/nc"
            server="http://localhost:8000/postimages"
            v-on:init="handleFilePondInit"
            enctype="multipart/form-data"
        />

        <div id="mapContainer"></div>
  
        <br>              
        
            <div class="tableContainer" id="cog-list">     
            
            <table class="table">
              <thead >
                <tr>
                  <th scope="col">Image Title</th>
                  
                  <th scope="col">CRS</th>

                  <th scope="col">Actions</th>
                </tr>
                
              </thead>
              <tbody id="table_body">
                <tr v-for="(cogname, index) in cogList" :key="index">
                  <td v-text="cogname.image_title"></td>
                  <td v-text="cogname.image_crs"></td>
                  <td><v-btn rounded
                        color="#008B8B" 
                       @click="loadCOG(cogname.image_title)">
                       <v-icon center>
                        mdi-eye
                      </v-icon>
                      
                  </v-btn>
                  &nbsp; 
                  <v-btn
                        color="#008B8B"
                        @click="deleteCOG(cogname.image_title)">
                        <v-icon center>
                        mdi-delete
                      </v-icon>
                  </v-btn>                                                           
                
                 </td>
                  
                </tr>
             
              </tbody>
            </table>
        </div>
       
  </div>

</template>

<script src="https://unpkg.com/leaflet@1.9.1/dist/leaflet.js" integrity="sha256-NDI0K41gVbWqfkkaHj15IzU7PtMoelkzyKp8TOaFQ3s=" crossorigin=""></script>

<script>

import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import vueFilePond from 'vue-filepond';
// Importing Filepond plugins
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type/dist/filepond-plugin-file-validate-type.esm.js';
import FilePondPluginImagePreview from 'filepond-plugin-image-preview/dist/filepond-plugin-image-preview.esm.js';
// Importing Filepond styles
import 'filepond/dist/filepond.min.css';
import 'filepond-plugin-image-preview/dist/filepond-plugin-image-preview.min.css';
import 'filepond/dist/filepond.css';

const FilePond = vueFilePond(FilePondPluginFileValidateType, FilePondPluginImagePreview);
    

export default {
  components: {
       FilePond,
    },

  data() {
    return {
      baseurl: "http://localhost:8000",
      blobAuthURL:"",
      mapObject:'',
      zoom: 10,
      center:'',
      cogList: [],
      }
    },

    headers: {
      headers: "Collections"
    },
    
    methods: {
        handleFilePondInit() {
        this.$refs.pond.getFiles();
        }, 
        // Setting Initial map layer with Open Street Map
        setupLeafletMap: function () {

        let mapDiv = L.map("mapContainer").setView([0,0], 0);

        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png?{foo}', 
                    {foo: 'bar', attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'})
        .addTo(mapDiv);

        this.mapObject = mapDiv; 
        },

        // Retriving center of an COG and assign to `center` data property
        getCenter: function() {
            console.log(this.baseurl + '/cog/bounds?url='+this.blobAuthURL)

            axios.get(this.baseurl + '/cog/bounds?url='+ this.blobAuthURL).then((response)=>{
              let bounds=response.data.bounds
              let imageCenter = [(bounds[1]+bounds[3])/2,(bounds[0]+bounds[2])/2]
             
              this.center = imageCenter;  
            })
        },

        loadCogList() {
          //fetching the data from postgresql database 'cogdb_table'
          axios.get("http://localhost:8000/getimages").then((data)=>{
          let objectData = data.data 
          this.cogList= objectData  
        })
        },

        // Function to load a COG on the map from titiler
        loadCOG: function(imageName) {
                          
          // Get's authorized blob URL
          axios.get(this.baseurl + '/viewcog/' + imageName)
            .then((response)=>{
              let encodedAuthUrl = encodeURIComponent(response.data)

              this.blobAuthURL = encodedAuthUrl
                                      
              //Gets info of the blob from titiler info endpoint
              axios.get(this.baseurl + '/cog/tilejson.json'+'?url=' + this.blobAuthURL)
              .then((response)=>{                  
                let tilesetLayer = response.data.tiles[0]
                //retrieving center of image from getCenter method
                this.getCenter()

                this.mapObject.setView(this.center, this.zoom)
                L.tileLayer(tilesetLayer).addTo(this.mapObject)                                
              }) 
            });                 
        },

        deleteCOG: function(imageName) {
          axios.delete(this.baseurl + '/deletecog/' + imageName)
          this.loadCogList();
        }       
  },

  mounted() {
   this.setupLeafletMap();
   this.loadCogList();
  },
    
}
</script>   

<style scoped>
  #mapContainer {
   width: 100vw;
   height: 80vh;
  }
  th {
        background-color: #008B8B;
        color: white;
    }
  
    tr:nth-child(even){background-color: #f2f2f2}
  
  </style>
