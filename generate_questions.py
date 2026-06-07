import json
import os

questions = []

categories = ["family_lineage", "political_allegiance", "conflict_causality", "geographic_political", "cross_domain"]

# 1. Family Lineage
family_data = [
    ("MH_001", "Who is the father of the person who killed Joffrey Baratheon?", "Tywin Lannister", ["Joffrey Baratheon", "Tyrion Lannister", "Tywin Lannister"], ["killed", "father"]),
    ("MH_002", "Who is the maternal grandfather of Joffrey Baratheon?", "Tywin Lannister", ["Joffrey Baratheon", "Cersei Lannister", "Tywin Lannister"], ["mother", "father"]),
    ("MH_003", "Who is the mother of Jon Snow?", "Lyanna Stark", ["Jon Snow", "Lyanna Stark"], ["mother"]),
    ("MH_004", "Who is the father of Arya Stark's mother?", "Hoster Tully", ["Arya Stark", "Catelyn Stark", "Hoster Tully"], ["mother", "father"]),
    ("MH_005", "Who is the brother of Daenerys Targaryen's father?", "None/Unknown (Aerys II had no notable brothers in the main show focus, let's change)", "Who is the brother of Daenerys Targaryen?", "Viserys Targaryen", ["Daenerys Targaryen", "Viserys Targaryen"], ["brother"]),
    # Let's fix MH_005
    ("MH_006", "Who is the sister of the Kingslayer?", "Cersei Lannister", ["Jaime Lannister", "Cersei Lannister"], ["sister", "alias"]),
    ("MH_007", "Who is the son of Ned Stark's sister?", "Jon Snow", ["Ned Stark", "Lyanna Stark", "Jon Snow"], ["sister", "son"]),
    ("MH_008", "Who is the father of the Bastard of Bolton?", "Roose Bolton", ["Ramsay Bolton", "Roose Bolton"], ["father", "alias"]),
    ("MH_009", "Who is the uncle of Robin Arryn?", "Edmure Tully", ["Robin Arryn", "Lysa Arryn", "Edmure Tully"], ["mother", "brother"]),
    ("MH_010", "Who is the grandmother of Margaery Tyrell?", "Olenna Tyrell", ["Margaery Tyrell", "Mace Tyrell", "Olenna Tyrell"], ["father", "mother"]),
]

# Fixing MH_005
family_data[4] = ("MH_005", "Who is the brother of Daenerys Targaryen?", "Viserys Targaryen", ["Daenerys Targaryen", "Viserys Targaryen"], ["brother"])


for i, d in enumerate(family_data):
    questions.append({
        "id": d[0], "question": d[1], "answer": d[2], "hops_required": 2,
        "entities_involved": d[3], "relationships_required": d[4], "difficulty": "medium", "category": "family_lineage"
    })

# 2. Political Allegiance
pol_data = [
    ("Who does House Karstark swear allegiance to?", "House Stark"),
    ("Which house does the commander of the Night's Watch owe allegiance to?", "None / Neutral"),
    ("Who is the liege lord of House Tarly?", "House Tyrell"),
    ("Which house did House Frey betray at the Red Wedding?", "House Stark"),
    ("Who did the Umbers betray House Stark for?", "House Bolton"),
    ("Which house rules the Stormlands?", "House Baratheon"),
    ("Who did House Tyrell ally with after Renly's death?", "House Lannister"),
    ("Which house controls the Westerlands?", "House Lannister"),
    ("Who is the leader of the Unsullied?", "Grey Worm"),
    ("Who did the Ironborn swear fealty to after the Kingsmoot?", "Euron Greyjoy")
]
for i, d in enumerate(pol_data):
    questions.append({
        "id": f"MH_{11+i:03d}", "question": d[0], "answer": d[1], "hops_required": 2,
        "entities_involved": [], "relationships_required": ["allegiance", "rules"], "difficulty": "medium", "category": "political_allegiance"
    })

# 3. Conflict Causality
conf_data = [
    ("What battle directly preceded the Red Wedding?", "Battle of the Fords / War of the Five Kings"),
    ("Who killed the Night King during the Battle of Winterfell?", "Arya Stark"),
    ("What event led to the execution of Ned Stark?", "Robert Baratheon's death"),
    ("Who won the Battle of the Bastards?", "House Stark / Jon Snow"),
    ("What caused the destruction of the Great Sept of Baelor?", "Wildfire / Cersei Lannister"),
    ("Who poisoned Joffrey Baratheon?", "Olenna Tyrell"),
    ("What battle resulted in the capture of Jaime Lannister?", "Battle of the Whispering Wood"),
    ("Who killed Tywin Lannister?", "Tyrion Lannister"),
    ("What was the outcome of the Viper vs the Mountain trial by combat?", "The Mountain won / Oberyn Martell died"),
    ("Who burned Shireen Baratheon?", "Melisandre / Stannis Baratheon")
]
for i, d in enumerate(conf_data):
    questions.append({
        "id": f"MH_{21+i:03d}", "question": d[0], "answer": d[1], "hops_required": 2,
        "entities_involved": [], "relationships_required": ["killed", "participated_in"], "difficulty": "medium", "category": "conflict_causality"
    })

# 4. Geographic Political
geo_data = [
    ("Who rules the castle located in the home of House Stark?", "House Stark"),
    ("What is the seat of House Lannister?", "Casterly Rock"),
    ("Who controls Dragonstone at the beginning of the series?", "Stannis Baratheon"),
    ("Where is the Iron Throne located?", "King's Landing"),
    ("What region does House Martell rule?", "Dorne"),
    ("What is the ancestral home of House Arryn?", "The Eyrie"),
    ("Where is the Citadel located?", "Oldtown"),
    ("What region does House Tyrell rule?", "The Reach"),
    ("Where did Daenerys hatch her dragons?", "The Dothraki Sea / Essos"),
    ("What castle guards the passage to the North?", "Moat Cailin")
]
for i, d in enumerate(geo_data):
    questions.append({
        "id": f"MH_{31+i:03d}", "question": d[0], "answer": d[1], "hops_required": 2,
        "entities_involved": [], "relationships_required": ["rules", "located_in"], "difficulty": "medium", "category": "geographic_political"
    })

# 5. Cross Domain
cross_data = [
    ("What religion is practiced by the founder of the house that won the Battle of the Bastards?", "Old Gods of the Forest"),
    ("Who is the leader of the group that defends the wall located in the North?", "Jon Snow / Commander of the Night's Watch"),
    ("Which house rules the region where the Red Wedding took place?", "House Frey / House Tully"),
    ("Who forged the sword Ice owned by the lord of Winterfell?", "Valyrian Freehold (Valyrian Steel)"),
    ("What is the sigil of the house that rules the Westerlands?", "A golden lion"),
    ("Which character has a direwolf named Ghost and belongs to the Night's Watch?", "Jon Snow"),
    ("What house rules the region where the Citadel is located?", "House Tyrell"),
    ("Who is the father of the person who burned the Great Sept of Baelor?", "Tywin Lannister"),
    ("Which Free City is home to the Iron Bank?", "Braavos"),
    ("What disease did the daughter of the lord of Dragonstone have?", "Greyscale")
]
for i, d in enumerate(cross_data):
    questions.append({
        "id": f"MH_{41+i:03d}", "question": d[0], "answer": d[1], "hops_required": 3,
        "entities_involved": [], "relationships_required": ["practices", "rules", "participated"], "difficulty": "hard", "category": "cross_domain"
    })

os.makedirs('evaluation', exist_ok=True)
with open('evaluation/questions.json', 'w') as f:
    json.dump(questions, f, indent=2)
