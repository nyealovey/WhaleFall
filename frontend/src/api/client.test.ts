import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError } from "./client";

const jsonResponse = (body: unknown, init?: ResponseInit) =>
  new Response(JSON.stringify(body), {
    status: init?.status ?? 200,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

describe("ApiClient", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("unwraps success envelopes and sends same-origin credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        error: false,
        message: "ok",
        data: { authenticated: true }
      })
    );
    const client = new ApiClient({ fetchImpl: fetchMock });

    await expect(client.get("/api/v1/auth/session")).resolves.toEqual({ authenticated: true });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/session",
      expect.objectContaining({ credentials: "include", method: "GET" })
    );
  });

  it("sends csrf token only in the X-CSRFToken header for writes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        error: false,
        message: "ok",
        data: {}
      })
    );
    const client = new ApiClient({ fetchImpl: fetchMock });
    client.setCsrfToken("csrf-token");

    await client.post("/api/v1/auth/logout", {});

    const [, init] = fetchMock.mock.calls[0];
    expect(init).toMatchObject({ method: "POST", credentials: "include" });
    expect(init.headers).toMatchObject({
      "Content-Type": "application/json",
      "X-CSRFToken": "csrf-token"
    });
    expect(init.body).toBe("{}");
  });

  it("supports PUT requests with JSON body for edit dialogs", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        error: false,
        message: "updated",
        data: { id: 7 }
      })
    );
    const client = new ApiClient({ fetchImpl: fetchMock });
    client.setCsrfToken("csrf-token");

    await expect(client.put("/api/v1/users/7", { role: "admin" })).resolves.toEqual({ id: 7 });

    const [, init] = fetchMock.mock.calls[0];
    expect(init).toMatchObject({ method: "PUT", credentials: "include" });
    expect(init.headers).toMatchObject({
      "Content-Type": "application/json",
      "X-CSRFToken": "csrf-token"
    });
    expect(init.body).toBe(JSON.stringify({ role: "admin" }));
  });

  it("supports DELETE requests without forcing an empty JSON body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        error: false,
        message: "deleted",
        data: { ok: true }
      })
    );
    const client = new ApiClient({ fetchImpl: fetchMock });
    client.setCsrfToken("csrf-token");

    await expect(client.delete("/api/v1/tags/3")).resolves.toEqual({ ok: true });

    const [, init] = fetchMock.mock.calls[0];
    expect(init).toMatchObject({ method: "DELETE", credentials: "include" });
    expect(init.headers).toMatchObject({ "X-CSRFToken": "csrf-token" });
    expect(init.body).toBeUndefined();
  });

  it("throws ApiError with stable error envelope fields", async () => {
    const errorEnvelope = {
      success: false,
      error: true,
      message: "未登录",
      message_code: "AUTHENTICATION_REQUIRED",
      recoverable: true,
      suggestions: []
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(errorEnvelope, { status: 401 }))
      .mockResolvedValueOnce(jsonResponse(errorEnvelope, { status: 401 }));
    const client = new ApiClient({ fetchImpl: fetchMock });

    await expect(client.get("/api/v1/auth/me")).rejects.toMatchObject({
      status: 401,
      message: "未登录",
      messageCode: "AUTHENTICATION_REQUIRED"
    });

    await client.get("/api/v1/auth/me").catch((error: unknown) => {
      expect(error).toBeInstanceOf(ApiError);
    });
  });
});
