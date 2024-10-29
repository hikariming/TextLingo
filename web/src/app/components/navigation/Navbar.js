import { Bars3Icon, BookOpenIcon, DocumentTextIcon, AcademicCapIcon } from '@heroicons/react/24/outline'
import LanguageSwitcher from '../LanguageSwitcher'
import { useTranslations } from 'next-intl'

export default function Navbar() {
  const t = useTranslations('app')

  const navigation = [
    { name: t('nav.library'), href: '/', icon: BookOpenIcon },
    { name: t('nav.words'), href: '/words', icon: DocumentTextIcon },
    { name: t('nav.knowledge'), href: '/knowledge', icon: AcademicCapIcon },
  ];

  return (
    <header className="relative w-full bg-neutral-100">
      <nav className="mx-auto flex max-w-5xl items-center justify-between p-2 lg:px-8">
        {/* Logo */}
        <div className="flex lg:flex-1">
          <a href="#" className="-m-1.5 p-1.5">
            <span className="sr-only">{t('nav.logoAlt')}</span>
            <img
              alt=""
              src="/images/logo.svg"
              className="h-12 w-auto"
            />
          </a>
        </div>

        {/* Mobile menu button */}
        <div className="flex lg:hidden">
          <button
            type="button"
            className="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-gray-700"
          >
            <span className="sr-only">{t('nav.openMenu')}</span>
            <Bars3Icon className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>

        {/* Navigation items */}
        <div className="hidden lg:flex lg:gap-x-12">
          {navigation.map((item) => (
            <a
              key={item.name}
              href={item.href}
              className="text-sm font-semibold leading-6 text-gray-900 hover:text-gray-600 flex items-center gap-2"
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </a>
          ))}
        </div>

        {/* Language switcher */}
        <div className="hidden lg:flex lg:flex-1 lg:justify-end">
          <LanguageSwitcher />
        </div>
      </nav>
      <div className="absolute bottom-0 w-full h-px bg-gradient-to-r from-neutral-200 via-neutral-300 to-neutral-200"></div>
    </header>
  )
}