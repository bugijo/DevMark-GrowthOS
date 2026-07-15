import type {
  ContentRevisionInput,
  ContentVersion,
} from "@/types/api";

export function revisionInputFrom(
  version: ContentVersion,
): ContentRevisionInput {
  return {
    title: version.title,
    caption: version.caption,
    cta: version.cta ?? "",
  };
}

export function normalizeRevisionInput(
  input: ContentRevisionInput,
): ContentRevisionInput {
  return {
    title: input.title.trim(),
    caption: input.caption.trim(),
    cta: input.cta.trim(),
  };
}

export function hasMeaningfulRevisionChange(
  original: ContentRevisionInput,
  candidate: ContentRevisionInput,
): boolean {
  const normalizedOriginal = normalizeRevisionInput(original);
  const normalizedCandidate = normalizeRevisionInput(candidate);

  return (
    normalizedOriginal.title !== normalizedCandidate.title ||
    normalizedOriginal.caption !== normalizedCandidate.caption ||
    normalizedOriginal.cta !== normalizedCandidate.cta
  );
}
