from backend.matching import QUANTITIES, SET_QUANTITY_FORMS, match_order, normalize
from backend.menu import LOCALIZED_MENU_NAMES, MENU, MENU_BY_KEY, menu_payload


NODES = {
    "greeting": (
        "ನಮಸ್ಕಾರ! ಏನು ಬೇಕು? ಬೇಕಾದ ಐಟಂ ಮತ್ತು ಸಂಖ್ಯೆ ಹೇಳಿ.",
        "Namaskara! What would you like? Say the item and quantity.",
    ),
    "order_added": (
        "ಸರಿ, ಸೇರಿಸಿದ್ದೇನೆ. ಇನ್ನೇನು ಬೇಕು? ಐಟಂ ಮತ್ತು ಸಂಖ್ಯೆ ಹೇಳಿ, ಅಥವಾ 'ಅಷ್ಟೇ' ಎಂದು ಹೇಳಿ.",
        "Added. What else would you like? Say an item and quantity, or say “that’s all.”",
    ),
    "order_changed": (
        "ಸರಿ, ಬದಲಾಯಿಸಿದ್ದೇನೆ. ಇನ್ನೇನಾದರೂ ಬೇಕಿದ್ದರೆ ಐಟಂ ಮತ್ತು ಸಂಖ್ಯೆ ಹೇಳಿ; ಮುಗಿದಿದ್ದರೆ 'ಅಷ್ಟೇ' ಎಂದು ಹೇಳಿ.",
        "Updated. Say another item and quantity, or say “that’s all” when you’re done.",
    ),
    "order_removed": (
        "ಸರಿ, ತೆಗೆದುಹಾಕಿದ್ದೇನೆ. ಇನ್ನೇನಾದರೂ ಬೇಕಿದ್ದರೆ ಐಟಂ ಮತ್ತು ಸಂಖ್ಯೆ ಹೇಳಿ, ಅಥವಾ 'ಅಷ್ಟೇ' ಎಂದು ಹೇಳಿ.",
        "Removed. Say another item and quantity, or say “that’s all” when you’re done.",
    ),
    "order_unchanged": (
        "ಸರಿ, ಆ ಬದಲಾವಣೆ ಮಾಡಿಲ್ಲ. ಎಷ್ಟು ಕಡಿಮೆ ಮಾಡಬೇಕು ಎಂದು ಹೇಳಿ, ಅಥವಾ ಐಟಂ ಸಂಪೂರ್ಣ ತೆಗೆದುಹಾಕಲು 'ತೆಗೆದುಹಾಕಿ' ಎಂದು ಹೇಳಿ.",
        "I left your order unchanged. Say how many to reduce, or say “remove” to remove the item entirely.",
    ),
    "quantity_limit": (
        "ಒಂದು ಐಟಂಗೆ ಗರಿಷ್ಠ ಹತ್ತು ಮಾತ್ರ ಆರ್ಡರ್ ಮಾಡಬಹುದು. ದಯವಿಟ್ಟು ಹತ್ತಕ್ಕಿಂತ ಕಡಿಮೆ ಸಂಖ್ಯೆ ಹೇಳಿ.",
        "You can order up to 10 of each item. Please say a quantity of 10 or fewer.",
    ),
    "clarify": (
        "ಕ್ಷಮಿಸಿ, ಯಾವ ಐಟಂ ಮತ್ತು ಎಷ್ಟು ಎಂದು ಸ್ಪಷ್ಟವಾಗಿ ಹೇಳಿ. ಉದಾಹರಣೆಗೆ, 'ಒಂದು ಇಡ್ಲಿ ತೆಗೆದುಹಾಕಿ'.",
        "I’m not sure which item or quantity you mean. Please name both, for example, “remove one idli.”",
    ),
    "order_review": (
        "ಇದು ನಿಮ್ಮ ಆರ್ಡರ್. ಸರಿ ಇದ್ದರೆ 'ಖಚಿತಪಡಿಸಿ' ಎಂದು ಹೇಳಿ; ಬದಲಾವಣೆ ಬೇಕಿದ್ದರೆ ಏನು ಬದಲಿಸಬೇಕೆಂದು ಹೇಳಿ.",
        "Here’s your order. Say “confirm” to place it, or tell me what you’d like to change.",
    ),
    "order_confirmed": ("ನಿಮ್ಮ ಆರ್ಡರ್ ಖಚಿತವಾಗಿದೆ. ಧನ್ಯವಾದಗಳು!", "Your order is confirmed. Thank you!"),
    "order_cancelled": (
        "ಸರಿ, ಬದಲಾಯಿಸಬಹುದು. ಬೇಕಾದ ಐಟಂ ಮತ್ತು ಸಂಖ್ಯೆ ಹೇಳಿ; ಮುಗಿದಿದ್ದರೆ 'ಅಷ್ಟೇ' ಎಂದು ಹೇಳಿ.",
        "No problem. Say an item and quantity to change your order, or say “that’s all” when done.",
    ),
    "empty_order": (
        "ಆರ್ಡರ್ ಖಾಲಿಯಿದೆ. ಮೆನುವಿನಿಂದ ಬೇಕಾದ ಐಟಂ ಮತ್ತು ಸಂಖ್ಯೆ ಹೇಳಿ.",
        "Your order is empty. Choose an item from the menu and say how many you’d like.",
    ),
    "retry": (
        "ಕ್ಷಮಿಸಿ, ಅರ್ಥವಾಗಲಿಲ್ಲ. ಐಟಂ ಮತ್ತು ಸಂಖ್ಯೆಯನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಹೇಳಿ; ಉದಾಹರಣೆಗೆ, ಎರಡು ಇಡ್ಲಿ.",
        "Sorry, I didn’t catch that. Clearly say an item and quantity, like “two idlis.”",
    ),
    "empty_cart": (
        "ಆರ್ಡರ್ ಖಾಲಿಯಾಗಿದೆ. ಬೇಕಾದ ಐಟಂ ಮತ್ತು ಸಂಖ್ಯೆ ಹೇಳಿ, ಅಥವಾ ಮೆನುವಿನಿಂದ ಆಯ್ಕೆಮಾಡಿ.",
        "Your basket is empty. Say an item and quantity, or choose from the menu.",
    ),
}

TRANSLATED_NODES = {
    "ta": {
        "greeting": "வணக்கம்! என்ன வேண்டும்? உணவுப் பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள்.",
        "order_added": "சரி, சேர்த்துவிட்டேன். வேறு ஏதாவது வேண்டுமா? உணவுப் பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள்; முடிந்தால் “அவ்வளவுதான்” என்று சொல்லுங்கள்.",
        "order_changed": "சரி, மாற்றிவிட்டேன். வேறு ஏதாவது வேண்டுமெனில் பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள்; முடிந்ததும் “அவ்வளவுதான்” என்று சொல்லுங்கள்.",
        "order_removed": "சரி, நீக்கிவிட்டேன். வேறு ஏதாவது வேண்டுமெனில் பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள்; முடிந்தால் “அவ்வளவுதான்” என்று சொல்லுங்கள்.",
        "order_unchanged": "உங்கள் ஆர்டரை மாற்றவில்லை. எத்தனை குறைக்க வேண்டும் அல்லது எந்தப் பொருளை முழுவதும் நீக்க வேண்டும் என்று சொல்லுங்கள்.",
        "quantity_limit": "ஒவ்வொரு பொருளுக்கும் அதிகபட்சம் பத்து மட்டுமே ஆர்டர் செய்யலாம். பத்து அல்லது அதற்குக் குறைவான எண்ணிக்கையைச் சொல்லுங்கள்.",
        "clarify": "எந்தப் பொருள், எத்தனை என்பது தெளிவாகவில்லை. உதாரணமாக, “ஒரு இட்லியை நீக்குங்கள்” என்று சொல்லுங்கள்.",
        "order_review": "இது உங்கள் ஆர்டர். சரியாக இருந்தால் “உறுதிப்படுத்துங்கள்” என்று சொல்லுங்கள்; மாற்றம் வேண்டுமெனில் என்ன மாற்ற வேண்டும் என்று சொல்லுங்கள்.",
        "order_confirmed": "உங்கள் ஆர்டர் உறுதிசெய்யப்பட்டது. நன்றி!",
        "order_cancelled": "பரவாயில்லை. மாற்ற வேண்டிய பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள்; முடிந்தால் “அவ்வளவுதான்” என்று சொல்லுங்கள்.",
        "empty_order": "ஆர்டர் காலியாக உள்ளது. மெனுவிலிருந்து வேண்டிய பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள்.",
        "retry": "மன்னிக்கவும், புரியவில்லை. பொருளையும் எண்ணிக்கையையும் தெளிவாகச் சொல்லுங்கள்; உதாரணமாக, இரண்டு இட்லி.",
        "empty_cart": "கூடை காலியாக உள்ளது. வேண்டிய பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள் அல்லது மெனுவிலிருந்து தேர்வு செய்யுங்கள்.",
    },
    "te": {
        "greeting": "నమస్కారం! మీకు ఏమి కావాలి? పదార్థం పేరు, సంఖ్య చెప్పండి.",
        "order_added": "సరే, చేర్చాను. ఇంకేమైనా కావాలా? పదార్థం, సంఖ్య చెప్పండి లేదా “ఇంతే” అని చెప్పండి.",
        "order_changed": "సరే, మార్చాను. ఇంకేమైనా కావాలంటే పదార్థం, సంఖ్య చెప్పండి; పూర్తయితే “ఇంతే” అని చెప్పండి.",
        "order_removed": "సరే, తీసేశాను. ఇంకేమైనా కావాలంటే పదార్థం, సంఖ్య చెప్పండి లేదా “ఇంతే” అని చెప్పండి.",
        "order_unchanged": "మీ ఆర్డర్‌ను మార్చలేదు. ఎన్ని తగ్గించాలో లేదా ఏ పదార్థాన్ని పూర్తిగా తీసేయాలో చెప్పండి.",
        "quantity_limit": "ఒక్కో పదార్థానికి గరిష్ఠంగా పది మాత్రమే ఆర్డర్ చేయవచ్చు. పది లేదా అంతకంటే తక్కువ సంఖ్య చెప్పండి.",
        "clarify": "ఏ పదార్థం, ఎన్ని అనేది స్పష్టంగా లేదు. ఉదాహరణకు, “ఒక ఇడ్లీ తీసేయండి” అని చెప్పండి.",
        "order_review": "ఇది మీ ఆర్డర్. సరిగ్గా ఉంటే “ఖరారు చేయండి” అని చెప్పండి; మార్చాలంటే ఏమి మార్చాలో చెప్పండి.",
        "order_confirmed": "మీ ఆర్డర్ ఖరారైంది. ధన్యవాదాలు!",
        "order_cancelled": "పర్వాలేదు. మార్చాల్సిన పదార్థం, సంఖ్య చెప్పండి లేదా “ఇంతే” అని చెప్పండి.",
        "empty_order": "ఆర్డర్ ఖాళీగా ఉంది. మెనూలోని పదార్థం, కావాల్సిన సంఖ్య చెప్పండి.",
        "retry": "క్షమించండి, అర్థం కాలేదు. పదార్థం, సంఖ్య స్పష్టంగా చెప్పండి; ఉదాహరణకు, రెండు ఇడ్లీలు.",
        "empty_cart": "బుట్ట ఖాళీగా ఉంది. పదార్థం, సంఖ్య చెప్పండి లేదా మెనూ నుంచి ఎంచుకోండి.",
    },
}

MAX_ITEM_QUANTITY = 10
REVIEW_PHRASES = (
    "ಅಷ್ಟೇ", "ಇಷ್ಟೇ", "ಸಾಕು", "ಆಯಿತು", "ಮುಗಿಯಿತು", "ಇನ್ನೇನೂ ಬೇಡ",
    "that's all", "that is all", "thats all", "that's it", "that is it",
    "checkout", "check out", "review order", "show my order", "done ordering",
    "அவ்வளவுதான்", "அதுவே போதும்", "போதும்", "முடிந்தது", "ஆர்டர் முடிந்தது",
    "ఇంతే", "ఇంక చాలు", "చాలు", "పూర్తయింది", "ఆర్డర్ పూర్తయింది",
)
CONFIRM_PHRASES = (
    "confirm", "confirm order", "place order", "submit order", "yes place it",
    "ಹೌದು ಖಚಿತ", "ಆರ್ಡರ್ ಖಚಿತ", "ಖಚಿತಪಡಿಸಿ",
    "உறுதிப்படுத்துங்கள்", "ஆர்டரை உறுதி செய்யுங்கள்", "ஆர்டரை உறுதிப்படுத்தவும்",
    "ఖరారు చేయండి", "ఆర్డర్ ఖరారు చేయండి", "నిర్ధారించండి",
)
CANCEL_REVIEW_PHRASES = (
    "back to menu", "keep shopping", "continue ordering", "edit order",
    "ಮೆನುಗೆ ಹಿಂತಿರುಗಿ", "ಇನ್ನಷ್ಟು ಬೇಕು", "ಆರ್ಡರ್ ಬದಲಿಸಿ",
    "மெனுவுக்கு திரும்பு", "மேலும் வேண்டும்", "ஆர்டரை மாற்றுங்கள்",
    "మెనూకి తిరిగి", "ఇంకా కావాలి", "ఆర్డర్ మార్చండి",
)
REMOVE_PHRASES = (
    "remove", "delete", "cancel", "take off", "take away", "drop",
    "skip", "leave out", "get rid of", "without", "subtract",
    "don't want", "dont want", "do not want", "not want",
    "don't need", "dont need", "do not need", "no", "not",
    "ಬೇಡ", "ತೆಗೆದುಹಾಕಿ", "ತೆಗೆದುಹಾಕು", "ತೆಗೆದು ಬಿಡಿ", "ತೆಗೆದುಬಿಡಿ",
    "ತೆಗೆ", "ರದ್ದು", "ಬೇಡ ನನಗೆ",
    "நீக்குங்கள்", "நீக்கு", "எடுத்து விடுங்கள்", "எடுத்துவிடுங்கள்",
    "வேண்டாம்", "ரத்து செய்யுங்கள்", "ரద్దுசெய்யுங்கள்",
    "తీసేయండి", "తీసివేయండి", "వద్దు", "రద్దు చేయండి", "రద్దుచేయండి",
)
DECREASE_PHRASES = (
    "reduce", "decrease", "lower", "less", "fewer", "minus", "cut",
    "ಕಡಿಮೆ ಮಾಡಿ", "ಕಡಿಮೆ ಮಾಡು", "ಕಡಿಮೆ", "ಇಳಿಸಿ", "ಇಳಿಸು", "ತಗ್ಗಿಸಿ", "ತಗ್ಗಿಸು",
    "குறைக்கவும்", "குறையுங்கள்", "குறைத்திடுங்கள்", "குறைக்க",
    "తగ్గించండి", "తగ్గించు", "తక్కువ చేయండి", "తగ్గించాలి",
)
SET_QUANTITY_PHRASES = (
    "change", "set", "make it", "make that", "update", "increase", "increase to", "reduce to",
    "decrease to", "only", "all but", "except", "ಬದಲಿಸಿ", "ಇರಲಿ", "ಇರಿಸಿ",
    "மாற்றுங்கள்", "மாற்று", "வைத்துக்கொள்ளுங்கள்", "ஆக வையுங்கள்",
    "మార్చండి", "మార్చు", "ఉంచండి", "గా పెట్టండి",
    "ಮಾತ್ರ ಇರಲಿ", "ಇಷ್ಟೇ ಇರಲಿ", "ಮಾತ್ರ ಸಾಕು", "ಸಾಕು",
)
CLEAR_ORDER_PHRASES = (
    "clear order", "clear my order", "clear basket", "empty basket", "empty my order",
    "clear my basket", "cancel order", "cancel my order", "cancel the order",
    "cancel this order", "cancel current order", "cancel current orders",
    "cancel my current order", "cancel the current order", "cancel everything",
    "cancel all items", "cancel all my items", "remove everything", "remove all",
    "remove all items", "clear all",
    "ಎಲ್ಲಾ ತೆಗೆದುಹಾಕಿ", "ಆರ್ಡರ್ ಖಾಲಿ ಮಾಡಿ",
    "ನನ್ನ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ", "ಈ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ", "ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ",
    "ನನ್ನ ಆರ್ಡರ್ ಕ್ಯಾನ್ಸಲ್ ಮಾಡಿ", "ಆರ್ಡರ್ ಕ್ಯಾನ್ಸಲ್ ಮಾಡಿ", "ಎಲ್ಲಾ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ",
    "என் ஆர்டரை ரத்து செய்யுங்கள்", "எனது ஆர்டரை ரத்து செய்யுங்கள்",
    "ஆர்டரை ரத்து செய்யுங்கள்", "எல்லாவற்றையும் நீக்குங்கள்", "ஆர்டரை காலி செய்யுங்கள்",
    "నా ఆర్డర్ రద్దు చేయండి", "ఆర్డర్ రద్దు చేయండి", "అన్ని తీసేయండి", "ఆర్డర్ ఖాళీ చేయండి",
)
CLEAR_BASKET_PHRASES = (
    "clear order", "clear my order", "clear basket", "empty basket", "empty my order",
    "clear my basket", "cancel order", "cancel my order", "cancel the order",
    "cancel this order", "cancel current order", "cancel current orders",
    "cancel my current order", "cancel the current order", "cancel everything",
    "cancel all items", "cancel all my items", "remove everything", "remove all items",
    "clear all",
    "ಆರ್ಡರ್ ಖಾಲಿ ಮಾಡಿ",
    "ನನ್ನ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ", "ಈ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ", "ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ",
    "ನನ್ನ ಆರ್ಡರ್ ಕ್ಯಾನ್ಸಲ್ ಮಾಡಿ", "ಆರ್ಡರ್ ಕ್ಯಾನ್ಸಲ್ ಮಾಡಿ", "ಎಲ್ಲಾ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ",
    "என் ஆர்டரை ரத்து செய்யுங்கள்", "எனது ஆர்டரை ரத்து செய்யுங்கள்",
    "ஆர்டரை ரத்து செய்யுங்கள்", "எல்லாவற்றையும் நீக்குங்கள்", "ஆர்டரை காலி செய்யுங்கள்",
    "నా ఆర్డర్ రద్దు చేయండి", "ఆర్డర్ రద్దు చేయండి", "అన్ని తీసేయండి", "ఆర్డర్ ఖాళీ చేయండి",
)
NO_CHANGE_PHRASES = (
    "don't remove", "dont remove", "do not remove", "don't want to remove",
    "do not want to remove", "don't decrease", "do not decrease",
    "don't cancel", "dont cancel", "do not cancel",
    "don't change", "dont change", "do not change", "keep", "leave",
    "no need to remove", "stop removing", "no more",
    "ಕಡಿಮೆ ಮಾಡಬೇಡಿ", "ಕಡಿಮೆ ಮಾಡಬೇಡ", "ತೆಗೆದುಹಾಕಬೇಡಿ", "ತೆಗೆದುಹಾಕಬೇಡ",
    "ರದ್ದು ಮಾಡಬೇಡಿ", "ಬದಲಿಸಬೇಡಿ", "ಬದಲಾಯಿಸಬೇಡಿ", "ಅದೇ ಇರಲಿ",
    "குறைக்க வேண்டாம்", "நீக்க வேண்டாம்",
    "తగ్గించవద్దు", "తీసేయవద్దు",
    "மாற்ற வேண்டாம்", "நீக்க வேண்டாம்", "அப்படியே வையுங்கள்",
    "మార్చవద్దు", "తీసేయవద్దు", "అలాగే ఉంచండి",
)
CORRECTION_MARKERS = (
    "actually", "i mean", "scratch that", "wait", "sorry",
    "உண்மையில்", "அதாவது", "ஒரு நிமிடம்",
    "నిజానికి", "అంటే", "ఒక్క నిమిషం",
)
NEGATION_PHRASES = (
    "don't", "dont", "do not", "don't want to", "dont want to", "do not want to",
    "not", "never", "ಬೇಡ", "ಮಾಡಬೇಡಿ", "வேண்டாம்", "செய்யாதீர்கள்",
    "వద్దు", "చేయవద్దు", "కాదు",
)

KANNADA_QUANTITIES = {
    1: "ಒಂದು", 2: "ಎರಡು", 3: "ಮೂರು", 4: "ನಾಲ್ಕು", 5: "ಐದು",
    6: "ಆರು", 7: "ಏಳು", 8: "ಎಂಟು", 9: "ಒಂಬತ್ತು", 10: "ಹತ್ತು",
}


def _contains_phrase(transcript: str, phrases: tuple[str, ...]) -> bool:
    words = normalize(transcript).split()
    for phrase in phrases:
        phrase_words = normalize(phrase).split()
        if any(
            words[index:index + len(phrase_words)] == phrase_words
            for index in range(len(words) - len(phrase_words) + 1)
        ):
            return True
    return False


def _contains_unnegated_phrase(transcript: str, phrases: tuple[str, ...]) -> bool:
    words = normalize(transcript).split()
    for phrase in phrases:
        phrase_words = normalize(phrase).split()
        for index in range(len(words) - len(phrase_words) + 1):
            if words[index:index + len(phrase_words)] != phrase_words:
                continue
            preceding = words[max(0, index - 5):index]
            if any(
                preceding[-len(negation_words):] == negation_words
                for negation_words in (normalize(value).split() for value in NEGATION_PHRASES)
            ):
                continue
            return True
    return False


def _clarification(state: dict, hint: str) -> tuple[dict, dict]:
    return _response(
        state,
        "clarify",
        matched=False,
        order_updated=False,
        clarification_required=True,
        hint=hint,
    )


def initial_state(scene_key: str = "order", language: str = "kn") -> dict:
    if scene_key != "order":
        raise ValueError(f"Unknown ordering session: {scene_key}.")
    if language not in {"kn", "ta", "te"}:
        raise ValueError("Choose Kannada, Tamil, or Telugu.")
    return {
        "scene_key": "order",
        "language": language,
        "node": "greeting",
        "order": {},
        "reviewing": False,
        "complete": False,
    }


def _menu_title(key: str, language: str) -> str:
    if language == "kn":
        return MENU_BY_KEY[key]["kannada"]
    if language in {"ta", "te"}:
        return LOCALIZED_MENU_NAMES[key][language][0]
    return MENU_BY_KEY[key]["title"]


def build_bill(order: dict, language: str = "kn") -> dict:
    items = [
        {
            "key": key,
            "title": _menu_title(key, language),
            "quantity": quantity,
            "unit_price": MENU_BY_KEY[key]["price"],
            "line_total": MENU_BY_KEY[key]["price"] * quantity,
        }
        for key, quantity in order.items()
        if quantity > 0
    ]
    return {
        "items": items,
        "subtotal": sum(item["line_total"] for item in items),
        "total": sum(item["line_total"] for item in items),
        "currency": "INR",
    }


def scene_view(state: dict) -> dict:
    language = state.get("language", "kn")
    stage_key = "complete" if state.get("complete") else "review" if state.get("reviewing") else "order"
    bill = build_bill(state.get("order", {}), language)
    goal_items = [
        {
            "key": key,
            "title": _menu_title(key, language),
            "kannada": MENU_BY_KEY[key]["kannada"],
            "localized_title": _menu_title(key, language),
            "romanization": MENU_BY_KEY[key]["romanization"],
            "quantity": quantity,
            "price": MENU_BY_KEY[key]["price"],
            "line_total": MENU_BY_KEY[key]["price"] * quantity,
        }
        for key, quantity in state.get("order", {}).items()
        if quantity > 0
    ]
    return {
        "key": "order",
        "title": {
            "kn": "ದರ್ಶಿನಿ ಆರ್ಡರ್",
            "ta": "தர்ஷிணி ஆர்டர்",
            "te": "దర్శిని ఆర్డర్",
        }.get(language, "Darshini order"),
        "stage_key": stage_key,
        "stage_title": {
            "order": {
                "kn": "ನಿಮ್ಮ ಆರ್ಡರ್ ಮಾಡಿ",
                "ta": "ஆர்டரை உருவாக்குங்கள்",
                "te": "మీ ఆర్డర్ తయారు చేయండి",
            }.get(language, "Build your order"),
            "review": {
                "kn": "ನಿಮ್ಮ ಆರ್ಡರ್ ಪರಿಶೀಲಿಸಿ",
                "ta": "ஆர்டரைச் சரிபார்க்கவும்",
                "te": "ఆర్డర్‌ను పరిశీలించండి",
            }.get(language, "Review your order"),
            "complete": {
                "kn": "ಆರ್ಡರ್ ಖಚಿತವಾಗಿದೆ",
                "ta": "ஆர்டர் உறுதிசெய்யப்பட்டது",
                "te": "ఆర్డర్ ఖరారైంది",
            }.get(language, "Order confirmed"),
        }[stage_key],
        "stage_index": 1 if stage_key == "order" else 2,
        "stage_count": 2,
        "goal": dict(state.get("order", {})),
        "goal_items": goal_items,
        "order_total": bill["total"],
        "menu": menu_payload(language),
        "bill": bill if state.get("complete") else None,
    }


def _response(state: dict, line_key: str, **outcome) -> tuple[dict, dict]:
    language = state.get("language", "kn")
    line, line_english = localized_line(line_key, language)
    if "hint" in outcome and isinstance(outcome["hint"], str):
        outcome["hint"] = _localized_hint(outcome["hint"], language)
    next_state = {**state, "node": line_key}
    return next_state, {
        "matched": line_key != "retry",
        "line": line,
        "line_english": line_english,
        "line_key": line_key,
        "scene": scene_view(next_state),
        "order": dict(next_state.get("order", {})),
        "matched_terms": [],
        **outcome,
    }


def localized_line(line_key: str, language: str = "kn") -> tuple[str, str]:
    line, line_english = NODES[line_key]
    return TRANSLATED_NODES.get(language, {}).get(line_key, line), line_english


def _localized_hint(hint: str, language: str) -> str:
    if language not in {"kn", "ta", "te"}:
        return hint
    translations = {
        "Please name the menu item as well as the quantity. I won’t change the basket until that’s clear.": {
            "kn": "ಯಾವ ಪದಾರ್ಥ ಮತ್ತು ಎಷ್ಟು ಬೇಕು ಎಂದು ಹೇಳಿ. ಸ್ಪಷ್ಟವಾಗುವವರೆಗೆ ಬುಟ್ಟಿಯನ್ನು ಬದಲಾಯಿಸುವುದಿಲ್ಲ.",
            "ta": "பொருளின் பெயரையும் எண்ணிக்கையையும் சொல்லுங்கள். தெளிவாகும் வரை கூடையை மாற்றமாட்டேன்.",
            "te": "పదార్థం పేరు, సంఖ్య చెప్పండి. స్పష్టత వచ్చే వరకు బుట్టను మార్చను.",
        },
        "Your basket is unchanged. Say how many to remove, or say “remove” to remove the whole item.": {
            "kn": "ಬುಟ್ಟಿಯಲ್ಲಿ ಬದಲಾವಣೆ ಮಾಡಿಲ್ಲ. ಎಷ್ಟು ಕಡಿಮೆ ಮಾಡಬೇಕು ಅಥವಾ ಪದಾರ್ಥವನ್ನು ಸಂಪೂರ್ಣ ತೆಗೆದುಹಾಕಬೇಕೇ ಎಂದು ಹೇಳಿ.",
            "ta": "கூடையில் மாற்றமில்லை. எத்தனை நீக்க வேண்டும் அல்லது அந்தப் பொருளை முழுவதும் நீக்க வேண்டும் என்று சொல்லுங்கள்.",
            "te": "బుట్టలో మార్పు లేదు. ఎన్ని తీసేయాలో లేదా ఆ పదార్థం మొత్తాన్ని తీసేయాలో చెప్పండి.",
        },
        "Say the exact quantity, for example “change idli to two.”": {
            "kn": "ನಿಖರವಾದ ಪ್ರಮಾಣ ಹೇಳಿ. ಉದಾಹರಣೆಗೆ, “ಇಡ್ಲಿ ಎರಡೇ ಇರಲಿ” ಎಂದು ಹೇಳಿ.",
            "ta": "சரியான எண்ணிக்கையைச் சொல்லுங்கள்; உதாரணமாக, “இட்லியை இரண்டாக மாற்றுங்கள்”.",
            "te": "సరైన సంఖ్య చెప్పండి; ఉదాహరణకు, “ఇడ్లీని రెండుగా మార్చండి”.",
        },
        "Please say “confirm order” clearly to place it, or say “keep shopping” to continue editing.": {
            "kn": "ಆರ್ಡರ್ ಖಚಿತಪಡಿಸಲು “ಆರ್ಡರ್ ಖಚಿತಪಡಿಸಿ” ಎಂದು ಹೇಳಿ; ಬದಲಾವಣೆ ಮಾಡಲು “ಇನ್ನಷ್ಟು ಬೇಕು” ಎಂದು ಹೇಳಿ.",
            "ta": "ஆர்டரை உறுதிசெய்ய “ஆர்டரை உறுதிசெய்யுங்கள்” என்றும், மாற்ற “மேலும் வேண்டும்” என்றும் சொல்லுங்கள்.",
            "te": "ఆర్డర్ ఖరారు చేయడానికి “ఆర్డర్ ఖరారు చేయండి” అని, మార్చడానికి “ఇంకా కావాలి” అని చెప్పండి.",
        },
        "I heard a correction but not the corrected item or quantity. Please repeat the full request.": {
            "kn": "ತಿದ್ದುಪಡಿ ಕೇಳಿದೆ, ಆದರೆ ಪದಾರ್ಥ ಅಥವಾ ಪ್ರಮಾಣ ಸ್ಪಷ್ಟವಾಗಲಿಲ್ಲ. ಸಂಪೂರ್ಣವಾಗಿ ಮತ್ತೆ ಹೇಳಿ.",
            "ta": "நீங்கள் திருத்திச் சொன்னது புரிந்தது; ஆனால் பொருள் அல்லது எண்ணிக்கை தெளிவாகவில்லை. முழு கோரிக்கையையும் மீண்டும் சொல்லுங்கள்.",
            "te": "మీరు సరిచెప్పారని అర్థమైంది; కానీ పదార్థం లేదా సంఖ్య స్పష్టంగా లేదు. పూర్తి అభ్యర్థనను మళ్లీ చెప్పండి.",
        },
        "I heard a correction but can’t tell which item you meant. Please repeat the corrected item and quantity.": {
            "kn": "ತಿದ್ದುಪಡಿ ಅರ್ಥವಾಯಿತು, ಆದರೆ ಯಾವ ಪದಾರ್ಥ ಎಂದು ಸ್ಪಷ್ಟವಾಗಲಿಲ್ಲ. ಪದಾರ್ಥ ಮತ್ತು ಪ್ರಮಾಣವನ್ನು ಮತ್ತೆ ಹೇಳಿ.",
            "ta": "திருத்தம் புரிந்தது; எந்தப் பொருள் என்று தெளிவாகவில்லை. பொருளையும் எண்ணிக்கையையும் மீண்டும் சொல்லுங்கள்.",
            "te": "సరిచెప్పారని అర్థమైంది; ఏ పదార్థమో స్పష్టంగా లేదు. పదార్థం, సంఖ్య మళ్లీ చెప్పండి.",
        },
        "I heard a correction but can’t tell which item or quantity you meant. Please repeat the full corrected request.": {
            "kn": "ತಿದ್ದುಪಡಿಯಲ್ಲಿನ ಪದಾರ್ಥ ಅಥವಾ ಪ್ರಮಾಣ ಸ್ಪಷ್ಟವಾಗಲಿಲ್ಲ. ಸಂಪೂರ್ಣವಾಗಿ ಮತ್ತೆ ಹೇಳಿ.",
            "ta": "திருத்தப்பட்ட பொருள் அல்லது எண்ணிக்கை தெளிவாகவில்லை. முழு கோரிக்கையையும் மீண்டும் சொல்லுங்கள்.",
            "te": "సరిచెప్పిన పదార్థం లేదా సంఖ్య స్పష్టంగా లేదు. పూర్తి అభ్యర్థనను మళ్లీ చెప్పండి.",
        },
        "Try: “எரಡು ಇಡ್ಲಿ”, “add one coffee”, or “remove one idli”.": {
            "ta": "உதாரணம்: “இரண்டு இட்லி”, “ஒரு காபி சேர்க்கவும்” அல்லது “ஒரு இட்லியை நீக்குங்கள்”.",
            "te": "ఉదాహరణ: “రెండు ఇడ్లీలు”, “ఒక కాఫీ వేయండి” లేదా “ఒక ఇడ్లీ తీసేయండి”.",
        },
        "Try: “ಎರಡು ಇಡ್ಲಿ”, “add one coffee”, or “remove one idli”.": {
            "kn": "ಉದಾಹರಣೆ: “ಎರಡು ಇಡ್ಲಿ”, “ಒಂದು ಕಾಫಿ ಸೇರಿಸಿ” ಅಥವಾ “ಒಂದು ಇಡ್ಲಿ ತೆಗೆದುಹಾಕಿ”.",
            "ta": "உதாரணம்: “இரண்டு இட்லி”, “ஒரு காபி சேர்க்கவும்” அல்லது “ஒரு இட்லியை நீக்குங்கள்”.",
            "te": "ఉదాహరణ: “రెండు ఇడ్లీలు”, “ఒక కాఫీ వేయండి” లేదా “ఒక ఇడ్లీ తీసేయండి”.",
        },
    }
    return translations.get(hint, {}).get(language, hint)


def adjust_item(state: dict, key: str, delta: int) -> tuple[dict, dict]:
    if key not in MENU_BY_KEY:
        raise ValueError("That menu item is no longer available.")
    if not isinstance(delta, int) or delta == 0:
        raise ValueError("Choose a valid quantity change.")
    order = dict(state.get("order", {}))
    quantity = order.get(key, 0) + delta
    if quantity > MAX_ITEM_QUANTITY:
        raise ValueError(f"You can order up to {MAX_ITEM_QUANTITY} of each item.")
    if quantity < 0:
        raise ValueError("The basket quantity cannot be negative.")
    if quantity:
        order[key] = quantity
    else:
        order.pop(key, None)
    next_state = {**state, "order": order}
    line_key = "order_changed" if order.get(key) else "order_removed"
    return _response(next_state, line_key, order_updated=True)


def clear_order(state: dict) -> tuple[dict, dict]:
    next_state = {**state, "order": {}, "reviewing": False}
    return _response(next_state, "empty_cart", order_updated=True)


def review_order(state: dict) -> tuple[dict, dict]:
    if state.get("complete"):
        raise ValueError("This order has already been confirmed.")
    if not state.get("order"):
        return _response(state, "empty_order", order_updated=False)
    next_state = {**state, "reviewing": True}
    return _response(next_state, "order_review", order_review=True)


def cancel_review(state: dict) -> tuple[dict, dict]:
    return _response(
        {**state, "reviewing": False},
        "order_cancelled",
        order_updated=False,
    )


def confirm_order(state: dict) -> tuple[dict, dict]:
    if state.get("complete"):
        raise ValueError("This order has already been confirmed.")
    if not state.get("reviewing"):
        raise ValueError("Review your basket before confirming the order.")
    if not state.get("order"):
        raise ValueError("Add at least one item before confirming the order.")
    next_state = {**state, "reviewing": False, "complete": True}
    bill = build_bill(next_state["order"], next_state.get("language", "kn"))
    next_state, result = _response(
        next_state,
        "order_confirmed",
        order_confirmed=True,
        bill=bill,
    )
    return next_state, result


def process_turn(state: dict, transcript: str) -> tuple[dict, dict]:
    if state.get("complete"):
        raise ValueError("This order is already confirmed. Start a new order to continue.")

    if state.get("reviewing"):
        if _contains_unnegated_phrase(transcript, CONFIRM_PHRASES):
            return confirm_order(state)
        if _contains_phrase(transcript, CONFIRM_PHRASES):
            return _clarification(state, "Please say “confirm order” clearly to place it, or say “keep shopping” to continue editing.")
        if _contains_unnegated_phrase(transcript, CANCEL_REVIEW_PHRASES):
            return cancel_review(state)

    if _contains_unnegated_phrase(transcript, REVIEW_PHRASES):
        state, outcome = _apply_spoken_items(state, transcript)
        if outcome["order_updated"] and state["order"]:
            state, review = review_order(state)
            review["order_added"] = outcome.get("order_added", {})
            return state, review
        return review_order(state)

    return _apply_spoken_items(state, transcript)


def _action_mentions(tokens: list[str]) -> list[tuple[int, int, str]]:
    phrases = (
        *((phrase, "unchanged") for phrase in NO_CHANGE_PHRASES),
        *((phrase, "set") for phrase in SET_QUANTITY_PHRASES),
        *((phrase, "decrease") for phrase in DECREASE_PHRASES),
        *((phrase, "remove") for phrase in REMOVE_PHRASES),
        ("increase by", "add"),
        ("ಹೆಚ್ಚಿಸಿ", "add"),
        ("ಹೆಚ್ಚಿಸು", "add"),
        ("ಜಾಸ್ತಿ ಮಾಡಿ", "add"),
        ("ಜಾಸ್ತಿ ಮಾಡು", "add"),
        ("அதிகப்படுத்துங்கள்", "add"),
        ("கூட்டுங்கள்", "add"),
        ("சேர்க்கவும்", "add"),
        ("சேருங்கள்", "add"),
        ("ఇంకా వేయండి", "add"),
        ("పెంచండి", "add"),
        ("కలపండి", "add"),
        ("add", "add"),
        ("order", "add"),
        ("include", "add"),
        ("want", "add"),
        ("get", "add"),
        ("give", "add"),
        ("need", "add"),
        ("ಸೇರಿಸಿ", "add"),
        ("ಸೇರಿಸು", "add"),
        ("ಕೊಡಿ", "add"),
        ("ಬೇಕು", "add"),
        ("கொடுங்கள்", "add"),
        ("வேண்டும்", "add"),
        ("வேணும்", "add"),
        ("ఇవ్వండి", "add"),
        ("కావాలి", "add"),
        ("వేయండి", "add"),
    )
    mentions = []
    for phrase, action in phrases:
        phrase_tokens = normalize(phrase).split()
        for start in range(len(tokens) - len(phrase_tokens) + 1):
            end = start + len(phrase_tokens)
            if tokens[start:end] == phrase_tokens:
                mentions.append((start, end, action))
    return mentions


def _item_action(
    tokens: list[str],
    match: dict,
    next_match: dict | None,
    action_mentions: list[tuple[int, int, str]],
) -> str:
    start = match["start"]
    prior = [mention for mention in action_mentions if mention[1] <= start]
    last_contrast = max(
        (index for index, token in enumerate(tokens[:start]) if token in {"but", "however", "ಆದರೆ"}),
        default=-1,
    )
    prior = [mention for mention in prior if mention[0] > last_contrast]

    action = None
    if next_match is None:
        following = [
            mention
            for mention in action_mentions
            if match["end"] <= mention[0] <= match["end"] + 3
            and not any(
                token in {"and", "ಹಾಗೂ", "ಮತ್ತು", "but", "ಆದರೆ"}
                for token in tokens[match["end"]:mention[0]]
            )
        ]
        if following:
            action = max(following, key=lambda mention: (mention[1], mention[1] - mention[0]))[2]
    if action is None:
        action = max(prior, key=lambda mention: (mention[1], mention[1] - mention[0]))[2] if prior else "add"
    trailing = tokens[match["end"]:match["end"] + 4]
    if action == "decrease" and any(
        token in {"to", "ஆக", "ஆக்கு", "గా", "కి", "కు"}
        for token in trailing
    ):
        return "set"
    if action == "decrease" and any(
        token in QUANTITIES and token in SET_QUANTITY_FORMS
        for token in trailing
    ):
        return "set"
    if action == "set" and "increase" in tokens[:start] and "by" in trailing:
        return "add"
    return action


def _quantity_distance(position: int, match: dict) -> int:
    if position < match["start"]:
        return match["start"] - position
    if position >= match["end"]:
        return position - match["end"] + 1
    return 0


def parse_order_intents(transcript: str, matches: list[dict] | None = None) -> list[dict]:
    """Resolve matched menu items into canonical actions and quantities."""
    tokens = normalize(transcript).split()
    if matches is None:
        expected = {item["key"]: 0 for item in MENU}
        matches = match_order(transcript, expected)["matches"]
    action_mentions = _action_mentions(tokens)
    quantity_positions = [
        (
            index,
            int(token) if token.isdigit() else QUANTITIES.get(token),
        )
        for index, token in enumerate(tokens)
        if token.isdigit() or token in QUANTITIES
    ]

    intents = []
    for index, match in enumerate(matches):
        next_match = matches[index + 1] if index + 1 < len(matches) else None
        action = _item_action(tokens, match, next_match, action_mentions)
        quantity = match["quantity"]
        explicit_quantity = match["explicit_quantity"]
        if not explicit_quantity and action in {"add", "set", "decrease", "remove"}:
            candidates = [
                (position, value)
                for position, value in quantity_positions
                if value is not None and _quantity_distance(position, match) <= 4
            ]
            if candidates:
                nearest_distance = min(
                    _quantity_distance(position, match)
                    for position, _ in candidates
                )
                nearest = [
                    (position, value)
                    for position, value in candidates
                    if _quantity_distance(position, match) == nearest_distance
                ]
                other_item_is_closer = any(
                    other_index != index
                    and _quantity_distance(position, other_match) < nearest_distance
                    for position, _ in nearest
                    for other_index, other_match in enumerate(matches)
                )
                if len({value for _, value in nearest}) == 1 and not other_item_is_closer:
                    quantity = nearest[0][1]
                    explicit_quantity = True

        intents.append({
            **match,
            "action": action,
            "quantity": quantity,
            "explicit_quantity": explicit_quantity,
        })
    return intents


def _quantity_after_to(tokens: list[str], match: dict) -> int | None:
    trailing = tokens[match["end"]:match["end"] + 4]
    for token in trailing:
        if token in QUANTITIES and token in SET_QUANTITY_FORMS:
            return QUANTITIES[token]
    connectors = {"to", "ஆக", "ஆக்கு", "గా", "కి", "కు"}
    connector = next((token for token in trailing if token in connectors), None)
    if connector is None:
        return None
    quantity_index = match["end"] + trailing.index(connector) + 1
    if quantity_index >= len(tokens):
        return None
    value = tokens[quantity_index]
    if value.isdigit():
        return int(value)
    return QUANTITIES.get(value)


def _correction_rewrite(transcript: str) -> tuple[str | None, str | None]:
    tokens = normalize(transcript).split()
    markers = [
        (index, len(normalize(marker).split()))
        for marker in CORRECTION_MARKERS
        for index in range(len(tokens) - len(normalize(marker).split()) + 1)
        if tokens[index:index + len(normalize(marker).split())] == normalize(marker).split()
    ]
    if not markers:
        return None, None
    marker_start, marker_length = min(markers)
    prefix = " ".join(tokens[:marker_start])
    suffix = " ".join(tokens[marker_start + marker_length:])
    if not suffix:
        return None, "I heard a correction but not the corrected item or quantity. Please repeat the full request."

    prefix_matches = match_order(prefix, {item["key"]: 0 for item in MENU})["matches"]
    suffix_matches = match_order(suffix, {item["key"]: 0 for item in MENU})["matches"]
    prefix_keys = {match["key"] for match in prefix_matches}
    suffix_keys = {match["key"] for match in suffix_matches}
    suffix_actions = {
        mention[2]
        for mention in _action_mentions(suffix.split())
    }

    if suffix_actions & {"add", "remove", "decrease"}:
        return suffix, None
    if suffix_matches:
        if "set" in suffix_actions:
            return suffix, None
        if (
            len(prefix_keys) == 1
            and suffix_keys == prefix_keys
            and all(match["explicit_quantity"] for match in suffix_matches)
        ):
            key = next(iter(prefix_keys))
            quantity = suffix_matches[-1]["quantity"]
            return f"set {MENU_BY_KEY[key]['romanization']} to {quantity}", None
        if prefix_keys:
            return None, "I heard a correction but can’t tell which item you meant. Please repeat the corrected item and quantity."
        return suffix, None

    suffix_tokens = suffix.split()
    quantities = [
        int(token) if token.isdigit() else QUANTITIES[token]
        for token in suffix_tokens
        if token.isdigit() or token in QUANTITIES
    ]
    if len(prefix_keys) == 1 and quantities:
        key = next(iter(prefix_keys))
        return f"set {MENU_BY_KEY[key]['romanization']} to {quantities[-1]}", None
    if prefix_keys:
        return None, "I heard a correction but can’t tell which item or quantity you meant. Please repeat the full corrected request."
    return suffix, None


def _is_vague_edit(transcript: str) -> bool:
    words = normalize(transcript).split()
    has_action = bool(
        _contains_phrase(transcript, REMOVE_PHRASES + DECREASE_PHRASES + SET_QUANTITY_PHRASES)
        or any(word in {"add", "increase", "ಸೇರಿಸಿ", "ಹೆಚ್ಚಿಸಿ"} for word in words)
    )
    has_reference = any(
        word in {
            "it", "that", "one", "last", "same", "ಇದನ್ನು", "ಅದನ್ನು", "ಅದು",
            "இது", "அது", "அதை", "கடைசி", "அதே",
            "ఇది", "అది", "దాన్ని", "చివరి", "అదే",
        }
        or word.isdigit()
        or word in QUANTITIES
        for word in words
    )
    return has_action and has_reference


def _apply_spoken_items(state: dict, transcript: str) -> tuple[dict, dict]:
    correction, correction_hint = _correction_rewrite(transcript)
    if correction_hint:
        return _clarification(state, correction_hint)
    if correction is not None:
        return _apply_spoken_items(state, correction)

    all_items = {item["key"]: 0 for item in MENU}
    heard = match_order(transcript, all_items)
    matches = heard["matches"]
    if not matches and _contains_phrase(transcript, CLEAR_ORDER_PHRASES):
        if not _contains_unnegated_phrase(transcript, CLEAR_ORDER_PHRASES):
            return _response(state, "order_unchanged", order_updated=False)
        return clear_order(state)
    if not matches:
        if _is_vague_edit(transcript):
            return _clarification(
                state,
                "Please name the menu item as well as the quantity. I won’t change the basket until that’s clear.",
            )
        return _response(
            state,
            "retry",
            order_updated=False,
            hint="Try: “ಎರಡು ಇಡ್ಲಿ”, “add one coffee”, or “remove one idli”.",
        )

    tokens = normalize(transcript).split()
    intents = parse_order_intents(transcript, matches)
    original_order = dict(state.get("order", {}))
    clear_basket = _contains_unnegated_phrase(transcript, CLEAR_BASKET_PHRASES)
    order = {} if clear_basket else dict(original_order)
    addition_baseline = dict(order)
    requested_actions = []
    previous_match = None
    previous_action = None
    skipped_matches = set()
    for index, match in enumerate(intents):
        if index in skipped_matches:
            continue
        next_match = matches[index + 1] if index + 1 < len(matches) else None
        action = match["action"]
        target_quantity = None
        if next_match is not None and next_match["key"] == match["key"]:
            target_tokens = tokens[next_match["start"]:next_match["end"]]
            has_quantity_target_suffix = any(
                token.endswith(("ಗೆ", "ಕ್ಕೆ", "க்கு", "ஆக", "யை", "ஐ", "ని", "గా", "కి", "కు"))
                for token in target_tokens
            )
            target_action = intents[index + 1]["action"]
            if (
                has_quantity_target_suffix
                and next_match["explicit_quantity"]
                and target_action in {"decrease", "set"}
            ):
                action = "set"
                target_quantity = next_match["quantity"]
                skipped_matches.add(index + 1)
        if (
            previous_match is not None
            and previous_action == "set"
            and previous_match["key"] == match["key"]
            and any(
                connector in tokens[previous_match["end"]:match["start"]]
                for connector in {"to", "ஆக", "ஆக்கு", "గా", "కి", "కు"}
            )
        ):
            previous_match = match
            previous_action = action
            continue
        key = match["key"]
        quantity = match["quantity"]
        old_quantity = order.get(key, 0)
        if action == "unchanged":
            previous_match = match
            previous_action = action
            continue
        if action == "set":
            requested_quantity = (
                target_quantity
                if target_quantity is not None
                else _quantity_after_to(tokens, match)
            )
            if requested_quantity is None and match["explicit_quantity"]:
                requested_quantity = quantity
            if requested_quantity is None and "except" in tokens[:match["start"]]:
                requested_quantity = 1
            if requested_quantity is None:
                return _response(
                    state,
                    "retry",
                    order_updated=False,
                    hint="Say the exact quantity, for example “change idli to two.”",
                )
            new_quantity = requested_quantity
        elif action == "remove":
            new_quantity = max(0, old_quantity - quantity) if match["explicit_quantity"] else 0
        elif action == "decrease":
            new_quantity = max(0, old_quantity - quantity)
        else:
            new_quantity = old_quantity + quantity
        if new_quantity > MAX_ITEM_QUANTITY:
            limit_hint = {
                "kn": f"ಒಂದು ಪದಾರ್ಥಕ್ಕೆ ಗರಿಷ್ಠ ಹತ್ತು ಮಾತ್ರ. {_menu_title(key, 'kn')} ಹತ್ತಕ್ಕಿಂತ ಹೆಚ್ಚು ಸೇರಿಸಲಾಗದು.",
                "ta": f"{_menu_title(key, 'ta')}க்கு அதிகபட்ச எண்ணிக்கை {MAX_ITEM_QUANTITY}.",
                "te": f"{_menu_title(key, 'te')}కు గరిష్ఠ సంఖ్య {MAX_ITEM_QUANTITY}.",
            }.get(state.get("language", "kn"), f"{MENU_BY_KEY[key]['title']} is limited to {MAX_ITEM_QUANTITY} per order.")
            return _response(
                state,
                "quantity_limit",
                order_updated=False,
                quantity_limit_exceeded=True,
                hint=limit_hint,
            )
        if new_quantity:
            order[key] = new_quantity
        else:
            order.pop(key, None)
        requested_actions.append(action)
        previous_match = match
        previous_action = action

    if order == original_order:
        return _response(
            state,
            "order_unchanged",
            order_updated=False,
            hint="Your basket is unchanged. Say how many to remove, or say “remove” to remove the whole item.",
        )

    next_state = {**state, "order": order}
    if requested_actions and all(action in {"remove", "decrease"} for action in requested_actions):
        line_key = "order_removed"
    elif requested_actions and all(action == "add" for action in requested_actions):
        line_key = "order_added"
    else:
        line_key = "order_changed"
    changed = {
        key: order.get(key, 0)
        for key in set(original_order) | set(order)
        if original_order.get(key, 0) != order.get(key, 0)
    }
    added = {
        key: order[key] - addition_baseline.get(key, 0)
        for key in order
        if order[key] > addition_baseline.get(key, 0)
    }
    return _response(
        next_state,
        line_key,
        order_updated=True,
        order_added=added,
        order_changes=changed,
        found=heard["found"],
        expected=original_order,
        matched_terms=heard["matched_terms"],
    )
