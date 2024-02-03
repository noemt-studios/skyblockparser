# skyblockparser v1.0.3
## This requires a [Hypixel API Key](https://developer.hypixel.net)

## Installation
Python 3.7 or higher is required.

Run `pip install skyblockparser` on your project folder.

## Usage
In the following example, we use the Profile class to get the stats of each member in a SkyBlock profile.

```py
from skyblockparser.profile import SkyblockParser
import requests

api_key = ""
uuid = "28667672039044989b0019b14a2c34d6" # Refractions UUID

url = f"https://api.hypixel.net/v2/skyblock/profiles?key={api_key}&uuid={uuid}"

response = requests.get(url).json()

player = SkyblockParser(response, uuid, api_key)
profile = player.select_profile("Apple") # Apple Profile of Refraction

print(profile.skill_data)
print(profile.dungeon_data)
print(profile.slayer_data)
# Printing some example data.

profile.inv[0].render().show()
# Item Render
```

## Valid Storage Types:
### Regular:
```
inv 
ender_chest
inv_armor
wardrobe
equipment
personal_vault
backpack_[index starting at 0] (Storage) the index sets the backpack
```

### Bags:
```
potion_bag
talisman_bag
fishing_bag
quiver
```

## Valid Stat Types:
```
skill_data
dungeon_data
slayer_data
```

# Note:
- Pets do not support rendering *yet* *unless they are not from the Pet Menu #HypixelAddPetLoreToApi
- If you want to use your own hosted api, or if mine ever goes offline, the code is in the `api` directory