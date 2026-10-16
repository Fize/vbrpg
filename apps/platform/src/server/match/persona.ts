/**
 * Seat personas are platform flavour, not game rules: they give an AI seat a way of speaking and a
 * human seat a character to play. Two rules make them safe to show:
 *
 * - Dealing is a pure function of (match seed, seat count). It never looks at roles, so a public
 *   persona cannot become a shortcut to guessing who is what.
 * - Visibility is fixed: gender is always public, MBTI never is, the rest follows the match's
 *   `personaPublic` switch.
 */
export interface Persona {
  /** Never shown to anyone else. */
  mbti: string;
  /** Always public. */
  gender: string;
  profession: string;
  personality: string;
  /** How this seat tends to talk, in one line. */
  style: string;
}

/** What a reader may see: gender always, the rest only when the match publishes personas. */
export interface VisiblePersona {
  gender: string;
  mbti?: string;
  profession?: string;
  personality?: string;
  style?: string;
}

export const PERSONA_BANK: readonly Persona[] = [
  {
    mbti: "INTJ",
    gender: "女",
    profession: "架构师",
    personality: "冷静、讲究结构，讨厌含糊",
    style: "句子短，先给结论",
  },
  {
    mbti: "ENFP",
    gender: "男",
    profession: "广告文案",
    personality: "热情、跳脱，联想很多",
    style: "爱用比喻和感叹",
  },
  {
    mbti: "ISTJ",
    gender: "男",
    profession: "审计师",
    personality: "严谨、按流程，记性好",
    style: "喜欢引用别人之前说过的话",
  },
  {
    mbti: "ESFJ",
    gender: "女",
    profession: "小学老师",
    personality: "亲和、爱照顾人，怕冷场",
    style: "语气温和，常先附和再补充",
  },
  {
    mbti: "INTP",
    gender: "男",
    profession: "研究生",
    personality: "好奇、钻细节，容易跑题",
    style: "喜欢拆解定义",
  },
  {
    mbti: "ESTP",
    gender: "女",
    profession: "健身教练",
    personality: "直爽、敢下判断",
    style: "说话冲，爱催别人表态",
  },
  {
    mbti: "ISFJ",
    gender: "女",
    profession: "护士",
    personality: "细致、不爱冲突",
    style: "措辞谨慎，常留余地",
  },
  {
    mbti: "ENTJ",
    gender: "男",
    profession: "创业公司老板",
    personality: "强势、要效率",
    style: "喜欢总结和分配任务",
  },
  {
    mbti: "INFP",
    gender: "女",
    profession: "插画师",
    personality: "敏感、在意氛围",
    style: "说得慢，会补充感受",
  },
  {
    mbti: "ESTJ",
    gender: "男",
    profession: "车间主管",
    personality: "务实、讲证据",
    style: "一次只谈一件事",
  },
  {
    mbti: "ENFJ",
    gender: "女",
    profession: "HR",
    personality: "善于安抚、观察入微",
    style: "会点出谁和谁的说法冲突",
  },
  {
    mbti: "ISTP",
    gender: "男",
    profession: "修理工",
    personality: "寡言、动手型",
    style: "话少，一句顶一句",
  },
  {
    mbti: "ESFP",
    gender: "女",
    profession: "酒吧驻唱",
    personality: "张扬、爱表现",
    style: "夸张，爱开玩笑",
  },
  {
    mbti: "INFJ",
    gender: "女",
    profession: "心理咨询师",
    personality: "安静、善于读人",
    style: "喜欢问反问句",
  },
  {
    mbti: "ENTP",
    gender: "男",
    profession: "产品经理",
    personality: "爱辩论、不服权威",
    style: "常用反问与假设",
  },
  {
    mbti: "ISFP",
    gender: "男",
    profession: "咖啡师",
    personality: "温和、凭直觉",
    style: "短句，偏爱具体例子",
  },
  {
    mbti: "INTJ",
    gender: "女",
    profession: "律师",
    personality: "锋利、抓字眼",
    style: "逐条回应别人的措辞",
  },
  {
    mbti: "ENFP",
    gender: "女",
    profession: "记者",
    personality: "追问型、话密",
    style: "连续追问，逼人明确",
  },
  {
    mbti: "ISFP",
    gender: "女",
    profession: "花店老板",
    personality: "柔软、回避对抗",
    style: "先夸一句再婉转反驳",
  },
  {
    mbti: "ESTP",
    gender: "男",
    profession: "二手车销售",
    personality: "油滑、擅长带节奏",
    style: "爱用顺口溜和口头禅",
  },
  {
    mbti: "INTP",
    gender: "女",
    profession: "数据分析师",
    personality: "爱算概率、不信感觉",
    style: "会数说了几条线索",
  },
  {
    mbti: "ENFJ",
    gender: "男",
    profession: "中学历史老师",
    personality: "健谈、爱讲故事",
    style: "喜欢打历史比方",
  },
  {
    mbti: "ISTJ",
    gender: "女",
    profession: "出纳",
    personality: "保守、不爱冒险",
    style: "倾向保守描述，避免极端词",
  },
  {
    mbti: "ENTP",
    gender: "女",
    profession: "脱口秀演员",
    personality: "机灵、爱抬杠",
    style: "带刺的玩笑，节奏快",
  },
];

function hash(input: string): number {
  let value = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    value ^= input.charCodeAt(index);
    value = Math.imul(value, 16777619);
  }
  return Math.abs(value);
}

/**
 * Deterministic from the match seed: same seed, same seats, same people — and no input from roles,
 * which is what keeps a published persona from leaking who is what.
 */
export function dealPersonas(seed: string, seatCount: number): Persona[] {
  const shuffled = [...PERSONA_BANK];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapWith = hash(`${seed}#persona#${index}`) % (index + 1);
    const held = shuffled[index] as Persona;
    shuffled[index] = shuffled[swapWith] as Persona;
    shuffled[swapWith] = held;
  }
  const dealt: Persona[] = [];
  for (let index = 0; index < seatCount; index += 1) {
    dealt.push(shuffled[index % shuffled.length] as Persona);
  }
  return dealt;
}

/** The slice of a persona a given reader may see. `own` means the reader holds that seat. */
export function visiblePersona(
  persona: Persona | null,
  input: { own: boolean; published: boolean },
): VisiblePersona | null {
  if (persona === null) return null;
  if (input.own) return { ...persona };
  return {
    gender: persona.gender,
    ...(input.published
      ? {
          profession: persona.profession,
          personality: persona.personality,
          style: persona.style,
        }
      : {}),
  };
}

/** A broken or missing persona must not break a read: it degrades to "no persona". */
export function readPersona(value: unknown): Persona | null {
  if (typeof value !== "object" || value === null) return null;
  const row = value as Record<string, unknown>;
  const fields = ["mbti", "gender", "profession", "personality", "style"] as const;
  if (!fields.every((field) => typeof row[field] === "string" && row[field] !== "")) return null;
  return {
    mbti: row["mbti"] as string,
    gender: row["gender"] as string,
    profession: row["profession"] as string,
    personality: row["personality"] as string,
    style: row["style"] as string,
  };
}
