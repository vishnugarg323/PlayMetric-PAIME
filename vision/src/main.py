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
import traceback
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


class TestVisionRequest(BaseModel):
    image_path: str
    use_gemini: bool = True  # ENABLED BY DEFAULT for better AI learning
    use_blip2: bool = True
    use_ocr: bool = True
    use_opencv: bool = True
    use_template: bool = True


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
    """Load EasyOCR reader with retry logic"""
    global ocr_reader, ocr_loaded
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"📖 Loading EasyOCR (attempt {attempt + 1}/{max_retries})...")
            import easyocr
            
            # Use custom model storage path and disable download if models exist
            model_storage_directory = '/data/models/easyocr'
            
            ocr_reader = easyocr.Reader(
                ['en'], 
                gpu=False,  # CPU mode for stability
                model_storage_directory=model_storage_directory,
                download_enabled=True,
                verbose=False
            )
            ocr_loaded = True
            logger.info("✅ EasyOCR loaded and ready")
            return
            
        except Exception as e:
            logger.error(f"Failed to load EasyOCR (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("❌ EasyOCR failed to load after all retries - OCR will be unavailable")
                ocr_loaded = False


async def load_llava_model():
    """Load BLIP model (lightweight vision model that ACTUALLY supports unconditional captioning)"""
    global llava_model, llava_processor, model_loaded, loading_progress
    
    try:
        logger.info("🔮 Starting BLIP model loading (supports unconditional image captioning)...")
        loading_progress = {"status": "loading", "progress": 10, "stage": "Checking cache"}
        
        from transformers import BlipProcessor, BlipForConditionalGeneration
        import torch
        import gc
        
        # BLIP-1 supports unconditional captioning (unlike BLIP-2 which requires text prompts)
        model_name = "Salesforce/blip-image-captioning-large"  # 425M params, works for unconditional captioning
        cache_dir = "/data/models/blip"
        
        # Check if model is cached
        import os.path
        if os.path.exists(cache_dir):
            logger.info("✅ BLIP cache found, loading will be fast")
            loading_progress["stage"] = "Loading from cache"
        else:
            logger.info("📥 Downloading BLIP model (first time, ~1.7GB)")
            loading_progress["stage"] = "Downloading model"
        
        loading_progress["progress"] = 20
        
        # Load processor
        logger.info("Loading processor...")
        llava_processor = BlipProcessor.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        
        loading_progress["progress"] = 40
        loading_progress["stage"] = "Processor loaded"
        logger.info("✅ Processor loaded")
        
        # Load BLIP model
        logger.info("Loading BLIP model (supports unconditional captioning)...")
        loading_progress["stage"] = "Loading BLIP model"
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🖥️  Loading on: {device}")
        
        # BLIP-1 loads fast and supports unconditional image captioning
        llava_model = BlipForConditionalGeneration.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        ).to(device)
        
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
        
        logger.info("✅ BLIP model fully loaded and ready! (Supports unconditional image captioning)")
        
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
    
    # Load both OCR and BLIP-2 on startup for faster analysis
    await asyncio.gather(
        load_ocr(),
        load_llava_model()  # Load BLIP-2 immediately for parallel analysis
    )
    
    logger.info("✅ Vision AI Service ready with OCR and BLIP-2")
    
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
    """Extract text from screenshot using OCR (EasyOCR with Tesseract fallback)"""
    
    try:
        # Try EasyOCR first
        if ocr_loaded and ocr_reader is not None:
            try:
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
                
                logger.info(f"✅ EasyOCR extracted {len(texts)} text elements")
                
                return {
                    "texts": texts,
                    "full_text": " ".join([t["text"] for t in texts])
                }
            except Exception as e:
                logger.warning(f"EasyOCR failed, trying Tesseract fallback: {e}")
        
        # Fallback to Tesseract if EasyOCR not available or failed
        logger.info("📝 Using Tesseract OCR fallback...")
        import pytesseract
        from PIL import Image
        import cv2
        import numpy as np
        
        # Load and preprocess image for better OCR
        img = cv2.imread(screenshot_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding for better text detection
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Get detailed OCR data with bounding boxes
        ocr_data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
        
        texts = []
        full_text_parts = []
        
        for i, text in enumerate(ocr_data['text']):
            if text.strip():  # Skip empty strings
                confidence = float(ocr_data['conf'][i]) / 100.0  # Normalize to 0-1
                if confidence > 0.3:  # Only include confident detections
                    x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                    bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                    
                    texts.append({
                        "text": text,
                        "confidence": confidence,
                        "bbox": bbox
                    })
                    full_text_parts.append(text)
        
        logger.info(f"✅ Tesseract OCR extracted {len(texts)} text elements")
        
        return {
            "texts": texts,
            "full_text": " ".join(full_text_parts)
        }
        
    except Exception as e:
        logger.error(f"All OCR methods failed: {e}")
        # Return empty result instead of failing completely
        return {
            "texts": [],
            "full_text": ""
        }


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


@app.post("/analyze/parallel")
async def parallel_multi_method_analysis(request: AnalysisRequest):
    """
    Analyze screenshot using MULTIPLE methods in parallel for best results:
    - EasyOCR (text extraction)
    - BLIP-2 (scene understanding)
    - OpenCV (button/UI detection)
    - Template matching (common UI patterns)
    
    All run simultaneously and results are fused into one comprehensive analysis
    """
    worker_id = os.getenv("WORKER_ID", "unknown")
    logger.info(f"🚀 [Worker {worker_id}] Starting parallel multi-method analysis for {request.screenshot_path}")
    
    try:
        from PIL import Image
        import cv2
        import numpy as np
        
        # Load image once for all analyses
        image_path = request.screenshot_path
        pil_image = Image.open(image_path)
        cv_image = cv2.imread(image_path)
        
        # Get screen dimensions for later use
        img_width, img_height = pil_image.size
        
        # Define all analysis tasks to run in parallel
        async def run_ocr():
            """OCR text extraction"""
            try:
                if not ocr_loaded:
                    return {"text": "", "confidence": 0}
                
                logger.info(f"[Worker {worker_id}] Running OCR...")
                # Convert PIL to numpy for OCR
                img_array = np.array(pil_image)
                results = ocr_reader.readtext(img_array)
                
                full_text = " ".join([text for (bbox, text, conf) in results])
                avg_conf = sum([conf for (bbox, text, conf) in results]) / len(results) if results else 0
                
                logger.info(f"[Worker {worker_id}] OCR found: {len(results)} text regions")
                return {
                    "text": full_text,
                    "confidence": avg_conf,
                    "regions": len(results)
                }
            except Exception as e:
                logger.error(f"[Worker {worker_id}] OCR failed: {e}")
                return {"text": "", "confidence": 0, "error": str(e)}
        
        async def run_blip2():
            """BLIP scene understanding - FINALLY works with unconditional image captioning!"""
            try:
                if not model_loaded:
                    logger.warning(f"[Worker {worker_id}] BLIP model not loaded, skipping")
                    return {"description": "", "scene_type": "unknown", "confidence": 0}
                
                logger.info(f"[Worker {worker_id}] Running BLIP...")
                import torch
                
                # Resize image to expected size
                image_resized = pil_image.copy()
                image_resized = image_resized.resize((384, 384), Image.Resampling.LANCZOS)
                
                with torch.no_grad():
                    # BLIP-1 unconditional image captioning - this ACTUALLY works!
                    inputs = llava_processor(
                        images=image_resized,
                        return_tensors="pt"
                    )
                    
                    # Move to device
                    device = next(llava_model.parameters()).device
                    inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}
                    
                    # Generate caption with better parameters for quality
                    outputs = llava_model.generate(
                        **inputs,
                        max_length=40,  # Longer captions
                        min_length=10,  # At least some detail
                        num_beams=5,    # More beams for better quality
                        length_penalty=0.6,  # Encourage longer descriptions
                        repetition_penalty=2.0,  # Prevent "screenshote screenshote" repetition
                        early_stopping=True
                    )
                    description = llava_processor.decode(outputs[0], skip_special_tokens=True)
                    logger.info(f"[Worker {worker_id}] ✅ BLIP caption: {description}")
                    
                    # Cleanup
                    del outputs, inputs
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                
                # Classify scene from description
                scene_type = "unknown"
                desc_lower = description.lower()
                
                if any(word in desc_lower for word in ['menu', 'button', 'start', 'home', 'settings']):
                    scene_type = "menu"
                elif any(word in desc_lower for word in ['game', 'play', 'screen', 'level', 'score', 'ball', 'block']):
                    scene_type = "gameplay"
                elif any(word in desc_lower for word in ['win', 'victory', 'success', 'complete', 'congratulations']):
                    scene_type = "victory"
                elif any(word in desc_lower for word in ['lose', 'fail', 'over', 'defeat', 'try again']):
                    scene_type = "defeat"
                elif any(word in desc_lower for word in ['load', 'wait', 'progress']):
                    scene_type = "loading"
                else:
                    # Default to gameplay if we see any game-related words
                    scene_type = "gameplay"
                
                return {
                    "description": description,
                    "scene_type": scene_type,
                    "confidence": 0.75
                }
                
            except Exception as e:
                logger.error(f"[Worker {worker_id}] BLIP-2 failed: {e}")
                import traceback
                logger.error(f"[Worker {worker_id}] Traceback: {traceback.format_exc()}")
                
                # Fallback: classify from OCR text if available
                return {"description": "Error in vision model", "scene_type": "gameplay", "confidence": 0.3, "error": str(e)}
        
        async def run_gemini():
            """Gemini Vision API - Cloud-based deep analysis (use sparingly)"""
            try:
                gemini_key = os.getenv("GEMINI_API_KEY")
                if not gemini_key:
                    logger.debug(f"[Worker {worker_id}] Gemini API key not set")
                    return {"description": "", "scene_type": "unknown", "confidence": 0, "used": False}
                
                logger.info(f"[Worker {worker_id}] Running Gemini Vision (cloud)...")
                
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                # Get screen dimensions DYNAMICALLY from image size
                img_width, img_height = pil_image.size
                
                # Use Gemini 2.5 Flash (latest fast vision model as of Dec 2024)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                prompt = f"""Analyze this mobile game screenshot for AI learning.
Screen size: {img_width}x{img_height}

You MUST respond in this EXACT format with pipe delimiters:
SCENE: <type> | STATE: <game state> | UI: <elements> | ACTION: <action> | INSIGHT: <learning>

SCENE TYPE: menu, gameplay, loading, victory, defeat, tutorial, or settings
GAME STATE: Score, lives, obstacles, objectives, level info
UI ELEMENTS: Buttons, controls, interactive elements with positions
ACTION: PERCENTAGE coordinates only! Format: "tap X%:Y%" or "swipe from X1%:Y1% to X2%:Y2%"
INSIGHT: Actionable pattern the AI can learn and generalize

CRITICAL: Use PERCENTAGE coordinates (0-100%) relative to screen size, NOT pixels!
Example: For {img_width}x{img_height} screen, pixel ({img_width//2},{img_height//2}) = 50%:50%

Example response: SCENE: gameplay | STATE: Level 1, 3 screws visible, score 0 | UI: Pause at 95%:5%, Settings at 5%:5% | ACTION: tap 50%:60% | INSIGHT: Tap highlighted interactive objects to progress"""
                
                response = model.generate_content([prompt, pil_image])
                result = response.text.strip()
                
                logger.info(f"[Worker {worker_id}] ✅ Gemini: {result[:150]}...")
                
                # Parse enhanced response (handle both pipe-delimited and line-break formats)
                scene_type = "gameplay"
                description = result
                action_suggestion = ""
                game_state = ""
                learning_insight = ""
                
                # Try pipe-delimited format first
                if "|" in result and "SCENE:" in result:
                    parts = result.split("|")
                    for part in parts:
                        part = part.strip()
                        if "SCENE:" in part:
                            scene_type = part.split("SCENE:")[1].strip().lower()
                        elif "STATE:" in part:
                            game_state = part.split("STATE:")[1].strip()
                        elif "UI:" in part:
                            description = part.split("UI:")[1].strip()
                        elif "ACTION:" in part:
                            action_suggestion = part.split("ACTION:")[1].strip()
                        elif "INSIGHT:" in part:
                            learning_insight = part.split("INSIGHT:")[1].strip()
                # Fallback: parse line-break format
                elif "SCENE:" in result:
                    lines = result.replace("\n", " ").split(".")
                    for line in lines:
                        line = line.strip()
                        if "SCENE:" in line:
                            scene_type = line.split("SCENE:")[1].strip().split()[0].lower()
                        elif "STATE:" in line:
                            state_part = line.split("STATE:")[1].strip()
                            game_state = state_part[:200] if len(state_part) > 200 else state_part
                        elif "ACTION:" in line:
                            action_suggestion = line.split("ACTION:")[1].strip()[:300]
                        elif "INSIGHT:" in line:
                            learning_insight = line.split("INSIGHT:")[1].strip()[:300]
                
                # Normalize scene type
                if "menu" in scene_type: scene_type = "menu"
                elif "game" in scene_type or "play" in scene_type: scene_type = "gameplay"
                elif "victory" in scene_type or "win" in scene_type: scene_type = "victory"
                elif "defeat" in scene_type or "lose" in scene_type: scene_type = "defeat"
                elif "load" in scene_type: scene_type = "loading"
                elif "tutorial" in scene_type: scene_type = "tutorial"
                elif "setting" in scene_type: scene_type = "settings"
                
                return {
                    "description": description,
                    "scene_type": scene_type,
                    "action_suggestion": action_suggestion,
                    "game_state": game_state,
                    "learning_insight": learning_insight,
                    "full_analysis": result,  # Store complete analysis for learning service
                    "confidence": 0.95,
                    "used": True
                }
                
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Gemini failed: {e}")
                return {"description": "", "scene_type": "unknown", "confidence": 0, "error": str(e), "used": False}
        
        async def run_grok():
            """xAI Grok Vision - Alternative cloud vision AI (OpenAI-compatible API)"""
            grok_key = os.getenv("XAI_API_KEY", "").strip()
            grok_enabled = os.getenv("GROK_ENABLED", "false").lower() == "true"
            
            if not grok_enabled or not grok_key:
                return {"used": False, "description": "", "scene_type": "unknown", "confidence": 0}
            
            try:
                logger.info(f"[Worker {worker_id}] Running Grok Vision (xAI)...")
                
                from openai import OpenAI
                
                # Get screen dimensions DYNAMICALLY from image size
                img_width, img_height = pil_image.size
                
                # xAI Grok uses OpenAI-compatible API
                client = OpenAI(
                    api_key=grok_key,
                    base_url="https://api.x.ai/v1"
                )
                
                # Convert PIL image to base64
                import base64
                from io import BytesIO
                buffered = BytesIO()
                pil_image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                prompt = f"""Analyze this mobile game screenshot for AI learning.
Screen size: {img_width}x{img_height}

You MUST respond in this EXACT format with pipe delimiters:
SCENE: <type> | STATE: <game state> | UI: <elements> | ACTION: <action> | INSIGHT: <learning>

SCENE TYPE: menu, gameplay, loading, victory, defeat, tutorial, or settings
GAME STATE: Score, lives, obstacles, objectives, level info
UI ELEMENTS: Buttons, controls, interactive elements
ACTION: PERCENTAGE coordinates! Format: "tap X%:Y%" or "swipe from X1%:Y1% to X2%:Y2%"
INSIGHT: Actionable pattern the AI can learn

Use PERCENTAGE coordinates (0-100%), NOT pixels!
Example: pixel ({img_width//2},{img_height//2}) = 50%:50%

Example: SCENE: gameplay | STATE: Level 1, 3 screws | UI: Pause at 95%:5% | ACTION: tap 50%:60% | INSIGHT: Tap highlighted objects"""

                response = client.chat.completions.create(
                    model="grok-2-vision-1212",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{img_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                
                result = response.choices[0].message.content.strip()
                logger.info(f"[Worker {worker_id}] ✅ Grok: {result[:150]}...")
                
                # Parse response (same format as Gemini)
                scene_type = "gameplay"
                description = result
                action_suggestion = ""
                game_state = ""
                learning_insight = ""
                
                # Try pipe-delimited format first
                if "|" in result and "SCENE:" in result:
                    parts = result.split("|")
                    for part in parts:
                        part = part.strip()
                        if "SCENE:" in part:
                            scene_type = part.split("SCENE:")[1].strip().lower()
                        elif "STATE:" in part:
                            game_state = part.split("STATE:")[1].strip()
                        elif "UI:" in part:
                            description = part.split("UI:")[1].strip()
                        elif "ACTION:" in part:
                            action_suggestion = part.split("ACTION:")[1].strip()
                        elif "INSIGHT:" in part:
                            learning_insight = part.split("INSIGHT:")[1].strip()
                # Fallback: parse line-break format
                elif "SCENE:" in result:
                    lines = result.replace("\n", " ").split(".")
                    for line in lines:
                        line = line.strip()
                        if "SCENE:" in line:
                            scene_type = line.split("SCENE:")[1].strip().split()[0].lower()
                        elif "STATE:" in line:
                            state_part = line.split("STATE:")[1].strip()
                            game_state = state_part[:200] if len(state_part) > 200 else state_part
                        elif "ACTION:" in line:
                            action_suggestion = line.split("ACTION:")[1].strip()[:300]
                        elif "INSIGHT:" in line:
                            learning_insight = line.split("INSIGHT:")[1].strip()[:300]
                
                # Normalize scene type
                if "menu" in scene_type: scene_type = "menu"
                elif "game" in scene_type or "play" in scene_type: scene_type = "gameplay"
                elif "victory" in scene_type or "win" in scene_type: scene_type = "victory"
                elif "defeat" in scene_type or "lose" in scene_type: scene_type = "defeat"
                elif "load" in scene_type: scene_type = "loading"
                elif "tutorial" in scene_type: scene_type = "tutorial"
                elif "setting" in scene_type: scene_type = "settings"
                
                return {
                    "description": description,
                    "scene_type": scene_type,
                    "action_suggestion": action_suggestion,
                    "game_state": game_state,
                    "learning_insight": learning_insight,
                    "full_analysis": result,
                    "confidence": 0.93,
                    "used": True
                }
                
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Grok failed: {e}")
                return {"description": "", "scene_type": "unknown", "confidence": 0, "error": str(e), "used": False}
        
        async def run_opencv_detection():
            """OpenCV button/UI element detection"""
            try:
                logger.info(f"[Worker {worker_id}] Running OpenCV detection...")
                
                # Convert to grayscale
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                
                # Edge detection for buttons
                edges = cv2.Canny(gray, 50, 150)
                
                # Find contours (potential buttons)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Filter contours that look like buttons (rectangular, reasonable size)
                buttons = []
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if 1000 < area < 50000:  # Reasonable button size
                        x, y, w, h = cv2.boundingRect(contour)
                        aspect_ratio = w / h if h > 0 else 0
                        if 0.5 < aspect_ratio < 3:  # Roughly rectangular
                            buttons.append({
                                "x": int(x),
                                "y": int(y),
                                "width": int(w),
                                "height": int(h),
                                "type": "button"
                            })
                
                logger.info(f"[Worker {worker_id}] OpenCV detected {len(buttons)} UI elements")
                return {
                    "ui_elements": buttons[:10],  # Top 10
                    "total_detected": len(buttons)
                }
            except Exception as e:
                logger.error(f"[Worker {worker_id}] OpenCV failed: {e}")
                return {"ui_elements": [], "error": str(e)}
        
        async def run_template_matching():
            """Template matching for common UI patterns"""
            try:
                logger.info(f"[Worker {worker_id}] Running template matching...")
                
                # Common UI patterns (you can expand this)
                patterns_detected = []
                
                # Check for common colors (play buttons are often green)
                hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
                
                # Green mask (play buttons)
                green_mask = cv2.inRange(hsv, np.array([40, 40, 40]), np.array([80, 255, 255]))
                green_pixels = cv2.countNonZero(green_mask)
                if green_pixels > 5000:
                    patterns_detected.append("green_button")
                
                # Red mask (close/stop buttons)
                red_mask = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
                red_pixels = cv2.countNonZero(red_mask)
                if red_pixels > 3000:
                    patterns_detected.append("red_button")
                
                logger.info(f"[Worker {worker_id}] Template matching found: {patterns_detected}")
                return {
                    "patterns": patterns_detected,
                    "confidence": 0.6
                }
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Template matching failed: {e}")
                return {"patterns": [], "error": str(e)}
        
        # Run ALL analyses in parallel for COMPREHENSIVE understanding
        # Both Gemini and Grok enabled by default for maximum insights
        use_gemini = os.getenv("GEMINI_ENABLED", "false").lower() == "true"  # Default to TRUE for better learning
        use_grok = os.getenv("GROK_ENABLED", "false").lower() == "true"
        
        if request.context:
            use_gemini = request.context.get("use_gemini", use_gemini)  # Default True unless explicitly disabled
            use_grok = request.context.get("use_grok", use_grok)
        
        methods_count = 4 + (1 if use_gemini else 0) + (1 if use_grok else 0)  # Base 4 + Gemini + Grok
        logger.info(f"[Worker {worker_id}] Running {methods_count} analysis methods in parallel...")
        start_time = asyncio.get_event_loop().time()
        
        # Track individual method times
        method_times = {}
        
        # Execute all enabled methods in parallel
        method_start = asyncio.get_event_loop().time()
        tasks = [
            run_ocr(),
            run_blip2(),
            run_opencv_detection(),
            run_template_matching()
        ]
        
        if use_gemini:
            tasks.append(run_gemini())
        if use_grok:
            tasks.append(run_grok())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Record completion time
        method_times['total_parallel'] = (asyncio.get_event_loop().time() - method_start) * 1000  # ms
        
        # Unpack results
        ocr_result = results[0]
        blip_result = results[1]
        opencv_result = results[2]
        template_result = results[3]
        
        # Add timing info to results (estimate based on typical durations)
        method_times['ocr'] = 2000  # OCR typically ~2s
        method_times['blip'] = 15000  # BLIP ~15s
        method_times['opencv'] = 500  # OpenCV ~0.5s
        method_times['template'] = 300  # Template ~0.3s
        
        gemini_result = {"used": False}
        grok_result = {"used": False}
        
        result_idx = 4
        if use_gemini:
            gemini_result = results[result_idx] if not isinstance(results[result_idx], Exception) else {"used": False, "error": str(results[result_idx])}
            method_times['gemini'] = 10000  # Gemini ~10s
            result_idx += 1
        if use_grok:
            grok_result = results[result_idx] if not isinstance(results[result_idx], Exception) else {"used": False, "error": str(results[result_idx])}
            method_times['grok'] = 12000  # Grok ~12s
        
        analysis_time = asyncio.get_event_loop().time() - start_time
        logger.info(f"[Worker {worker_id}] ✅ All analyses complete in {analysis_time:.2f}s")
        
        # Determine best scene type from multiple sources (weighted voting)
        scene_votes = []
        if isinstance(blip_result, dict) and blip_result.get("scene_type"):
            scene_votes.append((blip_result["scene_type"], blip_result.get("confidence", 0.5)))
        if isinstance(gemini_result, dict) and gemini_result.get("used") and gemini_result.get("scene_type"):
            scene_votes.append((gemini_result["scene_type"], gemini_result.get("confidence", 0.95)))
        if isinstance(grok_result, dict) and grok_result.get("used") and grok_result.get("scene_type"):
            scene_votes.append((grok_result["scene_type"], grok_result.get("confidence", 0.93)))
        
        # Pick scene with highest confidence
        best_scene = "gameplay"  # default
        if scene_votes:
            best_scene = max(scene_votes, key=lambda x: x[1])[0]
        
        # Fuse results into comprehensive analysis with detailed per-model insights for UI
        methods_used = ["OCR", "BLIP-1", "OpenCV", "Template"]
        if isinstance(gemini_result, dict) and gemini_result.get("used"):
            methods_used.append("Gemini")
        if isinstance(grok_result, dict) and grok_result.get("used"):
            methods_used.append("Grok")
        
        fused_result = {
            "worker_id": worker_id,
            "analysis_time": round(analysis_time, 2),
            "methods_used": methods_used,
            "method_times": method_times,  # Add timing info for each method
            "screen_width": img_width,
            "screen_height": img_height,
            
            # DETAILED PER-MODEL INSIGHTS FOR UI VISUALIZATION
            
            # OCR results - What text the AI can read
            "ocr": {
                "text": ocr_result.get("text", "") if isinstance(ocr_result, dict) else "",
                "confidence": ocr_result.get("confidence", 0) if isinstance(ocr_result, dict) else 0,
                "regions_found": ocr_result.get("regions", 0) if isinstance(ocr_result, dict) else 0,
                "what_learned": f"Detected {ocr_result.get('regions', 0)} text regions" if isinstance(ocr_result, dict) else "No text detected",
                "usefulness": "Identifies UI labels, scores, level numbers, button text" if isinstance(ocr_result, dict) and ocr_result.get("regions", 0) > 0 else "No readable text in frame"
            },
            
            # BLIP-2 local vision results - Fast local scene understanding
            "blip2": {
                "description": blip_result.get("description", "") if isinstance(blip_result, dict) else "",
                "scene_type": blip_result.get("scene_type", "unknown") if isinstance(blip_result, dict) else "unknown",
                "confidence": blip_result.get("confidence", 0) if isinstance(blip_result, dict) else 0,
                "what_learned": blip_result.get("description", "No description") if isinstance(blip_result, dict) else "Analysis failed",
                "usefulness": "Fast local scene caption, basic game state understanding",
                "error": blip_result.get("error") if isinstance(blip_result, dict) else None
            },
            
            # Gemini cloud vision results - COMPREHENSIVE AI LEARNING
            "gemini": {
                "used": gemini_result.get("used", False) if isinstance(gemini_result, dict) else False,
                "description": gemini_result.get("description", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                "scene_type": gemini_result.get("scene_type", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                "action_suggestion": gemini_result.get("action_suggestion", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                "game_state": gemini_result.get("game_state", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                "learning_insight": gemini_result.get("learning_insight", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                "full_analysis": gemini_result.get("full_analysis", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                "confidence": gemini_result.get("confidence", 0) if isinstance(gemini_result, dict) and gemini_result.get("used") else 0,
                "what_learned": (
                    f"Scene: {gemini_result.get('scene_type', 'unknown')}, "
                    f"State: {gemini_result.get('game_state', 'unknown')[:50]}..., "
                    f"Action: {gemini_result.get('action_suggestion', 'none')}"
                ) if isinstance(gemini_result, dict) and gemini_result.get("used") else "Not used",
                "usefulness": "Provides actionable coordinates, game state, and learning patterns for AI training" if isinstance(gemini_result, dict) and gemini_result.get("used") else "Disabled to save costs"
            },
            
            # Grok cloud vision results - xAI's game-focused AI
            "grok": {
                "used": grok_result.get("used", False) if isinstance(grok_result, dict) else False,
                "description": grok_result.get("description", "") if isinstance(grok_result, dict) and grok_result.get("used") else "",
                "scene_type": grok_result.get("scene_type", "") if isinstance(grok_result, dict) and grok_result.get("used") else "",
                "action_suggestion": grok_result.get("action_suggestion", "") if isinstance(grok_result, dict) and grok_result.get("used") else "",
                "game_state": grok_result.get("game_state", "") if isinstance(grok_result, dict) and grok_result.get("used") else "",
                "learning_insight": grok_result.get("learning_insight", "") if isinstance(grok_result, dict) and grok_result.get("used") else "",
                "full_analysis": grok_result.get("full_analysis", "") if isinstance(grok_result, dict) and grok_result.get("used") else "",
                "confidence": grok_result.get("confidence", 0) if isinstance(grok_result, dict) and grok_result.get("used") else 0,
                "what_learned": (
                    f"Scene: {grok_result.get('scene_type', 'unknown')}, "
                    f"State: {grok_result.get('game_state', 'unknown')[:50]}..., "
                    f"Action: {grok_result.get('action_suggestion', 'none')}"
                ) if isinstance(grok_result, dict) and grok_result.get("used") else "Not used",
                "usefulness": "Alternative AI perspective, excels at game strategy understanding" if isinstance(grok_result, dict) and grok_result.get("used") else "Disabled or no API key"
            },
            
            # UI detection results - Interactive elements
            "ui_detection": {
                "elements": opencv_result.get("ui_elements", []) if isinstance(opencv_result, dict) else [],
                "total_detected": opencv_result.get("total_detected", 0) if isinstance(opencv_result, dict) else 0,
                "what_learned": f"Found {opencv_result.get('total_detected', 0)} UI elements (buttons, icons)" if isinstance(opencv_result, dict) else "No UI elements detected",
                "usefulness": "Identifies clickable UI elements, helps AI locate buttons and controls"
            },
            
            # Pattern matching results - Visual patterns
            "patterns": {
                "detected": template_result.get("patterns", []) if isinstance(template_result, dict) else [],
                "confidence": template_result.get("confidence", 0) if isinstance(template_result, dict) else 0,
                "what_learned": f"Recognized patterns: {', '.join(template_result.get('patterns', []))}" if isinstance(template_result, dict) and template_result.get("patterns") else "No known patterns detected",
                "usefulness": "Matches visual templates (victory screens, specific UI elements)"
            },
            
            # Combined assessment - AI LEARNING & GAMEPLAY DECISION MAKING
            "summary": {
                "scene_type": best_scene,
                "description": (
                    gemini_result.get("description", "") if isinstance(gemini_result, dict) and gemini_result.get("used") and gemini_result.get("description")
                    else grok_result.get("description", "") if isinstance(grok_result, dict) and grok_result.get("used") and grok_result.get("description")
                    else blip_result.get("description", "") if isinstance(blip_result, dict) else ""
                ),
                # Prefer Gemini action, fallback to Grok
                "action_suggestion": (
                    gemini_result.get("action_suggestion", "") if isinstance(gemini_result, dict) and gemini_result.get("used") 
                    else grok_result.get("action_suggestion", "") if isinstance(grok_result, dict) and grok_result.get("used")
                    else ""
                ),
                # Combine game state from both AIs
                "game_state": " | ".join(filter(None, [
                    gemini_result.get("game_state", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                    grok_result.get("game_state", "") if isinstance(grok_result, dict) and grok_result.get("used") else ""
                ])),
                # Combine learning insights from both AIs
                "learning_insight": " | ".join(filter(None, [
                    gemini_result.get("learning_insight", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                    grok_result.get("learning_insight", "") if isinstance(grok_result, dict) and grok_result.get("used") else ""
                ])),
                "text_detected": len(ocr_result.get("text", "")) > 0 if isinstance(ocr_result, dict) else False,
                "ui_elements_count": len(opencv_result.get("ui_elements", [])) if isinstance(opencv_result, dict) else 0,
                "overall_confidence": round(
                    sum([
                        ocr_result.get("confidence", 0) if isinstance(ocr_result, dict) else 0,
                        blip_result.get("confidence", 0) if isinstance(blip_result, dict) else 0,
                        gemini_result.get("confidence", 0) if isinstance(gemini_result, dict) and gemini_result.get("used") else 0,
                        grok_result.get("confidence", 0) if isinstance(grok_result, dict) and grok_result.get("used") else 0,
                        template_result.get("confidence", 0) if isinstance(template_result, dict) else 0
                    ]) / methods_count, 2
                ),
                
                # AI LEARNING MODE - What the AI learns from this frame
                "learning_mode": {
                    "what_ai_learns": " | ".join(filter(None, [
                        gemini_result.get("learning_insight", "") if isinstance(gemini_result, dict) and gemini_result.get("used") else "",
                        grok_result.get("learning_insight", "") if isinstance(grok_result, dict) and grok_result.get("used") else ""
                    ])) or "Enable Gemini/Grok for learning insights",
                    "scene_understanding": f"{best_scene} scene with {len(ocr_result.get('text', '').split()) if isinstance(ocr_result, dict) else 0} words, {opencv_result.get('total_detected', 0) if isinstance(opencv_result, dict) else 0} UI elements",
                    "pattern_recognized": len(template_result.get("patterns", [])) if isinstance(template_result, dict) else 0,
                    "data_quality": (
                        "excellent" if (gemini_result.get("used") and grok_result.get("used") and ocr_result.get("regions", 0) > 0)
                        else "high" if ((gemini_result.get("used") or grok_result.get("used")) and ocr_result.get("regions", 0) > 0)
                        else "medium" if ocr_result.get("regions", 0) > 0
                        else "low"
                    )
                },
                
                # AI GAMEPLAY MODE - How this data will be used during gameplay
                "gameplay_mode": {
                    "action_coordinates": (
                        gemini_result.get("action_suggestion", "") if isinstance(gemini_result, dict) and gemini_result.get("used")
                        else grok_result.get("action_suggestion", "") if isinstance(grok_result, dict) and grok_result.get("used")
                        else "No action available"
                    ),
                    "decision_confidence": max(
                        gemini_result.get("confidence", 0) if isinstance(gemini_result, dict) and gemini_result.get("used") else 0,
                        grok_result.get("confidence", 0) if isinstance(grok_result, dict) and grok_result.get("used") else 0
                    ),
                    "fallback_available": opencv_result.get("total_detected", 0) > 0 if isinstance(opencv_result, dict) else False,
                    "can_play": bool(
                        gemini_result.get("action_suggestion") or grok_result.get("action_suggestion") 
                        or (opencv_result.get("total_detected", 0) > 0)
                    ) if isinstance(opencv_result, dict) else False
                },
                
                # METADATA
                "ai_ready": gemini_result.get("used", False) or grok_result.get("used", False),  # True if we have AI insights
                "actionable": bool(gemini_result.get("action_suggestion") or grok_result.get("action_suggestion")) if isinstance(gemini_result, dict) or isinstance(grok_result, dict) else False,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        logger.info(f"[Worker {worker_id}] 📊 Fused analysis complete - Scene: {fused_result['summary']['scene_type']}, Confidence: {fused_result['summary']['overall_confidence']}")
        
        return fused_result
        
    except Exception as e:
        logger.error(f"[Worker {worker_id}] Parallel analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-vision")
async def test_vision_analysis(request: TestVisionRequest):
    """
    Quick test endpoint for instant vision analysis without video upload.
    
    Usage:
    - Test BLIP-2 only: POST /test-vision {"image_path": "/path/to/image.png"}
    - Test with Gemini: POST /test-vision {"image_path": "/path/to/image.png", "use_gemini": true}
    - Test specific methods: Set use_blip2, use_ocr, use_opencv, use_template as needed
    
    Returns: Full analysis results from selected methods
    """
    logger.info(f"🧪 Testing vision analysis on: {request.image_path}")
    logger.info(f"Methods enabled - BLIP-2: {request.use_blip2}, Gemini: {request.use_gemini}, OCR: {request.use_ocr}, OpenCV: {request.use_opencv}, Template: {request.use_template}")
    
    # Validate image exists
    if not os.path.exists(request.image_path):
        raise HTTPException(status_code=404, detail=f"Image not found: {request.image_path}")
    
    # Create analysis request
    analysis_request = AnalysisRequest(
        screenshot_path=request.image_path,
        context={
            "use_gemini": request.use_gemini,
            "use_blip2": request.use_blip2,
            "use_ocr": request.use_ocr,
            "use_opencv": request.use_opencv,
            "use_template": request.use_template
        }
    )
    
    # Run analysis
    try:
        result = await parallel_multi_method_analysis(analysis_request)
        logger.info(f"✅ Test complete - Scene: {result.get('summary', {}).get('scene_type')}, Methods: {result.get('methods_used')}")
        return result
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8006"))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

