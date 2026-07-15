import { STATUS_LABELS } from "@/lib/format";
import type { ContentStatus } from "@/types/api";

const colors: Record<ContentStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  INTERNAL_REVIEW: "bg-amber-100 text-amber-800",
  CLIENT_REVIEW: "bg-violet-100 text-violet-800",
  CHANGES_REQUESTED: "bg-orange-100 text-orange-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  SCHEDULED: "bg-sky-100 text-sky-800",
  PUBLISHED: "bg-teal-100 text-teal-800",
  FAILED: "bg-red-100 text-red-800",
  ARCHIVED: "bg-slate-200 text-slate-600",
};

export function StatusBadge({ status }: { status: ContentStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold ${colors[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
