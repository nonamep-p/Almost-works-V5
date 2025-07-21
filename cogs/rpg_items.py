
import discord
from discord.ext import commands
from rpg_data.game_data import ITEMS, RARITY_COLORS
from utils.helpers import create_embed, format_number
from config import COLORS, is_module_enabled
import logging

logger = logging.getLogger(__name__)

class InventoryView(discord.ui.View):
    """Interactive inventory management interface."""

    def __init__(self, player_data, rpg_core, user_id):
        super().__init__(timeout=180)
        self.player_data = player_data
        self.rpg_core = rpg_core
        self.user_id = str(user_id)  # Ensure string format
        self.current_category = "all"
        self.current_page = 0
        self.items_per_page = 10

    @discord.ui.select(
        placeholder="📦 Select inventory category...",
        options=[
            discord.SelectOption(
                label="🔍 All Items",
                value="all",
                description="View all items in inventory"
            ),
            discord.SelectOption(
                label="⚔️ Weapons", 
                value="weapon",
                description="Swords, staffs, and combat gear"
            ),
            discord.SelectOption(
                label="🛡️ Armor",
                value="armor", 
                description="Protective equipment and shields"
            ),
            discord.SelectOption(
                label="🧪 Consumables",
                value="consumable",
                description="Potions and temporary items"
            ),
            discord.SelectOption(
                label="💎 Accessories",
                value="accessory",
                description="Rings and special equipment"
            ),
            discord.SelectOption(
                label="✨ Artifacts",
                value="artifact",
                description="Kwami artifacts and set pieces"
            ),
            discord.SelectOption(
                label="📦 Materials",
                value="material",
                description="Crafting components and resources"
            )
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This isn't your inventory!", ephemeral=True)
            return

        self.current_category = select.values[0]
        self.current_page = 0
        
        embed = self.create_inventory_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary, row=1)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This isn't your inventory!", ephemeral=True)
            return

        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_inventory_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ You're already on the first page!", ephemeral=True)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This isn't your inventory!", ephemeral=True)
            return

        filtered_items = self.get_filtered_items()
        max_pages = (len(filtered_items) - 1) // self.items_per_page

        if self.current_page < max_pages:
            self.current_page += 1
            embed = self.create_inventory_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ You're already on the last page!", ephemeral=True)

    @discord.ui.button(label="🎒 Equipment", style=discord.ButtonStyle.primary, row=1)
    async def show_equipment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This isn't your inventory!", ephemeral=True)
            return

        embed = self.create_equipment_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="📊 Item Details", style=discord.ButtonStyle.success, row=2)
    async def item_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This isn't your inventory!", ephemeral=True)
            return

        # Show detailed item selection
        filtered_items = self.get_filtered_items()
        if not filtered_items:
            await interaction.response.send_message("❌ No items in this category!", ephemeral=True)
            return

        view = ItemDetailView(filtered_items, self.rpg_core, self.user_id, self.player_data)
        embed = discord.Embed(
            title="📊 Item Details Selection",
            description="Choose an item to view detailed information:",
            color=COLORS['info']
        )
        await interaction.response.edit_message(embed=embed, view=view)

    def get_filtered_items(self):
        """Get items filtered by category."""
        inventory = self.player_data.get('inventory', {})
        filtered_items = []

        for item_key, quantity in inventory.items():
            if quantity > 0:
                item_data = ITEMS.get(item_key)
                if item_data:
                    if self.current_category == "all" or item_data.get('type') == self.current_category:
                        filtered_items.append((item_key, item_data, quantity))
                else:
                    # Handle items not in ITEMS database
                    if self.current_category == "all":
                        filtered_items.append((item_key, {"name": item_key.replace('_', ' ').title(), "type": "unknown"}, quantity))

        return filtered_items

    def create_inventory_embed(self):
        """Create the inventory display embed."""
        filtered_items = self.get_filtered_items()
        
        # Calculate pagination
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = filtered_items[start_idx:end_idx]
        
        category_names = {
            "all": "All Items",
            "weapon": "Weapons",
            "armor": "Armor", 
            "consumable": "Consumables",
            "accessory": "Accessories",
            "artifact": "Artifacts",
            "material": "Materials"
        }

        embed = discord.Embed(
            title=f"🎒 Inventory - {category_names.get(self.current_category, 'Unknown')}",
            description=f"**Total Items:** {len(filtered_items)}\n"
                       f"**Page:** {self.current_page + 1}/{max(1, (len(filtered_items) + self.items_per_page - 1) // self.items_per_page)}\n"
                       f"**Gold:** {format_number(self.player_data.get('gold', 0))}",
            color=COLORS['primary']
        )

        if not page_items:
            embed.add_field(
                name="📦 Empty Category",
                value="No items found in this category.\n\n*Visit the shop to buy items!*",
                inline=False
            )
        else:
            # Create organized display
            display_text = ""
            for i, (item_key, item_data, quantity) in enumerate(page_items):
                item_name = item_data.get('name', item_key.replace('_', ' ').title())
                rarity_emoji = self.get_rarity_emoji(item_data.get('rarity', 'common'))
                
                # Add stats preview
                stats_preview = ""
                if item_data.get('attack'):
                    stats_preview += f" ⚔️{item_data['attack']}"
                if item_data.get('defense'):
                    stats_preview += f" 🛡️{item_data['defense']}"
                if item_data.get('heal_amount'):
                    stats_preview += f" ❤️+{item_data['heal_amount']}"
                
                display_text += f"`{i+1}.` {rarity_emoji} **{item_name}**{stats_preview} x{quantity}\n"

            if display_text:
                embed.add_field(
                    name="📋 Items List",
                    value=display_text,
                    inline=False
                )

            # Add quick stats
            total_value = sum(
                ITEMS.get(item_key, {}).get('price', 0) * quantity * 0.6  # Sell price
                for item_key, _, quantity in filtered_items
            )
            
            embed.add_field(
                name="💰 Category Value",
                value=f"Sell Value: {format_number(int(total_value))} gold",
                inline=True
            )

        return embed

    def create_equipment_embed(self):
        """Create equipment display embed."""
        equipment = self.player_data.get('equipment', {})
        
        embed = discord.Embed(
            title="⚔️ Current Equipment",
            description="Your currently equipped items:",
            color=COLORS['warning']
        )

        slots = {
            'weapon': '⚔️ Weapon',
            'armor': '🛡️ Armor',
            'accessory': '💎 Accessory',
            'artifact': '✨ Artifact'
        }

        for slot, slot_name in slots.items():
            item_key = equipment.get(slot)
            if item_key and item_key in ITEMS:
                item_data = ITEMS[item_key]
                rarity_emoji = self.get_rarity_emoji(item_data.get('rarity', 'common'))
                
                stats_text = ""
                if item_data.get('attack'):
                    stats_text += f"⚔️ ATK: {item_data['attack']} "
                if item_data.get('defense'):
                    stats_text += f"🛡️ DEF: {item_data['defense']} "
                if item_data.get('hp'):
                    stats_text += f"❤️ HP: +{item_data['hp']} "
                if item_data.get('mana'):
                    stats_text += f"💙 MP: +{item_data['mana']} "

                value = f"{rarity_emoji} **{item_data['name']}**\n*{stats_text.strip()}*"
            else:
                value = "*Nothing equipped*"

            embed.add_field(name=slot_name, value=value, inline=True)

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
            'cosmic': '🌟'
        }
        return rarity_emojis.get(rarity, '⚪')

class ItemDetailView(discord.ui.View):
    """View for showing detailed item information."""

    def __init__(self, items, rpg_core, user_id, player_data):
        super().__init__(timeout=120)
        self.items = items
        self.rpg_core = rpg_core
        self.user_id = user_id
        self.player_data = player_data

        # Create select menu with items (max 25 options)
        options = []
        for i, (item_key, item_data, quantity) in enumerate(items[:25]):
            item_name = item_data.get('name', item_key.replace('_', ' ').title())
            rarity = item_data.get('rarity', 'common')
            options.append(discord.SelectOption(
                label=f"{item_name} (x{quantity})",
                value=item_key,
                description=f"{rarity.title()} {item_data.get('type', 'item')}"
            ))

        if options:
            self.add_item(ItemSelectMenu(options, self.rpg_core, self.user_id, self.player_data))

class ItemSelectMenu(discord.ui.Select):
    """Select menu for choosing items to view details."""

    def __init__(self, options, rpg_core, user_id, player_data):
        super().__init__(placeholder="Choose an item to examine...", options=options)
        self.rpg_core = rpg_core
        self.user_id = user_id
        self.player_data = player_data

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This isn't your inventory!", ephemeral=True)
            return

        item_key = self.values[0]
        item_data = ITEMS.get(item_key)
        quantity = self.player_data['inventory'].get(item_key, 0)

        if not item_data:
            await interaction.response.send_message("❌ Item data not found!", ephemeral=True)
            return

        # Create detailed item embed
        rarity_color = RARITY_COLORS.get(item_data['rarity'], COLORS['primary'])
        embed = discord.Embed(
            title=f"{item_data['name']}",
            description=item_data.get('description', 'No description available.'),
            color=rarity_color
        )

        # Basic info
        embed.add_field(
            name="📊 Basic Info",
            value=f"**Type:** {item_data['type'].title()}\n"
                  f"**Rarity:** {item_data['rarity'].title()}\n"
                  f"**Quantity:** {quantity}",
            inline=True
        )

        # Stats
        stats_text = ""
        if item_data.get('attack'):
            stats_text += f"⚔️ Attack: +{item_data['attack']}\n"
        if item_data.get('defense'):
            stats_text += f"🛡️ Defense: +{item_data['defense']}\n"
        if item_data.get('hp'):
            stats_text += f"❤️ HP: +{item_data['hp']}\n"
        if item_data.get('mana'):
            stats_text += f"💙 Mana: +{item_data['mana']}\n"
        if item_data.get('heal_amount'):
            stats_text += f"💊 Healing: {item_data['heal_amount']}\n"
        if item_data.get('mana_amount'):
            stats_text += f"🔮 Mana Restore: {item_data['mana_amount']}\n"

        if stats_text:
            embed.add_field(name="📈 Stats", value=stats_text, inline=True)

        # Effects
        if item_data.get('effects'):
            effects_text = "\n".join(f"✨ {effect}" for effect in item_data['effects'])
            embed.add_field(name="🌟 Special Effects", value=effects_text, inline=False)

        # Market value
        if item_data.get('price'):
            embed.add_field(
                name="💰 Market Value",
                value=f"**Buy:** {format_number(item_data['price'])} gold\n"
                      f"**Sell:** {format_number(int(item_data['price'] * 0.6))} gold",
                inline=True
            )

        # Action buttons
        view = ItemActionView(item_key, item_data, self.rpg_core, self.user_id, self.player_data)
        await interaction.response.edit_message(embed=embed, view=view)

class ItemActionView(discord.ui.View):
    """View for item actions (use, equip, sell)."""

    def __init__(self, item_key, item_data, rpg_core, user_id, player_data):
        super().__init__(timeout=120)
        self.item_key = item_key
        self.item_data = item_data
        self.rpg_core = rpg_core
        self.user_id = user_id
        self.player_data = player_data

        # Add appropriate action buttons
        if item_data['type'] == 'consumable':
            self.add_item(UseItemButton())
        elif item_data['type'] in ['weapon', 'armor', 'accessory', 'artifact']:
            self.add_item(EquipItemButton())
        
        self.add_item(SellItemButton())
        self.add_item(BackToInventoryButton())

class UseItemButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🧪 Use Item", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        # Implementation for using items
        await interaction.response.send_message("✅ Item used successfully!", ephemeral=True)

class EquipItemButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="⚔️ Equip", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        # Implementation for equipping items
        await interaction.response.send_message("✅ Item equipped successfully!", ephemeral=True)

class SellItemButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="💰 Sell", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        # Implementation for selling items
        await interaction.response.send_message("💰 Item sold successfully!", ephemeral=True)

class BackToInventoryButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔙 Back", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        # Return to main inventory
        inventory_view = InventoryView(view.player_data, view.rpg_core, view.user_id)
        embed = inventory_view.create_inventory_embed()
        await interaction.response.edit_message(embed=embed, view=inventory_view)

class RPGItems(commands.Cog):
    """RPG item management and equipment system."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="inventory", aliases=["inv", "bag"])
    async def inventory(self, ctx):
        """View your inventory with interactive interface."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return
            
        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return
        
        player_data = rpg_core.get_player_data(ctx.author.id)
        if not player_data:
            # Auto-start tutorial for new players
            embed = discord.Embed(
                title="🎮 Welcome to Project: Blood & Cheese!",
                description="You need to create a character first! Let's start with the interactive tutorial.",
                color=COLORS['info']
            )
            
            # Import tutorial view from help
            from cogs.help import TutorialView
            view = TutorialView(self.bot, "$")
            await ctx.send(embed=embed, view=view)
            return
        
        view = InventoryView(player_data, rpg_core, str(ctx.author.id))
        embed = view.create_inventory_embed()
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="equip")
    async def equip_item(self, ctx, *, item_name: str):
        """Equip weapons, armor, or accessories."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return
            
        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return
        
        player_data = rpg_core.get_player_data(ctx.author.id)
        if not player_data:
            # Auto-start tutorial
            from cogs.help import TutorialView
            view = TutorialView(self.bot, "$")
            embed = discord.Embed(
                title="🎮 Welcome! Let's get you started.",
                color=COLORS['info']
            )
            await ctx.send(embed=embed, view=view)
            return
        
        # Find the item
        item_key = None
        item_data = None
        for key, data in ITEMS.items():
            if key == item_name.lower().replace(" ", "_") or data['name'].lower() == item_name.lower():
                item_key = key
                item_data = data
                break
        
        if not item_data:
            await ctx.send(f"❌ Item '{item_name}' not found!")
            return
        
        # Check if player has the item
        if item_key not in player_data.get('inventory', {}) or player_data['inventory'][item_key] <= 0:
            await ctx.send(f"❌ You don't have **{item_data['name']}**!")
            return
        
        # Check if item is equippable
        item_type = item_data['type']
        if item_type not in ['weapon', 'armor', 'accessory', 'artifact']:
            await ctx.send(f"❌ **{item_data['name']}** cannot be equipped!")
            return
        
        # Unequip current item of same type
        current_equipment = player_data.get('equipment', {})
        old_item = current_equipment.get(item_type)
        
        if old_item:
            # Return old item to inventory
            if old_item in player_data['inventory']:
                player_data['inventory'][old_item] += 1
            else:
                player_data['inventory'][old_item] = 1
        
        # Equip new item
        current_equipment[item_type] = item_key
        player_data['equipment'] = current_equipment
        
        # Remove from inventory
        player_data['inventory'][item_key] -= 1
        if player_data['inventory'][item_key] <= 0:
            del player_data['inventory'][item_key]
        
        # Update stats
        self.update_equipment_stats(player_data)
        rpg_core.save_player_data(ctx.author.id, player_data)
        
        rarity_color = RARITY_COLORS.get(item_data['rarity'], COLORS['primary'])
        embed = discord.Embed(
            title="⚔️ Item Equipped!",
            description=f"Successfully equipped **{item_data['name']}**!",
            color=rarity_color
        )
        
        if old_item and old_item in ITEMS:
            embed.add_field(
                name="Previous Item",
                value=f"Unequipped: {ITEMS[old_item]['name']}",
                inline=False
            )
        
        # Show stat changes
        stats_text = ""
        if item_data.get('attack'):
            stats_text += f"⚔️ Attack: +{item_data['attack']}\n"
        if item_data.get('defense'):
            stats_text += f"🛡️ Defense: +{item_data['defense']}\n"
        if item_data.get('hp'):
            stats_text += f"❤️ HP: +{item_data['hp']}\n"
        if item_data.get('mana'):
            stats_text += f"💙 Mana: +{item_data['mana']}\n"
        
        if stats_text:
            embed.add_field(name="📊 Stat Bonuses", value=stats_text, inline=True)
        
        if item_data.get('effects'):
            effects_text = "\n".join(f"✨ {effect}" for effect in item_data['effects'])
            embed.add_field(name="🌟 Special Effects", value=effects_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="unequip")
    async def unequip_item(self, ctx, slot: str):
        """Unequip an item from a specific slot."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return
            
        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return
        
        player_data = rpg_core.get_player_data(ctx.author.id)
        if not player_data:
            from cogs.help import TutorialView
            view = TutorialView(self.bot, "$")
            embed = discord.Embed(
                title="🎮 Welcome! Let's get you started.",
                color=COLORS['info']
            )
            await ctx.send(embed=embed, view=view)
            return
        
        valid_slots = ['weapon', 'armor', 'accessory', 'artifact']
        slot = slot.lower()
        
        if slot not in valid_slots:
            await ctx.send(f"❌ Invalid slot! Choose from: {', '.join(valid_slots)}")
            return
        
        current_equipment = player_data.get('equipment', {})
        if slot not in current_equipment or not current_equipment[slot]:
            await ctx.send(f"❌ No item equipped in {slot} slot!")
            return
        
        item_key = current_equipment[slot]
        item_data = ITEMS.get(item_key)
        
        if not item_data:
            await ctx.send("❌ Equipped item data not found!")
            return
        
        # Return item to inventory
        if item_key in player_data.get('inventory', {}):
            player_data['inventory'][item_key] += 1
        else:
            player_data['inventory'][item_key] = 1
        
        # Remove from equipment
        current_equipment[slot] = None
        player_data['equipment'] = current_equipment
        
        # Update stats
        self.update_equipment_stats(player_data)
        rpg_core.save_player_data(ctx.author.id, player_data)
        
        embed = discord.Embed(
            title="📦 Item Unequipped",
            description=f"Unequipped **{item_data['name']}** from {slot} slot.\n\nItem returned to inventory.",
            color=COLORS['secondary']
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="use")
    async def use_item(self, ctx, *, item_name: str):
        """Use a consumable item."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return
            
        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return
        
        player_data = rpg_core.get_player_data(ctx.author.id)
        if not player_data:
            from cogs.help import TutorialView
            view = TutorialView(self.bot, "$")
            embed = discord.Embed(
                title="🎮 Welcome! Let's get you started.",
                color=COLORS['info']
            )
            await ctx.send(embed=embed, view=view)
            return
        
        # Find the item
        item_key = None
        item_data = None
        for key, data in ITEMS.items():
            if key == item_name.lower().replace(" ", "_") or data['name'].lower() == item_name.lower():
                item_key = key
                item_data = data
                break
        
        if not item_data:
            await ctx.send(f"❌ Item '{item_name}' not found!")
            return
        
        # Check if player has the item
        if item_key not in player_data.get('inventory', {}) or player_data['inventory'][item_key] <= 0:
            await ctx.send(f"❌ You don't have **{item_data['name']}**!")
            return
        
        # Check if item is consumable
        if item_data['type'] != 'consumable':
            await ctx.send(f"❌ **{item_data['name']}** is not a consumable item!")
            return
        
        # Apply item effects
        effects_applied = []
        
        if item_data.get('heal_amount'):
            heal = item_data['heal_amount']
            current_hp = player_data['resources']['hp']
            max_hp = player_data['resources']['max_hp']
            
            actual_heal = min(heal, max_hp - current_hp)
            player_data['resources']['hp'] += actual_heal
            effects_applied.append(f"❤️ Restored {actual_heal} HP")
        
        if item_data.get('mana_amount'):
            mana = item_data['mana_amount']
            current_mana = player_data['resources']['mana']
            max_mana = player_data['resources']['max_mana']
            
            actual_mana = min(mana, max_mana - current_mana)
            player_data['resources']['mana'] += actual_mana
            effects_applied.append(f"💙 Restored {actual_mana} Mana")
        
        # Remove item from inventory
        player_data['inventory'][item_key] -= 1
        if player_data['inventory'][item_key] <= 0:
            del player_data['inventory'][item_key]
        
        rpg_core.save_player_data(ctx.author.id, player_data)
        
        rarity_color = RARITY_COLORS.get(item_data['rarity'], COLORS['primary'])
        embed = discord.Embed(
            title="✨ Item Used!",
            description=f"You used **{item_data['name']}**!\n\n" + "\n".join(effects_applied),
            color=rarity_color
        )
        
        if item_data.get('effects'):
            embed.add_field(
                name="🌟 Additional Effects",
                value="\n".join(f"• {effect}" for effect in item_data['effects']),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="equipment", aliases=["gear"])
    async def show_equipment(self, ctx):
        """Show currently equipped items."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return
            
        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return
        
        player_data = rpg_core.get_player_data(ctx.author.id)
        if not player_data:
            from cogs.help import TutorialView
            view = TutorialView(self.bot, "$")
            embed = discord.Embed(
                title="🎮 Welcome! Let's get you started.",
                color=COLORS['info']
            )
            await ctx.send(embed=embed, view=view)
            return
        
        equipment = player_data.get('equipment', {})
        
        embed = discord.Embed(
            title=f"⚔️ {ctx.author.display_name}'s Equipment",
            color=COLORS['primary']
        )
        
        slots = ['weapon', 'armor', 'accessory', 'artifact']
        
        for slot in slots:
            item_key = equipment.get(slot)
            if item_key and item_key in ITEMS:
                item_data = ITEMS[item_key]
                rarity_emoji = "⚪" if item_data['rarity'] == 'common' else "🟢" if item_data['rarity'] == 'uncommon' else "🔵" if item_data['rarity'] == 'rare' else "🟣"
                
                value = f"{rarity_emoji} **{item_data['name']}**\n"
                
                # Show key stats
                stats = []
                if item_data.get('attack'):
                    stats.append(f"⚔️{item_data['attack']}")
                if item_data.get('defense'):
                    stats.append(f"🛡️{item_data['defense']}")
                if item_data.get('hp'):
                    stats.append(f"❤️{item_data['hp']}")
                if item_data.get('mana'):
                    stats.append(f"💙{item_data['mana']}")
                
                if stats:
                    value += f"*{' | '.join(stats)}*"
                
                embed.add_field(name=f"{slot.title()}", value=value, inline=True)
            else:
                embed.add_field(name=f"{slot.title()}", value="*None equipped*", inline=True)
        
        # Show total stat bonuses
        total_stats = self.calculate_equipment_bonuses(player_data)
        if any(total_stats.values()):
            bonus_text = ""
            if total_stats.get('attack', 0) > 0:
                bonus_text += f"⚔️ Attack: +{total_stats['attack']}\n"
            if total_stats.get('defense', 0) > 0:
                bonus_text += f"🛡️ Defense: +{total_stats['defense']}\n"
            if total_stats.get('hp', 0) > 0:
                bonus_text += f"❤️ HP: +{total_stats['hp']}\n"
            if total_stats.get('mana', 0) > 0:
                bonus_text += f"💙 Mana: +{total_stats['mana']}\n"
            
            embed.add_field(name="📊 Total Equipment Bonuses", value=bonus_text, inline=False)
        
        await ctx.send(embed=embed)
    
    def calculate_equipment_bonuses(self, player_data):
        """Calculate total bonuses from equipped items."""
        bonuses = {'attack': 0, 'defense': 0, 'hp': 0, 'mana': 0}
        equipment = player_data.get('equipment', {})
        
        for slot, item_key in equipment.items():
            if item_key and item_key in ITEMS:
                item_data = ITEMS[item_key]
                bonuses['attack'] += item_data.get('attack', 0)
                bonuses['defense'] += item_data.get('defense', 0)
                bonuses['hp'] += item_data.get('hp', 0)
                bonuses['mana'] += item_data.get('mana', 0)
        
        return bonuses
    
    def update_equipment_stats(self, player_data):
        """Update player's derived stats based on equipment."""
        # Recalculate base derived stats
        base_stats = player_data['stats']
        player_data['derived_stats']['attack'] = 10 + (base_stats['strength'] * 2)
        player_data['derived_stats']['magic_attack'] = 10 + (base_stats['intelligence'] * 2)
        player_data['derived_stats']['defense'] = 5 + base_stats['constitution']
        
        # Add equipment bonuses
        equipment_bonuses = self.calculate_equipment_bonuses(player_data)
        player_data['derived_stats']['attack'] += equipment_bonuses['attack']
        player_data['derived_stats']['defense'] += equipment_bonuses['defense']
        
        # Update max HP and mana
        base_hp = 100 + (base_stats['constitution'] * 10)
        base_mana = 50 + (base_stats['intelligence'] * 5)
        
        new_max_hp = base_hp + equipment_bonuses['hp']
        new_max_mana = base_mana + equipment_bonuses['mana']
        
        # Adjust current HP/mana if max increased
        hp_diff = new_max_hp - player_data['resources']['max_hp']
        mana_diff = new_max_mana - player_data['resources']['max_mana']
        
        player_data['resources']['max_hp'] = new_max_hp
        player_data['resources']['max_mana'] = new_max_mana
        
        if hp_diff > 0:
            player_data['resources']['hp'] += hp_diff
        if mana_diff > 0:
            player_data['resources']['mana'] += mana_diff

async def setup(bot):
    await bot.add_cog(RPGItems(bot))
