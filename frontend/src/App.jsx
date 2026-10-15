import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import SearchPage  from "./pages/SearchPage";
import ProductPage from "./pages/ProductPage";
import AlertsPage  from "./pages/AlertsPage";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/"              element={<SearchPage />} />
          <Route path="/product/:id"   element={<ProductPage />} />
          <Route path="/alerts"        element={<AlertsPage />} />
        </Routes>
      </main>
    </div>
  );
}
