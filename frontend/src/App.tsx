import { useState, useEffect } from 'react'
import './App.css'
import { Anime, FilterState } from './types'
import { getLocaleDisplayName } from './utils/locales'
import {
  Header,
  SearchBar,
  FilterControls,
  Pagination,
  AnimeCard
} from './components'

function App() {
  const [anime, setAnime] = useState<Anime[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [itemsPerPage, setItemsPerPage] = useState<number>(16)
  const [dataTimestamp, setDataTimestamp] = useState<string>('')
  const [filter, setFilter] = useState<FilterState>({
    mature: 'default',
    dubbed: 'default',
    subbed: 'default',
    audioLocales: [],
    requireCompleteDubs: false,
    minRating: 0,
    contentDescriptors: {},
    genres: {},
    tags: {},
    status: {},
    studios: {},
    sortBy: 'alphabetical',
    sortDirection: 'asc'
  })

  const clearFilters = () => {
    setFilter({
      mature: 'default',
      dubbed: 'default',
      subbed: 'default',
      audioLocales: [],
      requireCompleteDubs: false,
      minRating: 0,
      contentDescriptors: {},
      genres: {},
      tags: {},
      status: {},
      studios: {},
      sortBy: 'alphabetical',
      sortDirection: 'asc'
    })
    setSearchTerm('')
  }

  useEffect(() => {
    // Add cache-busting parameter to force fetch of latest version
    const cacheBuster = import.meta.env.DEV
      ? `?v=${Date.now()}`
      : `?v=${import.meta.env.VITE_BUILD_TIME || Date.now()}`

    const animeJsonUrl = `${import.meta.env.BASE_URL}anime.json`

    // Fetch anime data
    fetch(`${animeJsonUrl}${cacheBuster}`)
      .then(res => res.json())
      .then(data => {
        setAnime(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Error loading anime:', err)
        setLoading(false)
      })

    // Fetch file timestamp
    fetch(animeJsonUrl, { method: 'HEAD' })
      .then(res => {
        const lastModified = res.headers.get('Last-Modified')
        if (lastModified) {
          const date = new Date(lastModified)
          setDataTimestamp(date.toLocaleString())
        }
      })
      .catch(err => {
        console.error('Error fetching timestamp:', err)
      })
  }, [])

  // Extract unique genres, content descriptors, tags, statuses, and studios from loaded data
  const availableGenres = Array.from(
    new Set(
      anime.flatMap(item => item.anilist?.genres || [])
    )
  ).sort()

  const availableContentDescriptors = Array.from(
    new Set(
      anime.flatMap(item => item.series_metadata?.content_descriptors || [])
    )
  ).sort()

  const availableTags = Array.from(
    new Set(
      anime.flatMap(item => item.anilist?.tags || [])
    )
  ).sort()

  const availableStatuses = Array.from(
    new Set(
      anime.map(item => item.anilist?.status).filter(Boolean) as string[]
    )
  ).sort()

  const availableStudios = Array.from(
    new Set(
      anime.flatMap(item => item.anilist?.studios || [])
    )
  ).sort()

  const availableAudioLocales = Array.from(
    new Set(
      anime
        .flatMap(item => item.series_metadata?.audio_locales || [])
        .filter(locale => locale && locale !== 'ja-JP')
    )
  ).sort((a, b) => getLocaleDisplayName(a).localeCompare(getLocaleDisplayName(b)))

  const hasAudioCoverageData = anime.some(item =>
    Boolean(item.series_metadata?.complete_audio_locales?.length) ||
    Boolean(item.series_metadata?.audio_locale_coverage && Object.keys(item.series_metadata.audio_locale_coverage).length > 0)
  )

  const filteredAnime = anime.filter(item => {
    const matchesSearch = item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.description.toLowerCase().includes(searchTerm.toLowerCase())

    // Tri-state filter logic: default = any, include = must have, exclude = must not have
    const matchesMature = filter.mature === 'default' ||
                         (filter.mature === 'include' && item.series_metadata?.is_mature) ||
                         (filter.mature === 'exclude' && !item.series_metadata?.is_mature)

    const matchesDubbed = filter.dubbed === 'default' ||
                         (filter.dubbed === 'include' && item.series_metadata?.is_dubbed) ||
                         (filter.dubbed === 'exclude' && !item.series_metadata?.is_dubbed)

    const matchesSubbed = filter.subbed === 'default' ||
                         (filter.subbed === 'include' && item.series_metadata?.is_subbed) ||
                         (filter.subbed === 'exclude' && !item.series_metadata?.is_subbed)

    const matchesAudioLocales =
      filter.audioLocales.length === 0 ||
      (filter.requireCompleteDubs
        ? filter.audioLocales.some(locale => item.series_metadata?.complete_audio_locales?.includes(locale))
        : filter.audioLocales.some(locale => item.series_metadata?.audio_locales?.includes(locale)))

    const matchesRating = parseFloat(item.rating?.average || '0') >= filter.minRating

    // Content descriptor filters
    const matchesContentDescriptors = Object.entries(filter.contentDescriptors).every(([descriptor, filterValue]) => {
      if (filterValue === 'default') return true
      const hasDescriptor = item.series_metadata?.content_descriptors?.includes(descriptor) || false
      if (filterValue === 'include') return hasDescriptor
      if (filterValue === 'exclude') return !hasDescriptor
      return true
    })

    // Genre filters
    const matchesGenres = Object.entries(filter.genres).every(([genre, filterValue]) => {
      if (filterValue === 'default') return true
      const hasGenre = item.anilist?.genres?.includes(genre) || false
      if (filterValue === 'include') return hasGenre
      if (filterValue === 'exclude') return !hasGenre
      return true
    })

    // Tag filters
    const matchesTags = Object.entries(filter.tags).every(([tag, filterValue]) => {
      if (filterValue === 'default') return true
      const hasTag = item.anilist?.tags?.includes(tag) || false
      if (filterValue === 'include') return hasTag
      if (filterValue === 'exclude') return !hasTag
      return true
    })

    // Status filters
    const matchesStatus = Object.entries(filter.status).every(([status, filterValue]) => {
      if (filterValue === 'default') return true
      const hasStatus = item.anilist?.status === status
      if (filterValue === 'include') return hasStatus
      if (filterValue === 'exclude') return !hasStatus
      return true
    })

    // Studio filters
    const matchesStudios = Object.entries(filter.studios).every(([studio, filterValue]) => {
      if (filterValue === 'default') return true
      const hasStudio = item.anilist?.studios?.includes(studio) || false
      if (filterValue === 'include') return hasStudio
      if (filterValue === 'exclude') return !hasStudio
      return true
    })

    return matchesSearch && matchesMature && matchesDubbed && matchesSubbed && matchesAudioLocales && matchesRating && matchesContentDescriptors && matchesGenres && matchesTags && matchesStatus && matchesStudios
  }).sort((a, b) => {
    const direction = filter.sortDirection === 'asc' ? 1 : -1
    
    let comparison = 0
    switch (filter.sortBy) {
      case 'alphabetical':
        comparison = a.title.localeCompare(b.title)
        break
      case 'year':
        const yearA = a.series_metadata?.series_launch_year || 0
        const yearB = b.series_metadata?.series_launch_year || 0
        comparison = yearA - yearB
        break
      case 'rating':
        const ratingA = parseFloat(a.rating?.average || '0')
        const ratingB = parseFloat(b.rating?.average || '0')
        comparison = ratingA - ratingB
        break
      case 'anilist_rating':
        const anilistA = a.anilist?.average_score || 0
        const anilistB = b.anilist?.average_score || 0
        comparison = anilistA - anilistB
        break
    }

    // If values are equal (or for alphabetical), sort by title ascending (always)
    if (comparison === 0) {
      return a.title.localeCompare(b.title)
    }

    return comparison * direction
  })

  const totalPages = Math.max(1, Math.ceil(filteredAnime.length / itemsPerPage))
  const startIndex = (currentPage - 1) * itemsPerPage
  const paginatedAnime = filteredAnime.slice(startIndex, startIndex + itemsPerPage)
  const selectedAudioLocaleLabels = filter.audioLocales.map(locale => ({
    locale,
    label: getLocaleDisplayName(locale)
  }))
  const activeDubModeLabel = filter.requireCompleteDubs ? 'complete only' : null

  const clearAudioLocale = (locale: string) => {
    const nextLocales = filter.audioLocales.filter(value => value !== locale)
    setFilter({
      ...filter,
      audioLocales: nextLocales,
      requireCompleteDubs: nextLocales.length > 0 ? filter.requireCompleteDubs : false
    })
  }

  const clearAudioLocales = () => {
    setFilter({ ...filter, audioLocales: [], requireCompleteDubs: false })
  }

  // Reset to page 1 when filters, items per page, or sorting change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm, filter, itemsPerPage])

  if (loading) {
    return <div className="loading">Loading anime...</div>
  }

  return (
    <div className="container">
      <Header totalCount={anime.length} dataTimestamp={dataTimestamp} />

      <div className="controls">
        <SearchBar value={searchTerm} onChange={setSearchTerm} />
        <FilterControls
          filter={filter}
          onFilterChange={setFilter}
          itemsPerPage={itemsPerPage}
          onItemsPerPageChange={setItemsPerPage}
          onClearFilters={clearFilters}
          availableGenres={availableGenres}
          availableContentDescriptors={availableContentDescriptors}
          availableTags={availableTags}
          availableStatuses={availableStatuses}
          availableStudios={availableStudios}
          availableAudioLocales={availableAudioLocales}
          hasAudioCoverageData={hasAudioCoverageData}
          anime={anime}
        />
      </div>

      {(selectedAudioLocaleLabels.length > 0 || activeDubModeLabel) && (
        <div className="active-filter-summary" aria-label="Active dub language filters">
          <span className="active-filter-summary-label">Dubbed in:</span>
          {activeDubModeLabel && (
            <span className="active-filter-chip active-filter-chip--mode">Complete selected dubs</span>
          )}
          {selectedAudioLocaleLabels.map(({ locale, label }) => (
            <button
              key={locale}
              type="button"
              className="active-filter-chip"
              onClick={() => clearAudioLocale(locale)}
              aria-label={`Remove ${label} dub filter`}
            >
              {label}
              <span aria-hidden="true">×</span>
            </button>
          ))}
          <button
            type="button"
            className="active-filter-clear"
            onClick={clearAudioLocales}
          >
            Clear dub filters
          </button>
        </div>
      )}

      <p className="results-count">
        {filteredAnime.length} results (Page {currentPage} of {totalPages})
      </p>

      {filteredAnime.length > 0 ? (
        <div className="anime-grid">
          {paginatedAnime.map(item => (
            <AnimeCard
              key={item.id}
              anime={item}
              onFilterChange={setFilter}
              currentFilter={filter}
            />
          ))}
        </div>
      ) : (
        <div className="empty-results">
          <h2>No titles match these filters.</h2>
          {filter.audioLocales.length > 0 ? (
            <>
              <p>
                {filter.requireCompleteDubs
                  ? 'Try turning off complete-dub filtering, choosing another language, or clearing dub filters.'
                  : 'Try removing a dubbed language filter or choosing another language.'}
              </p>
              <button type="button" onClick={clearAudioLocales} className="clear-selected-btn">
                Clear dub filters
              </button>
            </>
          ) : (
            <p>Try clearing some filters or changing your search.</p>
          )}
        </div>
      )}

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={setCurrentPage}
      />
    </div>
  )
}

export default App
