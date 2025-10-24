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
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"✓ Successfully downloaded {filename}")
                return filename
        except Exception as e:
            print(f"⚠ Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
    return None

def analyze_video(video_file):
    """Analyze video file for audio information"""
    try:
        # Get detailed audio info
        cmd = ['ffprobe', '-v', 'error', '-show_streams', 
               '-select_streams', 'a', '-of', 'json', video_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        import json as json_module
        data = json_module.loads(result.stdout)
        
        if data.get('streams'):
            audio_stream = data['streams'][0]
            print(f"  Audio codec: {audio_stream.get('codec_name', 'unknown')}")
            print(f"  Sample rate: {audio_stream.get('sample_rate', 'unknown')} Hz")
            print(f"  Channels: {audio_stream.get('channels', 'unknown')}")
            return True
        else:
            print("  No audio stream found")
            return False
    except Exception as e:
        print(f"  Error analyzing: {e}")
        return False

def merge_videos_with_text(videos, hook, title, output="final.mp4"):
    """Merge 4 videos with text overlays and ensure audio"""
    
    # Download and analyze all videos
    video_files = []
    has_real_audio = False
    
    for i, video_url in enumerate(videos):
        filename = f"video_{i}.mp4"
        try:
            downloaded = download_video(video_url, filename)
            if downloaded:
                video_files.append(filename)
                print(f"\n📊 Analyzing video {i}:")
                has_audio = analyze_video(filename)
                if has_audio:
                    has_real_audio = True
            else:
                print(f"ERROR: Failed to download video {i}")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR downloading video {i}: {e}")
            sys.exit(1)
    
    print(f"\n🔊 Audio Status: {'Found audio streams' if has_real_audio else 'No audio found - will add background audio'}")
    
    # Build FFmpeg command
    if not has_real_audio:
        print("🎵 Adding background audio track...")
        
        # Method 1: Use sine wave for testing (audible)
        # This creates a soft 440Hz tone (A note) with fade in/out
        ffmpeg_cmd = [
            'ffmpeg'
        ]
        
        # Add all video inputs
        for video_file in video_files:
            ffmpeg_cmd.extend(['-i', video_file])
        
        # Add generated audio - soft sine wave with fade
        ffmpeg_cmd.extend([
            '-f', 'lavfi',
            '-i', 'sine=frequency=440:duration=20:sample_rate=48000'  # 440Hz sine wave
        ])
        
        # Complex filter for concatenation
        filter_complex = ""
        
        # Scale and pad each video
        for i in range(4):
            filter_complex += f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];"
        
        # Concatenate videos
        filter_complex += "[v0][v1][v2][v3]concat=n=4:v=1:a=0[outv];"
        
        # Add text overlays
        filter_complex += (
            f"[outv]drawtext=text='{hook}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize=80:fontcolor=yellow:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y=150:enable='between(t,0,3)',"
            f"drawtext=text='{title}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"fontsize=50:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-150:enable='between(t,17,20)'[final];"
        )
        
        # Process audio - add fade and reduce volume
        filter_complex += "[4:a]afade=t=in:st=0:d=1,afade=t=out:st=18:d=2,volume=0.1[audio]"
        
        ffmpeg_cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[final]',
            '-map', '[audio]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '48000',
            '-shortest',
            '-movflags', '+faststart',
            '-y',
            output
        ])
    else:
        # For videos WITH audio - concatenate properly
        print("🔊 Preserving original audio from videos...")
        
        ffmpeg_cmd = ['ffmpeg']
        
        # Add all inputs
        for video_file in video_files:
            ffmpeg_cmd.extend(['-i', video_file])
        
        # Complex filter to handle both video and audio
        filter_complex = ""
        
        # Process each video
        for i in range(4):
            filter_complex += f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];"
            # If video has audio, prepare it
            filter_complex += f"[{i}:a]aresample=48000,aformat=fltp[a{i}];" if has_real_audio else ""
        
        # Concatenate with audio
        if has_real_audio:
            filter_complex += "[v0][a0][v1][a1][v2][a2][v3][a3]concat=n=4:v=1:a=1[outv][outa];"
        else:
            filter_complex += "[v0][v1][v2][v3]concat=n=4:v=1:a=0[outv];"
        
        # Add text overlays
        filter_complex += (
            f"[outv]drawtext=text='{hook}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize=80:fontcolor=yellow:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y=150:enable='between(t,0,3)',"
            f"drawtext=text='{title}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"fontsize=50:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-150:enable='between(t,17,20)'[final]"
        )
        
        ffmpeg_cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[final]'
        ])
        
        if has_real_audio:
            ffmpeg_cmd.extend(['-map', '[outa]'])
        
        ffmpeg_cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            output
        ])
    
    print("\n🎬 Merging videos with text overlays...")
    print(f"Command: ffmpeg {' '.join(ffmpeg_cmd[1:10])}...")
    
    try:
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        print("✓ Video merged successfully!")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: FFmpeg failed")
        print(f"STDERR: {e.stderr[-2000:]}")
        sys.exit(1)
    
    # Verify and analyze output
    if not os.path.exists(output) or os.path.getsize(output) == 0:
        print("ERROR: Output file not created or is empty")
        sys.exit(1)
    
    print(f"\n📼 Final video analysis:")
    print(f"✓ File: {output}")
    print(f"✓ Size: {os.path.getsize(output) / 1024 / 1024:.2f} MB")
    analyze_video(output)
    
    # Clean up
    for video_file in video_files:
        try:
            os.remove(video_file)
        except:
            pass
    
    return output

if __name__ == "__main__":
    videos = json.loads(os.environ.get('VIDEO_URLS', '[]'))
    hook = os.environ.get('HOOK_TEXT', 'AMAZING')
    title = os.environ.get('TITLE_TEXT', 'Viral Video')
    
    print("=" * 50)
    print(f"🎥 Processing {len(videos)} videos")
    print(f"💬 Hook: {hook}")
    print(f"📝 Title: {title}")
    print("=" * 50)
    
    if not videos or len(videos) != 4:
        print("ERROR: Need exactly 4 video URLs")
        sys.exit(1)
    
    try:
        output_file = merge_videos_with_text(videos, hook, title)
        print("\n✅ SUCCESS! Video processing complete.")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)