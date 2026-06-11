import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import type { LoginResult, SessionState } from "../types/auth";

const SESSION_QUERY_KEY = ["auth", "session"] as const;

export function useSession() {
  return useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: async () => {
      const session = await apiClient.get<SessionState>("/api/v1/auth/session");
      apiClient.setCsrfToken(session.csrf_token);
      return session;
    },
    staleTime: 30_000
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { username: string; password: string }) => {
      const result = await apiClient.post<LoginResult>("/api/v1/auth/login", payload);
      apiClient.setCsrfToken(result.csrf_token);
      return result;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    }
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.post<Record<string, never>>("/api/v1/auth/logout", {});
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    }
  });
}
