<template>
<div>
<input type="file" @change="onFileSelected">
</div>
</template>

<script>
  export default {

    data: () => ({
      return:{
      selectedFile: null,
    }
    }),

    headers: {
        "Content-type": "multipart/form-data",
      },

    methods: {

      onFileSelected(event) {
        this.selectedFile = event.target.files[0]
      },
    }
  }
</script>