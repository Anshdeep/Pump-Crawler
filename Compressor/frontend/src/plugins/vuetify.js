import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: {
        colors: {
          primary: '#8B5CF6',     // Premium Electric Purple
          secondary: '#06B6D4',   // Cyber Cyan
          background: '#090A0F',  // Obsidian Deep Space
          surface: '#151722',     // Sleek Charcoal Glass surface
          success: '#10B981',     // Emerald Green
          warning: '#F59E0B',     // Golden Amber
          error: '#EF4444',       // Vibrant Coral Red
          info: '#3B82F6',        // Electric Blue
        }
      }
    }
  }
})
