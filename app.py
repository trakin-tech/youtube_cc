from flask import Flask, render_template, request, jsonify, send_file
import os
import threading
import time
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import functions from existing scripts
from pytubefix import YouTube
from pytubefix.cli import on_progress
import openai
from google import genai
from google.genai import types
import requests
import re

app = Flask(__name__)

# Global variables for progress tracking
progress_data = {}

class YouTubeProcessor:
    def __init__(self):
        self.openai_client = None
        self.gemini_client = None
        
    def load_models(self):
        """Load OpenAI and Gemini API clients"""
        if self.openai_client is None:
            print("Initializing OpenAI client...")
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in the .env file.")
            
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
            
        if self.gemini_client is None:
            print("Initializing Gemini client...")
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in the .env file.")
            
            self.gemini_client = genai.Client(
                api_key=gemini_api_key,
            )
    
    def download_audio_api(self, url, session_id):
        """Download audio using YouTube to MP3 API as fallback"""
        try:
            progress_data[session_id]['status'] = 'Downloading via API...'
            progress_data[session_id]['progress'] = 15
            
            # Extract video ID from URL
            video_id = self.extract_video_id(url)
            if not video_id:
                raise Exception("Could not extract video ID from URL")
            
            # Use the API to get download link
            api_url = f"https://api.vevioz.com/api/button/mp3/{video_id}"
            
            progress_data[session_id]['progress'] = 25
            
            # Make request to API
            response = requests.get(api_url, timeout=30)
            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}")
            
            # The API returns HTML with download links, we need to parse it
            # Look for download links in the response
            download_links = re.findall(r'href="([^"]*\.mp3[^"]*)"', response.text)
            
            if not download_links:
                raise Exception("No download links found in API response")
            
            progress_data[session_id]['progress'] = 40
            
            # Use the first download link
            download_url = download_links[0]
            
            # Get video title for filename
            yt = YouTube(url)
            title = yt.title
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            
            progress_data[session_id]['video_title'] = title
            progress_data[session_id]['progress'] = 50
            
            # Download the audio file
            audio_response = requests.get(download_url, timeout=60)
            if audio_response.status_code != 200:
                raise Exception(f"Audio download failed with status {audio_response.status_code}")
            
            # Save the file
            audio_file = f"{safe_title}.mp3"
            with open(audio_file, 'wb') as f:
                f.write(audio_response.content)
            
            progress_data[session_id]['progress'] = 70
            progress_data[session_id]['audio_file'] = audio_file
            
            return audio_file, safe_title
            
        except Exception as e:
            progress_data[session_id]['error'] = f"API download error: {str(e)}"
            raise e
    
    def extract_video_id(self, url):
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:v\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def download_audio(self, url, session_id):
        """Download audio from YouTube URL with fallback methods"""
        try:
            progress_data[session_id]['status'] = 'Downloading audio...'
            progress_data[session_id]['progress'] = 10
            
            # Try pytubefix first
            try:
                yt = YouTube(url, on_progress_callback=on_progress)
                title = yt.title
                
                # Clean title for filename
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                progress_data[session_id]['video_title'] = title
                progress_data[session_id]['progress'] = 30
                
                ys = yt.streams.get_audio_only()
                audio_file = ys.download(filename=f"{safe_title}.m4a")
                
                progress_data[session_id]['progress'] = 50
                progress_data[session_id]['audio_file'] = audio_file
                
                return audio_file, safe_title
                
            except Exception as pytubefix_error:
                print(f"Pytubefix failed: {pytubefix_error}")
                progress_data[session_id]['status'] = 'Trying alternative method...'
                
                # Fallback to API method
                return self.download_audio_api(url, session_id)
            
        except Exception as e:
            progress_data[session_id]['error'] = f"Download error: {str(e)}"
            raise e
    
    def transcribe_audio(self, audio_file, safe_title, session_id):
        """Translate audio to English using OpenAI Whisper API"""
        try:
            progress_data[session_id]['status'] = 'Translating audio to English...'
            progress_data[session_id]['progress'] = 60
            
            # Use OpenAI Whisper API for translation to English
            with open(audio_file, "rb") as audio_file_obj:
                print(f"Translating {audio_file} to English using OpenAI Whisper API...")
                
                # Use the translations endpoint to translate to English
                response = self.openai_client.audio.translations.create(
                    model="whisper-1",
                    file=audio_file_obj,
                    response_format="srt"  # Get SRT format directly
                )
            
            progress_data[session_id]['progress'] = 80
            
            # Save SRT file
            output_dir = '/Users/amanattar/Developer/youtube_CC/'
            srt_file = os.path.join(output_dir, f"{safe_title}.srt")
            
            with open(srt_file, 'w', encoding='utf-8') as f:
                f.write(response)
            
            progress_data[session_id]['srt_file'] = srt_file
            
            return srt_file, response
            
        except Exception as e:
            progress_data[session_id]['error'] = f"Translation error: {str(e)}"
            raise e
    
    def convert_srt_to_text(self, srt_content):
        """Convert SRT subtitle content to plain text"""
        import re
        
        # Remove subtitle numbers and timestamps
        # Pattern to match SRT format: number, timestamp, text
        lines = srt_content.split('\n')
        text_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
                
            # Skip subtitle numbers (lines that are just digits)
            if line.isdigit():
                i += 1
                continue
                
            # Skip timestamp lines (contain -->)
            if '-->' in line:
                i += 1
                continue
                
            # This should be subtitle text - clean it up
            # Remove any HTML tags that might be in SRT
            clean_line = re.sub(r'<[^>]+>', '', line)
            # Remove extra whitespace
            clean_line = re.sub(r'\s+', ' ', clean_line).strip()
            
            if clean_line:  # Only add non-empty lines
                text_lines.append(clean_line)
            i += 1
        
        # Join all text lines with spaces and clean up
        full_text = ' '.join(text_lines)
        # Remove multiple spaces and normalize
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        return full_text
    
    def get_channel_prompt(self, channel, srt_content):
        """Get channel-specific prompt for video description generation"""
        
        if channel == 'trakin_tech_marathi':
            return f"""<Task>
You are a YouTube video assistant. Based on the following .srt subtitles file, generate a Marathi YouTube video description in Trakin Tech style.
Your output should include:
A one-line hook in Marathi introducing the video (casual, engaging tone).
A short Marathi description summarizing the video.
SEO-optimized hashtags from product name, series, and video theme.
Buy/product links (if found in transcript, else add a placeholder link).
Disclaimer if mentioned.
Chapter titles with timestamps (auto-extracted from SRT).
Social Media Handles section in Marathi.
Follow this formatting example:
ह्या video मध्ये आपण iPhone 17 चं unboxing आणि Quick Review घेणार आहोत. Apple ने यावेळी base iPhone 17 मध्ये mast अपग्रेड्स दिलेत, 120Hz display, powerful performance आणि upgraded camera setup. हा iPhone खरंच वर्थ आहे का हे detail मध्ये या video मध्ये पाहूया!

Buy iPhone 17 here: `https://fktr.in/4P86gPb`

#iPhone17 #iPhone17Unboxing #TrakinTechMarathi

Highlights
0:00 Introduction
0:41 Unboxing
1:04 Design, In-Hand Feel & Build
2:32 Ports & Buttons
3:06 Display Upgrade
3:27 Performance & Gaming
3:48 Battery & Charging
4:19 Connectivity & Other Features
4:52 Camera Setup
5:38 Selfie Camera
6:16 My Opinion: iPhone 17 vs iPhone 16 Pro
7:15 Made in India!
7:34 What's Next?

Social Media Handles
Follow us on:
Web: `http://trak.in`
Instagram: `https://www.instagram.com/trakintech`
Twitter: `https://www.twitter.com/trakintech`
Twitter personal: `https://www.twitter.com/8ap`
Facebook: `https://www.facebook.com/trakintech`
For enquiries or product promotions get in touch with us on Youtube@trak.in
</Task>

<Inputs>
<Transcript>
{srt_content}
</Transcript>
</Inputs>

<Instructions>
Parse the SRT to detect video flow and topics.
Use Marathi casual YouTube tone.
Build chapter highlights with exact timestamps.
Summarize overall video in 3–4 lines.
Add SEO-rich hashtags at the bottom.
Include social handles and links in the given format.
Output everything inside <video_description> tags.
</Instructions>"""

        elif channel == 'trakin_tech_tamil':
            return f"""<Task>
You are a YouTube video content assistant. Based on the provided `.srt` transcript, generate a Tamil YouTube video description in Trakin Tech style.

Your output should include:
1. A one-line Tamil hook introducing the video.
2. A short Tamil summary encouraging viewers to watch, like, and share.
3. Disclaimer if the device was provided by a brand.
4. Product or camera sample links (if mentioned in transcript, else use placeholders).
5. SEO-optimized Tamil + English hashtags.
6. Timestamp-based chapter titles (auto-detected from the SRT).
7. "Subscribe to our channels" section with the links.
8. Format everything exactly like a YouTube description block.

Here's the reference format to follow:

---
இந்த வீடியோவில், Legacy பிராண்டுகளின் சந்தையில் சிறந்த Compact ஃபிளாக்ஷிப்களை ஒப்பிட்டுப் பார்த்தோம்! iPhone 17 vs Pixel 10 vs Galaxy S25. நீங்கள் வாங்கக்கூடிய சிறந்த காம்பாக்ட் ஃபிளாக்ஷிப் எது என்பதை இந்த வீடியோவிலிருந்து கண்டுபிடிக்கவும்.

இந்த மதிப்பாய்வு Phone, Brand-ஆல் வழங்கப்பட்டுள்ளது. இருப்பினும், வீடியோவில் உள்ள கருத்துகள் முற்றிலும் எனது தனிப்பட்ட பயன்பாட்டை அடிப்படையாகக் கொண்டவை.

Checkout the Camera Samples: `https://bit.ly/46WAT9Z`

#Pixel10 #iPhone17 #GalaxyS25

=============================
00:00 Introduction
00:58 Design
03:12 Display
04:48 Performance
08:31 Camera
11:12 Software
13:00 Conclusion
===============================

Subscribe to our other channels:
Trakin Tech  - `https://www.youtube.com/c/TrakinTech`
Trakin Tech English - `https://www.youtube.com/c/TrakinTechEnglish`
Trakin Tech Marathi - `https://www.youtube.com/c/TrakinTechMarathi`
Trakin Auto - `https://www.youtube.com/c/TrakinAuto`
---
</Task>

<Inputs>
<Transcript>
{srt_content}
</Transcript>
</Inputs>

<Instructions>
- Analyze the SRT transcript to detect the main sections of the video.
- Use casual Tamil tone with some English tech words (like performance, display, etc.).
- Generate an engaging SEO-optimized description in Tamil.
- Extract timestamps as chapter titles from the SRT file.
- Add hashtags based on product names and brands.
- Include disclaimers, links, and subscribe section as shown in the template.
- Output everything inside <video_description> tags.
</Instructions>"""

        else:  # Default to 'trakin_tech' (English/Hindi)
            return f"""You are a professional YouTube content creator for the Trakin Tech channel. Generate a complete YouTube video description in Hindi based on the provided transcript.

Your output should include:
- A one-line Hindi hook at the top describing the video.
- A short summary in Hindi encouraging users to watch, like, and share.
- SEO-friendly hashtags relevant to the video content.
- Camera samples / product links (if mentioned in the transcript, otherwise use dummy placeholders).
- A disclaimer in Hindi if the video is brand-sponsored (as indicated in the transcript).
- Promotional links (for music, Telegram, etc.) using the TrakinTech style.
- A standard block of social media handles.
- Auto-extracted chapter titles with timestamps based on the key topics discussed in the transcript. The chapter titles should be descriptive and in the specific format requested by the user.

Use this example as a reference for the overall output formatting, including the use of asterisks and headers:

Doston Aaj Hum Unbox Kar Rahe Hain All New iPhone Air Ko, To Aap Ye Video Ant Tak Dekhiye Aur Video Ko Like Aur Share Karna Na Bhoole.

#iPhoneAir #iPhone17Series #iPhoneAirUnboxing #TrakinTech

Check Out iPhone Air : `https://fkart.openinapp.co/r81su`

The Device shown in the video has been provided by respective brand. However, opinion mentioned in this video is completely personal and based on my usage only.

"Safar - The 10 Million Rap"
Streaming On All Platforms Listen or Set Your Callertune Enjoy & Stay Connected With Us !
♫ 𝐉𝐢𝐨 𝐒𝐚𝐚𝐯𝐧 - `https://bit.ly/3iWUfm4`
♫ 𝐆𝐚𝐚𝐧𝐚 - `https://bit.ly/2YHUdaY`
♫ 𝐀𝐩𝐩𝐥𝐞 𝐌𝐮𝐬𝐢𝐜 - `https://apple.co/3mQfwPy`
♫ 𝐒𝐩𝐨𝐭𝐢𝐟𝐲 - `https://spoti.fi/3oY1bmA`
♫ 𝐘𝐨𝐮𝐭𝐮𝐛𝐞 𝐌𝐮𝐬𝐢𝐜 - `https://bit.ly/3Ax2yuF`
♫ 𝐀𝐦𝐚𝐳𝐨𝐧 𝐌𝐮𝐬𝐢𝐜 - `https://amzn.to/3veYSgk`

Official TrakinTech Telegram Channel - `https://t.me/officialtrakintech`

Video Highlights
00:00 Introduction
00:35 Alienware Aurora 16 & 16X Unboxing
01:43 Alienware Aurora 16 & 16X Design
02:05 Alienware Aurora 16 & 16X Ports
03:29 Alienware Aurora 16 & 16X Dislpay
04:25 Alienware Aurora 16 & 16X Specifications
05:52 Alienware Aurora 16 & 16X Multimedia
06:19 Alienware Aurora 16 & 16X Battery
07:02 Alienware Aurora 16 & 16X Software
07:50 Alienware Aurora 16 & 16X Performance
09:04 Alienware Aurora 16 & 16X Connectivity
09:45 Alienware Aurora 16 & 16X Price

Social Media Handles
Follow us on:
Web: `http://trak.in`
Telegram : `https://t.me/officialtrakintech`
Instagram: `https://instagram.com/trakintech`
Twitter: `https://twitter.com/trakintech`
Twitter personal: `https://twitter.com/8ap`
Facebook: `https://www.facebook.com/TrakinTech`
English Trakin Tech YouTube Channel - `https://www.youtube.com/c/TrakinTechEnglish`

<Task>
Analyze the provided transcript and generate the complete YouTube description as specified.
</Task>

<Inputs>
<Transcript>
{srt_content}
</Transcript>
</Inputs>

<Instructions>
Carefully analyze the transcript to identify all major topic changes for chapter creation.
Map the identified topics to their exact start times to create accurate timestamps.
Ensure the chapter titles are descriptive, as shown in the example format (e.g., "Alienware Aurora 16 & 16X Design").
Maintain a casual, conversational Hindi tone throughout the description.
Use dummy links for products and promotions if not mentioned in the text.
Wrap the final, complete output inside <video_description> tags.
</Instructions>"""

    def generate_description(self, srt_file, session_id):
        """Generate YouTube description using Gemini with channel-specific prompts"""
        try:
            progress_data[session_id]['status'] = 'Generating description...'
            progress_data[session_id]['progress'] = 90
            
            # Get channel from progress data
            channel = progress_data[session_id].get('channel', 'trakin_tech')
            
            # Read raw SRT content with timestamps
            with open(srt_file, 'r', encoding='utf-8') as file:
                srt_content = file.read()
            
            print(f"Debug: SRT content length: {len(srt_content)} characters")
            print(f"Debug: Selected channel: {channel}")
            
            # Check if we have meaningful content
            if len(srt_content.strip()) < 50:
                raise ValueError(f"SRT content is too short ({len(srt_content)} chars). File may be empty or corrupted.")
            
            # Get channel-specific prompt
            prompt = self.get_channel_prompt(channel, srt_content)

            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            ]
            
            tools = [types.Tool(googleSearch=types.GoogleSearch())]
            
            # Remove ThinkingConfig to fix the API error
            generate_content_config = types.GenerateContentConfig(
                tools=tools,
            )

            response_text = ""
            for chunk in self.gemini_client.models.generate_content_stream(
                model="gemini-2.5-pro",
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    response_text += chunk.text

            # Save description to file
            description_file = srt_file.replace('.srt', '_description.txt')
            with open(description_file, 'w', encoding='utf-8') as file:
                file.write(response_text)
            
            progress_data[session_id]['description_file'] = description_file
            progress_data[session_id]['progress'] = 100
            progress_data[session_id]['status'] = 'Completed!'
            
            return description_file, response_text
            
        except Exception as e:
            progress_data[session_id]['error'] = f"Description generation error: {str(e)}"
            raise e

processor = YouTubeProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json()
        url = data.get('url')
        channel = data.get('channel')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        if not channel:
            return jsonify({'error': 'No channel selected'}), 400
        
        # Generate session ID
        session_id = str(int(time.time()))
        
        # Initialize progress data
        progress_data[session_id] = {
            'status': 'Starting...',
            'progress': 0,
            'video_title': '',
            'audio_file': '',
            'srt_file': '',
            'description_file': '',
            'channel': channel,
            'error': None
        }
        
        # Start processing in background thread
        thread = threading.Thread(target=process_video_background, args=(url, session_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({'session_id': session_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_video_background(url, session_id):
    try:
        # Load models
        processor.load_models()
        
        # Download audio
        audio_file, safe_title = processor.download_audio(url, session_id)
        
        # Transcribe audio
        srt_file, result = processor.transcribe_audio(audio_file, safe_title, session_id)
        
        # Generate description
        description_file, description_text = processor.generate_description(srt_file, session_id)
        
        # Clean up audio file
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
    except ValueError as e:
        # Handle API key validation errors specifically
        progress_data[session_id]['error'] = f"Configuration error: {str(e)}"
        progress_data[session_id]['status'] = 'Configuration error - check API keys'
    except Exception as e:
        progress_data[session_id]['error'] = str(e)
        progress_data[session_id]['status'] = 'Error occurred'

@app.route('/progress/<session_id>')
def get_progress(session_id):
    return jsonify(progress_data.get(session_id, {'error': 'Session not found'}))

@app.route('/download/<session_id>/<file_type>')
def download_file(session_id, file_type):
    try:
        session = progress_data.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if file_type == 'srt':
            file_path = session.get('srt_file')
        elif file_type == 'description':
            file_path = session.get('description_file')
        else:
            return jsonify({'error': 'Invalid file type'}), 400
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)