from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import requests
import base64
import time
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# load environment variables from .env (e.g. GEMINI_API_KEY)
load_dotenv()

# Prompt templates for different moderation levels
PROMPT_TEMPLATES = {
    'low': "Write a simple news article about '{topic}'. Minimal moderation is required; the tone may be casual but refrain from profanity.",
    'moderate': "Write an ethical news article about '{topic}' using a moderate moderation level. Prioritize neutrality, factual accuracy, and avoid biased or sensational language.",
    'strict': "Write a strictly ethical news article about '{topic}' with high moderation. Ensure the content is unbiased, fact-checked, free of speculation, and adheres to journalistic integrity."
}

def build_article_prompt(topic: str, level: str) -> str:
    """Return a prompt string adapted for the requested moderation level."""
    key = level.strip().lower()
    template = PROMPT_TEMPLATES.get(key, PROMPT_TEMPLATES['moderate'])
    return template.format(topic=topic)

# import Google Generative AI library
import google.generativeai as genai

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Generate a news article using Gemini API."""
    data = request.get_json() or {}
    topic = data.get('topic', '').strip()
    level = data.get('level', 'Moderate')

    if not topic:
        return jsonify({'article': 'Please provide a topic.'})

    # select one of several templates depending on moderation level
    prompt = build_article_prompt(topic, level)

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({'article': 'API key not configured.'})

    # configure and use Gemini API
    try:
        genai.configure(api_key=api_key)
        # Using gemini-flash-latest as it is confirmed to be available and likely has more quota
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        article = response.text.strip()
    except Exception as exc:
        article = f'Error generating article: {exc}'

    return jsonify({'article': article})

def _prepare_image_for_gemini(file):
    """Read uploaded image file, normalize (RGB, reasonable size), return (bytes, mime_type)."""
    image_data = file.read()
    if not image_data:
        raise ValueError("Image file is empty")
    image = Image.open(BytesIO(image_data))
    # Convert to RGB (Gemini can fail on RGBA or palette mode)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    elif image.mode == "L":
        image = image.convert("RGB")
    # Resize if very large to stay within API limits
    max_size = 2048
    w, h = image.size
    if w > max_size or h > max_size:
        ratio = min(max_size / w, max_size / h)
        new_size = (int(w * ratio), int(h * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    buf = BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf.read(), "image/png"


def _pdf_first_page_to_png_bytes(file):
    """
    Convert the first page of an uploaded PDF brochure into PNG bytes for Gemini Vision.
    Requires PyMuPDF (`pip install pymupdf`). If unavailable, a clear error is raised.
    """
    try:
        import fitz  # type: ignore[import]  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PDF brochures are not supported on this server yet "
            "(PyMuPDF is not installed). Please install 'pymupdf' or "
            "upload the brochure as an image (JPG/PNG)."
        ) from exc

    pdf_bytes = file.read()
    if not pdf_bytes:
        raise ValueError("PDF file is empty")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise ValueError("PDF has no pages to analyze")

    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("png")
    return img_bytes, "image/png"

def _get_gemini_vision_model():
    """
    Return a Gemini model name that works with the installed SDK/API version.
    Prefer the same model family you already use for text generation.
    """
    # `gemini-1.5-flash-latest` is not available for some v1beta setups.
    # `gemini-flash-latest` works in your app's /generate route, so prefer it here too.
    return os.getenv("GEMINI_VISION_MODEL", "gemini-flash-latest")

def _get_gemini_text_model():
    return os.getenv("GEMINI_TEXT_MODEL", "gemini-flash-latest")

def _hf_inference_headers():
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    if not hf_api_key:
        return None
    # Accept an image directly (HF may otherwise return JSON)
    return {"Authorization": f"Bearer {hf_api_key}", "Accept": "image/*"}

def _hf_generate_image(prompt: str):
    """
    Generate an image from text via Hugging Face Inference API.
    Retries when model is loading (503) using estimated_time.
    """
    headers = _hf_inference_headers()
    if not headers:
        raise ValueError("HUGGINGFACE_API_KEY is not configured in .env")

    primary_model = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-2-1")
    fallback_model = os.getenv("HF_IMAGE_MODEL_FALLBACK", "runwayml/stable-diffusion-v1-5")
    models_to_try = [m for m in [primary_model, fallback_model] if m]

    last_error = None
    base_url = os.getenv("HF_INFERENCE_BASE_URL", "https://router.huggingface.co/hf-inference/models").rstrip("/")

    for model_id in models_to_try:
        api_url = f"{base_url}/{model_id}"
        payload = {"inputs": prompt}

        # Try a few times if the model is loading
        for _ in range(4):
            resp = requests.post(api_url, headers=headers, json=payload, timeout=90)

            if resp.status_code == 200:
                ctype = resp.headers.get("content-type", "")
                if ctype.startswith("image/"):
                    return resp.content, ctype, model_id
                # Sometimes AHF returns JSON errors even with 200
                try:
                    j = resp.json()
                except Exception:
                    j = resp.text
                raise RuntimeError(f"Hugging Face returned non-image response. Details: {j}")

            # Model loading
            if resp.status_code == 503:
                try:
                    j = resp.json()
                except Exception:
                    j = {}
                wait_s = j.get("estimated_time")
                if isinstance(wait_s, (int, float)) and wait_s > 0:
                    time.sleep(min(float(wait_s), 15.0))
                    continue
                time.sleep(3)
                continue

            # HF legacy endpoint deprecation
            if resp.status_code == 410 and "api-inference.huggingface.co" in str(resp.text):
                # If user set the old base url, transparently retry with router
                base_url = "https://router.huggingface.co/hf-inference/models"
                api_url = f"{base_url}/{model_id}"
                continue

            # Other errors - capture and break to fallback model
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            last_error = f"HF model '{model_id}' error {resp.status_code}: {err}"
            break

    raise RuntimeError(last_error or "Hugging Face image generation failed.")

def _stability_headers():
    key = os.getenv("STABILITY_API_KEY", "").strip()
    if not key:
        return None
    return {"Authorization": f"Bearer {key}", "Accept": "image/*"}

def _stability_generate_image(prompt: str, aspect_ratio: str = "1:1", output_format: str = "png"):
    """
    Stability AI Stable Image (Core) text-to-image.
    Uses multipart/form-data and requests raw image bytes.
    """
    headers = _stability_headers()
    if not headers:
        raise ValueError("STABILITY_API_KEY is not configured in .env")

    host = os.getenv("STABILITY_BASE_URL", "https://api.stability.ai").rstrip("/")
    # Some accounts/docs use /v2beta/..., others /sd/v2beta/...
    candidate_paths = [
        "/v2beta/stable-image/generate/core",
        "/sd/v2beta/stable-image/generate/core",
    ]

    # Force multipart/form-data by using `files` with (None, value)
    files = {
        "prompt": (None, prompt),
        "aspect_ratio": (None, aspect_ratio),
        "output_format": (None, output_format),
    }

    last_error = None
    for path in candidate_paths:
        url = f"{host}{path}"
        resp = requests.post(url, headers=headers, files=files, timeout=120)
        if resp.status_code == 200:
            ctype = resp.headers.get("content-type", "")
            if ctype.startswith("image/"):
                return resp.content, ctype, f"{host}{path}"
            # Some errors may still come back as JSON
            try:
                j = resp.json()
            except Exception:
                j = resp.text
            raise RuntimeError(f"Stability returned non-image response. Details: {j}")

        # capture error and try next path
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        last_error = f"Stability error {resp.status_code} at {path}: {err}"
        # If auth is wrong, no need to try other paths
        if resp.status_code in (401, 403):
            break

    raise RuntimeError(last_error or "Stability image generation failed.")


@app.route('/generate-image', methods=['POST'])
def generate_image():
    """
    Generate an image from a topic or pasted content.
    Uses Gemini to craft a good prompt, then Hugging Face to generate the image.
    """
    data = request.get_json() or {}
    topic = (data.get("topic") or "").strip()
    content = (data.get("content") or "").strip()

    if not topic and not content:
        return jsonify({"error": "Please provide a topic or content.", "image_url": None}), 400

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY not configured.", "image_url": None}), 500

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(_get_gemini_text_model())

        basis = content if content else topic
        basis = basis[:2500]  # keep prompt-building bounded

        prompt_enhancement = (
            "Create a single, high-quality text-to-image prompt for a professional social media/event visual. "
            "It should be safe, brand-friendly, and not include any logos or copyrighted characters. "
            "Return ONLY the prompt, no extra text.\n\n"
            f"Source text:\n{basis}"
        )

        resp = model.generate_content(prompt_enhancement)
        enhanced_prompt = (resp.text or "").strip()
        if not enhanced_prompt:
            return jsonify({"error": "Failed to create an image prompt from the given text.", "image_url": None}), 400

        # Prefer Stability AI if configured (more reliable), otherwise fall back to Hugging Face.
        aspect_ratio = (data.get("aspect_ratio") or "1:1").strip()
        provider = (data.get("provider") or os.getenv("IMAGE_PROVIDER", "")).strip().lower()

        used_model = None
        if provider in ("stability", "stabilityai") or (_stability_headers() and provider not in ("hf", "huggingface")):
            image_bytes, content_type, used_model = _stability_generate_image(enhanced_prompt, aspect_ratio=aspect_ratio)
            provider_used = "stability"
        else:
            image_bytes, content_type, used_model = _hf_generate_image(enhanced_prompt)
            provider_used = "huggingface"

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return jsonify({
            "image_url": f"data:{content_type};base64,{image_b64}",
            "prompt": enhanced_prompt,
            "provider": provider_used,
            "model": used_model,
            "error": None
        })
    except Exception as exc:
        return jsonify({"error": f"Error generating image: {str(exc)}", "image_url": None}), 500


@app.route('/analyze-event-image', methods=['POST'])
def analyze_event_image():
    """Analyze an uploaded image or brochure and generate social media content using Gemini Vision."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({'error': 'API key not configured.'}), 500
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)

        # Prepare image or brochure: if PDF, convert first page to image; otherwise normalize image
        mimetype = (file.mimetype or "").lower()
        filename_lower = (file.filename or "").lower()
        if mimetype == "application/pdf" or filename_lower.endswith(".pdf"):
            image_bytes, mime_type = _pdf_first_page_to_png_bytes(file)
        else:
            image_bytes, mime_type = _prepare_image_for_gemini(file)
        # Pass as base64 string (API/JSON uses this); SDK may accept bytes too
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_part = {"inline_data": {"mime_type": mime_type, "data": image_b64}}
        
        # Use Gemini Vision model
        model = genai.GenerativeModel(_get_gemini_vision_model())
        
        # Step 1: Analyze image/brochure and extract key details.
        # This prompt is intentionally strict so we only show information that
        # actually appears in the brochure/poster (no guessing).
        analysis_prompt = """
        You are reading an academic event, workshop, course, or brochure poster.
        Extract ONLY the information that clearly appears in the image.
        Do NOT invent or guess missing information.
        Use only plain text for each value—no markdown, no asterisks, no bold formatting.

        Provide each line in this exact format (label followed by colon and space, then the value):
        1. Tech Event Name: (full name of the event / course / workshop as written)
        2. Organising Department: (department or organisation hosting the event, exactly as written)
        3. Date: (event date if visible)
        4. Start Time: (start time if visible)
        5. End Time: (end time if visible)
        6. Title: (main topic or heading of the event / course if it is separate from the event name)
        7. Purpose: (purpose or objective stated in the brochure)
        8. Key Persons / Authors / Speakers: (all named people such as authors, speakers, resource persons, coordinators, convenors, directors, etc., exactly as written)

        If any information is not visible in the image, use EXACTLY this text for that line: Not visible in image
        Be specific and detailed based ONLY on what you can see in the brochure or poster.
        """
        
        try:
            response = model.generate_content([image_part, analysis_prompt])
        except Exception as exc:
            # Fallback for environments where the preferred model name isn't available
            # (common with older/v1beta endpoints).
            fallback_name = os.getenv("GEMINI_VISION_MODEL_FALLBACK", "gemini-1.5-flash")
            if fallback_name and fallback_name != _get_gemini_vision_model():
                try:
                    model = genai.GenerativeModel(fallback_name)
                    response = model.generate_content([image_part, analysis_prompt])
                except Exception:
                    raise exc
            else:
                raise
        
        # Handle blocked or empty response
        if not response.candidates:
            block_reason = "Unknown"
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason = str(response.prompt_feedback.block_reason)
            return jsonify({
                'error': f'Image was not analyzed (blocked or empty). Reason: {block_reason}. Try a different image.',
                'event_details': {},
                'content': {}
            }), 400
        analysis_result = response.text.strip()
        if not analysis_result:
            return jsonify({
                'error': 'Analysis returned no text. Try a different image or check the image content.',
                'event_details': {},
                'content': {}
            }), 400
        
        # Parse the analysis to extract structured data (simple parsing)
        event_details = parse_event_details(analysis_result)
        
        # Step 2: Generate content for different platforms using RAG-like approach
        # Build context from the analysis
        context = f"""
        Tech Event Name: {event_details.get('tech_event_name', 'Not visible in image')}
        Organising Department: {event_details.get('organising_department', 'Not visible in image')}
        Date: {event_details.get('date', 'Not visible in image')}
        Start Time: {event_details.get('start_time', 'Not visible in image')}
        End Time: {event_details.get('end_time', 'Not visible in image')}
        Title: {event_details.get('title', 'Not visible in image')}
        Purpose: {event_details.get('purpose', 'Not visible in image')}
        Key Persons / Authors / Speakers: {event_details.get('key_persons', 'Not visible in image')}
        Additional Details (raw analysis): {analysis_result}
        """
        
        # Generate LinkedIn post (professional, detailed)
        linkedin_prompt = f"""
        Based on this event information:
        {context}
        
        Create an engaging LinkedIn post about this event. The post should:
        - Be professional and informative
        - Highlight the key benefits and learning outcomes
        - Include relevant hashtags (3-5 hashtags)
        - Be 200-300 words
        - Encourage engagement and networking
        - Mention the value for participants
        
        Write ONLY the post content, no additional text.
        """
        
        def _safe_text(r):
            try:
                return (r.text or "").strip() if r and r.candidates else ""
            except Exception:
                return ""

        linkedin_response = model.generate_content(linkedin_prompt)
        linkedin_content = _safe_text(linkedin_response) or "Could not generate LinkedIn post."
        
        # Generate Instagram post (visual, engaging, shorter)
        instagram_prompt = f"""
        Based on this event information:
        {context}
        
        Create an engaging Instagram post about this event. The post should:
        - Be visually appealing and engaging
        - Use emojis appropriately (2-4 emojis)
        - Be concise (150-200 words)
        - Include a call-to-action
        - Use relevant hashtags (5-8 hashtags)
        - Be friendly and approachable
        - Highlight the exciting aspects
        
        Write ONLY the post content, no additional text.
        """
        
        instagram_response = model.generate_content(instagram_prompt)
        instagram_content = _safe_text(instagram_response) or "Could not generate Instagram post."
        
        # Generate WhatsApp Status (very short, catchy)
        whatsapp_prompt = f"""
        Based on this event information:
        {context}
        
        Create a catchy WhatsApp status message about this event. The status should:
        - Be very short (50-100 words max)
        - Be engaging and attention-grabbing
        - Use emojis (3-5 emojis)
        - Include key highlights
        - Be casual and friendly
        - Encourage participation
        
        Write ONLY the status content, no additional text.
        """
        
        whatsapp_response = model.generate_content(whatsapp_prompt)
        whatsapp_content = _safe_text(whatsapp_response) or "Could not generate WhatsApp status."
        
        return jsonify({
            'event_details': event_details,
            'content': {
                'linkedin': linkedin_content,
                'instagram': instagram_content,
                'whatsapp': whatsapp_content
            },
            'error': None
        })
        
    except Exception as exc:
        return jsonify({
            'error': f'Error analyzing image: {str(exc)}',
            'event_details': {},
            'content': {}
        }), 500

def _strip_markdown(text):
    """Remove markdown asterisks and extra whitespace from parsed values."""
    if not text or not isinstance(text, str):
        return text or ''
    t = text.strip().strip('*').strip()
    return t if t else ''


def parse_event_details(analysis_text):
    """Parse the analysis text to extract structured event details."""
    details = {
        # Defaults are conservative so we don't show misleading values.
        'tech_event_name': 'Not visible in image',
        'organising_department': 'Not visible in image',
        'date': 'Not visible in image',
        'start_time': 'Not visible in image',
        'end_time': 'Not visible in image',
        'title': 'Not visible in image',
        'purpose': 'Not visible in image',
        'key_persons': 'Not visible in image',
    }
    
    lines = analysis_text.split('\n')
    for line in lines:
        line_lower = line.lower().strip()
        if 'tech event name' in line_lower:
            parts = line.split(':', 1)
            if len(parts) > 1:
                details['tech_event_name'] = _strip_markdown(parts[1]) or details['tech_event_name']
        elif 'organising department' in line_lower:
            parts = line.split(':', 1)
            if len(parts) > 1:
                details['organising_department'] = _strip_markdown(parts[1]) or 'N/A'
        elif line_lower.startswith('date:') and 'start' not in line_lower and 'end' not in line_lower:
            parts = line.split(':', 1)
            if len(parts) > 1:
                details['date'] = _strip_markdown(parts[1]) or 'N/A'
        elif 'start time' in line_lower:
            parts = line.split(':', 1)
            if len(parts) > 1:
                details['start_time'] = _strip_markdown(parts[1]) or 'N/A'
        elif 'end time' in line_lower:
            parts = line.split(':', 1)
            if len(parts) > 1:
                details['end_time'] = _strip_markdown(parts[1]) or 'N/A'
        elif line_lower.startswith('title:'):
            parts = line.split(':', 1)
            if len(parts) > 1:
                details['title'] = _strip_markdown(parts[1]) or details['title']
        elif line_lower.startswith('purpose:'):
            parts = line.split(':', 1)
            if len(parts) > 1:
                details['purpose'] = _strip_markdown(parts[1]) or details['purpose']
        elif 'key persons' in line_lower or 'authors' in line_lower or 'speakers' in line_lower or 'resource persons' in line_lower or 'resource person' in line_lower or 'coordinator' in line_lower or 'convenor' in line_lower:
            parts = line.split(':', 1)
            if len(parts) > 1:
                details['key_persons'] = _strip_markdown(parts[1]) or details['key_persons']
    
    return details

# optionally serve static files explicitly (Flask does this automatically)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
