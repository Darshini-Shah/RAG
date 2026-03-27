import yt_dlp

def get_video_urls(playlist_url: str) -> list[str]:
    """
    Given a YouTube playlist URL, extracts and returns a list of individual video URLs.
    Uses yt-dlp to efficiently fetch metadata without downloading video files.
    """
    video_urls = []
    ydl_opts = {
        'extract_flat': True, # Only extract metadata, do not download
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            
            if 'entries' in info:
                # It's a playlist
                for entry in info['entries']:
                    url = entry.get('url')
                    if url:
                        if url.startswith('http'):
                            video_urls.append(url)
                        else:
                            # yt-dlp might just return the video ID sometimes
                            video_urls.append(f"https://www.youtube.com/watch?v={url}")
            else:
                # It's a single video
                video_urls.append(info.get('webpage_url', playlist_url))
                
    except Exception as e:
        print(f"Error extracting playlist URLs: {e}")
        
    return video_urls

if __name__ == "__main__":
    # Test script
    test_url = "https://www.youtube.com/playlist?list=PL2yQDdvlhXf_hwHhkE2Ew5A3_KryAov-p"
    print(get_video_urls(test_url))
