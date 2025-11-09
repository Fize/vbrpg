/**
 * Image and Asset Optimization Utilities
 * Provides lazy loading, responsive images, and performance optimization
 */

/**
 * Lazy load images with Intersection Observer
 * @param {string} selector - CSS selector for images to lazy load
 */
export function enableLazyLoading(selector = 'img[data-src]') {
  if (!('IntersectionObserver' in window)) {
    // Fallback for browsers without IntersectionObserver
    document.querySelectorAll(selector).forEach(img => {
      img.src = img.dataset.src
      if (img.dataset.srcset) {
        img.srcset = img.dataset.srcset
      }
    })
    return
  }

  const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target
        
        // Load the image
        if (img.dataset.src) {
          img.src = img.dataset.src
        }
        if (img.dataset.srcset) {
          img.srcset = img.dataset.srcset
        }
        
        // Remove data attributes
        img.removeAttribute('data-src')
        img.removeAttribute('data-srcset')
        
        // Stop observing
        observer.unobserve(img)
        
        // Add loaded class
        img.classList.add('loaded')
      }
    })
  }, {
    rootMargin: '50px 0px', // Start loading 50px before entering viewport
    threshold: 0.01
  })

  document.querySelectorAll(selector).forEach(img => {
    imageObserver.observe(img)
  })
}

/**
 * Preload critical images
 * @param {string[]} urls - Array of image URLs to preload
 */
export function preloadImages(urls) {
  urls.forEach(url => {
    const link = document.createElement('link')
    link.rel = 'preload'
    link.as = 'image'
    link.href = url
    document.head.appendChild(link)
  })
}

/**
 * Generate srcset for responsive images
 * @param {string} basePath - Base path of the image (without extension)
 * @param {string} extension - Image extension (e.g., 'jpg', 'png', 'webp')
 * @param {number[]} widths - Array of image widths
 * @returns {string} srcset attribute value
 */
export function generateSrcset(basePath, extension, widths = [320, 640, 1024, 1920]) {
  return widths
    .map(width => `${basePath}-${width}w.${extension} ${width}w`)
    .join(', ')
}

/**
 * Get optimal image format based on browser support
 * @returns {string} 'webp', 'avif', or 'jpg'
 */
export function getOptimalImageFormat() {
  const canvas = document.createElement('canvas')
  canvas.width = 1
  canvas.height = 1
  
  // Check WebP support
  if (canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0) {
    return 'webp'
  }
  
  // Check AVIF support (requires async check, fallback to webp/jpg)
  const avifSupport = new Image()
  avifSupport.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADybWV0YQAAAAAAAAAoaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAGxpYmF2aWYAAAAADnBpdG0AAAAAAAEAAAAeaWxvYwAAAABEAAABAAEAAAABAAABGgAAAB0AAAAoaWluZgAAAAAAAQAAABppbmZlAgAAAAABAABhdjAxQ29sb3IAAAAAamlwcnAAAABLaXBjbwAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAAAxhdjFDgQ0MAAAAABNjb2xybmNseAACAAIAAYAAAAAXaXBtYQAAAAAAAAABAAEEAQKDBAAAACVtZGF0EgAKCBgANogQEAwgMg8f8D///8WfhwB8+ErK42A='
  
  return 'jpg' // Default fallback
}

/**
 * Compress and optimize image data URL
 * @param {string} dataUrl - Image data URL
 * @param {number} quality - Compression quality (0-1)
 * @returns {Promise<string>} Optimized data URL
 */
export function optimizeImageDataUrl(dataUrl, quality = 0.8) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.width
      canvas.height = img.height
      
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      
      resolve(canvas.toDataURL('image/jpeg', quality))
    }
    img.onerror = reject
    img.src = dataUrl
  })
}

/**
 * Create blur placeholder from image
 * @param {HTMLImageElement} img - Image element
 * @param {number} blurAmount - Blur radius
 * @returns {string} Data URL of blurred placeholder
 */
export function createBlurPlaceholder(img, blurAmount = 10) {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  
  // Small size for placeholder
  canvas.width = 40
  canvas.height = 40
  
  // Draw and blur
  ctx.filter = `blur(${blurAmount}px)`
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
  
  return canvas.toDataURL('image/jpeg', 0.5)
}

/**
 * Monitor image loading performance
 * @param {string} selector - CSS selector for images to monitor
 */
export function monitorImagePerformance(selector = 'img') {
  if (!('PerformanceObserver' in window)) return
  
  const observer = new PerformanceObserver((list) => {
    list.getEntries().forEach((entry) => {
      if (entry.initiatorType === 'img') {
        console.log(`Image loaded: ${entry.name}`)
        console.log(`  Duration: ${entry.duration.toFixed(2)}ms`)
        console.log(`  Size: ${(entry.transferSize / 1024).toFixed(2)}KB`)
      }
    })
  })
  
  observer.observe({ entryTypes: ['resource'] })
}

/**
 * Image cache manager
 */
class ImageCache {
  constructor(maxSize = 50) {
    this.cache = new Map()
    this.maxSize = maxSize
  }
  
  add(url, blob) {
    if (this.cache.size >= this.maxSize) {
      // Remove oldest entry
      const firstKey = this.cache.keys().next().value
      this.cache.delete(firstKey)
    }
    this.cache.set(url, blob)
  }
  
  get(url) {
    return this.cache.get(url)
  }
  
  has(url) {
    return this.cache.has(url)
  }
  
  clear() {
    this.cache.clear()
  }
}

export const imageCache = new ImageCache()

/**
 * Fetch and cache image
 * @param {string} url - Image URL
 * @returns {Promise<Blob>} Image blob
 */
export async function fetchAndCacheImage(url) {
  if (imageCache.has(url)) {
    return imageCache.get(url)
  }
  
  const response = await fetch(url)
  const blob = await response.blob()
  imageCache.add(url, blob)
  
  return blob
}

/**
 * Progressive image loader component helper
 * @param {string} lowQualityUrl - Low quality placeholder image
 * @param {string} highQualityUrl - High quality full image
 * @param {HTMLElement} container - Container element
 */
export function loadProgressiveImage(lowQualityUrl, highQualityUrl, container) {
  // Load low quality first
  const lowQualityImg = new Image()
  lowQualityImg.src = lowQualityUrl
  lowQualityImg.style.filter = 'blur(10px)'
  lowQualityImg.style.transition = 'opacity 0.3s'
  container.appendChild(lowQualityImg)
  
  // Load high quality in background
  const highQualityImg = new Image()
  highQualityImg.onload = () => {
    highQualityImg.style.opacity = '0'
    highQualityImg.style.transition = 'opacity 0.3s'
    container.appendChild(highQualityImg)
    
    // Fade in high quality
    setTimeout(() => {
      highQualityImg.style.opacity = '1'
    }, 10)
    
    // Remove low quality after transition
    setTimeout(() => {
      if (lowQualityImg.parentNode) {
        lowQualityImg.remove()
      }
    }, 300)
  }
  highQualityImg.src = highQualityUrl
}

/**
 * Asset loading priority manager
 */
export const AssetPriority = {
  CRITICAL: 0,   // Load immediately (above fold)
  HIGH: 1,       // Load soon (near viewport)
  MEDIUM: 2,     // Load when idle (below fold)
  LOW: 3         // Load on interaction
}

/**
 * Smart asset loader with priority queue
 */
class AssetLoader {
  constructor() {
    this.queue = []
    this.loading = new Set()
    this.loaded = new Set()
    this.maxConcurrent = 4
  }
  
  add(url, priority = AssetPriority.MEDIUM, callback) {
    if (this.loaded.has(url)) {
      callback?.(url)
      return
    }
    
    this.queue.push({ url, priority, callback })
    this.queue.sort((a, b) => a.priority - b.priority)
    this.processQueue()
  }
  
  async processQueue() {
    while (this.queue.length > 0 && this.loading.size < this.maxConcurrent) {
      const item = this.queue.shift()
      if (!item) break
      
      this.loading.add(item.url)
      
      try {
        await fetchAndCacheImage(item.url)
        this.loaded.add(item.url)
        item.callback?.(item.url)
      } catch (error) {
        console.error(`Failed to load asset: ${item.url}`, error)
      } finally {
        this.loading.delete(item.url)
        this.processQueue()
      }
    }
  }
  
  clear() {
    this.queue = []
    this.loading.clear()
  }
}

export const assetLoader = new AssetLoader()

/**
 * Initialize all image optimizations
 */
export function initImageOptimizations() {
  // Enable lazy loading
  enableLazyLoading()
  
  // Monitor performance in development
  if (import.meta.env.DEV) {
    monitorImagePerformance()
  }
  
  // Re-observe on DOM changes
  const observer = new MutationObserver(() => {
    enableLazyLoading()
  })
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  })
}
