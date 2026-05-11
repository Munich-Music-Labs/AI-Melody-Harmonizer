export interface ApiError {
  status: number;
  message: string;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (data && typeof data === "object") {
      if (typeof data.error === "string") return data.error;
      if (typeof data.detail === "string") return data.detail;
    }
  } catch {
    // ignore: body wasn't JSON
  }
  return response.statusText || `Request failed with status ${response.status}`;
}

export async function fetchGenres(): Promise<string[]> {
  const response = await fetch("/api/genres");
  if (!response.ok) {
    const message = await readErrorMessage(response);
    const err: ApiError = { status: response.status, message };
    throw err;
  }
  const data = (await response.json()) as { genres: string[] };
  return data.genres ?? [];
}

export interface HarmonizeResult {
  blob: Blob;
  filename: string;
}

export async function harmonize(
  file: File,
  genre: string
): Promise<HarmonizeResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("genre", genre);

  const response = await fetch("/api/harmonize", {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    const err: ApiError = { status: response.status, message };
    throw err;
  }

  const blob = await response.blob();
  const filename = parseFilename(response.headers.get("content-disposition")) ??
    fallbackFilename(file.name, genre);

  return { blob, filename };
}

function parseFilename(contentDisposition: string | null): string | undefined {
  if (!contentDisposition) return undefined;
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(contentDisposition);
  if (utf8 && utf8[1]) return decodeURIComponent(utf8[1].trim().replace(/^"|"$/g, ""));
  const ascii = /filename="?([^";]+)"?/i.exec(contentDisposition);
  if (ascii && ascii[1]) return ascii[1].trim();
  return undefined;
}

function fallbackFilename(originalName: string, genre: string): string {
  const dot = originalName.lastIndexOf(".");
  const stem = dot > 0 ? originalName.slice(0, dot) : originalName;
  return `${stem}_harmonized_${genre}.mid`;
}
