import { ApiError, apiErrorMessage } from "./api";

/**
 * 面向用户的中文提示。仅做展示层翻译，不改变服务端语义；
 * 未覆盖的错误码保留服务端原文，便于对照 requestId 排查。
 */
const MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "用户名或密码不正确",
  SESSION_INVALID: "登录已过期，请重新登录",
  CURRENT_PASSWORD_INVALID: "当前密码不正确",
  PASSWORD_UNCHANGED: "新密码不能与当前密码相同",
  CSRF_TOKEN_INVALID: "页面已过期，请刷新后重试",
  ORIGIN_REQUIRED: "请求缺少来源信息，请刷新后重试",
  ORIGIN_NOT_ALLOWED: "请求来源不受信任，请刷新后重试",
  INSUFFICIENT_ROLE: "当前账号没有该操作权限",
  RATE_LIMITED: "尝试次数过多，请稍后再试",
  ACCOUNT_MISSING: "账号状态异常，请联系管理员",
  CANNOT_DELETE_SELF: "不能删除当前登录的账号",
  USER_HAS_HISTORY: "该账号出现在对局记录里，请改为停用",
  PROVIDER_HAS_MODELS: "请先删除该供应商下的模型",
  USER_NOT_FOUND: "账号不存在",
  PROVIDER_NOT_FOUND: "供应商不存在",
  MODEL_NOT_FOUND: "模型不存在",
  INVALID_REQUEST: "请求格式不对，请刷新页面后重试",
  IDEMPOTENCY_KEY_REQUIRED: "这次提交缺少去重标识，请重试",
  ADMIN_REQUIRED: "当前账号没有该操作权限",
  MATCH_NOT_FOUND: "对局不存在",
  SEAT_NOT_FOUND: "这个席位不在该对局里",
  NOT_YOUR_SEAT: "该席位属于其他账号",
  SEAT_INACTIVE: "该席位已经不能行动了",
  MATCH_NOT_RUNNING: "这局当前不接受输入",
  MATCH_ENDED: "这局已经结束，不能再改",
  MATCH_NOT_PAUSED: "只有暂停中的对局才能恢复",
  MATCH_STATUS_UNCHANGED: "这局已经是这个状态了",
  UNKNOWN_GAME: "没有找到这个游戏",
  MATCH_NOT_FOUND_OR_UNKNOWN: "对局或游戏不存在",
  ENGINE_ERROR: "游戏规则拒绝了这一步",
  MODEL_CALL_FAILED: "模型调用失败",
  MODEL_TIMEOUT: "模型响应超时",
  MODEL_UNREACHABLE: "连不上模型服务",
  MODEL_BAD_RESPONSE: "模型返回的内容无法解析",
};

/**
 * Chinese first: a code the console knows reads as its own sentence, anything else reads as a
 * plain failure. The backend's own wording is English by design (logs, operators), so it is kept
 * out of the interface; the code and the request id are what a support case needs.
 */
export function uiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return MESSAGES[error.code] ?? `操作没有成功（${error.code}）`;
  }
  return apiErrorMessage(error);
}
