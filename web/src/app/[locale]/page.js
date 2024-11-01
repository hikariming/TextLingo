import Navbar from '../components/navigation/Navbar'
import MaterialCards from '../components/MaterialCards'

export default async function LandingPage({ params: { locale } }) {
  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar />
      <main className="container mx-auto px-4 pt-20">
        <div className="grid grid-cols-12 gap-6">
          
          
          {/* 主要内容区域 */}
          <div className="col-span-10">
            <MaterialCards />
          </div>
        </div>
      </main>
    </div>
  )
}
