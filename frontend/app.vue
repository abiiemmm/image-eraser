<script setup lang="ts">
import { ref } from 'vue'

// --- STATE MANAGEMENT ---
const file = ref<File | null>(null)
const originalPreview = ref<string | null>(null)
const processedImage = ref<string | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

// --- HANDLERS ---

// 1. Handle saat user memilih file (DragDrop atau Klik)
const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    processFile(input.files[0])
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault() // Mencegah browser membuka file di tab baru
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    processFile(event.dataTransfer.files[0])
  }
}

// 2. Logic memproses file untuk Preview awal
const processFile = (selectedFile: File) => {
  // Reset state
  errorMessage.value = null
  processedImage.value = null
  
  // Validasi tipe file
  if (!selectedFile.type.match('image.*')) {
    errorMessage.value = "File harus berupa gambar (JPG/PNG)"
    return
  }

  file.value = selectedFile
  originalPreview.value = URL.createObjectURL(selectedFile)
}

// 3. KIRIM KE BACKEND (FastAPI)
const removeBackground = async () => {
  if (!file.value) return

  isLoading.value = true
  errorMessage.value = null

  const formData = new FormData()
  formData.append('image', file.value)

  try {
    // Panggil API Backend (Pastikan port 8000 nyala)
    const response = await fetch('http://localhost:8000/api/remove-bg', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) throw new Error("Gagal memproses gambar di server")

    // Terima response sebagai BLOB (Binary Large Object)
    const blob = await response.blob()
    
    // Convert Blob ke URL agar bisa ditampilkan di <img>
    processedImage.value = URL.createObjectURL(blob)

  } catch (err) {
    errorMessage.value = "Terjadi kesalahan saat menghubungi server AI."
    console.error(err)
  } finally {
    isLoading.value = false
  }
}

// 4. Reset Ulang
const reset = () => {
  file.value = null
  originalPreview.value = null
  processedImage.value = null
  errorMessage.value = null
}
</script>

<template>
  <div class="min-h-screen bg-slate-900 text-white font-sans selection:bg-indigo-500 selection:text-white relative overflow-hidden">
    
    <div class="absolute top-0 left-0 w-96 h-96 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
    <div class="absolute top-0 right-0 w-96 h-96 bg-cyan-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>

    <div class="container mx-auto px-4 py-12 relative z-10 flex flex-col items-center min-h-screen justify-center">

      <div class="text-center mb-10 max-w-2xl">
        <h1 class="text-5xl md:text-6xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-indigo-500 mb-4 pb-2">
          Image Eraser
        </h1>
        <p class="text-slate-400 text-lg">
          Hapus latar belakang foto otomatis dengan hasil 
          <span class="text-slate-200 font-medium">presisi studio.</span>
          <br class="hidden md:block" />
          <span class="text-cyan-400 font-semibold">Gratis & Tanpa Database.</span>
        </p>
      </div>

      <div class="w-full max-w-5xl bg-slate-800/40 backdrop-blur-xl border border-white/10 rounded-3xl p-6 md:p-10 shadow-2xl">
        
        <div 
          v-if="!originalPreview"
          @dragover.prevent 
          @drop="handleDrop"
          class="group relative border-2 border-dashed border-slate-600 hover:border-cyan-400 rounded-2xl p-16 text-center transition-all duration-300 bg-slate-800/50 hover:bg-slate-800/80 cursor-pointer"
        >
          <input type="file" @change="handleFileSelect" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20" accept="image/*" />
          
          <div class="flex flex-col items-center gap-4 transition-transform group-hover:scale-105 duration-300">
            <div class="p-4 bg-slate-700/50 rounded-full text-4xl">
              ☁️
            </div>
            <div>
              <p class="text-xl font-semibold text-white">Drag & Drop gambar disini</p>
              <p class="text-slate-400 mt-2 text-sm">atau klik untuk browse file (JPG, PNG)</p>
            </div>
          </div>
        </div>

        <div v-else class="space-y-8">
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
            
            <div class="space-y-3">
              <div class="flex justify-between items-center px-2">
                <span class="text-sm font-bold text-slate-400 uppercase tracking-wider">Original</span>
                <span class="text-xs text-slate-500">{{ (file?.size! / 1024).toFixed(0) }} KB</span>
              </div>
              <div class="relative aspect-square bg-slate-700/30 rounded-2xl overflow-hidden border border-white/5 flex items-center justify-center">
                <img :src="originalPreview" class="max-w-full max-h-full object-contain" />
              </div>
            </div>

            <div class="space-y-3">
              <div class="flex justify-between items-center px-2">
                <span class="text-sm font-bold text-cyan-400 uppercase tracking-wider">Hasil</span>
                <span v-if="processedImage" class="text-xs text-green-400 animate-pulse">Selesai</span>
              </div>
              
              <div class="relative aspect-square bg-slate-900 rounded-2xl overflow-hidden border border-white/10 flex items-center justify-center group">
                
                <div class="absolute inset-0 opacity-20" 
                     style="background-image: radial-gradient(#4b5563 1px, transparent 1px); background-size: 20px 20px;">
                </div>

                <div v-if="isLoading" class="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/80 z-20 backdrop-blur-sm">
                  <div class="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                  <p class="text-cyan-300 font-medium animate-pulse">Sedang menghapus latar...</p>
                </div>

                <div v-if="!processedImage && !isLoading" class="absolute inset-0 flex items-center justify-center text-slate-500 text-sm px-8 text-center">
                  Klik tombol "Proses" di bawah untuk melihat hasil
                </div>

                <img v-if="processedImage" :src="processedImage" class="relative z-10 max-w-full max-h-full object-contain" />
              </div>
            </div>
          </div>

          <div v-if="errorMessage" class="bg-red-500/10 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg text-sm text-center">
            {{ errorMessage }}
          </div>

          <div class="flex flex-col sm:flex-row justify-end gap-4 pt-4 border-t border-white/10">
            <button @click="reset" class="px-6 py-3 rounded-xl text-slate-300 hover:text-white hover:bg-white/5 transition font-medium">
              Ulangi
            </button>
            
            <button 
              v-if="!processedImage" 
              @click="removeBackground" 
              :disabled="isLoading"
              class="px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-bold shadow-lg shadow-cyan-500/20 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ isLoading ? 'Memproses...' : 'Hapus Background' }}
            </button>

            <a 
              v-else 
              :href="processedImage" 
              download="image-eraser-result.png" 
              class="px-8 py-3 rounded-xl bg-green-500 hover:bg-green-400 text-white font-bold shadow-lg shadow-green-500/20 transition-all hover:scale-105 flex items-center justify-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download HD
            </a>
          </div>

        </div>
      </div>
      
      <footer class="mt-12 text-center">
        <p class="text-slate-500 text-sm">
          Built with Nuxt & FastAPI Python
        </p>
        
        <p class="text-slate-600 text-xs mt-2">
          Created with ❤️ by 
          <a 
            href="https://github.com/abiiemmm" 
            target="_blank" 
            rel="noopener noreferrer"
            class="text-cyan-400 font-semibold hover:text-cyan-300 hover:underline transition cursor-pointer"
          >
            Kucing Pungut
          </a>
        </p>
      </footer>

    </div>
  </div>
</template>

<style>
@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}
.animate-blob {
  animation: blob 7s infinite;
}
.animation-delay-2000 {
  animation-delay: 2s;
}
</style>