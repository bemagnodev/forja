import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Queue } from "./pages/Queue";

import { TooltipProvider } from "@/components/ui/tooltip";

function App() {
  return (
    <TooltipProvider delayDuration={150}>
      <Router>
      <div className="flex h-screen overflow-hidden bg-[#050505] text-foreground w-full">
        <Sidebar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <Routes>
            <Route path="/" element={<Queue />} />
            {/* Outras rotas entrarão aqui depois */}
          </Routes>
        </main>
      </div>
      </Router>
    </TooltipProvider>
  );
}

export default App;
