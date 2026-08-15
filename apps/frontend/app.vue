<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const config = useRuntimeConfig()

// --- STATE MANAGEMENT ---
const file = ref<File | null>(null)
const originalPreview = ref<string | null>(null)
const processedImage = ref<string | null>(null)
const processedBlob = ref<Blob | null>(null)
const sourceProcessedBlob = ref<Blob | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const outputFormat = ref<'png' | 'webp'>('png')
const backgroundColor = ref<'transparent' | 'white' | 'black'>('transparent')
const isDragging = ref(false)
const compareMode = ref<'side-by-side' | 'slider'>('side-by-side')
const comparePosition = ref(50)
const showEditor = ref(false)
const editorCanvas = ref<HTMLCanvasElement | null>(null)
const brushSize = ref(40)
const history = ref<ImageData[]>([])
const historyIndex = ref(-1)
const batchInputRef = ref<HTMLInputElement | null>(null)
const batchFiles = ref<File[]>([])
const batchLoading = ref(false)
const batchDownload = ref<string | null>(null)
interface HistoryItem {
  id: number
  name: string
  createdAt: number
  size: number
  type: string
  blob: Blob
}
const historyItems = ref<HistoryItem[]>([])
const showHistory = ref(false)
const historyError = ref<string | null>(null)
let requestController: AbortController | null = null

const HISTORY_DB = 'image-eraser-history'
const HISTORY_STORE = 'results'
const HISTORY_LIMIT = 8
const HISTORY_MAX_BYTES = 100 * 1024 * 1024

const openHistoryDb = (): Promise<IDBDatabase> => new Promise((resolve, reject) => {
  const request = indexedDB.open(HISTORY_DB, 1)
  request.onupgradeneeded = () => request.result.createObjectStore(HISTORY_STORE, { keyPath: 'id' })
  request.onsuccess = () => resolve(request.result)
  request.onerror = () => reject(request.error)
})

const loadHistory = async () => {
  if (!import.meta.client) return
  try {
    const db = await openHistoryDb()
    const request = db.transaction(HISTORY_STORE, 'readonly').objectStore(HISTORY_STORE).getAll()
    request.onsuccess = () => {
      historyItems.value = (request.result as HistoryItem[]).sort((a, b) => b.createdAt - a.createdAt)
      db.close()
    }
    request.onerror = () => db.close()
  } catch {
    historyError.value = 'Riwayat lokal tidak tersedia di browser ini.'
  }
}

const saveToHistory = async (blob: Blob, name: string) => {
  if (!import.meta.client) return
  try {
    const db = await openHistoryDb()
    const items = [...historyItems.value]
    const item: HistoryItem = { id: Date.now(), name, createdAt: Date.now(), size: blob.size, type: blob.type, blob }
    items.unshift(item)
    let total = items.reduce((sum, current) => sum + current.size, 0)
    while (items.length > HISTORY_LIMIT || total > HISTORY_MAX_BYTES) total -= items.pop()?.size || 0
    const transaction = db.transaction(HISTORY_STORE, 'readwrite')
    transaction.objectStore(HISTORY_STORE).clear()
    items.forEach(current => transaction.objectStore(HISTORY_STORE).put(current))
    transaction.oncomplete = () => {
      db.close()
      historyItems.value = items
    }
    transaction.onerror = () => {
      db.close()
      historyError.value = 'Riwayat tidak bisa disimpan karena storage browser penuh.'
    }
  } catch {
    historyError.value = 'Riwayat tidak bisa disimpan karena storage browser penuh.'
  }
}

const deleteHistoryItem = async (id: number) => {
  const db = await openHistoryDb()
  const transaction = db.transaction(HISTORY_STORE, 'readwrite')
  transaction.objectStore(HISTORY_STORE).delete(id)
  transaction.oncomplete = () => { db.close(); historyItems.value = historyItems.value.filter(item => item.id !== id) }
}

const downloadHistory = (item: HistoryItem) => {
  const url = URL.createObjectURL(item.blob)
  const link = document.createElement('a')
  link.href = url
  link.download = item.name
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

const clearHistory = async () => {
  const db = await openHistoryDb()
  const transaction = db.transaction(HISTORY_STORE, 'readwrite')
  transaction.objectStore(HISTORY_STORE).clear()
  transaction.oncomplete = () => { db.close(); historyItems.value = [] }
}

const revokeUrl = (url: string | null) => {
  if (url) URL.revokeObjectURL(url)
}

const prepareOutput = async (blob: Blob) => {
  if (outputFormat.value === 'png' && backgroundColor.value === 'transparent') return blob
  const bitmap = await createImageBitmap(blob)
  const canvas = document.createElement('canvas')
  canvas.width = bitmap.width
  canvas.height = bitmap.height
  const context = canvas.getContext('2d')!
  if (backgroundColor.value !== 'transparent') {
    context.fillStyle = backgroundColor.value
    context.fillRect(0, 0, canvas.width, canvas.height)
  }
  context.drawImage(bitmap, 0, 0)
  bitmap.close()
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(result => result ? resolve(result) : reject(new Error('Gagal menyiapkan output')), `image/${outputFormat.value}`)
  })
}

const setProcessedBlob = async (blob: Blob) => {
  processedBlob.value = blob
  revokeUrl(processedImage.value)
  processedImage.value = URL.createObjectURL(blob)
}

const exportEditedCanvas = async () => {
  const canvas = editorCanvas.value
  if (!canvas) return
  const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Gagal menyiapkan hasil')), 'image/png'))
  await setProcessedBlob(await prepareOutput(blob))
}

const snapshotEditor = () => {
  const context = editorCanvas.value?.getContext('2d')
  if (!context || !editorCanvas.value) return
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(context.getImageData(0, 0, editorCanvas.value.width, editorCanvas.value.height))
  historyIndex.value = history.value.length - 1
}

const undoEditor = () => {
  if (historyIndex.value <= 0 || !editorCanvas.value) return
  historyIndex.value--
  editorCanvas.value.getContext('2d')?.putImageData(history.value[historyIndex.value], 0, 0)
  exportEditedCanvas()
}

const brushErase = (event: MouseEvent | TouchEvent) => {
  const canvas = editorCanvas.value
  if (!canvas) return
  const point = 'touches' in event ? event.touches[0] : event
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const context = canvas.getContext('2d')!
  context.save()
  context.globalCompositeOperation = 'destination-out'
  context.beginPath()
  context.arc((point.clientX - rect.left) * scaleX, (point.clientY - rect.top) * scaleY, brushSize.value / 2 * scaleX, 0, Math.PI * 2)
  context.fill()
  context.restore()
}

const openEditor = async () => {
  showEditor.value = true
  await nextTick()
  const canvas = editorCanvas.value
  if (!canvas || !processedBlob.value) return
  const bitmap = await createImageBitmap(processedBlob.value)
  canvas.width = bitmap.width
  canvas.height = bitmap.height
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0)
  bitmap.close()
  history.value = []
  historyIndex.value = -1
  snapshotEditor()
}

const handlePaste = (event: ClipboardEvent) => {
  const image = [...(event.clipboardData?.items || [])].find(item => item.type.startsWith('image/'))
  const blob = image?.getAsFile()
  if (blob) processFile(new File([blob], 'clipboard-image.png', { type: blob.type }))
}

const selectBatch = (event: Event) => {
  const files = [...((event.target as HTMLInputElement).files || [])]
  batchFiles.value = files.filter(file => file.type.startsWith('image/')).slice(0, 10)
}

const processBatch = async () => {
  if (!batchFiles.value.length) return
  batchLoading.value = true
  try {
    const form = new FormData()
    batchFiles.value.forEach(file => form.append('images', file))
    const response = await fetch(`${config.public.apiBase}/api/remove-bg/batch`, { method: 'POST', body: form })
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Batch gagal diproses')
    revokeUrl(batchDownload.value)
    batchDownload.value = URL.createObjectURL(await response.blob())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Batch gagal diproses'
  } finally {
    batchLoading.value = false
  }
}

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
  isDragging.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    processFile(event.dataTransfer.files[0])
  }
}

// 2. Logic memproses file untuk Preview awal
const processFile = (selectedFile: File) => {
  // Reset state
  errorMessage.value = null
  revokeUrl(originalPreview.value)
  revokeUrl(processedImage.value)
  processedBlob.value = null
  originalPreview.value = null
  processedImage.value = null
  file.value = null
  
  // Validasi tipe file
  if (!selectedFile.type.match('image.*')) {
    errorMessage.value = 'File harus berupa gambar (JPG, PNG, atau WEBP)'
    return
  }
  if (selectedFile.size > 10 * 1024 * 1024) {
    errorMessage.value = 'Ukuran gambar maksimal 10 MB'
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
  requestController?.abort()
  requestController = new AbortController()
  const timeout = window.setTimeout(() => requestController?.abort(), 120000)

  const formData = new FormData()
  formData.append('image', file.value)

  try {
    // Panggil API Backend
    const response = await fetch(`${config.public.apiBase}/api/remove-bg`, {
      method: 'POST',
      body: formData,
      signal: requestController.signal,
    })

    if (!response.ok) {
      const details = await response.json().catch(() => null)
      throw new Error(details?.detail || 'Gagal memproses gambar di server')
    }

    // Terima response sebagai BLOB (Binary Large Object)
    const blob = await prepareOutput(await response.blob())
    
    // Convert Blob ke URL agar bisa ditampilkan di <img>
    sourceProcessedBlob.value = blob
    await setProcessedBlob(blob)
    await saveToHistory(blob, file.value?.name || 'image-eraser-result.png')

  } catch (err) {
    errorMessage.value = err instanceof DOMException && err.name === 'AbortError'
      ? 'Proses dibatalkan atau terlalu lama. Silakan coba lagi.'
      : err instanceof Error ? err.message : 'Terjadi kesalahan saat menghubungi server AI.'
    console.error(err)
  } finally {
    window.clearTimeout(timeout)
    isLoading.value = false
    requestController = null
  }
}

// 4. Reset Ulang
const reset = () => {
  requestController?.abort()
  revokeUrl(originalPreview.value)
  revokeUrl(processedImage.value)
  file.value = null
  originalPreview.value = null
  processedImage.value = null
  processedBlob.value = null
  sourceProcessedBlob.value = null
  showEditor.value = false
  errorMessage.value = null
  if (inputRef.value) inputRef.value.value = ''
}

onBeforeUnmount(() => {
  requestController?.abort()
  revokeUrl(originalPreview.value)
  revokeUrl(processedImage.value)
  revokeUrl(batchDownload.value)
})

onMounted(loadHistory)

watch([outputFormat, backgroundColor], () => {
  if (sourceProcessedBlob.value && !showEditor.value) prepareOutput(sourceProcessedBlob.value).then(setProcessedBlob)
})
</script>

<template>
  <div @paste="handlePaste" class="min-h-screen bg-slate-900 text-white font-sans selection:bg-indigo-500 selection:text-white relative overflow-hidden">
    
    <div class="absolute top-0 left-0 w-96 h-96 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
    <div class="absolute top-0 right-0 w-96 h-96 bg-cyan-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>

    <div class="container mx-auto px-4 py-12 relative z-10 flex flex-col items-center min-h-screen justify-center">

      <div class="text-center mb-10 max-w-2xl">
        <h1 class="text-5xl md:text-6xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-indigo-500 mb-4 pb-2">
          Image Eraser
        </h1>
        <p class="text-slate-400 text-lg">
           Hapus latar belakang foto otomatis dengan hasil rapi untuk kebutuhan desain dan katalog.
          <br class="hidden md:block" />
           <span class="text-cyan-400 font-semibold">Gratis dan tanpa login.</span>
        </p>
      </div>

      <div class="w-full max-w-5xl bg-slate-800/40 backdrop-blur-xl border border-white/10 rounded-3xl p-6 md:p-10 shadow-2xl">

        <div class="mb-6 rounded-2xl border border-white/10 bg-slate-900/50 p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p class="font-semibold">Batch processing</p>
              <p class="text-xs text-slate-400">Pilih hingga 10 gambar, lalu download sebagai ZIP.</p>
            </div>
            <div class="flex gap-2">
              <input ref="batchInputRef" type="file" multiple accept="image/png,image/jpeg,image/webp" class="hidden" @change="selectBatch" />
              <button class="rounded-lg bg-slate-700 px-4 py-2 text-sm hover:bg-slate-600" @click="batchInputRef?.click()">Pilih banyak</button>
              <button v-if="batchFiles.length" class="rounded-lg bg-indigo-600 px-4 py-2 text-sm disabled:opacity-50" :disabled="batchLoading" @click="processBatch">{{ batchLoading ? 'Memproses...' : `Proses ${batchFiles.length} file` }}</button>
              <a v-if="batchDownload" :href="batchDownload" download="image-eraser-results.zip" class="rounded-lg bg-green-600 px-4 py-2 text-sm">Download ZIP</a>
            </div>
          </div>
        </div>

        <div class="mb-6">
          <button class="rounded-lg border border-white/10 bg-slate-700 px-4 py-2 text-sm" @click="showHistory = !showHistory">{{ showHistory ? 'Tutup riwayat' : `Riwayat lokal (${historyItems.length})` }}</button>
          <div v-if="showHistory" class="mt-3 rounded-2xl border border-white/10 bg-slate-900/60 p-4">
            <div class="mb-3 flex items-center justify-between"><p class="text-sm text-slate-300">Maksimal 8 hasil atau 100 MB, tersimpan hanya di browser ini.</p><button v-if="historyItems.length" class="text-xs text-red-300 hover:text-red-200" @click="clearHistory">Hapus semua</button></div>
            <p v-if="historyError" role="alert" class="mb-2 text-xs text-red-300">{{ historyError }}</p>
            <div v-if="!historyItems.length" class="text-sm text-slate-500">Belum ada riwayat.</div>
            <div v-for="item in historyItems" :key="item.id" class="flex items-center justify-between gap-3 border-t border-white/5 py-2 text-sm">
              <span class="truncate">{{ item.name }} <small class="text-slate-500">({{ (item.size / 1024).toFixed(0) }} KB)</small></span>
              <div class="flex gap-2"><button class="text-cyan-300" @click="downloadHistory(item)">Download</button><button class="text-red-300" @click="deleteHistoryItem(item.id)">Hapus</button></div>
            </div>
          </div>
        </div>
        
        <div 
          v-if="!originalPreview"
          @dragover.prevent 
          @drop="handleDrop"
          class="group relative border-2 border-dashed border-slate-600 hover:border-cyan-400 rounded-2xl p-16 text-center transition-all duration-300 bg-slate-800/50 hover:bg-slate-800/80 cursor-pointer"
        >
           <input ref="inputRef" type="file" @change="handleFileSelect" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20" accept="image/png,image/jpeg,image/webp" aria-label="Pilih gambar" />
          
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
                <img :src="originalPreview" alt="Preview gambar asli" class="max-w-full max-h-full object-contain" />
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

                 <div v-if="processedImage && backgroundColor !== 'transparent'" class="absolute inset-0" :class="backgroundColor === 'white' ? 'bg-white' : 'bg-black'"></div>
                 <img v-if="processedImage" :src="processedImage" alt="Preview gambar tanpa background" class="relative z-10 max-w-full max-h-full object-contain" />
               </div>
               <div v-if="processedImage" class="flex items-center justify-between gap-2 text-xs text-slate-400">
                 <button class="rounded bg-slate-700 px-3 py-2 text-white" @click="compareMode = compareMode === 'side-by-side' ? 'slider' : 'side-by-side'">{{ compareMode === 'slider' ? 'Side by side' : 'Before / after slider' }}</button>
                 <button class="rounded bg-cyan-700 px-3 py-2 text-white" @click="openEditor">Edit mask</button>
               </div>
               <div v-if="processedImage && compareMode === 'slider'" class="space-y-2">
                 <input v-model.number="comparePosition" type="range" min="0" max="100" class="w-full accent-cyan-400" aria-label="Posisi perbandingan" />
                 <div class="relative aspect-video overflow-hidden rounded-xl border border-white/10">
                   <img :src="originalPreview" alt="Before" class="absolute inset-0 h-full w-full object-contain" />
                   <div class="absolute inset-y-0 left-0 overflow-hidden" :style="{ width: `${comparePosition}%` }"><img :src="processedImage" alt="After" class="h-full max-w-none object-contain" :style="{ width: `${100 / Math.max(comparePosition, 1) * 100}%` }" /></div>
                 </div>
               </div>
             </div>
          </div>

          <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center border-t border-white/10 pt-4">
            <label class="text-sm text-slate-300">Format output
              <select v-model="outputFormat" class="ml-2 rounded-lg bg-slate-700 px-3 py-2 text-white" :disabled="!!processedImage">
                <option value="png">PNG transparan</option>
                <option value="webp">WEBP</option>
              </select>
            </label>
            <label class="text-sm text-slate-300">Background
              <select v-model="backgroundColor" class="ml-2 rounded-lg bg-slate-700 px-3 py-2 text-white" :disabled="!!processedImage">
                <option value="transparent">Transparan</option>
                <option value="white">Putih</option>
                <option value="black">Hitam</option>
              </select>
            </label>
          </div>

          <div v-if="showEditor" class="rounded-2xl border border-cyan-400/30 bg-slate-900/70 p-4">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div><p class="font-semibold">Editor mask manual</p><p class="text-xs text-slate-400">Gambar area yang ingin dihapus.</p></div>
              <div class="flex items-center gap-2"><label class="text-xs text-slate-300">Brush <input v-model.number="brushSize" type="range" min="5" max="200" class="accent-cyan-400" /></label><button class="rounded bg-slate-700 px-3 py-2 text-xs" :disabled="historyIndex <= 0" @click="undoEditor">Undo</button><button class="rounded bg-green-600 px-3 py-2 text-xs" @click="exportEditedCanvas">Terapkan</button></div>
            </div>
            <canvas ref="editorCanvas" class="mx-auto max-h-[60vh] max-w-full rounded-lg bg-[url('data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2740%27 height=%2740%27%3E%3Crect width=%2720%27 height=%2720%27 fill=%27%234b5563%27/%3E%3Crect x=%2720%27 y=%2720%27 width=%2720%27 height=%2720%27 fill=%27%234b5563%27/%3E%3C/svg%3E')]" @mousedown="brushErase" @mousemove="($event.buttons ? brushErase($event) : undefined)" @mouseup="snapshotEditor" @touchmove.prevent="brushErase" @touchend="snapshotEditor"></canvas>
          </div>

           <div v-if="errorMessage" role="alert" class="bg-red-500/10 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg text-sm text-center">
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
               :download="`image-eraser-result.${outputFormat}`"
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
           File diproses sementara dan tidak disimpan setelah proses selesai.
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
