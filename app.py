#!/usr/bin/env python3
"""
YouTube Info API - Render Compatible
Endpoint: GET /youtube?url=<youtube_url>
"""

import sys
import re
import json
import urllib.request
import urllib.parse
import socket
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_BASE = "https://youtubedl-skbk.onrender.com"


def extract_video_id(url):
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|m\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'v=([a-zA-Z0-9_-]{11})',
        r'([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_channel_id(text):
    patterns = [
        r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        r'"channelId":"([a-zA-Z0-9_-]+)"',
        r'<meta itemprop="identifier" content="([a-zA-Z0-9_-]+)">',
        r'"browseId":"([a-zA-Z0-9_-]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_handle_from_url(url):
    if not url:
        return None
    match = re.search(r'youtube\.com/@([a-zA-Z0-9_.-]+)', url)
    if match:
        return match.group(1)
    return None


def extract_handle_from_html(text):
    patterns = [
        r'youtube\.com/@([a-zA-Z0-9_.-]+)',
        r'"canonicalBaseUrl":"/@([a-zA-Z0-9_.-]+)"',
        r'<meta property="og:url" content="https://www\.youtube\.com/@([a-zA-Z0-9_.-]+)">',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def fetch_url(url, headers=None, timeout=15):
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
        }
    try:
        req = urllib.request.Request(url, headers=headers)
        req.add_header('Cookie', 'CONSENT=YES+cb.20210328-17-p0.en+FX+{}'.format(100 + hash(url) % 900))
        socket.setdefaulttimeout(timeout)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8')
    except Exception:
        return None
    finally:
        socket.setdefaulttimeout(None)


def format_duration(seconds):
    if not seconds:
        return None
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_count(num):
    if not num:
        return None
    try:
        n = int(num)
        if n >= 1_000_000_000:
            return f"{n / 1_000_000_000:.1f}B"
        elif n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        elif n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)
    except:
        return str(num)


def parse_keywords(keywords_str):
    if not keywords_str:
        return []
    keywords = []
    current = ""
    in_quotes = False
    i = 0
    while i < len(keywords_str):
        char = keywords_str[i]
        if char == '"':
            if in_quotes:
                if current.strip():
                    keywords.append(current.strip())
                current = ""
                in_quotes = False
            else:
                if current.strip():
                    keywords.append(current.strip())
                current = ""
                in_quotes = True
        elif char == ' ' and not in_quotes:
            if current.strip():
                keywords.append(current.strip())
            current = ""
        else:
            current += char
        i += 1
    if current.strip():
        keywords.append(current.strip())
    return keywords


def get_download_info(video_url):
    try:
        api_url = f"{API_BASE}/youtube?url={urllib.parse.quote(video_url, safe='')}"
        response = fetch_url(api_url, timeout=30)
        if response:
            data = json.loads(response)
            if data.get('success'):
                return data
        return None
    except Exception as e:
        return {"api_error": str(e)}


def get_video_info(video_id, video_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
    }

    info = {
        'video_id': video_id,
        'url': f"https://www.youtube.com/watch?v={video_id}",
        'short_url': f"https://youtu.be/{video_id}",
        'embed_url': f"https://www.youtube.com/embed/{video_id}",
        'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        'thumbnail_urls': {
            'default': f"https://img.youtube.com/vi/{video_id}/default.jpg",
            'mqdefault': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
            'hqdefault': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            'sddefault': f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
            'maxresdefault': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        }
    }

    channel_id = None
    channel_handle = None

    # oEmbed
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        html = fetch_url(oembed_url, headers, timeout=10)
        if html:
            oembed_data = json.loads(html)
            info.update({
                'title': oembed_data.get('title'),
                'author_name': oembed_data.get('author_name'),
                'author_url': oembed_data.get('author_url'),
                'provider_name': oembed_data.get('provider_name'),
                'type': oembed_data.get('type'),
                'width': oembed_data.get('width'),
                'height': oembed_data.get('height'),
            })
            if oembed_data.get('author_url'):
                h = extract_handle_from_url(oembed_data['author_url'])
                if h:
                    channel_handle = h
    except Exception:
        pass

    # Fetch YouTube page
    html = None
    page_sources = [
        f"https://www.youtube.com/watch?v={video_id}",
        f"https://www.youtube.com/watch?v={video_id}&bpctr=9999999999&has_verified=1",
        f"https://www.youtube-nocookie.com/embed/{video_id}",
    ]

    for page_url in page_sources:
        try:
            html = fetch_url(page_url, headers, timeout=20)
            if html and ('ytInitialPlayerResponse' in html or 'videoDetails' in html):
                break
        except:
            continue

    try:
        if not html:
            raise ValueError("No HTML content fetched")

        channel_id = extract_channel_id(html)

        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});(?:\s*</script>|\s*var)', html, re.DOTALL)
        if not match:
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html, re.DOTALL)

        if match:
            try:
                player_data = json.loads(match.group(1))
                video_details = player_data.get('videoDetails', {})

                info['title'] = video_details.get('title', info.get('title'))
                info['author'] = video_details.get('author', info.get('author_name'))
                info['channel_id'] = video_details.get('channelId') or channel_id
                info['description'] = video_details.get('shortDescription')
                info['duration_seconds'] = int(video_details.get('lengthSeconds', 0)) if video_details.get('lengthSeconds') else None
                info['view_count'] = int(video_details.get('viewCount', 0)) if video_details.get('viewCount') else None
                info['like_count'] = int(video_details.get('likes', 0)) if video_details.get('likes') else None
                info['is_private'] = video_details.get('isPrivate', False)
                info['is_live'] = video_details.get('isLive', False)
                info['is_live_content'] = video_details.get('isLiveContent', False)
                info['keywords'] = video_details.get('keywords', [])
                info['category'] = video_details.get('category')
                info['publish_date'] = video_details.get('publishDate')
                info['upload_date'] = video_details.get('uploadDate')

                if video_details.get('channelId'):
                    channel_id = video_details.get('channelId')

                thumbs = video_details.get('thumbnail', {}).get('thumbnails', [])
                if thumbs:
                    info['thumbnails'] = thumbs

                microformat = player_data.get('microformat', {}).get('playerMicroformatRenderer', {})
                if microformat:
                    info['publish_date'] = microformat.get('publishDate') or info.get('publish_date')
                    info['upload_date'] = microformat.get('uploadDate') or info.get('upload_date')
                    info['category'] = microformat.get('category') or info.get('category')
                    info['is_family_safe'] = microformat.get('isFamilySafe')
                    info['has_ypc_metadata'] = microformat.get('hasYpcMetadata', False)
                    info['owner_channel_name'] = microformat.get('ownerChannelName')
                    info['owner_profile_url'] = microformat.get('ownerProfileUrl')
                    info['upload_date_iso'] = microformat.get('uploadDate')
                    info['publish_date_iso'] = microformat.get('publishDate')
                    info['duration_iso'] = microformat.get('lengthSeconds')

                    owner_profile_url = microformat.get('ownerProfileUrl')
                    if owner_profile_url:
                        h = extract_handle_from_url(owner_profile_url)
                        if h:
                            channel_handle = h

                    owner = microformat.get('videoOwner', {})
                    if owner:
                        info['owner'] = owner

                captions = player_data.get('captions', {}).get('playerCaptionsTracklistRenderer', {})
                if captions:
                    caption_tracks = captions.get('captionTracks', [])
                    if caption_tracks:
                        info['captions'] = [
                            {
                                'name': track.get('name', {}).get('simpleText'),
                                'language_code': track.get('languageCode'),
                                'is_translatable': track.get('isTranslatable', False),
                            }
                            for track in caption_tracks
                        ]
                    info['audio_tracks'] = captions.get('audioTracks', [])
                    info['default_audio_track_index'] = captions.get('defaultAudioTrackIndex')

            except json.JSONDecodeError:
                pass
        else:
            info['player_response_not_found'] = True

        meta_title = re.search(r'<meta name="title" content="([^"]+)">', html)
        if meta_title and not info.get('title'):
            info['title'] = meta_title.group(1)

        meta_desc = re.search(r'<meta name="description" content="([^"]+)">', html)
        if meta_desc:
            info['meta_description'] = meta_desc.group(1)

        if not info.get('view_count'):
            view_match = re.search(r'"viewCount":"(\d+)"', html)
            if view_match:
                info['view_count'] = int(view_match.group(1))

        like_match = re.search(r'"likeCount":"(\d+)"', html)
        if like_match:
            info['like_count'] = int(like_match.group(1))

        sub_match = re.search(r'"subscriberCountText":\{"simpleText":"([^"]+)"\}', html)
        if sub_match:
            info['subscriber_count_text'] = sub_match.group(1)

        comment_match = re.search(r'"commentCount":\{"simpleText":"([^"]+)"\}', html)
        if comment_match:
            info['comment_count_text'] = comment_match.group(1)

    except Exception:
        pass

    # Fallback nocookie
    if not info.get('title') or info.get('title') == 'YouTube':
        try:
            nocookie_url = f"https://www.youtube-nocookie.com/embed/{video_id}"
            nocookie_html = fetch_url(nocookie_url, headers, timeout=10)
            if nocookie_html:
                title_match = re.search(r'<title>([^<]+)</title>', nocookie_html)
                if title_match:
                    extracted = title_match.group(1).replace(' - YouTube', '').strip()
                    if extracted and extracted != 'YouTube':
                        info['title'] = extracted
                if 'ytInitialPlayerResponse' in nocookie_html:
                    match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', nocookie_html, re.DOTALL)
                    if match:
                        try:
                            embed_data = json.loads(match.group(1))
                            embed_details = embed_data.get('videoDetails', {})
                            if embed_details.get('title') and embed_details['title'] != 'YouTube':
                                info['title'] = embed_details['title']
                            if embed_details.get('author'):
                                info['author'] = embed_details['author']
                            if embed_details.get('channelId'):
                                info['channel_id'] = embed_details['channelId']
                                channel_id = embed_details['channelId']
                            if embed_details.get('shortDescription'):
                                info['description'] = embed_details['shortDescription']
                            if embed_details.get('lengthSeconds'):
                                info['duration_seconds'] = int(embed_details['lengthSeconds'])
                            if embed_details.get('viewCount'):
                                info['view_count'] = int(embed_details['viewCount'])
                        except:
                            pass
        except:
            pass

    # Formatting
    duration_formatted = format_duration(info['duration_seconds']) if info.get('duration_seconds') else None
    view_count_formatted = format_count(info['view_count']) if info.get('view_count') else None
    like_count_formatted = format_count(info['like_count']) if info.get('like_count') else None

    ordered_info = {}
    inserted = set()

    for key, value in info.items():
        if key in ('like_count', 'view_count_formatted', 'like_count_formatted', 'duration_formatted'):
            continue
        ordered_info[key] = value

        if key == 'view_count':
            if info.get('like_count') is not None:
                ordered_info['like_count'] = info['like_count']
                inserted.add('like_count')
            if view_count_formatted is not None:
                ordered_info['view_count_formatted'] = view_count_formatted
                inserted.add('view_count_formatted')
            if like_count_formatted is not None:
                ordered_info['like_count_formatted'] = like_count_formatted
                inserted.add('like_count_formatted')
            if duration_formatted is not None:
                ordered_info['duration_formatted'] = duration_formatted
                inserted.add('duration_formatted')

    for key in ('like_count', 'view_count_formatted', 'like_count_formatted', 'duration_formatted'):
        if key not in inserted:
            if key == 'like_count' and info.get('like_count') is not None:
                ordered_info['like_count'] = info['like_count']
            elif key == 'view_count_formatted' and view_count_formatted is not None:
                ordered_info['view_count_formatted'] = view_count_formatted
            elif key == 'like_count_formatted' and like_count_formatted is not None:
                ordered_info['like_count_formatted'] = like_count_formatted
            elif key == 'duration_formatted' and duration_formatted is not None:
                ordered_info['duration_formatted'] = duration_formatted

    ordered_info['publish_date_format'] = ""
    ordered_info['upload_date_format'] = ""

    return ordered_info, channel_id, channel_handle


def get_channel_info(channel_id=None, channel_handle=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
    }

    channel_info = {
        'channel_id': channel_id,
        'handle': channel_handle,
    }

    if channel_handle:
        channel_url = f"https://www.youtube.com/@{channel_handle}"
    elif channel_id:
        channel_url = f"https://www.youtube.com/channel/{channel_id}"
    else:
        return channel_info

    channel_info['url'] = channel_url

    try:
        html = fetch_url(channel_url, headers, timeout=20)
        if not html:
            if channel_handle:
                mobile_url = f"https://m.youtube.com/@{channel_handle}"
            else:
                mobile_url = f"https://m.youtube.com/channel/{channel_id}"
            html = fetch_url(mobile_url, headers, timeout=20)

        if html:
            if not channel_id:
                channel_id = extract_channel_id(html)
                if channel_id:
                    channel_info['channel_id'] = channel_id

            if not channel_handle:
                channel_handle = extract_handle_from_html(html)
                if channel_handle:
                    channel_info['handle'] = channel_handle

            data = None

            match = re.search(r"ytInitialData\s*=\s*'(.+?)';", html, re.DOTALL)
            if match:
                try:
                    data_str = match.group(1)
                    data_str = data_str.encode('utf-8').decode('unicode_escape')
                    data = json.loads(data_str)
                except Exception as e:
                    channel_info['parse_error_1'] = str(e)

            if not data:
                match = re.search(r'ytInitialData\s*=\s*({.+?});(?:\s*</script>|\s*var)', html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                    except Exception as e:
                        channel_info['parse_error_2'] = str(e)

            if not data:
                match = re.search(r'ytInitialData\s*=\s*({.+?});', html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                    except Exception as e:
                        channel_info['parse_error_3'] = str(e)

            if data:
                try:
                    metadata = data.get('metadata', {}).get('channelMetadataRenderer', {})
                    if metadata:
                        channel_info['title'] = metadata.get('title')
                        channel_info['description'] = metadata.get('description')
                        channel_info['rss_url'] = metadata.get('rssUrl')
                        channel_info['external_id'] = metadata.get('externalId')
                        channel_info['is_family_safe'] = metadata.get('isFamilySafe')

                        keywords = metadata.get('keywords')
                        if keywords:
                            if isinstance(keywords, str):
                                channel_info['keywords'] = parse_keywords(keywords)
                            elif isinstance(keywords, list):
                                channel_info['keywords'] = keywords

                        channel_info['owner'] = metadata.get('owner')
                        avatar = metadata.get('avatar', {})
                        if avatar:
                            channel_info['avatar'] = avatar.get('thumbnails', [])
                        channel_info['channel_url'] = metadata.get('channelUrl')
                        channel_info['vanity_channel_url'] = metadata.get('vanityChannelUrl')

                    header = data.get('header', {})
                    if header:
                        c4_header = header.get('c4TabbedHeaderRenderer', {})
                        if c4_header:
                            banner = c4_header.get('banner', {})
                            if banner:
                                channel_info['banner'] = banner.get('thumbnails', [])
                            tv_banner = c4_header.get('tvBanner', {})
                            if tv_banner:
                                channel_info['tv_banner'] = tv_banner.get('thumbnails', [])
                            mobile_banner = c4_header.get('mobileBanner', {})
                            if mobile_banner:
                                channel_info['mobile_banner'] = mobile_banner.get('thumbnails', [])

                            sub_text = c4_header.get('subscriberCountText', {})
                            if sub_text:
                                channel_info['subscriber_count_text'] = sub_text.get('simpleText')

                            videos_text = c4_header.get('videosCountText', {})
                            if videos_text:
                                runs = videos_text.get('runs', [])
                                if runs:
                                    channel_info['videos_count_text'] = runs[0].get('text')

                            handle_text = c4_header.get('channelHandleText', {})
                            if handle_text:
                                channel_info['channel_handle_text'] = handle_text.get('simpleText')

                            tags = c4_header.get('tags', [])
                            if tags:
                                channel_info['tags'] = tags

                    contents = data.get('contents', {})
                    if contents:
                        browse = contents.get('twoColumnBrowseResultsRenderer', {})
                        if not browse:
                            browse = contents.get('singleColumnBrowseResultsRenderer', {})

                        tabs = browse.get('tabs', [])
                        for tab in tabs:
                            tab_renderer = tab.get('tabRenderer', {})
                            if tab_renderer.get('selected'):
                                content = tab_renderer.get('content', {})
                                section_list = content.get('sectionListRenderer', {})
                                if section_list:
                                    for section in section_list.get('contents', []):
                                        item_section = section.get('itemSectionRenderer', {})
                                        if item_section:
                                            for item in item_section.get('contents', []):
                                                cvp = item.get('channelVideoPlayerRenderer', {})
                                                if cvp:
                                                    featured = {}
                                                    featured['video_id'] = cvp.get('videoId')
                                                    title = cvp.get('title', {})
                                                    if title:
                                                        runs = title.get('runs', [])
                                                        if runs:
                                                            featured['title'] = runs[0].get('text')
                                                    desc = cvp.get('description', {})
                                                    if desc:
                                                        runs = desc.get('runs', [])
                                                        if runs:
                                                            featured['description'] = runs[0].get('text')
                                                    view_text = cvp.get('viewCountText', {})
                                                    if view_text:
                                                        featured['view_count_text'] = view_text.get('simpleText')
                                                    pub_text = cvp.get('publishedTimeText', {})
                                                    if pub_text:
                                                        runs = pub_text.get('runs', [])
                                                        if runs:
                                                            featured['published_time_text'] = runs[0].get('text')
                                                    if featured:
                                                        channel_info['featured_video'] = featured

                                                about = item.get('channelAboutFullMetadataRenderer', {})
                                                if about:
                                                    stats = about.get('viewCountText', {})
                                                    if stats:
                                                        channel_info['total_views_text'] = stats.get('simpleText')

                                                    joined = about.get('joinedDateText', {})
                                                    if joined:
                                                        runs = joined.get('runs', [])
                                                        if len(runs) > 1:
                                                            channel_info['joined_date'] = runs[1].get('text')

                                                    primary_links = about.get('primaryLinks', [])
                                                    if primary_links:
                                                        channel_info['links'] = [
                                                            {
                                                                'title': link.get('title', {}).get('simpleText'),
                                                                'url': link.get('navigationEndpoint', {}).get('urlEndpoint', {}).get('url'),
                                                            }
                                                            for link in primary_links
                                                        ]

                                                    country = about.get('country', {})
                                                    if country:
                                                        channel_info['country'] = country.get('simpleText')

                                                    desc = about.get('description', {})
                                                    if desc:
                                                        simple = desc.get('simpleText')
                                                        if simple and not channel_info.get('description'):
                                                            channel_info['description'] = simple

                                        shelf = section.get('shelfRenderer', {})
                                        if shelf:
                                            title = shelf.get('title', {})
                                            if title:
                                                runs = title.get('runs', [])
                                                if runs:
                                                    shelf_title = runs[0].get('text', '').lower()
                                                    if 'playlist' in shelf_title:
                                                        channel_info['has_playlists_section'] = True
                                                    elif 'popular' in shelf_title or 'upload' in shelf_title:
                                                        channel_info['has_videos_section'] = True
                except Exception as e:
                    channel_info['data_extract_error'] = str(e)
            else:
                channel_info['ytInitialData_not_found'] = True

            meta_title = re.search(r'<meta property="og:title" content="([^"]+)">', html)
            if meta_title and not channel_info.get('title'):
                channel_info['title'] = meta_title.group(1)

            meta_desc = re.search(r'<meta property="og:description" content="([^"]+)">', html)
            if meta_desc and not channel_info.get('description'):
                channel_info['description'] = meta_desc.group(1)

            meta_image = re.search(r'<meta property="og:image" content="([^"]+)">', html)
            if meta_image:
                channel_info['og_image'] = meta_image.group(1)

            if not channel_info.get('subscriber_count_text'):
                sub_patterns = [
                    r'"subscriberCountText":\{"simpleText":"([^"]+)"\}',
                    r'"subscriberCountText":\{"runs":\[\{"text":"([^"]+)"\}\]\}',
                ]
                for pattern in sub_patterns:
                    sub_match = re.search(pattern, html)
                    if sub_match:
                        channel_info['subscriber_count_text'] = sub_match.group(1)
                        break

            vid_patterns = [
                r'"videosCountText":\{"runs":\[\{"text":"([^"]+)"\}\]\}',
                r'(\d[,\d]*) videos?',
            ]
            for pattern in vid_patterns:
                vid_match = re.search(pattern, html)
                if vid_match:
                    channel_info['videos_count_text'] = vid_match.group(1)
                    break

            avatar_match = re.search(r'<link rel="image_src" href="([^"]+)">', html)
            if avatar_match:
                channel_info['avatar_url'] = avatar_match.group(1)

            canonical_match = re.search(r'<link rel="canonical" href="([^"]+)">', html)
            if canonical_match:
                channel_info['canonical_url'] = canonical_match.group(1)

    except Exception as e:
        channel_info['fetch_error'] = str(e)

    if channel_id:
        channel_info['channel_url'] = f"https://www.youtube.com/channel/{channel_id}"
    if channel_handle:
        channel_info['handle_url'] = f"https://www.youtube.com/@{channel_handle}"
    if channel_id:
        channel_info['rss_feed'] = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    cleaned = {}
    for k, v in channel_info.items():
        if v is not None and v != [] and v != {}:
            cleaned[k] = v
        elif v == False and k in ['is_family_safe']:
            cleaned[k] = v

    return cleaned


@app.route('/')
def home():
    return jsonify({
        "status": True,
        "message": "YouTube Info API is running",
        "endpoints": {
            "/youtube?url=<youtube_url>": "Get video, channel & download info"
        },
        "creator": "WALUKA🇱🇰"
    })


@app.route('/youtube')
def youtube_endpoint():
    url = request.args.get('url')
    if not url:
        return jsonify({
            "status": False,
            "creator": "WALUKA🇱🇰",
            "error": "Missing 'url' parameter. Usage: /youtube?url=<youtube_url>"
        }), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({
            "status": False,
            "creator": "WALUKA🇱🇰",
            "error": "Could not extract video ID from URL",
            "url": url,
            "supported_formats": [
                "https://www.youtube.com/watch?v=VIDEO_ID",
                "https://youtu.be/VIDEO_ID",
                "https://m.youtube.com/watch?v=VIDEO_ID",
                "https://www.youtube.com/shorts/VIDEO_ID"
            ]
        }), 400

    try:
        video_info, channel_id, channel_handle = get_video_info(video_id, url)
        download_data = get_download_info(url)
        channel_info = get_channel_info(channel_id, channel_handle)

        cleaned_video = {}
        for k, v in video_info.items():
            if v is not None and v != [] and v != {}:
                cleaned_video[k] = v
            elif v == False and k in ['is_private', 'is_live', 'is_live_content', 'is_family_safe', 'has_ypc_metadata']:
                cleaned_video[k] = v
            elif v == "" and k in ['publish_date_format', 'upload_date_format']:
                cleaned_video[k] = v

        result = {
            "video_details": cleaned_video,
            "formats": {},
            "channel": channel_info
        }

        if download_data and download_data.get('success'):
            result["formats"] = download_data.get('formats', {})
        elif download_data and download_data.get('api_error'):
            result["formats"] = {"error": download_data['api_error']}
        else:
            result["formats"] = {"error": "Failed to fetch download links from API"}

        return jsonify({
            "status": True,
            "creator": "WALUKA🇱🇰",
            "result": {
                "result": result
            }
        })

    except Exception as e:
        return jsonify({
            "status": False,
            "creator": "WALUKA🇱🇰",
            "error": str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
