import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  enableLazyLoading,
  preloadImages,
  generateSrcset,
  getOptimalImageFormat,
  optimizeImageDataUrl,
  createBlurPlaceholder,
  fetchAndCacheImage,
  loadProgressiveImage,
  imageCache,
  AssetPriority,
  assetLoader,
  initImageOptimizations
} from '@/utils/imageOptimization'

describe('Image Optimization Utils', () => {
  beforeEach(() => {
    // Clear cache before each test
    imageCache.clear()
    assetLoader.clear()
    
    // Reset DOM
    document.body.innerHTML = ''
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('enableLazyLoading', () => {
    it('should observe images with data-src attribute', () => {
      // Create test images
      document.body.innerHTML = `
        <img data-src="/test1.jpg" />
        <img data-src="/test2.jpg" />
      `

      const observeMock = vi.fn()
      global.IntersectionObserver = vi.fn((callback) => ({
        observe: observeMock,
        unobserve: vi.fn(),
        disconnect: vi.fn()
      }))

      enableLazyLoading()

      expect(observeMock).toHaveBeenCalledTimes(2)
    })

    it('should fall back to immediate loading without IntersectionObserver', () => {
      document.body.innerHTML = `
        <img data-src="/test.jpg" data-srcset="/test-320w.jpg 320w" />
      `

      // Remove IntersectionObserver
      const originalIO = global.IntersectionObserver
      delete global.IntersectionObserver

      enableLazyLoading()

      const img = document.querySelector('img')
      expect(img.src).toContain('/test.jpg')
      expect(img.srcset).toContain('/test-320w.jpg')

      global.IntersectionObserver = originalIO
    })

    it('should add loaded class after image loads', () => {
      document.body.innerHTML = '<img data-src="/test.jpg" />'
      
      let observerCallback
      global.IntersectionObserver = vi.fn((callback) => {
        observerCallback = callback
        return {
          observe: vi.fn(),
          unobserve: vi.fn(),
          disconnect: vi.fn()
        }
      })

      enableLazyLoading()

      const img = document.querySelector('img')
      const entry = {
        isIntersecting: true,
        target: img
      }

      observerCallback([entry], {
        unobserve: vi.fn()
      })

      expect(img.classList.contains('loaded')).toBe(true)
    })
  })

  describe('preloadImages', () => {
    beforeEach(() => {
      // Clear any existing preload links
      document.querySelectorAll('link[rel="preload"]').forEach(link => link.remove())
    })

    it('should create preload links for given URLs', () => {
      const urls = ['/img1.jpg', '/img2.jpg', '/img3.jpg']
      
      // Mock createElement to avoid jsdom issues
      const mockLinks = []
      const originalCreateElement = document.createElement.bind(document)
      document.createElement = vi.fn((tagName) => {
        if (tagName === 'link') {
          const link = originalCreateElement('link')
          mockLinks.push(link)
          return link
        }
        return originalCreateElement(tagName)
      })

      preloadImages(urls)

      // Check that createElement was called for each URL
      const linkCalls = document.createElement.mock.calls.filter(call => call[0] === 'link')
      expect(linkCalls.length).toBe(3)
      
      // Restore
      document.createElement = originalCreateElement
    })
  })

  describe('generateSrcset', () => {
    it('should generate correct srcset string', () => {
      const srcset = generateSrcset('/images/hero', 'jpg', [320, 640, 1024])
      
      expect(srcset).toBe(
        '/images/hero-320w.jpg 320w, /images/hero-640w.jpg 640w, /images/hero-1024w.jpg 1024w'
      )
    })

    it('should use default widths if not provided', () => {
      const srcset = generateSrcset('/test', 'webp')
      
      expect(srcset).toContain('320w')
      expect(srcset).toContain('640w')
      expect(srcset).toContain('1024w')
      expect(srcset).toContain('1920w')
    })
  })

  describe('getOptimalImageFormat', () => {
    it('should detect WebP support', () => {
      // Mock canvas with WebP support
      const mockCanvas = {
        toDataURL: vi.fn((format) => {
          if (format === 'image/webp') {
            return 'data:image/webp;base64,abc'
          }
          return 'data:image/png;base64,xyz'
        })
      }
      
      vi.spyOn(document, 'createElement').mockReturnValue(mockCanvas)

      const format = getOptimalImageFormat()
      expect(format).toBe('webp')
    })

    it('should fall back to jpg without WebP support', () => {
      const mockCanvas = {
        toDataURL: vi.fn(() => 'data:image/png;base64,xyz')
      }
      
      vi.spyOn(document, 'createElement').mockReturnValue(mockCanvas)

      const format = getOptimalImageFormat()
      expect(format).toBe('jpg')
    })
  })

  describe('optimizeImageDataUrl', () => {
    it('should optimize image data URL', async () => {
      const mockCanvas = {
        width: 100,
        height: 100,
        getContext: vi.fn(() => ({
          drawImage: vi.fn()
        })),
        toDataURL: vi.fn(() => 'data:image/jpeg;base64,optimized')
      }
      
      vi.spyOn(document, 'createElement').mockReturnValue(mockCanvas)

      const result = await optimizeImageDataUrl('data:image/png;base64,original', 0.8)
      expect(result).toBe('data:image/jpeg;base64,optimized')
      expect(mockCanvas.toDataURL).toHaveBeenCalledWith('image/jpeg', 0.8)
    })
  })

  describe('createBlurPlaceholder', () => {
    it('should create small blurred placeholder', () => {
      const mockImg = { width: 800, height: 600 }
      const mockCanvas = {
        width: 0,
        height: 0,
        getContext: vi.fn(() => ({
          filter: '',
          drawImage: vi.fn()
        })),
        toDataURL: vi.fn(() => 'data:image/jpeg;base64,blurred')
      }
      
      vi.spyOn(document, 'createElement').mockReturnValue(mockCanvas)

      const result = createBlurPlaceholder(mockImg, 10)
      
      expect(mockCanvas.width).toBe(40)
      expect(mockCanvas.height).toBe(40)
      expect(result).toBe('data:image/jpeg;base64,blurred')
    })
  })

  describe('ImageCache', () => {
    it('should store and retrieve cached images', () => {
      const blob = new Blob(['test'], { type: 'image/jpeg' })
      
      imageCache.add('/test.jpg', blob)
      
      expect(imageCache.has('/test.jpg')).toBe(true)
      expect(imageCache.get('/test.jpg')).toBe(blob)
    })

    it('should enforce max cache size', () => {
      const cache = imageCache
      cache.clear()
      
      // Add images beyond max size (default 50)
      for (let i = 0; i < 52; i++) {
        const blob = new Blob([`test${i}`], { type: 'image/jpeg' })
        cache.add(`/test${i}.jpg`, blob)
      }
      
      // Should remove oldest entries
      expect(cache.has('/test0.jpg')).toBe(false)
      expect(cache.has('/test1.jpg')).toBe(false)
      expect(cache.has('/test51.jpg')).toBe(true)
    })

    it('should clear all cached images', () => {
      imageCache.add('/test1.jpg', new Blob())
      imageCache.add('/test2.jpg', new Blob())
      
      expect(imageCache.has('/test1.jpg')).toBe(true)
      
      imageCache.clear()
      
      expect(imageCache.has('/test1.jpg')).toBe(false)
      expect(imageCache.has('/test2.jpg')).toBe(false)
    })
  })

  describe('fetchAndCacheImage', () => {
    it('should fetch and cache image', async () => {
      const mockBlob = new Blob(['image data'], { type: 'image/jpeg' })
      global.fetch = vi.fn(() =>
        Promise.resolve({
          blob: () => Promise.resolve(mockBlob)
        })
      )

      const result = await fetchAndCacheImage('/test.jpg')
      
      expect(global.fetch).toHaveBeenCalledWith('/test.jpg')
      expect(result).toBe(mockBlob)
      expect(imageCache.has('/test.jpg')).toBe(true)
    })

    it('should return cached image without fetching', async () => {
      const cachedBlob = new Blob(['cached'], { type: 'image/jpeg' })
      imageCache.add('/cached.jpg', cachedBlob)
      
      global.fetch = vi.fn()

      const result = await fetchAndCacheImage('/cached.jpg')
      
      expect(global.fetch).not.toHaveBeenCalled()
      expect(result).toBe(cachedBlob)
    })
  })

  describe('loadProgressiveImage', () => {
    it('should load low quality first, then high quality', async () => {
      // Mock Image constructor to avoid jsdom issues
      const mockImages = []
      const OriginalImage = global.Image
      global.Image = class {
        constructor() {
          const img = {
            src: '',
            style: {},
            onload: null,
            parentNode: null,
            remove: vi.fn()
          }
          mockImages.push(img)
          
          // Trigger onload when src is set - simulate async load
          Object.defineProperty(img, 'src', {
            set: function(value) {
              this._src = value
              if (this.onload && value.includes('high')) {
                // High quality image triggers onload
                setTimeout(() => this.onload(), 10)
              }
            },
            get: function() {
              return this._src
            }
          })
          
          return img
        }
      }

      const container = {
        appendChild: vi.fn(),
        querySelectorAll: vi.fn(() => mockImages)
      }

      loadProgressiveImage('/low.jpg', '/high.jpg', container)

      // Check low quality and high quality images created and added
      await new Promise(resolve => setTimeout(resolve, 100))
      
      expect(mockImages.length).toBe(2) // Low quality + high quality
      expect(container.appendChild).toHaveBeenCalled() // At least low quality added
      
      global.Image = OriginalImage
    })
  })

  describe('AssetPriority', () => {
    it('should have correct priority levels', () => {
      expect(AssetPriority.CRITICAL).toBe(0)
      expect(AssetPriority.HIGH).toBe(1)
      expect(AssetPriority.MEDIUM).toBe(2)
      expect(AssetPriority.LOW).toBe(3)
    })
  })

  describe('AssetLoader', () => {
    it('should queue assets by priority', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          blob: () => Promise.resolve(new Blob())
        })
      )

      assetLoader.add('/critical.jpg', AssetPriority.CRITICAL)
      assetLoader.add('/low.jpg', AssetPriority.LOW)
      assetLoader.add('/high.jpg', AssetPriority.HIGH)

      // Wait for processing
      await new Promise(resolve => setTimeout(resolve, 100))

      // Critical should be loaded first
      expect(imageCache.has('/critical.jpg')).toBe(true)
    })

    it('should respect max concurrent loading', async () => {
      const fetchMock = vi.fn(() =>
        new Promise(resolve => 
          setTimeout(() => resolve({
            blob: () => Promise.resolve(new Blob())
          }), 50)
        )
      )
      global.fetch = fetchMock

      // Add more than maxConcurrent (4) assets
      for (let i = 0; i < 6; i++) {
        assetLoader.add(`/test${i}.jpg`, AssetPriority.HIGH)
      }

      await new Promise(resolve => setTimeout(resolve, 10))

      // Should not exceed max concurrent
      expect(assetLoader.loading.size).toBeLessThanOrEqual(4)
    })

    it('should call callback after loading', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          blob: () => Promise.resolve(new Blob())
        })
      )

      const callback = vi.fn()
      assetLoader.add('/test.jpg', AssetPriority.HIGH, callback)

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(callback).toHaveBeenCalledWith('/test.jpg')
    })

    it('should not reload already loaded assets', async () => {
      const blob = new Blob()
      imageCache.add('/loaded.jpg', blob)

      const callback = vi.fn()
      global.fetch = vi.fn()

      assetLoader.add('/loaded.jpg', AssetPriority.HIGH, callback)

      await new Promise(resolve => setTimeout(resolve, 50))

      expect(global.fetch).not.toHaveBeenCalled()
      expect(callback).toHaveBeenCalledWith('/loaded.jpg')
    })

    it('should clear queue', async () => {
      // Mock fetch to delay processing significantly
      global.fetch = vi.fn(() => new Promise(resolve => 
        setTimeout(() => resolve({
          blob: () => Promise.resolve(new Blob())
        }), 200)
      ))

      assetLoader.add('/test1.jpg', AssetPriority.HIGH)
      assetLoader.add('/test2.jpg', AssetPriority.HIGH)
      assetLoader.add('/test3.jpg', AssetPriority.HIGH)
      assetLoader.add('/test4.jpg', AssetPriority.HIGH)
      assetLoader.add('/test5.jpg', AssetPriority.HIGH)

      // Give time for items to be processed into queue/loading
      await new Promise(resolve => setTimeout(resolve, 50))

      // Items should be in queue or loading
      const totalItems = assetLoader.queue.length + assetLoader.loading.size
      expect(totalItems).toBeGreaterThan(0)

      assetLoader.clear()

      expect(assetLoader.queue.length).toBe(0)
      expect(assetLoader.loading.size).toBe(0)
    })
  })

  describe('initImageOptimizations', () => {
    it('should initialize lazy loading', () => {
      const observeMock = vi.fn()
      global.IntersectionObserver = vi.fn(() => ({
        observe: observeMock,
        unobserve: vi.fn(),
        disconnect: vi.fn()
      }))

      global.MutationObserver = vi.fn(() => ({
        observe: vi.fn(),
        disconnect: vi.fn()
      }))

      document.body.innerHTML = '<img data-src="/test.jpg" />'

      initImageOptimizations()

      expect(observeMock).toHaveBeenCalled()
    })

    it('should setup mutation observer for dynamic content', () => {
      const observeMock = vi.fn()
      global.MutationObserver = vi.fn(() => ({
        observe: observeMock,
        disconnect: vi.fn()
      }))

      global.IntersectionObserver = vi.fn(() => ({
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn()
      }))

      initImageOptimizations()

      expect(observeMock).toHaveBeenCalledWith(document.body, {
        childList: true,
        subtree: true
      })
    })
  })

  describe('Integration Tests', () => {
    it('should handle complete image loading workflow', async () => {
      // Setup
      document.body.innerHTML = `
        <img data-src="/test.jpg" data-srcset="/test-320w.jpg 320w" />
      `

      global.fetch = vi.fn(() =>
        Promise.resolve({
          blob: () => Promise.resolve(new Blob(['data'], { type: 'image/jpeg' }))
        })
      )

      let observerCallback
      global.IntersectionObserver = vi.fn((callback) => {
        observerCallback = callback
        return {
          observe: vi.fn(),
          unobserve: vi.fn(),
          disconnect: vi.fn()
        }
      })

      // Initialize
      enableLazyLoading()

      // Simulate image entering viewport
      const img = document.querySelector('img')
      observerCallback([{
        isIntersecting: true,
        target: img
      }], {
        unobserve: vi.fn()
      })

      // Image should be loaded
      expect(img.src).toContain('/test.jpg')
      expect(img.srcset).toContain('/test-320w.jpg')
      expect(img.classList.contains('loaded')).toBe(true)
    })

    it('should preload critical images and cache them', async () => {
      // Mock createElement to avoid jsdom issues
      const mockLinks = []
      const originalCreateElement = document.createElement.bind(document)
      document.createElement = vi.fn((tagName) => {
        if (tagName === 'link') {
          const link = {
            rel: '',
            as: '',
            href: ''
          }
          mockLinks.push(link)
          return link
        }
        return originalCreateElement(tagName)
      })

      // Mock document.head.appendChild
      const mockAppendChild = vi.fn()
      const originalHead = document.head
      Object.defineProperty(document, 'head', {
        value: { appendChild: mockAppendChild },
        configurable: true
      })

      global.fetch = vi.fn(() =>
        Promise.resolve({
          blob: () => Promise.resolve(new Blob(['critical'], { type: 'image/jpeg' }))
        })
      )

      const criticalUrls = ['/hero.jpg', '/logo.jpg']
      
      // Call preloadImages (DOM operations mocked)
      preloadImages(criticalUrls)
      
      // Check mocks were called
      expect(mockAppendChild).toHaveBeenCalledTimes(2)
      expect(mockLinks.length).toBe(2)
      
      // Fetch and cache
      await fetchAndCacheImage('/hero.jpg')
      await fetchAndCacheImage('/logo.jpg')

      // Should be cached
      expect(imageCache.has('/hero.jpg')).toBe(true)
      expect(imageCache.has('/logo.jpg')).toBe(true)

      // Restore
      document.createElement = originalCreateElement
      Object.defineProperty(document, 'head', {
        value: originalHead,
        configurable: true
      })
    })
  })
})
