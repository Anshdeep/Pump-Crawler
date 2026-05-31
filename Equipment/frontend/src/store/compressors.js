import { defineStore } from 'pinia'
import axios from 'axios'

export const useCompressorStore = defineStore('compressors', {
  state: () => ({
    compressorTree: [],
    models: [],
    selectedModel: null,
    modelDetailsLoading: false,
    crawlStatus: {
      active: false,
      compressor_type: null,
      stage: 'idle',
      percent: 0,
      status_msg: 'System idle',
      started_at: null,
      completed_at: null,
      discovered_manufacturers: 0,
      discovered_models: 0,
      enriched_records: 0,
    },
    crawlLoading: false,
    crawlHistory: [],
  }),
  
  actions: {
    async fetchCompressors() {
      try {
        const res = await axios.get('/api/compressors')
        this.compressorTree = res.data
      } catch (err) {
        console.error('Failed to fetch compressors tree:', err)
      }
    },

    async fetchModels(filters = {}) {
      try {
        const res = await axios.get('/api/models', { params: filters })
        this.models = res.data
      } catch (err) {
        console.error('Failed to fetch models list:', err)
      }
    },

    async fetchModelDetails(modelId) {
      this.modelDetailsLoading = true
      try {
        const res = await axios.get(`/api/models/${modelId}`)
        this.selectedModel = res.data
      } catch (err) {
        console.error(`Failed to fetch model details for ID ${modelId}:`, err)
      } finally {
        this.modelDetailsLoading = false
      }
    },

    async fetchCrawlStatus() {
      try {
        const res = await axios.get('/api/crawl/status')
        this.crawlStatus = res.data
      } catch (err) {
        console.error('Failed to fetch crawler status:', err)
      }
    },

    async fetchCrawlHistory() {
      try {
        const res = await axios.get('/api/crawl/history')
        this.crawlHistory = res.data
      } catch (err) {
        console.error('Failed to fetch crawl history:', err)
      }
    },

    async triggerCrawl(compressorType = null, noCache = false) {
      this.crawlLoading = true
      try {
        const res = await axios.post('/api/crawl', null, {
          params: {
            compressor_type: compressorType,
            no_cache: noCache
          }
        })
        await this.fetchCrawlStatus()
        await this.fetchCrawlHistory()
        return res.data
      } catch (err) {
        console.error('Failed to trigger background crawl:', err)
        throw err
      } finally {
        this.crawlLoading = false
      }
    },

    async initializeDatabase() {
      try {
        const res = await axios.post('/api/init-db')
        return res.data
      } catch (err) {
        console.error('Failed to initialize database tables:', err)
        throw err
      }
    }
  }
})
