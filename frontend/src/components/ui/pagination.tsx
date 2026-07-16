"use client";

type PaginationToken = number | "start-ellipsis" | "end-ellipsis";

export function paginationTokens(page: number, totalPages: number): PaginationToken[] {
  const current = Math.min(Math.max(page, 1), totalPages);
  if (totalPages <= 7) {
    return Array.from({ length: Math.max(totalPages, 0) }, (_, index) => index + 1);
  }

  const pages = new Set([1, totalPages, current - 1, current, current + 1]);
  const visiblePages = Array.from(pages)
    .filter((item) => item >= 1 && item <= totalPages)
    .sort((a, b) => a - b);
  const tokens: PaginationToken[] = [];

  visiblePages.forEach((item, index) => {
    const previous = visiblePages[index - 1];
    if (previous && item - previous > 1) {
      tokens.push(previous === 1 ? "start-ellipsis" : "end-ellipsis");
    }
    tokens.push(item);
  });

  return tokens;
}

export function Pagination({
  page,
  totalPages,
  disabled = false,
  ariaLabel = "Paginação",
  onPageChange,
}: {
  page: number;
  totalPages: number;
  disabled?: boolean;
  ariaLabel?: string;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  const current = Math.min(Math.max(page, 1), totalPages);
  const tokens = paginationTokens(current, totalPages);

  return (
    <nav aria-label={ariaLabel} className="flex flex-wrap items-center justify-center gap-2">
      <span className="sr-only" aria-live="polite" aria-atomic="true">
        Página {current} de {totalPages}
      </span>
      <button
        type="button"
        disabled={disabled || current === 1}
        onClick={() => onPageChange(current - 1)}
        className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
      >
        Anterior
      </button>
      {tokens.map((token) =>
        typeof token === "number" ? (
          <button
            key={token}
            type="button"
            aria-label={
              token === current
                ? `Página ${token}, atual`
                : `Ir para a página ${token}`
            }
            aria-current={token === current ? "page" : undefined}
            disabled={disabled}
            onClick={() => onPageChange(token)}
            className={`inline-flex size-11 items-center justify-center rounded-xl border text-sm font-bold ${
              token === current
                ? "border-emerald-700 bg-emerald-700 text-white"
                : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            } disabled:cursor-not-allowed disabled:opacity-60`}
          >
            {token}
          </button>
        ) : (
          <span key={token} aria-hidden="true" className="px-1 text-slate-500">
            …
          </span>
        ),
      )}
      <button
        type="button"
        disabled={disabled || current === totalPages}
        onClick={() => onPageChange(current + 1)}
        className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
      >
        Próxima
      </button>
    </nav>
  );
}
