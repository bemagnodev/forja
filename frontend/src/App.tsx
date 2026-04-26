import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Queue } from "./pages/Queue";

function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-[#050505] text-foreground w-full">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Queue />} />
            {/* Outras rotas entrarão aqui depois */}
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
