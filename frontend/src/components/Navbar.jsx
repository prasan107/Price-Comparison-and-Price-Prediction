import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm">
      <Link to="/" className="text-xl font-semibold text-blue-600 tracking-tight">
        PriceEngine
      </Link>
      <div className="flex gap-6 text-sm font-medium text-gray-600">
        <Link to="/"       className="hover:text-blue-600 transition-colors">Search</Link>
        <Link to="/alerts" className="hover:text-blue-600 transition-colors">My Alerts</Link>
      </div>
    </nav>
  );
}
