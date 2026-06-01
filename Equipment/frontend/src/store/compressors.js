import { defineStore } from 'pinia'
import axios from 'axios'

export const useCompressorStore = defineStore('compressors', {
  state: () => ({
    compressorTree: [],
    models: [],
    selectedModel: null,
    modelDetailsLoading: false,
    manufacturersList: [],  // Master list of manufacturer registries
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
    
    // ── Generalized Taxonomy & Settings State ──────────────────────────────
    equipmentMasters: [],
    equipmentTypes: [],
    equipmentSubtypes: [],
    systemSettings: [],
    taxonomyTree: [],
    dashboardStats: null,
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

    async fetchManufacturersList() {
      try {
        const res = await axios.get('/api/manufacturers')
        this.manufacturersList = res.data
      } catch (err) {
        console.error('Failed to fetch manufacturers list:', err)
      }
    },

    async toggleManufacturerApproval(manufacturerId, isApproved) {
      try {
        await axios.put(`/api/manufacturers/${manufacturerId}/approve`, null, {
          params: { is_approved: isApproved }
        })
        await this.fetchManufacturersList()
      } catch (err) {
        console.error(`Failed to toggle manufacturer approval for ID ${manufacturerId}:`, err)
        throw err
      }
    },

    async toggleModelApproval(modelId, isApproved) {
      try {
        await axios.put(`/api/models/${modelId}/approve`, null, {
          params: { is_approved: isApproved }
        })
        if (this.selectedModel && this.selectedModel.id === modelId) {
          this.selectedModel.is_approved = isApproved
        }
      } catch (err) {
        console.error(`Failed to toggle model approval for ID ${modelId}:`, err)
        throw err
      }
    },

    async bulkApproveModels(modelIds, isApproved) {
      try {
        await axios.put('/api/models/bulk-approve', {
          model_ids: modelIds,
          is_approved: isApproved
        })
        // Update local state models
        this.models.forEach(m => {
          if (modelIds.includes(m.id)) {
            m.is_approved = isApproved
          }
        })
        if (this.selectedModel && modelIds.includes(this.selectedModel.id)) {
          this.selectedModel.is_approved = isApproved
        }
      } catch (err) {
        console.error('Failed bulk models approval:', err)
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

    // ── Crawler triggers ────────────────────────────────────────────────────

    async triggerManufacturerDiscovery(equipmentTypeId = null, noCache = false) {
      this.crawlLoading = true
      try {
        const res = await axios.post('/api/crawl/discover-manufacturers', null, {
          params: {
            equipment_type_id: equipmentTypeId,
            no_cache: noCache
          }
        })
        await this.fetchCrawlStatus()
        await this.fetchCrawlHistory()
        return res.data
      } catch (err) {
        console.error('Failed to trigger background manufacturer discovery:', err)
        throw err
      } finally {
        this.crawlLoading = false
      }
    },

    async triggerSpecsHarvester(manufacturerIds = null, onlyUnharvested = false, noCache = false, modelIds = null, deepCrawl = true) {
      this.crawlLoading = true
      try {
        // Axios handles array parameters automatically
        const res = await axios.post('/api/crawl/harvest-specs', null, {
          params: {
            manufacturer_ids: manufacturerIds,
            model_ids: modelIds,
            deep_crawl: deepCrawl,
            only_unharvested: onlyUnharvested,
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

    async stopCrawl() {
      try {
        const res = await axios.post('/api/crawl/stop')
        await this.fetchCrawlStatus()
        await this.fetchCrawlHistory()
        return res.data
      } catch (err) {
        console.error('Failed to stop background crawl:', err)
        throw err
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
    },

    // ── Taxonomy & System Config CRUD Actions ────────────────────────────────

    async fetchTaxonomyTree() {
      try {
        const res = await axios.get('/api/taxonomy/tree')
        this.taxonomyTree = res.data
      } catch (err) {
        console.error('Failed to fetch taxonomy tree:', err)
      }
    },

    async fetchSettings() {
      try {
        const res = await axios.get('/api/settings')
        this.systemSettings = res.data
      } catch (err) {
        console.error('Failed to fetch system settings:', err)
      }
    },

    async fetchDashboardStats() {
      try {
        const res = await axios.get('/api/dashboard-stats')
        this.dashboardStats = res.data
      } catch (err) {
        console.error('Failed to fetch dashboard charts stats:', err)
      }
    },

    async updateSetting(key, value) {
      try {
        await axios.put(`/api/settings/${key}`, null, {
          params: { value: value }
        })
        await this.fetchSettings()
      } catch (err) {
        console.error(`Failed to update system setting '${key}':`, err)
        throw err
      }
    },

    // Equipment Masters
    async createMaster(name, description) {
      const res = await axios.post('/api/equipment-masters', { name, description })
      await this.fetchTaxonomyTree()
      return res.data
    },
    async updateMaster(id, name, description) {
      const res = await axios.put(`/api/equipment-masters/${id}`, { name, description })
      await this.fetchTaxonomyTree()
      return res.data
    },
    async deleteMaster(id) {
      await axios.delete(`/api/equipment-masters/${id}`)
      await this.fetchTaxonomyTree()
    },

    // Equipment Types
    async createType(name, equipmentMasterId, description) {
      const res = await axios.post('/api/equipment-types', { name, equipment_master_id: equipmentMasterId, description })
      await this.fetchTaxonomyTree()
      return res.data
    },
    async updateType(id, name, equipmentMasterId, description) {
      const res = await axios.put(`/api/equipment-types/${id}`, { name, equipment_master_id: equipmentMasterId, description })
      await this.fetchTaxonomyTree()
      return res.data
    },
    async deleteType(id) {
      await axios.delete(`/api/equipment-types/${id}`)
      await this.fetchTaxonomyTree()
    },

    // Subtypes
    async createSubtype(name, typeId) {
      const res = await axios.post('/api/equipment-subtypes', { name, type_id: typeId })
      await this.fetchTaxonomyTree()
      return res.data
    },
    async updateSubtype(id, name, typeId) {
      const res = await axios.put(`/api/equipment-subtypes/${id}`, { name, type_id: typeId })
      await this.fetchTaxonomyTree()
      return res.data
    },
    async deleteSubtype(id) {
      await axios.delete(`/api/equipment-subtypes/${id}`)
      await this.fetchTaxonomyTree()
    },

    // Manufacturers CRUD
    async createManufacturer(data) {
      const res = await axios.post('/api/manufacturers', data)
      await this.fetchManufacturersList()
      return res.data
    },
    async updateManufacturer(id, data) {
      const res = await axios.put(`/api/manufacturers/${id}`, data)
      await this.fetchManufacturersList()
      return res.data
    },
    async deleteManufacturer(id) {
      await axios.delete(`/api/manufacturers/${id}`)
      await this.fetchManufacturersList()
    }
  }
})
