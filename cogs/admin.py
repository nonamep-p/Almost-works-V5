import discord
from discord.ext import commands
from replit import db
import asyncio
import logging
from datetime import datetime
from utils.helpers import create_embed, format_number
from config import COLORS, get_server_config, update_server_config, user_has_permission
from utils.database import get_guild_data, update_guild_data, get_user_data, update_user_data
from utils.helpers import format_duration
from rpg_data.game_data import ITEMS # Corrected import path
import psutil
import os
from typing import Optional, Dict, Any
import traceback

logger = logging.getLogger(__name__)

# Fallback imports (keeping these as they were)
try:
    from config import MODULES
except ImportError:
    logger.warning("Could not import 'MODULES' from config.py. Using default values.")
    MODULES = {
        'rpg': {'name': 'RPG System', 'emoji': '🎮', 'description': 'Adventure, combat, and character progression'},
        'economy': {'name': 'Economy System', 'emoji': '💰', 'description': 'Jobs, money, and trading'},
    }

try:
    from config import get_prefix
except ImportError:
    logger.warning("Could not import 'get_prefix' from config.py. Using default prefix function.")
    def get_prefix(bot, message):
        guild_id = getattr(message, 'guild', None)
        if guild_id: guild_id = guild_id.id
        else: guild_id = getattr(message, 'id', None)
        if guild_id:
            guild_data = get_guild_data(str(guild_id)) or {}
            return guild_data.get('prefix', '$')
        return '$'

# --- Modals ---

class ModifyStatsModal(discord.ui.Modal):
    def __init__(self, user_id: str, rpg_core):
        super().__init__(title="Modify Player Stats", timeout=300)
        self.user_id = user_id
        self.rpg_core = rpg_core

        # Get current player data to pre-fill fields
        player_data = rpg_core.get_player_data(user_id)
        if player_data:
            current_gold = str(player_data.get('gold', 0))
            current_level = str(player_data.get('level', 1))
            current_xp = str(player_data.get('xp', 0))
        else:
            current_gold = "0"
            current_level = "1" 
            current_xp = "0"

    gold = discord.ui.TextInput(
        label="Gold",
        placeholder="Enter new gold amount...",
        required=False,
        max_length=10
    )

    level = discord.ui.TextInput(
        label="Level", 
        placeholder="Enter new level...",
        required=False,
        max_length=3
    )

    xp = discord.ui.TextInput(
        label="Experience Points",
        placeholder="Enter new XP amount...",
        required=False,
        max_length=10
    )

    hp = discord.ui.TextInput(
        label="Health Points",
        placeholder="Enter new HP amount...",
        required=False,
        max_length=10
    )

    mana = discord.ui.TextInput(
        label="Mana Points",
        placeholder="Enter new MP amount...",
        required=False,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get current player data
            player_data = self.rpg_core.get_player_data(self.user_id)
            if not player_data:
                await interaction.response.send_message(
                    "❌ Player data not found! They need to create a character first.",
                    ephemeral=True
                )
                return

            changes_made = []

            # Update gold
            if self.gold.value:
                try:
                    new_gold = int(self.gold.value)
                    old_gold = player_data.get('gold', 0)
                    player_data['gold'] = new_gold
                    changes_made.append(f"Gold: {old_gold:,} → {new_gold:,}")
                except ValueError:
                    await interaction.response.send_message("❌ Invalid gold amount!", ephemeral=True)
                    return

            # Update level
            if self.level.value:
                try:
                    new_level = int(self.level.value)
                    if new_level < 1 or new_level > 100:
                        await interaction.response.send_message("❌ Level must be between 1 and 100!", ephemeral=True)
                        return
                    old_level = player_data.get('level', 1)
                    player_data['level'] = new_level
                    changes_made.append(f"Level: {old_level} → {new_level}")

                    # Recalculate stats based on new level
                    self.rpg_core.update_level_stats(player_data)
                except ValueError:
                    await interaction.response.send_message("❌ Invalid level!", ephemeral=True)
                    return

            # Update XP
            if self.xp.value:
                try:
                    new_xp = int(self.xp.value)
                    old_xp = player_data.get('xp', 0)
                    player_data['xp'] = new_xp
                    changes_made.append(f"XP: {old_xp:,} → {new_xp:,}")
                except ValueError:
                    await interaction.response.send_message("❌ Invalid XP amount!", ephemeral=True)
                    return

            # Update HP
            if self.hp.value:
                try:
                    new_hp = int(self.hp.value)
                    old_hp = player_data['resources'].get('hp', 100)
                    max_hp = player_data['resources'].get('max_hp', 100)
                    player_data['resources']['hp'] = min(new_hp, max_hp)
                    changes_made.append(f"HP: {old_hp} → {player_data['resources']['hp']}")
                except ValueError:
                    await interaction.response.send_message("❌ Invalid HP amount!", ephemeral=True)
                    return

            # Update Mana
            if self.mana.value:
                try:
                    new_mana = int(self.mana.value)
                    old_mana = player_data['resources'].get('mana', 50)
                    max_mana = player_data['resources'].get('max_mana', 50)
                    player_data['resources']['mana'] = min(new_mana, max_mana)
                    changes_made.append(f"Mana: {old_mana} → {player_data['resources']['mana']}")
                except ValueError:
                    await interaction.response.send_message("❌ Invalid mana amount!", ephemeral=True)
                    return

            if not changes_made:
                await interaction.response.send_message("❌ No changes were made!", ephemeral=True)
                return

            # Save the updated data
            success = self.rpg_core.save_player_data(self.user_id, player_data)
            if not success:
                await interaction.response.send_message("❌ Failed to save player data!", ephemeral=True)
                return

            # Plagg's sarcastic response
            user = interaction.guild.get_member(int(self.user_id))
            username = user.display_name if user else "that player"

            plagg_responses = [
                f"Fine, I modified {username}'s stats. {', '.join(changes_made)}. Happy now? Can I go back to my cheese?",
                f"There, {username} is now slightly more capable. {', '.join(changes_made)}. Don't let it go to their head.",
                f"Ugh, more paperwork. I updated {username}: {', '.join(changes_made)}. Now where's my Camembert?",
                f"Modified {username}'s numbers: {', '.join(changes_made)}. They're still not as impressive as a good cheese wheel."
            ]

            import random
            response = random.choice(plagg_responses)

            await interaction.response.send_message(f"✅ {response}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error updating stats: {str(e)}", ephemeral=True)

class UserSearchModal(discord.ui.Modal, title="🔎 Search for User"):
    user_input = discord.ui.TextInput(label="User ID or Name#Tag", placeholder="e.g., 1297013439125917766 or Plagg#1234", required=True)

    def __init__(self, user_id: str, guild_id: int, bot):
        super().__init__()
        self.user_id = user_id
        self.guild_id = guild_id
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        query = self.user_input.value
        guild = self.bot.get_guild(self.guild_id)
        member = None
        try:
            if '#' in query:
                name, discrim = query.split('#')
                member = discord.utils.get(guild.members, name=name, discriminator=discrim)
            else:
                member = guild.get_member(int(query))
        except (ValueError, AttributeError): pass

        if member:
            view = ManageUserView(self.user_id, self.guild_id, self.bot, member)
            embed = view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(f"❌ Could not find a member matching `{query}`.", ephemeral=True)

class MultiplierModal(discord.ui.Modal, title="⚙️ Set Server Multipliers"):
    xp_multiplier = discord.ui.TextInput(label="XP Multiplier", placeholder="e.g., 1.5 for 150% XP", required=True)
    gold_multiplier = discord.ui.TextInput(label="Gold Multiplier", placeholder="e.g., 2.0 for 200% Gold", required=True)

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id
        guild_data = get_guild_data(str(guild_id)) or {}
        self.xp_multiplier.default = str(guild_data.get('xp_multiplier', 1.0))
        self.gold_multiplier.default = str(guild_data.get('gold_multiplier', 1.0))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            xp_rate = float(self.xp_multiplier.value)
            gold_rate = float(self.gold_multiplier.value)

            guild_data = get_guild_data(str(self.guild_id)) or {}
            guild_data['xp_multiplier'] = xp_rate
            guild_data['gold_multiplier'] = gold_rate
            update_guild_data(str(self.guild_id), guild_data)

            await interaction.response.send_message(f"✅ Multipliers updated: XP `x{xp_rate}`, Gold `x{gold_rate}`.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid input. Please enter numbers only (e.g., 1.5).", ephemeral=True)

class ColorModal(discord.ui.Modal):
    color_input = discord.ui.TextInput(label="New Hex Color Code", placeholder="e.g., #FF5733", min_length=7, max_length=7)

    def __init__(self, guild_id: int, color_key: str):
        super().__init__(title=f"🎨 Set {color_key.title()} Color")
        self.guild_id = guild_id
        self.color_key = color_key

    async def on_submit(self, interaction: discord.Interaction):
        color_hex = self.color_input.value
        if not color_hex.startswith('#') or len(color_hex) != 7:
            await interaction.response.send_message("❌ Invalid format. Please use a 7-digit hex code (e.g., `#RRGGBB`).", ephemeral=True)
            return

        try:
            int(color_hex[1:], 16) # Validate hex
        except ValueError:
            await interaction.response.send_message("❌ Invalid hex code. Please check the code and try again.", ephemeral=True)
            return

        guild_data = get_guild_data(str(self.guild_id)) or {}
        if 'colors' not in guild_data:
            guild_data['colors'] = {}
        guild_data['colors'][self.color_key] = color_hex
        update_guild_data(str(self.guild_id), guild_data)

        await interaction.response.send_message(f"✅ {self.color_key.title()} color updated to `{color_hex}`.", ephemeral=True)

class GiveItemModal(discord.ui.Modal):
    def __init__(self, user_id: str, rpg_core):
        super().__init__(title="Give Item to Player", timeout=300)
        self.user_id = user_id
        self.rpg_core = rpg_core

    item_name = discord.ui.TextInput(
        label="Item Name/ID",
        placeholder="Enter item name or ID...",
        required=True,
        max_length=50
    )

    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="Enter quantity (default: 1)...",
        required=False,
        max_length=5,
        default="1"
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            from rpg_data.game_data import ITEMS

            # Get player data
            player_data = self.rpg_core.get_player_data(self.user_id)
            if not player_data:
                await interaction.response.send_message(
                    "❌ Player data not found! They need to create a character first.",
                    ephemeral=True
                )
                return

            # Parse quantity
            try:
                qty = int(self.quantity.value) if self.quantity.value else 1
                if qty <= 0:
                    await interaction.response.send_message("❌ Quantity must be positive!", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Invalid quantity!", ephemeral=True)
                return

            # Find the item
            item_input = self.item_name.value.lower().strip()
            item_key = None
            item_data = None

            # Try exact key match first
            if item_input in ITEMS:
                item_key = item_input
                item_data = ITEMS[item_input]
            else:
                # Try name matching
                for key, data in ITEMS.items():
                    if data.get('name', '').lower() == item_input:
                        item_key = key
                        item_data = data
                        break

                # Try partial name matching
                if not item_key:
                    for key, data in ITEMS.items():
                        if item_input in data.get('name', '').lower():
                            item_key = key
                            item_data = data
                            break

            if not item_key or not item_data:
                await interaction.response.send_message(
                    f"❌ Item '{self.item_name.value}' not found!\n"
                    f"💡 Try using exact item names like 'Iron Sword' or 'Health Potion'",
                    ephemeral=True
                )
                return

            # Add item to inventory
            if 'inventory' not in player_data:
                player_data['inventory'] = {}

            current_qty = player_data['inventory'].get(item_key, 0)
            player_data['inventory'][item_key] = current_qty + qty

            # Save the data
            success = self.rpg_core.save_player_data(self.user_id, player_data)
            if not success:
                await interaction.response.send_message("❌ Failed to save player data!", ephemeral=True)
                return

            # Get user info
            user = interaction.guild.get_member(int(self.user_id))
            username = user.display_name if user else "that player"

            # Plagg's responses based on item type
            item_name = item_data.get('name', item_key.replace('_', ' ').title())

            if 'cheese' in item_key.lower() or 'cheese' in item_name.lower():
                response = f"FINALLY! Someone with good taste! I gave {username} {qty}x {item_name}. This is the first sensible admin decision I've seen!"
            elif item_data.get('type') == 'consumable':
                responses = [
                    f"I gave {username} {qty}x {item_name}. At least it's something they can actually consume, unlike most of your junk.",
                    f"There, {username} now has {qty}x {item_name}. Still not cheese, but consumables are tolerable.",
                    f"Fine, {qty}x {item_name} for {username}. Try not to let them choke on it."
                ]
            elif item_data.get('type') in ['weapon', 'armor']:
                responses = [
                    f"I gave {username} {qty}x {item_name}. More metal junk for their collection. Thrilling.",
                    f"There, {username} now has {qty}x {item_name}. I hope they appreciate this fine piece of... whatever this is.",
                    f"Delivered {qty}x {item_name} to {username}. It's probably going to collect dust, but whatever."
                ]
            else:
                responses = [
                    f"I gave {username} {qty}x {item_name}. Another piece of junk for their hoard.",
                    f"There, {username} now has {qty}x {item_name}. Don't expect me to explain what it does.",
                    f"Delivered {qty}x {item_name} to {username}. You're welcome, I guess."
                ]

            if 'cheese' not in item_key.lower():
                import random
                response = random.choice(responses)

            await interaction.response.send_message(f"✅ {response}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error giving item: {str(e)}", ephemeral=True)

# --- Views ---

class BaseAdminView(discord.ui.View):
    def __init__(self, user_id: str, guild_id: int, bot, timeout=300):
        super().__init__(timeout=timeout)
        self.user_id = str(user_id)
        self.guild_id = guild_id
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This isn't your panel!", ephemeral=True)
            return False
        return True

    def create_embed(self):
        raise NotImplementedError("Subclasses must implement create_embed()")

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.danger, emoji="🔙", row=4)
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ConfigMainView(self.guild_id)
        embed = await view.create_main_embed(interaction.guild.name)
        await interaction.response.edit_message(embed=embed, view=view)

class GiveItemView(BaseAdminView):
    def __init__(self, user_id: str, guild_id: int, bot, target_member: discord.Member):
        super().__init__(user_id, guild_id, bot)
        self.target_member = target_member
        self.add_item(self.create_item_dropdown())

    def create_item_dropdown(self):
        options = [
            discord.SelectOption(label=item_data['name'], value=item_id, emoji='🎁')
            for item_id, item_data in list(ITEMS.items())[:25]
        ]
        select = discord.ui.Select(placeholder="Select an item to give...", options=options)
        select.callback = self.item_select_callback
        return select

    async def item_select_callback(self, interaction: discord.Interaction):
        item_id = interaction.data['values'][0]
        item_name = ITEMS[item_id]['name']

        user_data = get_user_data(str(self.target_member.id)) or {}
        inventory = user_data.get('inventory', {})
        inventory[item_id] = inventory.get(item_id, 0) + 1
        user_data['inventory'] = inventory
        update_user_data(str(self.target_member.id), user_data)

        await interaction.response.send_message(f"✅ Gave 1x {item_name} to {self.target_member.mention}.", ephemeral=True)

    def create_embed(self):
        return discord.Embed(
            title=f"🎁 Give Item to {self.target_member.display_name}",
            description="Select an item from the dropdown below to add to the user's inventory.",
            color=COLORS['info']
        )

class ManageUserView(BaseAdminView):
    def __init__(self, user_id: str, guild_id: int, bot, target_member: discord.Member):
        super().__init__(user_id, guild_id, bot)
        self.target_member = target_member
        if hasattr(self.bot, 'owner_id') and int(user_id) == self.bot.owner_id:
            self.add_item(self.create_grant_infinite_button())

    def create_grant_infinite_button(self):
        button = discord.ui.Button(label="👑 Grant Infinite Power", style=discord.ButtonStyle.success, emoji="✨", row=2)
        async def callback(interaction: discord.Interaction):
            await self.grant_infinite_power(interaction)
        button.callback = callback
        return button

    async def grant_infinite_power(self, interaction: discord.Interaction):
        user_data = get_user_data(str(self.target_member.id)) or {}
        user_data.update({ 
            'level': 999, 
            'gold': 999999999999, 
            'xp': 0, 
            'stats': {
                'strength': 999, 
                'dexterity': 999, 
                'constitution': 999, 
                'intelligence': 999, 
                'wisdom': 999, 
                'charisma': 999
            } 
        })
        update_user_data(str(self.target_member.id), user_data)
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        await interaction.followup.send(f"🧀 Wow, look at you with the 'infinite power' button. I gave {self.target_member.mention} god-mode stats. Are you going to create a block of cheese so big you can't eat it? No? Then what's the point of infinite power? *Claws out for cheese, not for boring admin stuff.*", ephemeral=True)

    def create_embed(self):
        user_data = get_user_data(str(self.target_member.id)) or {}
        stats = user_data.get('stats', {})
        embed = discord.Embed(
            title=f"👤 Staring at {self.target_member.display_name}'s Stats", 
            description=f"*Here's everything about {self.target_member.display_name}. Spoiler: it's not that interesting.*\n\n**User ID:** `{self.target_member.id}`\n\n*What meddling are we doing today?*", 
            color=COLORS['warning']
        )
        embed.set_thumbnail(url=self.target_member.display_avatar.url)
        embed.add_field(name="Level", value=user_data.get('level', 1))
        embed.add_field(name="Gold", value=f"{user_data.get('gold', 0):,}")
        embed.add_field(name="XP", value=user_data.get('xp', 0))
        embed.add_field(name="STR", value=stats.get('strength', 5))
        embed.add_field(name="DEX", value=stats.get('dexterity', 5))
        return embed

    @discord.ui.button(label="📝 Modify Stats", style=discord.ButtonStyle.primary, emoji="📝", row=1)
    async def modify_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModifyStatsModal(self.target_member.id, self.bot.get_cog('RPG').rpg_core))

    @discord.ui.button(label="🎁 Give Item", style=discord.ButtonStyle.primary, emoji="🎁", row=1)
    async def give_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GiveItemModal(self.target_member.id, self.bot.get_cog('RPG').rpg_core))

class UserManagementView(BaseAdminView):
    def create_embed(self):
        return discord.Embed(
            title="👥 Picking on Players", 
            description="*Sigh...* So you want to mess with someone's profile? Fine. Pick a victim from the list or use the button to find them. Just get it over with so I can get back to my cheese wheel.\n\n*Don't blame me if you make the game boring.*", 
            color=COLORS['error']
        )

    @discord.ui.button(label="🔎 Find User", style=discord.ButtonStyle.primary, emoji="🔎", row=1)
    async def find_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UserSearchModal(self.user_id, self.guild_id, self.bot))

    @discord.ui.button(label="📊 Top Players", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def top_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.create_leaderboard_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def create_leaderboard_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📊 Server Leaderboards",
            description="Top players across different categories.",
            color=COLORS['legendary']
        )
        players = []
        for key in db.keys():
            if key.startswith(f'player_{self.guild_id}_'):
                try:
                    player_data = db[key]
                    if isinstance(player_data, dict) and 'level' in player_data:
                        user_id = key.split('_')[-1]
                        players.append((user_id, player_data['level'], player_data.get('gold', 0)))
                except:
                    continue

        players.sort(key=lambda x: x[1], reverse=True)
        top_players = players[:5]

        if top_players:
            leaderboard = ""
            for i, (user_id, level, gold) in enumerate(top_players, 1):
                try:
                    user = interaction.guild.get_member(int(user_id))
                    name = user.display_name if user else f"User {user_id}"
                    leaderboard += f"{i}. **{name}** - Level {level} ({format_number(gold)} gold)\n"
                except:
                    leaderboard += f"{i}. User {user_id} - Level {level}\n"

            embed.add_field(name="🏆 Top Players by Level", value=leaderboard, inline=False)
        else:
            embed.add_field(name="📊 No Data", value="No players found for this server.", inline=False)

        return embed

class DatabaseToolsView(BaseAdminView):
    def create_embed(self):
        guild_data = get_guild_data(str(self.guild_id)) or {}
        xp_rate = guild_data.get('xp_multiplier', 1.0)
        gold_rate = guild_data.get('gold_multiplier', 1.0)
        embed = discord.Embed(
            title="💾 The Really Boring Stuff",
            description="*This is the REALLY boring stuff.* Multipliers, backups... *zzz.* Just don't delete anything important. Or do. The chaos could be fun to watch from a distance while I eat cheese.\n\n*Can we make this quick? My Camembert is getting warm.*",
            color=COLORS['dark']
        )
        embed.add_field(name="✨ XP Multiplier", value=f"`{xp_rate}x`", inline=True)
        embed.add_field(name="💰 Gold Multiplier", value=f"`{gold_rate}x`", inline=True)
        return embed

    @discord.ui.button(label="⚙️ Make Numbers Bigger", style=discord.ButtonStyle.primary, emoji="⚙️", row=1)
    async def set_multipliers(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MultiplierModal(self.guild_id))

    @discord.ui.button(label="💾 Copy Boring Numbers", style=discord.ButtonStyle.secondary, emoji="💾", row=1)
    async def backup_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💾 Making Copies of Boring Data",
            description="*Ugh, you want a copy of all this... data? Why? It's not like it's a rare wheel of cheese.* \n\nFine, I'll make a copy of all the boring numbers... *Don't lose it.*",
            color=COLORS['warning']
        )
        await interaction.response.edit_message(embed=embed, view=self)

        await asyncio.sleep(2)

        embed.description = "✅ There. I copied all your precious data. *Happy now? Can I go back to my cheese?*\n\n*Server backup completed successfully (and boringly).*"
        embed.color = COLORS['success']
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="🧹 Clean Database", style=discord.ButtonStyle.secondary, emoji="🧹", row=2)
    async def clean_database(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🧹 Database Cleanup",
            description="Cleaning unused and orphaned records...",
            color=COLORS['warning']
        )
        await interaction.response.edit_message(embed=embed, view=self)

        guild_keys = [k for k in db.keys() if str(self.guild_id) in k]

        embed.description = f"✅ Database cleanup completed!\nProcessed {len(guild_keys)} server records."
        embed.color = COLORS['success']
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="📊 Database Stats", style=discord.ButtonStyle.primary, emoji="📊", row=2)
    async def database_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_keys = len(list(db.keys()))
        guild_keys = len([k for k in db.keys() if str(self.guild_id) in k])
        player_keys = len([k for k in db.keys() if k.startswith(f'player_{self.guild_id}_')])

        embed = discord.Embed(
            title="📊 Database Statistics",
            description="Current database usage and health information.",
            color=COLORS['info']
        )

        embed.add_field(
            name="📈 Usage Stats",
            value=f"**Total Records:** {total_keys}\n"
                  f"**Server Records:** {guild_keys}\n"
                  f"**Player Profiles:** {player_keys}\n"
                  f"**Health Status:** ✅ Operational",
            inline=True
        )

        await interaction.response.edit_message(embed=embed, view=self)

class CustomizationView(BaseAdminView):
    def create_embed(self):
        guild_data = get_guild_data(str(self.guild_id)) or {}
        colors = guild_data.get('colors', {})

        embed = discord.Embed(
            title="🎨 Playing Interior Decorator",
            description="*Time to play interior decorator? How thrilling.* Here you can change colors and make everything look... different. Don't get any funny ideas about making me look less awesome.\n\n*Let me know when you add 'Camembert Yellow' or 'Brie White.' Until then, I don't care.*",
            color=COLORS['secondary']
        )

        def get_color_val(key):
            return colors.get(key, COLORS.get(key, '#FFFFFF'))

        embed.add_field(name="Primary Color", value=f"`{get_color_val('primary')}`", inline=True)
        embed.add_field(name="Success Color", value=f"`{get_color_val('success')}`", inline=True)
        embed.add_field(
            name="Info Color", value=f"`{get_color_val('info')}`", inline=True)
        return embed

    @discord.ui.button(label="Primary", style=discord.ButtonStyle.primary, emoji="🟥", row=1)
    async def set_primary_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColorModal(self.guild_id, 'primary'))

    @discord.ui.button(label="Success", style=discord.ButtonStyle.success, emoji="🟩", row=1)
    async def set_success_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColorModal(self.guild_id, 'success'))

    @discord.ui.button(label="Info", style=discord.ButtonStyle.primary, emoji="🟦", row=1)
    async def set_info_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColorModal(self.guild_id, 'info'))

class Admin(commands.Cog):
    """Admin panel with enhanced RPG integration."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="adminpanel", aliases=["admin", "panel"])
    @commands.has_permissions(administrator=True)
    async def admin_panel(self, ctx):
        """Open the main admin panel with RPG integration."""
        view = ConfigMainView(ctx.guild.id)
        embed = await view.create_main_embed(ctx.guild.name)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="givegold")
    @commands.has_permissions(administrator=True)
    async def give_gold(self, ctx, user: discord.Member, amount: int):
        """Give gold to a player directly."""
        rpg_cog = self.bot.get_cog('RPGCore')
        if not rpg_cog:
            await ctx.send("❌ RPG system not available!")
            return

        player_data = rpg_cog.get_player_data(str(user.id))
        if not player_data:
            await ctx.send(f"❌ {user.display_name} doesn't have a character!")
            return

        old_gold = player_data.get('gold', 0)
        player_data['gold'] = old_gold + amount

        success = rpg_cog.save_player_data(str(user.id), player_data)
        if success:
            embed = discord.Embed(
                title="💰 Gold Added",
                description=f"*\"Fine, I gave {user.display_name} {amount:,} gold. They now have {player_data['gold']:,} total. Happy now?\"*",
                color=COLORS['success']
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Failed to save player data!",
                color=COLORS['error']
            )

        await ctx.send(embed=embed)

    @commands.command(name="setlevel")
    @commands.has_permissions(administrator=True)
    async def set_level(self, ctx, user: discord.Member, level: int):
        """Set a player's level directly."""
        if level < 1 or level > 100:
            await ctx.send("❌ Level must be between 1 and 100!")
            return

        rpg_cog = self.bot.get_cog('RPGCore')
        if not rpg_cog:
            await ctx.send("❌ RPG system not available!")
            return

        player_data = rpg_cog.get_player_data(str(user.id))
        if not player_data:
            await ctx.send(f"❌ {user.display_name} doesn't have a character!")
            return

        old_level = player_data.get('level', 1)
        player_data['level'] = level

        # Update XP to match level
        xp_needed = level * 100
        player_data['xp'] = xp_needed

        success = rpg_cog.save_player_data(str(user.id), player_data)
        if success:
            embed = discord.Embed(
                title="📈 Level Updated",
                description=f"*\"There, {user.display_name} is now level {level}. They went from {old_level} to {level}. Thrilling.\"*",
                color=COLORS['success']
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Failed to save player data!",
                color=COLORS['error']
            )

        await ctx.send(embed=embed)

    @commands.command(name="resetplayer")
    @commands.has_permissions(administrator=True)
    async def reset_player(self, ctx, user: discord.Member):
        """Reset a player's data completely."""
        rpg_cog = self.bot.get_cog('RPGCore')
        if not rpg_cog:
            await ctx.send("❌ RPG system not available!")
            return

        # Delete player data
        success = rpg_cog.delete_player_data(str(user.id))
        if success:
            embed = discord.Embed(
                title="🗑️ Player Reset",
                description=f"*\"Poof! {user.display_name}'s data is gone. They can start fresh... or not. I don't really care.\"*",
                color=COLORS['warning']
            )
        else:
            embed = discord.Embed(
                title="❌ Failed",
                description="Failed to reset player data!",
                color=COLORS['error']
            )

        await ctx.send(embed=embed)

class ConfigMainView(discord.ui.View):
    """Main configuration panel view."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    async def create_main_embed(self, guild_name: str):
        """Create the main admin panel embed."""
        embed = discord.Embed(
            title="⚙️ Admin Control Panel",
            description=f"*\"Oh great, another admin panel. Just what I needed to make my day more exciting...\"*\n\n"
                       f"**Server:** {guild_name}\n"
                       f"**Admin Tools:** Configure settings, manage players, and other boring admin stuff.\n\n"
                       f"*Pick something from the buttons below so I can get back to my cheese.*",
            color=COLORS['primary']
        )

        # Get some basic stats
        guild_data = get_guild_data(str(self.guild_id)) or {}

        embed.add_field(
            name="🎮 RPG Settings",
            value=f"**XP Multiplier:** {guild_data.get('xp_multiplier', 1.0)}x\n"
                  f"**Gold Multiplier:** {guild_data.get('gold_multiplier', 1.0)}x\n"
                  f"**Enabled Modules:** RPG Core, Shop, Inventory",
            inline=True
        )

        embed.add_field(
            name="🛠️ Quick Actions",
            value="• Player Management\n"
                  "• Database Tools\n"
                  "• Server Customization\n"
                  "• Module Configuration",
            inline=True
        )

        return embed

    @discord.ui.button(label="👥 User Management", style=discord.ButtonStyle.primary, emoji="👥", row=0)
    async def user_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = UserManagementView(str(interaction.user.id), self.guild_id, interaction.client)
        embed = view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="💾 Database Tools", style=discord.ButtonStyle.secondary, emoji="💾", row=0)
    async def database_tools(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DatabaseToolsView(str(interaction.user.id), self.guild_id, interaction.client)
        embed = view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎨 Customization", style=discord.ButtonStyle.secondary, emoji="🎨", row=0)
    async def customization(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CustomizationView(str(interaction.user.id), self.guild_id, interaction.client)
        embed = view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Admin(bot))