#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import subprocess
from pathlib import Path
import time

def download_video(url, filename, max_retries=3):
    """Download video from URL with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"Downloading {filename} (attempt {attempt + 1})...")
            urllib.request.urlretrieve(url, filename)
            # Verify file was downloaded
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"✓ Successfully downloaded {filename}")
                return filename
        except Exception as e:
            print(f"⚠ Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
            else:
                raise
    return None

def merge_videos_with_text(videos, hook, title, output="final.mp4"):
    """Merge 4 videos with text overlays using FFmpeg"""
    
    # Download all videos
    video_files = []
    for i, video_url in enumerate(videos):
        filename = f"video_{i}.mp4"
        try:
            downloaded = download_video(video_url, filename)
            if downloaded:
                video_files.append(filename)
            else:
                print(f"ERROR: Failed to download video {i}")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR downloading video {i}: {e}")
            sys.exit(1)
    
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
        '-movflags', '+faststart',  # Optimize for streaming
        '-y',
        output
    ]
    
    print("Merging videos with text overlays...")
    try:
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        print("✓ Video merged successfully!")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: FFmpeg failed: {e.stderr}")
        sys.exit(1)
    
    # Verify output file
    if not os.path.exists(output) or os.path.getsize(output) == 0:
        print("ERROR: Output file not created or is empty")
        sys.exit(1)
    
    print(f"✓ Video created: {output} ({os.path.getsize(output) / 1024 / 1024:.2f} MB)")
    
    # Clean up downloaded files
    for video_file in video_files:
        try:
            os.remove(video_file)
        except:
            pass
    try:
        os.remove("concat.txt")
    except:
        pass
    
    return output

if __name__ == "__main__":
    # Get inputs from environment variables (set by GitHub Actions)
    videos = json.loads(os.environ.get('VIDEO_URLS', '[]'))
    hook = os.environ.get('HOOK_TEXT', 'AMAZING')
    title = os.environ.get('TITLE_TEXT', 'Viral Video')
    
    print(f"Processing {len(videos)} videos...")
    print(f"Hook: {hook}")
    print(f"Title: {title}")
    
    if not videos or len(videos) != 4:
        print("ERROR: Need exactly 4 video URLs")
        sys.exit(1)
    
    # Process videos
    try:
        output_file = merge_videos_with_text(videos, hook, title)
        print(f"SUCCESS: {output_file}")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)