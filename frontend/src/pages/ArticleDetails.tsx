import { useMemo, useState } from "react"
import { useParams, Link, useLocation } from "react-router"
import { useArticle } from "../hooks/useApi"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { ArrowLeft, Globe, Calendar, MapPin, TrendingUp, TrendingDown, ArrowUpDown } from "lucide-react"

export default function ArticleDetails() {
  const { articleId } = useParams<{ articleId: string }>()
  const location = useLocation()
  const { data: article, isLoading, isError } = useArticle(articleId)

  const [entitySort, setEntitySort] = useState<"default" | "desc" | "asc">("default")

  const backLink = location.state?.searchString 
    ? `/search?${location.state.searchString}` 
    : "/search"

  const processedTimeline = useMemo(() => {
    if (!article?.timeline || article.timeline.length === 0) return []
    
    const sorted = [...article.timeline].sort((a, b) => a.sequence_index - b.sequence_index)
    let runningSum = 0
    
    return sorted.map((point, index) => {
      runningSum += point.sentiment_score
      return {
        ...point,
        display_index: point.sequence_index + 1,
        running_average: runningSum / (index + 1)
      }
    })
  }, [article?.timeline])

  const sortedEntities = useMemo(() => {
    if (!article?.entities) return []
    if (entitySort === "default") return article.entities

    return [...article.entities].sort((a: any, b: any) => {
      const scoreA = typeof a === 'string' ? null : (a.sentiment !== undefined ? a.sentiment : null)
      const scoreB = typeof b === 'string' ? null : (b.sentiment !== undefined ? b.sentiment : null)

      if (scoreA === null && scoreB === null) return 0
      if (scoreA === null) return 1
      if (scoreB === null) return -1

      return entitySort === "desc" ? scoreB - scoreA : scoreA - scoreB
    })
  }, [article?.entities, entitySort])

  const handleEntitySortChange = (val: string | null) => {
    if (val === "default" || val === "desc" || val === "asc") {
      setEntitySort(val)
    }
  }

  const getSentimentColor = (score?: number) => {
    if (score === undefined || score === null) return "bg-muted text-muted-foreground"
    if (score > 0.15) return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
    if (score < -0.15) return "bg-destructive/10 text-destructive dark:bg-destructive/20"
    return "bg-muted text-muted-foreground"
  }

  const getEntitySentimentTextColor = (score?: number) => {
    if (score === undefined || score === null) return "text-muted-foreground"
    if (score > 0.1) return "text-emerald-600 dark:text-emerald-400 font-semibold"
    if (score < -0.1) return "text-destructive font-semibold"
    return "text-muted-foreground"
  }

  if (isLoading) {
    return (
      <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-6">
        <div className="h-6 w-24 bg-muted animate-pulse rounded" />
        <Card className="h-48 bg-muted/20 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="h-64 bg-muted/20 animate-pulse" />
          <Card className="h-64 bg-muted/20 animate-pulse" />
        </div>
      </div>
    )
  }

  if (isError || !article) {
    return (
      <div className="p-4 md:p-8 max-w-6xl mx-auto text-center space-y-4">
        <p className="text-destructive font-medium">Failed to retrieve article details.</p>
        <Link to={backLink} className={buttonVariants({ variant: "outline" })}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Search
        </Link>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* BACK TO SEARCH NAVIGATION */}
        <div className="flex items-center justify-between">
          <Link 
            to={backLink} 
            className={`${buttonVariants({ variant: "ghost", size: "sm" })} text-muted-foreground hover:text-foreground`}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Search
          </Link>
          
          {article.url && (
            <a 
              href={article.url} 
              target="_blank" 
              rel="noreferrer"
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              <Globe className="mr-2 h-4 w-4" />
              Original Source
            </a>
          )}
        </div>

        {/* HERO TITLE BLOCK */}
        <header className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-2 flex-1">
              <h1 className="text-2xl md:text-4xl font-bold tracking-tight text-foreground leading-tight">
                {article.title}
              </h1>
              
              <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground font-medium pt-1">
                <span className="bg-secondary text-secondary-foreground px-2 py-0.5 rounded-md text-xs">
                  {article.domain}
                </span>
                {article.seendate && (
                  <span className="flex items-center gap-1.5">
                    <Calendar className="h-4 w-4" />
                    {new Date(article.seendate).toLocaleDateString(undefined, { 
                      month: 'long', day: 'numeric', year: 'numeric' 
                    })}
                  </span>
                )}
                {article.sourcecountry && article.sourcecountry !== "Unknown" && (
                  <span className="flex items-center gap-1.5 border-l border-border pl-4">
                    <MapPin className="h-4 w-4" />
                    {article.sourcecountry}
                  </span>
                )}
              </div>
            </div>

            {article.sentiment_score !== undefined && article.sentiment_score !== null && (
              <div className="flex flex-col items-start md:items-end gap-1 shrink-0">
                <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Overall Sentiment</span>
                <Badge className={`text-lg px-3 py-1 font-bold ${getSentimentColor(article.sentiment_score)}`}>
                  {article.sentiment_score > 0 ? '+' : ''}{article.sentiment_score.toFixed(2)}
                </Badge>
              </div>
            )}
          </div>
        </header>

        {/* GRAPHS LAYOUT */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Raw Sentence Sentiment</CardTitle>
              <CardDescription>
                Sentence-by-sentence narrative progression.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {processedTimeline.length > 0 ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart 
                      data={processedTimeline}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                      <XAxis 
                        dataKey="display_index"
                        type="number"
                        domain={['dataMin', 'dataMax']}
                        tickCount={20}
                        allowDecimals={false}
                        stroke="var(--muted-foreground)" 
                        fontSize={12} 
                        tickMargin={8}
                      />
                      <YAxis domain={[-1, 1]} stroke="var(--muted-foreground)" fontSize={12} />
                      <Tooltip 
                        formatter={(value: any) => [`${typeof value === 'number' && value > 0 ? '+' : ''}${typeof value === 'number' ? value.toFixed(2) : value}`, 'Raw Score']}
                        labelFormatter={(label) => `Sentence #${label}`}
                        contentStyle={{ 
                          borderRadius: 'var(--radius)',
                          border: '1px solid var(--border)', 
                          backgroundColor: 'var(--background)',
                          color: 'var(--foreground)',
                          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' 
                        }}
                      />
                      <ReferenceLine y={0} stroke="var(--border)" strokeWidth={1.5} />
                      <Area 
                        type="monotone" 
                        dataKey="sentiment_score" 
                        stroke="var(--chart-2)" 
                        fill="var(--chart-2)" 
                        fillOpacity={0.1}
                        strokeWidth={2.5}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No sentence-level sentiment data available.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Cumulative Sentiment Average</CardTitle>
              <CardDescription>
                Running tally mapping the overall sentiment trajectory.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {processedTimeline.length > 0 ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart 
                      data={processedTimeline}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                      <XAxis 
                        dataKey="display_index"
                        type="number"
                        domain={['dataMin', 'dataMax']}
                        tickCount={20}
                        allowDecimals={false}
                        stroke="var(--muted-foreground)" 
                        fontSize={12} 
                        tickMargin={8}
                      />
                      <YAxis domain={[-1, 1]} stroke="var(--muted-foreground)" fontSize={12} />
                      <Tooltip 
                        formatter={(value: any) => [`${typeof value === 'number' && value > 0 ? '+' : ''}${typeof value === 'number' ? value.toFixed(2) : value}`, 'Cumulative Avg']}
                        labelFormatter={(label) => `Up to Sentence #${label}`}
                        contentStyle={{ 
                          borderRadius: 'var(--radius)',
                          border: '1px solid var(--border)', 
                          backgroundColor: 'var(--background)',
                          color: 'var(--foreground)',
                          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' 
                        }}
                      />
                      <ReferenceLine y={0} stroke="var(--border)" strokeWidth={1.5} />
                      <Line 
                        type="monotone" 
                        dataKey="running_average" 
                        stroke="var(--chart-3)" 
                        strokeWidth={3} 
                        dot={false}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No data available for running average.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* SNIPPETS & ENTITIES SPLIT LAYOUT */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          <div className="md:col-span-2 space-y-6">
            <Card className="h-full">
              <CardHeader>
                <CardTitle>Key Snippets</CardTitle>
                <CardDescription>Most positive and negative sentences parsed from the article.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {article.snippets?.most_positive ? (
                  <div className="space-y-1.5 border border-border bg-emerald-50/20 dark:bg-emerald-950/10 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                      <TrendingUp className="h-4 w-4" />
                      Peak Positive Sentence
                    </div>
                    <p className="text-sm text-foreground italic leading-relaxed">
                      "{article.snippets.most_positive}"
                    </p>
                  </div>
                ) : null}

                {article.snippets?.most_negative ? (
                  <div className="space-y-1.5 border border-border bg-destructive/5 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-destructive">
                      <TrendingDown className="h-4 w-4" />
                      Peak Negative Sentence
                    </div>
                    <p className="text-sm text-foreground italic leading-relaxed">
                      "{article.snippets.most_negative}"
                    </p>
                  </div>
                ) : null}

                {!article.snippets?.most_positive && !article.snippets?.most_negative && (
                  <p className="text-sm text-muted-foreground italic text-center py-4">No key structural sentences generated.</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 space-y-0 pb-4">
              <div className="space-y-1.5">
                <CardTitle>Recognized Entities</CardTitle>
                <CardDescription>Extracted Named Entities observed in this document.</CardDescription>
              </div>
              <Select value={entitySort} onValueChange={handleEntitySortChange}>
                <SelectTrigger className="w-full sm:w-35 h-8 text-xs bg-background">
                  <div className="flex items-center gap-2">
                    <ArrowUpDown className="h-3 w-3" />
                    <SelectValue placeholder="Sort..." />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Default</SelectItem>
                  <SelectItem value="desc">Highest First</SelectItem>
                  <SelectItem value="asc">Lowest First</SelectItem>
                </SelectContent>
              </Select>
            </CardHeader>
            
            <CardContent className="p-0 pt-0 sm:p-6 sm:pt-0">
              {sortedEntities.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Entity</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Sentiment</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedEntities.map((ent: any, idx: number) => {
                      const isString = typeof ent === 'string'
                      const entityName = isString ? ent : ent.entity
                      const entityType = isString ? 'Mention' : ent.type || 'Unknown'
                      const entitySentiment = isString ? undefined : ent.sentiment

                      return (
                        <TableRow key={idx}>
                          <TableCell className="font-medium max-w-30 truncate" title={entityName}>
                            {entityName}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-[10px] uppercase tracking-wider bg-secondary text-secondary-foreground">
                              {entityType}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            {entitySentiment !== undefined && entitySentiment !== null ? (
                              <span className={`text-sm ${getEntitySentimentTextColor(entitySentiment)}`}>
                                {entitySentiment > 0 ? '+' : ''}{entitySentiment.toFixed(2)}
                              </span>
                            ) : (
                              <span className="text-muted-foreground text-xs">-</span>
                            )}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground p-6 pt-0 italic">No named entities recognized inside the text.</p>
              )}
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  )
}