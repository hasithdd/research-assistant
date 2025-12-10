import { Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import PaperPage from './pages/PaperPage';
import { Header } from './components/layout/Header';

export default function App() {
  return (
    <div className="min-h-screen bg-surface text-ink">
      <Header />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/paper/:paperId" element={<PaperPage />} />
      </Routes>
    </div>
  );
}
