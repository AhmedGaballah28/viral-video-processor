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

def check_video_has_audio(video_file):
    """Check if video file has audio stream"""
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', 
               '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', video_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip() != ""
    except:
        return False

def merge_videos_with_text(videos, hook, title, output="final.mp4"):
    """Merge 4 videos with text overlays using FFmpeg"""
    
    # Download all videos
    video_files = []
    has_audio = False
    
    for i, video_url in enumerate(videos):
        filename = f"video_{i}.mp4"
        try:
            downloaded = download_video(video_url, filename)
            if downloaded:
                video_files.append(filename)
                # Check if any video has audio
                if check_video_has_audio(filename):
                    has_audio = True
                    print(f"✓ Video {i} has audio")
                else:
                    print(f"ℹ Video {i} has no audio")
            else:
                print(f"ERROR: Failed to download video {i}")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR downloading video {i}: {e}")
            sys.exit(1)
    
    # Create concat file with proper format
    concat_content = ""
    for video_file in video_files:
        concat_content += f"file '{os.path.abspath(video_file)}'\n"
    
    with open("concat.txt", "w") as f:
        f.write(concat_content)
    
    print(f"Audio detected: {has_audio}")
    
    # Build FFmpeg command based on whether we have audio
    if has_audio:
        # Complex filter for videos WITH audio
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];"
            f"[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];"
            f"[2:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v2];"
            f"[3:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v3];"
            f"[v0][0:a][v1][1:a][v2][2:a][v3][3:a]concat=n=4:v=1:a=1[outv][outa];"
            f"[outv]drawtext=text='{hook}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize=80:fontcolor=yellow:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y=150:enable='between(t,0,3)',"
            f"drawtext=text='{title}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"fontsize=50:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-150:enable='between(t,17,20)'[final]"
        )
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_files[0],
            '-i', video_files[1],
            '-i', video_files[2],
            '-i', video_files[3],
            '-filter_complex', filter_complex,
            '-map', '[final]',
            '-map', '[outa]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '48000',
            '-movflags', '+faststart',
            '-y',
            output
        ]
    else:
        # Simpler command for videos WITHOUT audio (add silent audio track)
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', 'concat.txt',
            '-f', 'lavfi',
            '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000',
            '-vf', (
                f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
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
            '-b:a', '192k',
            '-shortest',
            '-movflags', '+faststart',
            '-y',
            output
        ]
    
    print("Merging videos with text overlays...")
    print(f"Command: {' '.join(ffmpeg_cmd[:50])}...")  # Print first part of command for debugging
    
    try:
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        print("✓ Video merged successfully!")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: FFmpeg failed")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)
    
    # Verify output file
    if not os.path.exists(output) or os.path.getsize(output) == 0:
        print("ERROR: Output file not created or is empty")
        sys.exit(1)
    
    # Check output has audio
    output_has_audio = check_video_has_audio(output)
    print(f"✓ Video created: {output} ({os.path.getsize(output) / 1024 / 1024:.2f} MB)")
    print(f"✓ Output has audio: {output_has_audio}")
    
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
    
    # Show video URLs (for debugging)
    for i, url in enumerate(videos):
        print(f"Video {i}: {url[:50]}...")
    
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