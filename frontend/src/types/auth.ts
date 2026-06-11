export type SessionUser = {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  email?: string;
};

export type SessionState = {
  authenticated: boolean;
  auth_model: "session";
  csrf_token: string;
  permissions: string[];
  user: SessionUser | null;
};

export type LoginResult = {
  auth_model: "session";
  csrf_token: string;
  user: SessionUser;
};
