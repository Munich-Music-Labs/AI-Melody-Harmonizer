import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

interface DropzoneProps {
  file: File | null;
  onFileSelected: (file: File | null) => void;
  disabled?: boolean;
}

export function Dropzone({ file, onFileSelected, disabled }: DropzoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) {
        onFileSelected(accepted[0]);
      }
    },
    [onFileSelected]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    multiple: false,
    disabled,
    accept: {
      "audio/midi": [".mid", ".midi"],
      "audio/x-midi": [".mid", ".midi"],
    },
  });

  const baseClasses =
    "relative flex flex-col items-center justify-center w-full rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-colors";
  const stateClasses = isDragReject
    ? "border-red-400 bg-red-50 text-red-700"
    : isDragActive
      ? "border-indigo-500 bg-indigo-50 text-indigo-700"
      : "border-slate-300 bg-white/60 text-slate-600 hover:border-indigo-400 hover:bg-white";
  const disabledClasses = disabled ? "opacity-50 pointer-events-none" : "cursor-pointer";

  return (
    <div {...getRootProps({ className: `${baseClasses} ${stateClasses} ${disabledClasses}` })}>
      <input {...getInputProps()} />

      {file ? (
        <div className="flex flex-col items-center gap-2">
          <div className="text-sm uppercase tracking-wider text-slate-500">Selected file</div>
          <div className="text-lg font-semibold text-slate-900 break-all">{file.name}</div>
          <div className="text-xs text-slate-500">{formatBytes(file.size)}</div>
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onFileSelected(null);
            }}
            disabled={disabled}
            className="mt-3 inline-flex items-center rounded-full border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:border-red-400 hover:text-red-600 disabled:opacity-50"
          >
            Remove
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <UploadIcon className="h-10 w-10 text-indigo-500" />
          <div className="text-base font-semibold text-slate-800">
            {isDragActive ? "Drop the MIDI file here" : "Drag and drop a MIDI file"}
          </div>
          <div className="text-sm text-slate-500">
            or <span className="font-medium text-indigo-600">browse</span> to choose a file
          </div>
          <div className="mt-2 text-xs text-slate-400">.mid or .midi only</div>
        </div>
      )}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 16V4" />
      <path d="m6 10 6-6 6 6" />
      <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
    </svg>
  );
}
