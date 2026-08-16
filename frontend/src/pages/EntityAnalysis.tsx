import { useEffect, useState } from "react"
import { useSearchParams } from "react-router"
import { useEntityAnalysis, useEntitySuggest } from "../hooks/useApi"
import { getSentimentTextColor } from "@/lib/sentiment"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Search, Globe, Activity } from "lucide-react"

export default function EntityAnalysis() {
  const [searchParams, setSearchParams] = useSearchParams()

  const entityQuery = searchParams.get("entity") || ""
  const startDate = searchParams.get("start_date") || ""
  const endDate = searchParams.get("end_date") || ""

  const [inputVal, setInputVal] = useState(entityQuery)
  const [debouncedInput, setDebouncedInput] = useState(inputVal)
  const [showSuggestions, setShowSuggestions] = useState(false)

  const { data: analysisData, isLoading, isError } = useEntityAnalysis(entityQuery, startDate || undefined, endDate || undefined)
  
  const { data: suggestions } = useEntitySuggest(debouncedInput)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedInput(inputVal), 300)
    return () => clearTimeout(timer)
  }, [inputVal])

  useEffect(() => {
    setInputVal(entityQuery)
  }, [entityQuery])

  const handleSearch = (e?: React.SyntheticEvent) => {
    if (e) e.preventDefault()
    if (!inputVal.trim()) return
    const newParams = new URLSearchParams(searchParams)
    newParams.set("entity", inputVal.trim())
    setSearchParams(newParams)
    setShowSuggestions(false)
  }

  const handleSuggestionClick = (suggestion: string) => {
    setInputVal(suggestion)
    setShowSuggestions(false)
    const newParams = new URLSearchParams(searchParams)
    newParams.set("entity", suggestion)
    setSearchParams(newParams)
  }

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newParams = new URLSearchParams(searchParams)
    if (e.target.value) newParams.set("start_date", e.target.value)
    else newParams.delete("start_date")
    setSearchParams(newParams)
  }

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newParams = new URLSearchParams(searchParams)
    if (e.target.value) newParams.set("end_date", e.target.value)
    else newParams.delete("end_date")
    setSearchParams(newParams)
  }

  return (
    <div className="p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        
        <header className="pb-4 border-b border-border">
          <h1 className="text-3xl font-bold tracking-tight">Entity Analysis</h1>
          <p className="text-muted-foreground mt-1">Cross-examination of sentiment and publication volume for any named entity.</p>
        </header>

        <Card className="bg-card overflow-visible">
          <CardContent className="p-4 sm:p-6 space-y-4 overflow-visible">
            <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4">
              
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Enter entity name (e.g., Apple, Elon Musk, Congress)..." 
                  className="pl-9 w-full"
                  value={inputVal}
                  onChange={(e) => {
                    setInputVal(e.target.value)
                    setShowSuggestions(true)
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                />
                
                {showSuggestions && suggestions?.suggestions && suggestions.suggestions.length > 0 && (
                  <div className="absolute top-full left-0 mt-1 w-full bg-popover border border-border rounded-md shadow-lg z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-100">
                    {suggestions.suggestions.map((item) => (
                      <button
                        key={item.name}
                        type="button"
                        onClick={() => handleSuggestionClick(item.name)}
                        className="w-full text-left px-4 py-2.5 text-sm hover:bg-muted focus:bg-muted focus:outline-none transition-colors"
                      >
                        {item.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              
              <Button type="submit" className="sm:w-32" disabled={isLoading || !inputVal.trim()}>
                {isLoading ? "Analyzing..." : "Analyze"}
              </Button>
            </form>

            <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-border/50">
              <div className="flex items-center gap-2">
                <Label className="text-muted-foreground whitespace-nowrap">From:</Label>
                <Input 
                  type="date" 
                  value={startDate} 
                  onChange={handleStartDateChange} 
                  className="h-9 w-37 sm:w-38 text-xs sm:text-sm"
                />
              </div>

              <div className="flex items-center gap-2">
                <Label className="text-muted-foreground whitespace-nowrap">To:</Label>
                <Input 
                  type="date" 
                  value={endDate} 
                  onChange={handleEndDateChange} 
                  className="h-9 w-37 sm:w-38 text-xs sm:text-sm"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* RESULTS SECTION */}
        {!entityQuery ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center h-48 text-muted-foreground gap-2">
              <Activity className="h-8 w-8 text-muted-foreground/50" />
              <p>Type an entity name above and click Analyze to view cross-domain stats.</p>
            </CardContent>
          </Card>
        ) : isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="h-32 animate-pulse bg-muted/20" />
            ))}
          </div>
        ) : isError ? (
          <Card className="border-destructive/50 bg-destructive/10">
            <CardContent className="p-6 text-destructive text-center">
              Failed to retrieve entity analysis data. Please try again.
            </CardContent>
          </Card>
        ) : analysisData && analysisData.total_mentions === 0 ? (
          <Card>
            <CardContent className="flex items-center justify-center h-48 text-muted-foreground">
              No mentions found for "{entityQuery}" within the selected date range.
            </CardContent>
          </Card>
        ) : analysisData ? (
          <div className="space-y-6">
            
            <div className="flex items-center gap-3 pt-2">
              <h2 className="text-2xl font-bold tracking-tight">{analysisData.entity}</h2>
            </div>

            {/* OVERALL SUMMARY METRIC CARDS */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs uppercase font-semibold">Total Mentions</CardDescription>
                  <CardTitle className="text-3xl font-bold">{analysisData.total_mentions.toLocaleString()}</CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  Number of articles across {analysisData.domains.length} news sources.
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs uppercase font-semibold">Overall Average Sentiment</CardDescription>
                  <CardTitle className="text-3xl font-normal">
                    <span className={getSentimentTextColor(analysisData.overall_avg_sentiment)}>
                      {analysisData.overall_avg_sentiment > 0 ? '+' : ''}{analysisData.overall_avg_sentiment.toFixed(2)}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  Normalized scale between -1.0 and +1.0.
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs uppercase font-semibold">Cumulative Sentiment Sum</CardDescription>
                  <CardTitle className="text-3xl font-bold">
                    <span className={getSentimentTextColor(analysisData.overall_avg_sentiment)}>
                      {analysisData.overall_sum_sentiment > 0 ? '+' : ''}{analysisData.overall_sum_sentiment.toFixed(2)}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  Aggregate sentiment of all occurrences.
                </CardContent>
              </Card>
            </div>

            {/* DOMAIN BREAKDOWN TABLE */}
            <Card>
              <CardHeader>
                <CardTitle>Domain Breakdown</CardTitle>
                <CardDescription>
                  Comparison of mention frequency and sentiment across news domains.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0 sm:p-6 sm:pt-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>News Source Domain</TableHead>
                      <TableHead className="text-center">Mentions</TableHead>
                      <TableHead className="text-right">Avg Sentiment</TableHead>
                      <TableHead className="text-right">Sum Sentiment</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analysisData.domains.map((dom: any) => (
                      <TableRow key={dom.domain}>
                        <TableCell className="font-medium flex items-center gap-2">
                          <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
                          {dom.domain}
                        </TableCell>
                        <TableCell className="text-center font-semibold">
                          {dom.mention_count.toLocaleString()}
                        </TableCell>
                        <TableCell className={`text-right ${getSentimentTextColor(dom.avg_sentiment)}`}>
                          {dom.avg_sentiment > 0 ? '+' : ''}{dom.avg_sentiment.toFixed(2)}
                        </TableCell>
                        <TableCell className={`text-right font-bold ${getSentimentTextColor(dom.avg_sentiment)}`}>
                          {dom.sum_sentiment > 0 ? '+' : ''}{dom.sum_sentiment.toFixed(2)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

          </div>
        ) : null}

      </div>
    </div>
  )
}