import { useState } from 'react'
import { useSentimentTrend, useTopEntities, useDomains } from './hooks/useApi'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export default function App() {
  const [interval, setIntervalState] = useState<string>('day')
  const [domain, setDomain] = useState<string>('')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')

  const { data: domainsData } = useDomains()

  const { data: trendData, isLoading: trendLoading } = useSentimentTrend(
    interval,
    domain || undefined, 
    startDate || undefined,
    endDate || undefined
  )

  const { data: entitiesData, isLoading: entitiesLoading } = useTopEntities(
    domain || undefined,
    5,
    startDate || undefined,
    endDate || undefined
  )

  const handleReset = () => {
    setIntervalState('day')
    setDomain('')
    setStartDate('')
    setEndDate('')
  }

  return (
    <div className="min-h-screen bg-background p-4 md:p-8 font-sans text-foreground">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* HEADER */}
        <header className="pb-4 border-b border-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Macro Analytics</h1>
            <p className="text-muted-foreground mt-1">Entity and sentiment overview</p>
          </div>
          {(domain || startDate || endDate || interval !== 'day') && (
            <Button variant="outline" size="sm" onClick={handleReset}>
              Clear Filters
            </Button>
          )}
        </header>

        {/* FILTER BAR */}
        <Card className="bg-card">
          <CardContent className="p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
            
            {/* Interval Selection */}
            <div className="flex flex-col gap-2">
              <Label>Aggregation Interval</Label>
              <Select value={interval} onValueChange={(val) => setIntervalState(val ?? 'day')}>
                <SelectTrigger>
                  <SelectValue placeholder="Select interval" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="day">Day</SelectItem>
                  <SelectItem value="week">Week</SelectItem>
                  <SelectItem value="month">Month</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Domain Selection */}
            <div className="flex flex-col gap-2">
              <Label>News Domain</Label>
              <Select 
                value={domain || "all"} 
                onValueChange={(val) => setDomain(val === "all" || val === null ? "" : val)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a domain" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Domains</SelectItem>
                  {domainsData?.domains.map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Start Date Selection */}
            <div className="flex flex-col gap-2">
              <Label>Start Date</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            {/* End Date Selection */}
            <div className="flex flex-col gap-2">
              <Label>End Date</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>

          </CardContent>
        </Card>

        {/* TRENDLINE CARD */}
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Trend</CardTitle>
            <CardDescription>
              Average sentiment aggregated by {interval} {domain && `for ${domain}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {trendLoading ? (
              <div className="h-64 flex items-center justify-center text-muted-foreground animate-pulse">Loading chart...</div>
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart 
                    data={trendData?.trends} 
                    margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid 
                      strokeDasharray="3 3" 
                      vertical={false} 
                      stroke="var(--border)" 
                    />
                    <XAxis 
                      dataKey="date" 
                      stroke="var(--muted-foreground)" 
                      fontSize={12} 
                      tickMargin={10} 
                      interval="equidistantPreserveStart"
                    />
                    <YAxis 
                      domain={[-1, 1]} 
                      stroke="var(--muted-foreground)" 
                      fontSize={12} 
                    />
                    <Tooltip 
                      contentStyle={{ 
                        borderRadius: 'var(--radius)',
                        border: '1px solid var(--border)', 
                        backgroundColor: 'var(--background)',
                        color: 'var(--foreground)',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' 
                      }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="avg_sentiment" 
                      stroke="var(--chart-2)" 
                      strokeWidth={3} 
                      dot={{ r: 4, fill: 'var(--chart-2)' }} 
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ENTITIES GRID */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Positive Entities Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-emerald-600 dark:text-emerald-400">Top Positive Entities</CardTitle>
              <CardDescription>{domain && `for ${domain}`}</CardDescription>
            </CardHeader>
            <CardContent className="p-0 sm:p-6 sm:pt-0">
              {entitiesLoading ? (
                <p className="p-6 text-muted-foreground animate-pulse">Loading entities...</p>
              ) : entitiesData?.most_positive.length === 0 ? (
                <p className="p-6 text-muted-foreground text-sm">No positive entities found.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Entity</TableHead>
                      <TableHead className="text-right">Mentions</TableHead>
                      <TableHead className="text-right">Avg</TableHead>
                      <TableHead className="text-right">Sum</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entitiesData?.most_positive.map((item, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">
                          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
                            {item.entity}
                            <Badge variant="secondary" className="w-fit text-[10px] sm:text-xs">
                              {item.type}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">{item.mention_count}</TableCell>
                        <TableCell className="text-right text-emerald-600 dark:text-emerald-400">+{item.avg_sentiment.toFixed(2)}</TableCell>
                        <TableCell className="text-right text-emerald-600 dark:text-emerald-400 font-semibold">+{item.sum_sentiment.toFixed(2)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Negative Entities Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-destructive">Top Negative Entities</CardTitle>
              <CardDescription>{domain && `for ${domain}`}</CardDescription>
            </CardHeader>
            <CardContent className="p-0 sm:p-6 sm:pt-0">
              {entitiesLoading ? (
                <p className="p-6 text-muted-foreground animate-pulse">Loading entities...</p>
              ) : entitiesData?.most_negative.length === 0 ? (
                <p className="p-6 text-muted-foreground text-sm">No negative entities found.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Entity</TableHead>
                      <TableHead className="text-right">Mentions</TableHead>
                      <TableHead className="text-right">Avg</TableHead>
                      <TableHead className="text-right">Sum</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entitiesData?.most_negative.map((item, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">
                          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
                            {item.entity}
                            <Badge variant="secondary" className="w-fit text-[10px] sm:text-xs">
                              {item.type}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">{item.mention_count}</TableCell>
                        <TableCell className="text-right text-destructive">{item.avg_sentiment.toFixed(2)}</TableCell>
                        <TableCell className="text-right text-destructive font-semibold">{item.sum_sentiment.toFixed(2)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

        </section>
      </div>
    </div>
  )
}