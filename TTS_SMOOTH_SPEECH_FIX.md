# TTS Smooth Speech Fix - Punctuation Pause Elimination

## Problem with Punctuation Pauses

**Before Fix:**
```python
# Raw text chunks sent to TTS with punctuation
"Hello, I'm"     → TTS plays with comma pause
"SAIGE, your"    → TTS plays with comma pause  
"assistant. I"   → TTS plays with period pause (long!)
"can help,"      → TTS plays with comma pause
```

**Result:** Choppy speech with artificial pauses between chunks

## After Fix - Smooth Flow

**After Fix:**
```python
# Punctuation cleaned before TTS
"Hello, I'm"     → "Hello I'm"      (smooth)
"SAIGE, your"    → "SAIGE your"     (smooth)
"assistant. I"   → "assistant I"    (smooth)
"can help,"      → "can help"       (smooth)
```

**Result:** Natural flowing speech without artificial chunk pauses

## Code Implementation

```python
def add_text(self, text):
    if text.strip():
        # Clean punctuation for smoother speech flow
        clean_text = text.strip()
        clean_text = clean_text.replace(',', ' ').replace('.', ' ')
        clean_text = clean_text.replace('!', ' ').replace('?', ' ')
        clean_text = ' '.join(clean_text.split())  # Clean extra spaces
        
        if clean_text:
            self.tts_queue.put(clean_text)
```

## Benefits
✅ **No artificial pauses** between chunks  
✅ **Smoother speech flow** across word boundaries  
✅ **Faster audio** without punctuation delays  
✅ **Natural conversation** rhythm  

The TTS now flows like natural continuous speech instead of choppy sentence fragments!