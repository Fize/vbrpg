/**
 * Phase 3 投票交互前端单元测试
 * 
 * 测试覆盖:
 * - T28: VotePanel 人类玩家投票支持
 * - T28: Game Store 投票状态
 * - T28: Socket Store 投票方法
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import VotePanel from '@/components/werewolf/VotePanel.vue'
import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  CircleCheck: { template: '<span></span>' },
  Check: { template: '<span></span>' },
  Clock: { template: '<span></span>' }
}))

describe('Phase 3 前端: VotePanel 人类玩家投票', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('基础渲染', () => {
    it('应该正确渲染投票面板', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1, vote_count: 0 },
            { id: 'p2', name: '玩家2', seat_number: 2, vote_count: 0 }
          ]
        }
      })
      
      expect(wrapper.find('.vote-panel').exists()).toBe(true)
      expect(wrapper.find('.panel-title').text()).toContain('投票')
    })

    it('当没有候选人时应该显示空列表', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: []
        }
      })
      
      expect(wrapper.findAll('.candidate-item').length).toBe(0)
    })

    it('应该渲染所有候选人', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1 },
            { id: 'p2', name: '玩家2', seat_number: 2 },
            { id: 'p3', name: '玩家3', seat_number: 3 }
          ]
        }
      })
      
      expect(wrapper.findAll('.candidate-item').length).toBe(3)
    })
  })

  describe('投票选择', () => {
    it('点击候选人应该选中', async () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1 },
            { id: 'p2', name: '玩家2', seat_number: 2 }
          ]
        }
      })
      
      const firstCandidate = wrapper.findAll('.candidate-item')[0]
      await firstCandidate.trigger('click')
      
      expect(firstCandidate.classes()).toContain('selected')
    })

    it('再次点击已选中的候选人应该取消选择', async () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1 }
          ]
        }
      })
      
      const candidate = wrapper.find('.candidate-item')
      await candidate.trigger('click')
      expect(candidate.classes()).toContain('selected')
      
      await candidate.trigger('click')
      expect(candidate.classes()).not.toContain('selected')
    })

    it('当 disabled=true 时不能选择候选人', async () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1 }
          ],
          disabled: true
        }
      })
      
      const candidate = wrapper.find('.candidate-item')
      await candidate.trigger('click')
      
      expect(candidate.classes()).not.toContain('selected')
    })
  })

  describe('投票提交', () => {
    it('点击确认投票应该触发 vote 事件', async () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1 }
          ]
        },
        global: {
          stubs: {
            'el-button': {
              template: '<button @click="$emit(\'click\')" :disabled="disabled"><slot/></button>',
              props: ['disabled', 'type', 'size']
            },
            'el-icon': { template: '<span><slot/></span>' }
          }
        }
      })
      
      // 先选中候选人
      await wrapper.find('.candidate-item').trigger('click')
      
      // 点击确认投票 - 第二个按钮
      const buttons = wrapper.findAll('button')
      const voteButton = buttons[1]  // 确认投票按钮
      await voteButton.trigger('click')
      
      expect(wrapper.emitted('vote')).toBeTruthy()
    })

    it('未选中候选人时确认按钮应该禁用', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1 }
          ]
        },
        global: {
          stubs: {
            'el-button': {
              template: '<button @click="$emit(\'click\')" :disabled="disabled"><slot/></button>',
              props: ['disabled', 'type', 'size']
            },
            'el-icon': { template: '<span><slot/></span>' }
          }
        }
      })
      
      // 确认投票按钮（第二个）
      const buttons = wrapper.findAll('button')
      const voteButton = buttons[1]
      expect(voteButton.attributes('disabled')).toBeDefined()
    })
  })

  describe('弃票功能', () => {
    it('点击弃票应该触发 abstain 事件', async () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1 }
          ]
        },
        global: {
          stubs: {
            'el-button': {
              template: '<button @click="$emit(\'click\')" :disabled="disabled"><slot/></button>',
              props: ['disabled', 'type', 'size']
            },
            'el-icon': { template: '<span><slot/></span>' }
          }
        }
      })
      
      // 弃票按钮（第一个）
      const buttons = wrapper.findAll('button')
      const abstainButton = buttons[0]
      await abstainButton.trigger('click')
      
      expect(wrapper.emitted('abstain')).toBeTruthy()
    })

    it('当 disabled=true 时弃票按钮应该禁用', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [],
          disabled: true
        },
        global: {
          stubs: {
            'el-button': {
              template: '<button @click="$emit(\'click\')" :disabled="disabled"><slot/></button>',
              props: ['disabled', 'type', 'size']
            },
            'el-icon': { template: '<span><slot/></span>' }
          }
        }
      })
      
      const buttons = wrapper.findAll('button')
      const abstainButton = buttons[0]
      expect(abstainButton.attributes('disabled')).toBeDefined()
    })
  })

  describe('已投票状态', () => {
    it('当 hasVoted=true 时应该显示已投票状态', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [
            { id: 'p1', name: '玩家1', seat_number: 1 }
          ],
          hasVoted: true,
          myVote: 'p1'
        }
      })
      
      expect(wrapper.find('.voted-status').exists()).toBe(true)
      expect(wrapper.text()).toContain('已投票')
    })

    it('弃票后应该显示已弃票', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [],
          hasVoted: true,
          myVote: null
        }
      })
      
      expect(wrapper.text()).toContain('弃票')
    })
  })

  describe('倒计时显示', () => {
    it('当 countdown > 0 时应该显示倒计时', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [],
          countdown: 30
        }
      })
      
      expect(wrapper.find('.countdown').exists()).toBe(true)
      expect(wrapper.text()).toContain('30')
    })

    it('当 countdown <= 10 时应该显示紧急样式', () => {
      const wrapper = mount(VotePanel, {
        props: {
          candidates: [],
          countdown: 5
        }
      })
      
      expect(wrapper.find('.is-urgent').exists()).toBe(true)
    })
  })
})

describe('Phase 3 前端: Game Store 投票状态', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('应该初始化空的 voteOptions', () => {
    const gameStore = useGameStore()
    expect(gameStore.voteOptions).toEqual([])
  })

  it('应该初始化 voteTimeout 为 0', () => {
    const gameStore = useGameStore()
    expect(gameStore.voteTimeout).toBe(0)
  })

  it('setVoteOptions 应该更新投票选项', () => {
    const gameStore = useGameStore()
    const options = [
      { seat_number: 1, player_name: '玩家1' },
      { seat_number: 2, player_name: '玩家2' }
    ]
    
    gameStore.setVoteOptions(options)
    
    expect(gameStore.voteOptions).toEqual(options)
  })

  it('setVoteTimeout 应该更新超时时间', () => {
    const gameStore = useGameStore()
    
    gameStore.setVoteTimeout(60)
    
    expect(gameStore.voteTimeout).toBe(60)
  })

  it('clearVoteState 应该清除所有投票状态', () => {
    const gameStore = useGameStore()
    
    // 先设置一些状态
    gameStore.setVoteOptions([{ seat_number: 1 }])
    gameStore.setVoteTimeout(60)
    gameStore.setVote('player1')
    
    // 清除
    gameStore.clearVoteState()
    
    expect(gameStore.voteOptions).toEqual([])
    expect(gameStore.voteTimeout).toBe(0)
    expect(gameStore.hasVoted).toBe(false)
    expect(gameStore.myVote).toBe(null)
  })
})

describe('Phase 3 前端: Socket Store 投票方法', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('应该有 submitHumanVote 方法', () => {
    const socketStore = useSocketStore()
    expect(typeof socketStore.submitHumanVote).toBe('function')
  })

  it('submitHumanVote 未连接时应抛出错误', () => {
    const socketStore = useSocketStore()
    
    expect(() => {
      socketStore.submitHumanVote('ROOM123', 'game123', 1)
    }).toThrow('WebSocket 未连接')
  })
})
