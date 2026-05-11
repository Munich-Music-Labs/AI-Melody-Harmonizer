interface GenreSelectProps {
  genres: string[];
  value: string;
  onChange: (genre: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

export function GenreSelect({ genres, value, onChange, disabled, loading }: GenreSelectProps) {
  return (
    <label className="flex flex-col gap-1.5 text-left">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Genre style
      </span>
      <div className="relative">
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled || loading || genres.length === 0}
          className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-9 text-sm font-medium text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {genres.length === 0 ? (
            <option value="">{loading ? "Loading..." : "No genres available"}</option>
          ) : (
            genres.map((genre) => (
              <option key={genre} value={genre}>
                {prettyName(genre)}
              </option>
            ))
          )}
        </select>
        <svg
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.06l3.71-3.83a.75.75 0 0 1 1.08 1.04l-4.24 4.39a.75.75 0 0 1-1.08 0L5.21 8.27a.75.75 0 0 1 .02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </div>
    </label>
  );
}

function prettyName(genre: string): string {
  if (!genre) return genre;
  return genre.charAt(0).toUpperCase() + genre.slice(1);
}
