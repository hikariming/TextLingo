'use client'

import { Bars3Icon, BookOpenIcon, DocumentTextIcon, AcademicCapIcon, Cog6ToothIcon } from '@heroicons/react/24/outline'
import LanguageSwitcher from '../LanguageSwitcher'
import { useTranslations, useLocale } from 'next-intl'
import { usePathname } from 'next/navigation'
import Link from 'next/link'

export default function NavbarClient({ currentLocale }) {
  const t = useTranslations('app')
  const locale = useLocale()
  const pathname = usePathname()

  const navigation = [
    { name: t('nav.library'), href: `/${locale}/`, icon: BookOpenIcon },
    { name: t('nav.words'), href: `/${locale}/words`, icon: DocumentTextIcon },
    { name: t('nav.knowledge'), href: `/${locale}/knowledge`, icon: AcademicCapIcon },
    { name: t('nav.setting'), href: `/${locale}/setting`, icon: Cog6ToothIcon },
  ]

  const isActiveLink = (href) => {
    const currentPath = pathname.replace(new RegExp(`^/${currentLocale}`), '') || '/'
    const itemPath = href.replace(new RegExp(`^/${locale}`), '') || '/'
    return currentPath === itemPath
  }

  return (
    <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="flex h-16 justify-between">
        <div className="flex">
          <div className="flex flex-shrink-0 items-center">
            <Link href={`/${locale}/`} className="text-xl font-bold">
              TextLingo
            </Link>
          </div>
          <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                    isActiveLink(item.href)
                      ? 'border-b-2 border-primary text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Icon className="mr-1 h-5 w-5" />
                  {item.name}
                </Link>
              )
            })}
          </div>
        </div>
        <div className="flex items-center">
          <LanguageSwitcher />
        </div>
        <div className="flex items-center sm:hidden">
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-background hover:text-foreground focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary"
          >
            <span className="sr-only">Open main menu</span>
            <Bars3Icon className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>
      </div>
    </nav>
  )
}
