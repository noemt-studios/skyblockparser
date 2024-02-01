from util.profile import SkyblockParser
import requests

api_key = "hypixel_api_key"
uuid = "28667672039044989b0019b14a2c34d6" # Refractions UUID

url = f"https://api.hypixel.net/v2/skyblock/profiles?key={api_key}&uuid={uuid}"

response = requests.get(url).json()

player = SkyblockParser(response, uuid, api_key)
profile = player.select_profile("Apple") # Apple Profile of Refraction

print(profile.skill_data)
print(profile.dungeon_data)
print(profile.slayer_data)
# Printing some example data.

profile.inventory[0].render().show()
# Item Render