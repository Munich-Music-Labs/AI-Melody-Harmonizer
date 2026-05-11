import { useEffect, useMemo, useState } from "react";
import { Dropzone } from "./components/Dropzone";
import { GenreSelect } from "./components/GenreSelect";
import { fetchGenres, harmonize, type ApiError } from "./api";

type Status = "idle" | "loading-genres" | "uploading" | "success" | "error";

interface DownloadInfo {
  url: string;
  filename: string;
}

export default function App() {
  const [genres, setGenres] = useState<string[]>([]);
  const [genre, setGenre] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("loading-genres");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [download, setDownload] = useState<DownloadInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading-genres");
    fetchGenres()
      .then((list) => {
        if (cancelled) return;
        setGenres(list);
        setGenre((prev) => (prev && list.includes(prev) ? prev : list[0] ?? ""));
        setStatus("idle");
      })
      .catch((err: ApiError) => {
        if (cancelled) return;
        setErrorMessage(err.message ?? "Failed to load genres.");
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (download?.url) URL.revokeObjectURL(download.url);
    };
  }, [download]);

  const isBusy = status === "uploading" || status === "loading-genres";
  const canHarmonize = useMemo(
    () => Boolean(file && genre) && !isBusy,
    [file, genre, isBusy]
  );

  async function onHarmonize() {
    if (!file || !genre) return;
    if (download?.url) URL.revokeObjectURL(download.url);
    setDownload(null);
    setErrorMessage("");
    setStatus("uploading");
    try {
      const { blob, filename } = await harmonize(file, genre);
      const url = URL.createObjectURL(blob);
      setDownload({ url, filename });
      setStatus("success");
    } catch (err) {
      const apiErr = err as ApiError;
      setErrorMessage(apiErr.message ?? "Harmonization failed.");
      setStatus("error");
    }
  }

  function onFileSelected(next: File | null) {
    setFile(next);
    if (status === "success" || status === "error") {
      setStatus("idle");
      setErrorMessage("");
      if (download?.url) URL.revokeObjectURL(download.url);
      setDownload(null);
    }
  }

  return (
    <div className="min-h-full bg-gradient-to-br from-indigo-50 via-white to-slate-100 text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-2xl flex-col items-center px-4 py-12">
        <header className="mb-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">
            AI Melody Harmonizer
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Drop a melody. Get a harmonized MIDI back.
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            Upload a MIDI file, pick a genre style, and the harmonizer will generate a
            chord progression and return a new MIDI you can download.
          </p>
        </header>

        <main className="w-full rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm backdrop-blur">
          <Dropzone file={file} onFileSelected={onFileSelected} disabled={isBusy} />

          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <GenreSelect
              genres={genres}
              value={genre}
              onChange={setGenre}
              disabled={status === "uploading"}
              loading={status === "loading-genres"}
            />

            <div className="flex flex-col gap-1.5 text-left">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Action
              </span>
              <button
                type="button"
                onClick={onHarmonize}
                disabled={!canHarmonize}
                className="inline-flex h-[42px] items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {status === "uploading" ? (
                  <>
                    <Spinner /> Harmonizing...
                  </>
                ) : (
                  "Harmonize"
                )}
              </button>
            </div>
          </div>

          <div className="mt-6 min-h-[60px]">
            {status === "success" && download && (
              <div className="flex flex-col gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-sm font-semibold text-emerald-800">
                    Harmonization complete
                  </div>
                  <div className="text-xs text-emerald-700">{download.filename}</div>
                </div>
                <a
                  href={download.url}
                  download={download.filename}
                  className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700"
                >
                  Download MIDI
                </a>
              </div>
            )}

            {status === "error" && errorMessage && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                <div className="font-semibold">Something went wrong</div>
                <div className="mt-1 text-red-700">{errorMessage}</div>
              </div>
            )}
          </div>
        </main>

        <footer className="mt-8 text-center text-xs text-slate-500">
          Built on the AutoHarmonizer model. Backend on :8000, UI on :5173.
        </footer>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"
      />
    </svg>
  );
}
