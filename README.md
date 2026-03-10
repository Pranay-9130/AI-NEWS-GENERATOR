# Ethical AI News Generator

Simple Flask application that asks Gemini (via the OpenAI Python library) to produce ethically‑framed news articles. It also integrates with the Hugging Face Inference API for on‑demand image generation, allowing each article to be paired with a relevant illustration.

## Setup

1. Clone or copy this project into a folder.
2. Create a virtual environment and activate it:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install flask python-dotenv google-generativeai requests
   ```
   Or use the requirements file:
   ```powershell
   pip install -r requirements.txt
   ```
4. Add your API keys to `.env`:
   ```dotenv
   GEMINI_API_KEY=your_gemini_api_key_here
   HUGGINGFACE_API_KEY=your_huggingface_api_key_here  # Optional, for image generation
   ```
   **Note:** Image generation works with or without Hugging Face API key. Without it, a placeholder will be used.

## Running

```powershell
python app.py
```

Then visit http://localhost:5000 in your browser.

## Usage

### Generate News Articles
Enter a topic, choose a moderation level and press **Generate Article**. The article will appear in the output box.

### Generate Images
Enter a topic and press **Generate Image** to create AI-generated images related to your topic. The system uses Gemini AI to enhance the prompt and then generates the image.

**Features:**
- ✨ Generate ethical news articles with AI
- 🎨 Generate images from topics
- 📥 Download articles and images
- 📤 Share content easily
- 📋 Copy to clipboard

## Notes

* If text appears unstyled, double-check that you are running via Flask (not opening the HTML directly).
* You can modify `style.css` to change colours.
* The project uses the new OpenAI `responses` API; adapt as needed for future model changes.
