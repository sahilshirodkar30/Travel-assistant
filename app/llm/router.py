"""Model Rounting """

from enum import Enum


class Tier(str,Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


INTENT_TIER ={
    "booking_lookup": Tier.SMALL,
    "refund_status": Tier.SMALL,
    "booking_change": Tier.SMALL,
    "place_info": Tier.MEDIUM,
    "live_info": Tier.MEDIUM,
    "itinerary": Tier.LARGE,
    "chitchat": Tier.SMALL
}

def pick_tier(intent:str,message:str)->Tier:
    tier = INTENT_TIER.get(intent,Tier.MEDIUM)
    if tier is Tier.MEDIUM and len(message)>400:
        return Tier.LARGE
    return tier