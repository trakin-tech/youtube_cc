# 🎥 Trakin Tech Closed Caption Generator

A powerful Flask web application that processes YouTube videos to generate SRT subtitles and channel-specific video descriptions using AI. Built specifically for the Trakin Tech family of channels.

## ✨ Features

- **Multi-Channel Support**: Generate descriptions for 3 different channels:
  - Trakin Tech (Hindi/English)
  - Trakin Tech Marathi
  - Trakin Tech Tamil
- **YouTube Video Processing**: Download and process any YouTube video
- **AI-Powered Transcription**: Convert audio to accurate SRT subtitles using OpenAI Whisper
- **Smart Descriptions**: Generate channel-specific YouTube descriptions using Google Gemini AI
- **Real-time Progress Tracking**: Live updates during video processing
- **Modern Web Interface**: Beautiful, responsive UI with gradient design
- **Instant Downloads**: Download SRT files and descriptions immediately after processing

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API Key
- Google Gemini API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd youtube_cc
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # OpenAI API Configuration
   OPENAI_API_KEY=your-openai-api-key-here
   
   # Gemini API Configuration
   GEMINI_API_KEY=your-gemini-api-key-here
   ```

   **Get your API keys:**
   - OpenAI: https://platform.openai.com/api-keys
   - Gemini: https://aistudio.google.com/app/apikey

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open your browser**
   
   Navigate to `http://localhost:8080`

## 🎯 How to Use

1. **Select Channel**: Choose from Trakin Tech, Trakin Tech Marathi, or Trakin Tech Tamil
2. **Enter YouTube URL**: Paste any YouTube video URL
3. **Process Video**: Click "Process Video" and watch the real-time progress
4. **Download Files**: Get your SRT subtitles and AI-generated description

## 🏗️ Project Structure

```
youtube_cc/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (API keys)
├── templates/
│   └── index.html        # Web interface
└── README.md             # This file
```

## 🔧 Technical Details

### Dependencies

- **Flask 2.3.3**: Web framework
- **pytubefix 6.9.2**: YouTube video downloading
- **openai**: Whisper API for transcription
- **google-genai**: Gemini AI for description generation
- **python-dotenv 1.0.0**: Environment variable management

### AI Models Used

- **OpenAI Whisper**: For accurate audio transcription to SRT format
- **Google Gemini**: For generating channel-specific YouTube descriptions

### Channel-Specific Prompts

Each channel has customized AI prompts that generate descriptions in the appropriate language and style:

- **Trakin Tech**: Hindi/English mix with tech focus
- **Trakin Tech Marathi**: Casual Marathi tone with English tech terms
- **Trakin Tech Tamil**: Tamil descriptions with English tech vocabulary

## 🌐 Deployment

### Free Deployment Options

1. **Render** (Recommended)
   - 750 hours/month free
   - Easy Flask deployment
   - Automatic HTTPS

2. **Railway**
   - $5 monthly credits
   - Simple deployment process

3. **Fly.io**
   - 3 shared-cpu VMs free
   - Docker-based deployment

### Deployment Files Needed

Create these files for deployment:

**Procfile**:
```
web: python app.py
```

**runtime.txt**:
```
python-3.11.0
```

Update `app.py` for production:
```python
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
```

### Environment Variables for Deployment

Set these on your deployment platform:
- `OPENAI_API_KEY`: Your OpenAI API key
- `GEMINI_API_KEY`: Your Google Gemini API key
- `PORT`: Will be set automatically by the platform

## 🔒 Security Notes

- Never commit API keys to version control
- Use environment variables for all sensitive data
- The `.env` file is included in `.gitignore`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For issues or questions:
1. Check the console logs for error messages
2. Verify your API keys are correctly set
3. Ensure you have a stable internet connection
4. Check that the YouTube URL is valid and accessible

## 🔄 Recent Updates

- ✅ Added multi-channel support with dropdown selection
- ✅ Implemented channel-specific AI prompts
- ✅ Enhanced UI with modern gradient design
- ✅ Added real-time progress tracking
- ✅ Optimized for deployment on free platforms

---

**Built with ❤️ for the Trakin Tech community**