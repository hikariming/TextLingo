import Navbar from '../components/navigation/Navbar'
import KnowledgeCards from '../components/KnowledgeCards'

export default async function LandingPage({ params: { locale } }) {
  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar />
      <main className="container mx-auto px-4">
        <div className=" mx-auto">
          <KnowledgeCards />
        </div>
      </main>
    </div>
  )
}
