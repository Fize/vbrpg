import { seededIndex } from "../game/seeded.js";

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

/**
 * Five independent pools, combined per seat at creation. They are deliberately not a list of
 * ready-made characters: 16 × 2 × 24 × 20 × 20 combinations are why a table of twelve rarely
 * sees the same person twice, and why publishing a persona says little about who is what.
 */
export const MBTI_POOL: readonly string[] = [
  "INTJ",
  "INTP",
  "ENTJ",
  "ENTP",
  "INFJ",
  "INFP",
  "ENFJ",
  "ENFP",
  "ISTJ",
  "ISFJ",
  "ESTJ",
  "ESFJ",
  "ISTP",
  "ISFP",
  "ESTP",
  "ESFP",
];

export const GENDER_POOL: readonly string[] = ["男", "女"];

export const PROFESSION_POOL: readonly string[] = [
  "架构师",
  "广告文案",
  "审计师",
  "小学老师",
  "研究生",
  "健身教练",
  "护士",
  "创业公司老板",
  "插画师",
  "车间主管",
  "HR",
  "修理工",
  "酒吧驻唱",
  "心理咨询师",
  "产品经理",
  "咖啡师",
  "律师",
  "记者",
  "花店老板",
  "二手车销售",
  "数据分析师",
  "中学历史老师",
  "出纳",
  "脱口秀演员",
];

export const PERSONALITY_POOL: readonly string[] = [
  "冷静、讲究结构，讨厌含糊",
  "热情、跳脱，联想很多",
  "严谨、按流程，记性好",
  "亲和、爱照顾人，怕冷场",
  "好奇、钻细节，容易跑题",
  "直爽、敢下判断",
  "细致、不爱冲突",
  "强势、要效率",
  "敏感、在意氛围",
  "务实、讲证据",
  "善于安抚、观察入微",
  "寡言、动手型",
  "张扬、爱表现",
  "安静、善于读人",
  "爱辩论、不服权威",
  "温和、凭直觉",
  "锋利、抓字眼",
  "追根究底、话密",
  "柔软、回避对抗",
  "油滑、擅长带节奏",
];

export const STYLE_POOL: readonly string[] = [
  "句子短，先给结论",
  "爱用比喻和感叹",
  "喜欢引用别人之前说过的话",
  "语气温和，常先附和再补充",
  "喜欢拆解定义",
  "说话冲，爱催别人表态",
  "措辞谨慎，常留余地",
  "喜欢总结和分配任务",
  "说得慢，会补充感受",
  "一次只谈一件事",
  "会点出谁和谁的说法冲突",
  "话少，一句顶一句",
  "夸张，爱开玩笑",
  "喜欢问反问句",
  "常用反问与假设",
  "短句，偏爱具体例子",
  "逐条回应别人的措辞",
  "连续追问，逼人明确",
  "先夸一句再婉转反驳",
  "爱用顺口溜和口头禅",
];

/** One independent pick per dimension, so the same MBTI can arrive with any job or manner. */
function pick(pool: readonly string[], seed: string, dimension: string, seat: number): string {
  return pool[seededIndex(seed, `persona#${dimension}#${seat}`, pool.length)] as string;
}

/**
 * Deterministic from the match seed: same seed, same seats, same people — and no input from roles,
 * which is what keeps a published persona from leaking who is what.
 */
export function dealPersonas(seed: string, seatCount: number): Persona[] {
  const dealt: Persona[] = [];
  for (let seat = 0; seat < seatCount; seat += 1) {
    dealt.push({
      mbti: pick(MBTI_POOL, seed, "mbti", seat),
      gender: pick(GENDER_POOL, seed, "gender", seat),
      profession: pick(PROFESSION_POOL, seed, "profession", seat),
      personality: pick(PERSONALITY_POOL, seed, "personality", seat),
      style: pick(STYLE_POOL, seed, "style", seat),
    });
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
