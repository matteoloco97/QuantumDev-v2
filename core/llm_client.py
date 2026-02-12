"""
core/llm_client.py - Unified LLM Client for DeepSeek R1
Centralizes all LLM interactions with retry logic and error handling
"""
import requests
import re
import codecs
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class LLMClient:
    """
    DeepSeek R1 client with reasoning support and automatic retry logic.
    
    Features:
    - Automatic retry with exponential backoff
    - <think> tag cleaning for DeepSeek R1
    - Code block extraction with escape sequence handling
    - Temperature calibration for different modes
    """
    
    def __init__(self, api_url: str = "http://localhost:8001/chat/god-mode"):
        self.api_url = api_url
        self.model = "DeepSeek-R1-Distill-Qwen-32B-abliterated-Q6_K.gguf"
        logger.info(f"LLMClient initialized with endpoint: {api_url}")
    
    def generate(
        self, 
        message: str, 
        history: List[Dict] = None,
        system_context: str = "",
        mode: str = "general",
        silent: bool = False,
        max_retries: int = 3,
        timeout: int = 300
    ) -> str:
        """
        Generate response with automatic retry on failure.
        
        Args:
            message: User input message
            history: Conversation history (list of dicts with 'role' and 'content')
            system_context: System prompt to prepend
            mode: "general" or "factory"
            silent: Suppress logging
            max_retries: Number of retry attempts on failure
            timeout: Request timeout in seconds
        
        Returns:
            LLM response text
        """
        if history is None:
            history = []
        
        full_prompt = f"{system_context}\n\nUTENTE: {message}" if system_context else message
        payload = {
            "message": full_prompt,
            "history": history,
            "mode": mode
        }
        
        for attempt in range(max_retries):
            try:
                if not silent:
                    logger.debug(f"LLM request attempt {attempt + 1}/{max_retries}")
                
                resp = requests.post(self.api_url, json=payload, timeout=timeout)
                resp.raise_for_status()
                
                result = resp.json().get("response", "")
                
                if not silent:
                    logger.info(f"LLM response received ({len(result)} chars)")
                
                return result
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"Timeout after {max_retries} attempts")
                return f"ERRORE API: Timeout dopo {max_retries} tentativi"
                
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return f"ERRORE API: {e}"
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return f"ERRORE API: {e}"
        
        return "ERRORE: Max retries exceeded"
    
    @staticmethod
    def clean_think_tags(text: str) -> str:
        """
        Remove <think> reasoning tags from DeepSeek R1 output.
        
        Args:
            text: Raw LLM output
        
        Returns:
            Cleaned text without <think>...</think> blocks
        """
        if not text:
            return ""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    @staticmethod
    def extract_code_block(text: str) -> Optional[str]:
        """
        Extract code from markdown blocks with escape sequence handling.
        
        Handles:
        - Markdown code blocks (```language ... ```)
        - DeepSeek R1 <think> tags
        - Escaped newlines (\\n → real newlines)
        
        Args:
            text: Raw text containing code blocks
        
        Returns:
            Extracted code or None if no code block found
        """
        if not text:
            return None
        
        # 1. Remove <think> tags
        clean = LLMClient.clean_think_tags(text)
        
        # 2. Extract code blocks (supports language specification)
        matches = re.findall(r'```(?:\w+)?\s*(.*?)```', clean, re.DOTALL)
        if not matches:
            return None
        
        # 3. Get longest block (most likely to be the actual code)
        code = max(matches, key=len).strip()
        
        # 4. Unescape if needed (fix for literal \n sequences)
        if '\\n' in code:
            real_newlines = code.count('\n')
            escaped_newlines = code.count('\\n')
            
            # If >50% of newlines are escaped, perform unescape
            if escaped_newlines > real_newlines * 0.5:
                try:
                    code = codecs.decode(code, 'unicode_escape')
                    logger.debug("Unescaped literal escape sequences in code block")
                except Exception as e:
                    logger.warning(f"Unicode unescape failed, using fallback: {e}")
                    # Fallback: manual replacement
                    code = code.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
        
        return code
