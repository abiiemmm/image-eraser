// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: ['@nuxtjs/tailwindcss'],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'
    }
  },

  app: {
    head: {
      title: 'Image Eraser',
      meta: [
        { name: 'description', content: 'Hapus background gambar gratis, cepat, tanpa login.' },
        { property: 'og:title', content: 'Image Eraser' },
        { property: 'og:description', content: 'Hapus background gambar dengan AI tanpa login.' },
        { property: 'og:type', content: 'website' }
      ]
    }
  },

  compatibilityDate: '2025-07-15',
  devtools: { enabled: true }
})
