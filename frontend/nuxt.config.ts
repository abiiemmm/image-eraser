// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: ['@nuxtjs/tailwindcss'],

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
