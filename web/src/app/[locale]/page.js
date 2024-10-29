import { getTranslations } from 'next-intl/server'
import Navbar from '../components/navigation/Navbar'
import KnowledgeCards from '../components/KnowledgeCards'

export default async function LandingPage({ params: { locale } }) {
  const t = await getTranslations('Landing')

  return (
    <div className="min-h-screen bg-neutral-100">
      <Navbar t={t} />
      <main >
        <KnowledgeCards t={t} />
      </main>
    </div>
  )
}
