import os
import re
import requests


def extract_flight_code(text: str) -> str | None:
  """Extracts KQ flight codes (e.g., KQ101, KQ 102, kq305) from user text."""
  pattern = r'\b(kq\s?\d{3,4})\b'
  match = re.search(pattern, text, re.IGNORECASE)
  if match:
    return match.group(1).replace(' ', '').upper()
  return None


def get_live_flight_status(flight_code: str) -> str:
  """Queries live aviation API for real-time KQ flight status."""
  # Get a free API key from AviationStack (100 free calls/mo)
  api_key = os.getenv("AVIATIONSTACK_API_KEY", "459c83af34f9ea01033e145d6cfb230f")

  url = "http://api.aviationstack.com/v1/flights"
  params = {"access_key": api_key, "flight_iata": flight_code.upper()}

  try:
    response = requests.get(url, params=params, timeout=5)
    data = response.json()

    if "data" in data and len(data["data"]) > 0:
      flight = data["data"][0]
      status = flight.get("flight_status", "Scheduled").capitalize()
      dep_airport = flight.get("departure", {}).get(
          "airport", "Nairobi Jomo Kenyatta"
      )
      arr_airport = flight.get("arrival", {}).get("airport", "Destination")
      sched_dep = flight.get("departure", {}).get("scheduled", "N/A")
      sched_arr = flight.get("arrival", {}).get("scheduled", "N/A")
      gate = flight.get("departure", {}).get("gate", "TBD")

      return (
          f"✈️ **Live Flight Status for {flight_code.upper()}:**\n\n"
          f"• **Status:** {status}\n"
          f"• **Origin:** {dep_airport}\n"
          f"• **Destination:** {arr_airport}\n"
          f"• **Scheduled Departure:** {sched_dep}\n"
          f"• **Scheduled Arrival:** {sched_arr}\n"
          f"• **Gate:** {gate}"
      )
    else:
      return (
          f"I extracted flight code **{flight_code.upper()}**, but could not find"
          " an active live schedule for today. Please verify the flight"
          " number."
      )

  except Exception as e:
    return f"Unable to fetch live flight details right now. Internal Error: {str(e)}"