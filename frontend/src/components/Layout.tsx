import { Link, Outlet, useLocation } from "react-router"
import { BarChart3, Search, Activity } from "lucide-react"

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen text-foreground">
      <nav className="border-b border-border bg-card sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 md:px-8 flex h-14 items-center gap-6">
          <span className="font-bold tracking-tight mr-4">NewsSentiment</span>
          
          <Link 
            to="/" 
            className={`flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary ${
              location.pathname === "/" ? "text-primary" : "text-muted-foreground"
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            Macro Analytics
          </Link>

          <Link 
            to="/search" 
            className={`flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary ${
              location.pathname === "/search" ? "text-primary" : "text-muted-foreground"
            }`}
          >
            <Search className="h-4 w-4" />
            Article Search
          </Link>

          <Link 
            to="/entity-analysis" 
            className={`flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary ${
              location.pathname === "/entity-analysis" ? "text-primary" : "text-muted-foreground"
            }`}
          >
            <Activity className="h-4 w-4" />
            Entity Analysis
          </Link>
        </div>
      </nav>

      <main>
        <Outlet />
      </main>
    </div>
  )
}