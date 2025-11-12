"""
LLaVA Model Loader - Pre-loads model at agent startup
Runs in background to avoid blocking agent service
"""

import logging
import asyncio
import os
from typing import Optional

logger = logging.getLogger(__name__)

class LLaVALoader:
    """Background loader for LLaVA model"""
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.loading = False
        self.loaded = False
        self.error = None
        
    async def preload_model(self):
        """Pre-load LLaVA model in background"""
        if self.loading or self.loaded:
            return
        
        self.loading = True
        logger.info("🔮 Starting LLaVA model pre-load in background...")
        
        try:
            import torch
            from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
            
            model_id = "llava-hf/llava-v1.6-mistral-7b-hf"
            
            # Check if model is already cached
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            if os.path.exists(cache_dir):
                logger.info("✅ LLaVA cache found, loading will be fast")
            else:
                logger.info("📥 First time: downloading LLaVA (~7GB, 5-10 min)")
            
            # Load in thread to not block
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"🖥️  Loading on: {device}")
            
            self.processor = await asyncio.to_thread(
                LlavaNextProcessor.from_pretrained,
                model_id
            )
            logger.info("✅ Processor loaded")
            
            self.model = await asyncio.to_thread(
                LlavaNextForConditionalGeneration.from_pretrained,
                model_id,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else "cpu",
                low_cpu_mem_usage=True
            )
            logger.info("✅ Model loaded")
            
            self.loaded = True
            logger.info("🎉 LLaVA ready for vision AI!")
            
        except ImportError as e:
            self.error = f"LLaVA dependencies not installed: {e}"
            logger.warning(f"⚠️  {self.error}")
        except Exception as e:
            self.error = str(e)
            logger.error(f"❌ Failed to load LLaVA: {e}")
        finally:
            self.loading = False
    
    def get_model(self):
        """Get loaded model if available"""
        if self.loaded:
            return self.model, self.processor
        return None, None
    
    def get_status(self):
        """Get loading status"""
        return {
            "loading": self.loading,
            "loaded": self.loaded,
            "error": self.error
        }

# Global instance
llava_loader = LLaVALoader()

async def start_preload():
    """Start pre-loading LLaVA model"""
    asyncio.create_task(llava_loader.preload_model())
