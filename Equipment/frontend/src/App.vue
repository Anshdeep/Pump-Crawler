<template>
  <v-app style="background: #090A0F !important;">
    <!-- ── PREMIUM GLASSMORPHIC SIDEBAR ── -->
    <v-navigation-drawer
      app
      permanent
      :width="sidebarCollapsed ? 75 : 280"
      class="glass-sidebar py-4"
      border="right"
    >
      <div class="px-3 mb-8 d-flex align-center gap-3 overflow-hidden" :class="sidebarCollapsed ? 'justify-center' : 'px-6'">
        <v-avatar color="primary" size="42" elevation="6" class="glowing-avatar flex-shrink-0">
          <v-icon icon="mdi-robot-industrial" color="white" size="24"></v-icon>
        </v-avatar>
        <div v-if="!sidebarCollapsed" class="text-truncate">
          <h3 class="outfit-font font-weight-bold text-h6 text-white leading-tight">
            Equipment<span class="glow-text-primary"> Specs</span>
          </h3>
          <span class="text-caption text-secondary font-weight-black text-uppercase tracking-wider">Enterprise RAG</span>
        </div>
      </div>

      <v-list nav class="px-2" :class="sidebarCollapsed ? 'px-1' : 'px-4'">
        <v-list-item
          v-for="item in navItems"
          :key="item.value"
          :value="item.value"
          :prepend-icon="item.icon"
          :title="sidebarCollapsed ? '' : item.title"
          class="outfit-font text-subtitle-1 mb-2 py-3 rounded-lg text-capitalize sidebar-nav-item"
          :active="tab === item.value"
          @click="tab = item.value"
          v-tooltip:right="sidebarCollapsed ? item.title : ''"
        >
          <template v-slot:append v-if="!sidebarCollapsed && item.value === 'catalog'">
            <v-chip size="x-small" color="secondary" variant="flat">{{ models.length }}</v-chip>
          </template>
          <template v-slot:append v-else-if="!sidebarCollapsed && item.value === 'manufacturers'">
            <v-chip size="x-small" color="primary" variant="flat">{{ manufacturersList.length }}</v-chip>
          </template>
        </v-list-item>
      </v-list>
      
      <template v-slot:append>
        <div class="pa-4 text-center">
          <v-divider class="mb-4 rgba(255,255,255,0.05)"></v-divider>
          <span class="text-caption text-disabled outfit-font">
            {{ sidebarCollapsed ? 'v3.2' : 'Specs Control v3.2.0' }}
          </span>
        </div>
      </template>
    </v-navigation-drawer>

    <!-- ── App Header Bar ── -->
    <v-app-bar app flat class="glass-header px-6 border-bottom" height="70">
      <v-app-bar-nav-icon color="white" class="mr-2" @click="sidebarCollapsed = !sidebarCollapsed"></v-app-bar-nav-icon>
      
      <div class="outfit-font font-weight-bold text-h5 text-white">
        <span class="text-secondary font-weight-light">Control Room</span> / <span class="text-white">{{ currentTabTitle }}</span>
      </div>
      <v-spacer></v-spacer>

      <v-chip color="secondary" variant="tonal" class="font-weight-black mr-2 px-3 py-1">
        <v-icon start icon="mdi-database-search" class="mr-1"></v-icon> {{ models.length }} Models
      </v-chip>
      <v-chip color="primary" variant="tonal" class="font-weight-black px-3 py-1">
        <v-icon start icon="mdi-factory" class="mr-1"></v-icon> {{ manufacturersList.length }} Manufacturers
      </v-chip>
    </v-app-bar>

    <!-- ── Main Content View ── -->
    <v-main class="dashboard-main" :style="`margin-left: 0px !important;`">
      <v-container fluid class="px-6 py-6">
        
        <!-- ── TAB 1: OVERVIEW DASHBOARD ── -->
        <div v-show="tab === 'overview'">
          <v-row class="mb-6">
            <!-- Modern Stats Grid -->
            <v-col cols="12" sm="6" md="4" lg="2" v-for="stat in overviewStats" :key="stat.title">
              <v-card class="glass-card pa-4 d-flex align-center gap-3 relative overflow-hidden" rounded="xl">
                <v-avatar :color="stat.colorBg" size="48" class="mr-1 flex-shrink-0">
                  <v-icon :icon="stat.icon" :color="stat.color" size="24"></v-icon>
                </v-avatar>
                <div>
                  <div class="text-h5 font-weight-bold text-white outfit-font leading-tight">{{ stat.value }}</div>
                  <div class="text-caption text-medium-emphasis font-weight-bold uppercase">{{ stat.title }}</div>
                </div>
                <div class="stat-gradient-glow" :style="`background: radial-gradient(circle, ${stat.color} 0%, transparent 80%);`"></div>
              </v-card>
            </v-col>
          </v-row>

          <v-row>
            <!-- Premium Welcome Card -->
            <v-col cols="12" md="7">
              <v-card class="glass-card pa-8 h-100 d-flex flex-column justify-center relative overflow-hidden" rounded="xl">
                <div class="z-index-1">
                  <h3 class="outfit-font text-h4 font-weight-black text-white mb-2">
                    Welcome to the <span class="glow-text-primary">Control Room</span>
                  </h3>
                  <p class="text-subtitle-1 text-medium-emphasis mb-6 outfit-font font-weight-light">
                    Real-time web crawling, dynamic pgvector semantic de-duplication, and Gemini-powered technical specifications extraction engine.
                  </p>
                  <div class="d-flex gap-3">
                    <v-chip color="secondary" variant="tonal">Playwright Browser Bypass Active</v-chip>
                    <v-chip color="primary" variant="tonal">Gemini Structured Outputs Ready</v-chip>
                  </div>
                </div>
                <div class="stat-gradient-glow" style="background: radial-gradient(circle, rgba(139, 92, 246, 0.15) 0%, transparent 80%); top: -30%; right: -30%; width: 350px; height: 350px;"></div>
              </v-card>
            </v-col>

            <!-- Actions Center -->
            <v-col cols="12" md="5">
              <v-card class="glass-card pa-6 h-100 d-flex flex-column" rounded="xl">
                <h3 class="outfit-font text-h5 font-weight-black text-white mb-4">
                  <v-icon icon="mdi-lightning-bolt" color="primary" class="mr-2"></v-icon>Crawler Actions Center
                </h3>
                <p class="text-body-2 text-medium-emphasis mb-6">
                  Access crawler triggers, target directories approval lists, and fine-tune rate controls from settings.
                </p>

                <div class="d-flex flex-column gap-3 flex-grow-1 justify-center">
                  <v-btn
                    color="primary"
                    variant="tonal"
                    height="54"
                    prepend-icon="mdi-robot-mower"
                    class="outfit-font text-capitalize text-left font-weight-bold justify-start"
                    block
                    @click="tab = 'crawler'"
                  >
                    Configure & Trigger Crawl Task
                  </v-btn>

                  <v-btn
                    color="secondary"
                    variant="tonal"
                    height="54"
                    prepend-icon="mdi-factory"
                    class="outfit-font text-capitalize text-left font-weight-bold justify-start"
                    block
                    @click="tab = 'manufacturers'"
                  >
                    Manage Manufacturers Directory
                  </v-btn>

                  <v-btn
                    color="white"
                    variant="tonal"
                    height="54"
                    prepend-icon="mdi-file-tree"
                    class="outfit-font text-capitalize text-left font-weight-bold justify-start"
                    block
                    @click="tab = 'taxonomy'"
                  >
                    Edit Equipment Taxonomy Tree
                  </v-btn>
                </div>
              </v-card>
            </v-col>
          </v-row>
        </div>

        <!-- ── TAB 2: SPECS CATALOG ── -->
        <div v-show="tab === 'catalog'">
          <v-row>
            <!-- Left Sidebar Filters (Renamed to Catalog) -->
            <v-col cols="12" md="3" class="sticky-sidebar">
              <v-card class="glass-card pa-5 mb-4" rounded="xl">
                <h3 class="outfit-font text-h6 font-weight-bold mb-4 glow-text-secondary">
                  <v-icon icon="mdi-filter-variant" class="mr-2" size="20"></v-icon>Catalog
                </h3>

                <!-- Master Category Filter -->
                <v-autocomplete
                  v-model="filters.equipment_master_id"
                  :items="equipmentMastersList"
                  item-title="name"
                  item-value="id"
                  label="Master Equipment"
                  prepend-inner-icon="mdi-robot-industrial"
                  variant="outlined"
                  density="comfortable"
                  color="secondary"
                  clearable
                  class="mb-3"
                  @update:model-value="onMasterFilterChange"
                ></v-autocomplete>

                <!-- Type Dropdown -->
                <v-autocomplete
                  v-model="filters.equipment_type_id"
                  :items="filteredTypes"
                  item-title="name"
                  item-value="id"
                  label="Equipment Type"
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
                  :items="manufacturersListForFilter"
                  item-title="name"
                  item-value="id"
                  label="Manufacturer"
                  prepend-inner-icon="mdi-domain"
                  variant="outlined"
                  density="comfortable"
                  color="secondary"
                  clearable
                  class="mb-3"
                  @update:model-value="fetchModels"
                ></v-autocomplete>

                <!-- Search field (Moved below primary filters dropdowns) -->
                <v-text-field
                  v-model="filters.q"
                  label="Search Models / Series"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  density="comfortable"
                  color="secondary"
                  clearable
                  class="mb-3"
                  @update:model-value="debouncedFetchModels"
                ></v-text-field>

                <!-- Approval Toggles in Filter -->
                <v-select
                  v-model="filters.is_approved"
                  :items="[
                    { title: 'Show All Statuses', value: null },
                    { title: 'Only Approved', value: true },
                    { title: 'Only Pending', value: false }
                  ]"
                  item-title="title"
                  item-value="value"
                  label="Approval Status"
                  variant="outlined"
                  density="comfortable"
                  color="secondary"
                  class="mb-3"
                  @update:model-value="fetchModels"
                ></v-select>

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

            <!-- Central Results View -->
            <v-col cols="12" md="9">
              <!-- Sorting Toolbar & Actions -->
              <v-card class="glass-card pa-4 mb-4 d-flex justify-space-between align-center flex-wrap gap-3" rounded="xl">
                <!-- Sorting Inputs -->
                <div class="d-flex align-center flex-wrap gap-2 flex-grow-1 max-width-sort">
                  <span class="text-caption text-medium-emphasis font-weight-bold outfit-font mr-2">SORT BY:</span>
                  <v-select
                    v-model="sortBy"
                    :items="[
                      { title: 'Model Name', value: 'model_name' },
                      { title: 'Series', value: 'series' },
                      { title: 'Manufacturer', value: 'manufacturer' },
                      { title: 'Date Created', value: 'created_at' }
                    ]"
                    item-title="title"
                    item-value="value"
                    variant="outlined"
                    density="compact"
                    hide-details
                    color="secondary"
                    style="max-width: 170px;"
                  ></v-select>

                  <v-btn
                    variant="tonal"
                    color="secondary"
                    icon
                    size="small"
                    title="Toggle Sort Direction"
                    @click="sortDesc = !sortDesc"
                  >
                    <v-icon :icon="sortDesc ? 'mdi-sort-descending' : 'mdi-sort-ascending'"></v-icon>
                  </v-btn>
                </div>

                <!-- Right Side toggles -->
                <div class="d-flex align-center gap-3">
                  <div class="outfit-font text-subtitle-2 text-medium-emphasis">
                    Total: <span class="text-white font-weight-bold">{{ sortedModels.length }}</span> models
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
              </v-card>

              <!-- ── BULK ACTION BAR ── -->
              <v-expand-transition>
                <div v-if="selectedModelIds.length > 0" class="mb-4">
                  <v-card class="pa-4 bg-primary-glowing border border-primary d-flex justify-space-between align-center flex-wrap gap-4" rounded="xl">
                    <div class="d-flex align-center gap-2">
                      <v-icon icon="mdi-checkbox-multiple-marked" color="white" size="22"></v-icon>
                      <span class="outfit-font font-weight-bold text-white text-subtitle-1">
                        {{ selectedModelIds.length }} models selected
                      </span>
                    </div>

                    <div class="d-flex gap-2">
                      <v-btn
                        color="success"
                        variant="flat"
                        prepend-icon="mdi-check-decagram"
                        class="text-capitalize font-weight-bold px-4"
                        @click="bulkApprove(true)"
                      >
                        Approve Selected
                      </v-btn>
                      <v-btn
                        color="warning"
                        variant="tonal"
                        prepend-icon="mdi-clock-outline"
                        class="text-capitalize font-weight-bold px-4 border-glass"
                        @click="bulkApprove(false)"
                      >
                        Set to Pending
                      </v-btn>
                      <v-btn
                        variant="text"
                        color="white"
                        class="text-capitalize font-weight-medium"
                        @click="selectedModelIds = []"
                      >
                        Clear
                      </v-btn>
                    </div>
                  </v-card>
                </div>
              </v-expand-transition>

              <!-- Grid layout -->
              <div v-if="sortedModels.length > 0">
                <!-- Select All Trigger -->
                <div class="d-flex align-center px-4 mb-2">
                  <v-checkbox
                    :model-value="isAllSelected"
                    color="secondary"
                    density="compact"
                    hide-details
                    label="Select All Models on Page"
                    class="d-inline-flex select-all-checkbox"
                    @click.prevent="toggleSelectAll"
                  ></v-checkbox>
                </div>

                <v-row v-if="viewMode === 'grid'">
                  <v-col
                    v-for="model in sortedModels"
                    :key="model.id"
                    cols="12"
                    sm="6"
                    md="4"
                  >
                    <v-card 
                      class="glass-card pa-4 d-flex flex-column h-100 position-relative cursor-pointer" 
                      rounded="xl" 
                      :class="selectedModelIds.includes(model.id) ? 'selected-card-border' : ''"
                      @click="viewDetails(model.id)"
                    >
                      <!-- Top Select Checkbox Overlay -->
                      <div class="position-checkbox-overlay" @click.stop>
                        <v-checkbox
                          v-model="selectedModelIds"
                          :value="model.id"
                          color="secondary"
                          density="compact"
                          hide-details
                        ></v-checkbox>
                      </div>

                      <div class="d-flex justify-space-between align-center mb-3 pr-8">
                        <span class="text-caption text-secondary font-weight-bold text-uppercase">
                          {{ model.equipment_type }}
                        </span>
                        <v-chip size="x-small" color="primary" variant="flat">
                          {{ model.manufacturer }}
                        </v-chip>
                      </div>

                      <h4 class="outfit-font text-h6 font-weight-bold white--text mb-1">
                        {{ model.model_name }}
                      </h4>
                      <p class="text-subtitle-2 text-medium-emphasis mb-2">
                        Series: {{ model.series || 'Standard Line' }}
                      </p>
                      
                      <!-- Show Model Created Date -->
                      <span class="text-caption text-disabled mb-4 d-flex align-center">
                        <v-icon icon="mdi-calendar-plus" start size="12" class="mr-1"></v-icon>
                        Added: {{ formatDateTime(model.created_at) }}
                      </span>

                      <v-spacer></v-spacer>

                      <div class="d-flex justify-space-between align-center mt-3 pt-2 border-top border-glass">
                        <v-chip
                          size="x-small"
                          :color="model.is_approved ? 'success' : 'warning'"
                          variant="tonal"
                          class="font-weight-bold"
                          @click.stop="toggleModelApprovalInline(model)"
                        >
                          <v-icon start size="10" :icon="model.is_approved ? 'mdi-check-decagram' : 'mdi-clock-outline'"></v-icon>
                          {{ model.is_approved ? 'Approved' : 'Pending' }}
                        </v-chip>

                        <v-chip
                          size="x-small"
                          :color="model.is_harvested ? 'info' : 'rgba(255,255,255,0.15)'"
                          variant="flat"
                          class="font-weight-black"
                        >
                          {{ model.is_harvested ? 'Harvested' : 'Empty' }}
                        </v-chip>
                      </div>
                    </v-card>
                  </v-col>
                </v-row>

                <!-- Table layout -->
                <v-table v-else class="glass-table-card elevation-2 mb-4" rounded="lg">
                  <thead>
                    <tr>
                      <th style="width: 50px;"></th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Model Name</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Series</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Manufacturer</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Type</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Date Added</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4" style="width: 130px;">Specs Harvest</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4" style="width: 140px;">Catalog Approval</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="model in sortedModels"
                      :key="model.id"
                      class="glass-table-row"
                      :class="selectedModelIds.includes(model.id) ? 'selected-row-bg' : ''"
                      @click="viewDetails(model.id)"
                    >
                      <td @click.stop class="py-3">
                        <v-checkbox
                          v-model="selectedModelIds"
                          :value="model.id"
                          color="secondary"
                          density="compact"
                          hide-details
                          class="d-inline-flex"
                        ></v-checkbox>
                      </td>
                      <td class="font-weight-medium text-white py-3">{{ model.model_name }}</td>
                      <td class="text-medium-emphasis py-3">{{ model.series || '—' }}</td>
                      <td class="py-3">
                        <v-chip size="x-small" color="primary" variant="flat" class="font-weight-bold">
                          {{ model.manufacturer }}
                        </v-chip>
                      </td>
                      <td class="text-caption text-secondary font-weight-bold text-uppercase py-3">
                        {{ model.equipment_type }}
                      </td>
                      <td class="text-center text-caption text-medium-emphasis py-3">
                        {{ formatDateTime(model.created_at) }}
                      </td>
                      <td class="text-center py-3">
                        <v-chip
                          size="x-small"
                          :color="model.is_harvested ? 'info' : 'rgba(255,255,255,0.1)'"
                          variant="flat"
                          class="font-weight-bold"
                        >
                          {{ model.is_harvested ? 'Harvested' : 'Empty' }}
                        </v-chip>
                      </td>
                      <td class="text-center py-3" @click.stop>
                        <v-switch
                          v-model="model.is_approved"
                          color="success"
                          density="compact"
                          inset
                          hide-details
                          class="d-inline-flex"
                          @change="toggleModelApproval(model.id, model.is_approved)"
                        ></v-switch>
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </div>

              <!-- Empty state -->
              <v-card v-else class="glass-card pa-12 text-center" rounded="xl">
                <v-avatar color="rgba(6, 182, 212, 0.1)" size="72" class="mb-4">
                  <v-icon icon="mdi-database-alert" color="secondary" size="36"></v-icon>
                </v-avatar>
                <h3 class="outfit-font text-h5 font-weight-bold mb-2">No Models Found</h3>
                <p class="text-body-1 text-medium-emphasis mb-6">
                  Try adjusting your filters, or go to the Control Center to start selective spec crawler harvests.
                </p>
              </v-card>
            </v-col>
          </v-row>
        </div>

        <!-- ── TAB 3: TAXONOMY EXPLORER & CRUD MANAGER ── -->
        <div v-show="tab === 'taxonomy'">
          <v-row class="justify-center">
            <v-col cols="12" md="10">
              <v-card class="glass-card pa-6" rounded="xl">
                <div class="d-flex justify-space-between align-center mb-6">
                  <div>
                    <h3 class="outfit-font text-h5 font-weight-black text-white">
                      <v-icon icon="mdi-file-tree" color="primary" class="mr-2"></v-icon>Taxonomy Tree Catalog
                    </h3>
                    <p class="text-caption text-medium-emphasis">
                      Create, update, and manage Equipment Masters, Equipment Types, and Subtypes in a multi-level hierarchy.
                    </p>
                  </div>
                  <v-btn
                    color="success"
                    prepend-icon="mdi-plus"
                    class="outfit-font text-capitalize font-weight-bold"
                    @click.stop="openAddMaster"
                  >
                    Add Master Category
                  </v-btn>
                </div>

                <!-- Nested Taxonomy Accordion -->
                <div v-if="taxonomyTree.length > 0" class="taxonomy-explorer">
                  <v-expansion-panels variant="accordion" class="gap-3">
                    <v-expansion-panel
                      v-for="master in taxonomyTree"
                      :key="master.id"
                      class="glass-panel-item rounded-xl border mb-3 overflow-hidden"
                    >
                      <v-expansion-panel-title class="font-weight-black outfit-font text-subtitle-1 text-white py-4 px-6">
                        <v-icon icon="mdi-robot-industrial" color="secondary" class="mr-3"></v-icon>
                        <span class="text-white">{{ master.name }}</span>
                        
                        <v-spacer></v-spacer>
                        
                        <span class="text-caption text-disabled mr-4 d-none d-sm-inline-flex">
                          Created: {{ formatDateTime(master.created_at) }}
                        </span>
                        
                        <div class="d-flex align-center gap-1">
                          <v-btn icon="mdi-plus" size="x-small" variant="tonal" color="success" class="mr-1" title="Add Type under Master" @click.stop="openAddType(master.id)"></v-btn>
                          <v-btn icon="mdi-pencil" size="x-small" variant="tonal" color="info" class="mr-1" title="Edit Master" @click.stop="openEditMaster(master)"></v-btn>
                          <v-btn icon="mdi-delete" size="x-small" variant="tonal" color="error" title="Delete Master" @click.stop="deleteMaster(master.id)"></v-btn>
                        </div>
                      </v-expansion-panel-title>

                      <v-expansion-panel-text class="bg-glass-sub-panel px-4 py-4 border-top">
                        <p class="text-body-2 text-medium-emphasis mb-5 italic" v-if="master.description">
                          "{{ master.description }}"
                        </p>

                        <!-- Types Listing under Master -->
                        <div v-if="master.types && master.types.length > 0">
                          <div
                            v-for="etype in master.types"
                            :key="etype.id"
                            class="pa-4 rounded-xl bg-rgba-white-02 border border-glass mb-4"
                          >
                            <div class="d-flex align-center justify-space-between flex-wrap gap-4 mb-3">
                              <div>
                                <h4 class="font-weight-bold text-white d-flex align-center text-subtitle-1">
                                  <v-icon icon="mdi-shape-outline" color="primary" class="mr-2" size="18"></v-icon>
                                  {{ etype.name }}
                                </h4>
                                <span class="text-caption text-medium-emphasis" v-if="etype.description">
                                  {{ etype.description }}
                                </span>
                              </div>

                              <div class="d-flex align-center gap-1">
                                <v-chip size="x-small" variant="tonal" color="rgba(255,255,255,0.2)" class="mr-2 d-none d-sm-inline-flex">
                                  Updated: {{ formatDateTime(etype.updated_at) }}
                                </v-chip>
                                <v-btn
                                  variant="tonal"
                                  size="x-small"
                                  color="success"
                                  prepend-icon="mdi-plus"
                                  class="text-capitalize font-weight-bold mr-1"
                                  @click.stop="openAddSubtype(etype.id)"
                                >
                                  Add Subtype
                                </v-btn>
                                <v-btn icon="mdi-pencil" size="x-small" variant="tonal" color="info" class="mr-1" title="Edit Type" @click.stop="openEditType(etype)"></v-btn>
                                <v-btn icon="mdi-delete" size="x-small" variant="tonal" color="error" title="Delete Type" @click.stop="deleteType(etype.id)"></v-btn>
                              </div>
                            </div>

                            <!-- Subtypes rendering list -->
                            <div class="pl-6 border-left-indicator py-2 mt-2">
                              <div class="text-caption text-secondary font-weight-black mb-2 d-flex align-center">
                                <v-icon icon="mdi-tag-multiple-outline" start size="14" class="mr-1"></v-icon>
                                Equipment Subtypes ({{ etype.subtypes ? etype.subtypes.length : 0 }})
                              </div>
                              
                              <!-- FIX: Removed closable / close-icon triggers to avoid hiding chips visually on edit -->
                              <div v-if="etype.subtypes && etype.subtypes.length > 0" class="d-flex flex-wrap gap-2">
                                <v-chip
                                  v-for="sub in etype.subtypes"
                                  :key="sub.id"
                                  size="small"
                                  color="secondary"
                                  variant="tonal"
                                  class="pr-2 font-weight-medium subtype-chip"
                                >
                                  {{ sub.name }}
                                  <template v-slot:append>
                                    <v-btn
                                      icon="mdi-pencil"
                                      variant="text"
                                      density="compact"
                                      size="x-small"
                                      color="info"
                                      class="ml-2 mr-1 icon-btn-hover"
                                      title="Edit Subtype"
                                      @click.stop="openEditSubtype(sub)"
                                    ></v-btn>
                                    <v-btn
                                      icon="mdi-close"
                                      variant="text"
                                      density="compact"
                                      size="x-small"
                                      color="error"
                                      class="icon-btn-hover"
                                      title="Delete Subtype"
                                      @click.stop="deleteSubtype(sub.id)"
                                    ></v-btn>
                                  </template>
                                </v-chip>
                              </div>
                              <div v-else class="text-caption text-disabled italic">
                                No subtypes added under this equipment type. Click "Add Subtype" to create one.
                              </div>
                            </div>
                          </div>
                        </div>
                        <div v-else class="text-center py-4 text-medium-emphasis italic">
                          No equipment types added. Click "+" above to add your first type.
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                </div>

                <div v-else class="text-center py-12 text-medium-emphasis">
                  <v-icon icon="mdi-file-tree-outline" size="48" class="mb-2"></v-icon>
                  <p>Taxonomy directory empty. Initialize database to seed defaults or create them manually above.</p>
                </div>
              </v-card>
            </v-col>
          </v-row>
        </div>

        <!-- ── TAB 4: MANUFACTURERS DIRECTORY ── -->
        <div v-show="tab === 'manufacturers'">
          <v-row class="justify-center">
            <v-col cols="12" md="11">
              <v-card class="glass-card pa-6" rounded="xl">
                <div class="d-flex justify-space-between align-center flex-wrap gap-4 mb-6">
                  <div>
                    <h3 class="outfit-font text-h5 font-weight-black text-white">
                      <v-icon icon="mdi-factory" color="primary" class="mr-2"></v-icon>Manufacturer Directory Manager
                    </h3>
                    <p class="text-caption text-medium-emphasis">
                      Manage manufacturer profiles, HQ origins, web URLs, and toggles for background crawler approval.
                    </p>
                  </div>
                  <div class="d-flex gap-2">
                    <v-btn
                      color="success"
                      prepend-icon="mdi-plus"
                      class="outfit-font text-capitalize font-weight-bold"
                      @click.stop="openAddManufacturer"
                    >
                      Add Manufacturer
                    </v-btn>
                    <v-btn
                      color="secondary"
                      variant="tonal"
                      prepend-icon="mdi-sync"
                      class="outfit-font text-capitalize font-weight-bold"
                      @click="fetchManufacturers"
                    >
                      Refresh Directory
                    </v-btn>
                  </div>
                </div>

                <!-- Manufacturers Directory Table -->
                <v-table v-if="manufacturersList.length > 0" class="glass-table-card elevation-2" rounded="lg">
                  <thead>
                    <tr>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Manufacturer</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">HQ Country</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Official Website</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Models</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Harvest Status</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Date Added</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4" style="width: 110px;">Approval</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4" style="width: 120px;">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="mfr in manufacturersList" :key="mfr.id" class="glass-table-row">
                      <td class="text-white py-4 font-weight-bold text-subtitle-1">{{ mfr.name }}</td>
                      <td class="text-medium-emphasis py-4">{{ mfr.country || 'Global HQ' }}</td>
                      <td class="py-4">
                        <a v-if="mfr.website" :href="'https://' + mfr.website" target="_blank" class="text-secondary font-weight-bold text-decoration-none d-flex align-center">
                          <v-icon icon="mdi-open-in-new" start size="14" class="mr-1"></v-icon>{{ mfr.website }}
                        </a>
                        <span class="text-disabled" v-else>—</span>
                      </td>
                      <td class="text-center py-4">
                        <v-chip v-if="mfr.model_count > 0" size="small" color="primary" variant="flat" class="font-weight-bold">
                          {{ mfr.model_count }} Models
                        </v-chip>
                        <v-chip v-else size="small" variant="outlined" color="rgba(255,255,255,0.2)" class="text-medium-emphasis">
                          0 Models
                        </v-chip>
                      </td>
                      <td class="text-center py-4">
                        <v-chip
                          size="small"
                          :color="mfr.is_harvested ? 'success' : 'rgba(255,255,255,0.1)'"
                          :variant="mfr.is_harvested ? 'flat' : 'outlined'"
                          class="font-weight-bold"
                        >
                          {{ mfr.is_harvested ? 'Harvested' : 'Unharvested' }}
                        </v-chip>
                      </td>
                      <td class="text-center text-caption text-medium-emphasis py-4">
                        {{ formatDateTime(mfr.created_at) }}
                      </td>
                      <td class="text-center py-4">
                        <v-switch
                          v-model="mfr.is_approved"
                          color="success"
                          density="compact"
                          inset
                          hide-details
                          class="d-inline-flex"
                          @change="toggleApproval(mfr.id, mfr.is_approved)"
                        ></v-switch>
                      </td>
                      <td class="text-center py-4" @click.stop>
                        <div class="d-inline-flex gap-1">
                          <v-btn icon="mdi-pencil" size="x-small" variant="tonal" color="info" title="Edit Manufacturer" @click.stop="openEditManufacturer(mfr)"></v-btn>
                          <v-btn icon="mdi-delete" size="x-small" variant="tonal" color="error" title="Delete Manufacturer" @click.stop="deleteManufacturer(mfr.id)"></v-btn>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </v-table>

                <div v-else class="text-center py-12 text-medium-emphasis">
                  <v-avatar color="rgba(6, 182, 212, 0.05)" size="72" class="mb-4">
                    <v-icon icon="mdi-domain-off" color="secondary" size="36"></v-icon>
                  </v-avatar>
                  <h4 class="outfit-font text-h6 font-weight-bold">No Discovered Manufacturers</h4>
                  <p class="text-body-2 text-medium-emphasis">
                    Trigger Discovery under Crawler Controls or click "Add Manufacturer" to seed them manually.
                  </p>
                </div>
              </v-card>
            </v-col>
          </v-row>
        </div>

        <!-- ── TAB 5: CRAWLER OPERATOR & SETTINGS ── -->
        <!-- ── TAB 5: CRAWLER OPERATOR ── -->
        <div v-show="tab === 'crawler'">
          <v-row class="justify-center">
            <v-col cols="12" md="10">
              <!-- Database Migrations Trigger -->
              <v-card class="glass-card pa-6 mb-6" rounded="xl">
                <div class="d-flex justify-space-between align-center flex-wrap gap-4">
                  <div>
                    <h3 class="outfit-font text-h5 font-weight-black text-white">
                      <v-icon icon="mdi-database-cog" color="primary" class="mr-2"></v-icon>Schema Setup & Migrations
                    </h3>
                    <p class="text-caption text-medium-emphasis">
                      Recreate table structures dynamically, apply modifications, and load seed values immediately.
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
                    Run Table Seeding / Init
                  </v-btn>
                </div>
              </v-card>

              <!-- Crawler Parameters -->
              <v-card class="glass-card pa-6 mb-6" rounded="xl">
                <h3 class="outfit-font text-h5 font-weight-bold mb-5 glow-text-secondary">
                  <v-icon icon="mdi-robot-mower" class="mr-2"></v-icon>Enterprise Crawler Operations Control
                </h3>
                
                <v-row>
                  <!-- Stage 1 Discovery -->
                  <v-col cols="12" md="6" class="pr-md-6 border-right">
                    <div class="mb-4">
                      <div class="text-h6 font-weight-bold outfit-font text-white d-flex align-center">
                        <v-avatar color="rgba(6, 182, 212, 0.1)" size="30" class="mr-2 text-subtitle-2 font-weight-black text-secondary">1</v-avatar>
                        Step 1: Manufacturer Discovery
                      </div>
                      <p class="text-caption text-medium-emphasis mt-2" style="min-height: 50px;">
                        Find manufacturers for specified equipment types on internet directory searches using Gemini processing.
                      </p>
                    </div>

                    <v-select
                      v-model="crawlParams.equipment_type_id"
                      :items="equipmentTypesDropdown"
                      item-title="name"
                      item-value="id"
                      label="Target Equipment Category"
                      variant="outlined"
                      density="comfortable"
                      color="secondary"
                      class="mb-3"
                    ></v-select>
                    
                    <v-switch
                      v-model="crawlParams.no_cache"
                      label="Bypass Local Web Cache"
                      color="secondary"
                      inset
                      density="compact"
                      class="mb-4"
                    ></v-switch>

                    <v-btn
                      color="primary"
                      block
                      height="45"
                      prepend-icon="mdi-feature-search"
                      class="outfit-font text-capitalize font-weight-bold"
                      :disabled="store.crawlStatus.active"
                      :loading="store.crawlLoading"
                      @click="triggerManufacturerDiscovery"
                    >
                      Run Discovery (Stage 1)
                    </v-btn>
                  </v-col>

                  <!-- Stage 2/3 Harvester -->
                  <v-col cols="12" md="6" class="pl-md-6">
                    <div class="mb-4">
                      <div class="text-h6 font-weight-bold outfit-font text-white d-flex align-center">
                        <v-avatar color="rgba(6, 182, 212, 0.1)" size="30" class="mr-2 text-subtitle-2 font-weight-black text-secondary">2</v-avatar>
                        Step 2: Specs & Model Harvester
                      </div>
                      <p class="text-caption text-medium-emphasis mt-2" style="min-height: 50px;">
                        Scrape model specs files and evaluate vector models matching ONLY for approved manufacturer directories.
                      </p>
                    </div>

                    <div class="mb-3">
                      <v-select
                        v-model="crawlParams.selected_manufacturer_ids"
                        :items="approvedManufacturers"
                        item-title="name"
                        item-value="id"
                        label="Target Specific Manufacturers"
                        variant="outlined"
                        density="comfortable"
                        color="secondary"
                        multiple
                        chips
                        clearable
                        hint="Bypasses all other manufacturers to restrict search quotas. Leave blank for all."
                        persistent-hint
                      ></v-select>
                    </div>

                    <div class="d-flex justify-space-between mb-4 mt-2 flex-wrap gap-2">
                      <v-switch
                        v-model="crawlParams.deep_crawl"
                        label="Deep Crawl (Model Discovery)"
                        color="primary"
                        inset
                        density="compact"
                        hide-details
                      ></v-switch>
                      <v-switch
                        v-model="crawlParams.only_unharvested"
                        label="Only Unharvested"
                        color="secondary"
                        inset
                        density="compact"
                        hide-details
                      ></v-switch>
                      <v-switch
                        v-model="crawlParams.no_cache_specs"
                        label="Bypass Cache"
                        color="secondary"
                        inset
                        density="compact"
                        hide-details
                      ></v-switch>
                    </div>

                    <div v-if="crawlParams.deep_crawl" class="mb-3">
                      <v-select
                        v-model="crawlParams.selected_model_ids"
                        :items="availableModelsForSelection"
                        item-title="model_name"
                        item-value="id"
                        label="Target Specific Models"
                        variant="outlined"
                        density="comfortable"
                        color="secondary"
                        multiple
                        chips
                        clearable
                        hint="Select specific models to harvest. (Bypasses Stage 2 discovery)"
                        persistent-hint
                      ></v-select>
                    </div>

                    <v-btn
                      color="secondary"
                      block
                      height="45"
                      prepend-icon="mdi-database-import"
                      class="outfit-font text-capitalize font-weight-bold"
                      :disabled="store.crawlStatus.active || approvedManufacturersCount === 0"
                      :loading="store.crawlLoading"
                      @click="triggerSpecsHarvester"
                    >
                      Harvest Approved Manufacturers Specs
                    </v-btn>
                  </v-col>
                </v-row>
              </v-card>

              <!-- Live Crawler Tracker -->
              <v-card class="glass-card pa-6 mb-6" rounded="xl">
                <div class="d-flex justify-space-between align-center mb-6">
                  <div>
                    <h3 class="outfit-font text-h5 font-weight-black text-white">
                      <v-icon icon="mdi-pulse" color="secondary" class="mr-2"></v-icon>Live Crawler Tracker
                    </h3>
                    <p class="text-caption text-medium-emphasis">Background harvester active queues and rates logs.</p>
                  </div>
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
                  height="16"
                  rounded
                  striped
                  class="mb-4 glow-progress"
                ></v-progress-linear>

                <div class="d-flex justify-space-between text-body-2 text-medium-emphasis mb-8">
                  <span class="d-flex align-center">
                    <v-icon icon="mdi-information-outline" start size="14" class="mr-1"></v-icon>
                    Status: {{ store.crawlStatus.status_msg }}
                  </span>
                  <span class="font-weight-black text-white text-subtitle-1">{{ store.crawlStatus.percent }}%</span>
                </div>

                <!-- Stop Button -->
                <div v-if="store.crawlStatus.active" class="d-flex justify-center mb-8">
                  <v-btn
                    color="error"
                    variant="flat"
                    prepend-icon="mdi-stop-circle"
                    size="large"
                    class="outfit-font text-capitalize font-weight-bold px-8 border-glass animate-pulse"
                    :loading="stoppingCrawl"
                    @click="stopActiveCrawl"
                  >
                    Abort Active Task
                  </v-btn>
                </div>

                <!-- Telemetry Counters -->
                <v-row class="text-center mt-2">
                  <v-col cols="4">
                    <v-card class="pa-4 bg-glass-surface" rounded="lg" border>
                      <div class="text-h4 outfit-font font-weight-black text-white mb-1">
                        {{ store.crawlStatus.discovered_manufacturers }}
                      </div>
                      <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">
                        Manufacturers Crawled
                      </div>
                    </v-card>
                  </v-col>
                  
                  <v-col cols="4">
                    <v-card class="pa-4 bg-glass-surface" rounded="lg" border>
                      <div class="text-h4 outfit-font font-weight-black text-white mb-1">
                        {{ store.crawlStatus.discovered_models }}
                      </div>
                      <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">
                        Models Found
                      </div>
                    </v-card>
                  </v-col>

                  <v-col cols="4">
                    <v-card class="pa-4 bg-glass-surface" rounded="lg" border>
                      <div class="text-h4 outfit-font font-weight-black glow-text-secondary mb-1">
                        {{ store.crawlStatus.enriched_records }}
                      </div>
                      <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">
                        Specs Enriched
                      </div>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card>

              <!-- Crawl Run History Log -->
              <v-card class="glass-card pa-6" rounded="xl">
                <div class="d-flex justify-space-between align-center mb-6">
                  <div>
                    <h3 class="outfit-font text-h5 font-weight-black text-white">
                      <v-icon icon="mdi-history" color="primary" class="mr-2"></v-icon>Crawl Run History Log
                    </h3>
                    <p class="text-caption text-medium-emphasis">Historical runs telemetry catalog stored in database.</p>
                  </div>
                  <v-btn color="secondary" variant="tonal" size="small" prepend-icon="mdi-refresh" @click="store.fetchCrawlHistory">Refresh Logs</v-btn>
                </div>

                <v-table v-if="crawlHistory.length > 0" class="glass-table-card elevation-2" rounded="lg">
                  <thead>
                    <tr>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Started At</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Category</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Duration</th>
                      <th class="text-left font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Status</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">New Manufacturers</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">New Models</th>
                      <th class="text-center font-weight-bold outfit-font text-subtitle-2 text-medium-emphasis py-4">Specs Populated</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="run in crawlHistory" :key="run.id" class="glass-table-row">
                      <td class="text-white py-3 font-weight-medium">{{ formatDateTime(run.started_at) }}</td>
                      <td class="text-medium-emphasis py-3">{{ run.compressor_type || 'All' }}</td>
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

        <!-- ── TAB 6: SYSTEM SETTINGS (NEW) ── -->
        <div v-show="tab === 'settings'">
          <v-row class="justify-center">
            <v-col cols="12" md="10">
              <!-- Dynamic Settings Editor -->
              <v-card class="glass-card pa-6" rounded="xl">
                <h3 class="outfit-font text-h5 font-weight-bold mb-4 white--text">
                  <v-icon icon="mdi-tune" color="primary" class="mr-2"></v-icon>Dynamic System Settings Editor
                </h3>
                <p class="text-caption text-medium-emphasis mb-5">
                  Tweak crawler query quotas, request intervals, and pgvector cosine search margins instantly.
                </p>

                <v-row v-if="systemSettings.length > 0">
                  <v-col v-for="setting in systemSettings" :key="setting.key" cols="12" sm="6" class="mb-4">
                    <v-card class="pa-4 bg-glass-surface" border rounded="xl" height="100%">
                      <div class="text-caption text-secondary font-weight-black mb-1">
                        {{ formatKey(setting.key) }}
                      </div>
                      <p class="text-caption text-medium-emphasis mb-3" style="min-height: 35px;">
                        {{ setting.description }}
                      </p>

                      <div class="d-flex align-center gap-2">
                        <!-- Upgraded limits slider max values up to 100 and 1000 based on key names -->
                        <v-slider
                          v-if="setting.value_type === 'int' || setting.value_type === 'float'"
                          v-model="setting.temp_val"
                          :min="setting.key.includes('DELAY') ? 0 : 1"
                          :max="setting.key.includes('MANUFACTURERS') ? 100 : (setting.key.includes('MODELS') ? 1000 : 10)"
                          :step="setting.value_type === 'float' ? 0.05 : 1"
                          thumb-label
                          color="secondary"
                          hide-details
                          class="flex-grow-1 mr-4"
                          @end="saveSetting(setting.key, setting.temp_val)"
                        ></v-slider>

                        <v-switch
                          v-else-if="setting.value_type === 'bool'"
                          v-model="setting.temp_val"
                          color="success"
                          density="compact"
                          inset
                          hide-details
                          @change="saveSetting(setting.key, setting.temp_val ? 'true' : 'false')"
                        ></v-switch>

                        <v-text-field
                          v-else
                          v-model="setting.temp_val"
                          variant="outlined"
                          density="compact"
                          hide-details
                          color="secondary"
                          append-inner-icon="mdi-content-save"
                          @click:append-inner="saveSetting(setting.key, setting.temp_val)"
                          @keyup.enter="saveSetting(setting.key, setting.temp_val)"
                        ></v-text-field>

                        <span class="text-subtitle-1 font-weight-bold text-white px-2">
                          {{ setting.temp_val }}
                        </span>
                      </div>
                    </v-card>
                  </v-col>
                </v-row>
                <div v-else class="text-center py-6 text-medium-emphasis">
                  <v-btn variant="tonal" color="primary" @click="fetchSettings">Load Configurations</v-btn>
                </div>
              </v-card>
            </v-col>
          </v-row>
        </div>

      </v-container>
    </v-main>

    <!-- ── POPUP DETAILED DRAWER ── -->
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

        <!-- Header -->
        <v-card-item class="pb-2">
          <div class="d-flex justify-space-between align-center">
            <span class="text-caption text-secondary font-weight-bold text-uppercase outfit-font">
              Detailed Specifications Worksheet
            </span>
            <v-btn icon="mdi-close" variant="text" color="medium-emphasis" density="comfortable" @click="drawer = false"></v-btn>
          </div>
        </v-card-item>

        <v-card-text v-if="selectedModel" class="px-6 py-4 overflow-y-auto" style="max-height: 60vh;">
          <!-- Model identification header -->
          <div class="mb-6">
            <span class="text-caption text-secondary font-weight-bold text-uppercase">
              {{ selectedModel.equipment_master }} $\rightarrow$ {{ selectedModel.equipment_type }}
            </span>
            <h2 class="outfit-font text-h4 font-weight-bold glow-text-primary mt-1 mb-2">
              {{ selectedModel.model_name }}
            </h2>
            <v-chip color="primary" class="font-weight-bold">{{ selectedModel.manufacturer.name }}</v-chip>
          </div>

          <!-- Manufacturer info -->
          <v-card class="pa-4 mb-6 bg-glass-surface" border rounded="lg">
            <h4 class="outfit-font font-weight-bold mb-2">
              <v-icon icon="mdi-domain" start size="16" color="secondary"></v-icon>Manufacturer Profile
            </h4>
            <div class="d-flex justify-space-between align-center flex-wrap gap-2">
              <span class="text-body-2 text-medium-emphasis">
                HQ Location: {{ selectedModel.manufacturer.country || 'Global HQ' }}
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
                Visit Site
              </v-btn>
            </div>
            <p v-if="selectedModel.manufacturer.description" class="text-caption text-medium-emphasis mt-2 italic">
              "{{ selectedModel.manufacturer.description }}"
            </p>
          </v-card>

          <!-- Specifications Sheet -->
          <div class="mb-4">
            <div class="d-flex justify-space-between align-center mb-4">
              <h3 class="outfit-font text-h6 font-weight-bold white--text">
                <v-icon icon="mdi-playlist-check" start color="secondary"></v-icon>Technical Attributes
              </h3>
              
              <!-- Inline model approval -->
              <v-chip
                :color="selectedModel.is_approved ? 'success' : 'warning'"
                variant="flat"
                class="font-weight-bold cursor-pointer"
                @click="toggleModelApprovalInline(selectedModel)"
              >
                <v-icon start :icon="selectedModel.is_approved ? 'mdi-check-decagram' : 'mdi-clock-outline'"></v-icon>
                {{ selectedModel.is_approved ? 'Approved in Catalog' : 'Approve Model' }}
              </v-chip>
            </div>

            <!-- Grid sheet attributes -->
            <v-row v-if="hasSpecs" dense>
              <v-col
                v-for="(val, key) in filteredAttributes"
                :key="key"
                cols="12"
                sm="6"
                class="mb-3"
              >
                <v-card class="pa-3 bg-glass-surface-dense" border rounded="md" height="100%">
                  <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold mb-1">
                    {{ formatKey(key) }}
                  </div>
                  <div class="text-body-1 text-white font-weight-medium">
                    {{ formatVal(key, val) }}
                  </div>
                </v-card>
              </v-col>
            </v-row>

            <div v-else class="text-center py-12 text-medium-emphasis">
              <v-icon icon="mdi-file-cancel-outline" size="48" class="mb-2"></v-icon>
              <p>No specifications compiled for this model yet.</p>
            </div>
          </div>
        </v-card-text>

        <!-- Footer actions -->
        <v-card-actions v-if="selectedModel" class="px-6 py-4 border-top bg-glass-surface">
          <v-btn
            v-if="selectedModel.product_url"
            :href="selectedModel.product_url"
            target="_blank"
            color="secondary"
            variant="flat"
            prepend-icon="mdi-card-text-outline"
            class="outfit-font text-capitalize flex-grow-1"
          >
            Open Catalog Page
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

    <!-- ── TAXONOMY CRUD DIALOG ── -->
    <v-dialog v-model="taxonomyDialog.active" max-width="500">
      <v-card class="glass-card border pa-4" rounded="xl">
        <v-card-title class="outfit-font font-weight-black text-h6 text-white mb-2">
          {{ taxonomyDialog.title }}
        </v-card-title>
        
        <v-card-text class="py-2">
          <v-text-field
            v-model="taxonomyDialog.name"
            label="Name"
            variant="outlined"
            density="comfortable"
            color="secondary"
            class="mb-3"
          ></v-text-field>

          <v-textarea
            v-if="taxonomyDialog.type !== 'subtype'"
            v-model="taxonomyDialog.description"
            label="Description (Optional)"
            variant="outlined"
            density="comfortable"
            color="secondary"
            rows="3"
          ></v-textarea>
        </v-card-text>

        <v-card-actions class="pt-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" class="text-capitalize" @click="taxonomyDialog.active = false">Cancel</v-btn>
          <v-btn color="secondary" variant="flat" class="text-capitalize px-6" :loading="taxonomyDialog.loading" @click="submitTaxonomyForm">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ── MANUFACTURER CRUD DIALOG ── -->
    <v-dialog v-model="manufacturerDialog.active" max-width="600">
      <v-card class="glass-card border pa-4" rounded="xl">
        <v-card-title class="outfit-font font-weight-black text-h6 text-white mb-2">
          {{ manufacturerDialog.title }}
        </v-card-title>
        
        <v-card-text class="py-2">
          <v-text-field
            v-model="manufacturerDialog.name"
            label="Company / Manufacturer Name"
            variant="outlined"
            density="comfortable"
            color="secondary"
            class="mb-3"
          ></v-text-field>

          <v-row dense>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="manufacturerDialog.country"
                label="HQ Country Location"
                variant="outlined"
                density="comfortable"
                color="secondary"
                class="mb-3"
              ></v-text-field>
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="manufacturerDialog.founded_year"
                label="Founded Year"
                type="number"
                variant="outlined"
                density="comfortable"
                color="secondary"
                class="mb-3"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-text-field
            v-model="manufacturerDialog.website"
            label="Official Website Domain"
            placeholder="e.g. atlascopco.com"
            variant="outlined"
            density="comfortable"
            color="secondary"
            class="mb-3"
          ></v-text-field>

          <v-textarea
            v-model="manufacturerDialog.description"
            label="Company Profile Summary"
            variant="outlined"
            density="comfortable"
            color="secondary"
            rows="3"
          ></v-textarea>
        </v-card-text>

        <v-card-actions class="pt-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" class="text-capitalize" @click="manufacturerDialog.active = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" class="text-capitalize px-6" :loading="manufacturerDialog.loading" @click="submitManufacturerForm">Save Profile</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="toast.active" :color="toast.color" timeout="3000" rounded="lg">
      {{ toast.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useCompressorStore } from './store/compressors'

const store = useCompressorStore()

// Navigation & Sidebar state
const tab = ref('overview')
const drawer = ref(false)
const initLoading = ref(false)
const viewMode = ref('grid')
const sidebarCollapsed = ref(false)

// Sidebar Nav Menu Items
const navItems = [
  { value: 'overview', title: 'Overview Dashboard', icon: 'mdi-view-dashboard-outline' },
  { value: 'catalog', title: 'Specifications Catalog', icon: 'mdi-database-search' },
  { value: 'taxonomy', title: 'Taxonomy Manager', icon: 'mdi-file-tree' },
  { value: 'manufacturers', title: 'Manufacturer Directory', icon: 'mdi-factory' },
  { value: 'crawler', title: 'Crawler Operator', icon: 'mdi-robot-mower' },
  { value: 'settings', title: 'System Settings', icon: 'mdi-cog-outline' }
]

const currentTabTitle = computed(() => {
  const match = navItems.find(n => n.value === tab.value)
  return match ? match.title : 'Details'
})

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
  equipment_master_id: null,
  equipment_type_id: null,
  manufacturer_id: null,
  is_approved: null
})

// Clear Checklist selections whenever catalog filters update
watch(filters, () => {
  selectedModelIds.value = []
}, { deep: true })

const crawlParams = ref({
  equipment_type_id: null,
  selected_manufacturer_ids: [],
  selected_model_ids: [],
  deep_crawl: true,
  only_unharvested: false,
  no_cache: false,
  no_cache_specs: false
})

const toast = ref({
  active: false,
  message: '',
  color: 'success'
})

const stoppingCrawl = ref(false)

// Taxonomy Form state
const taxonomyDialog = ref({
  active: false,
  title: '',
  type: '', // 'master', 'type', 'subtype'
  action: '', // 'create', 'edit'
  id: null,
  parentId: null,
  name: '',
  description: '',
  loading: false
})

// Manufacturer Form state
const manufacturerDialog = ref({
  active: false,
  title: '',
  action: '', // 'create', 'edit'
  id: null,
  name: '',
  country: '',
  website: '',
  founded_year: null,
  description: '',
  loading: false
})

// Catalog Selection and Sorting States
const selectedModelIds = ref([])
const sortBy = ref('model_name')
const sortDesc = ref(false)

// Lifecycle
onMounted(async () => {
  await store.fetchCompressors()
  await store.fetchModels()
  await store.fetchManufacturersList()
  await store.fetchCrawlStatus()
  await store.fetchCrawlHistory()
  await store.fetchTaxonomyTree()
  await store.fetchSettings()
  
  // Polling crawler status dynamically
  setInterval(() => {
    if (store.crawlStatus.active) {
      store.fetchCrawlStatus()
      if (store.crawlStatus.percent === 100) {
        store.fetchCompressors()
        store.fetchModels(filters.value)
        store.fetchManufacturersList()
        store.fetchCrawlHistory()
        store.fetchTaxonomyTree()
      }
    }
  }, 3000)
})

// Computeds
const models = computed(() => store.models || [])
const manufacturersList = computed(() => store.manufacturersList || [])
const crawlHistory = computed(() => store.crawlHistory || [])
const approvedManufacturersCount = computed(() => manufacturersList.value.filter(b => b.is_approved).length)
const taxonomyTree = computed(() => store.taxonomyTree || [])
const availableModelsForSelection = computed(() => {
  const approvedModels = models.value.filter(m => m.is_approved)
  if (!crawlParams.value.selected_manufacturer_ids || crawlParams.value.selected_manufacturer_ids.length === 0) {
    return approvedModels
  }
  return approvedModels.filter(m => crawlParams.value.selected_manufacturer_ids.includes(m.manufacturer_id))
})
const systemSettings = computed(() => {
  return (store.systemSettings || []).map(s => {
    if (s.temp_val === undefined) {
      if (s.value_type === 'int') s.temp_val = parseInt(s.value)
      else if (s.value_type === 'float') s.temp_val = parseFloat(s.value)
      else if (s.value_type === 'bool') s.temp_val = s.value === 'true'
      else s.temp_val = s.value
    }
    return s
  })
})

// Reactive Client-side Sorting of computed models array
const sortedModels = computed(() => {
  let list = [...models.value]
  list.sort((a, b) => {
    let valA = a[sortBy.value]
    let valB = b[sortBy.value]
    
    if (sortBy.value === 'created_at') {
      valA = valA ? new Date(valA) : new Date(0)
      valB = valB ? new Date(valB) : new Date(0)
    } else {
      valA = valA ? valA.toString().toLowerCase() : ''
      valB = valB ? valB.toString().toLowerCase() : ''
    }
    
    if (valA < valB) return sortDesc.value ? 1 : -1
    if (valA > valB) return sortDesc.value ? -1 : 1
    return 0
  })
  return list
})

// Bulk Select State Helpers
const isAllSelected = computed(() => {
  return sortedModels.value.length > 0 && selectedModelIds.value.length === sortedModels.value.length
})

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedModelIds.value = []
  } else {
    selectedModelIds.value = sortedModels.value.map(m => m.id)
  }
}

const bulkApprove = async (approveState) => {
  try {
    await store.bulkApproveModels(selectedModelIds.value, approveState)
    showToast(`Successfully ${approveState ? 'approved' : 'unapproved'} selected models!`, 'success')
    selectedModelIds.value = []
    fetchModels()
  } catch (err) {
    showToast('Failed to update status for selected models.', 'error')
  }
}

// Overview Dashboard Dynamic Stats List
const overviewStats = computed(() => {
  let subtypesCount = 0
  let typesCount = 0
  taxonomyTree.value.forEach(m => {
    typesCount += (m.types || []).length
    m.types.forEach(t => {
      subtypesCount += (t.subtypes || []).length
    })
  })
  
  const specsEnriched = models.value.filter(m => m.is_harvested).length

  return [
    { title: 'Masters Categories', value: taxonomyTree.value.length, icon: 'mdi-robot-industrial', color: '#8B5CF6', colorBg: 'rgba(139, 92, 246, 0.1)' },
    { title: 'Equipment Types', value: typesCount, icon: 'mdi-shape-outline', color: '#06B6D4', colorBg: 'rgba(6, 182, 212, 0.1)' },
    { title: 'Equipment Subtypes', value: subtypesCount, icon: 'mdi-tag-multiple-outline', color: '#10B981', colorBg: 'rgba(16, 185, 129, 0.1)' },
    { title: 'Approved Manufacturers', value: approvedManufacturersCount.value, icon: 'mdi-factory', color: '#F59E0B', colorBg: 'rgba(245, 158, 11, 0.1)' },
    { title: 'Discovered Models', value: models.value.length, icon: 'mdi-database', color: '#3B82F6', colorBg: 'rgba(59, 130, 246, 0.1)' },
    { title: 'Specs Enriched', value: specsEnriched, icon: 'mdi-playlist-check', color: '#EF4444', colorBg: 'rgba(239, 68, 68, 0.1)' }
  ]
})

// Filter builders
const equipmentMastersList = computed(() => {
  return taxonomyTree.value.map(m => ({ id: m.id, name: m.name }))
})

const filteredTypes = computed(() => {
  if (!filters.value.equipment_master_id) {
    const list = []
    taxonomyTree.value.forEach(m => {
      list.push(...(m.types || []))
    })
    return list
  }
  const match = taxonomyTree.value.find(m => m.id === filters.value.equipment_master_id)
  return match ? match.types : []
})

const manufacturersListForFilter = computed(() => {
  const list = []
  const ids = new Set()
  const tree = store.compressorTree || []
  tree.forEach(t => {
    if (filters.value.equipment_type_id && t.id !== filters.value.equipment_type_id) return
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

const equipmentTypesDropdown = computed(() => {
  const list = [{ name: 'Crawl All Categories', id: null }]
  taxonomyTree.value.forEach(m => {
    (m.types || []).forEach(t => {
      list.push({ name: `${m.name} ➔ ${t.name}`, id: t.id })
    })
  })
  return list
})

const approvedManufacturers = computed(() => {
  return manufacturersList.value.filter(b => b.is_approved)
})

// Specs details Computes
const selectedModel = computed(() => store.selectedModel)

const hasSpecs = computed(() => {
  return selectedModel.value && 
         selectedModel.value.attributes && 
         Object.keys(selectedModel.value.attributes).length > 0 &&
         Object.values(selectedModel.value.attributes).some(v => v !== null)
})

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

const onMasterFilterChange = () => {
  filters.value.equipment_type_id = null
  fetchModels()
}

const fetchManufacturers = async () => {
  await store.fetchManufacturersList()
}

const toggleApproval = async (manufacturerId, isApproved) => {
  try {
    await store.toggleManufacturerApproval(manufacturerId, isApproved)
    showToast(`Manufacturer approval toggled!`, 'success')
  } catch (err) {
    showToast('Failed to update manufacturer status.', 'error')
  }
}

const toggleModelApproval = async (modelId, isApproved) => {
  try {
    await store.toggleModelApproval(modelId, isApproved)
    showToast(`Model approval toggled!`, 'success')
    fetchModels()
  } catch (err) {
    showToast('Failed to update model status.', 'error')
  }
}

const toggleModelApprovalInline = async (model) => {
  const nextVal = !model.is_approved
  await toggleModelApproval(model.id, nextVal)
  model.is_approved = nextVal
}

const resetFilters = () => {
  filters.value = {
    q: '',
    equipment_master_id: null,
    equipment_type_id: null,
    manufacturer_id: null,
    is_approved: null
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
    await store.fetchTaxonomyTree()
    await store.fetchSettings()
    await store.fetchCompressors()
    showToast(res.message, 'success')
  } catch (err) {
    showToast('Failed to initialize database schemas.', 'error')
  } finally {
    initLoading.value = false
  }
}

const triggerManufacturerDiscovery = async () => {
  try {
    const res = await store.triggerManufacturerDiscovery(
      crawlParams.value.equipment_type_id,
      crawlParams.value.no_cache
    )
    showToast(res.message, 'success')
  } catch (err) {
    showToast('Failed to trigger manufacturer discovery.', 'error')
  }
}

const triggerSpecsHarvester = async () => {
  try {
    const mfrIds = crawlParams.value.selected_manufacturer_ids.length > 0 
      ? crawlParams.value.selected_manufacturer_ids 
      : null
      
    const modelIds = (crawlParams.value.deep_crawl && crawlParams.value.selected_model_ids.length > 0)
      ? crawlParams.value.selected_model_ids
      : null

    const res = await store.triggerSpecsHarvester(
      mfrIds,
      crawlParams.value.only_unharvested,
      crawlParams.value.no_cache_specs,
      modelIds,
      crawlParams.value.deep_crawl
    )
    showToast(res.message, 'success')
  } catch (err) {
    showToast('Failed to trigger specifications harvester.', 'error')
  }
}

const stopActiveCrawl = async () => {
  stoppingCrawl.value = true
  try {
    const res = await store.stopCrawl()
    showToast(res.message || 'Stop request successfully sent.', 'warning')
  } catch (err) {
    showToast('Failed to stop the active crawl process.', 'error')
  } finally {
    stoppingCrawl.value = false
  }
}

const saveSetting = async (key, val) => {
  try {
    await store.updateSetting(key, val)
    showToast(`Setting '${formatKey(key)}' updated to ${val}!`, 'success')
  } catch (err) {
    showToast('Failed to update system setting.', 'error')
  }
}

const fetchSettings = async () => {
  await store.fetchSettings()
}

// ── Taxonomy Form Controllers ──────────────────────────────────────────────

const openAddMaster = () => {
  taxonomyDialog.value = {
    active: true,
    title: 'Create Master Equipment Category',
    type: 'master',
    action: 'create',
    name: '',
    description: '',
    id: null,
    loading: false
  }
}

const openEditMaster = (master) => {
  taxonomyDialog.value = {
    active: true,
    title: 'Edit Master Equipment Category',
    type: 'master',
    action: 'edit',
    name: master.name,
    description: master.description,
    id: master.id,
    loading: false
  }
}

const deleteMaster = async (id) => {
  if (confirm('Warning: Deleting this equipment category will permanently delete all its underlying types, subtypes, and models. Continue?')) {
    try {
      await store.deleteMaster(id)
      showToast('Equipment master category deleted successfully.', 'success')
    } catch (err) {
      showToast('Delete operation failed.', 'error')
    }
  }
}

const openAddType = (masterId) => {
  taxonomyDialog.value = {
    active: true,
    title: 'Add Equipment Type Category',
    type: 'type',
    action: 'create',
    name: '',
    description: '',
    id: null,
    parentId: masterId,
    loading: false
  }
}

const openEditType = (etype) => {
  taxonomyDialog.value = {
    active: true,
    title: 'Edit Equipment Type Category',
    type: 'type',
    action: 'edit',
    name: etype.name,
    description: etype.description,
    id: etype.id,
    parentId: etype.equipment_master_id,
    loading: false
  }
}

const deleteType = async (id) => {
  if (confirm('Warning: Deleting this type category will permanently delete all its subtypes and models. Continue?')) {
    try {
      await store.deleteType(id)
      showToast('Equipment type category deleted successfully.', 'success')
    } catch (err) {
      showToast('Delete operation failed.', 'error')
    }
  }
}

const openAddSubtype = (typeId) => {
  taxonomyDialog.value = {
    active: true,
    title: 'Add Equipment Subtype',
    type: 'subtype',
    action: 'create',
    name: '',
    description: '',
    id: null,
    parentId: typeId,
    loading: false
  }
}

const openEditSubtype = (subtype) => {
  taxonomyDialog.value = {
    active: true,
    title: 'Edit Equipment Subtype',
    type: 'subtype',
    action: 'edit',
    name: subtype.name,
    description: '',
    id: subtype.id,
    parentId: subtype.type_id,
    loading: false
  }
}

const deleteSubtype = async (id) => {
  if (confirm('Delete this equipment subtype?')) {
    try {
      await store.deleteSubtype(id)
      showToast('Equipment subtype deleted successfully.', 'success')
    } catch (err) {
      showToast('Delete operation failed.', 'error')
    }
  }
}

const submitTaxonomyForm = async () => {
  const d = taxonomyDialog.value
  if (!d.name || !d.name.trim()) {
    showToast('Name is a required field.', 'error')
    return
  }
  d.loading = true
  try {
    if (d.type === 'master') {
      if (d.action === 'create') {
        await store.createMaster(d.name, d.description)
      } else {
        await store.updateMaster(d.id, d.name, d.description)
      }
    } else if (d.type === 'type') {
      if (d.action === 'create') {
        await store.createType(d.name, d.parentId, d.description)
      } else {
        await store.updateType(d.id, d.name, d.parentId, d.description)
      }
    } else if (d.type === 'subtype') {
      if (d.action === 'create') {
        await store.createSubtype(d.name, d.parentId)
      } else {
        await store.updateSubtype(d.id, d.name, d.parentId)
      }
    }
    showToast('Taxonomy folder tree updated successfully!', 'success')
    d.active = false
  } catch (err) {
    showToast(`Operation failed: ${err.response?.data?.detail || err.message}`, 'error')
  } finally {
    d.loading = false
  }
}


// ── Manufacturer Form Controllers ───────────────────────────────────────────

const openAddManufacturer = () => {
  manufacturerDialog.value = {
    active: true,
    title: 'Register New Manufacturer',
    action: 'create',
    id: null,
    name: '',
    country: '',
    website: '',
    founded_year: null,
    description: '',
    loading: false
  }
}

const openEditManufacturer = (manufacturer) => {
  manufacturerDialog.value = {
    active: true,
    title: `Modify Profile: ${manufacturer.name}`,
    action: 'edit',
    id: manufacturer.id,
    name: manufacturer.name,
    country: manufacturer.country || '',
    website: manufacturer.website || '',
    founded_year: manufacturer.founded_year || null,
    description: manufacturer.description || '',
    loading: false
  }
}

const deleteManufacturer = async (id) => {
  if (confirm('Warning: Deleting this manufacturer will permanently erase all its harvested models and spec worksheets from the database. Continue?')) {
    try {
      await store.deleteManufacturer(id)
      showToast('Manufacturer registration deleted successfully.', 'success')
    } catch (err) {
      showToast('Delete manufacturer operation failed.', 'error')
    }
  }
}

const submitManufacturerForm = async () => {
  const m = manufacturerDialog.value
  if (!m.name || !m.name.trim()) {
    showToast('Manufacturer Name is a required field.', 'error')
    return
  }
  m.loading = true
  
  const payload = {
    name: m.name,
    country: m.country ? m.country.trim() : null,
    website: m.website ? m.website.trim() : null,
    founded_year: m.founded_year ? parseInt(m.founded_year) : null,
    description: m.description ? m.description.trim() : null
  }
  
  try {
    if (m.action === 'create') {
      await store.createManufacturer(payload)
      showToast(`Manufacturer '${payload.name}' registered successfully!`, 'success')
    } else {
      await store.updateManufacturer(m.id, payload)
      showToast(`Manufacturer profile updated successfully!`, 'success')
    }
    m.active = false
  } catch (err) {
    showToast(`Operation failed: ${err.response?.data?.detail || err.message}`, 'error')
  } finally {
    m.loading = false
  }
}


// Format helpers
const formatDateTime = (isoString) => {
  if (!isoString) return '—'
  const date = new Date(isoString)
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
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

const showToast = (message, color = 'success') => {
  toast.value = {
    active: true,
    message,
    color
  }
}
</script>

<style>
/* Typography and General resets */
.v-application {
  font-family: 'Inter', sans-serif !important;
}
.outfit-font {
  font-family: 'Outfit', sans-serif !important;
}

/* Glassmorphism sidebar navigation drawer */
.glass-sidebar {
  background: rgba(9, 10, 15, 0.85) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
  transition: width 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}

/* App Header styling */
.glass-header {
  background: rgba(9, 10, 15, 0.6) !important;
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
  position: fixed !important;
  z-index: 100 !important;
}

/* Sidebar Nav active highlights */
.sidebar-nav-item {
  color: rgba(255, 255, 255, 0.7) !important;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  border: 1px solid transparent !important;
}
.sidebar-nav-item:hover {
  background: rgba(255, 255, 255, 0.03) !important;
  color: white !important;
  border-color: rgba(255, 255, 255, 0.05) !important;
}
.v-list-item--active.sidebar-nav-item {
  background: rgba(139, 92, 246, 0.15) !important;
  color: #8b5cf6 !important;
  border-color: rgba(139, 92, 246, 0.25) !important;
  text-shadow: 0 0 8px rgba(139, 92, 246, 0.2);
}

/* Glow styles */
.glowing-avatar {
  box-shadow: 0 0 15px rgba(139, 92, 246, 0.4);
}
.glow-text-primary {
  color: #8b5cf6;
  text-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
}
.glow-text-secondary {
  color: #06b6d4;
  text-shadow: 0 0 10px rgba(6, 182, 212, 0.5);
}
.glow-progress {
  box-shadow: 0 0 8px rgba(6, 182, 212, 0.2);
}

/* Glassmorphism General Card */
.glass-card {
  background: rgba(255, 255, 255, 0.01) !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.06) !important;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
  color: white !important;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.glass-card:hover {
  transform: translateY(-2px);
  border-color: rgba(6, 182, 212, 0.25) !important;
}

/* Background gradient glows for stats cards */
.relative {
  position: relative;
}
.stat-gradient-glow {
  position: absolute;
  top: -30%;
  right: -30%;
  width: 120px;
  height: 120px;
  opacity: 0.15;
  pointer-events: none;
  filter: blur(15px);
}

/* Glassmorphism Surface blocks */
.bg-glass-surface {
  background: rgba(255, 255, 255, 0.01) !important;
  border-color: rgba(255, 255, 255, 0.04) !important;
}
.bg-glass-surface-dense {
  background: rgba(255, 255, 255, 0.02) !important;
  border-color: rgba(255, 255, 255, 0.05) !important;
}
.bg-glass-sub-panel {
  background: rgba(255, 255, 255, 0.005) !important;
}
.bg-rgba-white-02 {
  background: rgba(255, 255, 255, 0.01) !important;
}

/* Indicator bars */
.border-left-indicator {
  border-left: 2px dashed rgba(139, 92, 246, 0.2) !important;
}
.border-top {
  border-top: 1px solid rgba(255, 255, 255, 0.05) !important;
}
.border-left {
  border-left: 1px solid rgba(255, 255, 255, 0.05) !important;
}
.border-right {
  border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
}
.border-glass {
  border-color: rgba(255, 255, 255, 0.05) !important;
}

/* Glass table card styles */
.glass-table-card {
  background: rgba(255, 255, 255, 0.005) !important;
  border: 1px solid rgba(255, 255, 255, 0.04) !important;
}
.glass-table-card th {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
  background: rgba(255, 255, 255, 0.01) !important;
  color: rgba(255, 255, 255, 0.7) !important;
}
.glass-table-row {
  cursor: pointer;
  transition: all 0.2s ease;
}
.glass-table-row:hover {
  background: rgba(255, 255, 255, 0.03) !important;
}
.glass-table-row td {
  border-bottom: 1px solid rgba(255, 255, 255, 0.02) !important;
}

/* Catalog View Toggles */
.glass-toggle {
  background: rgba(255, 255, 255, 0.02) !important;
  border: 1px solid rgba(255, 255, 255, 0.06) !important;
  border-radius: 8px !important;
}
.glass-toggle-selected {
  background: rgba(6, 182, 212, 0.15) !important;
  color: #06b6d4 !important;
}

/* Expand panels custom */
.glass-panel-item {
  background: rgba(255, 255, 255, 0.01) !important;
  border-color: rgba(255, 255, 255, 0.04) !important;
}

/* Sidebar safe scrolls */
.sticky-sidebar {
  position: sticky !important;
  top: 90px !important;
  z-index: 5;
  align-self: flex-start !important;
  max-height: calc(100vh - 110px) !important;
  overflow-y: auto !important;
}

/* Animations */
.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: .7;
  }
}

/* Checkbox positions on grid cards */
.position-checkbox-overlay {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
}

/* Selection card borders styling */
.selected-card-border {
  border-color: rgba(6, 182, 212, 0.6) !important;
  background: rgba(6, 182, 212, 0.03) !important;
}
.selected-row-bg {
  background: rgba(6, 182, 212, 0.05) !important;
}

/* Glower bulk actions */
.bg-primary-glowing {
  background: rgba(139, 92, 246, 0.15) !important;
  border-color: rgba(139, 92, 246, 0.4) !important;
  box-shadow: 0 0 15px rgba(139, 92, 246, 0.25) !important;
}

/* Taxonomy Chip styles custom */
.subtype-chip {
  padding-right: 4px !important;
}
.icon-btn-hover {
  opacity: 0.7;
  transition: opacity 0.2s ease;
}
.icon-btn-hover:hover {
  opacity: 1;
}

/* Select Checkbox fixes */
.select-all-checkbox .v-label {
  color: rgba(255, 255, 255, 0.8) !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: bold !important;
  font-size: 14px !important;
}

/* Layout Utilities */
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.leading-tight { line-height: 1.25; }
.italic { font-style: italic; }
.max-width-sort {
  max-width: 320px;
}
</style>
