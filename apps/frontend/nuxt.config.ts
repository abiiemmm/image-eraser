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
      title: 'Magic Eraser',
      meta: [
        { name: 'description', content: 'Hapus background gambar gratis, cepat, tanpa login.' }
      ]
    }
  },

  compatibilityDate: '2025-07-15',
  devtools: { enabled: true }
})
