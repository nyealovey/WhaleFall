export function formatStatisticsSizeMb(value: number | undefined): string {
  const size = value ?? 0;
  if (size >= 1024 * 1024) {
    return `${(size / 1024 / 1024).toFixed(2)} TB`;
  }
  if (size >= 1024) {
    return `${(size / 1024).toFixed(2)} GB`;
  }
  return `${size.toFixed(2)} MB`;
}
