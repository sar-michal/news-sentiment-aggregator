import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { 
  ArticleListResponse, 
  ArticleResponse, 
  SentimentTrendResponse, 
  TopEntitiesResponse, 
  DomainListResponse,
  EntityAnalysisResponse,
  EntitySuggestionResponse
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
  startDate?: string,
  endDate?: string,
  page = 1,
  size = 20
) {
  return useQuery({
    queryKey: ['articles', queryStr, domain, startDate, endDate, page, size],
    queryFn: async () => {
      const response = await apiClient.get<ArticleListResponse>('/articles/', {
        params: { 
          query_str: queryStr, 
          domain,
          start_date: startDate,
          end_date: endDate,
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

export function useEntityAnalysis(
  entityName?: string,
  startDate?: string,
  endDate?: string
) {
  return useQuery({
    queryKey: ['entityAnalysis', entityName, startDate, endDate],
    queryFn: async () => {
      if (!entityName) return null
      const response = await apiClient.get<EntityAnalysisResponse>('/analytics/entity-analysis', {
        params: { 
          entity: entityName, 
          start_date: startDate, 
          end_date: endDate 
        },
      })
      return response.data
    },
    enabled: !!entityName && entityName.trim().length > 0,
  })
}

export function useEntitySuggest(prefix: string) {
  return useQuery({
    queryKey: ['entitySuggest', prefix],
    queryFn: async () => {
      const response = await apiClient.get<EntitySuggestionResponse>('/analytics/entity-suggest', {
        params: { prefix },
      })
      return response.data
    },
    enabled: prefix.trim().length >= 2,
    staleTime: 1000 * 60 * 5, 
    placeholderData: (previousData) => previousData,
  })
}