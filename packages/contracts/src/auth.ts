import { z } from "zod";

export const platformRoleSchema = z.enum(["admin", "user"]);
export type PlatformRole = z.infer<typeof platformRoleSchema>;

const uuidSchema = z.string().uuid();
const instantSchema = z.string().datetime({ offset: true });

/** Usernames are stored lowercase; callers must normalize before lookup. */
export const usernameSchema = z
  .string()
  .min(3)
  .max(64)
  .regex(/^[A-Za-z0-9._-]+$/, "Username may contain letters, digits, dot, underscore and hyphen only");

export const newPasswordSchema = z.string().min(12).max(256);

export const loginRequestSchema = z
  .object({
    username: usernameSchema,
    password: z.string().min(1).max(256),
  })
  .strict();

export const changePasswordRequestSchema = z
  .object({
    currentPassword: z.string().min(1).max(256),
    newPassword: newPasswordSchema,
  })
  .strict();

export const userSchema = z
  .object({
    id: uuidSchema,
    username: z.string().min(1),
    role: platformRoleSchema,
    active: z.boolean(),
    mustChangePassword: z.boolean(),
    createdAt: instantSchema,
  })
  .strict();

export const csrfTokenResponseSchema = z.object({ csrfToken: z.string().min(1) }).strict();

export const loginResultSchema = z
  .object({
    user: userSchema,
    csrfToken: z.string().min(1),
    expiresAt: instantSchema,
  })
  .strict();

export const createUserRequestSchema = z
  .object({
    username: usernameSchema,
    temporaryPassword: newPasswordSchema,
    role: platformRoleSchema,
  })
  .strict();

export const updateUserRequestSchema = z
  .object({
    role: platformRoleSchema.optional(),
    active: z.boolean().optional(),
    resetPassword: newPasswordSchema.optional(),
  })
  .strict()
  .refine(
    (value) => value.role !== undefined || value.active !== undefined || value.resetPassword !== undefined,
    { message: "At least one of role, active or resetPassword is required" },
  );

export const userListSchema = z.object({ users: z.array(userSchema) }).strict();

export function normalizeUsername(username: string): string {
  return username.trim().toLowerCase();
}

export function parseLoginRequest(input: unknown) {
  return loginRequestSchema.parse(input);
}

export function parseChangePasswordRequest(input: unknown) {
  return changePasswordRequestSchema.parse(input);
}

export function parseCreateUserRequest(input: unknown) {
  return createUserRequestSchema.parse(input);
}

export function parseUpdateUserRequest(input: unknown) {
  return updateUserRequestSchema.parse(input);
}

export type PlatformUser = z.infer<typeof userSchema>;
export type LoginRequest = z.infer<typeof loginRequestSchema>;
export type LoginResult = z.infer<typeof loginResultSchema>;
export type ChangePasswordRequest = z.infer<typeof changePasswordRequestSchema>;
export type CreateUserRequest = z.infer<typeof createUserRequestSchema>;
export type UpdateUserRequest = z.infer<typeof updateUserRequestSchema>;
