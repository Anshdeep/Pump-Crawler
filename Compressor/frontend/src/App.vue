<template>
  <v-app style="background: transparent !important;">
    <!-- --- App Header Bar --- -->
    <v-app-bar app flat class="glass-panel px-6 fixed-header" height="70" border="bottom">
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
        
        <!-- Standard Vue tab conditional div views - bypasses Vuetify window layout boundary limitations -->
        <div>
          <!-- ── TAB 1: SPECS CATALOG ── -->
          <div v-show="tab === 'catalog'">
            <v-row>
              <!-- Left Search & Filter Sidebar -->
              <v-col cols="12" md="3" class="sticky-sidebar">
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

              <!-- Central Models Results Grid & Table -->
              <v-col cols="12" md="9">
                <!-- Toggle View and Counter Header -->
                <div v-if="models.length > 0" class="d-flex justify-space-between align-center mb-4">
                  <div class="outfit-font text-subtitle-1 text-medium-emphasis">
                    Showing <span class="text-white font-weight-bold">{{ models.length }}</span> models
                  </div>
                  <v-btn-toggle
                    v-model="viewMode"
                    mandatory
                    color="secondary"
                    variant="outlined"
                    density="comfortable"
                    selected-class="glass-toggle-selected"
                    class="glass-toggle"
                  >
                    <v-btn value="grid" icon="mdi-view-grid"></v-btn>
                    <v-btn value="table" icon="mdi-table"></v-btn>
                  </v-btn-toggle>
                </div>

                <v-row v-if="models.length > 0 && viewMode === 'grid'">
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

                <!-- Tabular View -->
                <v-table v-else-if="models.length > 0 && viewMode === 'table'" class="glass-table-card elevation-2 mb-4" rounded="lg">
                  <thead>
                    <tr>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Model Name</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Series</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Manufacturer</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Type</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4" style="width: 120px;">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="model in models"
                      :key="model.id"
                      class="glass-table-row"
                      @click="viewDetails(model.id)"
                    >
                      <td class="font-weight-medium text-white py-3">{{ model.model_name }}</td>
                      <td class="text-medium-emphasis py-3">{{ model.series || '—' }}</td>
                      <td class="py-3">
                        <v-chip size="x-small" color="primary" variant="flat" class="font-weight-bold">
                          {{ model.manufacturer }}
                        </v-chip>
                      </td>
                      <td class="text-caption text-secondary font-weight-bold text-uppercase py-3">
                        {{ model.compressor_type }}
                      </td>
                      <td class="text-center py-3">
                        <v-btn
                          icon="mdi-eye"
                          size="small"
                          variant="text"
                          color="secondary"
                          @click.stop="viewDetails(model.id)"
                        ></v-btn>
                      </td>
                    </tr>
                  </tbody>
                </v-table>

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
          </div>
 
          <!-- ── TAB 2: CRAWLER CONTROL CENTER ── -->
          <div v-show="tab === 'crawler'">
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

                <!-- Crawl Run History Log Card -->
                <v-card class="glass-card pa-6 mt-6" rounded="lg">
                  <h3 class="outfit-font text-h5 font-weight-bold white--text mb-4">
                    <v-icon icon="mdi-history" color="primary" class="mr-2"></v-icon>Crawl Run History Log
                  </h3>

                  <v-table v-if="crawlHistory.length > 0" class="glass-table-card elevation-2" rounded="lg">
                    <thead>
                      <tr>
                        <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Started At</th>
                        <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Category</th>
                        <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Duration</th>
                        <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Status</th>
                        <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Discovered Manufacturers</th>
                        <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Discovered Models</th>
                        <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Specs Enriched</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="run in crawlHistory" :key="run.id" class="glass-table-row">
                        <td class="text-white py-3 font-weight-medium">{{ formatDateTime(run.started_at) }}</td>
                        <td class="text-medium-emphasis py-3">{{ run.compressor_type || 'All Categories' }}</td>
                        <td class="text-medium-emphasis py-3">{{ formatDuration(run.started_at, run.completed_at) }}</td>
                        <td class="py-3">
                          <v-chip
                            size="x-small"
                            :color="run.status === 'completed' ? 'success' : (run.status === 'active' ? 'warning' : 'error')"
                            variant="flat"
                            class="font-weight-bold text-uppercase"
                          >
                            {{ run.status }}
                          </v-chip>
                        </td>
                        <td class="text-center text-white py-3 font-weight-bold">+{{ run.new_manufacturers_count }}</td>
                        <td class="text-center text-white py-3 font-weight-bold">+{{ run.new_models_count }}</td>
                        <td class="text-center glow-text-secondary py-3 font-weight-bold">{{ run.total_specs_enriched }}</td>
                      </tr>
                    </tbody>
                  </v-table>

                  <div v-else class="text-center py-10 text-medium-emphasis">
                    <v-icon icon="mdi-history" size="48" class="mb-2"></v-icon>
                    <p>No historical crawl records found. Trigger a crawl to start logging runs.</p>
                  </div>
                </v-card>
              </v-col>
            </v-row>
          </div>
        </div>

      </v-container>
    </v-main>

    <!-- ── DYNAMIC DIALOG: MODEL TECHNICAL SPEC SHEETS (CENTRAL LOCATION) ── -->
    <v-dialog
      v-model="drawer"
      max-width="700"
      scrollable
      transition="dialog-bottom-transition"
    >
      <v-card class="glass-card border pa-1" rounded="xl" style="overflow: hidden;">
        <v-progress-linear
          v-if="store.modelDetailsLoading"
          indeterminate
          color="secondary"
        ></v-progress-linear>

        <!-- Dialog Header -->
        <v-card-item class="pb-2">
          <div class="d-flex justify-space-between align-center">
            <span class="text-caption text-secondary font-weight-bold text-uppercase outfit-font">
              Model Specs Details
            </span>
            <v-btn icon="mdi-close" variant="text" color="medium-emphasis" density="comfortable" @click="drawer = false"></v-btn>
          </div>
        </v-card-item>

        <v-card-text v-if="selectedModel" class="px-6 py-4 overflow-y-auto" style="max-height: 60vh;">
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
            <div class="d-flex justify-space-between align-center flex-wrap gap-2">
              <span class="text-body-2 text-medium-emphasis">
                HQ: {{ selectedModel.manufacturer.country || 'Global HQ' }}
              </span>
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
            </div>
          </v-card>

          <v-divider class="mb-6 opacity-10"></v-divider>

          <!-- Technical Attributes Specifications Sheet -->
          <div class="mb-4">
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
                <v-card class="pa-3 bg-rgba(255,255,255,0.01)" border rounded="md" height="100%">
                  <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold mb-1">
                    {{ formatKey(key) }}
                  </div>
                  <div class="text-body-1 text-white font-weight-medium">
                    {{ formatVal(key, val) }}
                  </div>
                </v-card>
              </v-col>
            </v-row>

            <!-- No Specs Warning -->
            <div v-else class="text-center py-12 text-medium-emphasis">
              <v-icon icon="mdi-file-cancel-outline" size="48" class="mb-2"></v-icon>
              <p>No specifications extracted for this model yet.</p>
            </div>
          </div>
        </v-card-text>

        <!-- Dialog Footer Actions -->
        <v-card-actions v-if="selectedModel" class="px-6 py-4 border-top bg-rgba(255,255,255,0.01)">
          <v-btn
            v-if="selectedModel.product_url"
            :href="selectedModel.product_url"
            target="_blank"
            color="secondary"
            variant="flat"
            prepend-icon="mdi-card-text-outline"
            class="outfit-font text-capitalize flex-grow-1"
          >
            View Technical Catalog Page
          </v-btn>
          <v-btn
            variant="tonal"
            class="outfit-font text-capitalize px-6"
            @click="drawer = false"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Dynamic Success/Error Toast Feedback Snackbars -->
    <v-snackbar v-model="toast.active" :color="toast.color" timeout="3000" rounded="lg">
      {{ toast.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useCompressorStore } from './store/compressors'

const store = useCompressorStore()

// State
const tab = ref('catalog')
const drawer = ref(false)
const initLoading = ref(false)
const viewMode = ref('grid')

// Prevent background scroll when sidebar drawer is open
watch(drawer, (newVal) => {
  if (newVal) {
    document.documentElement.style.overflow = 'hidden'
  } else {
    document.documentElement.style.overflow = ''
  }
})

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
  await store.fetchCrawlHistory()
  
  // Periodically poll crawl status if a task is active in background
  setInterval(() => {
    if (store.crawlStatus.active) {
      store.fetchCrawlStatus()
      // Refresh tree and lists upon completion
      if (store.crawlStatus.percent === 100) {
        store.fetchCompressors()
        store.fetchModels(filters.value)
        store.fetchCrawlHistory()
      }
    }
  }, 3000)
})

// Computeds
const models = computed(() => store.models || [])
const crawlHistory = computed(() => store.crawlHistory || [])

// Formatters
const formatDateTime = (isoString) => {
  if (!isoString) return '—'
  const date = new Date(isoString)
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatDuration = (started, completed) => {
  if (!started || !completed) return '—'
  const diffMs = new Date(completed) - new Date(started)
  const diffSecs = Math.floor(diffMs / 1000)
  if (diffSecs < 60) return `${diffSecs}s`
  const mins = Math.floor(diffSecs / 60)
  const secs = diffSecs % 60
  return `${mins}m ${secs}s`
}

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

/* Glassmorphism View Toggle Styles */
.glass-toggle {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 8px !important;
  overflow: hidden;
}

.glass-toggle-selected {
  background: rgba(6, 182, 212, 0.15) !important;
  color: #06b6d4 !important;
}

/* Glassmorphism Custom Table Styles */
.glass-table-card {
  background: rgba(255, 255, 255, 0.02) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.05) !important;
  color: white !important;
}

.glass-table-card th {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
  background: rgba(255, 255, 255, 0.01) !important;
}

.glass-table-row {
  cursor: pointer;
  transition: all 0.2s ease;
}

.glass-table-row:hover {
  background: rgba(255, 255, 255, 0.05) !important;
}

.glass-table-row td {
  border-bottom: 1px solid rgba(255, 255, 255, 0.03) !important;
}

/* Fixed App Header Styles */
.fixed-header {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 1000 !important;
  width: 100% !important;
}

.v-main {
  margin-top: 70px !important; /* Offset for the 70px high fixed app bar */
}

/* Sticky Sidebar Styles */
.sticky-sidebar {
  position: sticky !important;
  top: 90px !important;
  z-index: 5;
  align-self: flex-start !important; /* Crucial: stops flexbox stretching and enables column sticky bounds */
  max-height: calc(100vh - 110px) !important;
  overflow-y: auto !important;
}

/* Scroll Safe-guards for Sticky Elements */
html, body {
  overflow-y: visible !important;
}

.v-application {
  overflow: visible !important;
}

.v-application__wrap {
  overflow: visible !important;
  min-height: 100vh !important;
}

/* Force Vuetify Window to be Overflow-Visible to permit sticky calculations */
.v-window,
.v-window-item,
.v-window__container {
  overflow: visible !important;
}
</style>
