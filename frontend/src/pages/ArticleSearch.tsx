import { useEffect } from "react"
import { useSearchParams, Link } from "react-router"
import { useArticleSearch, useDomains } from "../hooks/useApi"
import { getSentimentBadgeColor } from "@/lib/sentiment"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
import { 
  Search, 
  Globe, 
  Calendar, 
  TrendingUp, 
  TrendingDown,
  ChevronLeft,
  ChevronRight
} from "lucide-react"

export default function ArticleSearch() {
  const [searchParams, setSearchParams] = useSearchParams()
  
  const query = searchParams.get("q") || undefined
  const domain = searchParams.get("domain") || "all"
  const startDate = searchParams.get("start_date") || undefined
  const endDate = searchParams.get("end_date") || undefined
  const size = searchParams.get("size") || "20"
  const page = parseInt(searchParams.get("page") || "1", 10)

  const { data: domainsData } = useDomains()
  const { data, isLoading, isError } = useArticleSearch(
    query, 
    domain === "all" ? undefined : domain, 
    startDate,
    endDate,
    page, 
    parseInt(size)
  )

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" })
  }, [page, query, domain, startDate, endDate, size])

  const updateParams = (updates: Record<string, string | undefined>) => {
    const newParams = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value === undefined || value === "") {
        newParams.delete(key)
      } else {
        newParams.set(key, value)
      }
    })
    setSearchParams(newParams)
  }

  const handleSearch = async (formData: FormData) => {
    const q = formData.get("q") as string
    updateParams({ q, page: "1" })
  }

  const handleDomainChange = (val: string | null) => {
    if (!val) return
    updateParams({ domain: val === "all" ? undefined : val, page: "1" })
  }

  const handleSizeChange = (val: string | null) => {
    if (!val) return
    updateParams({ size: val, page: "1" })
  }

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateParams({ start_date: e.target.value, page: "1" })
  }

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateParams({ end_date: e.target.value, page: "1" })
  }

  const setPage = (newPage: number) => {
    updateParams({ page: newPage.toString() })
  }

  const PaginationControls = ({ className = "" }: { className?: string }) => (
    <div className={`flex items-center justify-between py-4 ${className}`}>
      <Button
        variant="outline"
        onClick={() => setPage(Math.max(1, page - 1))}
        disabled={page <= 1 || isLoading}
        className="w-28"
      >
        <ChevronLeft className="h-4 w-4 mr-2" />
        Previous
      </Button>
      
      <span className="text-sm font-medium text-muted-foreground hidden sm:inline-block">
        Page {data?.page || page} of {data?.total_pages || 1}
      </span>

      <Button
        variant="outline"
        onClick={() => setPage(page + 1)}
        disabled={!data || page >= data.total_pages || data.total_pages === 0 || isLoading}
        className="w-28"
      >
        Next
        <ChevronRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  )

  return (
    <div className="p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        
        <header className="pb-4 border-b border-border">
          <h1 className="text-3xl font-bold tracking-tight">Article Search</h1>
          <p className="text-muted-foreground mt-1">Analysis of specific news coverage and sentiment.</p>
        </header>

        {/* SEARCH & FILTER CONTROLS */}
        <Card className="bg-card">
          <CardContent className="p-4 sm:p-6 space-y-4">
            
            <form action={handleSearch} className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  name="q" 
                  key={query || "empty"} 
                  placeholder="Search for companies, people, or keywords..." 
                  className="pl-9 w-full"
                  defaultValue={query}
                />
              </div>
              <Button type="submit" className="sm:w-32" disabled={isLoading}>
                {isLoading ? "Searching..." : "Search"}
              </Button>
            </form>

            <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-border/50">
              <div className="flex items-center gap-2 flex-1 min-w-50">
                <Label className="text-muted-foreground whitespace-nowrap">Source:</Label>
                <Select value={domain} onValueChange={handleDomainChange}>
                  <SelectTrigger className="w-full h-9">
                    <SelectValue placeholder="All Domains" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Domains</SelectItem>
                    {domainsData?.domains.map((d) => (
                      <SelectItem key={d} value={d}>{d}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-2">
                <Label className="text-muted-foreground whitespace-nowrap">From:</Label>
                <Input 
                  type="date" 
                  value={startDate || ""} 
                  onChange={handleStartDateChange} 
                  className="h-9 w-32.5 sm:w-37.5 text-xs sm:text-sm"
                />
              </div>

              <div className="flex items-center gap-2">
                <Label className="text-muted-foreground whitespace-nowrap">To:</Label>
                <Input 
                  type="date" 
                  value={endDate || ""} 
                  onChange={handleEndDateChange} 
                  className="h-9 w-32.5 sm:w-37.5 text-xs sm:text-sm"
                />
              </div>

              <div className="flex items-center gap-2 ml-auto">
                <Label className="text-muted-foreground whitespace-nowrap">Per page:</Label>
                <Select value={size} onValueChange={handleSizeChange}>
                  <SelectTrigger className="w-20 h-9">
                    <SelectValue placeholder="20" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="20">20</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

          </CardContent>
        </Card>

        {/* RESULTS AREA */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse h-48 bg-muted/20" />
              ))}
            </div>
          ) : isError ? (
            <Card className="border-destructive/50 bg-destructive/10">
              <CardContent className="p-6 text-destructive text-center">
                An error occurred while searching. Please try again.
              </CardContent>
            </Card>
          ) : data?.articles.length === 0 ? (
            <Card>
              <CardContent className="flex items-center justify-center h-48 text-muted-foreground">
                No articles found matching your criteria.
              </CardContent>
            </Card>
          ) : data?.articles ? (
            <>
              <div className="flex justify-between items-end">
                <p className="text-sm text-muted-foreground font-medium">
                  Found {data.total_results.toLocaleString()} results
                  {query && ` for "${query}"`}
                </p>
              </div>
              
              {data.total_pages > 1 && (
                <PaginationControls className="border-b border-border mb-4" />
              )}
              
              <div className="grid grid-cols-1 gap-4">
                {data.articles.map((article) => (
                  <Card key={article.id} className="transition-all hover:shadow-md">
                    <CardContent className="p-5 flex flex-col gap-4">
                      
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex items-center gap-3 flex-wrap">
                          <Link 
                            to={`/article/${article.id}`} 
                            state={{ searchString: searchParams.toString() }}
                            className="font-semibold text-lg text-foreground hover:text-primary transition-colors leading-tight"
                          >
                            {article.title}
                          </Link>

                          {article.url && (
                            <a 
                              href={article.url} 
                              target="_blank" 
                              rel="noreferrer"
                              title="Read original article"
                              className="text-muted-foreground hover:text-primary transition-colors p-1"
                            >
                              <Globe className="h-4 w-4" />
                            </a>
                          )}
                        </div>
                        
                        {article.sentiment_score !== undefined && article.sentiment_score !== null && (
                          <Badge variant="outline" className={`shrink-0 ${getSentimentBadgeColor(article.sentiment_score)}`}>
                            {article.sentiment_score > 0 ? '+' : ''}{article.sentiment_score.toFixed(2)}
                          </Badge>
                        )}
                      </div>

                      {(article.snippets?.most_positive || article.snippets?.most_negative) && (
                        <div className="flex flex-col gap-2 rounded-md bg-muted/30 p-3 border border-border/50">
                          {article.snippets.most_positive && (
                            <div className="flex gap-2 items-start text-sm">
                              <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
                              <span className="text-muted-foreground italic">"{article.snippets.most_positive}"</span>
                            </div>
                          )}
                          {article.snippets.most_negative && (
                            <div className="flex gap-2 items-start text-sm">
                              <TrendingDown className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                              <span className="text-muted-foreground italic">"{article.snippets.most_negative}"</span>
                            </div>
                          )}
                        </div>
                      )}

                      <div className="flex items-center gap-4 mt-auto pt-2 text-xs text-muted-foreground font-medium">
                        <span className="flex items-center gap-1.5 bg-secondary px-2 py-1 rounded-md text-secondary-foreground">
                          {article.domain}
                        </span>
                        {article.seendate && (
                          <span className="flex items-center gap-1.5">
                            <Calendar className="h-3.5 w-3.5" />
                            {new Date(article.seendate).toLocaleDateString(undefined, { 
                              month: 'short', day: 'numeric', year: 'numeric' 
                            })}
                          </span>
                        )}
                        {article.sourcecountry && article.sourcecountry !== "Unknown" && (
                          <span className="flex items-center gap-1.5 border-l border-border pl-4">
                            {article.sourcecountry}
                          </span>
                        )}
                      </div>
                      
                    </CardContent>
                  </Card>
                ))}
              </div>

              {data.total_pages > 1 && (
                <PaginationControls className="border-t border-border mt-4" />
              )}
            </>
          ) : null}
        </div>

      </div>
    </div>
  )
}