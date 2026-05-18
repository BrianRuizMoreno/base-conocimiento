import axios from 'axios'

const isProduction = import.meta.env.PROD

export const client = axios.create({
  baseURL: isProduction ? '/api' : (import.meta.env.VITE_API_URL || '/api'),
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add PIN header
client.interceptors.request.use((config) => {
  const pin = localStorage.getItem('pin')
  if (pin) {
    config.headers['X-Auth-PIN'] = pin
  }
  return config
})

// Handle errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('pin')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)
