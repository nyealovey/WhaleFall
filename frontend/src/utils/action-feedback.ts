import { toast } from "sonner";

type ActionMessages<T> = {
  loading?: string;
  success: string | ((data: T) => string);
  error?: string;
};

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function runAction<T>(promise: Promise<T>, messages: ActionMessages<T>): Promise<T> {
  toast.promise(promise, {
    loading: messages.loading ?? "正在处理",
    success: messages.success,
    error: (error) => errorMessage(error, messages.error ?? "操作失败")
  });
  return promise;
}
