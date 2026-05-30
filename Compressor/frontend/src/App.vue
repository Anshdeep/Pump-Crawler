<template>
  <v-app class="glass-panel" style="background: transparent !important;">
    <!-- --- App Header Bar --- -->
    <v-app-bar flat class="glass-panel px-6" height="70" border="bottom">
      <v-avatar color="primary" class="mr-3" size="42" elevation="6">
        <v-icon icon="mdi-compressor" color="white" size="24"></v-icon>
      </v-avatar>
      <v-app-bar-title class="outfit-font font-weight-bold text-h5">
        Compressor<span class="glow-text-primary">Crawler</span>
      </v-app-bar-title>

      <v-spacer></v-spacer>

      <v-tabs v-model="tab" color="primary" align-tabs="end">
        <v-tab value="catalog" class="outfit-font text-subtitle-1 text-capitalize px-6">
          <v-icon start icon="mdi-database-search" class="mr-1"></v-icon> Specs Catalog
        </v-tab>
        <v-tab value="crawler" class="outfit-font text-subtitle-1 text-capitalize px-6">
          <v-icon start icon="mdi-robot-mower" class="mr-1"></v-icon> Control Center
        </v-tab>
      </v-tabs>
    </v-app-bar>

    <!-- --- Main Content View --- -->
    <v-main class="mt-4">
      <v-container fluid class="px-6 py-4">
        
        <v-window v-model="tab">
          <!-- ── TAB 1: SPECS CATALOG ── -->
          <v-window-item value="catalog">
            <v-row>
              <!-- Left Search & Filter Sidebar -->
              <v-col cols="12" md="3">
                <v-card class="glass-card pa-5 mb-4" rounded="lg">
                  <h3 class="outfit-font text-h6 font-weight-bold mb-4 glow-text-secondary">
                    <v-icon icon="mdi-filter-variant" class="mr-2" size="20"></v-icon>Filter Database
                  </h3>

                  <!-- Search field -->
                  <v-text-field
                    v-model="filters.q"
                    label="Search Models"
                    prepend-inner-icon="mdi-magnify"
                    variant="outlined"
                    density="comfortable"
                    color="secondary"
                    clearable
                    class="mb-3"
                    @update:model-value="debouncedFetchModels"
                  ></v-text-field>

                  <!-- Category Type Dropdown -->
                  <v-autocomplete
                    v-model="filters.type_id"
                    :items="compressorTypes"
                    item-title="name"
                    item-value="id"
                    label="Compressor Type"
                    prepend-inner-icon="mdi-shape-outline"
                    variant="outlined"
                    density="comfortable"
                    color="secondary"
                    clearable
                    class="mb-3"
                    @update:model-value="fetchModels"
                  ></v-autocomplete>

                  <!-- Manufacturer Dropdown -->
                  <v-autocomplete
                    v-model="filters.manufacturer_id"
                    :items="manufacturers"
                    item-title="name"
                    item-value="id"
                    label="Manufacturer"
                    prepend-inner-icon="mdi-domain"
                    variant="outlined"
                    density="comfortable"
                    color="secondary"
                    clearable
                    @update:model-value="fetchModels"
                  ></v-autocomplete>

                  <v-divider class="my-4 rgba(255,255,255,0.05)"></v-divider>

                  <v-btn
                    block
                    variant="tonal"
                    color="secondary"
                    prepend-icon="mdi-refresh"
                    class="outfit-font text-capitalize"
                    @click="resetFilters"
                  >
                    Reset Filters
                  </v-btn>
                </v-card>
              </v-col>

              <!-- Central Models Results Grid -->
              <v-col cols="12" md="9">
                <v-row v-if="models.length > 0">
                  <v-col
                    v-for="model in models"
                    :key="model.id"
                    cols="12"
                    sm="6"
                    md="4"
                  >
                    <v-card class="glass-card pa-4 d-flex flex-column h-100" rounded="lg" @click="viewDetails(model.id)">
                      <div class="d-flex justify-space-between align-center mb-3">
                        <span class="text-caption text-secondary font-weight-bold text-uppercase">
                          {{ model.compressor_type }}
                        </span>
                        <v-chip size="x-small" color="primary" variant="flat">
                          {{ model.manufacturer }}
                        </v-chip>
                      </div>

                      <h4 class="outfit-font text-h6 font-weight-bold white--text mb-1">
                        {{ model.model_name }}
                      </h4>
                      <p class="text-subtitle-2 text-medium-emphasis mb-4">
                        Series: {{ model.series || 'Standard Line' }}
                      </p>

                      <v-spacer></v-spacer>

                      <div class="d-flex justify-space-between align-center mt-3">
                        <span class="text-caption text-medium-emphasis">
                          <v-icon icon="mdi-eye" start size="14"></v-icon>Click to view specs
                        </span>
                        <v-icon icon="mdi-chevron-right" color="secondary"></v-icon>
                      </div>
                    </v-card>
                  </v-col>
                </v-row>

                <!-- Empty State -->
                <v-card v-else class="glass-card pa-12 text-center" rounded="lg">
                  <v-avatar color="rgba(6, 182, 212, 0.1)" size="72" class="mb-4">
                    <v-icon icon="mdi-database-alert" color="secondary" size="36"></v-icon>
                  </v-avatar>
                  <h3 class="outfit-font text-h5 font-weight-bold mb-2">No Models Found</h3>
                  <p class="text-body-1 text-medium-emphasis mb-6">
                    Try adjusting your filters, or go to the Control Center to start the crawler pipeline.
                  </p>
                </v-card>
              </v-col>
            </v-row>
          </v-window-item>

          <!-- ── TAB 2: CRAWLER CONTROL CENTER ── -->
          <v-window-item value="crawler">
            <v-row class="justify-center">
              <v-col cols="12" md="8">
                <!-- Database Initialization Card -->
                <v-card class="glass-card pa-6 mb-6" rounded="lg">
                  <div class="d-flex justify-space-between align-center">
                    <div>
                      <h3 class="outfit-font text-h5 font-weight-bold mb-1 white--text">
                        <v-icon icon="mdi-database-cog" color="primary" class="mr-2"></v-icon>Database Initialization
                      </h3>
                      <p class="text-body-2 text-medium-emphasis">
                        Spin up the PostgreSQL schema, register pgvector extensions, and create base schemas.
                      </p>
                    </div>
                    <v-btn
                      color="primary"
                      prepend-icon="mdi-database-import"
                      class="outfit-font text-capitalize px-6"
                      elevation="4"
                      :loading="initLoading"
                      @click="triggerDbInit"
                    >
                      Init PostgreSQL
                    </v-btn>
                  </div>
                </v-card>

                <!-- Crawler Setup Options -->
                <v-card class="glass-card pa-6 mb-6" rounded="lg">
                  <h3 class="outfit-font text-h5 font-weight-bold mb-4 glow-text-secondary">
                    <v-icon icon="mdi-robot-mower" class="mr-2"></v-icon>Launch Crawler Pipeline
                  </h3>
                  
                  <v-row>
                    <v-col cols="12" sm="6">
                      <v-select
                        v-model="crawlParams.compressor_type"
                        :items="crawlTypeOptions"
                        label="Target Compressor Type"
                        variant="outlined"
                        density="comfortable"
                        color="secondary"
                        hint="Leave blank to crawl all categories end-to-end"
                        persistent-hint
                      ></v-select>
                    </v-col>
                    
                    <v-col cols="12" sm="6" class="d-flex align-center">
                      <v-switch
                        v-model="crawlParams.no_cache"
                        label="Bypass Crawler Web Cache (Force Fresh Search)"
                        color="secondary"
                        inset
                        hide-details
                      ></v-switch>
                    </v-col>
                  </v-row>

                  <v-divider class="my-5 opacity-10"></v-divider>

                  <v-btn
                    color="secondary"
                    block
                    height="50"
                    prepend-icon="mdi-play-circle"
                    class="outfit-font text-capitalize text-h6 font-weight-bold"
                    elevation="6"
                    :disabled="store.crawlStatus.active"
                    :loading="store.crawlLoading"
                    @click="triggerCrawl"
                  >
                    Start Crawler Pipeline Task
                  </v-btn>
                </v-card>

                <!-- Crawler Live Progress Progress Card -->
                <v-card class="glass-card pa-6" rounded="lg">
                  <div class="d-flex justify-space-between align-center mb-4">
                    <h3 class="outfit-font text-h5 font-weight-bold white--text">
                      <v-icon icon="mdi-pulse" color="secondary" class="mr-2"></v-icon>Live Crawler Tracker
                    </h3>
                    <v-chip
                      :color="statusChipColor"
                      variant="flat"
                      class="text-uppercase font-weight-bold outfit-font px-4"
                      size="small"
                    >
                      <v-icon start :icon="statusChipIcon"></v-icon>
                      {{ store.crawlStatus.stage }}
                    </v-chip>
                  </div>

                  <!-- Progress Bar -->
                  <v-progress-linear
                    v-model="store.crawlStatus.percent"
                    color="secondary"
                    height="12"
                    rounded
                    striped
                    class="mb-3"
                  ></v-progress-linear>

                  <div class="d-flex justify-space-between text-body-2 text-medium-emphasis mb-6">
                    <span>Status: {{ store.crawlStatus.status_msg }}</span>
                    <span class="font-weight-bold text-white">{{ store.crawlStatus.percent }}%</span>
                  </div>

                  <!-- Metrics Display -->
                  <v-row class="text-center">
                    <v-col cols="4">
                      <v-card class="pa-4 bg-rgba(255,255,255,0.02)" rounded="lg" border>
                        <div class="text-h4 outfit-font font-weight-bold text-white mb-1">
                          {{ store.crawlStatus.discovered_manufacturers }}
                        </div>
                        <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">
                          Manufacturers
                        </div>
                      </v-card>
                    </v-col>
                    
                    <v-col cols="4">
                      <v-card class="pa-4 bg-rgba(255,255,255,0.02)" rounded="lg" border>
                        <div class="text-h4 outfit-font font-weight-bold text-white mb-1">
                          {{ store.crawlStatus.discovered_models }}
                        </div>
                        <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">
                          Models Discovered
                        </div>
                      </v-card>
                    </v-col>

                    <v-col cols="4">
                      <v-card class="pa-4 bg-rgba(255,255,255,0.02)" rounded="lg" border>
                        <div class="text-h4 outfit-font font-weight-bold glow-text-secondary mb-1">
                          {{ store.crawlStatus.enriched_records }}
                        </div>
                        <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">
                          Specs Enriched
                        </div>
                      </v-card>
                    </v-col>
                  </v-row>
                </v-card>
              </v-col>
            </v-row>
          </v-window-item>
        </v-window>

      </v-container>
    </v-main>

    <!-- ── DYNAMIC RIGHT DRAWERS: MODEL TECHNICAL SPEC SHEETS ── -->
    <v-navigation-drawer
      v-model="drawer"
      location="right"
      width="480"
      temporary
      class="glass-panel border-left"
    >
      <v-progress-linear
        v-if="store.modelDetailsLoading"
        indeterminate
        color="secondary"
      ></v-progress-linear>

      <div v-if="selectedModel" class="pa-6 d-flex flex-column h-100 overflow-y-auto">
        <!-- Close Drawer Button -->
        <div class="d-flex justify-end mb-2">
          <v-btn icon="mdi-close" variant="text" color="medium-emphasis" @click="drawer = false"></v-btn>
        </div>

        <!-- Model Heading Header -->
        <div class="mb-6">
          <span class="text-caption text-secondary font-weight-bold text-uppercase">
            {{ selectedModel.compressor_type }}
          </span>
          <h2 class="outfit-font text-h4 font-weight-bold glow-text-primary mt-1 mb-2">
            {{ selectedModel.model_name }}
          </h2>
          <v-chip color="primary" class="font-weight-bold">{{ selectedModel.manufacturer.name }}</v-chip>
        </div>

        <!-- Manufacturer Brand Card -->
        <v-card class="pa-4 mb-6 bg-rgba(255,255,255,0.02)" border rounded="lg">
          <h4 class="outfit-font font-weight-bold mb-2">
            <v-icon icon="mdi-domain" start size="16" color="secondary"></v-icon>Manufacturer Details
          </h4>
          <p class="text-body-2 text-medium-emphasis mb-3">
            HQ: {{ selectedModel.manufacturer.country || 'Global HQ' }}
          </p>
          <v-btn
            v-if="selectedModel.manufacturer.website"
            :href="'https://' + selectedModel.manufacturer.website"
            target="_blank"
            variant="tonal"
            size="small"
            color="secondary"
            prepend-icon="mdi-open-in-new"
            class="text-capitalize"
          >
            Visit Website
          </v-btn>
        </v-card>

        <v-divider class="mb-6 opacity-10"></v-divider>

        <!-- Technical Attributes Specifications Sheet -->
        <div class="flex-grow-1">
          <h3 class="outfit-font text-h6 font-weight-bold mb-4 white--text">
            <v-icon icon="mdi-chart-bell-curve-cumulative" start color="secondary"></v-icon>Technical Specifications
          </h3>

          <!-- Attributes Grid -->
          <v-row v-if="hasSpecs" dense>
            <v-col
              v-for="(val, key) in filteredAttributes"
              :key="key"
              cols="12"
              sm="6"
              class="mb-3"
            >
              <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">
                {{ formatKey(key) }}
              </div>
              <div class="text-body-1 text-white font-weight-medium">
                {{ formatVal(key, val) }}
              </div>
            </v-col>
          </v-row>

          <!-- No Specs Warning -->
          <div v-else class="text-center py-12 text-medium-emphasis">
            <v-icon icon="mdi-file-cancel-outline" size="48" class="mb-2"></v-icon>
            <p>No specifications extracted for this model yet.</p>
          </div>
        </div>

        <!-- Footer Direct Link -->
        <v-btn
          v-if="selectedModel.product_url"
          :href="selectedModel.product_url"
          target="_blank"
          block
          color="secondary"
          prepend-icon="mdi-card-text-outline"
          class="outfit-font text-capitalize mt-6"
        >
          View Technical Catalog Page
        </v-btn>
      </div>
    </v-navigation-drawer>

    <!-- Dynamic Success/Error Toast Feedback Snackbars -->
    <v-snackbar v-model="toast.active" :color="toast.color" timeout="3000" rounded="lg">
      {{ toast.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useCompressorStore } from './store/compressors'

const store = useCompressorStore()

// State
const tab = ref('catalog')
const drawer = ref(false)
const initLoading = ref(false)

const filters = ref({
  q: '',
  type_id: null,
  manufacturer_id: null
})

const crawlParams = ref({
  compressor_type: null,
  no_cache: false
})

const toast = ref({
  active: false,
  message: '',
  color: 'success'
})

// Lifecycle
onMounted(async () => {
  await store.fetchCompressors()
  await store.fetchModels()
  await store.fetchCrawlStatus()
  
  // Periodically poll crawl status if a task is active in background
  setInterval(() => {
    if (store.crawlStatus.active) {
      store.fetchCrawlStatus()
      // Refresh tree and lists upon completion
      if (store.crawlStatus.percent === 100) {
        store.fetchCompressors()
        store.fetchModels(filters.value)
      }
    }
  }, 3000)
})

// Computeds
const models = computed(() => store.models || [])

const compressorTypes = computed(() => {
  return (store.compressorTree || []).map(t => ({ id: t.id, name: t.name }))
})

const manufacturers = computed(() => {
  const list = []
  const ids = new Set()
  
  const tree = store.compressorTree || []
  tree.forEach(t => {
    if (filters.value.type_id && t.id !== filters.value.type_id) return
    const items = t.manufacturers || []
    items.forEach(m => {
      if (!ids.has(m.id)) {
        ids.add(m.id)
        list.push({ id: m.id, name: m.name })
      }
    })
  })
  return list
})

const crawlTypeOptions = computed(() => {
  const options = (store.compressorTree || []).map(t => t.name)
  return [ { title: 'Crawl All Categories', value: null }, ...options ]
})

const selectedModel = computed(() => store.selectedModel)

const hasSpecs = computed(() => {
  return selectedModel.value && 
         selectedModel.value.attributes && 
         Object.keys(selectedModel.value.attributes).length > 0 &&
         Object.values(selectedModel.value.attributes).some(v => v !== null)
})

// Filter out null/empty spec sheet attributes
const filteredAttributes = computed(() => {
  if (!selectedModel.value || !selectedModel.value.attributes) return {}
  const attrs = {}
  Object.entries(selectedModel.value.attributes).forEach(([k, v]) => {
    if (v !== null && v !== "" && k !== "manufacturer" && k !== "model" && k !== "compressor_type") {
      attrs[k] = v
    }
  })
  return attrs
})

// Crawler Status computes
const statusChipColor = computed(() => {
  const stage = (store.crawlStatus?.stage || 'idle').toLowerCase()
  if (stage.includes('completed')) return 'success'
  if (stage.includes('failed')) return 'error'
  if (stage.includes('idle')) return 'rgba(255,255,255,0.1)'
  return 'warning'
})

const statusChipIcon = computed(() => {
  const stage = (store.crawlStatus?.stage || 'idle').toLowerCase()
  if (stage.includes('completed')) return 'mdi-check-circle'
  if (stage.includes('failed')) return 'mdi-alert-circle'
  if (stage.includes('idle')) return 'mdi-pause'
  return 'mdi-sync'
})

// Debounce timer
let debounceTimer = null
const debouncedFetchModels = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchModels()
  }, 350)
}

// Methods
const fetchModels = () => {
  store.fetchModels(filters.value)
}

const resetFilters = () => {
  filters.value = {
    q: '',
    type_id: null,
    manufacturer_id: null
  }
  fetchModels()
}

const viewDetails = async (modelId) => {
  drawer.value = true
  await store.fetchModelDetails(modelId)
}

const triggerDbInit = async () => {
  initLoading.value = true
  try {
    const res = await store.initializeDatabase()
    showToast(res.message, 'success')
  } catch (err) {
    showToast('Failed to initialize database.', 'error')
  } finally {
    initLoading.value = false
  }
}

const triggerCrawl = async () => {
  try {
    const res = await store.triggerCrawl(
      crawlParams.value.compressor_type,
      crawlParams.value.no_cache
    )
    showToast(res.message, 'success')
  } catch (err) {
    showToast('Failed to trigger background crawl task.', 'error')
  }
}

const showToast = (message, color = 'success') => {
  toast.value = {
    active: true,
    message,
    color
  }
}

// Spec Formatter helpers
const formatKey = (key) => {
  return key.replace(/_/g, ' ')
}

const formatVal = (key, val) => {
  if (Array.isArray(val)) return val.join(', ')
  if (typeof val === 'number') {
    if (key.includes('pressure_psi')) return `${val} PSI`
    if (key.includes('pressure_bar')) return `${val} bar`
    if (key.includes('capacity_cfm')) return `${val} CFM`
    if (key.includes('power_kw')) return `${val} kW`
    if (key.includes('power_hp')) return `${val} HP`
    if (key.includes('weight_kg')) return `${val} kg`
    if (key.includes('weight_lbs')) return `${val} lbs`
    if (key.includes('tank_size_liters')) return `${val} L`
    if (key.includes('tank_size_gallons')) return `${val} gal`
    if (key.includes('outlet_size_inch')) return `${val}"`
  }
  return val
}
</script>

<style>
.v-application {
  font-family: 'Inter', sans-serif !important;
}

.border-left {
  border-left: 1px solid rgba(255, 255, 255, 0.05) !important;
}
</style>
