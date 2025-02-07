import random
import re

def extract_number(text):
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else 0

class Player:
    def __init__(self, player_id, name):
        self.id = player_id
        self.name = name
        self.position = 0
        self.popularity = 50
        self.influence = 10
        self.budget = 100000
        self.cards = []
        
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'popularity': self.popularity,
            'influence': self.influence,
            'budget': self.budget
        }

class FieldAction:
    def __init__(self, name, description, effect_type):
        self.name = name
        self.description = description
        self.effect_type = effect_type
        
    def serialize(self):
        return {
            'name': self.name,
            'description': self.description,
            'effect_type': self.effect_type
        }

class Field:
    def __init__(self, type_name, description, actions):
        self.type = type_name
        self.description = description
        self.actions = actions
        
    def serialize(self):
        return {
            'type': self.type,
            'description': self.description,
            'effect': self.description,  # dla kompatybilności z poprzednim kodem
            'actions': [action.serialize() for action in self.actions]
        }

class Player:
    def __init__(self, player_id, name, avatar):
        self.id = player_id
        self.name = name
        self.avatar = avatar
        self.position = 0
        self.popularity = 50
        self.influence = 10
        self.budget = 100000
        self.items = []  # Lista posiadanych przedmiotów
        
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'avatar': self.avatar,
            'position': self.position,
            'popularity': self.popularity,
            'influence': self.influence,
            'budget': self.budget,
            'items': self.items  # Dodajemy przedmioty do serializacji
        }

class GameEngine:
    def __init__(self):
        self.players = {}
        self.board = []
        self.items = {
            "📓 Notatnik": {
                "price": 5000,
                "effects": {
                    "influence": 5,
                    "description": "Zwiększa wpływy o 5"
                }
            },
            "📱 Telefon służbowy": {
                "price": 10000,
                "effects": {
                    "popularity": 10,
                    "description": "Zwiększa popularność o 10"
                }
            },
            "🙋 Doradca PR": {
                "price": 20000,
                "effects": {
                    "popularity": 15,
                    "influence": 10,
                    "description": "Zwiększa popularność o 15 i wpływy o 10"
                }
            },
            "📊 Badanie opinii": {
                "price": 15000,
                "effects": {
                    "popularity": 20,
                    "description": "Zwiększa popularność o 20"
                }
            }
        }
        self.current_turn = 0
        self.voting = None
        self.initialize_board()

    def next_turn(self):
        player_ids = list(self.players.keys())
        self.current_turn = (self.current_turn + 1) % len(player_ids)
        return player_ids[self.current_turn]

    def buy_item(self, player_id, item_name):
        if player_id not in self.players:
            return "Błąd: Nie znaleziono gracza!"

        if item_name not in self.items:
            return "Błąd: Nie ma takiego przedmiotu!"

        player = self.players[player_id]
        item = self.items[item_name]

        if player.budget < item["price"]:
            return "Nie masz wystarczająco środków!"

        if item_name in player.items:
            return "Już posiadasz ten przedmiot!"

        # Pobierz opłatę
        player.budget -= item["price"]

        # Dodaj przedmiot do ekwipunku
        if not hasattr(player, 'items'):
            player.items = []
        player.items.append(item_name)

        # Zastosuj efekty przedmiotu
        effects = item["effects"]
        if "popularity" in effects:
            player.popularity = min(100, player.popularity + effects["popularity"])
        if "influence" in effects:
            player.influence += effects["influence"]

        return f"Kupiłeś {item_name}! {effects['description']}"


        
    def initialize_board(self):
        self.board = [
            Field("Start", "Rozpoczynasz kadencję w Sejmie!", [
                FieldAction("Odbierz mandat", "Twoja polityczna przygoda się zaczyna. Otrzymujesz 5000 zł budżetu.", "receive_diet")
            ]),
            Field("Głosowanie", "Czas na ważne głosowanie w Sejmie!", [
                FieldAction("Głosuj Za", "Twoja partia jest zadowolona. +10 wpływów", "vote_for"),
                FieldAction("Głosuj Przeciw", "Ryzykujesz konflikt, ale zyskujesz niezależność. +5 popularności", "vote_against"),
                FieldAction("Wstrzymaj się", "Bezpieczna decyzja, ale bez efektów.", "vote_abstain")
            ]),
            Field("Ministerstwo Finansów", "Masz okazję zdobyć dodatkowe fundusze!", [
                FieldAction("Złóż wniosek o dotację", "Otrzymujesz 20 000 zł na swoją kampanię!", "grant_money"),
                FieldAction("Zignoruj dotację", "Twoja reputacja pozostaje czysta, ale nic nie zyskujesz.", "ignore_grant")
            ]),
            Field("Debata Telewizyjna", "Zmierzasz się w debacie politycznej!", [
                FieldAction("Mów mądrze", "Twoje argumenty przekonują wyborców. +15% popularności", "smart_speech"),
                FieldAction("Atakuj przeciwnika", "Twoja partia zyskuje, ale media są przeciw tobie. +10 wpływów, -5% popularności", "attack_opponent"),
                FieldAction("Unikaj tematu", "Ludzie uznają cię za nudnego. -5% popularności", "dodge_question")
            ]),
            Field("Afera Korupcyjna", "Dziennikarze śledczy znaleźli podejrzane powiązania!", [
                FieldAction("Zaprzeczaj wszystkiemu", "Niektórzy ci wierzą, ale ryzyko pozostaje. -10% popularności", "deny_scandal"),
                FieldAction("Przyznaj się i przeproś", "Ludzie cenią szczerość. -10 000 zł, ale +5% popularności", "admit_scandal"),
                FieldAction("Zrzuć winę na asystenta", "Tracisz wpływy, ale unikasz kary. -10 wpływów", "blame_assistant")
            ]),
            Field("Protest Wyborców", "Ludzie niezadowoleni z twoich decyzji zbierają się pod Sejmem!", [
                FieldAction("Wyjdź do protestujących", "Pokazujesz ludzką twarz. +10% popularności", "support_protesters"),
                FieldAction("Ignoruj protest", "Ludzie są wściekli. -15% popularności", "ignore_protest"),
                FieldAction("Wezwij policję", "Opozycja oskarża cię o brutalność. -5% popularności, ale +10 wpływów", "call_police")
            ]),
            Field("Dziennikarze Śledczy", "Media badają twoją przeszłość!", [
                FieldAction("Opublikuj własny artykuł", "Kontrolujesz narrację, ale kosztuje to 5000 zł", "publish_article"),
                FieldAction("Nie komentuj", "Ryzykujesz, że sprawa urośnie w skandal.", "silent_mode"),
                FieldAction("Zatrudnij doradcę PR", "Za 15 000 zł ratujesz swoją reputację. +10% popularności", "hire_PR")
            ]),
            Field("Komisja Śledcza", "Jesteś wezwany przed komisję sejmową!", [
                FieldAction("Współpracuj", "Zyskujesz sympatię wyborców. +5% popularności", "cooperate"),
                FieldAction("Matacz", "Nie dają ci spokoju. -5% popularności, ale +10 wpływów", "manipulate"),
                FieldAction("Zostań świadkiem koronnym", "Zdradzasz kolegów z partii! +20% popularności, -20 wpływów", "whistleblower")
            ]),
            Field("Lobbyści", "Wpływowe osoby oferują wsparcie...", [
                FieldAction("Przyjmij ofertę", "Zyskujesz 50 000 zł, ale ryzykujesz skandal.", "accept_lobby"),
                FieldAction("Odrzuć propozycję", "Zachowujesz honor, ale nic nie zyskujesz.", "reject_lobby"),
            ]),
            Field("Media Społecznościowe", "Twoje konto na Twitterze eksplodowało!", [
                FieldAction("Zamieść błyskotliwy tweet", "Zyskujesz 15% popularności", "post_tweet"),
                FieldAction("Wejdź w konflikt", "Zwiększasz wpływy, ale tracisz fanów. +10 wpływów, -5% popularności", "twitter_fight")
            ]),
            Field("Wybory", "Czas na sprawdzian twoich rządów!", [
                FieldAction("Prowadź kampanię", "Kosztuje 10 000 zł, ale daje 20% popularności", "election_campaign"),
                FieldAction("Zaufaj wyborcom", "Brak kosztów, ale ryzykujesz przegraną.", "trust_people")
            ]),
            Field("Kantyna", "Możesz kupić przydatne przedmioty", [
                FieldAction("Kup przedmiot", "Wydaj budżet na pomocne narzędzia", "buy_item")
            ]),
        ]
        
    def handle_field_action(self, player, action_type):
        field = self.board[player.position]
        for action in field.actions:
            if action.effect_type == action_type:
                effect = self.apply_action_effect(player, action_type)
                return effect
        return "Brak efektu"

    def apply_action_effect(self, player, action_type):
        effects = {
            "vote_for": ["Twoja partia jest zadowolona. +10 wpływów"],
            "vote_against": ["Masz odwagę, ale nie wszystkim się to podoba. +5% popularności, -5 wpływów"],
            "smart_speech": ["Twoje argumenty przekonały wyborców. +15% popularności"],
            "attack_opponent": ["Zyskujesz wpływy, ale media krytykują. +10 wpływów, -5% popularności"],
            "grant_money": ["Dotacja zatwierdzona! +20 000 zł"],
            "deny_scandal": ["Próbujesz się bronić. -10% popularności"],
            "admit_scandal": ["Ludzie doceniają twoją szczerość. -10 000 zł, ale +5% popularności"],
            "blame_assistant": ["Unikasz kary, ale ludzie ci nie ufają. -10 wpływów"],
            "support_protesters": ["Pokazujesz, że słuchasz wyborców. +10% popularności"],
            "call_police": ["Używasz siły. +10 wpływów, -5% popularności"],
            "publish_article": ["Media idą za twoją narracją. -5000 zł, ale +10% popularności"],
            "whistleblower": ["Zdobywasz sympatię wyborców, ale tracisz kontakty. +20% popularności, -20 wpływów"],
            "post_tweet": ["Twoje konto wybucha popularnością! +15% popularności"],
            "twitter_fight": ["Media się tobą interesują. +10 wpływów, -5% popularności"],
            "election_campaign": ["Inwestujesz w kampanię. -10 000 zł, ale +20% popularności"],
            "buy_coffee": ["Kofeina działa! -200 zł, +2% popularności"],
            "receive_diet": ["Pobierasz dietę poselską +20 000 zł"]
        }
        effect = random.choice(effects.get(action_type, ["Brak efektu"]))
        self.apply_effect(player, effect)
        return effect
      
    
    def apply_effect(self, player, effect):
        effects = effect.split(", ")
        for single_effect in effects:
            value = extract_number(single_effect)
            
            if "popularności" in single_effect:
                player.popularity = min(100, player.popularity + value if "+" in single_effect else player.popularity - value)
            elif "zł" in single_effect:
                player.budget += value * 1000 if "+" in single_effect else -value * 1000
            elif "wpływów" in single_effect:
                player.influence += value if "+" in single_effect else -value
            else:
                print(f"Nieobsłużony efekt: {effect}")  # Debugging

    def add_player(self, player):
        self.players[player.id] = player
        
    def initialize_game(self):
        # self.current_turn = 0
        self.current_turn = list(self.players.keys())[0]
        print(f"DEBUG: Dostępne przedmioty w kantynie: {self.items}")

        
    def move_player(self, player_id, steps):
        player = self.players[player_id]
        new_position = (player.position + steps) % len(self.board)
        player.position = new_position
        effect = self.handle_field_effect(player)
        self.next_turn()
        return effect
    
    def next_turn(self):
        player_ids = list(self.players.keys())  # Pobieramy listę ID graczy
        current_index = player_ids.index(self.current_turn)  # Znajdujemy obecnego gracza

        # Zmiana tury na następnego gracza (z pętlą cykliczną)
        next_index = (current_index + 1) % len(player_ids)
        self.current_turn = player_ids[next_index]

        print(f"Tura gracza: {self.players[self.current_turn].name}")  # Debugowanie

    def handle_field_effect(self, player):
        field = self.board[player.position]
        effect = None

        if field.type == 'Start':  # ✅ Poprawione
            player.budget += 10000
            effect = "+10 000 zł"
        elif field.type == 'Afera':
            effect = self.draw_scandal_card(player)
        elif field.type == 'Media':
            player.popularity = min(100, player.popularity + 10)
            effect = "+10% popularności"
        # elif field.type == 'Komisja':
        #     player.position = (player.position + 3) % len(self.board)
        #     effect = "Przesunięcie o 3 pola"
        #     subsequent_effect = self.handle_field_effect(player)
        #     if subsequent_effect:
        #         effect += " oraz " + subsequent_effect
        return effect

    def draw_scandal_card(self, player):
        scandals = [
            "Ujawniono tajne spotkania! -15% popularności",
            "Fałszywe oświadczenie majątkowe! -30k zł",
            "Konflikt interesów! -10 wpływów",
            "Hulanka w rządzie! +20% popularności"
        ]
        effect = random.choice(scandals)

        if "-%" in effect:
            value = extract_number(effect)
            player.popularity = max(0, player.popularity - value)
        elif "k zł" in effect:
            value = extract_number(effect)
            player.budget -= value * 1000
        elif "wpływów" in effect:
            value = extract_number(effect)
            player.influence = max(0, player.influence - value)
        elif "+%" in effect:
            value = extract_number(effect)
            player.popularity = min(100, player.popularity + value)

        return effect
