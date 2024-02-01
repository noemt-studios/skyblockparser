from .exceptions import *
from .constants import *
from .levels import *
from .renderer import render
import gzip
import base64
import struct
import asyncio
import aiohttp


def TAG_End(b):
    return None, b


def TAG_byte(b):
    return b[0], b[1:]


def TAG_Short(b):
    return struct.unpack('>h', b[:2])[0], b[2:]


def TAG_Short_unsigned(b):
    return struct.unpack('>H', b[:2])[0], b[2:]


def TAG_Int(b):
    return struct.unpack('>i', b[:4])[0], b[4:]


def TAG_Long(b):
    return struct.unpack('>q', b[:8])[0], b[8:]


def TAG_Float(b):
    return struct.unpack('>f', b[:4])[0], b[4:]


def TAG_Double(b):
    return struct.unpack('>d', b[:8])[0], b[8:]


def TAG_Byte_Array(b):
    length, b = TAG_Int(b)
    items = []
    for _ in range(length):
        item, b = TAG_byte(b)
        items.append(item)
    decomp = gzip.decompress(bytes(items))
    return TAG_Compound(decomp)[0]['']['i'], b


def TAG_String(b):
    length, b = TAG_Short_unsigned(b)
    value = b[:length]
    b = b[length:]
    return value, b


def TAG_List(b, use_binary=False):
    tag_type, b = b[0], b[1:]
    length, b = TAG_Int(b)
    values = []
    for _ in range(length):
        if tag_type in (9, 10):
            value, b = tags[tag_type](b, use_binary=use_binary)
        else:
            value, b = tags[tag_type](b)
        values.append(value.decode('utf-8')
                      if isinstance(value, bytes) else value)
    return values, b


def TAG_Compound(b, use_binary=False):
    output = {}
    value = True
    while b:
        tag_type, b = TAG_byte(b)
        if tag_type == 0:
            break
        else:
            tag_name, b = TAG_String(b)
            if tag_type in (9, 10):
                value, b = tags[tag_type](b, use_binary=use_binary)
            else:
                value, b = tags[tag_type](b)
            if not use_binary:
                tag_name = tag_name.decode('utf-8')
            output[tag_name] = value.decode(
                'utf-8') if isinstance(value, bytes) else value
    return output, b


def TAG_Int_Array(b):
    pass


def TAG_Long_Array(b):
    pass


tags = (
    TAG_End,
    TAG_byte,
    TAG_Short,
    TAG_Int,
    TAG_Long,
    TAG_Float,
    TAG_Double,
    TAG_Byte_Array,
    TAG_String,
    TAG_List,
    TAG_Compound,
    TAG_Int_Array,
    TAG_Long_Array,
)


def decode_item(nbt):
    nbt = gzip.decompress(base64.b64decode(nbt))
    data = TAG_Compound(nbt)[0]

    return data


class Item:
    def __init__(self, data):

        self.count = data.get("Count", 1)

        tag = data.get("tag", {})
        display = tag.get("display", {})
        item_lore = display.get("Lore", [])
        item_name = display.get("Name", "")

        self.lore = []
        lore = [item_name, *item_lore]
        for line in lore:
            line = line.replace("§", "&")
            self.lore.append(line)

        attributes = tag.get("ExtraAttributes", {})
        self.hot_potato_count = attributes.get("hot_potato_count", 0)
        self.reforge = attributes.get("modifier", "")
        self.stars = attributes.get("upgrade_level", 0)
        self._id = attributes.get("id", "")
        self.enchantments = attributes.get("enchantments", {})
        self.item_uuid = attributes.get("uuid", "")

    def render(self):
        return render(self.lore)


class Pet:
    def __init__(self, data):
        self.uuid = data.get("uuid", "")
        self.type = data.get("type", "")
        self.exp = data.get("exp", 0)
        self.active = data.get("active", False)
        self.tier = data.get("tier", 0)

        self.held_item = data.get("heldItem", "")
        if self.held_item in rarity_upgrading_pet_items:
            current_tier = pet_tiers.index(self.tier)
            if current_tier == len(pet_tiers)-1:
                self.tier = pet_tiers[current_tier]
            else:
                self.tier = pet_tiers[current_tier+1]

        self.candy_used = data.get("candyUsed", 0)
        self.skin = data.get("skin", "")

        self.max_level = 100
        if self.type in special_pet_levels:
            self.max_level = special_pet_levels[self.type]

        self.calculate_level()

    def calculate_level(self):

        if self.type == "BINGO":
            pet_offset = 0
        else:
            pet_offset = rarity_offset[self.tier]

        new_pet_levels = pet_levels[pet_offset:]
        new_pet_levels = new_pet_levels[:self.max_level-1]

        total_pet_xp = 0

        for i in new_pet_levels:
            total_pet_xp += i
            if total_pet_xp >= self.exp:
                level = new_pet_levels.index(i)+1
                break
        else:
            level = 100
            if self.type in special_pet_levels:
                level = special_pet_levels[self.type]

        self.level = level
        self.max_xp = sum(new_pet_levels)


class Profile:
    def __init__(self, profile_data, cute_name, uuid, api_key):
        self.profile_data_raw = profile_data
        self.cute_name = cute_name
        self.profile_id = None
        self.uuid = uuid
        self.networth_data = None
        self.bank_balance = 0
        self.museum_data = 0
        self.api_key = api_key

        for profile in profile_data["profiles"]:
            if profile["cute_name"] == cute_name:
                banking = profile.get("banking", {})
                self.bank_balance = banking.get("balance", 0)
                self.profile_data_raw = profile
                self.profile_id = profile["profile_id"]

                if uuid in profile["members"]:
                    self.profile_data_user = profile["members"][uuid]
                    break

                else:
                    raise SkyHelperNetworthException("User not in Profile")

        else:
            raise SkyHelperNetworthException("Profile not found")

        self.collections = self.profile_data_user.get("collection", {})

        self.pets = []
        pet_data = self.profile_data_user.get("pets_data", [])
        for pet in pet_data.get("pets", []):
            self.pets.append(Pet(pet))

        if self.profile_data_user.get("rift", {}).get("dead_cats", {}).get("montezuma"):
            self.pets.append(
                Pet(self.profile_data_user["rift"]["dead_cats"]["montezuma"]))

        inventory = self.profile_data_user.get("inventory", {})

        inventory_contents = inventory.get("inv_contents", {})
        inventory_data = inventory_contents.get("data", "")
        inventory_items = decode_item(inventory_data)[""]["i"]
        self.inventory = [Item(item) for item in inventory_items if item]

        enderchest_contents = inventory.get("ender_chest_contents", {})
        enderchest_data = enderchest_contents.get("data", "")
        enderchest_items = decode_item(enderchest_data)
        self.enderchest = [Item(item) for item in enderchest_items if item]

        armor = inventory.get("inv_armor", {})
        armor_data = armor.get("data", "")
        armor_items = decode_item(armor_data)[""]["i"]
        self.armor = [Item(item) for item in armor_items if item]

        wardrobe = inventory.get("wardrobe_contents", {})
        wardrobe_data = wardrobe.get("data", "")
        wardrobe_items = decode_item(wardrobe_data)[""]["i"]
        self.wardrobe = [Item(item) for item in wardrobe_items if item]

        equipment = inventory.get("equipment_contents", {})
        equipment_data = equipment.get("data", "")
        equipment_items = decode_item(equipment_data)[""]["i"]
        self.equipment = [Item(item) for item in equipment_items if item]

        persoal_vault = inventory.get("personal_vault_contents", {})
        personal_vault_data = persoal_vault.get("data", "")
        personal_vault_items = decode_item(personal_vault_data)[""]["i"]
        self.personal_vault = [Item(item)
                               for item in personal_vault_items if item]

        bags = inventory.get("bag_contents", {})

        potion_bag = bags.get("potion_bag", {})
        potion_bag_data = potion_bag.get("data", "")
        potion_bag_items = decode_item(potion_bag_data)[""]["i"]
        self.potion_bag = [Item(item) for item in potion_bag_items if item]

        talisman_bag = bags.get("talisman_bag", {})
        talisman_bag_data = talisman_bag.get("data", "")
        talisman_bag_items = decode_item(talisman_bag_data)[""]["i"]
        self.talisman_bag = [Item(item) for item in talisman_bag_items if item]

        fishing_bag = bags.get("fishing_bag", {})
        fishing_bag_data = fishing_bag.get("data", "")
        fishing_bag_items = decode_item(fishing_bag_data)[""]["i"]
        self.fishing_bag = [Item(item) for item in fishing_bag_items if item]

        quiver = bags.get("quiver", {})
        quiver_data = quiver.get("data", "")
        quiver_items = decode_item(quiver_data)[""]["i"]
        self.quiver = [Item(item) for item in quiver_items if item]

        asyncio.run(self.get_museum())
        asyncio.run(self.get_networth())
        self.get_dungeon_stats()
        self.get_slayer_stats()
        self.get_skill_stats()

    async def get_museum(self):
        if self.museum_data is None:
            url = f"https://api.hypixel.net/v2/skyblock/museum?key={self.api_key}&profile={self.profile_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    self.museum_data = data["members"][self.uuid]

    async def get_networth(self):
        if self.networth_data is None:
            url = "https://nw-api.noms.tech/networth"
            body = {
                "profile": self.profile_data_user,
                "bank": self.bank_balance,
                "museumData": self.museum_data
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=body) as response:
                    data = await response.json()
                    self.networth_data = data

    def get_dungeon_stats(self):

        experience = self.profile_data_user.get("dungeons", {}).get(
            "dungeon_types", {}).get("catacombs", {}).get("experience", 0)
        level = get_cata_lvl(experience)

        classes = [
            "healer",
            "mage",
            "berserk",
            "archer",
            "tank"
        ]

        class_data = {_class: {} for _class in classes}

        for d_class in classes:
            d_class_data = self.profile_data_user.get("dungeons", {}).get(
                "player_classes", {}).get(d_class, {})

            class_xp = d_class_data.get("experience", 0)

            class_data[d_class]["experience"] = class_xp
            class_data[d_class]["level"] = get_cata_lvl(class_xp)

        dungeon_data = {
            "experience": experience,
            "level": level,
            "classes": class_data,
            "raw": self.profile_data_user.get("dungeons", {})
        }
        self.dungeon_data = dungeon_data
        return

    def get_slayer_stats(self):
        slayers = ["zombie", "spider", "wolf", "enderman", "blaze", "vampire"]
        slayer_data = {slayer: {} for slayer in slayers}

        for slayer in slayers:
            _slayer = self.profile_data_user.get(
                "slayer_bosses", {}).get(slayer, {})
            experience = _slayer.get("xp", 0)
            level = get_slayer_level(slayer, experience)
            slayer_data[slayer]["experience"] = experience
            slayer_data[slayer]["level"] = level

        slayer_data["raw"] = self.profile_data_user.get("slayer_bosses", {})

        self.slayer_data = slayer_data
        return

    def get_skill_stats(self):
        skills = self.profile_data_user.get("player_data", {}).get("experience", {})
        skill_data = {}
        for skill in skills:
            formatted_skill_string = skill.replace("SKILL_", "").lower()
            exp = skills[skill]
            level = get_skill_lvl(formatted_skill_string, exp)
            skill_data[formatted_skill_string] = {
                "experience": exp,
                "level": level
            }

        self.skill_data = skill_data
        return
    

class SkyblockParser:
    """
    Use raw Hypixel API Data
    """

    def __init__(self, data, uuid, api_key):
        self.profiles = data
        self.uuid = uuid
        self.api_key = api_key
        if data.get("success") is False:
            reason = data.get("cause")
            raise SkyHelperNetworthException(reason)

    def select_profile(self, cute_name):
        return Profile(self.profiles, cute_name, self.uuid, self.api_key)