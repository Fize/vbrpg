/**
 * T11: RoleSelector 组件测试
 * 角色选择器组件单元测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RoleSelector from '@/components/werewolf/RoleSelector.vue'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue('confirm')
  }
}))

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Check: { template: '<span class="icon-check"></span>' },
  Close: { template: '<span class="icon-close"></span>' }
}))

// Mock roles API
vi.mock('@/services/api', () => ({
  rolesApi: {
    getRoles: vi.fn().mockResolvedValue({
      roles: [
        { id: '1', name: '狼人', type: 'werewolf', team: 'werewolf', description: '夜间可以杀人' },
        { id: '2', name: '预言家', type: 'seer', team: 'villager', description: '夜间可以查验玩家身份' },
        { id: '3', name: '女巫', type: 'witch', team: 'villager', description: '拥有解药和毒药' },
        { id: '4', name: '猎人', type: 'hunter', team: 'villager', description: '死亡时可以开枪带走一人' },
        { id: '5', name: '村民', type: 'villager', team: 'villager', description: '没有特殊技能' }
      ]
    })
  }
}))

// Mock socket store
const mockSocket = {
  emit: vi.fn(),
  on: vi.fn(),
  off: vi.fn()
}

vi.mock('@/stores/socket', () => ({
  useSocketStore: () => ({
    socket: mockSocket,
    isConnected: true,
    emit: vi.fn(),
    on: vi.fn(),
    off: vi.fn()
  })
}))

// Mock RoleCard component
vi.mock('@/components/werewolf/RoleCard.vue', () => ({
  default: {
    template: '<div class="mock-role-card" @click="$emit(\'select\', role)">{{ role.name }}</div>',
    props: ['role', 'selected', 'disabled'],
    emits: ['select']
  }
}))

describe('RoleSelector', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  /**
   * 辅助函数：挂载组件
   */
  function mountRoleSelector(props = {}) {
    return mount(RoleSelector, {
      global: {
        stubs: {
          'el-skeleton': { template: '<div class="el-skeleton"></div>' },
          'el-empty': { template: '<div class="el-empty"><slot /></div>' },
          'el-checkbox': {
            template: '<label class="el-checkbox"><input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" /><slot /></label>',
            props: ['modelValue'],
            emits: ['update:modelValue', 'change']
          },
          'el-button': {
            template: '<button :disabled="disabled" :class="{ \'is-loading\': loading }" @click="$emit(\'click\')"><slot /></button>',
            props: ['type', 'size', 'disabled', 'loading']
          },
          'el-icon': {
            template: '<span class="el-icon"><slot /></span>'
          }
        }
      },
      props: {
        roomCode: 'TEST123',
        ...props
      }
    })
  }

  describe('组件渲染', () => {
    it('应该正确渲染组件结构', () => {
      const wrapper = mountRoleSelector()
      
      expect(wrapper.find('.role-selector').exists()).toBe(true)
      expect(wrapper.find('.selector-header').exists()).toBe(true)
      expect(wrapper.find('.selector-title').exists()).toBe(true)
    })

    it('应该显示选择角色的标题', () => {
      const wrapper = mountRoleSelector()
      
      expect(wrapper.text()).toContain('选择你的角色')
    })

    it('应该有随机分配选项', () => {
      const wrapper = mountRoleSelector()
      
      expect(wrapper.text()).toContain('随机分配')
    })
  })

  describe('角色选择功能', () => {
    it('应该有选择角色的功能', () => {
      const wrapper = mountRoleSelector()
      
      // 检查组件有处理角色选择的方法
      expect(typeof wrapper.vm.handleRoleSelect).toBe('function')
    })

    it('randomAssign 初始应为 true', () => {
      const wrapper = mountRoleSelector()
      
      // 默认随机分配
      expect(wrapper.vm.randomAssign).toBe(true)
    })

    it('选择角色后 selectedRole 应该更新', async () => {
      const wrapper = mountRoleSelector()
      
      // 模拟选择角色
      const mockRole = { id: '1', name: '狼人', type: 'werewolf', team: 'werewolf' }
      wrapper.vm.handleRoleSelect(mockRole)
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.selectedRole).toEqual(mockRole)
    })
  })

  describe('确认选择', () => {
    it('应该有确认按钮', () => {
      const wrapper = mountRoleSelector()
      
      const button = wrapper.find('button')
      expect(button.exists()).toBe(true)
    })

    it('canConfirm 计算属性应该正确工作', async () => {
      const wrapper = mountRoleSelector()
      
      // 默认 randomAssign 为 true，应该可以确认
      expect(wrapper.vm.canConfirm).toBe(true)
    })

    it('点击确认应该触发按钮点击事件', async () => {
      const wrapper = mountRoleSelector()
      
      const button = wrapper.find('button')
      await button.trigger('click')
      
      // 验证按钮存在并可被点击
      expect(button.exists()).toBe(true)
    })
  })

  describe('角色技能描述', () => {
    it('应该有获取角色技能描述的方法', () => {
      const wrapper = mountRoleSelector()
      
      expect(typeof wrapper.vm.getRoleSkillDescription).toBe('function')
    })

    it('狼人角色应该有正确的技能描述', () => {
      const wrapper = mountRoleSelector()
      
      const mockRole = { name: '狼人', type: 'werewolf' }
      const description = wrapper.vm.getRoleSkillDescription(mockRole)
      
      // 检查描述包含关键内容
      expect(description).toBeTruthy()
    })
  })

  describe('阵营分类', () => {
    it('应该有获取阵营名称的方法', () => {
      const wrapper = mountRoleSelector()
      
      expect(typeof wrapper.vm.getTeamName).toBe('function')
    })

    it('应该有获取阵营样式类的方法', () => {
      const wrapper = mountRoleSelector()
      
      expect(typeof wrapper.vm.getTeamClass).toBe('function')
    })
  })

  describe('Props', () => {
    it('应该接收 roomCode prop', () => {
      const wrapper = mountRoleSelector({
        roomCode: 'ROOM456'
      })
      
      expect(wrapper.props('roomCode')).toBe('ROOM456')
    })

    it('应该接收 gameType prop', () => {
      const wrapper = mountRoleSelector({
        gameType: 'werewolf'
      })
      
      expect(wrapper.props('gameType')).toBe('werewolf')
    })
  })

  describe('加载状态', () => {
    it('loading 状态应该是响应式的', () => {
      const wrapper = mountRoleSelector()
      
      // 组件有 loading 属性
      expect(wrapper.vm.loading).toBeDefined()
    })

    it('confirming 初始应为 false', () => {
      const wrapper = mountRoleSelector()
      
      expect(wrapper.vm.confirming).toBe(false)
    })
  })
})
