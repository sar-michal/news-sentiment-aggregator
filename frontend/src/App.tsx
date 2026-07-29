import { Routes, Route } from "react-router"
import Layout from "./components/Layout"
import MacroAnalytics from "./pages/MacroAnalytics"
import ArticleSearch from "./pages/ArticleSearch"

export default function App() {
  return (
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<MacroAnalytics />} />
          <Route path="search" element={<ArticleSearch />} />
        </Route>
      </Routes>
  )
}