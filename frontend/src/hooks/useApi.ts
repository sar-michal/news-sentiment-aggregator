import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { 
  ArticleListResponse, 
  ArticleResponse, 
  SentimentTrendResponse, 
  TopEntitiesResponse, 
  DomainListResponse 
} from '../types/api'

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
})

export function useSentimentTrend(
  interval = 'day', 
  domain?: string, 
  startDate?: string, 
  endDate?: string
) {
  return useQuery({
    queryKey: ['sentimentTrend', interval, domain, startDate, endDate],
    queryFn: async () => {
      const response = await apiClient.get<SentimentTrendResponse>('/analytics/sentiment-trend', {
        params: { 
          interval, 
          domain,
          start_date: startDate, 
          end_date: endDate 
        },
      })
      return response.data
    },
  })
}

export function useTopEntities(
  domain?: string,
  minMentions = 5, 
  startDate?: string, 
  endDate?: string
) {
  return useQuery({
    queryKey: ['topEntities', domain, minMentions, startDate, endDate],
    queryFn: async () => {
      const response = await apiClient.get<TopEntitiesResponse>('/analytics/top-entities', {
        params: { 
          domain: domain,
          min_mentions: minMentions,
          start_date: startDate,
          end_date: endDate
        },
      })
      return response.data
    },
  })
}

export function useDomains() {
  return useQuery({
    queryKey: ['domains'],
    queryFn: async () => {
      const response = await apiClient.get<DomainListResponse>('/metadata/domains')
      return response.data
    },
  })
}

export function useArticleSearch(
  queryStr?: string, 
  domain?: string, 
  page = 1,
  size = 20
) {
  return useQuery({
    queryKey: ['articles', queryStr, domain, page, size],
    queryFn: async () => {
      const response = await apiClient.get<ArticleListResponse>('/articles/', {
        params: { 
          query_str: queryStr, 
          domain, 
          page, 
          size 
        },
      })
      return response.data
    },
  })
}

export function useArticle(articleId: string | undefined) {
  return useQuery({
    queryKey: ['article', articleId],
    queryFn: async () => {
      const response = await apiClient.get<ArticleResponse>(`/articles/${articleId}`)
      return response.data
    },
    enabled: !!articleId, 
  })
}