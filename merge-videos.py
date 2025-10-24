#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import subprocess
from pathlib import Path

def download_video(url, filename):
    """Download video from URL"""
    print(f"Downloading {filename}...")
    urllib.request.urlretrieve(url, filename)
    return filename

def merge_videos_with_text(videos, hook, title, output="final.mp4"):
    """Merge 4 videos with text overlays using FFmpeg"""
    
    # Download all videos
    video_files = []
    for i, video_url in enumerate(videos):
        filename = f"video_{i}.mp4"
        download_video(video_url, filename)
        video_files.append(filename)
    
    # Create concat file
    with open("concat.txt", "w") as f:
        for video_file in video_files:
            f.write(f"file '{video_file}'\n")
    
    # FFmpeg command with text overlays
    # Hook text for first 3 seconds
    # Title text for last 3 seconds
    ffmpeg_cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', 'concat.txt',
        '-vf', (
            f"drawtext=text='{hook}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize=80:fontcolor=yellow:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y=150:enable='between(t,0,3)',"
            f"drawtext=text='{title}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"fontsize=50:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-150:enable='between(t,17,20)'"
        ),
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        output
    ]
    
    print("Merging videos with text overlays...")
    subprocess.run(ffmpeg_cmd, check=True)
    
    # Clean up downloaded files
    for video_file in video_files:
        os.remove(video_file)
    os.remove("concat.txt")
    
    print(f"Video created: {output}")
    return output

if __name__ == "__main__":
    # Get inputs from environment variables (set by GitHub Actions)
    videos = json.loads(os.environ.get('VIDEO_URLS', '[]'))
    hook = os.environ.get('HOOK_TEXT', '')
    title = os.environ.get('TITLE_TEXT', '')
    
    if not videos or len(videos) != 4:
        print("Error: Need exactly 4 video URLs")
        sys.exit(1)
    
    # Process videos
    output_file = merge_videos_with_text(videos, hook, title)
    
    # Set output for GitHub Actions
    print(f"::set-output name=video_file::{output_file}")