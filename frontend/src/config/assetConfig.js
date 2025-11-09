/**
 * Asset Management Plugin for Vite
 * Optimizes images and generates responsive variants
 */

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// Image optimization configuration
export const imageOptimizationConfig = {
  // Supported formats
  formats: ['webp', 'jpg', 'png'],
  
  // Responsive image widths
  responsiveWidths: [320, 640, 768, 1024, 1280, 1920],
  
  // Quality settings
  quality: {
    webp: 80,
    jpg: 85,
    png: 90
  },
  
  // Compression settings
  compression: {
    jpg: {
      quality: 85,
      progressive: true
    },
    png: {
      quality: 90,
      compressionLevel: 9
    },
    webp: {
      quality: 80,
      lossless: false
    }
  }
}

/**
 * Custom Vite plugin for asset optimization
 */
export function assetOptimizationPlugin() {
  return {
    name: 'asset-optimization',
    
    // Transform image imports
    transform(code, id) {
      if (!/\.(jpg|jpeg|png|webp|svg)$/.test(id)) {
        return null
      }
      
      // Add cache headers for production
      if (process.env.NODE_ENV === 'production') {
        return {
          code,
          map: null,
          meta: {
            cacheControl: 'public, max-age=31536000, immutable'
          }
        }
      }
      
      return null
    },
    
    // Configure build options
    config() {
      return {
        build: {
          assetsInlineLimit: 4096, // 4kb - inline small assets
          rollupOptions: {
            output: {
              // Asset file naming
              assetFileNames: (assetInfo) => {
                const info = assetInfo.name.split('.')
                const ext = info[info.length - 1]
                
                if (/png|jpe?g|svg|gif|webp/i.test(ext)) {
                  return `assets/images/[name]-[hash][extname]`
                }
                if (/woff2?|ttf|otf/i.test(ext)) {
                  return `assets/fonts/[name]-[hash][extname]`
                }
                return `assets/[name]-[hash][extname]`
              }
            }
          }
        }
      }
    }
  }
}

/**
 * Asset preloading configuration
 */
export const preloadAssets = {
  // Critical CSS
  styles: [
    '/src/assets/styles/global.css',
    '/src/assets/styles/transitions.css'
  ],
  
  // Critical fonts
  fonts: [
    // Add font paths here when available
  ],
  
  // Critical images
  images: [
    // Logo, hero images, etc.
  ]
}

/**
 * Generate preload links
 */
export function generatePreloadLinks() {
  const links = []
  
  // Preload styles
  preloadAssets.styles.forEach(href => {
    links.push({
      rel: 'preload',
      as: 'style',
      href
    })
  })
  
  // Preload fonts
  preloadAssets.fonts.forEach(href => {
    links.push({
      rel: 'preload',
      as: 'font',
      type: 'font/woff2',
      crossorigin: 'anonymous',
      href
    })
  })
  
  // Preload images
  preloadAssets.images.forEach(href => {
    links.push({
      rel: 'preload',
      as: 'image',
      href
    })
  })
  
  return links
}

/**
 * SVG optimization settings
 */
export const svgOptimizationConfig = {
  plugins: [
    'removeDoctype',
    'removeXMLProcInst',
    'removeComments',
    'removeMetadata',
    'removeEditorsNSData',
    'cleanupAttrs',
    'mergeStyles',
    'inlineStyles',
    'minifyStyles',
    'cleanupIDs',
    'removeUselessDefs',
    'cleanupNumericValues',
    'convertColors',
    'removeUnknownsAndDefaults',
    'removeNonInheritableGroupAttrs',
    'removeUselessStrokeAndFill',
    'removeViewBox',
    'cleanupEnableBackground',
    'removeHiddenElems',
    'removeEmptyText',
    'convertShapeToPath',
    'moveElemsAttrsToGroup',
    'moveGroupAttrsToElems',
    'collapseGroups',
    'convertPathData',
    'convertTransform',
    'removeEmptyAttrs',
    'removeEmptyContainers',
    'mergePaths',
    'removeUnusedNS',
    'sortAttrs',
    'removeTitle',
    'removeDesc'
  ]
}

/**
 * Asset bundle analyzer configuration
 */
export const bundleAnalyzerConfig = {
  enabled: process.env.ANALYZE === 'true',
  openAnalyzer: true,
  analyzerMode: 'static',
  reportFilename: 'bundle-report.html'
}
