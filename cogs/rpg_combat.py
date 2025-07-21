import discord
from discord.ext import commands
import random
import asyncio
from rpg_data.game_data import CLASSES, ITEMS, RARITY_COLORS, TACTICAL_MONSTERS
from utils.helpers import create_embed, format_number
from config import COLORS, is_module_enabled
import logging

logger = logging.getLogger(__name__)

# Enhanced monster data with weaknesses
ENHANCED_MONSTERS = {
    'goblin': {
        'name': 'Goblin Warrior',
        'emoji': '👹',
        'hp': 120,
        'max_hp': 120,
        'toughness': 60,
        'max_toughness': 60,
        'weakness_type': 'physical',
        'attack': 25,
        'defense': 8,
        'level': 3,
        'xp_reward': 35,
        'gold_reward': 15,
        'skills': ['quick_slash'],
        'loot_table': {'health_potion': 0.4, 'iron_sword': 0.2}
    },
    'orc': {
        'name': 'Orc Berserker',
        'emoji': '👺',
        'hp': 180,
        'max_hp': 180,
        'toughness': 80,
        'max_toughness': 80,
        'weakness_type': 'ice',
        'attack': 35,
        'defense': 12,
        'level': 6,
        'xp_reward': 60,
        'gold_reward': 25,
        'skills': ['berserker_rage'],
        'loot_table': {'health_potion': 0.3, 'steel_armor': 0.15}
    },
    'ice_elemental': {
        'name': 'Ice Elemental',
        'emoji': '🧊',
        'hp': 150,
        'max_hp': 150,
        'toughness': 70,
        'max_toughness': 70,
        'weakness_type': 'fire',
        'attack': 30,
        'defense': 15,
        'level': 5,
        'xp_reward': 50,
        'gold_reward': 20,
        'skills': ['ice_blast'],
        'loot_table': {'mana_potion': 0.5, 'ice_crystal': 0.3}
    },
    'dragon': {
        'name': 'Ancient Dragon',
        'emoji': '🐉',
        'hp': 400,
        'max_hp': 400,
        'toughness': 120,
        'max_toughness': 120,
        'weakness_type': 'lightning',
        'attack': 60,
        'defense': 25,
        'level': 15,
        'xp_reward': 200,
        'gold_reward': 100,
        'skills': ['dragon_breath', 'tail_sweep'],
        'loot_table': {'dragon_scale': 0.8, 'legendary_weapon': 0.1}
    }
}

# Status Effects System
STATUS_EFFECTS = {
    # Blessings (Buffs)
    'fortify': {
        'name': 'Fortify',
        'type': 'blessing',
        'emoji': '🛡️',
        'effect': 'def_boost',
        'value': 0.30,
        'duration': 3,
        'description': 'Increases Defense by 30% for 3 turns'
    },
    'empower': {
        'name': 'Empower',
        'type': 'blessing',
        'emoji': '💪',
        'effect': 'atk_boost',
        'value': 0.30,
        'duration': 3,
        'description': 'Increases Attack by 30% for 3 turns'
    },
    'haste': {
        'name': 'Haste',
        'type': 'blessing',
        'emoji': '⚡',
        'effect': 'speed_boost',
        'value': 0.50,
        'duration': 1,
        'description': 'Acts 50% sooner on next turn'
    },
    'regeneration': {
        'name': 'Regeneration',
        'type': 'blessing',
        'emoji': '💚',
        'effect': 'heal_over_time',
        'value': 0.10,
        'duration': 3,
        'description': 'Heals 10% of Max HP at start of turn for 3 turns'
    },
    'crit_up': {
        'name': 'Crit Up',
        'type': 'blessing',
        'emoji': '🔥',
        'effect': 'crit_boost',
        'value': 0.50,
        'duration': 2,
        'description': 'Increases Critical Hit Chance by 50% for 2 turns'
    },
    'evade_up': {
        'name': 'Evade Up',
        'type': 'blessing',
        'emoji': '👻',
        'effect': 'dodge_boost',
        'value': 0.30,
        'duration': 2,
        'description': 'Increases dodge chance by 30% for 2 turns'
    },

    # Curses (Debuffs)
    'bleed': {
        'name': 'Bleed',
        'type': 'curse',
        'emoji': '🩸',
        'effect': 'damage_over_time',
        'value': 0.05,
        'duration': 3,
        'description': 'Deals 5% of Max HP as damage at start of turn for 3 turns'
    },
    'burn': {
        'name': 'Burn',
        'type': 'curse',
        'emoji': '🔥',
        'effect': 'damage_over_time_no_heal',
        'value': 0.08,
        'duration': 2,
        'description': 'Deals 8% Max HP damage and prevents healing for 2 turns'
    },
    'stun': {
        'name': 'Stun',
        'type': 'curse',
        'emoji': '🌟',
        'effect': 'skip_turn',
        'duration': 1,
        'description': 'Cannot act for 1 turn'
    },
    'weakness_break': {
        'name': 'Weakness Break',
        'type': 'curse',
        'emoji': '💥',
        'effect': 'vulnerability',
        'value': 0.50,
        'duration': 2,
        'description': 'Stunned for 1 turn, +50% damage taken for 2 turns'
    },
    'armor_break': {
        'name': 'Armor Break',
        'type': 'curse',
        'emoji': '🛡️💔',
        'effect': 'def_reduction',
        'value': 0.50,
        'duration': 3,
        'description': 'Reduces Defense by 50% for 3 turns'
    },
    'slow': {
        'name': 'Slow',
        'type': 'curse',
        'emoji': '🐌',
        'effect': 'speed_reduction',
        'value': 0.50,
        'duration': 1,
        'description': 'Acts 50% later on next turn'
    },
    'blind': {
        'name': 'Blind',
        'type': 'curse',
        'emoji': '🙈',
        'effect': 'accuracy_reduction',
        'value': 0.50,
        'duration': 2,
        'description': 'Reduces accuracy by 50% for 2 turns'
    },
    'stopwatch': {
        'name': 'Stopwatch',
        'type': 'curse',
        'emoji': '⏱️',
        'effect': 'stacking_stun',
        'stacks': 0,
        'max_stacks': 3,
        'description': 'Stacking debuff. At 3 stacks, target is Stunned for 1 turn'
    }
}

# Enhanced skills with SP costs and status effects
TACTICAL_SKILLS = {
    'power_strike': {
        'name': 'Power Strike',
        'cost': 20,
        'damage': 40,
        'toughness_damage': 15,
        'damage_type': 'physical',
        'ultimate_gain': 20,
        'description': 'A powerful physical attack that costs 20 SP.',
        'effects': [],
        'classes': ['warrior', 'battlemage']
    },
    'flame_slash': {
        'name': 'Flame Slash',
        'cost': 20,
        'damage': 35,
        'toughness_damage': 20,
        'damage_type': 'fire',
        'ultimate_gain': 20,
        'description': 'A burning sword technique that costs 20 SP.',
        'effects': [{'status': 'burn', 'chance': 0.7}],
        'classes': ['battlemage', 'mage'],
        'required_items': {}
    },
    'ice_lance': {
        'name': 'Ice Lance',
        'cost': 20,
        'damage': 38,
        'toughness_damage': 18,
        'damage_type': 'ice',
        'ultimate_gain': 20,
        'description': 'A piercing ice attack that costs 20 SP.',
        'effects': [{'status': 'slow', 'chance': 0.6}],
        'classes': ['mage'],
        'required_items': {}
    },
    'healing_light': {
        'name': 'Healing Light',
        'cost': 30,
        'heal': 50,
        'ultimate_gain': 15,
        'description': 'Restores health using 30 SP.',
        'effects': [{'status': 'regeneration', 'chance': 0.3}]
    },
    'shield_bash': {
        'name': 'Shield Bash',
        'cost': 20,
        'damage': 25,
        'toughness_damage': 20,
        'damage_type': 'physical',
        'ultimate_gain': 20,
        'description': 'Bash enemy with shield, chance to stun.',
        'effects': [{'status': 'stun', 'chance': 0.5}]
    },
    'taunting_shout': {
        'name': 'Taunting Shout',
        'cost': 15,
        'damage': 0,
        'ultimate_gain': 15,
        'description': 'Force enemy to target you and gain defense.',
        'self_effects': [{'status': 'fortify', 'chance': 1.0}]
    },
    'fireball': {
        'name': 'Fireball',
        'cost': 25,
        'damage': 45,
        'toughness_damage': 25,
        'damage_type': 'fire',
        'ultimate_gain': 20,
        'description': 'Heavy fire damage with burn chance.',
        'effects': [{'status': 'burn', 'chance': 0.8}]
    },
    'arcane_explosion': {
        'name': 'Arcane Explosion',
        'cost': 40,
        'damage': 30,
        'toughness_damage': 20,
        'damage_type': 'magic',
        'ultimate_gain': 30,
        'description': 'Moderate magic damage to all enemies.',
        'effects': []
    },
    'serrated_strike': {
        'name': 'Serrated Strike',
        'cost': 20,
        'damage': 35,
        'toughness_damage': 15,
        'damage_type': 'physical',
        'ultimate_gain': 20,
        'description': 'Causes bleeding damage over time.',
        'effects': [{'status': 'bleed', 'chance': 0.9}]
    },
    'shadow_step': {
        'name': 'Shadow Step',
        'cost': 25,
        'damage': 0,
        'ultimate_gain': 15,
        'description': 'Grants evasion and critical hit bonus.',
        'self_effects': [
            {'status': 'evade_up', 'chance': 1.0},
            {'status': 'crit_up', 'chance': 1.0}
        ]
    },
    'piercing_shot': {
        'name': 'Piercing Shot',
        'cost': 25,
        'damage': 40,
        'toughness_damage': 20,
        'damage_type': 'physical',
        'ultimate_gain': 20,
        'description': 'Ignores 50% of enemy defense.',
        'effects': [],
        'armor_penetration': 0.5
    },
    'pinning_shot': {
        'name': 'Pinning Shot',
        'cost': 20,
        'damage': 25,
        'toughness_damage': 15,
        'damage_type': 'physical',
        'ultimate_gain': 15,
        'description': 'Low damage but applies slow.',
        'effects': [{'status': 'slow', 'chance': 0.8}]
    },
    'purify': {
        'name': 'Purify',
        'cost': 25,
        'heal': 30,
        'ultimate_gain': 15,
        'description': 'Removes debuffs and grants regeneration.',
        'effects': [],
        'remove_debuffs': True,
        'self_effects': [{'status': 'regeneration', 'chance': 1.0}]
    },
    'imbue_weapon': {
        'name': 'Imbue Weapon',
        'cost': 20,
        'damage': 0,
        'ultimate_gain': 20,
        'description': 'Next 3 basic attacks deal extra magic damage.',
        'self_effects': [{'status': 'empower', 'chance': 1.0}]
    },
    'arcane_shield': {
        'name': 'Arcane Shield',
        'cost': 25,
        'damage': 0,
        'ultimate_gain': 15,
        'description': 'Creates shield and empowers attacks.',
        'self_effects': [
            {'status': 'fortify', 'chance': 1.0},
            {'status': 'empower', 'chance': 1.0}
        ]
    },
    'time_dilation': {
        'name': 'Time Dilation',
        'cost': 30,
        'damage': 20,
        'toughness_damage': 10,
        'damage_type': 'temporal',
        'ultimate_gain': 25,
        'description': 'Applies Stopwatch stack to enemy.',
        'effects': [{'status': 'stopwatch', 'chance': 1.0}],
        'classes': ['chrono_knight'],
        'required_items': {}
    },
    'temporal_shift': {
        'name': 'Temporal Shift',
        'cost': 20,
        'damage': 0,
        'ultimate_gain': 15,
        'description': 'Grants ally haste effect.',
        'self_effects': [{'status': 'haste', 'chance': 1.0}],
        'classes': ['chrono_knight'],
        'required_items': {}
    },
    # Warrior specific skills
    'berserker_fury': {
        'name': 'Berserker Fury',
        'cost': 25,
        'damage': 50,
        'toughness_damage': 20,
        'damage_type': 'physical',
        'ultimate_gain': 30,
        'description': 'Devastating attack that increases with missing health.',
        'effects': [],
        'classes': ['warrior'],
        'required_items': {}
    },
    # Archer specific skills
    'explosive_shot': {
        'name': 'Explosive Shot',
        'cost': 30,
        'damage': 45,
        'toughness_damage': 25,
        'damage_type': 'physical',
        'ultimate_gain': 25,
        'description': 'Ranged attack that deals area damage.',
        'effects': [{'status': 'burn', 'chance': 0.5}],
        'classes': ['archer'],
        'required_items': {'explosive_arrow': 1}
    },
    # Healer enhanced abilities
    'mass_heal': {
        'name': 'Mass Heal',
        'cost': 40,
        'heal': 80,
        'ultimate_gain': 20,
        'description': 'Powerful healing that affects entire party.',
        'effects': [],
        'classes': ['healer'],
        'required_items': {'holy_water': 1}
    },
    # Rogue stealth skills
    'vanish': {
        'name': 'Vanish',
        'cost': 25,
        'damage': 0,
        'ultimate_gain': 15,
        'description': 'Become invisible and gain massive crit chance.',
        'self_effects': [
            {'status': 'evade_up', 'chance': 1.0},
            {'status': 'crit_up', 'chance': 1.0}
        ],
        'classes': ['rogue'],
        'required_items': {'smoke_bomb': 1}
    }
}

# Ultimate abilities by class
ULTIMATE_ABILITIES = {
    'warrior': {
        'name': 'Blade Storm',
        'description': 'Unleashes a devastating series of strikes',
        'damage': 120,
        'toughness_damage': 50,
        'damage_type': 'physical'
    },
    'mage': {
        'name': 'Arcane Devastation',
        'description': 'Channels pure magical energy',
        'damage': 100,
        'toughness_damage': 60,
        'damage_type': 'quantum'
    },
    'rogue': {
        'name': 'Shadow Assassination',
        'description': 'Strikes from the shadows with lethal precision',
        'damage': 110,
        'toughness_damage': 40,
        'damage_type': 'physical'
    },
    'archer': {
        'name': 'Rain of Arrows',
        'description': 'Unleashes a devastating arrow barrage',
        'damage': 105,
        'toughness_damage': 35,
        'damage_type': 'physical'
    },
    'healer': {
        'name': 'Divine Intervention',
        'description': 'Calls upon divine power for massive healing',
        'heal': 150,
        'damage': 80,
        'toughness_damage': 30,
        'damage_type': 'divine'
    },
    'battlemage': {
        'name': 'Elemental Fury',
        'description': 'Combines magic and melee in perfect harmony',
        'damage': 115,
        'toughness_damage': 45,
        'damage_type': 'elemental'
    },
    'chrono_knight': {
        'name': 'Time Fracture',
        'description': 'Manipulates time to deal devastating damage',
        'damage': 130,
        'toughness_damage': 55,
        'damage_type': 'temporal'
    }
}

# Active combat sessions
active_combats = {}

class TacticalCombatView(discord.ui.View):
    """Enhanced combat view with tactical mechanics."""

    def __init__(self, player_id, monster_key, initial_message, rpg_core_cog):
        super().__init__(timeout=300)
        self.player_id = player_id
        self.monster_key = monster_key
        self.message = initial_message
        self.rpg_core = rpg_core_cog
        self.combat_log = []
        self.turn_count = 0

        # Load player data
        self.player_data = self.rpg_core.get_player_data(player_id)
        if not self.player_data:
            return

        # Initialize combat state with tactical elements
        monster_data = ENHANCED_MONSTERS.get(monster_key, ENHANCED_MONSTERS['goblin']).copy()

        self.combat_state = {
            'in_combat': True,
            'skill_points': 3,
            'max_skill_points': 5,
            'enemy': monster_data,
            'turn': 'player',
            'enemy_broken_turns': 0
        }

        self.add_log(f"⚔️ A wild **{monster_data['name']} {monster_data['emoji']}** appears!")
        self.add_log(f"🔍 Enemy weakness: {monster_data['weakness_type'].title()}")

    def add_log(self, text):
        """Add entry to combat log."""
        self.combat_log.append(f"• {text}")
        if len(self.combat_log) > 8:
            self.combat_log.pop(0)

    def create_bar(self, current, maximum, length=10, fill="█", empty="░"):
        """Create visual progress bar."""
        if maximum == 0:
            return empty * length
        percentage = current / maximum
        filled = int(percentage * length)
        empty_count = length - filled
        return fill * filled + empty * empty_count

    def create_sp_display(self):
        """Create skill points display."""
        sp = self.combat_state['skill_points']
        max_sp = self.combat_state['max_skill_points']
        filled = "💎" * sp
        empty = "▢" * (max_sp - sp)
        return f"{filled}{empty} ({sp}/{max_sp})"

    async def create_embed(self):
        """Generate comprehensive tactical combat embed."""
        enemy = self.combat_state['enemy']
        resources = self.player_data['resources']

        embed = discord.Embed(
            title=f"⚔️ Tactical Combat: {self.player_data.get('name', 'Player')} vs. {enemy['name']}", 
            color=COLORS['error']
        )

        # Skill Points display
        embed.add_field(
            name="💎 Skill Points",
            value=f"**SP:** {self.create_sp_display()}",
            inline=False
        )

        # Player status
        player_hp_bar = self.create_bar(resources['hp'], resources['max_hp'])
        ultimate_bar = self.create_bar(
            resources.get('ultimate_energy', 0), 
            100
        )

        embed.add_field(
            name=f"👤 {self.player_data.get('name', 'Player')}",
            value=f"❤️ **HP:** {resources['hp']}/{resources['max_hp']} {player_hp_bar}\n"
                  f"⚡ **Ultimate:** {ultimate_bar} ({resources.get('ultimate_energy', 0)}/100)",
            inline=True
        )

        # Enemy status with toughness
        enemy_hp_bar = self.create_bar(enemy['hp'], enemy['max_hp'])

        if enemy.get('is_broken', False):
            toughness_display = "💥 [ BROKEN ] 💥"
        else:
            toughness_bar = self.create_bar(enemy['toughness'], enemy['max_toughness'])
            toughness_display = f"🛡️ {enemy['toughness']}/{enemy['max_toughness']} {toughness_bar}"

        embed.add_field(
            name=f"{enemy['emoji']} {enemy['name']}",
            value=f"❤️ **HP:** {enemy['hp']}/{enemy['max_hp']} {enemy_hp_bar}\n"
                  f"{toughness_display}\n"
                  f"🔍 **Weakness:** {enemy['weakness_type'].title()}",
            inline=True
        )

        # Turn indicator
        turn_text = "🎯 **Your Turn**" if self.combat_state['turn'] == 'player' else "🔴 **Enemy Turn**"
        if enemy.get('is_broken', False):
            turn_text += " (Enemy Stunned!)"

        embed.add_field(name="Current Turn", value=f"{turn_text} | Turn {self.turn_count + 1}", inline=False)

        # Combat log
        if self.combat_log:
            log_content = "\n".join(self.combat_log[-6:])
            embed.add_field(name="📜 Combat Log", value=f"```{log_content}```", inline=False)

        return embed

    async def update_view(self):
        """Update combat display and button states."""
        enemy = self.combat_state['enemy']
        resources = self.player_data['resources']

        # Update button availability
        for item in self.children:
            if hasattr(item, 'label'):
                if item.label == "💥 ULTIMATE":
                    item.disabled = (
                        self.combat_state['turn'] != 'player' or
                        resources.get('ultimate_energy', 0) < 100 or
                        resources['hp'] <= 0 or
                        enemy['hp'] <= 0
                    )
                    item.style = discord.ButtonStyle.success if resources.get('ultimate_energy', 0) >= 100 else discord.ButtonStyle.secondary
                else:
                    item.disabled = (
                        self.combat_state['turn'] != 'player' or
                        resources['hp'] <= 0 or
                        enemy['hp'] <= 0
                    )

        embed = await self.create_embed()
        try:
            await self.message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException, discord.Forbidden) as e:
            logger.warning(f"Failed to update combat view: {e}")
            # Try to handle the error gracefully
            if hasattr(self, 'message') and hasattr(self.message, 'channel'):
                try:
                    await self.message.channel.send(f"⚠️ Combat display error - use `$profile` to check your status!")
                except:
                    pass

    async def check_weakness_break(self, damage_type, toughness_damage):
        """Check and handle weakness break mechanics."""
        enemy = self.combat_state['enemy']
        weakness_match = damage_type == enemy['weakness_type']

        if weakness_match and toughness_damage > 0:
            old_toughness = enemy['toughness']
            enemy['toughness'] = max(0, enemy['toughness'] - toughness_damage)
            self.add_log(f"💥 Weakness hit! Toughness damage: {toughness_damage}")

            # Check for break
            if old_toughness > 0 and enemy['toughness'] == 0:
                enemy['is_broken'] = True
                self.combat_state['enemy_broken_turns'] = 1
                self.add_log(f"🔥 WEAKNESS BREAK! {enemy['name']} is stunned!")
                return True

        return False

    async def end_combat(self, victory):
        """Handle combat conclusion with enhanced rewards."""
        self.player_data['in_combat'] = False
        enemy = self.combat_state['enemy']

        if victory:
            # Calculate rewards
            base_xp = enemy['xp_reward']
            base_gold = enemy['gold_reward']

            # Level multiplier
            level_mult = 1 + (self.player_data['level'] - 1) * 0.1
            xp_gained = int(base_xp * level_mult)
            gold_gained = int(base_gold * level_mult)

            self.player_data['xp'] += xp_gained
            self.player_data['gold'] += gold_gained

            # Loot drops
            loot_found = []
            for item_name, chance in enemy.get('loot_table', {}).items():
                if random.random() < chance:
                    if item_name in self.player_data['inventory']:
                        self.player_data['inventory'][item_name] += 1
                    else:
                        self.player_data['inventory'][item_name] = 1
                    loot_found.append(item_name)

            self.add_log(f"🏆 Victory! Gained {xp_gained} XP and {gold_gained} gold!")
            if loot_found:
                items_str = ", ".join([item.replace('_', ' ').title() for item in loot_found])
                self.add_log(f"💎 Found: {items_str}")

            # Check for level up
            levels_gained = self.rpg_core.level_up_check(self.player_data)
            if levels_gained:
                self.add_log(f"⭐ LEVEL UP! You are now level {self.player_data['level']}!")

            final_embed = discord.Embed(
                title="🏆 TACTICAL VICTORY! 🏆",
                description="\n".join(self.combat_log),
                color=COLORS['success']
            )
        else:
            # Defeat consequences
            gold_lost = max(1, int(self.player_data['gold'] * 0.15))
            self.player_data['gold'] = max(0, self.player_data['gold'] - gold_lost)
            self.player_data['resources']['hp'] = max(1, self.player_data['resources']['max_hp'] // 4)

            self.add_log(f"💀 Defeat! Lost {gold_lost} gold and most of your health.")

            final_embed = discord.Embed(
                title="☠️ TACTICAL DEFEAT ☠️",
                description="\n".join(self.combat_log),
                color=COLORS['error']
            )

        # Reset ultimate energy
        self.player_data['resources']['ultimate_energy'] = 0
        self.rpg_core.save_player_data(self.player_id, self.player_data)

        try:
            await self.message.edit(content="Combat concluded.", embed=final_embed, view=None)
        except discord.NotFound:
            pass

        if self.message.channel.id in active_combats:
            del active_combats[self.message.channel.id]
        self.stop()

    async def monster_turn(self):
        """Enhanced monster AI."""
        enemy = self.combat_state['enemy']

        # Check if broken/stunned
        if enemy.get('is_broken', False):
            if self.combat_state['enemy_broken_turns'] > 0:
                self.add_log(f"💫 {enemy['name']} is stunned and skips their turn!")
                self.combat_state['enemy_broken_turns'] -= 1

                if self.combat_state['enemy_broken_turns'] <= 0:
                    enemy['is_broken'] = False
                    enemy['toughness'] = enemy['max_toughness']
                    self.add_log(f"🛡️ {enemy['name']} recovers!")

                self.combat_state['turn'] = 'player'
                await self.update_view()
                return

        # Monster attacks
        damage = random.randint(enemy['attack'] - 5, enemy['attack'] + 10)
        self.player_data['resources']['hp'] = max(0, self.player_data['resources']['hp'] - damage)
        self.add_log(f"{enemy['name']} attacks for {damage} damage!")

        self.combat_state['turn'] = 'player'
        self.turn_count += 1
        await self.update_view()

        # Check for player defeat
        if self.player_data['resources']['hp'] <= 0:
            await self.end_combat(victory=False)

    def get_available_skills(self):
        """Get skills available to the player's class with inventory checking."""
        player_class = self.player_data.get('class', 'warrior')
        player_level = self.player_data.get('level', 1)
        
        available_skills = []
        
        # Check all skills for class compatibility
        for skill_key, skill_data in TACTICAL_SKILLS.items():
            # Check class restriction
            allowed_classes = skill_data.get('classes', [])
            if player_class not in allowed_classes:
                continue
                
            # Check level requirement
            min_level = skill_data.get('min_level', 1)
            if player_level < min_level:
                continue
                
            # Add to available skills (inventory check happens in dropdown)
            available_skills.append(skill_key)
        
        # Ensure at least basic attack is available
        if not available_skills:
            available_skills = ['power_strike']
            
        return available_skills

    def apply_status_effect(self, target, effect_name, duration_override=None):
        """Apply a status effect to target (player or enemy)."""
        if effect_name not in STATUS_EFFECTS:
            return False

        effect_data = STATUS_EFFECTS[effect_name].copy()
        if duration_override:
            effect_data['duration'] = duration_override

        if 'active_effects' not in target:
            target['active_effects'] = {}

        # Handle stacking effects like Stopwatch
        if effect_name == 'stopwatch':
            if effect_name in target['active_effects']:
                target['active_effects'][effect_name]['stacks'] += 1
                if target['active_effects'][effect_name]['stacks'] >= 3:
                    # Trigger stun and remove stopwatch
                    self.apply_status_effect(target, 'stun', 1)
                    del target['active_effects'][effect_name]
                    self.add_log(f"💥 Stopwatch triggered! Stunning target!")
            else:
                effect_data['stacks'] = 1
                target['active_effects'][effect_name] = effect_data
        else:
            target['active_effects'][effect_name] = effect_data

        return True

    def process_status_effects(self, target, is_player=False):
        """Process all active status effects on a target."""
        if 'active_effects' not in target:
            return

        effects_to_remove = []

        for effect_name, effect_data in target['active_effects'].items():
            effect_type = effect_data.get('effect')

            # Process effect based on type
            if effect_type == 'damage_over_time':
                damage = int(target['max_hp'] * effect_data['value'])
                target['hp'] = max(0, target['hp'] - damage)
                self.add_log(f"🩸 {effect_data['name']}: {damage} damage")

            elif effect_type == 'heal_over_time':
                heal = int(target['max_hp'] * effect_data['value'])
                target['hp'] = min(target['max_hp'], target['hp'] + heal)
                self.add_log(f"💚 {effect_data['name']}: {heal} healing")

            elif effect_type == 'skip_turn' and effect_data['duration'] > 0:
                if is_player:
                    self.add_log(f"🌟 You are stunned and skip your turn!")
                else:
                    self.add_log(f"🌟 Enemy is stunned and skips their turn!")

            # Reduce duration
            effect_data['duration'] -= 1
            if effect_data['duration'] <= 0:
                effects_to_remove.append(effect_name)

        # Remove expired effects
        for effect_name in effects_to_remove:
            del target['active_effects'][effect_name]

    # Combat buttons
    @discord.ui.button(label="⚔️ Basic Attack", style=discord.ButtonStyle.secondary, emoji="⚔️")
    async def basic_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your combat!", ephemeral=True)
            return

        await interaction.response.defer()

        # Basic attack generates SP and ultimate energy
        base_damage = 20 + self.player_data['derived_stats']['attack'] // 2
        damage = random.randint(base_damage - 5, base_damage + 8)

        # Check for critical hit
        crit_chance = self.player_data['derived_stats'].get('critical_chance', 0.05)
        is_critical = random.random() < crit_chance

        if is_critical:
            damage = int(damage * 1.5)
            self.add_log(f"💥 CRITICAL HIT! (150% damage)")

        # Generate SP
        sp_gained = min(10, self.combat_state['max_skill_points'] - self.combat_state['skill_points'])
        self.combat_state['skill_points'] += sp_gained

        # Generate ultimate energy
        ultimate_gain = 10
        old_ultimate = self.player_data['resources'].get('ultimate_energy', 0)
        self.player_data['resources']['ultimate_energy'] = min(100, old_ultimate + ultimate_gain)

        # Check for weakness (basic attacks are physical)
        enemy = self.combat_state['enemy']
        if enemy['weakness_type'] == 'physical':
            toughness_damage = 10
            await self.check_weakness_break('physical', toughness_damage)

        # Apply damage multiplier if enemy is broken
        if enemy.get('is_broken', False):
            damage = int(damage * 1.3)
            self.add_log(f"💥 Bonus damage on broken enemy!")

        enemy['hp'] = max(0, enemy['hp'] - damage)

        log_msg = f"⚔️ Basic Attack! Dealt {damage} damage"
        if sp_gained > 0:
            log_msg += f", gained {sp_gained} SP"
        log_msg += f", gained {ultimate_gain} UE!"

        self.add_log(log_msg)

        self.combat_state['turn'] = 'monster'
        await self.update_view()
        await asyncio.sleep(1.5)

        if enemy['hp'] <= 0:
            await self.end_combat(victory=True)
            return

        await self.monster_turn()

    @discord.ui.button(label="✨ Skills", style=discord.ButtonStyle.primary, emoji="✨")
    async def skills_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your combat!", ephemeral=True)
            return

        available_skills = self.get_available_skills()
        if not available_skills:
            await interaction.response.send_message("❌ No skills available!", ephemeral=True)
            return

        # Create skill dropdown
        options = []
        for skill_key in available_skills:
            if skill_key in TACTICAL_SKILLS:
                skill_data = TACTICAL_SKILLS[skill_key]
                can_afford = self.combat_state['skill_points'] >= skill_data['cost']
                emoji = "✅" if can_afford else "❌"

                options.append(discord.SelectOption(
                    label=f"{skill_data['name']} ({skill_data['cost']} SP)",
                    value=skill_key,
                    description=skill_data['description'][:100],
                    emoji=emoji
                ))

        if not options:
            await interaction.response.send_message("❌ No skills available!", ephemeral=True)
            return

        view = SkillSelectionView(self, available_skills)
        await interaction.response.send_message("Select a skill to use:", view=view, ephemeral=True)

    @discord.ui.button(label="💥 ULTIMATE", style=discord.ButtonStyle.secondary, emoji="💥")
    async def ultimate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your combat!", ephemeral=True)
            return

        # Check if ultimate is ready
        if self.player_data['resources'].get('ultimate_energy', 0) < 100:
            await interaction.response.send_message("❌ Ultimate not ready!", ephemeral=True)
            return

        await interaction.response.defer()

        # Get ultimate based on class
        player_class = self.player_data.get('class', 'warrior')
        ultimate_data = ULTIMATE_ABILITIES.get(player_class, ULTIMATE_ABILITIES['warrior'])

        # Consume ultimate energy
        self.player_data['resources']['ultimate_energy'] = 0

        enemy = self.combat_state['enemy']

        # Calculate ultimate damage
        if 'damage' in ultimate_data:
            base_damage = ultimate_data['damage']
            damage = random.randint(base_damage - 10, base_damage + 20)

            # Check for weakness break
            toughness_damage = ultimate_data.get('toughness_damage', 30)
            damage_type = ultimate_data.get('damage_type', 'physical')
            await self.check_weakness_break(damage_type, toughness_damage)

            # Apply damage multiplier if enemy is broken
            if enemy.get('is_broken', False):
                damage = int(damage * 1.8)
                self.add_log(f"💥 Massive bonus damage on broken enemy!")

            enemy['hp'] = max(0, enemy['hp'] - damage)
            self.add_log(f"🌟 ULTIMATE: {ultimate_data['name']}!")
            self.add_log(f"💥 Dealt {damage} {damage_type} damage!")

        # Healing ultimates
        if 'heal' in ultimate_data:
            heal_amount = ultimate_data['heal']
            old_hp = self.player_data['resources']['hp']
            self.player_data['resources']['hp'] = min(
                self.player_data['resources']['max_hp'],
                old_hp + heal_amount
            )
            actual_heal = self.player_data['resources']['hp'] - old_hp
            self.add_log(f"✨ Healed {actual_heal} HP!")

        await self.update_view()

        if enemy['hp'] <= 0:
            await self.end_combat(victory=True)
            return

    async def use_skill(self, interaction, skill_key):
        """Execute a skill during combat."""
        if skill_key not in TACTICAL_SKILLS:
            await interaction.response.send_message("❌ Invalid skill!", ephemeral=True)
            return

        skill_data = TACTICAL_SKILLS[skill_key]

        # Check SP cost
        if self.combat_state['skill_points'] < skill_data['cost']:
            await interaction.response.send_message(f"❌ Not enough SP! Need {skill_data['cost']} SP.", ephemeral=True)
            return

        await interaction.response.defer()

        # Consume SP
        self.combat_state['skill_points'] -= skill_data['cost']

        enemy = self.combat_state['enemy']

        # Apply damage if skill has damage
        if skill_data.get('damage', 0) > 0:
            base_damage = skill_data['damage'] + self.player_data['derived_stats']['attack'] // 2
            damage = random.randint(base_damage - 5, base_damage + 10)

            # Apply armor penetration if skill has it
            if skill_data.get('armor_penetration', 0) > 0:
                self.add_log(f"🔓 Armor penetration: {int(skill_data['armor_penetration']*100)}%")

            # Check for weakness break
            toughness_damage = skill_data.get('toughness_damage', 0)
            damage_type = skill_data.get('damage_type', 'physical')
            if toughness_damage > 0:
                await self.check_weakness_break(damage_type, toughness_damage)

            # Apply damage multiplier if enemy is broken
            if enemy.get('is_broken', False):
                damage = int(damage * 1.5)
                self.add_log(f"💥 Bonus damage on broken enemy!")

            enemy['hp'] = max(0, enemy['hp'] - damage)
            self.add_log(f"✨ {skill_data['name']}! Dealt {damage} {damage_type} damage!")

            # Apply status effects to enemy
            for effect in skill_data.get('effects', []):
                if random.random() < effect['chance']:
                    self.apply_status_effect(enemy, effect['status'])
                    effect_name = STATUS_EFFECTS[effect['status']]['name']
                    self.add_log(f"🌟 Applied {effect_name} to enemy!")

        # Apply healing if skill has healing
        if skill_data.get('heal', 0) > 0:
            heal_amount = skill_data['heal']
            old_hp = self.player_data['resources']['hp']
            self.player_data['resources']['hp'] = min(
                self.player_data['resources']['max_hp'],
                old_hp + heal_amount
            )
            actual_heal = self.player_data['resources']['hp'] - old_hp
            self.add_log(f"❤️ Healed {actual_heal} HP!")

        # Apply self-effects (buffs to player)
        for effect in skill_data.get('self_effects', []):
            if random.random() < effect['chance']:
                self.apply_status_effect(self.player_data, effect['status'])
                effect_name = STATUS_EFFECTS[effect['status']]['name']
                self.add_log(f"✨ Gained {effect_name}!")

        # Remove debuffs if skill has that ability
        if skill_data.get('remove_debuffs', False):
            if 'active_effects' in self.player_data:
                removed_effects = []
                for effect_name in list(self.player_data['active_effects'].keys()):
                    if STATUS_EFFECTS[effect_name]['type'] == 'curse':
                        del self.player_data['active_effects'][effect_name]
                        removed_effects.append(effect_name)
                if removed_effects:
                    self.add_log(f"✨ Removed debuffs: {', '.join(removed_effects)}")

        # Grant ultimate energy
        ultimate_gain = skill_data.get('ultimate_gain', 0)
        old_ultimate = self.player_data['resources'].get('ultimate_energy', 0)
        self.player_data['resources']['ultimate_energy'] = min(100, old_ultimate + ultimate_gain)

        self.combat_state['turn'] = 'monster'
        await self.update_view()
        await asyncio.sleep(1.5)

        if enemy['hp'] <= 0:
            await self.end_combat(victory=True)
            return

        await self.monster_turn()

    @discord.ui.button(label="🎒 Use Item", style=discord.ButtonStyle.success, emoji="🎒")
    async def use_item_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your combat!", ephemeral=True)
            return

        # Get consumable items from inventory
        consumable_items = {}
        for item_key, quantity in self.player_data.get('inventory', {}).items():
            if item_key in ITEMS and ITEMS[item_key].get('type') == 'consumable' and quantity > 0:
                consumable_items[item_key] = quantity

        if not consumable_items:
            await interaction.response.send_message("❌ No consumable items available!", ephemeral=True)
            return

        view = ItemSelectionView(self, consumable_items)
        await interaction.response.send_message("Select an item to use:", view=view, ephemeral=True)

    @discord.ui.button(label="❓ Analyze", style=discord.ButtonStyle.secondary, emoji="❓")
    async def analyze_enemy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your combat!", ephemeral=True)
            return

        enemy = self.combat_state['enemy']

        embed = discord.Embed(
            title=f"🔍 Analysis: {enemy['name']}",
            color=COLORS['info']
        )

        embed.add_field(
            name="📊 Stats",
            value=f"**HP:** {enemy['hp']}/{enemy['max_hp']}\n"
                  f"**Attack:** {enemy['attack']}\n"
                  f"**Defense:** {enemy['defense']}\n"
                  f"**Level:** {enemy['level']}",
            inline=True
        )

        embed.add_field(
            name="🎯 Weakness",
            value=f"**Weak to:** {enemy['weakness_type'].title()}\n"
                  f"*Deal bonus toughness damage with {enemy['weakness_type']} attacks*",
            inline=True
        )

        # Show active effects
        if enemy.get('active_effects'):
            effects_text = []
            for effect_name, effect_data in enemy['active_effects'].items():
                emoji = STATUS_EFFECTS[effect_name]['emoji']
                duration = effect_data['duration']
                effects_text.append(f"{emoji} {effect_data['name']} ({duration})")

            embed.add_field(
                name="🌟 Active Effects",
                value="\n".join(effects_text) if effects_text else "None",
                inline=False
            )

        embed.add_field(
            name="💡 Plagg's Analysis",
            value=f"*\"This {enemy['name']} looks about as threatening as yesterday's cheese. "
                  f"Hit it with {enemy['weakness_type']} attacks to break its toughness. "
                  f"Or don't, I'm not your boss.\"*",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🏃 Flee", style=discord.ButtonStyle.secondary, emoji="🏃")
    async def flee(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your combat!", ephemeral=True)
            return

        await interaction.response.defer()

        # Flee always succeeds but has consequences
        self.add_log("🏃 You fled from combat!")
        self.player_data['in_combat'] = False
        self.player_data['resources']['ultimate_energy'] = 0
        self.rpg_core.save_player_data(self.player_id, self.player_data)

        embed = await self.create_embed()
        embed.title = "🏃 Fled from Combat"
        embed.color = COLORS['warning']

        try:
            await self.message.edit(content="You escaped!", embed=embed, view=None)
        except discord.NotFound:
            pass

        if self.message.channel.id in active_combats:
            del active_combats[self.message.channel.id]
        self.stop()

    def use_consumable_item(self, item_key):
        """Use a consumable item and apply its effects with detailed feedback."""
        from rpg_data.game_data import ITEMS
        from utils.helpers import format_number

        item_data = ITEMS.get(item_key, {})
        if item_data.get('type') != 'consumable':
            return "❌ Item cannot be consumed!"

        # Check if item exists in inventory
        inventory = self.player_data.get('inventory', {})
        if inventory.get(item_key, 0) <= 0:
            return "❌ Item not found in inventory!"

        # Remove item from inventory
        self.player_data['inventory'][item_key] -= 1
        if self.player_data['inventory'][item_key] <= 0:
            del self.player_data['inventory'][item_key]

        results = []

        # Apply item effects with enhanced feedback
        if item_data.get('heal_amount'):
            heal = item_data['heal_amount']
            old_hp = self.player_data['resources']['hp']
            max_hp = self.player_data['resources']['max_hp']
            
            # Apply class bonuses for healers
            if self.player_data.get('class') == 'healer':
                heal = int(heal * 1.25)  # 25% bonus healing
                results.append("✨ Healer class bonus: +25% healing!")
            
            self.player_data['resources']['hp'] = min(old_hp + heal, max_hp)
            actual_heal = self.player_data['resources']['hp'] - old_hp
            results.append(f"❤️ Restored {actual_heal} HP ({self.player_data['resources']['hp']}/{max_hp})")

        if item_data.get('mana_amount'):
            restore = item_data['mana_amount']
            
            # Apply class bonuses for mages
            if self.player_data.get('class') == 'mage':
                restore = int(restore * 1.3)  # 30% bonus mana restoration
                results.append("🔮 Mage class bonus: +30% mana restoration!")
            
            # Initialize mana if needed
            if 'mana' not in self.player_data['resources']:
                self.player_data['resources']['mana'] = self.player_data.get('derived_stats', {}).get('max_mana', 100)
            
            old_mana = self.player_data['resources']['mana']
            max_mana = self.player_data.get('derived_stats', {}).get('max_mana', 100)
            self.player_data['resources']['mana'] = min(old_mana + restore, max_mana)
            actual_restore = self.player_data['resources']['mana'] - old_mana
            results.append(f"💙 Restored {actual_restore} Mana ({self.player_data['resources']['mana']}/{max_mana})")

        # Combat-specific effects
        if item_data.get('effects'):
            for effect in item_data['effects']:
                if effect == 'remove_debuffs':
                    if 'active_effects' in self.player_data:
                        removed = []
                        for effect_name in list(self.player_data['active_effects'].keys()):
                            if STATUS_EFFECTS.get(effect_name, {}).get('type') == 'curse':
                                del self.player_data['active_effects'][effect_name]
                                removed.append(effect_name)
                        if removed:
                            results.append(f"✨ Removed debuffs: {', '.join(removed)}")
                
                elif effect == 'temporary_boost':
                    # Apply temporary combat bonuses
                    self.apply_status_effect(self.player_data, 'empower')
                    results.append("⚡ Gained temporary power boost!")
                
                elif effect == 'ultimate_energy':
                    energy_gain = item_data.get('ultimate_energy', 25)
                    old_energy = self.player_data['resources'].get('ultimate_energy', 0)
                    self.player_data['resources']['ultimate_energy'] = min(100, old_energy + energy_gain)
                    actual_gain = self.player_data['resources']['ultimate_energy'] - old_energy
                    results.append(f"⚡ Gained {actual_gain} Ultimate Energy!")

        # Special cheese handling
        if 'cheese' in item_key.lower():
            # Plagg is excited about cheese!
            cheese_bonus = random.randint(10, 25)
            old_hp = self.player_data['resources']['hp']
            max_hp = self.player_data['resources']['max_hp']
            self.player_data['resources']['hp'] = min(old_hp + cheese_bonus, max_hp)
            actual_heal = self.player_data['resources']['hp'] - old_hp
            results.append(f"🧀 CHEESE POWER! Plagg grants extra {actual_heal} HP!")
            
            # Also gain some ultimate energy
            old_energy = self.player_data['resources'].get('ultimate_energy', 0)
            self.player_data['resources']['ultimate_energy'] = min(100, old_energy + 15)
            results.append("🧀 Plagg's joy gives +15 Ultimate Energy!")

        # Default message if no specific effects
        if not results:
            results.append(f"✨ {item_data.get('name', 'Item')} consumed!")

        return '\n'.join(results)

class SkillSelectionView(discord.ui.View):
    """Dropdown view for selecting skills during combat."""
    
    def __init__(self, combat_view, available_skills):
        super().__init__(timeout=60)  # Increased timeout
        self.combat_view = combat_view
        self.available_skills = available_skills
        
        # Create skill dropdown
        self.add_item(SkillDropdown(combat_view, available_skills))
    
    async def on_timeout(self):
        """Handle view timeout gracefully."""
        try:
            # Disable all items and update view
            for item in self.children:
                item.disabled = True
            
            # Don't try to edit the message if it might not exist
            pass
        except Exception as e:
            logger.error(f"Error handling SkillSelectionView timeout: {e}")

class SkillDropdown(discord.ui.Select):
    """Dropdown for skill selection."""
    
    def __init__(self, combat_view, available_skills):
        self.combat_view = combat_view
        
        options = []
        for skill_key in available_skills:
            if skill_key in TACTICAL_SKILLS:
                skill_data = TACTICAL_SKILLS[skill_key]
                can_afford = combat_view.combat_state['skill_points'] >= skill_data['cost']
                emoji = "✅" if can_afford else "❌"
                
                # Check inventory requirements
                inventory_check = self.check_skill_requirements(skill_key, combat_view.player_data)
                if not inventory_check['can_use']:
                    emoji = "🚫"
                    description = f"Missing: {inventory_check['missing']}"
                else:
                    description = skill_data['description'][:100]

                options.append(discord.SelectOption(
                    label=f"{skill_data['name']} ({skill_data['cost']} SP)",
                    value=skill_key,
                    description=description,
                    emoji=emoji
                ))

        super().__init__(
            placeholder="Choose a skill to use...",
            options=options if options else [discord.SelectOption(label="No skills", value="none")]
        )

    def check_skill_requirements(self, skill_key, player_data):
        """Check if player meets skill requirements including inventory items."""
        skill_data = TACTICAL_SKILLS.get(skill_key, {})
        inventory = player_data.get('inventory', {})
        
        # Check for required items (some skills might need components)
        required_items = skill_data.get('required_items', {})
        missing_items = []
        
        for item_key, needed_amount in required_items.items():
            if inventory.get(item_key, 0) < needed_amount:
                missing_items.append(f"{ITEMS.get(item_key, {}).get('name', item_key)} x{needed_amount}")
        
        return {
            'can_use': len(missing_items) == 0,
            'missing': ', '.join(missing_items) if missing_items else ''
        }

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.combat_view.player_id:
            await interaction.response.send_message("Not your combat!", ephemeral=True)
            return
            
        if self.values[0] == "none":
            await interaction.response.defer()
            return
            
        # Check requirements again before use
        inventory_check = self.check_skill_requirements(self.values[0], self.combat_view.player_data)
        if not inventory_check['can_use']:
            await interaction.response.send_message(f"❌ Cannot use skill: {inventory_check['missing']}", ephemeral=True)
            return
            
        await self.combat_view.use_skill(interaction, self.values[0])

class ItemSelectionView(discord.ui.View):
    """Dropdown view for selecting consumable items during combat."""
    
    def __init__(self, combat_view, consumable_items):
        super().__init__(timeout=60)  # Increased timeout
        self.combat_view = combat_view
        self.consumable_items = consumable_items
        
        # Create item dropdown
        self.add_item(ItemDropdown(combat_view, consumable_items))
    
    async def on_timeout(self):
        """Handle view timeout gracefully."""
        try:
            # Disable all items
            for item in self.children:
                item.disabled = True
        except Exception as e:
            logger.error(f"Error handling ItemSelectionView timeout: {e}")

class ItemDropdown(discord.ui.Select):
    """Dropdown for item selection."""
    
    def __init__(self, combat_view, consumable_items):
        self.combat_view = combat_view
        
        options = []
        for item_key, quantity in consumable_items.items():
            item_data = ITEMS.get(item_key, {})
            item_name = item_data.get('name', item_key.replace('_', ' ').title())
            
            # Show healing amount or effect
            effect_preview = ""
            if item_data.get('heal_amount'):
                effect_preview = f" (+{item_data['heal_amount']} HP)"
            elif item_data.get('mana_amount'):
                effect_preview = f" (+{item_data['mana_amount']} MP)"
            
            options.append(discord.SelectOption(
                label=f"{item_name} x{quantity}",
                value=item_key,
                description=f"{item_data.get('description', 'Consumable item')}{effect_preview}"[:100],
                emoji="🧪"
            ))

        super().__init__(
            placeholder="Select an item to use...",
            options=options if options else [discord.SelectOption(label="No items", value="none")]
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.combat_view.player_id:
            await interaction.response.send_message("Not your combat!", ephemeral=True)
            return
            
        if self.values[0] == "none":
            await interaction.response.defer()
            return
            
        # Use the item and provide feedback
        item_key = self.values[0]
        item_data = ITEMS.get(item_key, {})
        item_name = item_data.get('name', item_key.replace('_', ' ').title())
        
        # Check if item still exists
        inventory = self.combat_view.player_data.get('inventory', {})
        if inventory.get(item_key, 0) <= 0:
            await interaction.response.send_message("❌ Item no longer available!", ephemeral=True)
            return
            
        # Process item usage
        result = self.combat_view.use_consumable_item(item_key)
        
        self.combat_view.add_log(f"🧪 Used {item_name}!")
        if result:
            self.combat_view.add_log(result)
        
        # Save player data
        self.combat_view.rpg_core.save_player_data(self.combat_view.player_id, self.combat_view.player_data)
        
        # Update the combat view
        await self.combat_view.update_view()
        await interaction.response.send_message(f"✅ Used **{item_name}**!", ephemeral=True)

class RPGCombat(commands.Cog):
    """Enhanced RPG combat system with tactical mechanics."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="battle", aliases=["fight", "combat"])
    async def battle(self, ctx, monster_name: str = None):
        """Initiate tactical combat with enhanced mechanics."""
        if not is_module_enabled("rpg", ctx.guild.id):
            return

        rpg_core = self.bot.get_cog('RPGCore')
        if not rpg_core:
            await ctx.send("❌ RPG system not loaded.")
            return

        player_data = rpg_core.get_player_data(ctx.author.id)
        if not player_data:
            embed = create_embed("No Character", "Use `$startrpg` first!", COLORS['error'])
            await ctx.send(embed=embed)
            return

        if player_data.get('in_combat') or ctx.channel.id in active_combats:
            embed = create_embed("Already Fighting", "Finish your current battle first!", COLORS['warning'])
            await ctx.send(embed=embed)
            return

        if player_data['resources']['hp'] <= 0:
            embed = create_embed("No Health", "You need to heal first! Use a health potion.", COLORS['error'])
            await ctx.send(embed=embed)
            return

        # Select monster
        if monster_name:
            monster_key = monster_name.lower().replace(' ', '_')
            if monster_key not in ENHANCED_MONSTERS:
                available = ", ".join(ENHANCED_MONSTERS.keys())
                embed = create_embed("Monster Not Found", f"Available: {available}", COLORS['error'])
                await ctx.send(embed=embed)
                return
        else:
            # Level-appropriate random monster
            level = player_data.get('level', 1)
            if level >= 10:
                available_monsters = list(ENHANCED_MONSTERS.keys())
            elif level >= 5:
                available_monsters = ['goblin', 'orc', 'ice_elemental']
            else:
                available_monsters = ['goblin']

            monster_key = random.choice(available_monsters)

        # Start tactical combat
        player_data['in_combat'] = True
        rpg_core.save_player_data(ctx.author.id, player_data)

        embed = discord.Embed(
            title="⚔️ Tactical Combat Initiated!", 
            description="Preparing for enhanced battle...", 
            color=COLORS['primary']
        )
        message = await ctx.send(embed=embed)

        await asyncio.sleep(1)

        view = TacticalCombatView(ctx.author.id, monster_key, message, rpg_core)
        active_combats[ctx.channel.id] = view

        await view.update_view()

async def setup(bot):
    await bot.add_cog(RPGCombat(bot))