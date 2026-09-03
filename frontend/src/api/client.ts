const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as
    | string
    | undefined) ??
  "http://localhost:8000";

export class ApiError extends Error {
  public readonly status: number;

  constructor(
    status: number,
    message: string,
  ) {
    super(message);

    this.name = "ApiError";
    this.status = status;
  }
}

export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}${path}`,
      {
        ...options,
        headers: {
          "Content-Type":
            "application/json",
          ...(options?.headers ?? {}),
        },
      },
    );
  } catch {
    throw new ApiError(
      0,
      `Could not reach ${API_BASE_URL}. Is the backend running?`,
    );
  }

  if (!response.ok) {
    let message =
      response.statusText ||
      `HTTP ${response.status}`;

    try {
      const body = (await response.json()) as {
        detail?: string;
      };

      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Response was not JSON.
    }

    throw new ApiError(
      response.status,
      message,
    );
  }

  return (await response.json()) as T;
}

export { API_BASE_URL };