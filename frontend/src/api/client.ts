type FetchImpl = typeof fetch;

type ApiSuccessEnvelope<TData> = {
  success: true;
  error: false;
  message: string;
  timestamp?: string;
  data?: TData;
  meta?: Record<string, unknown>;
};

type ApiErrorEnvelope = {
  success: false;
  error: true;
  message: string;
  message_code?: string;
  recoverable?: boolean;
  suggestions?: string[];
  context?: Record<string, unknown>;
};

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: HeadersInit;
};

export class ApiError extends Error {
  readonly status: number;
  readonly messageCode?: string;
  readonly response: unknown;

  constructor(message: string, options: { status: number; messageCode?: string; response: unknown }) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.messageCode = options.messageCode;
    this.response = options.response;
  }
}

export class ApiClient {
  private csrfToken = "";
  private readonly fetchImpl: FetchImpl;

  constructor(options: { fetchImpl?: FetchImpl } = {}) {
    this.fetchImpl = options.fetchImpl ?? window.fetch.bind(window);
  }

  setCsrfToken(token: string): void {
    this.csrfToken = token;
  }

  get<TData>(path: string): Promise<TData> {
    return this.request<TData>(path, { method: "GET" });
  }

  post<TData>(path: string, body: unknown): Promise<TData> {
    return this.request<TData>(path, { method: "POST", body });
  }

  put<TData>(path: string, body: unknown): Promise<TData> {
    return this.request<TData>(path, { method: "PUT", body });
  }

  patch<TData>(path: string, body: unknown): Promise<TData> {
    return this.request<TData>(path, { method: "PATCH", body });
  }

  delete<TData>(path: string, body?: unknown): Promise<TData> {
    return this.request<TData>(path, { method: "DELETE", body });
  }

  async request<TData>(path: string, options: RequestOptions = {}): Promise<TData> {
    const method = (options.method ?? "GET").toUpperCase();
    const headers: Record<string, string> = {
      Accept: "application/json"
    };

    const init: RequestInit = {
      method,
      credentials: "include",
      headers
    };

    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }

    if (method !== "GET" && method !== "HEAD" && this.csrfToken) {
      headers["X-CSRFToken"] = this.csrfToken;
    }

    const response = await this.fetchImpl(path, init);
    const payload = await this.parseJson(response);

    if (!response.ok) {
      throw this.toApiError(response.status, payload);
    }

    if (this.isErrorEnvelope(payload)) {
      throw this.toApiError(response.status, payload);
    }

    if (!this.isSuccessEnvelope<TData>(payload)) {
      throw new ApiError("接口响应格式无效", { status: response.status, response: payload });
    }

    return payload.data as TData;
  }

  private async parseJson(response: Response): Promise<unknown> {
    const text = await response.text();
    if (!text) {
      return null;
    }
    try {
      return JSON.parse(text) as unknown;
    } catch {
      throw new ApiError("接口响应不是有效 JSON", { status: response.status, response: text });
    }
  }

  private isSuccessEnvelope<TData>(payload: unknown): payload is ApiSuccessEnvelope<TData> {
    return (
      typeof payload === "object" &&
      payload !== null &&
      "success" in payload &&
      (payload as { success: unknown }).success === true &&
      "error" in payload &&
      (payload as { error: unknown }).error === false
    );
  }

  private isErrorEnvelope(payload: unknown): payload is ApiErrorEnvelope {
    return (
      typeof payload === "object" &&
      payload !== null &&
      "success" in payload &&
      (payload as { success: unknown }).success === false &&
      "error" in payload &&
      (payload as { error: unknown }).error === true
    );
  }

  private toApiError(status: number, payload: unknown): ApiError {
    if (this.isErrorEnvelope(payload)) {
      return new ApiError(payload.message, {
        status,
        messageCode: payload.message_code,
        response: payload
      });
    }
    return new ApiError("请求失败", { status, response: payload });
  }
}

export const apiClient = new ApiClient();
