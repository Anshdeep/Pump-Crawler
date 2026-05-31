import { defineStore } from 'pinia'
import axios from 'axios'

export const useCompressorStore = defineStore('compressors', {
  state: () => ({
    compressorTree: [],
    models: [],
    selectedModel: null,
    modelDetailsLoading: false,
    brandsList: [],
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

    async fetchBrandsList() {
      try {
        const res = await axios.get('/api/manufacturers')
        this.brandsList = res.data
      } catch (err) {
        console.error('Failed to fetch brands list:', err)
      }
    },

    async toggleBrandApproval(manufacturerId, isApproved) {
      try {
        await axios.put(`/api/manufacturers/${manufacturerId}/approve`, null, {
          params: { is_approved: isApproved }
        })
        await this.fetchBrandsList()
      } catch (err) {
        console.error(`Failed to toggle brand approval for ID ${manufacturerId}:`, err)
        throw err
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

    async triggerBrandDiscovery(compressorType = null, noCache = false) {
      this.crawlLoading = true
      try {
        const res = await axios.post('/api/crawl/discover-brands', null, {
          params: {
            compressor_type: compressorType,
            no_cache: noCache
          }
        })
        await this.fetchCrawlStatus()
        await this.fetchCrawlHistory()
        return res.data
      } catch (err) {
        console.error('Failed to trigger background brand discovery:', err)
        throw err
      } finally {
        this.crawlLoading = false
      }
    },

    async triggerSpecsHarvester(noCache = false) {
      this.crawlLoading = true
      try {
        const res = await axios.post('/api/crawl/harvest-specs', null, {
          params: {
            no_cache: noCache
          }
        })
        await this.fetchCrawlStatus()
        await this.fetchCrawlHistory()
        return res.data
      } catch (err) {
        console.error('Failed to trigger specs harvesting:', err)
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
