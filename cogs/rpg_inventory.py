import discord
from discord.ext import commands
from replit import db
import math
from typing import Dict, Any, List, Optional
from datetime import datetime

from config import COLORS, is_module_enabled
from utils.helpers import create_embed, format_number
from rpg_data.game_data import ITEMS, RARITY_COLORS
import logging

logger = logging.getLogger(__name__)

# Plagg's inventory categories with his signature complaints
INVENTORY_CATEGORIES = {
    'all': {
        'name': '📦 All Items',
        'emoji': '📦',
        'description': "Everything you've hoarded. It's heavier than it looks and smells nothing like cheese."
    },
    'weapons': {
        'name': '⚔️ Weapons', 
        'emoji': '⚔️',
        'description': "Pointy things that aren't cheese knives. Disappointing, really."
    },
    'armor': {
        'name': '🛡️ Armor',
        'emoji': '🛡️', 
        'description': "Heavy metal that won't protect you from cheese withdrawal. Trust me on this."
    },
    'accessories': {
        'name': '💍 Accessories',
        'emoji': '💍',
        'description': "Shiny baubles. None of them smell like Camembert, which is their fatal flaw."
    },
    'artifacts': {
        'name': '✨ Kwami Artifacts',
        'emoji': '✨',
        'description': "Mystical items with actual power. Still not cheese though, so... mediocre."
    },
    'consumables': {
        'name': '🧪 Consumables',
        'emoji': '🧪',
        'description': "Things you can actually eat. Finally, some potential! Unless it's not cheese."
    },
    'materials': {
        'name': '🧱 Materials',
        'emoji': '🧱',
        'description': "Crafting junk. Can you craft cheese with these? Probably not. Waste of space."
    }
}

class InventoryView(discord.ui.View):
    """Plagg's revolutionary interactive inventory management system."""

    def __init__(self, user_id, rpg_core):
        super().__init__(timeout=300)
        self.user_id = str(user_id)
        self.rpg_core = rpg_core
        self.current_category = 'all'
        self.current_page = 0
        self.items_per_page = 8
        self.selected_item = None
        self.in_inspection_mode = False
        self.last_interaction = None
        self.cooldown_duration = 1  # 1 second cooldown

        # Load player data
        self.player_data = rpg_core.get_player_data(self.user_id)
        if not self.player_data:
            return

        # Initialize view
        self.update_components()

    def get_player_inventory(self):
        """Get the player's inventory with proper formatting."""
        return self.player_data.get('inventory', {})

    def get_equipped_items(self):
        """Get currently equipped items."""
        return self.player_data.get('equipment', {})

    def filter_items_by_category(self, category):
        """Filter inventory items by category."""
        inventory = self.get_player_inventory()
        if category == 'all':
            return inventory

        filtered = {}
        for item_key, quantity in inventory.items():
            item_data = ITEMS.get(item_key, {})
            item_type = item_data.get('type', 'materials').lower()

            # Map item types to categories
            category_mapping = {
                'weapons': ['weapon', 'sword', 'bow', 'staff', 'dagger', 'axe'],
                'armor': ['armor', 'helmet', 'chestplate', 'boots', 'shield'],
                'accessories': ['accessory', 'ring', 'necklace', 'charm', 'amulet'],
                'artifacts': ['artifact', 'kwami_artifact', 'miraculous'],
                'consumables': ['consumable', 'potion', 'food', 'cheese', 'elixir'],
                'materials': ['material', 'resource', 'component', 'ore', 'wood']
            }

            if category in category_mapping and item_type in category_mapping[category]:
                filtered[item_key] = quantity

        return filtered

    def get_paginated_items(self):
        """Get items for the current page."""
        filtered_items = self.filter_items_by_category(self.current_category)
        items_list = list(filtered_items.items())

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page

        return items_list[start_idx:end_idx], len(items_list)

    def create_main_inventory_embed(self):
        """Create the main inventory display embed."""
        category_info = INVENTORY_CATEGORIES[self.current_category]

        embed = discord.Embed(
            title="🎒 Your Bag of Mostly Useless Junk",
            description=f"*\"Ugh, fine. Here's all your stuff. It's heavy and none of it smells like Camembert. "
                       f"Try not to make a mess.\"*\n\n"
                       f"**📂 Current Category:** {category_info['name']}\n"
                       f"*{category_info['description']}*",
            color=COLORS['warning']
        )

        # Get paginated items
        page_items, total_items = self.get_paginated_items()

        if not page_items:
            embed.add_field(
                name="📭 Empty Category",
                value="*\"Well, would you look at that. Nothing here. Maybe try hoarding more stuff? "
                      "Or better yet, find some cheese.\"*",
                inline=False
            )
        else:
            # Calculate pagination info
            total_pages = math.ceil(total_items / self.items_per_page) if total_items > 0 else 1
            current_page_display = self.current_page + 1

            # Build item list with enhanced display
            item_list = ""
            for i, (item_key, quantity) in enumerate(page_items, 1):
                item_data = ITEMS.get(item_key, {
                    'name': item_key.replace('_', ' ').title(), 
                    'rarity': 'common',
                    'type': 'unknown'
                })

                rarity = item_data.get('rarity', 'common')
                rarity_emoji = self.get_rarity_emoji(rarity)
                item_name = item_data.get('name', item_key.replace('_', ' ').title())

                # Add quick stats preview
                stats_preview = []
                if item_data.get('attack'):
                    stats_preview.append(f"⚔️{item_data['attack']}")
                if item_data.get('defense'):
                    stats_preview.append(f"🛡️{item_data['defense']}")
                if item_data.get('heal_amount'):
                    stats_preview.append(f"❤️+{item_data['heal_amount']}")
                if item_data.get('mana_amount'):
                    stats_preview.append(f"💙+{item_data['mana_amount']}")

                stats_str = f" `({'/'.join(stats_preview)})`" if stats_preview else ""
                quantity_text = f" **x{quantity}**" if quantity > 1 else ""

                item_list += f"`{i}.` {rarity_emoji} **{item_name}**{stats_str}{quantity_text}\n"

            embed.add_field(
                name=f"📋 Items Page {current_page_display}/{total_pages}",
                value=item_list,
                inline=False
            )

            # Enhanced stats summary
            equipped = self.get_equipped_items()
            equipped_count = len([item for item in equipped.values() if item])
            total_value = self.calculate_inventory_value()

            embed.add_field(
                name="⚡ Inventory Stats",
                value=f"**📦 Total Items:** {sum(self.get_player_inventory().values())}\n"
                      f"**⚔️ Equipped:** {equipped_count}/4 slots\n"
                      f"**💰 Gold:** {format_number(self.player_data.get('gold', 0))}\n"
                      f"**💎 Est. Value:** {format_number(total_value)} gold",
                inline=True
            )

        embed.set_footer(text="💡 Use dropdowns to browse and buttons to interact | 🧀 Still no cheese in sight...")
        return embed

    def calculate_inventory_value(self):
        """Calculate total estimated value of inventory."""
        total = 0
        inventory = self.get_player_inventory()

        for item_key, quantity in inventory.items():
            item_data = ITEMS.get(item_key, {})
            price = item_data.get('price', 0)
            # Sell price is typically 60% of buy price
            sell_price = int(price * 0.6)
            total += sell_price * quantity

        return total

    def create_item_inspection_embed(self, item_key):
        """Create the detailed item inspection view."""
        item_data = ITEMS.get(item_key, {})
        inventory = self.get_player_inventory()
        quantity = inventory.get(item_key, 0)

        # Get item info
        item_name = item_data.get('name', item_key.replace('_', ' ').title())
        rarity = item_data.get('rarity', 'common')
        rarity_emoji = self.get_rarity_emoji(rarity)
        rarity_color = RARITY_COLORS.get(rarity, COLORS['secondary'])

        embed = discord.Embed(
            title=f"{rarity_emoji} {item_name}",
            description=item_data.get('description', '*No description available. Probably junk.*'),
            color=rarity_color
        )

        # Item type and basic info
        item_type = item_data.get('type', 'Unknown').title()

        embed.add_field(
            name="📋 Item Details",
            value=f"**Type:** {item_type}\n"
                  f"**Rarity:** {rarity.title()}\n"
                  f"**Owned:** {quantity}\n"
                  f"**Weight:** {item_data.get('weight', 1)} kg",
            inline=True
        )

        # Enhanced stats display
        stats_text = ""
        if item_data.get('attack'):
            stats_text += f"⚔️ **Attack:** +{item_data['attack']}\n"
        if item_data.get('defense'):
            stats_text += f"🛡️ **Defense:** +{item_data['defense']}\n"
        if item_data.get('hp'):
            stats_text += f"❤️ **HP Bonus:** +{item_data['hp']}\n"
        if item_data.get('mana'):
            stats_text += f"💙 **Mana Bonus:** +{item_data['mana']}\n"
        if item_data.get('heal_amount'):
            stats_text += f"💊 **Healing:** {item_data['heal_amount']} HP\n"
        if item_data.get('mana_amount'):
            stats_text += f"🔮 **Mana Restore:** {item_data['mana_amount']} MP\n"
        if item_data.get('critical_chance'):
            stats_text += f"💥 **Crit Chance:** +{item_data['critical_chance']}%\n"

        if stats_text:
            embed.add_field(name="📊 Stats & Effects", value=stats_text, inline=True)

        # Requirements
        requirements = []
        if item_data.get('level_required'):
            requirements.append(f"Level {item_data['level_required']}")
        if item_data.get('class_required'):
            requirements.append(f"{item_data['class_required'].title()} class")

        if requirements:
            embed.add_field(
                name="⚠️ Requirements", 
                value="\n".join(f"• {req}" for req in requirements),
                inline=True
            )

        # Special effects
        if item_data.get('effects'):
            effects_text = "\n".join(f"✨ {effect}" for effect in item_data['effects'])
            embed.add_field(name="🌟 Special Effects", value=effects_text, inline=False)

        # Set bonus info
        if item_data.get('set_bonus'):
            embed.add_field(
                name="🔮 Set Bonus", 
                value=item_data['set_bonus'],
                inline=False
            )

        # Plagg's enhanced commentary
        plagg_comments = self.get_enhanced_plagg_commentary(item_key, item_data)
        embed.add_field(
            name="🧀 Plagg's Professional Opinion",
            value=f"*\"{plagg_comments}\"*",
            inline=False
        )

        # Market value and trading info
        if item_data.get('price'):
            buy_price = item_data['price']
            sell_price = int(buy_price * 0.6)
            embed.add_field(
                name="💰 Market Value",
                value=f"**Shop Price:** {format_number(buy_price)} gold\n"
                      f"**Sell Price:** {format_number(sell_price)} gold\n"
                      f"**Total Value:** {format_number(sell_price * quantity)} gold",
                inline=True
            )

        embed.set_footer(text="💡 Use the buttons below to interact with this item")
        return embed

    def get_rarity_emoji(self, rarity):
        """Get emoji for item rarity."""
        rarity_emojis = {
            'common': '⚪',
            'uncommon': '🟢', 
            'rare': '🔵',
            'epic': '🟣',
            'legendary': '🟠',
            'mythical': '🔴',
            'divine': '⭐',
            'cosmic': '🌟',
            'plagg_cheese': '🧀'
        }
        return rarity_emojis.get(rarity.lower(), '⚪')

    def get_enhanced_plagg_commentary(self, item_key, item_data):
        """Generate Plagg's enhanced sarcastic commentary for items."""
        item_type = item_data.get('type', '').lower()
        rarity = item_data.get('rarity', '').lower()
        item_name = item_data.get('name', '').lower()

        # Special cheese detection
        if 'cheese' in item_key.lower() or 'cheese' in item_name or item_type == 'cheese':
            cheese_responses = [
                "NOW WE'RE TALKING! Finally, something worthwhile in this mess! This is the only item that actually matters!",
                "CHEESE! Oh sweet, beautiful, magnificent cheese! This makes all the other junk tolerable!",
                "Finally! An item with actual value! Everything else can disappear for all I care, but keep this cheese safe!",
                "This is what I'm talking about! Forget weapons, forget armor - cheese is the ultimate treasure!"
            ]
            import random
            return random.choice(cheese_responses)

        # Type-specific enhanced comments
        if item_type in ['weapon', 'sword', 'bow', 'dagger', 'axe']:
            weapon_responses = [
                "Wow, it's pointy. Groundbreaking. Can you use it to slice cheese? That's literally the only stat I care about.",
                "Another weapon. Because clearly, what this world needs is more ways to fight and less cheese to enjoy.",
                "Sharp and dangerous. Unlike cheese, which is soft, wonderful, and doesn't try to hurt anyone.",
                "I suppose it's decent for poking things. But can it poke holes in cheese for better aging? I doubt it.",
                "Metal stick goes stab. Very creative. Now if only someone made a weapon that shot cheese at enemies...",
                "This could probably cut through stone. But can it cut the perfect cheese slice? Priorities, people!"
            ]
        elif item_type in ['armor', 'helmet', 'chestplate', 'boots', 'shield']:
            armor_responses = [
                "This hunk of metal is supposed to protect you. A wheel of Camembert is bigger, tastier, and probably more protective.",
                "Heavy, uncomfortable, and definitely not cheese-scented. What's the point of protection if you can't enjoy cheese?",
                "Great, more armor. Because the real threat isn't cheese deprivation, apparently. News flash: it is.",
                "It might stop a sword, but it won't stop my complaints about the lack of cheese here.",
                "Protection from everything except the crushing disappointment of a cheese-less existence.",
                "This metal shell might keep you alive, but will you really be living without cheese? Think about it."
            ]
        elif item_type in ['potion', 'consumable', 'elixir']:
            if 'health' in item_key.lower() or 'heal' in item_name:
                consumable_responses = [
                    "Smells awful. If you're that hurt, maybe you should try fighting less and napping more. Also, more cheese.",
                    "Red liquid that supposedly heals you. I prefer the red wax on cheese wheels, personally.",
                    "Medicinal and boring. Where's the cheese-flavored healing potion? That would actually be useful.",
                    "Tastes like regret and poor life choices. Unlike cheese, which tastes like happiness."
                ]
            else:
                consumable_responses = [
                    "At least this one you can actually consume. Still not cheese though, so it's automatically inferior.",
                    "Consumable items are the only category with potential. Shame this isn't cheese-related.",
                    "You can eat this, which puts it above 90% of your other junk. But it's still not cheese.",
                    "Finally, something that goes in your mouth! Too bad it's not the creamy goodness of Camembert."
                ]
        elif rarity in ['legendary', 'mythical', 'divine', 'cosmic']:
            rare_responses = [
                "Ooh, fancy rarity. I bet it still doesn't taste as good as aged Camembert. Nothing does.",
                "Legendary, huh? The only true legend is the perfect cheese wheel. This is just shiny junk.",
                "Very impressive. Would be more impressive if it were cheese-related. Just saying.",
                "Mythical power, mundane flavor. That's my professional assessment as a cheese connoisseur.",
                "Divine rarity but earthly disappointment. At least divine cheese exists - it's called Roquefort.",
                "Cosmic power? Cool. Can it manifest cosmic cheese? No? Then what's the point?"
            ]
        elif item_type in ['accessory', 'ring', 'necklace', 'charm']:
            accessory_responses = [
                "Shiny trinket. Does it make you more attractive to cheese vendors? No? Then it's useless.",
                "Pretty bauble. Shame it's not cheese-shaped. Everything should be cheese-shaped.",
                "Fancy jewelry. I bet it doesn't even smell faintly of cheese. Disappointing design choice.",
                "Ornamental junk. At least it's small, so there's more room for cheese storage."
            ]
        else:
            generic_responses = [
                "More junk for your collection. When do we get to the cheese section? I'm still waiting.",
                "I'm sure this seemed important when you picked it up. Spoiler alert: it's not cheese, so it's not important.",
                "Another item that's definitely not cheese. Color me surprised. And disappointed. Mostly disappointed.",
                "This is taking up space that could be used for cheese storage. Priorities, people!",
                "Mildly interesting. Emphasis on 'mildly.' Unlike cheese, which is extremely interesting. Always.",
                "Generic item number 47. Still not cheese. My enthusiasm remains at absolute zero."
            ]

        # Select appropriate response list
        if item_type in ['weapon', 'sword', 'bow', 'dagger', 'axe']:
            responses = weapon_responses
        elif item_type in ['armor', 'helmet', 'chestplate', 'boots', 'shield']:
            responses = armor_responses
        elif item_type in ['potion', 'consumable', 'elixir']:
            responses = consumable_responses
        elif rarity in ['legendary', 'mythical', 'divine', 'cosmic']:
            responses = rare_responses
        elif item_type in ['accessory', 'ring', 'necklace', 'charm']:
            responses = accessory_responses
        else:
            responses = generic_responses

        import random
        return random.choice(responses)

    def update_components(self):
        """Update the view components based on current mode."""
        self.clear_items()

        if not self.in_inspection_mode:
            # Main inventory mode
            self.add_item(CategorySelect(self))

            # Only add item select if there are items
            page_items, total_items = self.get_paginated_items()
            if page_items:
                self.add_item(ItemSelect(self, page_items))

            # Pagination buttons
            if total_items > self.items_per_page:
                self.add_item(PreviousPageButton(self))
                self.add_item(NextPageButton(self))

            self.add_item(CloseInventoryButton(self))
        else:
            # Item inspection mode - enhanced action buttons
            item_data = ITEMS.get(self.selected_item, {})
            item_type = item_data.get('type', '').lower()

            # Equipment button for equippable items
            if item_type in ['weapon', 'armor', 'accessory', 'artifact']:
                self.add_item(EquipItemButton(self))
                self.add_item(CompareItemButton(self))

            # Use button for consumables
            if item_type in ['consumable', 'potion', 'food', 'cheese', 'elixir']:
                self.add_item(UseItemButton(self))

            # Enhanced action buttons
            self.add_item(SellItemButton(self))
            self.add_item(DropItemButton(self))
            self.add_item(BackToInventoryButton(self))

    def check_cooldown(self, interaction: discord.Interaction):
        """Check and update cooldown."""
        now = datetime.utcnow()
        if self.last_interaction is None or (now - self.last_interaction).total_seconds() >= self.cooldown_duration:
            self.last_interaction = now
            return True
        return False

class CategorySelect(discord.ui.Select):
    """Dropdown for selecting inventory categories."""

    def __init__(self, inventory_view):
        self.inventory_view = inventory_view

        options = []
        for cat_key, cat_data in INVENTORY_CATEGORIES.items():
            options.append(discord.SelectOption(
                label=cat_data['name'],
                value=cat_key,
                emoji=cat_data['emoji'],
                description=cat_data['description'][:100],
                default=(cat_key == inventory_view.current_category)
            ))

        super().__init__(
            placeholder="🧀 Select a category... *sigh*",
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        self.inventory_view.current_category = self.values[0]
        self.inventory_view.current_page = 0  # Reset to first page
        self.inventory_view.update_components()

        embed = self.inventory_view.create_main_inventory_embed()
        await interaction.response.edit_message(embed=embed, view=self.inventory_view)

class ItemSelect(discord.ui.Select):
    """Dropdown for selecting specific items."""

    def __init__(self, inventory_view, page_items):
        self.inventory_view = inventory_view

        options = []
        for i, (item_key, quantity) in enumerate(page_items):
            if len(options) >= 25:  # Discord limit
                break

            item_data = ITEMS.get(item_key, {'name': item_key.replace('_', ' ').title(), 'rarity': 'common'})
            item_name = item_data.get('name', item_key.replace('_', ' ').title())
            rarity = item_data.get('rarity', 'common')
            rarity_emoji = inventory_view.get_rarity_emoji(rarity)

            # Truncate name if too long
            display_name = item_name[:45] + "..." if len(item_name) > 45 else item_name
            quantity_text = f" (x{quantity})" if quantity > 1 else ""

            options.append(discord.SelectOption(
                label=f"{display_name}{quantity_text}",
                value=item_key,
                emoji=rarity_emoji,
                description=f"{rarity.title()} {item_data.get('type', 'Item').title()}"
            ))

        super().__init__(
            placeholder="🔍 Select an item to inspect...",
            options=options if options else [discord.SelectOption(label="No items", value="none")],
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        if self.values[0] == "none":
            await interaction.response.defer()
            return

        self.inventory_view.selected_item = self.values[0]
        self.inventory_view.in_inspection_mode = True
        self.inventory_view.update_components()

        embed = self.inventory_view.create_item_inspection_embed(self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.inventory_view)

class PreviousPageButton(discord.ui.Button):
    """Navigate to previous page."""

    def __init__(self, inventory_view):
        self.inventory_view = inventory_view
        super().__init__(
            label="Previous",
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            disabled=(inventory_view.current_page <= 0),
            row=2
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        self.inventory_view.current_page = max(0, self.inventory_view.current_page - 1)
        self.inventory_view.update_components()

        embed = self.inventory_view.create_main_inventory_embed()
        await interaction.response.edit_message(embed=embed, view=self.inventory_view)

class NextPageButton(discord.ui.Button):
    """Navigate to next page."""

    def __init__(self, inventory_view):
        self.inventory_view = inventory_view
        page_items, total_items = inventory_view.get_paginated_items()
        max_pages = math.ceil(total_items / inventory_view.items_per_page) if total_items > 0 else 1

        super().__init__(
            label="Next",
            emoji="➡️", 
            style=discord.ButtonStyle.secondary,
            disabled=(inventory_view.current_page >= max_pages - 1),
            row=2
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        page_items, total_items = self.inventory_view.get_paginated_items()
        max_pages = math.ceil(total_items / self.inventory_view.items_per_page) if total_items > 0 else 1

        self.inventory_view.current_page = min(max_pages - 1, self.inventory_view.current_page + 1)
        self.inventory_view.update_components()

        embed = self.inventory_view.create_main_inventory_embed()
        await interaction.response.edit_message(embed=embed, view=self.inventory_view)

class CloseInventoryButton(discord.ui.Button):
    """Close the inventory."""

    def __init__(self, inventory_view):
        super().__init__(
            label="Close",
            emoji="❌",
            style=discord.ButtonStyle.danger,
            row=2
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎒 Inventory Closed",
            description="*\"Finally! Now I can get back to important things. Like napping. And thinking about cheese.\"*",
            color=COLORS['success']
        )

        await interaction.response.edit_message(embed=embed, view=None)

class EquipItemButton(discord.ui.Button):
    """Equip the selected item."""

    def __init__(self, inventory_view):
        super().__init__(
            label="Equip",
            emoji="✅",
            style=discord.ButtonStyle.success,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        item_key = self.inventory_view.selected_item
        item_data = ITEMS.get(item_key, {})
        item_name = item_data.get('name', item_key.replace('_', ' ').title())

        # Get equipment slot
        item_type = item_data.get('type', '').lower()
        equipment_slots = {
            'weapon': 'weapon',
            'sword': 'weapon', 
            'bow': 'weapon',
            'staff': 'weapon',
            'dagger': 'weapon',
            'axe': 'weapon',
            'helmet': 'helmet',
            'chestplate': 'chestplate',
            'armor': 'chestplate',
            'shield': 'chestplate',
            'boots': 'boots',
            'accessory': 'accessory',
            'ring': 'ring',
            'necklace': 'necklace',
            'charm': 'accessory',
            'amulet': 'accessory',
            'artifact': 'artifact',
            'kwami_artifact': 'artifact'
        }

        slot = equipment_slots.get(item_type)
        if not slot:
            await interaction.response.send_message("This item cannot be equipped!", ephemeral=True)
            return

        # Handle equipment swap
        player_data = self.inventory_view.player_data
        equipment = player_data.get('equipment', {})
        inventory = player_data.get('inventory', {})

        # Remove from inventory
        if inventory.get(item_key, 0) > 1:
            inventory[item_key] -= 1
        else:
            inventory.pop(item_key, None)

        # Unequip current item if any
        old_item = equipment.get(slot)
        if old_item:
            inventory[old_item] = inventory.get(old_item, 0) + 1

        # Equip new item
        equipment[slot] = item_key

        # Save changes
        player_data['equipment'] = equipment
        player_data['inventory'] = inventory
        self.inventory_view.rpg_core.save_player_data(self.inventory_view.user_id, player_data)

        # Plagg's response
        plagg_responses = [
            f"Fine, I swapped it. You look slightly more ridiculous now, if that was even possible.",
            f"There, it's equipped. Happy? Can we please find some cheese now?",
            f"Congratulations, you're now wearing slightly different junk.",
            f"Equipped. Now you're 0.1% more likely to survive. Don't get cocky.",
        ]

        import random
        response = random.choice(plagg_responses)

        embed = discord.Embed(
            title="✅ Item Equipped!",
            description=f"*\"{response}\"*\n\n**{item_name}** has been equipped!",
            color=COLORS['success']
        )

        if old_item:
            old_item_data = ITEMS.get(old_item, {})
            old_name = old_item_data.get('name', old_item.replace('_', ' ').title())
            embed.add_field(
                name="🔄 Previous Item",
                value=f"**{old_name}** was returned to your inventory.",
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=None)

class UseItemButton(discord.ui.Button):
    """Use/consume the selected item."""

    def __init__(self, inventory_view):
        super().__init__(
            label="Use",
            emoji="🧪",
            style=discord.ButtonStyle.primary,
            row=0
        )
        self.inventory_view = inventory_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        # Anti-spam cooldown check
        if not self.inventory_view.check_cooldown(interaction):
            await interaction.response.send_message(
                "*\"Whoa, slow down there, hero. You're going to wear yourself out. Take a nap. Eat some cheese. The world can wait.\"*",
                ephemeral=True
            )
            return

        item_key = self.inventory_view.selected_item        
        item_data = ITEMS.get(item_key, {})
        item_name = item_data.get('name', item_key.replace('_', ' ').title())

        # Check if item exists in inventory
        player_data = self.inventory_view.player_data
        inventory = player_data.get('inventory', {})

        if inventory.get(item_key, 0) <= 0:
            await interaction.response.send_message("You don't have this item!", ephemeral=True)
            return

        # Process item effects
        effect_result = self.process_item_effect(item_key, item_data, player_data)

        # Remove item from inventory
        inventory = player_data.get('inventory', {})
        if inventory.get(item_key, 0) > 1:
            inventory[item_key] -= 1
        else:
            inventory.pop(item_key, None)

        player_data['inventory'] = inventory

        # Save changes
        self.inventory_view.rpg_core.save_player_data(self.inventory_view.user_id, player_data)

        embed = discord.Embed(
            title="🧪 Item Used!",
            description=f"**{item_name}** has been consumed!\n\n{effect_result}",
            color=COLORS['success']
        )

        await interaction.response.edit_message(embed=embed, view=None)

    def process_item_effect(self, item_key, item_data, player_data):
        """Process the effects of using an item."""
        effect_type = item_data.get('effect_type')
        resources = player_data.get('resources', {})

        if 'cheese' in item_key.lower():
            # Special cheese handling
            hp_heal = item_data.get('heal_amount', 50)
            current_hp = resources.get('hp', 100)
            max_hp = resources.get('max_hp', 100)
            actual_heal = min(hp_heal, max_hp - current_hp)
            resources['hp'] = min(max_hp, current_hp + actual_heal)
            player_data['resources'] = resources
            return f"*\"NOW WE'RE TALKING! That cheese was absolutely divine! +{actual_heal} HP restored!\"*"

        elif effect_type == 'heal' or item_data.get('heal_amount'):
            heal_amount = item_data.get('heal_amount', 25)
            current_hp = resources.get('hp', 100)
            max_hp = resources.get('max_hp', 100)
            actual_heal = min(heal_amount, max_hp - current_hp)
            resources['hp'] = min(max_hp, current_hp + actual_heal)
            player_data['resources'] = resources
            return f"*\"Tastes awful, but I guess it worked. +{actual_heal} HP restored.\"*"

        elif effect_type == 'mana' or item_data.get('mana_amount'):
            mana_amount = item_data.get('mana_amount', 20)
            current_mana = resources.get('mana', 50)
            max_mana = resources.get('max_mana', 50)
            actual_mana = min(mana_amount, max_mana - current_mana)
            resources['mana'] = min(max_mana, current_mana + actual_mana)
            player_data['resources'] = resources
            return f"*\"Magical and boring. +{actual_mana} Mana restored.\"*"

        elif effect_type == 'buff':
            # Handle temporary buffs (would need a buff system)
            return f"*\"I suppose you feel slightly more capable now. For a few minutes.\"*"

        else:
            return f"*\"You consumed it. Something probably happened. I wasn't paying attention.\"*"

class CompareItemButton(discord.ui.Button):
    """Compare item with currently equipped."""

    def __init__(self, inventory_view):
        super().__init__(
            label="Compare",
            emoji="⚖️",
            style=discord.ButtonStyle.secondary,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        item_key = self.inventory_view.selected_item
        item_data = ITEMS.get(item_key, {})
        item_name = item_data.get('name', item_key.replace('_', ' ').title())

        # Get equipment slot
        item_type = item_data.get('type', '').lower()
        equipment_slots = {
            'weapon': 'weapon',
            'sword': 'weapon',
            'dagger': 'weapon',
            'axe': 'weapon',
            'armor': 'chestplate',
            'helmet': 'helmet',
            'shield': 'chestplate',
            'boots': 'boots',
            'accessory': 'accessory',
            'ring': 'ring',
            'necklace': 'necklace',
            'charm': 'accessory',
            'amulet': 'accessory',
            'artifact': 'artifact',
            'kwami_artifact': 'artifact'
        }

        slot = equipment_slots.get(item_type)
        if not slot:
            await interaction.response.send_message("Cannot compare this item type!", ephemeral=True)
            return

        # Get currently equipped item
        equipment = self.inventory_view.player_data.get('equipment', {})
        equipped_key = equipment.get(slot)

        if not equipped_key:
            embed = discord.Embed(
                title="⚖️ Item Comparison",
                description=f"*\"There's nothing equipped in that slot to compare with. This {item_name} would be an upgrade by default.\"*",
                color=COLORS['info']
            )
            await interaction.response.edit_message(embed=embed, view=self.inventory_view)
            return

        # Create comparison embed
        equipped_data = ITEMS.get(equipped_key, {})
        equipped_name = equipped_data.get('name', equipped_key.replace('_', ' ').title())

        embed = discord.Embed(
            title="⚖️ Item Comparison",
            description=f"*\"Let's see... old junk vs new junk. Riveting.\"*",
            color=COLORS['info']
        )

        # Compare stats
        new_stats = item_data.get('stats', {})
        old_stats = equipped_data.get('stats', {})

        # Get all unique stat names
        all_stats = set(new_stats.keys()) | set(old_stats.keys())

        new_column = f"**{item_name}**\n"
        old_column = f"**{equipped_name}** (Current)\n"

        for stat in sorted(all_stats):
            new_value = new_stats.get(stat, 0)
            old_value = old_stats.get(stat, 0)

            stat_display = stat.replace('_', ' ').title()

            if new_value > old_value:
                new_column += f"✅ {stat_display}: {new_value} (+{new_value - old_value})\n"
                old_column += f"❌ {stat_display}: {old_value}\n"
            elif new_value < old_value:
                new_column += f"❌ {stat_display}: {new_value}\n"
                old_column += f"✅ {stat_display}: {old_value} (+{old_value - new_value})\n"
            else:
                new_column += f"⚪ {stat_display}: {new_value}\n"
                old_column += f"⚪ {stat_display}: {old_value}\n"

        embed.add_field(name="📊 New Item", value=new_column, inline=True)
        embed.add_field(name="📊 Equipped Item", value=old_column, inline=True)

        await interaction.response.edit_message(embed=embed, view=self.inventory_view)

class SellItemButton(discord.ui.Button):
    """Sell the selected item."""

    def __init__(self, inventory_view):
        item_data = ITEMS.get(inventory_view.selected_item, {})
        sell_price = item_data.get('sell_price', 10)

        super().__init__(
            label=f"Sell ({format_number(sell_price)} Gold)",
            emoji="💰",
            style=discord.ButtonStyle.danger,
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        # Create confirmation view
        confirm_view = SellConfirmationView(self.inventory_view, self.inventory_view.selected_item)

        item_data = ITEMS.get(self.inventory_view.selected_item, {})
        item_name = item_data.get('name', self.inventory_view.selected_item.replace('_', ' ').title())
        sell_price = item_data.get('sell_price', 10)

        embed = discord.Embed(
            title="💰 Confirm Sale",
            description=f"*\"You sure you want to get rid of this {item_name}? I mean, it's not cheese, so I don't really care, but...\"*\n\n"
                       f"**Item:** {item_name}\n"
                       f"**Sale Price:** {format_number(sell_price)} Gold\n\n"
                       f"Are you sure you want to sell this item?",
            color=COLORS['warning']
        )

        await interaction.response.edit_message(embed=embed, view=confirm_view)

class DropItemButton(discord.ui.Button):
    """Drop the selected item."""

    def __init__(self, inventory_view):
        super().__init__(
            label="Drop Item",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        # Create confirmation view
        confirm_view = DropConfirmationView(self.inventory_view, self.inventory_view.selected_item)

        item_data = ITEMS.get(self.inventory_view.selected_item, {})
        item_name = item_data.get('name', self.inventory_view.selected_item.replace('_', ' ').title())

        embed = discord.Embed(
            title="🗑️ Confirm Drop",
            description=f"*\"You really wanna just toss this {item_name} away? Hope you don't need it later...\"*\n\n"
                       f"**Item:** {item_name}\n\n"
                       f"Are you absolutely sure you want to drop this item?",
            color=COLORS['warning']
        )

        await interaction.response.edit_message(embed=embed, view=confirm_view)

class BackToInventoryButton(discord.ui.Button):
    """Return to main inventory view."""

    def __init__(self, inventory_view):
        super().__init__(
            label="Back to Inventory",
            emoji="🔙",
            style=discord.ButtonStyle.secondary,
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        self.inventory_view.in_inspection_mode = False
        self.inventory_view.selected_item = None
        self.inventory_view.update_components()

        embed = self.inventory_view.create_main_inventory_embed()
        await interaction.response.edit_message(embed=embed, view=self.inventory_view)

class SellConfirmationView(discord.ui.View):
    """Confirmation dialog for selling items."""

    def __init__(self, inventory_view, item_key):
        super().__init__(timeout=60)
        self.inventory_view = inventory_view
        self.item_key = item_key

    @discord.ui.button(label="Confirm Sale", emoji="✅", style=discord.ButtonStyle.danger)
    async def confirm_sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        player_data = self.inventory_view.player_data
        inventory = player_data.get('inventory', {})

        # Check if item still exists
        if inventory.get(self.item_key, 0) <= 0:
            await interaction.response.send_message("Item no longer in inventory!", ephemeral=True)
            return

        # Process sale
        item_data = ITEMS.get(self.item_key, {})
        item_name = item_data.get('name', self.item_key.replace('_', ' ').title())
        sell_price = item_data.get('sell_price', 10)

        # Remove item
        if inventory[self.item_key] > 1:
            inventory[self.item_key] -= 1
        else:
            inventory.pop(self.item_key, None)

        # Add gold
        player_data['gold'] = player_data.get('gold', 0) + sell_price

        # Save changes
        self.inventory_view.rpg_core.save_player_data(self.inventory_view.user_id, player_data)

        # Plagg's response
        if 'cheese' in self.item_key.lower():
            response = "WHAT?! You sold CHEESE?! This is a travesty! A crime against all that is holy and delicious!"
        else:
            responses = [
                "Good riddance. More space for cheese.",
                "Finally got rid of some junk. Now let's find some actual food.",
                "Sold it for pocket change. Probably could've bought half a cheese wheel with that.",
                "One person's trash is another person's... also trash. But hey, gold is gold."
            ]
            import random
            response = random.choice(responses)

        embed = discord.Embed(
            title="💰 Item Sold!",
            description=f"*\"{response}\"*\n\n"
                       f"**{item_name}** has been sold for **{format_number(sell_price)} Gold**!",
            color=COLORS['success']
        )

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel_sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        # Return to item inspection
        embed = self.inventory_view.create_item_inspection_embed(self.item_key)
        self.inventory_view.update_components()
        await interaction.response.edit_message(embed=embed, view=self.inventory_view)

class DropConfirmationView(discord.ui.View):
    """Confirmation dialog for dropping items."""

    def __init__(self, inventory_view, item_key):
        super().__init__(timeout=60)
        self.inventory_view = inventory_view
        self.item_key = item_key

    @discord.ui.button(label="Confirm Drop", emoji="✅", style=discord.ButtonStyle.danger)
    async def confirm_drop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        player_data = self.inventory_view.player_data
        inventory = player_data.get('inventory', {})

        # Check if item still exists
        if inventory.get(self.item_key, 0) <= 0:
            await interaction.response.send_message("Item no longer in inventory!", ephemeral=True)
            return

        # Process drop
        item_data = ITEMS.get(self.item_key, {})
        item_name = item_data.get('name', self.item_key.replace('_', ' ').title())

        # Remove item
        if inventory[self.item_key] > 1:
            inventory[self.item_key] -= 1
        else:
            inventory.pop(self.item_key, None)

        # Save changes
        self.inventory_view.rpg_core.save_player_data(self.inventory_view.user_id, player_data)

        # Plagg's response
        if 'cheese' in self.item_key.lower():
            response = "WHAT?! You dropped CHEESE?! You absolute buffoon! You'll regret this!"
        else:
            responses = [
                "Eh, whatever. One less thing to carry.",
                "Dropped it like it's hot. Or, you know, not cheese.",
                "Hope you don't need that. Actually, I don't care.",
                "Bye-bye, garbage item. Now, about that cheese..."
            ]
            import random
            response = random.choice(responses)

        embed = discord.Embed(
            title="🗑️ Item Dropped!",
            description=f"*\"{response}\"*\n\n"
                       f"**{item_name}** has been dropped!",
            color=COLORS['success']
        )

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel_drop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.inventory_view.user_id):
            await interaction.response.send_message("Not your inventory!", ephemeral=True)
            return

        # Return to item inspection
        embed = self.inventory_view.create_item_inspection_embed(self.item_key)
        self.inventory_view.update_components()
        await interaction.response.edit_message(embed=embed, view=self.inventory_view)

class RPGInventoryManager(commands.Cog):
    """Plagg's revolutionary interactive inventory management system."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="inventory", aliases=["inv", "bag", "items"])
    async def inventory_command(self, ctx):
        """Open Plagg's enhanced interactive inventory interface."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return

        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return

        player_data = rpg_core.get_player_data(str(ctx.author.id))
        if not player_data:
            embed = create_embed(
                "🎒 No Inventory Found", 
                "You need to create a character first!\n\n"
                "**Use `$startrpg` to begin your adventure!**\n"
                "*Then you can hoard all the non-cheese items your heart desires...*",
                COLORS['error']
            )
            await ctx.send(embed=embed)
            return

        # Create enhanced inventory view
        view = InventoryView(str(ctx.author.id), rpg_core)
        if not view.player_data:
            await ctx.send("❌ Error loading player data.")
            return

        embed = view.create_main_inventory_embed()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="equip")
    async def quick_equip(self, ctx, *, item_name: str = None):
        """Quickly equip an item by name."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return

        if not item_name:
            await ctx.send("Please specify an item to equip! Example: `$equip iron sword`")
            return

        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return

        player_data = rpg_core.get_player_data(str(ctx.author.id))
        if not player_data:
            await ctx.send("❌ Create a character first with `$startrpg`!")
            return

        # Find item in inventory
        inventory = player_data.get('inventory', {})
        item_key = None

        # Search by partial name
        item_name_lower = item_name.lower()
        for key in inventory:
            item_data = ITEMS.get(key, {})
            display_name = item_data.get('name', key.replace('_', ' ')).lower()
            if item_name_lower in display_name or item_name_lower in key.lower():
                item_key = key
                break

        if not item_key or inventory.get(item_key, 0) <= 0:
            await ctx.send(f"❌ You don't have '{item_name}' in your inventory!")
            return

        # Check if equippable
        item_data = ITEMS.get(item_key, {})
        item_type = item_data.get('type', '').lower()

        equipment_slots = {
            'weapon': 'weapon', 'sword': 'weapon', 'bow': 'weapon', 'staff': 'weapon', 'dagger': 'weapon', 'axe': 'weapon',
            'helmet': 'helmet', 'chestplate': 'chestplate', 'armor': 'chestplate', 'shield': 'chestplate',
            'boots': 'boots', 'accessory': 'accessory', 'ring': 'ring', 'necklace': 'necklace', 'charm': 'accessory', 'amulet': 'accessory',
            'artifact': 'artifact', 'kwami_artifact': 'artifact'
        }

        slot = equipment_slots.get(item_type)
        if not slot:
            await ctx.send(f"❌ '{item_name}' cannot be equipped!")
            return

        # Perform equipment
        equipment = player_data.get('equipment', {})

        # Remove from inventory
        if inventory[item_key] > 1:
            inventory[item_key] -= 1
        else:
            inventory.pop(item_key, None)

        # Handle old equipment
        old_item = equipment.get(slot)
        if old_item:
            inventory[old_item] = inventory.get(old_item, 0) + 1

        # Equip new item
        equipment[slot] = item_key

        # Save
        player_data['equipment'] = equipment
        player_data['inventory'] = inventory
        rpg_core.save_player_data(ctx.author.id, player_data)

        item_display_name = item_data.get('name', item_key.replace('_', ' ').title())

        embed = discord.Embed(
            title="✅ Quick Equip Success!",
            description=f"*\"Fine, {item_display_name} is now equipped. You look... marginally less pathetic.\"*",
            color=COLORS['success']
        )

        if old_item:
            old_data = ITEMS.get(old_item, {})
            old_name = old_data.get('name', old_item.replace('_', ' ').title())
            embed.add_field(
                name="🔄 Replaced Item",
                value=f"**{old_name}** returned to inventory",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="use")
    async def quick_use(self, ctx, *, item_name: str = None):
        """Quickly use a consumable item by name."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return

        if not item_name:
            await ctx.send("Please specify an item to use! Example: `$use health potion`")
            return

        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return

        player_data = rpg_core.get_player_data(str(ctx.author.id))
        if not player_data:
            await ctx.send("❌ Create a character first with `$startrpg`!")
            return

        # Find item in inventory
        inventory = player_data.get('inventory', {})
        item_key = None

        # Search by partial name
        item_name_lower = item_name.lower()
        for key in inventory:
            item_data = ITEMS.get(key, {})
            display_name = item_data.get('name', key.replace('_', ' ')).lower()
            if item_name_lower in display_name or item_name_lower in key.lower():
                item_key = key
                break

        if not item_key or inventory.get(item_key, 0) <= 0:
            await ctx.send(f"❌ You don't have '{item_name}' in your inventory!")
            return

        # Check if usable
        item_data = ITEMS.get(item_key, {})
        item_type = item_data.get('type', '').lower()

        if item_type not in ['consumable', 'potion', 'food', 'cheese', 'elixir']:
            await ctx.send(f"❌ '{item_name}' cannot be used!")
            return

         # Process item effects
        effect_result = self.process_item_effect(item_key, item_data, player_data)

        # Remove item from inventory
        inventory = player_data.get('inventory', {})
        if inventory.get(item_key, 0) > 1:
            inventory[item_key] -= 1
        else:
            inventory.pop(item_key, None)

        player_data['inventory'] = inventory

        # Save changes
        rpg_core.save_player_data(ctx.author.id, player_data)

        item_display_name = item_data.get('name', item_key.replace('_', ' ').title())

        embed = discord.Embed(
            title="🧪 Item Used!",
            description=f"**{item_display_name}** has been consumed!\n\n{effect_result}",
            color=COLORS['success']
        )

        await ctx.send(embed=embed)

    def process_item_effect(self, item_key, item_data, player_data):
        """Process the effects of using an item with proper resource validation."""
        resources = player_data.get('resources', {})

        if 'cheese' in item_key.lower():
            # Special cheese handling
            hp_heal = item_data.get('heal_amount', 50)
            current_hp = resources.get('hp', 100)
            max_hp = resources.get('max_hp', 100)
            actual_heal = min(hp_heal, max_hp - current_hp)
            resources['hp'] = min(max_hp, current_hp + actual_heal)
            player_data['resources'] = resources
            return f"*\"NOW WE'RE TALKING! That cheese was absolutely divine! +{actual_heal} HP restored!\"*"

        elif item_data.get('heal_amount'):
            heal_amount = item_data.get('heal_amount', 25)
            current_hp = resources.get('hp', 100)
            max_hp = resources.get('max_hp', 100)
            actual_heal = min(heal_amount, max_hp - current_hp)
            resources['hp'] = min(max_hp, current_hp + actual_heal)
            player_data['resources'] = resources
            return f"*\"Tastes awful, but I guess it worked. +{actual_heal} HP restored.\"*"

        elif item_data.get('mana_amount'):
            mana_amount = item_data.get('mana_amount', 20)
            current_mana = resources.get('mana', 50)
            max_mana = resources.get('max_mana', 50)
            actual_mana = min(mana_amount, max_mana - current_mana)
            resources['mana'] = min(max_mana, current_mana + actual_mana)
            player_data['resources'] = resources
            return f"*\"Magical and boring. +{actual_mana} Mana restored.\"*"

        else:
            return f"*\"You consumed it. Something probably happened. I wasn't paying attention.\"*"

async def setup(bot):
    await bot.add_cog(RPGInventoryManager(bot))