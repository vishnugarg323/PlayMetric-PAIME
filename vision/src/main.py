"""
Vision AI Service - LLaVA/GPT-4V/Gemini for Game Screen Analysis
Separated from agent for better monitoring and resource management

This service handles:
- LLaVA vision AI model loading and inference
- Gemini/GPT-4V API calls
- OCR text extraction
- Batch image analysis (16 images/second)
- Game screen understanding
"""
import os
import logging
import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global model state
llava_model = None
llava_processor = None
ocr_reader = None
model_loaded = False
ocr_loaded = False
loading_progress = {"status": "not_started", "progress": 0, "stage": ""}
warmup_complete = False
batch_processor = None  # Intelligent batch processing for 16 FPS


class AnalysisRequest(BaseModel):
    screenshot_path: str
    context: Optional[Dict[str, Any]] = None
    model_type: str = "llava"  # llava, gpt4v, gemini


class BatchAnalysisRequest(BaseModel):
    """Analyze batch of 16 screenshots captured in 1 second"""
    screenshot_paths: List[str]
    context: Optional[Dict[str, Any]] = None
    model_type: str = "llava"


class AnalysisResponse(BaseModel):
    scene_type: str
    recommended_action: Dict[str, Any]
    game_context: str
    visual_features: list
    confidence: float
    ocr_text: Optional[str] = None
    buttons_detected: Optional[List[Dict]] = None


async def load_ocr():
    """Load EasyOCR reader"""
    global ocr_reader, ocr_loaded
    
    try:
        logger.info("📖 Loading EasyOCR...")
        import easyocr
        ocr_reader = easyocr.Reader(['en'], gpu=False)  # CPU mode for stability
        ocr_loaded = True
        logger.info("✅ EasyOCR loaded and ready")
    except Exception as e:
        logger.error(f"Failed to load EasyOCR: {e}")
        ocr_loaded = False


async def load_llava_model():
    """Load BLIP-2 model (much lighter alternative to LLaVA - uses ~3-4GB vs ~20GB)"""
    global llava_model, llava_processor, model_loaded, loading_progress
    
    try:
        logger.info("🔮 Starting BLIP-2 model loading (lightweight vision-language model)...")
        loading_progress = {"status": "loading", "progress": 10, "stage": "Checking cache"}
        
        from transformers import AutoProcessor, Blip2ForConditionalGeneration
        import torch
        import gc
        
        # BLIP-2 is much smaller and faster than LLaVA
        model_name = "Salesforce/blip2-opt-2.7b"  # Only 2.7B params vs LLaVA's 7B
        cache_dir = "/data/models/blip2"
        
        # Check if model is cached
        import os.path
        if os.path.exists(cache_dir):
            logger.info("✅ BLIP-2 cache found, loading will be fast")
            loading_progress["stage"] = "Loading from cache"
        else:
            logger.info("📥 Downloading BLIP-2 model (first time, ~5GB - much smaller than LLaVA)")
            loading_progress["stage"] = "Downloading model"
        
        loading_progress["progress"] = 20
        
        # Load processor
        logger.info("Loading processor...")
        llava_processor = AutoProcessor.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        loading_progress["progress"] = 40
        loading_progress["stage"] = "Processor loaded"
        logger.info("✅ Processor loaded")
        
        # Load BLIP-2 model (much lighter than LLaVA)
        logger.info("Loading BLIP-2 model (lightweight)...")
        loading_progress["stage"] = "Loading BLIP-2 model"
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🖥️  Loading on: {device}")
        
        # BLIP-2 loads much faster with less memory
        llava_model = Blip2ForConditionalGeneration.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto"
        )
        
        # Aggressive garbage collection
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        loading_progress["progress"] = 100
        loading_progress["stage"] = "Model loaded"
        model_loaded = True
        
        # Initialize batch processor
        logger.info("🚀 Initializing batch processor for 16 FPS gameplay...")
        from src.batch_processor import GameplayBatchProcessor
        global batch_processor
        batch_processor = GameplayBatchProcessor(ocr_reader, llava_model, llava_processor)
        logger.info("✅ Batch processor ready for high-FPS analysis")
        
        logger.info("✅ BLIP-2 model fully loaded and ready! (Much lighter than LLaVA)")
        
    except Exception as e:
        logger.error(f"Failed to load BLIP-2 model: {e}")
        loading_progress = {"status": "error", "progress": 0, "stage": f"Error: {str(e)}"}
        model_loaded = False


async def warmup_llava():
    """Make dummy inference call to warm up model after loading"""
    global warmup_complete
    
    try:
        logger.info("🔥 Warming up LLaVA model...")
        
        from PIL import Image
        import torch
        
        # Create simple dummy image
        dummy_image = Image.new('RGB', (224, 224), color='blue')
        
        # Simple warm-up prompt
        prompt = "USER: <image>\nWhat do you see? ASSISTANT:"
        
        inputs = llava_processor(text=prompt, images=dummy_image, return_tensors="pt")
        
        # Move to same device as model
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # Generate response
        with torch.no_grad():
            output = llava_model.generate(**inputs, max_new_tokens=10)
        
        warmup_complete = True
        logger.info("✅ LLaVA warm-up complete - model ready for inference")
        
    except Exception as e:
        logger.error(f"Failed to warm up LLaVA: {e}")
        warmup_complete = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting Vision AI Service...")
    logger.info("✅ Vision AI Service ready")
    logger.info("💡 BLIP-2 will load on first use (lightweight model - only ~3-4GB)")
    
    # Start OCR loading in background (lighter than BLIP-2)
    asyncio.create_task(load_ocr())
    
    yield
    
    logger.info("Shutting down Vision AI Service...")


app = FastAPI(
    title="PlayMetric Vision AI Service",
    description="LLaVA/GPT-4V/Gemini for game screen analysis",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model_loaded,
        "ocr_loaded": ocr_loaded,
        "warmup_complete": warmup_complete,
        "loading_progress": loading_progress
    }


@app.get("/model/status")
async def get_model_status():
    """Get LLaVA model loading status"""
    return {
        "model_loaded": model_loaded,
        "ocr_loaded": ocr_loaded,
        "warmup_complete": warmup_complete,
        "loading_progress": loading_progress,
        "model_name": "BLIP-2 (Salesforce/blip2-opt-2.7b - lightweight, ~3-4GB)"
    }


@app.post("/analyze")
async def analyze_screenshot(request: AnalysisRequest):
    """Analyze game screenshot using Vision AI"""
    
    # Lazy load BLIP-2 on first use
    if not model_loaded and request.model_type == "llava":
        logger.info("🔮 First vision request - loading BLIP-2 model now...")
        await load_llava_model()
        
        if not model_loaded:
            raise HTTPException(
                status_code=503,
                detail=f"BLIP-2 model failed to load. Progress: {loading_progress['progress']}%"
            )
    
    try:
        from PIL import Image
        import torch
        
        # Load and optimize image for memory efficiency
        image = Image.open(request.screenshot_path).convert("RGB")
        
        # Downscale large images (LLaVA works well at 336x336-512x512)
        max_size = 512  # Balance between quality and memory
        if image.width > max_size or image.height > max_size:
            ratio = min(max_size / image.width, max_size / image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"📐 Downscaled image to {new_size} for memory efficiency")
        
        # Prepare prompt for BLIP-2 (simpler than LLaVA)
        game_context = request.context.get('game_id', 'unknown') if request.context else 'unknown'
        
        # BLIP-2 works better with direct questions
        prompt = f"Question: Analyze this mobile game screen. What scene is this (menu, gameplay, loading, reward, tutorial, or game over)? What action should be taken next? Answer:"
        
        # Process with BLIP-2
        inputs = llava_processor(images=image, text=prompt, return_tensors="pt")
        
        # Move to same device as model
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # Generate with optimized parameters for memory efficiency
        with torch.no_grad():
            outputs = llava_model.generate(
                **inputs,
                max_new_tokens=200,  # Reduced from 300 to save memory
                do_sample=False,
                num_beams=1,  # Greedy decoding (faster, less memory than beam search)
                use_cache=True  # Reuse past key values
            )
        
        # Free up memory immediately after generation
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        del inputs  # Explicitly delete large tensors
        
        # Decode response
        response_text = llava_processor.decode(outputs[0], skip_special_tokens=True)
        
        # Parse BLIP-2 response (simpler than JSON parsing)
        logger.info(f"BLIP-2 response: {response_text}")
        
        # Extract scene type and create structured response
        response_lower = response_text.lower()
        scene_type = "gameplay"  # default
        if "menu" in response_lower:
            scene_type = "menu"
        elif "loading" in response_lower:
            scene_type = "loading"
        elif "reward" in response_lower:
            scene_type = "reward"
        elif "tutorial" in response_lower:
            scene_type = "tutorial"
        elif "game over" in response_lower or "gameover" in response_lower:
            scene_type = "game_over"
        
        result = {
            "scene_type": scene_type,
            "description": response_text,
            "recommended_action": {"action": "tap", "x": 540, "y": 960},
            "ui_elements": [],
            "confidence": 0.8
        }
        
        logger.info(f"✅ Vision analysis complete: {result.get('scene_type')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/ocr")
async def extract_text_with_ocr(screenshot_path: str):
    """Extract text from screenshot using OCR"""
    
    if not ocr_loaded:
        raise HTTPException(
            status_code=503,
            detail="OCR not ready yet. Please wait for initialization."
        )
    
    try:
        # Run OCR
        result = ocr_reader.readtext(screenshot_path)
        
        # Extract text and bounding boxes
        texts = []
        for detection in result:
            bbox, text, confidence = detection
            texts.append({
                "text": text,
                "confidence": confidence,
                "bbox": bbox
            })
        
        logger.info(f"✅ OCR extracted {len(texts)} text elements")
        
        return {
            "texts": texts,
            "full_text": " ".join([t["text"] for t in texts])
        }
        
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/gemini")
async def analyze_with_gemini(request: AnalysisRequest):
    """Analyze screenshot using Gemini Pro Vision API"""
    
    # TODO: Implement Gemini API integration
    # This requires GOOGLE_API_KEY environment variable
    # and google-generativeai package
    
    try:
        import google.generativeai as genai
        from PIL import Image
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="Gemini API key not configured. Set GOOGLE_API_KEY environment variable."
            )
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # Load image
        image = Image.open(request.screenshot_path)
        
        # Prepare prompt
        prompt = f"""Analyze this mobile game screenshot and provide:
1. Scene type (menu/gameplay/loading/reward/tutorial/game_over)
2. What is happening on screen
3. Recommended next action
4. UI elements visible

Respond in JSON format:
{{
    "scene_type": "menu|gameplay|loading|reward|tutorial|game_over",
    "description": "what's on screen",
    "recommended_action": {{"action": "tap|swipe|wait", "x": 0, "y": 0}},
    "ui_elements": ["button1", "button2"],
    "confidence": 0.95
}}
"""
        
        # Generate response
        response = model.generate_content([prompt, image])
        
        # Parse JSON response
        import json
        result = json.loads(response.text)
        
        logger.info(f"✅ Gemini analysis complete: {result.get('scene_type')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/batch")
async def batch_analyze(request: BatchAnalysisRequest):
    """
    Intelligently analyze batch of 16 screenshots captured in 1 second
    
    Optimizations:
    - Caches recent analysis to avoid redundant BLIP-2 calls
    - Uses frame hashing to detect scene changes
    - Runs OCR on all frames in parallel (fast)
    - Uses BLIP-2 only on keyframes when scene changes (slow but accurate)
    - Detects UI elements and click candidates
    - Provides recommended actions
    
    Perfect for 16 FPS gameplay monitoring with limited CPU resources
    """
    
    if not model_loaded:
        raise HTTPException(
            status_code=503,
            detail=f"BLIP-2 model not ready yet. Loading progress: {loading_progress['progress']}%"
        )
    
    if not batch_processor:
        raise HTTPException(
            status_code=503,
            detail="Batch processor not initialized yet"
        )
    
    try:
        logger.info(f"📦 Batch analysis request: {len(request.screenshot_paths)} frames")
        
        # Determine mode based on context
        detect_clicks = request.context and request.context.get("mode") == "user_gameplay"
        use_blip = request.model_type == "llava"  # "llava" here means BLIP-2
        
        # Use intelligent batch processor
        result = await batch_processor.process_frame_batch(
            image_paths=request.screenshot_paths,
            use_blip=use_blip,
            detect_clicks=detect_clicks
        )
        
        logger.info(f"✅ Batch processed in {result['processing_time_ms']:.0f}ms - Scene: {result['scene_type']}")
        
        return {
            **result,
            "frames_analyzed": result["frame_count"],
            "optimization": "intelligent_sampling_with_caching"
        }
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8006"))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
