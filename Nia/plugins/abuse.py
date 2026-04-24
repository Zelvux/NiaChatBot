import re
from telegram import Update
from telegram.ext import ContextTypes

# 🔥 IMPORTANT: chatai & load_caches import kar
from Nia.database import chatai   # 👉 apne project ke hisab se path check kar
from Nia.utils import load_caches  # 👉 agar alag file me hai to correct kar

# 🔥 ABUSE LIST (tera full list)
abuse_list = [
    "aad", "aand", "bahenchod", "behenchod", "bhenchod", "bhenchodd", "b.c.", "bc", "bakchod", "bakchodd", "bakchodi",
    "bevda", "bewda", "bevdey", "bewday", "bevakoof", "bevkoof", "bevkuf", "bewakoof", "bewkoof", "bewkuf", "bhadua",
    "bhaduaa", "bhadva", "bhadvaa", "bhadwa", "bhadwaa", "bhosada", "bhosda", "bhosdaa", "bhosdike", "bhonsdike",
    "bsdk", "b.s.d.k", "bhosdiki", "bhosdiwala", "bhosdiwale", "bhosadchodal", "bhosadchod", "babbe", "babbey", "bube",
    "bubey", "bur", "burr", "buurr", "buur", "charsi", "chooche", "choochi", "chuchi", "chhod", "chod", "chodd",
    "chudne", "chudney", "chudwa", "chudwaa", "chudwane", "chudwaane", "choot", "chut", "chute", "chutia", "chutiya",
    "chutiye", "chuttad", "chutad", "dalaal", "dalal", "dalle", "dalley", "fattu", "gadha", "gadhe", "gadhalund",
    "gaand", "gand", "gandu", "gandfat", "gandfut", "gandiya", "gandiye", "gote", "gotey", "gotte",
    "hag", "haggu", "hagne", "hagney", "harami", "haramjada", "haraamjaada", "haramzyada", "haraamzyaada", "haraamjaade",
    "haraamzaade", "haraamkhor", "haramkhor", "jhat", "jhaat", "jhaatu", "jhatu", "kutta", "kutte", "kuttey", "kutia",
    "kutiya", "kuttiya", "kutti", "landi", "landy", "laude", "laudey", "laura", "lora", "lauda", "ling", "loda", "lode",
    "lund", "launda", "lounde", "laundey", "laundi", "loundi", "laundiya", "loundiya", "lulli", "maar", "maro",
    "marunga", "madarchod", "madarchodd", "madarchood", "madarchoot", "madarchut", "m.c.", "mc", "mamme", "mammey",
    "moot", "mut", "mootne", "mutne", "mooth", "muth", "nunni", "nunnu", "paaji", "paji", "pesaab", "pesab", "peshaab",
    "peshab", "pilla", "pillay", "pille", "pilley", "pisaab", "pisab", "pkmkb", "porkistan", "raand", "rand", "randi",
    "randy", "suar", "tatte", "tatti", "tatty", "ullu", "आंड़", "आंड", "आँड", "बहनचोद", "बेहेनचोद", "भेनचोद",
    "बकचोद", "बकचोदी", "बेवड़ा", "बेवड़े", "बेवकूफ", "भड़ुआ", "भड़वा", "भोसड़ा", "भोसड़ीके", "भोसड़ीकी",
    "भोसड़ीवाला", "भोसड़ीवाले", "भोसरचोदल", "भोसदचोद", "भोसड़ाचोदल", "भोसड़ाचोद", "बब्बे", "बूबे", "बुर",
    "चरसी", "चूचे", "चूची", "चुची", "चोद", "चुदने", "चुदवा", "चुदवाने", "चूत", "चूतिया", "चुटिया", "चूतिये",
    "चुत्तड़", "चूत्तड़", "दलाल", "दलले", "फट्टू", "गधा", "गधे", "गधालंड", "गांड", "गांडू", "गंडफट", "गंडिया",
    "गंडिये", "गू", "गोटे", "हग", "हग्गू", "हगने", "हरामी", "हरामजादा", "हरामज़ादा", "हरामजादे", "हरामज़ादे",
    "हरामखोर", "झाट", "झाटू", "कुत्ता", "कुत्ते", "कुतिया", "कुत्ती", "लेंडी", "लोड़े", "लौड़े", "लौड़ा",
    "लोड़ा", "लौडा", "लिंग", "लोडा", "लोडे", "लंड", "लौंडा", "लौंडे", "लौंडी", "लौंडिया", "लुल्ली", "मार",
    "मारो", "मारूंगा", "मादरचोद", "मादरचूत", "मादरचुत", "मम्मे", "मूत", "मुत", "मूतने", "मुतने", "मूठ", "मुठ",
    "नुननी", "नुननु", "पाजी", "पेसाब", "पेशाब", "पिल्ला", "पिल्ले", "पिसाब", "पोरकिस्तान", "रांड", "रंडी",
    "सुअर", "सूअर", "टट्टे", "टट्टी", "उल्लू"
]

# 🔥 TEXT CLEAN FUNCTION (ANTI-BYPASS)
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\u0900-\u097F]', '', text)
    return text

# ---------------- MAIN FUNCTION ---------------- #

async def delete_abusive_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            return

        ok = await message.reply_text("🔍 Searching abusive replies...")

        deleted_count = 0

        # 🔥 FAST COMBINED REGEX
        pattern = "|".join(map(re.escape, abuse_list))

        query = {
            "$or": [
                {"word": {"$regex": pattern, "$options": "i"}},
                {"text": {"$regex": pattern, "$options": "i"}}
            ]
        }

        result = await chatai.delete_many(query)
        deleted_count = result.deleted_count

        await ok.edit_text(f"✅ Deleted {deleted_count} abusive replies.")

        # 🔥 cache reload (safe)
        try:
            await load_caches()
        except:
            pass

    except Exception as e:
        print(f"[ERROR delete_abusive_replies] {e}")
        if update.message:
            await update.message.reply_text("❌ Error while deleting.")
