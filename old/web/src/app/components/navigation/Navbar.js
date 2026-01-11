import { useLocale } from 'next-intl'
import NavbarClient from './NavbarClient'

export default function Navbar() {
  const locale = useLocale()
  
  return (
    <header className="fixed top-0 z-50 w-full h-16 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <NavbarClient currentLocale={locale} />
    </header>
  )
}