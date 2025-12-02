const PHASE_CATEGORY_MAP = {
  waiting: 'waiting',
  night: 'night',
  night_werewolf: 'night',
  night_seer: 'night',
  night_witch: 'night',
  night_hunter: 'night',
  day: 'day',
  day_announcement: 'day',
  day_discussion: 'discussion',
  day_vote: 'vote',
  discussion: 'discussion',
  vote: 'vote',
  last_words: 'discussion',
  hunter_shoot: 'discussion',
  game_over: 'result',
  ended: 'result',
  result: 'result'
}

const PHASE_DISPLAY_MAP = {
  waiting: '等待开始',
  night: '夜晚',
  day: '白天',
  discussion: '讨论',
  vote: '投票',
  result: '结算',
  night_werewolf: '夜晚·狼人行动',
  night_seer: '夜晚·预言家查验',
  night_witch: '夜晚·女巫行动',
  night_hunter: '夜晚·猎人技能',
  day_announcement: '白天·公告',
  day_discussion: '白天·讨论',
  day_vote: '白天·投票',
  last_words: '遗言阶段',
  hunter_shoot: '猎人发动技能',
  game_over: '游戏结束',
  ended: '游戏结束'
}

const NIGHT_PHASE_TO_SUBPHASE = {
  night_werewolf: 'werewolf',
  night_seer: 'seer',
  night_witch: 'witch',
  night_hunter: 'hunter',
  hunter_shoot: 'hunter'
}

const NIGHT_SUBPHASE_LABELS = {
  werewolf: '狼人行动',
  seer: '预言家查验',
  witch: '女巫行动',
  hunter: '猎人技能'
}

export function getPhaseCategory(phase) {
  if (!phase) return null
  if (PHASE_CATEGORY_MAP[phase]) {
    return PHASE_CATEGORY_MAP[phase]
  }
  if (phase.startsWith('night')) {
    return 'night'
  }
  if (phase.startsWith('day')) {
    return 'day'
  }
  return phase
}

export function getPhaseDisplayName(phase, subPhase) {
  if (!phase) return ''
  if (PHASE_DISPLAY_MAP[phase]) {
    return PHASE_DISPLAY_MAP[phase]
  }
  const category = getPhaseCategory(phase)
  if (category === 'night' && subPhase) {
    const label = NIGHT_SUBPHASE_LABELS[subPhase]
    if (label) {
      return `夜晚·${label}`
    }
  }
  return PHASE_DISPLAY_MAP[category] || phase
}

export function resolveNightSubPhase(phase, providedSubPhase) {
  if (providedSubPhase !== undefined) {
    return providedSubPhase
  }
  if (!phase) return null
  return NIGHT_PHASE_TO_SUBPHASE[phase] || null
}

export function getNightSubPhaseLabel(subPhase) {
  if (!subPhase) return ''
  return NIGHT_SUBPHASE_LABELS[subPhase] || ''
}
