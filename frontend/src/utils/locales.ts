const LOCALE_LABELS: Record<string, { display: string; short: string }> = {
  'en-US': { display: 'English', short: 'EN' },
  'es-419': { display: 'Spanish (Latin America)', short: 'ES-LA' },
  'es-ES': { display: 'Spanish (Spain)', short: 'ES' },
  'pt-BR': { display: 'Portuguese (Brazil)', short: 'PT-BR' },
  'de-DE': { display: 'German', short: 'DE' },
  'fr-FR': { display: 'French', short: 'FR' },
  'hi-IN': { display: 'Hindi', short: 'HI' },
  'ta-IN': { display: 'Tamil', short: 'TA' },
  'te-IN': { display: 'Telugu', short: 'TE' },
  'it-IT': { display: 'Italian', short: 'IT' },
  'ko-KR': { display: 'Korean', short: 'KO' },
  'zh-CN': { display: 'Chinese (Simplified)', short: 'ZH-CN' },
  'zh-TW': { display: 'Chinese (Traditional)', short: 'ZH-TW' },
  'pl-PL': { display: 'Polish', short: 'PL' },
  'tr-TR': { display: 'Turkish', short: 'TR' },
  'ru-RU': { display: 'Russian', short: 'RU' },
  'ja-JP': { display: 'Japanese', short: 'JA' }
}

const REGION_OVERRIDES: Record<string, string> = {
  '419': 'Latin America',
  US: 'United States',
  BR: 'Brazil',
  DE: 'Germany',
  FR: 'France',
  IN: 'India',
  IT: 'Italy',
  KR: 'Korea',
  CN: 'China',
  TW: 'Taiwan',
  PL: 'Poland',
  TR: 'Turkey',
  RU: 'Russia',
  ES: 'Spain',
  JP: 'Japan'
}

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  es: 'Spanish',
  pt: 'Portuguese',
  de: 'German',
  fr: 'French',
  hi: 'Hindi',
  ta: 'Tamil',
  te: 'Telugu',
  it: 'Italian',
  ko: 'Korean',
  zh: 'Chinese',
  pl: 'Polish',
  tr: 'Turkish',
  ru: 'Russian',
  ja: 'Japanese'
}

const formatFallbackLocale = (locale: string) => {
  const [language = locale, region] = locale.split('-')
  const languageName = LANGUAGE_NAMES[language.toLowerCase()] || language.charAt(0).toUpperCase() + language.slice(1).toLowerCase()

  if (!region) {
    return languageName
  }

  const normalizedRegion = region.toUpperCase()
  const regionName = REGION_OVERRIDES[normalizedRegion] || normalizedRegion
  return `${languageName} (${regionName})`
}

export const getLocaleDisplayName = (locale: string) => {
  return LOCALE_LABELS[locale]?.display || formatFallbackLocale(locale)
}

export const getLocaleShortLabel = (locale: string) => {
  return LOCALE_LABELS[locale]?.short || locale.toUpperCase()
}
