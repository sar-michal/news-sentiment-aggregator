export const getSentimentBadgeColor = (score?: number) => {
  if (score === undefined || score === null) return "bg-muted text-muted-foreground"
  if (score > 0.15) return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
  if (score < -0.15) return "bg-destructive/10 text-destructive dark:bg-destructive/20"
  return "bg-muted text-muted-foreground"
}

export const getSentimentTextColor = (score?: number) => {
  if (score === undefined || score === null) return "text-muted-foreground"
  if (score > 0.15) return "text-emerald-600 dark:text-emerald-400"
  if (score < -0.15) return "text-destructive"
  return "text-muted-foreground"
}

