
import discord
from discord.ext import commands
from replit import db
import random
import asyncio
from datetime import datetime
from rpg_data.game_data import TACTICAL_MONSTERS, ITEMS
from utils.helpers import create_embed, format_number
from config import COLORS, is_module_enabled
import logging

logger = logging.getLogger(__name__)

# Plagg's Scenario Library for Dynamic Dungeon Generation
MONSTER_SCENARIOS = [
    {
        'name': 'Ambush',
        'description': "You enter a room and—surprise!—a bunch of Shadow Grubs drop from the ceiling. They look squishy. And definitely not like cheese. What do you do?",
        'choices': [
            {'text': '⚔️ Attack them head-on!', 'type': 'combat', 'difficulty': 'easy'},
            {'text': '🛡️ Defensive stance', 'type': 'defense', 'bonus': 'damage_reduction'},
            {'text': '💨 Quick dodge roll', 'type': 'skill_check', 'stat': 'dexterity'},
            {'text': '🧀 Throw cheese as distraction', 'type': 'cheese_option', 'requires': 'cheese'}
        ]
    },
    {
        'name': 'Sleeping Giant',
        'description': "There's a massive Stone Golem snoozing in the middle of the room. You could probably sneak past it... unless you're as clumsy as Adrien. Your call.",
        'choices': [
            {'text': '👻 Sneak past quietly', 'type': 'skill_check', 'stat': 'dexterity'},
            {'text': '⚔️ Wake it up for a fight', 'type': 'combat', 'difficulty': 'hard'},
            {'text': '🔍 Search room while it sleeps', 'type': 'treasure', 'bonus': 'stealth_bonus'},
            {'text': '🧀 Leave cheese offering', 'type': 'cheese_option', 'requires': 'cheese'}
        ]
    },
    {
        'name': 'Patrol Guards',
        'description': "You hear footsteps. A squad of grim-looking Akuma Sentinels is marching your way. Hiding seems smart. Fighting seems like a lot of work.",
        'choices': [
            {'text': '🫥 Hide in shadows', 'type': 'skill_check', 'stat': 'dexterity'},
            {'text': '⚔️ Fight the patrol', 'type': 'combat', 'difficulty': 'medium'},
            {'text': '🗣️ Try to bluff past them', 'type': 'skill_check', 'stat': 'charisma'},
            {'text': '💥 Use Cataclysm!', 'type': 'ultimate_ability', 'class': 'destruction'}
        ]
    },
    {
        'name': 'Rare Elite',
        'description': "Whoa, look at that one! A 'Glimmering Slime' is jiggling in the corner. I bet it drops something shiny. Or maybe it's just... slimy. 50/50 shot.",
        'choices': [
            {'text': '⚔️ Attack the elite monster', 'type': 'combat', 'difficulty': 'elite'},
            {'text': '🧪 Try to capture essence', 'type': 'skill_check', 'stat': 'intelligence'},
            {'text': '🎣 Lure it into a trap', 'type': 'skill_check', 'stat': 'wisdom'},
            {'text': '🧀 Offer it fancy cheese', 'type': 'cheese_option', 'requires': 'rare_cheese'}
        ]
    }
]

TREASURE_SCENARIOS = [
    {
        'name': 'Standard Chest',
        'description': "Ooh, a treasure chest! It's probably full of gold or whatever. Now, if it were a CHEESE chest, I'd be impressed. Are you going to open it or just stare?",
        'choices': [
            {'text': '🔓 Open the chest', 'type': 'treasure', 'reward': 'standard'},
            {'text': '🔍 Check for traps first', 'type': 'skill_check', 'stat': 'wisdom'},
            {'text': '💥 Blast it open with magic', 'type': 'skill_check', 'stat': 'intelligence'},
            {'text': '🧀 Hope there\'s cheese inside', 'type': 'cheese_hope', 'special': True}
        ]
    },
    {
        'name': 'Suspicious Mimic',
        'description': "Hey, another chest! This one looks... toothier? It's probably fine. Go on, poke it.",
        'choices': [
            {'text': '👆 Poke the chest', 'type': 'combat', 'difficulty': 'mimic'},
            {'text': '🏹 Attack from range', 'type': 'combat', 'difficulty': 'mimic', 'bonus': 'first_strike'},
            {'text': '🧀 Offer it cheese to calm it', 'type': 'cheese_option', 'requires': 'cheese'},
            {'text': '🚪 Back away slowly', 'type': 'avoidance', 'safe': True}
        ]
    },
    {
        'name': 'Offering Fountain',
        'description': "You find a fountain with glowing water. A sign reads, 'Offer a coin for a blessing.' Or you could just drink it. I wouldn't, but you do you.",
        'choices': [
            {'text': '🪙 Offer a gold coin', 'type': 'blessing', 'cost': 100, 'reward': 'random_buff'},
            {'text': '🥤 Drink the glowing water', 'type': 'random_effect', 'risky': True},
            {'text': '💎 Offer something valuable', 'type': 'blessing', 'cost': 'item', 'reward': 'major_buff'},
            {'text': '🧀 Offer premium cheese', 'type': 'cheese_option', 'requires': 'premium_cheese'}
        ]
    },
    {
        'name': 'Hidden Cache',
        'description': "One of the walls looks crumbly. You could probably break it down. Sounds like effort, but there might be good stuff behind it. Or just more rocks.",
        'choices': [
            {'text': '👊 Punch through the wall', 'type': 'skill_check', 'stat': 'strength'},
            {'text': '🔨 Use tools to break it', 'type': 'treasure', 'requires': 'tools'},
            {'text': '💥 Magic missile the wall', 'type': 'skill_check', 'stat': 'intelligence'},
            {'text': '💥 Cataclysm!', 'type': 'ultimate_ability', 'guaranteed': True}
        ]
    }
]

TRAP_SCENARIOS = [
    {
        'name': 'Pressure Plates',
        'description': "The floor is covered in pressure plates. Classic. One wrong step and... well, I'm sure it'll be hilarious. You could try to disarm them, I guess.",
        'choices': [
            {'text': '👻 Carefully navigate around', 'type': 'skill_check', 'stat': 'dexterity'},
            {'text': '🔧 Try to disarm the traps', 'type': 'skill_check', 'stat': 'intelligence'},
            {'text': '🏃 Sprint across quickly', 'type': 'risky_run', 'damage_on_fail': 20},
            {'text': '🧀 Throw cheese to test plates', 'type': 'cheese_option', 'requires': 'cheese'}
        ]
    },
    {
        'name': 'Swinging Blades',
        'description': "Giant axe pendulums are swinging across the room. You'll have to time your run perfectly. Don't worry, I'll be watching... and judging.",
        'choices': [
            {'text': '⏰ Time your run perfectly', 'type': 'skill_check', 'stat': 'dexterity'},
            {'text': '🛡️ Tank through with shield up', 'type': 'skill_check', 'stat': 'constitution'},
            {'text': '🔥 Melt the blade mechanisms', 'type': 'skill_check', 'stat': 'intelligence'},
            {'text': '🧀 Distract yourself with cheese thoughts', 'type': 'cheese_meditation', 'special': True}
        ]
    },
    {
        'name': 'Rune Puzzle Door',
        'description': "A big door is covered in glowing runes. To open it, you have to press them in the right sequence. Or you could just try to smash it down with 'Cataclysm!'... Oh, wait, that's MY job.",
        'choices': [
            {'text': '🧩 Solve the rune puzzle', 'type': 'skill_check', 'stat': 'intelligence'},
            {'text': '💪 Try to force the door open', 'type': 'skill_check', 'stat': 'strength'},
            {'text': '🔍 Look for hidden switches', 'type': 'skill_check', 'stat': 'wisdom'},
            {'text': '💥 Ask Plagg to Cataclysm it', 'type': 'plagg_help', 'cheese_cost': 'premium'}
        ]
    },
    {
        'name': 'Gas Chamber',
        'description': "The room starts filling with a weird green gas. It smells like old socks, not Camembert. You should probably find a way out, like, yesterday.",
        'choices': [
            {'text': '🏃 Run for the exit', 'type': 'quick_escape', 'time_pressure': True},
            {'text': '🤧 Hold breath and search', 'type': 'skill_check', 'stat': 'constitution'},
            {'text': '💨 Create air current with magic', 'type': 'skill_check', 'stat': 'intelligence'},
            {'text': '🧀 Eat cheese for courage', 'type': 'cheese_option', 'requires': 'cheese'}
        ]
    }
]

UNIQUE_SCENARIOS = [
    {
        'name': 'Ghostly Merchant',
        'description': "A transparent, ghostly figure offers you wares from beyond the grave. His prices are spooky good, but can you trust him? He doesn't seem to have any cheese...",
        'choices': [
            {'text': '🛒 Browse his ghostly wares', 'type': 'shop', 'merchant': 'ghost'},
            {'text': '❓ Ask about his death', 'type': 'dialogue', 'stat': 'charisma'},
            {'text': '👻 Try to help his spirit', 'type': 'skill_check', 'stat': 'wisdom'},
            {'text': '🧀 Ask if he sells cheese', 'type': 'cheese_inquiry', 'disappointing': True}
        ]
    },
    {
        'name': 'Ancient Puzzle Box',
        'description': "You find a small, intricate box on a pedestal. It hums with energy. Solving it could grant a reward, but failing might trigger a curse. High stakes! I love it.",
        'choices': [
            {'text': '🧩 Attempt to solve the puzzle', 'type': 'skill_check', 'stat': 'intelligence'},
            {'text': '🔨 Smash it open', 'type': 'risky_action', 'curse_chance': 0.7},
            {'text': '🔍 Study it carefully first', 'type': 'skill_check', 'stat': 'wisdom'},
            {'text': '🧀 Hope it contains ancient cheese', 'type': 'cheese_dream', 'futile': True}
        ]
    },
    {
        'name': 'Lost Child Illusion',
        'description': "You see a crying child who asks for help finding their parents. It's probably an illusion meant to trick you... but what if it's not? How heroic are you feeling?",
        'choices': [
            {'text': '❤️ Help the child', 'type': 'heroic_choice', 'alignment': 'good'},
            {'text': '🔍 Try to see through illusion', 'type': 'skill_check', 'stat': 'wisdom'},
            {'text': '⚔️ Attack the illusion', 'type': 'combat', 'alignment': 'evil'},
            {'text': '🧀 Offer child some cheese', 'type': 'cheese_option', 'wholesome': True}
        ]
    },
    {
        'name': 'Mirror of Truth',
        'description': "A large mirror shows a reflection of you, but... different. It might offer a cryptic clue or just insult your fashion sense. Worth a look?",
        'choices': [
            {'text': '👁️ Look into the mirror', 'type': 'self_reflection', 'random_effect': True},
            {'text': '💬 Ask it a question', 'type': 'skill_check', 'stat': 'charisma'},
            {'text': '👊 Punch the mirror', 'type': 'destructive', 'bad_luck': True},
            {'text': '🧀 Show it your cheese stash', 'type': 'cheese_option', 'mirror_approves': True}
        ]
    }
]

# Enhanced Dungeon definitions with Plagg's themes
DUNGEONS = {
    'akuma_catacombs': {
        'name': 'The Crumbling Akuma Catacombs',
        'emoji': '🏴‍☠️',
        'min_level': 1,
        'max_level': 8,
        'floors': 3,
        'description': 'Dusty, dark stone corridors filled with cobwebs, leftover magical energy, and the faint scent of old cheese (much to Plagg\'s disappointment).',
        'monsters': ['shadow_grub', 'akuma_sentinel', 'cursed_spirit'],
        'boss': 'Giant Akumatized Spider',
        'theme': 'dark_catacombs',
        'plagg_intro': "Ugh, finally. You've stumbled into the Akuma Catacombs. It smells like old socks and regret, with just a HINT of aged cheese. Disappointing, really.",
        'rewards': {
            'xp_multiplier': 1.5,
            'gold_multiplier': 1.3,
            'rare_materials': ['shadow_essence', 'akuma_fragment', 'old_cheese_rind']
        }
    },
    'foxen_forest': {
        'name': 'The Whispering Foxen Forest',
        'emoji': '🌲',
        'min_level': 8,
        'max_level': 15,
        'floors': 5,
        'description': 'An enchanted forest of perpetual twilight. Trees have glowing runes, illusions flicker at the edge of vision, and the air hums with trickster magic.',
        'monsters': ['forest_sprite', 'illusion_fox', 'trickster_spirit'],
        'boss': 'Council of Kitsune Illusionists',
        'theme': 'mystical_forest',
        'plagg_intro': "Great, a magical forest. It's all sparkly and mystical and has exactly ZERO cheese. The foxes better have some good snacks hidden somewhere.",
        'rewards': {
            'xp_multiplier': 2.0,
            'gold_multiplier': 1.8,
            'rare_materials': ['fox_fur', 'illusion_crystal', 'forest_cheese_maybe']
        }
    },
    'turtle_temple': {
        'name': 'The Sunken Turtle Temple',
        'emoji': '🌊',
        'min_level': 15,
        'max_level': 25,
        'floors': 7,
        'description': 'Underwater ruins, corridors filled with water, bioluminescent coral, and immense water pressure. Players need a water breathing buff to survive.',
        'monsters': ['water_elemental', 'temple_guardian', 'sea_phantom'],
        'boss': 'Ancient Turtle Shell Golem',
        'theme': 'underwater_ruins',
        'plagg_intro': "Oh PERFECT. An underwater temple. Because what I really wanted was to get my fur wet while searching for nonexistent aquatic cheese.",
        'special_requirement': 'water_breathing',
        'rewards': {
            'xp_multiplier': 2.5,
            'gold_multiplier': 2.2,
            'rare_materials': ['coral_fragment', 'water_essence', 'sea_aged_cheese']
        }
    },
    'cosmic_void': {
        'name': 'The Cosmic Void of the Peacock',
        'emoji': '🌌',
        'min_level': 25,
        'max_level': 40,
        'floors': 10,
        'description': 'A mind-bending reality of floating islands, shifting gravity, and walls made of crystallized emotions. It\'s weird, and there\'s definitely no cheese here.',
        'monsters': ['emotion_wraith', 'void_walker', 'cosmic_horror'],
        'boss': 'Manifestation of Cosmic Indifference',
        'theme': 'cosmic_void',
        'plagg_intro': "Well, THIS is new. We're in some kind of emotional void space thing. It's all floaty and weird and I GUARANTEE there's no cheese. This is the worst.",
        'rewards': {
            'xp_multiplier': 3.5,
            'gold_multiplier': 3.0,
            'rare_materials': ['emotion_crystal', 'void_essence', 'cosmic_cheese_dreams']
        }
    },
    'shadow_fortress': {
        'name': 'Shadow Fortress',
        'emoji': '🏰',
        'min_level': 8,
        'max_level': 15,
        'floors': 5,
        'description': 'An ancient fortress consumed by darkness and shadowy beings.',
        'monsters': ['shadow_assassin', 'shadow_assassin', 'frost_elemental'],
        'boss': 'shadow_lord',
        'scenarios': {
            'mirror_hall': {
                'name': '🪞 Hall of Mirrors',
                'description': 'Countless mirrors reflect your image, but some reflections move independently...',
                'encounter_type': 'illusion_battle'
            },
            'library_ruins': {
                'name': '📚 Ruined Library',
                'description': 'Ancient tomes float in the air, whispering forgotten secrets.',
                'challenge': 'wisdom',
                'reward_on_success': 'forbidden_knowledge'
            },
            'shadow_portal': {
                'name': '🌀 Unstable Portal',
                'description': 'A swirling portal tears through reality itself.',
                'special_encounter': True
            }
        },
        'rewards': {
            'xp_multiplier': 2.0,
            'gold_multiplier': 1.8,
            'rare_materials': ['shadow_essence', 'dark_crystal', 'enchanted_steel']
        }
    },
    'dragons_lair': {
        'name': "Dragon's Lair",
        'emoji': '🐉',
        'min_level': 20,
        'max_level': 30,
        'floors': 7,
        'description': 'The lair of an ancient dragon, filled with legendary treasures.',
        'monsters': ['ancient_dragon', 'frost_elemental', 'shadow_assassin'],
        'boss': 'ancient_red_dragon',
        'scenarios': {
            'hoard_chamber': {
                'name': '💰 Dragon Hoard',
                'description': 'Mountains of gold and jewels stretch as far as the eye can see!',
                'rewards': {'gold_multiplier': 5.0, 'legendary_chance': 0.25}
            },
            'lava_bridge': {
                'name': '🔥 Molten Lava Bridge',
                'description': 'A narrow stone bridge spans a chasm of bubbling lava.',
                'challenge': 'constitution',
                'damage_on_fail': 30
            },
            'egg_chamber': {
                'name': '🥚 Dragon Nursery',
                'description': 'Massive dragon eggs rest in crystalline nests.',
                'special_reward': 'dragon_egg_fragment'
            }
        },
        'rewards': {
            'xp_multiplier': 3.0,
            'gold_multiplier': 2.5,
            'rare_materials': ['dragon_scale', 'dragon_heart', 'legendary_gem']
        }
    },
    'cosmic_void': {
        'name': 'Cosmic Void',
        'emoji': '🌌',
        'min_level': 35,
        'max_level': 50,
        'floors': 10,
        'description': 'A tear in reality leads to the endless cosmic void.',
        'monsters': ['void_walker', 'star_devourer', 'cosmic_horror'],
        'boss': 'void_emperor',
        'scenarios': {
            'star_field': {
                'name': '⭐ Dying Star Field',
                'description': 'Stars collapse around you in brilliant supernovas!',
                'cosmic_encounter': True
            },
            'time_rift': {
                'name': '⏰ Temporal Anomaly',
                'description': 'Time flows backward and forward simultaneously.',
                'special_effect': 'time_distortion'
            },
            'void_sanctuary': {
                'name': '🛡️ Void Sanctuary',
                'description': 'A pocket of calm in the chaotic void.',
                'healing': True,
                'safe_rest': True
            }
        },
        'rewards': {
            'xp_multiplier': 4.0,
            'gold_multiplier': 3.0,
            'rare_materials': ['void_essence', 'cosmic_dust', 'reality_fragment']
        }
    }
}

class PlaggDungeonView(discord.ui.View):
    """Plagg's narrative-driven dungeon exploration with dynamic scenario generation."""

    def __init__(self, player_id, dungeon_key, rpg_core):
        super().__init__(timeout=900)  # 15 minute timeout for longer dungeons
        self.player_id = player_id
        self.dungeon_key = dungeon_key
        self.rpg_core = rpg_core
        self.dungeon_data = DUNGEONS[dungeon_key]

        # Plagg's dungeon state management
        self.current_floor = 1
        self.current_room = 1
        self.rooms_per_floor = random.randint(3, 5)  # Variable rooms per floor
        self.rooms_explored_this_floor = 0
        self.completed = False
        self.total_gold_earned = 0
        self.total_xp_earned = 0
        
        # Scenario tracking to avoid repetition
        self.last_scenario_type = None
        self.scenarios_encountered = []
        self.cheese_count = 0  # Track cheese for special options
        
        # Current scenario state
        self.current_scenario = None
        self.awaiting_choice = False

        # Load player data
        self.player_data = self.rpg_core.get_player_data(player_id)
        if not self.player_data:
            self.stop()
            return
        
        # Check if player has cheese items
        self.update_cheese_count()

    def update_cheese_count(self):
        """Update cheese count from player inventory."""
        inventory = self.player_data.get('inventory', {})
        cheese_items = ['cheese', 'camembert', 'premium_cheese', 'rare_cheese', 'aged_cheese']
        self.cheese_count = sum(inventory.get(cheese, 0) for cheese in cheese_items)

    def get_random_scenario(self):
        """Get a random scenario, avoiding repetition when possible."""
        scenario_pools = {
            'monster': MONSTER_SCENARIOS,
            'treasure': TREASURE_SCENARIOS,
            'trap': TRAP_SCENARIOS,
            'unique': UNIQUE_SCENARIOS
        }
        
        # Weight scenarios based on floor and previous scenario
        available_types = list(scenario_pools.keys())
        if self.last_scenario_type and len(available_types) > 1:
            available_types.remove(self.last_scenario_type)
        
        # Adjust weights based on floor
        weights = {
            'monster': 40 - (self.current_floor * 5),  # Less monsters on deeper floors
            'treasure': 25 + (self.current_floor * 2),  # More treasure deeper
            'trap': 20 + (self.current_floor * 3),      # More traps deeper
            'unique': 15 + (self.current_floor * 5)     # More unique deeper
        }
        
        scenario_type = random.choices(
            available_types,
            weights=[weights[t] for t in available_types]
        )[0]
        
        scenario = random.choice(scenario_pools[scenario_type])
        self.last_scenario_type = scenario_type
        
        return scenario, scenario_type

    def create_plagg_embed(self, scenario=None, outcome=None):
        """Create Plagg's narrative embed."""
        if not scenario and not outcome:
            # Floor introduction
            embed = discord.Embed(
                title=f"🧀 Floor {self.current_floor} - {self.dungeon_data['name']}",
                description=self.dungeon_data['plagg_intro'],
                color=COLORS['warning']
            )
            
            embed.add_field(
                name="📍 Current Status",
                value=f"**Floor:** {self.current_floor}/{self.dungeon_data['floors']}\n"
                      f"**Room:** {self.rooms_explored_this_floor + 1}/{self.rooms_per_floor}\n"
                      f"**Cheese Count:** {self.cheese_count} 🧀",
                inline=True
            )
            
            embed.add_field(
                name="💰 Session Rewards",
                value=f"**Gold:** {format_number(self.total_gold_earned)}\n"
                      f"**XP:** {format_number(self.total_xp_earned)}",
                inline=True
            )
            
        elif scenario and not outcome:
            # Scenario presentation
            embed = discord.Embed(
                title=f"🎭 {scenario['name']} - Room {self.rooms_explored_this_floor + 1}",
                description=scenario['description'],
                color=COLORS['primary']
            )
            
            embed.add_field(
                name="🧀 Plagg's Status",
                value=f"*\"Hmm, still no cheese in sight. This is tragic.\"*\n"
                      f"**Your Cheese:** {self.cheese_count} 🧀",
                inline=False
            )
            
        else:
            # Outcome presentation
            embed = discord.Embed(
                title="📜 Plagg's Commentary",
                description=outcome,
                color=COLORS['success']
            )
        
        embed.set_footer(text=f"💡 Floor {self.current_floor} of {self.dungeon_data['floors']} | Plagg is judging your choices...")
        return embed

    def filter_choices_by_requirements(self, choices):
        """Filter choices based on player capabilities and inventory."""
        available_choices = []
        
        for choice in choices:
            # Check cheese requirements
            if choice.get('requires') == 'cheese' and self.cheese_count <= 0:
                continue
            elif choice.get('requires') == 'rare_cheese' and self.cheese_count < 3:
                continue
            elif choice.get('requires') == 'premium_cheese' and self.cheese_count < 5:
                continue
            
            # Check class requirements
            if choice.get('class') and self.player_data['class'] != choice.get('class'):
                continue
                
            # Check item requirements
            if choice.get('requires') == 'tools':
                inventory = self.player_data.get('inventory', {})
                if not any(tool in inventory for tool in ['rope', 'lockpicks', 'hammer']):
                    continue
            
            available_choices.append(choice)
        
        return available_choices[:4]  # Max 4 choices for Discord buttons

    async def update_view(self):
        """Update the view with current scenario or navigation."""
        if self.current_scenario and not self.awaiting_choice:
            # Present new scenario
            embed = self.create_plagg_embed(scenario=self.current_scenario)
            self.clear_items()
            
            # Filter and add choice buttons
            available_choices = self.filter_choices_by_requirements(self.current_scenario['choices'])
            
            for i, choice in enumerate(available_choices):
                button = ScenarioChoiceButton(choice, i)
                self.add_item(button)
            
            # Always add exit option
            self.add_item(ExitDungeonButton())
            self.awaiting_choice = True
            
        elif self.rooms_explored_this_floor >= self.rooms_per_floor:
            # Floor completed
            if self.current_floor >= self.dungeon_data['floors']:
                # Final boss time
                embed = self.create_boss_encounter_embed()
                self.clear_items()
                self.add_item(FightBossButton())
                self.add_item(ExitDungeonButton())
            else:
                # Stairs to next floor
                embed = self.create_floor_complete_embed()
                self.clear_items()
                self.add_item(NextFloorButton())
                self.add_item(RestButton())
                self.add_item(ExitDungeonButton())
        else:
            # Continue exploration
            embed = self.create_plagg_embed()
            self.clear_items()
            self.add_item(ExploreRoomButton())
            self.add_item(RestButton())
            self.add_item(ExitDungeonButton())

        try:
            await self.message.edit(embed=embed, view=self)
        except discord.NotFound:
            pass

    def create_boss_encounter_embed(self):
        """Create the final boss encounter embed."""
        return discord.Embed(
            title=f"🐉 FINAL BOSS: {self.dungeon_data['boss']}",
            description=f"*\"Well, well, well. We've reached the big cheese... metaphorically speaking, of course. "
                       f"There's still no actual cheese here, which is frankly insulting.\"*\n\n"
                       f"The {self.dungeon_data['boss']} emerges from the depths, and even I have to admit... "
                       f"this might actually be interesting. Don't die, I guess.",
            color=COLORS['error']
        )
    
    def create_floor_complete_embed(self):
        """Create floor completion embed."""
        return discord.Embed(
            title=f"🏁 Floor {self.current_floor} Complete!",
            description=f"*\"Congratulations, you survived another floor of this cheese-less nightmare. "
                       f"The stairs down await, leading to even MORE disappointment, I'm sure.\"*\n\n"
                       f"**Floor {self.current_floor} Summary:**\n"
                       f"• Rooms Explored: {self.rooms_explored_this_floor}\n"
                       f"• Scenarios Encountered: {len([s for s in self.scenarios_encountered if s.get('floor') == self.current_floor])}\n"
                       f"• Still No Cheese Found: ✅\n\n"
                       f"Ready for Floor {self.current_floor + 1}?",
            color=COLORS['success']
        )

    def create_dungeon_embed(self):
        """Create the comprehensive dungeon exploration display."""
        embed = discord.Embed(
            title=f"{self.dungeon_data['emoji']} {self.dungeon_data['name']}",
            description=self.dungeon_data['description'],
            color=COLORS['warning']
        )

        # Player status
        player_resources = self.player_data['resources']
        hp_bar = self.create_health_bar(player_resources['hp'], player_resources['max_hp'])

        status_text = (f"**Level:** {self.player_data['level']}\n"
                      f"**HP:** {hp_bar} {player_resources['hp']}/{player_resources['max_hp']}\n"
                      f"**Gold:** {format_number(self.player_data['gold'])}")
        embed.add_field(name="🛡️ Adventurer Status", value=status_text, inline=True)

        # Floor and room progress
        floor_progress = f"{self.current_floor}/{self.dungeon_data['floors']}"
        room_progress = f"{self.current_room}/{self.rooms_per_floor}"
        total_progress = f"{self.rooms_explored}/{self.total_rooms}"
        
        progress_percentage = (self.rooms_explored / self.total_rooms) * 100
        progress_bar = self.create_progress_bar(progress_percentage)

        progress_text = (f"**Floor:** {floor_progress}\n"
                        f"**Room:** {room_progress}\n"
                        f"**Total Progress:** {progress_bar} {int(progress_percentage)}%")
        embed.add_field(name="🗺️ Exploration Progress", value=progress_text, inline=True)

        # Session statistics
        stats_text = (f"**Monsters Defeated:** {self.monsters_defeated}\n"
                     f"**Treasures Found:** {len(self.treasures_found)}\n"
                     f"**Scenarios Encountered:** {len(self.scenarios_encountered)}\n"
                     f"**Gold Earned:** {format_number(self.total_gold_earned)}\n"
                     f"**XP Earned:** {format_number(self.total_xp_earned)}")
        embed.add_field(name="📊 Session Stats", value=stats_text, inline=True)

        # Current floor status
        floor_rooms_remaining = max(0, self.rooms_per_floor - self.current_floor_rooms)
        if floor_rooms_remaining > 0:
            embed.add_field(
                name=f"🏛️ Floor {self.current_floor} Status",
                value=f"Rooms remaining: {floor_rooms_remaining}\n"
                      f"Difficulty: {self.get_floor_difficulty()}",
                inline=True
            )

        # Boss encounter check
        if self.rooms_explored >= self.total_rooms and not self.completed:
            embed.add_field(
                name="🐉 FINAL BOSS ENCOUNTER!",
                value=f"You've reached the deepest chamber!\n"
                      f"**Boss:** {self.dungeon_data['boss'].replace('_', ' ').title()}\n"
                      f"Prepare for the ultimate challenge!",
                inline=False
            )

        # Recent discoveries
        if self.treasures_found or self.scenarios_encountered:
            recent_events = []
            
            if self.treasures_found:
                recent_treasures = self.treasures_found[-3:]  # Last 3 treasures
                recent_events.extend([f"💎 {t.replace('_', ' ').title()}" for t in recent_treasures])
            
            if self.scenarios_encountered:
                recent_scenarios = self.scenarios_encountered[-2:]  # Last 2 scenarios
                recent_events.extend([f"🎭 {s}" for s in recent_scenarios])
            
            if recent_events:
                embed.add_field(
                    name="📜 Recent Discoveries", 
                    value="\n".join(recent_events[-5:]),  # Max 5 recent events
                    inline=False
                )

        embed.set_footer(text=f"💡 Recommended Level: {self.dungeon_data['min_level']}-{self.dungeon_data['max_level']} | Choose your actions carefully!")
        return embed

    def get_floor_difficulty(self):
        """Get current floor difficulty description."""
        difficulty_levels = ["Novice", "Apprentice", "Veteran", "Expert", "Master", "Legendary", "Mythical", "Cosmic"]
        floor_index = min(self.current_floor - 1, len(difficulty_levels) - 1)
        return difficulty_levels[floor_index]

    def create_health_bar(self, current, maximum):
        """Create a visual health bar."""
        if maximum == 0:
            return "▱▱▱▱▱▱▱▱▱▱"

        percentage = current / maximum
        filled_blocks = int(percentage * 10)
        empty_blocks = 10 - filled_blocks

        return "▰" * filled_blocks + "▱" * empty_blocks

    def create_progress_bar(self, percentage):
        """Create a visual progress bar."""
        filled_blocks = int(percentage / 10)
        empty_blocks = 10 - filled_blocks

        return "🟦" * filled_blocks + "⬜" * empty_blocks

class ScenarioChoiceButton(discord.ui.Button):
    """Button for scenario choices with Plagg's commentary."""

    def __init__(self, choice_data, choice_index):
        super().__init__(
            label=choice_data['text'], 
            style=self.get_button_style(choice_data['type']),
            row=choice_index // 2  # Arrange in rows
        )
        self.choice_data = choice_data

    def get_button_style(self, choice_type):
        """Get Discord button style based on choice type."""
        styles = {
            'combat': discord.ButtonStyle.danger,
            'skill_check': discord.ButtonStyle.primary,
            'treasure': discord.ButtonStyle.success,
            'cheese_option': discord.ButtonStyle.secondary,
            'avoidance': discord.ButtonStyle.secondary
        }
        return styles.get(choice_type, discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("Not your adventure!", ephemeral=True)
            return

        await interaction.response.defer()
        
        # Process the choice and get Plagg's outcome
        outcome = await self.process_choice(view)
        
        # Update room progress
        view.rooms_explored_this_floor += 1
        view.scenarios_encountered.append({
            'scenario': view.current_scenario['name'],
            'choice': self.choice_data['text'],
            'floor': view.current_floor
        })
        
        # Clear current scenario
        view.current_scenario = None
        view.awaiting_choice = False
        
        # Show outcome first
        outcome_embed = view.create_plagg_embed(outcome=outcome)
        await interaction.edit_original_response(embed=outcome_embed, view=None)
        
        # Wait a moment for dramatic effect
        await asyncio.sleep(2)
        
        # Continue to next room or floor transition
        await view.update_view()

    async def process_choice(self, view):
        """Process the player's choice and return Plagg's commentary."""
        choice_type = self.choice_data['type']
        player_stats = view.player_data['stats']
        
        plagg_responses = {
            'success': [
                "Well, well! Look who actually managed to do something right for once!",
                "Impressive. Still no cheese involved, but impressive nonetheless.",
                "Not bad, not bad. You might actually survive this cheese-less nightmare.",
                "Huh. Maybe you're not completely hopeless after all."
            ],
            'failure': [
                "Oh, THAT was painful to watch. Even I felt embarrassed for you.",
                "Well, that went about as well as expected. Which is to say, terribly.",
                "Yikes. And I thought MY destructive tendencies were bad.",
                "That was... something. Something very, very sad."
            ],
            'cheese_success': [
                "FINALLY! Someone who understands the power of cheese! You're my new favorite human!",
                "Now THAT'S what I'm talking about! Cheese solves everything!",
                "See? I TOLD you cheese was the answer! Magnificent!",
                "Beautiful! Simply beautiful! The cheese strategy never fails!"
            ],
            'cheese_failure': [
                "Even the cheese couldn't save that disaster. I'm disappointed in both of you.",
                "Well, the cheese tried its best, but you... didn't.",
                "The cheese deserved better than that performance.",
                "Next time, try MORE cheese. Much more."
            ]
        }

        if choice_type == 'combat':
            # Combat encounter
            difficulty = self.choice_data.get('difficulty', 'medium')
            success = self.roll_combat_success(player_stats, difficulty)
            
            if success:
                gold_reward = random.randint(50, 150) * view.current_floor
                xp_reward = random.randint(25, 75) * view.current_floor
                view.total_gold_earned += gold_reward
                view.total_xp_earned += xp_reward
                
                view.player_data['gold'] += gold_reward
                view.player_data['xp'] += xp_reward
                view.rpg_core.save_player_data(view.player_id, view.player_data)
                
                outcome = f"{random.choice(plagg_responses['success'])}\n\n"
                outcome += f"**Combat Victory!**\n"
                outcome += f"• Gold Earned: {format_number(gold_reward)}\n"
                outcome += f"• XP Gained: {format_number(xp_reward)}"
            else:
                damage = random.randint(10, 30) * view.current_floor
                view.player_data['resources']['hp'] = max(1, view.player_data['resources']['hp'] - damage)
                view.rpg_core.save_player_data(view.player_id, view.player_data)
                
                outcome = f"{random.choice(plagg_responses['failure'])}\n\n"
                outcome += f"**Combat Defeat!**\n"
                outcome += f"• Damage Taken: {damage} HP\n"
                outcome += f"• Current HP: {view.player_data['resources']['hp']}/{view.player_data['resources']['max_hp']}"
                
        elif choice_type == 'skill_check':
            # Skill-based challenge
            stat = self.choice_data.get('stat', 'strength')
            difficulty = 10 + (view.current_floor * 2)
            roll = player_stats.get(stat, 5) + random.randint(1, 20)
            success = roll >= difficulty
            
            if success:
                reward_gold = random.randint(30, 80) * view.current_floor
                view.total_gold_earned += reward_gold
                view.player_data['gold'] += reward_gold
                view.rpg_core.save_player_data(view.player_id, view.player_data)
                
                outcome = f"{random.choice(plagg_responses['success'])}\n\n"
                outcome += f"**Skill Check Success!** ({stat.title()} roll: {roll} vs {difficulty})\n"
                outcome += f"• Gold Found: {format_number(reward_gold)}"
            else:
                outcome = f"{random.choice(plagg_responses['failure'])}\n\n"
                outcome += f"**Skill Check Failed!** ({stat.title()} roll: {roll} vs {difficulty})\n"
                outcome += "• Maybe try a different approach next time?"
                
        elif choice_type == 'cheese_option':
            # Cheese-powered choice!
            view.cheese_count -= 1
            if 'cheese' in view.player_data.get('inventory', {}):
                view.player_data['inventory']['cheese'] -= 1
                if view.player_data['inventory']['cheese'] <= 0:
                    del view.player_data['inventory']['cheese']
            
            # Cheese always makes things better
            reward_gold = random.randint(100, 300) * view.current_floor
            reward_xp = random.randint(50, 100) * view.current_floor
            view.total_gold_earned += reward_gold
            view.total_xp_earned += reward_xp
            
            view.player_data['gold'] += reward_gold
            view.player_data['xp'] += reward_xp
            view.rpg_core.save_player_data(view.player_id, view.player_data)
            
            outcome = f"{random.choice(plagg_responses['cheese_success'])}\n\n"
            outcome += f"**CHEESE POWER ACTIVATED!** 🧀\n"
            outcome += f"• Gold Earned: {format_number(reward_gold)}\n"
            outcome += f"• XP Gained: {format_number(reward_xp)}\n"
            outcome += f"• Cheese Remaining: {view.cheese_count}"
            
        elif choice_type == 'treasure':
            # Treasure discovery
            gold_reward = random.randint(100, 200) * view.current_floor
            view.total_gold_earned += gold_reward
            view.player_data['gold'] += gold_reward
            
            # Chance for item
            if random.random() < 0.3:
                possible_items = ['health_potion', 'mana_potion', 'cheese']
                item = random.choice(possible_items)
                quantity = random.randint(1, 3)
                
                if item in view.player_data.get('inventory', {}):
                    view.player_data['inventory'][item] += quantity
                else:
                    view.player_data['inventory'][item] = quantity
                
                if item == 'cheese':
                    view.update_cheese_count()
                
                view.rpg_core.save_player_data(view.player_id, view.player_data)
                
                item_text = f"• Item Found: {item.replace('_', ' ').title()} x{quantity}"
            else:
                item_text = ""
            
            view.rpg_core.save_player_data(view.player_id, view.player_data)
            
            outcome = f"{random.choice(plagg_responses['success'])}\n\n"
            outcome += f"**Treasure Discovered!**\n"
            outcome += f"• Gold Found: {format_number(gold_reward)}\n"
            if item_text:
                outcome += f"{item_text}"
                
        else:
            # Default outcome
            outcome = f"{random.choice(plagg_responses['success'])}\n\nYou handle the situation... adequately, I suppose."
        
        return outcome

    def roll_combat_success(self, player_stats, difficulty):
        """Roll for combat success based on difficulty."""
        base_chance = {
            'easy': 0.8,
            'medium': 0.6,
            'hard': 0.4,
            'elite': 0.3,
            'mimic': 0.5
        }
        
        # Modify chance based on player stats
        combat_bonus = (player_stats.get('strength', 5) + player_stats.get('dexterity', 5)) / 20
        success_chance = base_chance.get(difficulty, 0.6) + combat_bonus
        
        return random.random() < success_chance

class ExploreRoomButton(discord.ui.Button):
    """Explore the next room with Plagg's narrative."""

    def __init__(self):
        super().__init__(label="🚪 Enter Next Room", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("Not your dungeon exploration!", ephemeral=True)
            return

        await interaction.response.defer()
        
        # Generate new scenario
        scenario, scenario_type = view.get_random_scenario()
        view.current_scenario = scenario
        view.awaiting_choice = False
        
        # Update view with new scenario
        await view.update_view()

    async def encounter_monster(self, interaction, view):
        """Handle enhanced monster encounters."""
        available_monsters = view.dungeon_data['monsters']
        monster_key = random.choice(available_monsters)

        # Floor-based monster scaling
        monster_level_bonus = (view.current_floor - 1) * 2
        
        embed = discord.Embed(
            title="⚔️ Monster Encounter!",
            description=f"A **{monster_key.replace('_', ' ').title()}** blocks your path!\n\n"
                       f"*Floor {view.current_floor} Difficulty: Enhanced with +{monster_level_bonus} levels*\n\n"
                       f"Preparing for tactical combat...",
            color=COLORS['error']
        )

        await interaction.response.edit_message(embed=embed, view=None)
        
        # Start combat (implementation would connect to combat system)
        view.monsters_defeated += 1
        
        # Simulate combat rewards
        gold_reward = random.randint(50, 150) * view.current_floor
        xp_reward = random.randint(25, 75) * view.current_floor
        
        view.player_data['gold'] += gold_reward
        view.player_data['xp'] += xp_reward
        view.total_gold_earned += gold_reward
        view.total_xp_earned += xp_reward
        
        view.rpg_core.save_player_data(view.player_id, view.player_data)
        
        await asyncio.sleep(2)
        await view.update_view()

    async def encounter_scenario(self, interaction, view):
        """Handle special scenario encounters."""
        scenarios = list(view.dungeon_data['scenarios'].values())
        if scenarios:
            scenario = random.choice(scenarios)
            scenario_name = scenario['name']
            
            view.scenarios_encountered.append(scenario_name)
            
            embed = discord.Embed(
                title=scenario_name,
                description=scenario['description'],
                color=COLORS['info']
            )

            # Handle different scenario types
            if 'challenge' in scenario:
                success = await self.handle_scenario_challenge(scenario, view)
                if success:
                    embed.add_field(
                        name="✅ Success!",
                        value="You overcome the challenge through skill and determination!",
                        inline=False
                    )
                    if 'reward_on_success' in scenario:
                        reward = scenario['reward_on_success']
                        view.treasures_found.append(reward)
                        view.player_data['inventory'][reward] = view.player_data['inventory'].get(reward, 0) + 1
                else:
                    embed.add_field(
                        name="❌ Failed!",
                        value="The challenge proves too difficult this time.",
                        inline=False
                    )
                    if 'damage_on_fail' in scenario:
                        damage = scenario['damage_on_fail']
                        view.player_data['resources']['hp'] = max(1, view.player_data['resources']['hp'] - damage)

            elif 'rewards' in scenario:
                # Apply scenario rewards
                rewards = scenario['rewards']
                if 'gold_multiplier' in rewards:
                    bonus_gold = int(100 * rewards['gold_multiplier'] * view.current_floor)
                    view.player_data['gold'] += bonus_gold
                    view.total_gold_earned += bonus_gold
                    embed.add_field(name="💰 Gold Found", value=f"+{format_number(bonus_gold)} gold", inline=True)

            view.rpg_core.save_player_data(view.player_id, view.player_data)
            
            await interaction.response.edit_message(embed=embed, view=view)
            await asyncio.sleep(3)
            await view.update_view()

    async def handle_scenario_challenge(self, scenario, view):
        """Handle scenario challenges based on player stats."""
        challenge_stat = scenario['challenge']
        player_stat_value = view.player_data['stats'].get(challenge_stat, 5)
        
        # Challenge difficulty scales with floor
        difficulty_threshold = 5 + (view.current_floor * 2)
        
        # Roll against stat + random factor
        roll = player_stat_value + random.randint(1, 10)
        return roll >= difficulty_threshold

    async def find_treasure(self, interaction, view):
        """Handle enhanced treasure discovery."""
        possible_treasures = view.dungeon_data['rewards']['rare_materials']
        treasure = random.choice(possible_treasures)
        
        # Floor-based quantity scaling
        quantity = random.randint(1, 2 + view.current_floor)
        
        # Rare chance for upgraded treasure
        if random.random() < 0.1 * view.current_floor:
            treasure = f"enhanced_{treasure}"
            quantity = max(1, quantity // 2)

        # Add to inventory
        if treasure in view.player_data['inventory']:
            view.player_data['inventory'][treasure] += quantity
        else:
            view.player_data['inventory'][treasure] = quantity

        view.treasures_found.append(treasure)

        # Gold reward with floor scaling
        gold_reward = random.randint(75, 200) * view.dungeon_data['rewards']['gold_multiplier'] * view.current_floor
        view.player_data['gold'] += int(gold_reward)
        view.total_gold_earned += int(gold_reward)

        view.rpg_core.save_player_data(view.player_id, view.player_data)

        embed = discord.Embed(
            title="💎 Treasure Discovery!",
            description=f"You discover a hidden cache on Floor {view.current_floor}!\n\n"
                       f"**Found:**\n"
                       f"• {treasure.replace('_', ' ').title()} x{quantity}\n"
                       f"• {format_number(int(gold_reward))} Gold",
            color=COLORS['success']
        )

        await interaction.response.edit_message(embed=embed, view=view)
        await asyncio.sleep(2)
        await view.update_view()

    async def encounter_trap(self, interaction, view):
        """Handle trap encounters."""
        traps = [
            {"name": "Poison Dart Trap", "damage": 10 + view.current_floor * 3, "stat": "dexterity"},
            {"name": "Crushing Walls", "damage": 15 + view.current_floor * 4, "stat": "constitution"},
            {"name": "Magic Rune Trap", "damage": 12 + view.current_floor * 3, "stat": "intelligence"}
        ]
        
        trap = random.choice(traps)
        player_stat = view.player_data['stats'].get(trap['stat'], 5)
        
        # Trap difficulty scales with floor
        avoid_roll = player_stat + random.randint(1, 10)
        trap_difficulty = 8 + view.current_floor * 2
        
        embed = discord.Embed(
            title=f"⚡ {trap['name']}!",
            color=COLORS['warning']
        )
        
        if avoid_roll >= trap_difficulty:
            embed.description = f"You skillfully avoid the {trap['name'].lower()}!"
            embed.color = COLORS['success']
        else:
            damage = trap['damage']
            view.player_data['resources']['hp'] = max(1, view.player_data['resources']['hp'] - damage)
            embed.description = f"The {trap['name'].lower()} catches you!\n\n**Damage taken:** {damage} HP"
            embed.color = COLORS['error']
        
        view.rpg_core.save_player_data(view.player_id, view.player_data)
        
        await interaction.response.edit_message(embed=embed, view=view)
        await asyncio.sleep(2)
        await view.update_view()

    async def empty_room(self, interaction, view):
        """Handle empty room encounters."""
        empty_descriptions = [
            f"An empty chamber echoes with your footsteps. Floor {view.current_floor} feels abandoned.",
            f"Dust motes dance in shafts of dim light. This Floor {view.current_floor} room holds no secrets.",
            f"The silence is deafening in this vacant space on Floor {view.current_floor}.",
            f"Faded murals on the walls tell stories of ancient times. Floor {view.current_floor} keeps its mysteries."
        ]
        
        description = random.choice(empty_descriptions)
        
        embed = discord.Embed(
            title="🏛️ Empty Chamber",
            description=description,
            color=COLORS['secondary']
        )

        await interaction.response.edit_message(embed=embed, view=view)
        await asyncio.sleep(1)
        await view.update_view()

class NextFloorButton(discord.ui.Button):
    """Advance to the next floor."""

    def __init__(self):
        super().__init__(label="⬆️ Ascend to Next Floor", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("Not your dungeon exploration!", ephemeral=True)
            return

        old_floor = view.current_floor
        view.current_floor += 1
        view.current_floor_rooms = 0
        view.current_room = 1
        view.floor_completion[old_floor] = True

        # Floor transition rewards
        transition_gold = 100 * view.current_floor
        transition_xp = 50 * view.current_floor
        
        view.player_data['gold'] += transition_gold
        view.player_data['xp'] += transition_xp
        view.total_gold_earned += transition_gold
        view.total_xp_earned += transition_xp
        
        view.rpg_core.save_player_data(view.player_id, view.player_data)

        embed = discord.Embed(
            title=f"⬆️ Floor {view.current_floor} Reached!",
            description=f"You ascend to Floor {view.current_floor} of {view.dungeon_data['name']}!\n\n"
                       f"**Floor Completion Bonus:**\n"
                       f"• {format_number(transition_gold)} Gold\n"
                       f"• {format_number(transition_xp)} XP\n\n"
                       f"The challenges ahead will be more difficult but more rewarding!",
            color=COLORS['success']
        )

        await interaction.response.edit_message(embed=embed, view=view)
        await asyncio.sleep(2)
        await view.update_view()

class SearchButton(discord.ui.Button):
    """Thoroughly search the current room."""

    def __init__(self):
        super().__init__(label="🔍 Search Thoroughly", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("Not your dungeon exploration!", ephemeral=True)
            return

        # Wisdom-based search success with floor scaling
        wisdom_bonus = view.player_data['stats'].get('wisdom', 5)
        search_roll = wisdom_bonus + random.randint(1, 15)
        search_threshold = 10 + view.current_floor

        if search_roll >= search_threshold:
            # Successful search - better rewards on higher floors
            rare_materials = view.dungeon_data['rewards']['rare_materials']
            item = random.choice(rare_materials)
            quantity = random.randint(1, 2 + view.current_floor)

            # Chance for rare finds on higher floors
            if view.current_floor >= 3 and random.random() < 0.3:
                item = f"rare_{item}"

            if item in view.player_data['inventory']:
                view.player_data['inventory'][item] += quantity
            else:
                view.player_data['inventory'][item] = quantity

            # Additional gold find
            bonus_gold = random.randint(25, 75) * view.current_floor
            view.player_data['gold'] += bonus_gold
            view.total_gold_earned += bonus_gold

            view.rpg_core.save_player_data(view.player_id, view.player_data)

            embed = discord.Embed(
                title="🔍 Thorough Search Success!",
                description=f"Your careful investigation of this Floor {view.current_floor} room pays off!\n\n"
                           f"**Found:**\n"
                           f"• {item.replace('_', ' ').title()} x{quantity}\n"
                           f"• {format_number(bonus_gold)} bonus gold",
                color=COLORS['success']
            )
        else:
            # Failed search
            embed = discord.Embed(
                title="🔍 Search Complete",
                description=f"You search Floor {view.current_floor} room carefully but find nothing of value.\n\n"
                           f"Perhaps your wisdom needs improvement, or this room simply holds no secrets.",
                color=COLORS['secondary']
            )

        await interaction.response.edit_message(embed=embed, view=view)
        await asyncio.sleep(2)
        await view.update_view()

class RestButton(discord.ui.Button):
    """Rest to recover health and mana with enhanced mechanics."""

    def __init__(self):
        super().__init__(label="😴 Rest & Recover", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("Not your dungeon exploration!", ephemeral=True)
            return

        # Rest effectiveness based on constitution and floor
        constitution = view.player_data['stats'].get('constitution', 5)
        rest_effectiveness = 1.0 + (constitution * 0.05)
        
        # Base recovery amounts
        hp_restored = int((view.player_data['resources']['max_hp'] // 4) * rest_effectiveness)
        mana_restored = int((view.player_data['resources']['max_mana'] // 3) * rest_effectiveness)

        old_hp = view.player_data['resources']['hp']
        old_mana = view.player_data['resources']['mana']

        view.player_data['resources']['hp'] = min(
            view.player_data['resources']['max_hp'],
            view.player_data['resources']['hp'] + hp_restored
        )
        view.player_data['resources']['mana'] = min(
            view.player_data['resources']['max_mana'],
            view.player_data['resources']['mana'] + mana_restored
        )

        actual_hp_restored = view.player_data['resources']['hp'] - old_hp
        actual_mana_restored = view.player_data['resources']['mana'] - old_mana

        # Chance of encounter while resting (higher on deeper floors)
        encounter_chance = 0.1 + (view.current_floor * 0.03)
        
        if random.random() < encounter_chance:
            # Ambush while resting!
            damage = random.randint(5, 15 + view.current_floor * 2)
            view.player_data['resources']['hp'] = max(1, view.player_data['resources']['hp'] - damage)
            
            view.rpg_core.save_player_data(view.player_id, view.player_data)

            embed = discord.Embed(
                title="😴 Ambushed While Resting!",
                description=f"Your rest on Floor {view.current_floor} is interrupted by a surprise attack!\n\n"
                           f"**Recovery:** ❤️ {actual_hp_restored} HP, 💙 {actual_mana_restored} Mana\n"
                           f"**Ambush Damage:** -{damage} HP\n\n"
                           f"You managed to recover some strength before the attack!",
                color=COLORS['warning']
            )
        else:
            # Peaceful rest
            view.rpg_core.save_player_data(view.player_id, view.player_data)

            rest_descriptions = [
                f"You find a safe alcove on Floor {view.current_floor} and rest peacefully.",
                f"The silence of Floor {view.current_floor} allows for undisturbed recovery.",
                f"You meditate quietly, restoring your strength for Floor {view.current_floor}'s challenges.",
                f"A brief respite on Floor {view.current_floor} rejuvenates your spirit."
            ]

            embed = discord.Embed(
                title="😴 Peaceful Rest",
                description=f"{random.choice(rest_descriptions)}\n\n"
                           f"**Recovered:**\n"
                           f"• ❤️ {actual_hp_restored} HP\n"
                           f"• 💙 {actual_mana_restored} Mana",
                color=COLORS['success']
            )

        await interaction.response.edit_message(embed=embed, view=view)
        await asyncio.sleep(2)
        await view.update_view()

class FightBossButton(discord.ui.Button):
    """Fight the dungeon boss with dramatic presentation."""

    def __init__(self):
        super().__init__(label="🐉 Challenge the Final Boss", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("Not your dungeon exploration!", ephemeral=True)
            return

        boss_key = view.dungeon_data['boss']
        boss_name = boss_key.replace('_', ' ').title()

        embed = discord.Embed(
            title="🐉 FINAL BOSS ENCOUNTER!",
            description=f"**{boss_name}** emerges from the deepest chamber of {view.dungeon_data['name']}!\n\n"
                       f"*The very air trembles with malevolent power...*\n\n"
                       f"This is the culmination of your {view.dungeon_data['floors']}-floor journey.\n"
                       f"Victory will bring legendary rewards!\n\n"
                       f"**Your Stats This Run:**\n"
                       f"• Floors Conquered: {view.current_floor}\n"
                       f"• Monsters Defeated: {view.monsters_defeated}\n"
                       f"• Treasures Found: {len(view.treasures_found)}\n\n"
                       f"Preparing for the ultimate battle...",
            color=COLORS['error']
        )

        await interaction.response.edit_message(embed=embed, view=None)

        # Simulate epic boss battle
        await asyncio.sleep(3)
        
        # Boss battle rewards (much higher than regular encounters)
        boss_gold = random.randint(500, 1000) * view.dungeon_data['rewards']['gold_multiplier']
        boss_xp = random.randint(200, 400) * view.dungeon_data['rewards']['xp_multiplier']
        
        view.player_data['gold'] += int(boss_gold)
        view.player_data['xp'] += int(boss_xp)
        view.total_gold_earned += int(boss_gold)
        view.total_xp_earned += int(boss_xp)
        
        # Guaranteed rare material from boss
        rare_materials = view.dungeon_data['rewards']['rare_materials']
        boss_material = random.choice(rare_materials)
        boss_material_qty = random.randint(3, 6)
        
        view.player_data['inventory'][boss_material] = view.player_data['inventory'].get(boss_material, 0) + boss_material_qty
        
        view.completed = True
        view.rpg_core.save_player_data(view.player_id, view.player_data)

        victory_embed = discord.Embed(
            title="🎉 BOSS DEFEATED!",
            description=f"**{boss_name} falls before your might!**\n\n"
                       f"The {view.dungeon_data['name']} has been conquered!\n\n"
                       f"**Epic Victory Rewards:**\n"
                       f"• 💰 {format_number(int(boss_gold))} Gold\n"
                       f"• ⭐ {format_number(int(boss_xp))} XP\n"
                       f"• 💎 {boss_material.replace('_', ' ').title()} x{boss_material_qty}\n\n"
                       f"**Dungeon Complete!** 🏆",
            color=COLORS['success']
        )

        await interaction.edit_original_response(embed=victory_embed)
        await asyncio.sleep(3)
        await view.update_view()

class CollectRewardsButton(discord.ui.Button):
    """Collect final dungeon completion rewards."""

    def __init__(self):
        super().__init__(label="🏆 Collect Completion Rewards", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("Not your dungeon exploration!", ephemeral=True)
            return

        # Calculate completion bonuses
        completion_multiplier = 1.0 + (view.monsters_defeated * 0.1) + (len(view.treasures_found) * 0.05)
        
        completion_gold = int(200 * view.dungeon_data['floors'] * completion_multiplier)
        completion_xp = int(100 * view.dungeon_data['floors'] * completion_multiplier)
        
        view.player_data['gold'] += completion_gold
        view.player_data['xp'] += completion_xp
        
        # Level up check
        levels_gained = view.rpg_core.level_up_check(view.player_data)
        
        view.rpg_core.save_player_data(view.player_id, view.player_data)

        embed = discord.Embed(
            title="🏆 Dungeon Mastery Achieved!",
            description=f"**{view.dungeon_data['name']} Conquered!**\n\n"
                       f"**Completion Statistics:**\n"
                       f"• Total Floors: {view.dungeon_data['floors']}\n"
                       f"• Rooms Explored: {view.rooms_explored}\n"
                       f"• Monsters Defeated: {view.monsters_defeated}\n"
                       f"• Treasures Found: {len(view.treasures_found)}\n"
                       f"• Scenarios Encountered: {len(view.scenarios_encountered)}\n\n"
                       f"**Final Session Totals:**\n"
                       f"• 💰 {format_number(view.total_gold_earned + completion_gold)} Total Gold\n"
                       f"• ⭐ {format_number(view.total_xp_earned + completion_xp)} Total XP\n\n"
                       f"**Completion Bonus:**\n"
                       f"• 🎯 Performance Multiplier: {completion_multiplier:.2f}x\n"
                       f"• 💰 {format_number(completion_gold)} Bonus Gold\n"
                       f"• ⭐ {format_number(completion_xp)} Bonus XP",
            color=COLORS['legendary']
        )

        if levels_gained > 0:
            embed.add_field(
                name="🎉 LEVEL UP!",
                value=f"Congratulations! You gained {levels_gained} level{'s' if levels_gained > 1 else ''}!\n"
                      f"Current Level: {view.player_data['level']}",
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=None)

class ExitDungeonButton(discord.ui.Button):
    """Exit the dungeon with comprehensive summary."""

    def __init__(self):
        super().__init__(label="🚪 Exit Dungeon", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("Not your dungeon exploration!", ephemeral=True)
            return

        # Mark player as no longer in dungeon
        view.player_data['in_combat'] = False
        view.rpg_core.save_player_data(view.player_id, view.player_data)

        # Calculate completion percentage
        completion_percentage = (view.rooms_explored / view.total_rooms) * 100

        embed = discord.Embed(
            title=f"🚪 Exited {view.dungeon_data['name']}",
            description=f"You emerge from the depths, battle-worn but victorious!\n\n"
                       f"**Adventure Summary:**\n"
                       f"• Completion: {completion_percentage:.1f}% ({view.rooms_explored}/{view.total_rooms} rooms)\n"
                       f"• Floors Reached: {view.current_floor}/{view.dungeon_data['floors']}\n"
                       f"• Monsters Defeated: {view.monsters_defeated}\n"
                       f"• Treasures Found: {len(view.treasures_found)}\n"
                       f"• Scenarios Encountered: {len(view.scenarios_encountered)}\n\n"
                       f"**Session Rewards:**\n"
                       f"• 💰 {format_number(view.total_gold_earned)} Gold Earned\n"
                       f"• ⭐ {format_number(view.total_xp_earned)} XP Gained\n\n"
                       f"{'🏆 **DUNGEON COMPLETED!**' if view.completed else '⏰ Come back anytime to continue your adventure!'}",
            color=COLORS['success'] if view.completed else COLORS['secondary']
        )

        await interaction.response.edit_message(embed=embed, view=None)
        view.stop()

class RPGDungeons(commands.Cog):
    """Advanced interactive dungeon exploration system."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dungeons", aliases=["explore_dungeon"])
    async def dungeons(self, ctx, dungeon_name: str = None):
        """Enter an interactive dungeon for extended exploration and epic rewards."""
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
                description="You need to create a character before exploring dungeons! Let's start with the interactive tutorial.",
                color=COLORS['info']
            )
            
            from cogs.help import TutorialView
            view = TutorialView(self.bot, "$")
            await ctx.send(embed=embed, view=view)
            return

        if player_data.get('in_combat'):
            embed = create_embed("Already Exploring", "Finish your current adventure first!", COLORS['warning'])
            await ctx.send(embed=embed)
            return

        if not dungeon_name:
            # Show available dungeons with enhanced information
            embed = discord.Embed(
                title="🏰 Epic Dungeon Adventures",
                description="**Choose your dungeon adventure wisely!**\n\n"
                           "Each dungeon offers unique challenges, floors to explore, scenarios to encounter, and epic boss battles!",
                color=COLORS['warning']
            )

            for dungeon_key, dungeon_data in DUNGEONS.items():
                level_range = f"Level {dungeon_data['min_level']}-{dungeon_data['max_level']}"
                floors = f"{dungeon_data['floors']} floors"
                scenarios = f"{len(dungeon_data['scenarios'])} unique scenarios"

                value = (f"{dungeon_data['description']}\n\n"
                        f"**📊 Dungeon Info:**\n"
                        f"• **Difficulty:** {level_range}\n"
                        f"• **Size:** {floors}\n"
                        f"• **Features:** {scenarios}\n"
                        f"• **Boss:** {dungeon_data['boss'].replace('_', ' ').title()}")

                embed.add_field(
                    name=f"{dungeon_data['emoji']} {dungeon_data['name']}",
                    value=value,
                    inline=False
                )

            embed.add_field(
                name="💡 How to Play",
                value="• Use `$dungeons <name>` to enter a specific dungeon\n"
                      "• Navigate through floors with interactive buttons\n"
                      "• Encounter monsters, treasures, traps, and scenarios\n"
                      "• Defeat the final boss for epic rewards!",
                inline=False
            )

            embed.set_footer(text="💀 Dungeons are challenging! Make sure you're prepared before entering.")
            await ctx.send(embed=embed)
            return

        # Find dungeon
        dungeon_key = None
        for key, data in DUNGEONS.items():
            if dungeon_name.lower() in data['name'].lower().replace(' ', '_') or dungeon_name.lower() in key:
                dungeon_key = key
                break

        if not dungeon_key:
            embed = create_embed("Dungeon Not Found", f"No dungeon named '{dungeon_name}' exists!\n\nUse `$dungeons` to see all available dungeons.", COLORS['error'])
            await ctx.send(embed=embed)
            return

        dungeon_data = DUNGEONS[dungeon_key]

        # Check level requirement
        if player_data['level'] < dungeon_data['min_level']:
            embed = create_embed(
                "Level Too Low", 
                f"You need to be at least Level {dungeon_data['min_level']} to enter {dungeon_data['name']}!\n\n"
                f"**Your Level:** {player_data['level']}\n"
                f"**Required Level:** {dungeon_data['min_level']}\n\n"
                f"Keep training and come back when you're stronger!", 
                COLORS['warning']
            )
            await ctx.send(embed=embed)
            return

        # Check health requirement
        health_percentage = player_data['resources']['hp'] / player_data['resources']['max_hp']
        if health_percentage < 0.75:  # Require 75% health for dungeons
            embed = create_embed(
                "Insufficient Health", 
                f"You need at least 75% HP to enter a dangerous dungeon!\n\n"
                f"**Current HP:** {player_data['resources']['hp']}/{player_data['resources']['max_hp']} ({int(health_percentage*100)}%)\n"
                f"**Required:** {int(player_data['resources']['max_hp'] * 0.75)} HP (75%)\n\n"
                f"Use healing items or rest before attempting the dungeon!", 
                COLORS['warning']
            )
            await ctx.send(embed=embed)
            return

        # Mark player as in dungeon
        player_data['in_combat'] = True
        rpg_core.save_player_data(ctx.author.id, player_data)

        # Create dramatic entrance
        embed = discord.Embed(
            title=f"🏰 Entering {dungeon_data['name']}",
            description=f"{dungeon_data['description']}\n\n"
                       f"**⚔️ Dungeon Details:**\n"
                       f"• **Floors to Conquer:** {dungeon_data['floors']}\n"
                       f"• **Difficulty Range:** Level {dungeon_data['min_level']}-{dungeon_data['max_level']}\n"
                       f"• **Final Boss:** {dungeon_data['boss'].replace('_', ' ').title()}\n"
                       f"• **Rewards Multiplier:** {dungeon_data['rewards']['xp_multiplier']}x XP, {dungeon_data['rewards']['gold_multiplier']}x Gold\n\n"
                       f"*The entrance seals behind you as you step into the darkness...*\n"
                       f"*Your adventure through {dungeon_data['floors']} treacherous floors begins now!*",
            color=COLORS['warning']
        )

        message = await ctx.send(embed=embed)

        # Start Plagg's narrative exploration
        view = PlaggDungeonView(ctx.author.id, dungeon_key, rpg_core)
        view.message = message

        await asyncio.sleep(3)  # Dramatic pause for effect
        await view.update_view()

async def setup(bot):
    await bot.add_cog(RPGDungeons(bot))
