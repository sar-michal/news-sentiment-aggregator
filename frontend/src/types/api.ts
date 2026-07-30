export interface EntityResponse {
  entity: string;
  type: string;
  sentiment: number;
}

export interface TimelinePoint {
  sequence_index: number;
  sentiment_score: number;
}

export interface KeySnippets {
  most_positive: string | null;
  most_negative: string | null;
}

export interface ArticleResponse {
  id: string;
  url: string;
  title: string;
  seendate: string;
  domain: string;
  sourcecountry: string;
  sentiment_score: number | null;
  entities: EntityResponse[];
  timeline: TimelinePoint[];
  snippets: KeySnippets | null;
}

export interface ArticleListResponse {
  total_results: number;
  page: number;
  size: number;
  total_pages: number;
  articles: ArticleResponse[];
}

export interface EntityLeaderboardItem {
  entity: string;
  type: string;
  avg_sentiment: number;
  sum_sentiment: number;
  mention_count: number;
}

export interface TopEntitiesResponse {
  most_positive: EntityLeaderboardItem[];
  most_negative: EntityLeaderboardItem[];
}

export interface TrendDataPoint {
  date: string;
  avg_sentiment: number;
  doc_count: number;
}

export interface SentimentTrendResponse {
  trends: TrendDataPoint[];
}

export interface DomainListResponse {
  domains: string[];
}

export interface DomainEntityStats {
  domain: string;
  mention_count: number;
  avg_sentiment: number;
  sum_sentiment: number;
}

export interface EntityAnalysisResponse {
  entity: string;
  total_mentions: number;
  overall_avg_sentiment: number;
  overall_sum_sentiment: number;
  domains: DomainEntityStats[];
}

export interface EntitySuggestionItem {
  name: string;
}

export interface EntitySuggestionResponse {
  suggestions: EntitySuggestionItem[];
}