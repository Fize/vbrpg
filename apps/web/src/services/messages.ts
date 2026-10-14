import { ApiError, apiErrorMessage } from "./api";

/**
 * 面向用户的中文提示。仅做展示层翻译，不改变服务端语义；
 * 未覆盖的错误码保留服务端原文，便于对照 requestId 排查。
 */
const MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "用户名或密码不正确",
  SESSION_INVALID: "登录已过期，请重新登录",
  PASSWORD_CHANGE_REQUIRED: "请先修改初始密码",
  CURRENT_PASSWORD_INVALID: "当前密码不正确",
  PASSWORD_UNCHANGED: "新密码不能与当前密码相同",
  CSRF_TOKEN_INVALID: "页面已过期，请刷新后重试",
  ORIGIN_REQUIRED: "请求缺少来源信息，请刷新后重试",
  ORIGIN_NOT_ALLOWED: "请求来源不受信任，请刷新后重试",
  INSUFFICIENT_ROLE: "当前账号没有该操作权限",
  RATE_LIMITED: "尝试次数过多，请稍后再试",
  ACCOUNT_MISSING: "账号状态异常，请联系管理员",
};

export function uiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const message = MESSAGES[error.code];
    if (message !== undefined) {
      return message;
    }
  }
  return apiErrorMessage(error);
}
