from pytube import Playlist

def get_video_links_from_playlist(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        # video_urls is a list of all video links in the playlist
        links = list(playlist.video_urls)
        print(f"Found {len(links)} videos in the playlist.")
        return links
    except Exception as e:
        print(f"Error fetching playlist: {e}")
        return []

# Usage:
# playlist_link = "https://www.youtube.com/playlist?list=PL..."
# VIDEO_URLS = get_video_links_from_playlist(playlist_link)