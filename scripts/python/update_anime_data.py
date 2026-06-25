#!/usr/bin/env python3
"""
Fetch anime data from Crunchyroll (anonymous API), enhance with AniList data, and track changes.
Designed to run in GitHub Actions.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from difflib import SequenceMatcher
import requests


def get_anonymous_token(max_retries: int = 3) -> str:
    """Get an anonymous access token from Crunchyroll with retry logic."""
    print("Getting anonymous access token from Crunchyroll...")

    # Crunchyroll's public OAuth client credentials for anonymous access
    auth_header = "Basic Y3Jfd2ViOg=="

    auth_url = "https://www.crunchyroll.com/auth/v1/token"

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.crunchyroll.com",
        "Referer": "https://www.crunchyroll.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    data = {
        "grant_type": "client_id"
    }

    for attempt in range(max_retries):
        try:
            # Add delay between retries (exponential backoff)
            if attempt > 0:
                delay = 2 ** attempt  # 2, 4, 8 seconds
                print(f"Retry attempt {attempt + 1}/{max_retries} after {delay}s delay...")
                time.sleep(delay)

            response = requests.post(auth_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                print("ERROR: No access token in response")
                continue

            print("✓ Got anonymous access token")
            return access_token

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"WARNING: 403 Forbidden (attempt {attempt + 1}/{max_retries})")
                print("This may indicate that Crunchyroll is blocking automated requests from this IP")
                if attempt == max_retries - 1:
                    print("\nERROR: Crunchyroll API is blocking requests after multiple retries.")
                    print("This is common with GitHub Actions. Consider:")
                    print("  1. Running the script manually and committing the data")
                    print("  2. Using a different hosting service for automation")
                    print("  3. Setting up a proxy or VPN")
                    sys.exit(1)
            else:
                print(f"ERROR: HTTP {e.response.status_code}: {e}")
                if attempt == max_retries - 1:
                    sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Request failed: {e}")
            if attempt == max_retries - 1:
                sys.exit(1)

    print("ERROR: Failed to get token after all retries")
    sys.exit(1)


def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def get_anilist_data_batch(titles: List[str]) -> Dict[str, Optional[Dict]]:
    """Query AniList API for multiple anime in a single request."""
    query_parts = []
    for i, title in enumerate(titles):
        alias = f"anime{i}"
        safe_title = title.replace('"', '\\"')
        query_parts.append(f'''
        {alias}: Page(page: 1, perPage: 3) {{
          media(search: "{safe_title}", type: ANIME, sort: SEARCH_MATCH) {{
            id
            idMal
            title {{
              romaji
              english
              native
            }}
            startDate {{
              year
              month
              day
            }}
            endDate {{
              year
              month
              day
            }}
            format
            status
            episodes
            duration
            genres
            tags {{
              name
              rank
              isMediaSpoiler
            }}
            popularity
            averageScore
            meanScore
            studios {{
              nodes {{
                name
                isAnimationStudio
              }}
            }}
            season
            seasonYear
          }}
        }}
        ''')

    query = "query {\n" + "\n".join(query_parts) + "\n}"
    results = {}

    try:
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': query},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json().get('data', {})

            for i, title in enumerate(titles):
                alias = f"anime{i}"
                media_list = data.get(alias, {}).get('media', [])

                if not media_list:
                    results[title] = None
                    continue

                # Find best match using fuzzy matching
                best_match = None
                best_score = 0.0

                for media in media_list:
                    anime_titles = [
                        media.get('title', {}).get('romaji'),
                        media.get('title', {}).get('english'),
                        media.get('title', {}).get('native')
                    ]

                    for anime_title in anime_titles:
                        if anime_title:
                            score = similarity(title, anime_title)
                            if score > best_score:
                                best_score = score
                                best_match = media

                # Only accept matches with similarity > 0.6
                if best_match and best_score > 0.6:
                    # Extract non-spoiler tags with rank >= 60
                    tags = best_match.get('tags', []) or []
                    filtered_tags = [
                        tag['name'] for tag in tags
                        if not tag.get('isMediaSpoiler', False) and tag.get('rank', 0) >= 60
                    ]

                    # Get animation studios only
                    studios = best_match.get('studios', {}).get('nodes', []) or []
                    animation_studios = [
                        studio['name'] for studio in studios
                        if studio.get('isAnimationStudio', False)
                    ]

                    matched_title = (
                        best_match.get('title', {}).get('english') or
                        best_match.get('title', {}).get('romaji')
                    )

                    results[title] = {
                        'anilist_id': best_match.get('id'),
                        'mal_id': best_match.get('idMal'),
                        'matched_title': matched_title,
                        'match_score': round(best_score, 3),
                        'start_date': best_match.get('startDate'),
                        'end_date': best_match.get('endDate'),
                        'format': best_match.get('format'),
                        'status': best_match.get('status'),
                        'episodes': best_match.get('episodes'),
                        'duration': best_match.get('duration'),
                        'genres': best_match.get('genres', []) or [],
                        'tags': filtered_tags,
                        'popularity': best_match.get('popularity'),
                        'average_score': best_match.get('averageScore'),
                        'mean_score': best_match.get('meanScore'),
                        'studios': animation_studios,
                        'season': best_match.get('season'),
                        'season_year': best_match.get('seasonYear'),
                    }
                else:
                    results[title] = None

        elif response.status_code == 429:
            print("  Rate limited, waiting 60s...")
            time.sleep(60)
            return get_anilist_data_batch(titles)
        else:
            print(f"  API error: {response.status_code}")
            return {title: None for title in titles}

    except Exception as e:
        print(f"  Error fetching batch: {e}")
        return {title: None for title in titles}

    return results


def validate_crunchyroll_format(item: Dict) -> bool:
    """Validate that a Crunchyroll item has the expected format."""
    required_fields = ['id', 'title', 'type', 'description']
    return all(field in item for field in required_fields)


def validate_anilist_format(item: Dict) -> bool:
    """Validate that an AniList item has the expected format."""
    if not item:
        return True  # None is acceptable for no match
    required_fields = ['anilist_id', 'matched_title', 'match_score']
    return all(field in item for field in required_fields)


def fetch_crunchyroll_anime(access_token: str) -> List[Dict]:
    """Fetch all anime series from Crunchyroll."""
    print("Fetching anime catalog from Crunchyroll...")

    url = "https://www.crunchyroll.com/content/v2/discover/browse"

    headers = crunchyroll_browser_headers(access_token)

    page_size = 100

    params = {
        "n": page_size,
        "type": "series",
        "locale": "en-US",
        "sort_by": "alphabetical",
        "ratings": "true",
        "preferred_audio_language": "ja-JP"
    }

    all_items = []

    try:
        total = None
        start = 0

        while total is None or start < total:
            page_params = {**params, "start": start}
            response = requests.get(url, headers=headers, params=page_params, timeout=60)
            response.raise_for_status()

            data = response.json()
            items = data.get("data", [])
            total = data.get("total", len(all_items) + len(items))

            if not items:
                break

            all_items.extend(items)
            print(f"  Fetched {len(all_items)} of {total} anime series")
            start += len(items)

            if len(items) < page_size:
                break

            time.sleep(0.2)

        # Validate format of first item
        if all_items and not validate_crunchyroll_format(all_items[0]):
            print("ERROR: Crunchyroll API format has changed!")
            print(f"Expected fields: id, title, type, description")
            print(f"Received fields: {list(all_items[0].keys())}")
            sys.exit(1)

        print(f"✓ Fetched {len(all_items)} of {total} anime series")
        return all_items

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch anime: {e}")
        sys.exit(1)


def crunchyroll_browser_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.crunchyroll.com/videos/alphabetical",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }


def extract_season_audio_locales(season: Dict) -> Set[str]:
    locales: Set[str] = set()

    for locale in season.get('audio_locales', []) or []:
        if locale:
            locales.add(locale)

    audio_locale = season.get('audio_locale')
    if audio_locale:
        locales.add(audio_locale)

    for version in season.get('versions', []) or []:
        version_locale = version.get('audio_locale')
        if version_locale:
            locales.add(version_locale)

    return locales


def fetch_series_audio_coverage(access_token: str, series_id: str, season_count: int, max_retries: int = 3) -> Optional[Dict]:
    if season_count <= 1:
        return None

    url = f"https://www.crunchyroll.com/content/v2/cms/series/{series_id}/seasons"
    headers = crunchyroll_browser_headers(access_token)
    params = {
        "locale": "en-US",
        "preferred_audio_language": "ja-JP",
        "n": 200
    }

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = 1.5 * attempt
                print(f"    Coverage retry {attempt + 1}/{max_retries} for {series_id} after {delay:.1f}s")
                time.sleep(delay)

            response = requests.get(url, headers=headers, params=params, timeout=45)

            if response.status_code == 429:
                print(f"    Coverage rate limited for {series_id} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None

            response.raise_for_status()
            data = response.json()
            seasons = data.get('data') or data.get('items') or data.get('seasons') or []

            if not seasons:
                print(f"    WARNING: No season coverage data returned for {series_id}")
                return None

            season_locale_sets = [extract_season_audio_locales(season) for season in seasons]

            if not season_locale_sets:
                print(f"    WARNING: No audio locale data found for {series_id}")
                return None

            seasons_total = len(season_locale_sets)
            all_locales = set().union(*season_locale_sets)
            coverage: Dict[str, Dict[str, object]] = {}
            complete_audio_locales = []

            for locale in sorted(all_locales):
                if locale == 'ja-JP':
                    continue
                seasons_with_locale = sum(1 for locales in season_locale_sets if locale in locales)
                complete = seasons_with_locale == seasons_total
                coverage[locale] = {
                    'complete': complete,
                    'seasons_with_locale': seasons_with_locale,
                    'seasons_total': seasons_total
                }
                if complete:
                    complete_audio_locales.append(locale)

            return {
                'complete_audio_locales': complete_audio_locales,
                'audio_locale_coverage': coverage,
                'seasons_total': seasons_total
            }

        except requests.exceptions.RequestException as e:
            print(f"    WARNING: Coverage fetch failed for {series_id} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None
        except Exception as e:
            print(f"    WARNING: Could not parse coverage for {series_id}: {e}")
            return None

    return None


def enrich_audio_coverage(anime_data: List[Dict], access_token: str) -> Dict[str, int]:
    print("\nEnriching audio coverage metadata...")

    derived_count = 0
    refreshed_count = 0
    failed_count = 0

    for index, anime in enumerate(anime_data):
        metadata = anime.get('series_metadata')
        if not metadata:
            continue

        season_count = metadata.get('season_count') or 0
        base_audio_locales = [locale for locale in (metadata.get('audio_locales') or []) if locale and locale != 'ja-JP']

        if not base_audio_locales:
            continue

        if season_count <= 1:
            metadata['complete_audio_locales'] = sorted(base_audio_locales)
            metadata['audio_locale_coverage'] = {
                locale: {
                    'complete': True,
                    'seasons_with_locale': 1,
                    'seasons_total': 1
                }
                for locale in base_audio_locales
            }
            derived_count += 1
            continue

        if index > 0 and index % 20 == 0:
            time.sleep(0.25)

        coverage = fetch_series_audio_coverage(access_token, anime['id'], season_count)
        if not coverage:
            failed_count += 1
            continue

        metadata['complete_audio_locales'] = coverage['complete_audio_locales']
        metadata['audio_locale_coverage'] = coverage['audio_locale_coverage']
        refreshed_count += 1

    print(
        f"✓ Audio coverage derived for {derived_count} single-season series, "
        f"refreshed for {refreshed_count} multi-season series, {failed_count} failed"
    )

    return {
        'derived': derived_count,
        'refreshed': refreshed_count,
        'failed': failed_count
    }


def load_previous_data(filepath: str) -> List[Dict]:
    """Load previous anime.json if it exists."""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def compare_datasets(old_data: List[Dict], new_data: List[Dict]) -> Dict:
    """Compare old and new datasets and return diff statistics."""
    old_ids = {item['id']: item for item in old_data}
    new_ids = {item['id']: item for item in new_data}

    old_id_set = set(old_ids.keys())
    new_id_set = set(new_ids.keys())

    added = new_id_set - old_id_set
    removed = old_id_set - new_id_set
    kept = old_id_set & new_id_set

    # Track status changes for kept items
    status_changes = []
    for anime_id in kept:
        old_item = old_ids[anime_id]
        new_item = new_ids[anime_id]

        # Check for AniList status changes (only if anilist data exists)
        old_anilist = old_item.get('anilist') if old_item.get('anilist') is not None else {}
        new_anilist = new_item.get('anilist') if new_item.get('anilist') is not None else {}

        old_status = old_anilist.get('status', '')
        new_status = new_anilist.get('status', '')

        if old_status and new_status and old_status != new_status:
            status_changes.append({
                'id': anime_id,
                'title': new_item.get('title', 'Unknown'),
                'old_status': old_status,
                'new_status': new_status
            })

    return {
        'added': [new_ids[aid] for aid in added],
        'removed': [old_ids[rid] for rid in removed],
        'status_changes': status_changes,
        'total_old': len(old_data),
        'total_new': len(new_data)
    }


def save_change_log(diff: Dict, log_dir: str):
    """Save change log with timestamp."""
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = os.path.join(log_dir, f'changes_{timestamp}.json')

    log_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_old': diff['total_old'],
            'total_new': diff['total_new'],
            'added_count': len(diff['added']),
            'removed_count': len(diff['removed']),
            'status_changes_count': len(diff['status_changes'])
        },
        'added': [{'id': item['id'], 'title': item.get('title', 'Unknown')} for item in diff['added']],
        'removed': [{'id': item['id'], 'title': item.get('title', 'Unknown')} for item in diff['removed']],
        'status_changes': diff['status_changes']
    }

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Change log saved to {log_file}")
    return log_data


def print_summary(diff_summary: Dict):
    """Print a summary of changes."""
    print("\n" + "="*60)
    print("CHANGE SUMMARY")
    print("="*60)
    print(f"Previous total: {diff_summary['total_old']}")
    print(f"New total:      {diff_summary['total_new']}")
    print(f"Added:          {diff_summary['added_count']}")
    print(f"Removed:        {diff_summary['removed_count']}")
    print(f"Status changes: {diff_summary['status_changes_count']}")
    print("="*60 + "\n")


def enhance_with_anilist(anime_data: List[Dict], batch_size: int = 10) -> tuple[int, int]:
    """Enhance anime data with AniList information."""
    print("\nEnhancing with AniList data...")
    print(f"Total anime entries to enhance: {len(anime_data)}")

    all_results = {}
    total_batches = (len(anime_data) + batch_size - 1) // batch_size

    for i in range(0, len(anime_data), batch_size):
        batch = anime_data[i:i + batch_size]
        titles = [item['title'] for item in batch]
        batch_num = i // batch_size + 1

        progress_pct = (batch_num / total_batches) * 100
        print(f"  Batch {batch_num}/{total_batches} ({progress_pct:.1f}% complete) - Processing {len(titles)} titles...")
        batch_results = get_anilist_data_batch(titles)
        all_results.update(batch_results)

        # Log some successful matches from this batch
        matches_in_batch = sum(1 for v in batch_results.values() if v is not None)
        print(f"    Found {matches_in_batch}/{len(titles)} AniList matches in this batch")

        # Validate format of first non-None result
        if i == 0:
            first_valid_result = next((v for v in batch_results.values() if v is not None), None)
            if first_valid_result and not validate_anilist_format(first_valid_result):
                print("ERROR: AniList API format has changed!")
                print(f"Expected fields: anilist_id, matched_title, match_score")
                print(f"Received fields: {list(first_valid_result.keys())}")
                sys.exit(1)

        # Rate limiting between batches
        if i + batch_size < len(anime_data):
            time.sleep(1.5)  # Be nice to the API

    # Enhance the anime data
    enhanced_count = 0
    not_found_count = 0

    for anime in anime_data:
        title = anime['title']
        anilist_data = all_results.get(title)

        if anilist_data:
            anime['anilist'] = anilist_data
            enhanced_count += 1
        else:
            anime['anilist'] = None
            not_found_count += 1

    print(f"✓ Enhanced {enhanced_count} entries, {not_found_count} not found")
    return enhanced_count, not_found_count


def main():
    """Main execution function."""
    print("="*70)
    print("CRUNCHYROLL ANIME DATA UPDATE SCRIPT")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Paths
    anime_json_path = 'frontend/public/anime.json'
    log_dir = 'data_change_logs'

    # Load previous data
    print("\n[1/7] Loading previous anime data...")
    old_data = load_previous_data(anime_json_path)
    print(f"✓ Loaded {len(old_data)} previous entries")

    # Get anonymous token and fetch new data
    print("\n[2/7] Getting anonymous access token...")
    access_token = get_anonymous_token()

    print("\n[3/7] Fetching anime catalog from Crunchyroll...")
    new_raw_data = fetch_crunchyroll_anime(access_token)

    # Enhance new data with AniList
    print("\n[4/7] Enhancing data with AniList metadata...")
    enhanced_count, not_found_count = enhance_with_anilist(new_raw_data)

    # Enrich audio coverage metadata
    print("\n[5/7] Enriching audio coverage metadata...")
    coverage_stats = enrich_audio_coverage(new_raw_data, access_token)

    # Compare datasets
    print("\n[6/7] Comparing datasets and generating change log...")
    diff = compare_datasets(old_data, new_raw_data)

    # Save change log
    log_data = save_change_log(diff, log_dir)

    # Print summary
    print_summary(log_data['summary'])

    # Save new data
    print(f"[7/7] Saving new data to {anime_json_path}...")
    with open(anime_json_path, 'w', encoding='utf-8') as f:
        json.dump(new_raw_data, f, indent=2, ensure_ascii=False)
    print("✓ Data saved successfully")

    print("\n" + "="*70)
    print(f"UPDATE COMPLETED at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Set GitHub Actions output for use in commit message
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
            f.write(f"added={log_data['summary']['added_count']}\n")
            f.write(f"removed={log_data['summary']['removed_count']}\n")
            f.write(f"status_changes={log_data['summary']['status_changes_count']}\n")
            f.write(f"enhanced={enhanced_count}\n")
            f.write(f"not_found={not_found_count}\n")
            f.write(f"coverage_derived={coverage_stats['derived']}\n")
            f.write(f"coverage_refreshed={coverage_stats['refreshed']}\n")
            f.write(f"coverage_failed={coverage_stats['failed']}\n")


if __name__ == '__main__':
    main()
