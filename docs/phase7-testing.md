# Phase 7 测试文档

## 概述

为Phase 7的所有新增功能补充了完整的单元测试，包括动画图标组件、图片优化工具和资源配置。

## 测试文件结构

```
frontend/tests/
├── setup.js                              # 全局测试配置
├── unit/
│   ├── icons/
│   │   ├── AnimatedIcons.spec.js        # 动画图标组件测试
│   │   └── IconIntegration.spec.js      # 图标库集成测试
│   ├── utils/
│   │   └── imageOptimization.spec.js    # 图片优化工具测试
│   └── config/
│       └── assetConfig.spec.js          # 资源配置测试
└── e2e/                                  # E2E测试（已存在）
```

## 测试覆盖

### 1. 动画图标组件测试 (`AnimatedIcons.spec.js`)

**测试范围**：
- ✅ 所有6个图标组件（Detective, Dice, Thinking, Trophy, Clue, Location）
- ✅ Props验证（size, color, animate, className等）
- ✅ 动画逻辑（requestAnimationFrame, 状态更新）
- ✅ 生命周期钩子（mount, unmount, cleanup）
- ✅ SVG结构和viewBox
- ✅ 通用行为测试

**测试用例统计**：
- DetectiveIcon: 8个测试
- DiceIcon: 7个测试
- ThinkingIcon: 5个测试
- TrophyIcon: 5个测试
- ClueIcon: 5个测试
- LocationIcon: 4个测试
- 通用测试: 30个测试（6个图标 × 5个通用用例）
- **总计**: ~70个测试用例

**关键测试**：
```javascript
// Props测试
it('accepts custom size prop')
it('accepts custom color prop')
it('accepts custom className prop')

// 动画测试
it('starts animation when animate prop is true')
it('does not animate when animate prop is false')
it('updates transform during animation')

// 清理测试
it('cleans up animation on unmount')
```

### 2. 图片优化工具测试 (`imageOptimization.spec.js`)

**测试范围**：
- ✅ 懒加载功能（Intersection Observer）
- ✅ 图片预加载
- ✅ srcset生成
- ✅ 格式检测（WebP/AVIF支持）
- ✅ 图片缓存（ImageCache class）
- ✅ 渐进式加载
- ✅ 优先级队列（AssetLoader）
- ✅ 初始化函数

**测试用例统计**：
- enableLazyLoading: 3个测试
- preloadImages: 1个测试
- generateSrcset: 2个测试
- getOptimalImageFormat: 2个测试
- optimizeImageDataUrl: 1个测试
- createBlurPlaceholder: 1个测试
- ImageCache: 3个测试
- fetchAndCacheImage: 2个测试
- loadProgressiveImage: 1个测试
- AssetLoader: 5个测试
- initImageOptimizations: 2个测试
- 集成测试: 2个测试
- **总计**: ~25个测试用例

**关键测试**：
```javascript
// 懒加载测试
it('should observe images with data-src attribute')
it('should fall back to immediate loading without IntersectionObserver')

// 缓存测试
it('should store and retrieve cached images')
it('should enforce max cache size')

// 优先级队列测试
it('should queue assets by priority')
it('should respect max concurrent loading')
```

### 3. 资源配置测试 (`assetConfig.spec.js`)

**测试范围**：
- ✅ imageOptimizationConfig配置
- ✅ assetOptimizationPlugin插件
- ✅ preloadAssets配置
- ✅ generatePreloadLinks函数
- ✅ svgOptimizationConfig配置
- ✅ bundleAnalyzerConfig配置
- ✅ Vite插件集成

**测试用例统计**：
- imageOptimizationConfig: 4个测试
- assetOptimizationPlugin: 7个测试
- preloadAssets: 4个测试
- generatePreloadLinks: 5个测试
- svgOptimizationConfig: 3个测试
- bundleAnalyzerConfig: 5个测试
- 配置集成: 4个测试
- Vite插件集成: 3个测试
- 性能优化: 4个测试
- **总计**: ~40个测试用例

**关键测试**：
```javascript
// 配置测试
it('should have correct supported formats')
it('should have responsive width breakpoints')
it('should have quality settings for each format')

// 插件测试
it('should return a valid Vite plugin')
it('should configure asset file naming')
it('should optimize small assets by inlining')
```

### 4. 图标集成测试 (`IconIntegration.spec.js`)

**测试范围**：
- ✅ 导出验证（所有图标组件）
- ✅ GameIcons常量
- ✅ IconSizes预设
- ✅ IconThemes主题系统
- ✅ getIconComponent辅助函数
- ✅ getIconColor辅助函数
- ✅ 主题切换
- ✅ 错误处理
- ✅ 性能测试

**测试用例统计**：
- 导出测试: 2个测试
- GameIcons: 2个测试
- IconSizes: 3个测试
- IconThemes: 6个测试
- getIconComponent: 4个测试
- getIconColor: 8个测试
- 主题集成: 2个测试
- 使用模式: 3个测试
- 文档和DX: 3个测试
- 无障碍: 3个测试
- 错误处理: 4个测试
- 性能: 2个测试
- 完整覆盖: 3个测试
- **总计**: ~45个测试用例

**关键测试**：
```javascript
// 导出测试
it('should export all icon components')

// 主题测试
it('should have colors for all icons in each theme')
it('should support theme switching')

// 辅助函数测试
it('should return correct component for valid icon name')
it('should use primary theme by default')

// 性能测试
it('should use object lookups for O(1) access')
```

## 运行测试

### 安装依赖

首先确保安装了测试依赖（已在package.json中）：

```bash
cd frontend
npm install
```

需要的测试依赖：
- `vitest`: ^1.2.1
- `@vue/test-utils`: ^2.4.3
- `@vitest/ui`: 可选，用于UI界面
- `@vitest/coverage-v8`: 可选，用于覆盖率报告

### 运行所有测试

```bash
npm run test
```

### 运行特定测试文件

```bash
# 图标组件测试
npm run test tests/unit/icons/AnimatedIcons.spec.js

# 图片优化测试
npm run test tests/unit/utils/imageOptimization.spec.js

# 资源配置测试
npm run test tests/unit/config/assetConfig.spec.js

# 集成测试
npm run test tests/unit/icons/IconIntegration.spec.js
```

### 监听模式

```bash
npm run test -- --watch
```

### 生成覆盖率报告

```bash
npm run test -- --coverage
```

覆盖率报告会生成在 `coverage/` 目录：
- `coverage/index.html` - HTML格式报告
- `coverage/coverage-final.json` - JSON格式数据

### UI模式（可选）

```bash
npm run test -- --ui
```

## 测试配置文件

### `vitest.config.js`

```javascript
export default defineConfig({
  test: {
    globals: true,           // 全局测试API
    environment: 'jsdom',    // DOM环境
    setupFiles: ['./tests/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [/* ... */]
    },
    include: ['tests/unit/**/*.spec.js'],
    exclude: ['node_modules', 'dist', 'tests/e2e']
  }
})
```

### `tests/setup.js`

全局Mock和配置：
- ✅ window.matchMedia
- ✅ IntersectionObserver
- ✅ MutationObserver
- ✅ requestAnimationFrame
- ✅ performance.now
- ✅ HTMLCanvasElement
- ✅ Image
- ✅ fetch

## 更新package.json脚本

在 `frontend/package.json` 中添加测试脚本：

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage"
  }
}
```

## 测试统计总结

| 测试文件 | 测试用例数 | 覆盖功能 |
|---------|-----------|---------|
| AnimatedIcons.spec.js | ~70 | 6个图标组件 |
| imageOptimization.spec.js | ~25 | 图片优化工具 |
| assetConfig.spec.js | ~40 | 资源配置 |
| IconIntegration.spec.js | ~45 | 图标库集成 |
| **总计** | **~180** | **完整Phase 7功能** |

## 预期测试结果

运行 `npm run test` 后，预期输出：

```
✓ tests/unit/icons/AnimatedIcons.spec.js (70 tests)
✓ tests/unit/utils/imageOptimization.spec.js (25 tests)
✓ tests/unit/config/assetConfig.spec.js (40 tests)
✓ tests/unit/icons/IconIntegration.spec.js (45 tests)

Test Files  4 passed (4)
Tests  180 passed (180)
Duration  X.XXs
```

## 覆盖率目标

- **行覆盖率**: > 85%
- **分支覆盖率**: > 80%
- **函数覆盖率**: > 90%
- **语句覆盖率**: > 85%

## CI/CD集成

可以在 `.github/workflows/test.yml` 中添加：

```yaml
- name: Run Frontend Tests
  run: |
    cd frontend
    npm ci
    npm run test -- --coverage
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./frontend/coverage/coverage-final.json
```

## 故障排查

### 常见问题

1. **jsdom环境错误**
   ```bash
   npm install --save-dev jsdom
   ```

2. **@vue/test-utils版本不兼容**
   ```bash
   npm install --save-dev @vue/test-utils@latest
   ```

3. **Mock不生效**
   - 检查 `tests/setup.js` 是否正确加载
   - 确保在 `vitest.config.js` 中配置了 `setupFiles`

4. **动画测试超时**
   - 使用 `vi.useFakeTimers()`
   - 通过 `vi.advanceTimersByTime()` 控制时间

## 后续改进

1. **E2E测试**: 为图标和优化功能添加端到端测试
2. **视觉回归测试**: 使用Percy或Chromatic测试图标渲染
3. **性能基准测试**: 测量动画帧率和加载时间
4. **可访问性测试**: 使用axe-core测试ARIA和键盘导航

## 相关文档

- [Vitest文档](https://vitest.dev/)
- [Vue Test Utils文档](https://test-utils.vuejs.org/)
- [测试最佳实践](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
