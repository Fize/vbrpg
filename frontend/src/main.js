import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './assets/styles/global.css'
import './assets/styles/transitions.css'
import './assets/styles/typography.css'
import './assets/styles/interactive.css'
import App from './App.vue'
import router from './router'
import pinia from './stores'

const app = createApp(App)

app.use(ElementPlus)
app.use(router)
app.use(pinia)

app.mount('#app')
