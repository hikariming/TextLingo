"""
Flashcard field mapping logic for different card types
"""
from typing import List, Dict, Any, Tuple


def get_jlpt_card_content(fields: List[str], tags: List[str]) -> Tuple[str, str]:
    """
    Get front and back content for JLPT cards
    
    JLPT card field structure:
    0: ID
    1: Japanese word (日文单词)
    2: Pitch accent (①)
    3: Part of speech (名)
    4: English translation
    5: Chinese translation (simplified)
    6: Chinese translation (traditional)
    7: Empty
    8: Audio reference for word
    9: Empty
    10: Example sentence (Japanese)
    11: Example sentence with furigana
    12: Example sentence (Chinese simplified)
    13: Example sentence (Chinese traditional)
    14: Audio reference for example
    ... more fields
    """
    # For JLPT cards, front should be Japanese word, back should be Chinese meaning
    front = fields[1] if len(fields) > 1 else ""
    
    # Try to get Chinese translation, fallback to English if not available
    if len(fields) > 5 and fields[5]:
        back = fields[5]  # Simplified Chinese
    elif len(fields) > 4 and fields[4]:
        back = fields[4]  # English
    elif len(fields) > 1:
        back = fields[1]  # Fallback to Japanese word itself
    else:
        back = ""
    
    # Add part of speech and pitch accent to back if available
    extras = []
    if len(fields) > 3 and fields[3]:
        extras.append(fields[3])  # Part of speech
    if len(fields) > 2 and fields[2]:
        extras.append(fields[2])  # Pitch accent
    
    if extras:
        back = f"{back}\n{' '.join(extras)}"
    
    return front, back


def get_basic_card_content(fields: List[str]) -> Tuple[str, str]:
    """
    Get front and back content for basic cards
    """
    front = fields[0] if len(fields) > 0 else ""
    back = fields[1] if len(fields) > 1 else ""
    return front, back


def map_card_fields(fields: List[str], tags: List[str], note_type_name: str = "") -> Tuple[str, str]:
    """
    Map fields to front and back content based on card type
    
    Returns:
        Tuple of (front_content, back_content)
    """
    # Process tags - they might be comma-separated or have special format
    processed_tags = []
    for tag in tags:
        # Handle tags like ",NEW-JLPT-v2::N5,NEW-JLPT-v2::v25.06.24,"
        if ',' in tag:
            # Split by comma and clean
            subtags = [t.strip() for t in tag.split(',') if t.strip()]
            processed_tags.extend(subtags)
        else:
            processed_tags.append(tag)
    
    # Check if this is a JLPT card
    is_jlpt = any("jlpt" in tag.lower() or "n5" in tag.lower() or "n4" in tag.lower() 
                  or "n3" in tag.lower() or "n2" in tag.lower() or "n1" in tag.lower() 
                  for tag in processed_tags)
    
    # Check if first field looks like a UUID (indicating JLPT structure)
    is_uuid_first = len(fields) > 0 and len(fields[0]) == 36 and fields[0].count('-') == 4
    
    if is_jlpt or is_uuid_first:
        return get_jlpt_card_content(fields, processed_tags)
    else:
        return get_basic_card_content(fields)


def get_media_fields_for_card(fields: List[str], tags: List[str]) -> Dict[str, List[int]]:
    """
    Get the field indices that contain media references
    
    Returns:
        Dict mapping media type to list of field indices
    """
    is_jlpt = any("jlpt" in tag.lower() or "n5" in tag.lower() for tag in tags)
    
    if is_jlpt:
        return {
            "audio": [8, 14],  # Word audio and example audio
            "image": []  # JLPT cards typically don't have images
        }
    else:
        # For other card types, scan all fields for media references
        audio_fields = []
        image_fields = []
        
        for i, field in enumerate(fields):
            if "[音频:" in field or "[sound:" in field:
                audio_fields.append(i)
            if "<img" in field:
                image_fields.append(i)
        
        return {
            "audio": audio_fields,
            "image": image_fields
        }