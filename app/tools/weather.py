"""Live info tool: current Goa weather from Open-Meteo (free, no key)."""
import httpx

GOA = (15.2993, 74.1240)


async def goa_weather() -> str:
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={GOA[0]}&longitude={GOA[1]}"
           "&current=temperature_2m,precipitation,wind_speed_10m&timezone=Asia%2FKolkata")
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(url)
    r.raise_for_status()
    cur = r.json()["current"]
    return (f"Live Goa weather: {cur['temperature_2m']}°C, rain {cur['precipitation']} mm, "
            f"wind {cur['wind_speed_10m']} km/h (as of {cur['time']})")
