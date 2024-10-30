import { Bars3Icon, BookOpenIcon, DocumentTextIcon, AcademicCapIcon } from '@heroicons/react/24/outline'
import LanguageSwitcher from '../LanguageSwitcher'
import { useTranslations, useLocale } from 'next-intl'
import { headers } from 'next/headers'

export default function Navbar() {
  const t = useTranslations('app')
  const headersList = headers()
  const currentLocale = headersList.get('x-next-intl-locale')

  console.log(currentLocale)
  const locale = useLocale()

//   console.log('=== All Headers ===')
//   headersList.forEach((value, key) => {
//     console.log(`${key}: ${value}`)
//   })

//   console.log('=== Debug Info ===')
//   console.log('currentLocale:', currentLocale)
//   console.log('locale:', locale)

  const navigation = [
    { name: t('nav.library'), href: `/${locale}/`, icon: BookOpenIcon },
    { name: t('nav.words'), href: `/${locale}/words`, icon: DocumentTextIcon },
    { name: t('nav.knowledge'), href: `/${locale}/knowledge`, icon: AcademicCapIcon },
  ];

  const isActiveLink = (href) => {
    // 从 link header 获取当前路径
    const linkHeader = headersList.get('link') || ''
    const currentUrlMatch = linkHeader.match(/<([^>]+)>/)
    const currentFullUrl = currentUrlMatch ? currentUrlMatch[1] : ''
    const pathname = new URL(currentFullUrl).pathname
    
    // 添加调试日志
    console.log('当前完整路径:', pathname)
    console.log('当前语言:', currentLocale)
    console.log('目标链接:', href)
    
    // 移除开头的语言前缀，以便进行比较
    const currentPath = pathname.replace(new RegExp(`^/${currentLocale}`), '') || '/'
    const itemPath = href.replace(new RegExp(`^/${locale}`), '') || '/'
    
    console.log('比较路径:', { currentPath, itemPath })
    
    return currentPath === itemPath
  }

  return (
    <header className="relative w-full bg-slate-100">
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
              className={`text-sm font-semibold leading-6 flex items-center gap-2 px-4 py-2 rounded-full relative
                ${isActiveLink(item.href)
                  ? 'text-blue-600 hover:text-blue-500 bg-white shadow-md' 
                  : 'text-gray-900 hover:text-gray-600'
                }`}
            >
              <item.icon className={`h-5 w-5 ${isActiveLink(item.href) ? 'text-blue-600' : ''}`} />
              {item.name}
              {isActiveLink(item.href) && (
                <div className="absolute -bottom-[1px] left-2 right-2 h-[2px] bg-gradient-to-r from-blue-400/0 via-blue-400/70 to-blue-400/0"></div>
              )}
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