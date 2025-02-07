from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from game_logic import GameEngine, Player, Field, FieldAction
import random
import string
import logging


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klucz_sejmowy_123'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

active_games = {}
players = {}

class GameRoom:  
    def __init__(self, code, host_name):  
        self.code = code  
        self.players = []  
        self.game_engine = GameEngine()  
        self.status = "lobby"  
        self.host_name = host_name  
        self.host_id = None  
        self.current_player_index = 0  

    @property  
    def current_player(self):  
        if self.players:  
            return self.players[self.current_player_index % len(self.players)]  
        return None  

    def next_turn(self):  
        if self.players:  
            self.current_player_index = (self.current_player_index + 1) % len(self.players)  
        # Nie ustawiamy current_player bezpośrednio, używamy property  

    def add_player(self, player_id, name, avatar):  
        player = Player(player_id, name, avatar)  
        self.game_engine.add_player(player)  
        self.players.append(player_id)  

        if name == self.host_name and not self.host_id:  
            self.host_id = player_id  

        return player
    
@app.route('/')
def lobby():
    return render_template('lobby.html')

@app.route('/game/<game_code>')
def game(game_code):
    return render_template('game.html', game_code=game_code)

def generate_game_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('get_games_list')
def handle_get_games_list():
    games_list = [
        {
            'code': game.code,
            'players': len(game.players)
        }
        for game in active_games.values()
        if game.status == 'lobby'
    ]
    print(f"Sending games list: {games_list}")
    emit('games_list', games_list)

def broadcast_games_list():
    games_list = [
        {
            'code': game.code,
            'players': len(game.players)
        }
        for game in active_games.values()
        if game.status == 'lobby'
    ]
    print(f"Broadcasting games list: {games_list}")
    socketio.emit('games_list', games_list)

@socketio.on('create_game')
def handle_create_game(data):
    try:
        game_code = generate_game_code()
        host_name = data['name'].strip()
        host_avatar = data['avatar']
        room = GameRoom(game_code, host_name)
        active_games[game_code] = room

        player_id = request.sid
        player = room.add_player(player_id, host_name, host_avatar)
        players[player_id] = (game_code, player)

        join_room(game_code)
        session['game_code'] = game_code

        emit('game_created', {'game_code': game_code})

        emit('room_state', {
            'status': room.status,
            'players': [{
                **player.serialize(),
                'is_host': True
            }],
            'board': [field.serialize() for field in room.game_engine.board],
            'game_code': game_code
        }, room=player_id)

        logging.info(f"Gra utworzona: {game_code} przez {host_name}")
        broadcast_games_list()
    except Exception as e:
        logging.error(f"Błąd tworzenia gry: {str(e)}")
        emit('error', {'message': 'Błąd tworzenia gry!'})

@socketio.on('join_game')
def handle_join_game(data):
    try:
        game_code = data['game_code'].upper().strip()
        name = data['name'].strip()
        avatar = data['avatar']

        if not game_code:
            emit('error', {'message': 'Podaj kod gry!'})
            return
        if not name:
            emit('error', {'message': 'Podaj swoją nazwę!'})
            return

        if game_code not in active_games:
            emit('error', {'message': 'Nieprawidłowy kod gry!'})
            return

        room = active_games[game_code]
        player_id = request.sid

        existing_player = next(
            (p for p in room.game_engine.players.values() if p.name == name), 
            None
        )

        if existing_player:
            old_id = existing_player.id
            existing_player.id = player_id

            if existing_player.name == room.host_name:
                room.host_id = player_id

            if old_id in room.players:
                room.players.remove(old_id)
            room.players.append(player_id)

            if old_id in players:
                del players[old_id]
            players[player_id] = (game_code, existing_player)
            player = existing_player
        else:
            if len(room.players) >= 6:
                emit('error', {'message': 'Gra jest pełna!'})
                return
            player = room.add_player(player_id, name, avatar)
            players[player_id] = (game_code, player)

        join_room(game_code)
        session['game_code'] = game_code

        is_host = (name == room.host_name)

        emit('room_state', {
            'status': room.status,
            'players': [{
                **p.serialize(),
                'is_host': (p.name == room.host_name)
            } for p in room.game_engine.players.values()],
            'board': [field.serialize() for field in room.game_engine.board],
            'is_host': is_host,
            'game_code': game_code
        }, room=player_id)

        emit('players_update', {
            'players': [{
                'id': p.id, 
                'name': p.name, 
                'is_host': (p.name == room.host_name)
            } for p in room.game_engine.players.values()],
            'game_code': game_code
        }, room=game_code)

        emit('game_joined', {'game_code': game_code})
        socketio.start_background_task(broadcast_games_list)

    except Exception as e:
        logging.error(f"Błąd dołączania: {str(e)}")
        emit('error', {'message': 'Błąd systemowy!'})

@socketio.on('start_game')
def handle_start_game():
    try:
        player_id = request.sid
        if player_id not in players:
            emit('error', {'message': 'Nie jesteś w grze!'})
            return

        game_code, player = players[player_id]
        room = active_games.get(game_code)

        if not room or player.name != room.host_name:
            emit('error', {'message': 'Tylko host może rozpocząć grę!'})
            return

        room.status = "in_progress"
        room.game_engine.initialize_game()

        emit('game_started', {
            'status': 'in_progress',
            'board': [field.serialize() for field in room.game_engine.board],
            'players': [{
                **p.serialize(),
                'is_host': (p.name == room.host_name)
            } for p in room.game_engine.players.values()],
            'current_player': room.current_player
        }, room=game_code)

        broadcast_games_list()

    except Exception as e:
        logging.error(f"Błąd startu gry: {str(e)}")
        emit('error', {'message': 'Błąd inicjalizacji gry!'})

@socketio.on('get_items')
def handle_get_items():
    try:
        player_id = request.sid
        if player_id not in players:
            emit('error', {'message': 'Nie znaleziono gracza!'})
            return

        game_code, player = players[player_id]
        room = active_games.get(game_code)

        if not room:
            emit('error', {'message': 'Nie znaleziono gry!'})
            return

        items = room.game_engine.items
        emit('item_list', {'items': items})

    except Exception as e:
        logging.error(f"Błąd pobierania przedmiotów: {str(e)}")
        emit('error', {'message': 'Błąd podczas pobierania listy przedmiotów!'})
        
@socketio.on('player_action')
def handle_player_action(data):
    try:
        player_id = request.sid
        if player_id not in players:
            emit('error', {'message': 'Nie znaleziono gracza!'})
            return

        game_code, player = players[player_id]
        room = active_games.get(game_code)

        if not room or room.status != "in_progress":
            emit('error', {'message': 'Gra nie jest aktywna!'})
            return

        if room.current_player != player_id:
            emit('error', {'message': 'Nie twoja tura!'})
            return

        action_type = data.get('type')
        logging.info(f"Otrzymano akcję: {action_type}")

        if action_type == 'roll_dice':
            steps = random.randint(1, 6)
            board_size = len(room.game_engine.board)
            current_position = player.position

            forward_position = (current_position + steps) % board_size
            backward_position = (current_position - steps) % board_size

            emit('choose_move', {
                'steps': steps,
                'possible_positions': [forward_position, backward_position]
            }, room=player_id)

            emit('player_rolled', {
                'player_name': player.name,
                'steps': steps
            }, room=game_code, include_self=False)

        elif action_type == 'move':
            new_position = data.get('new_position')

            if new_position is None or not isinstance(new_position, int):
                emit('error', {'message': 'Nieprawidłowe dane ruchu!'})
                return

            player.position = new_position
            effect = room.game_engine.handle_field_effect(player)

            players_on_field = [p for p in room.game_engine.players.values() if p.position == new_position and p.id != player_id]

            emit('game_update', {
                'players': [{
                    **p.serialize(),
                    'is_host': (p.name == room.host_name)
                } for p in room.game_engine.players.values()],
                'effect': f"Ruszyłeś się na pole {new_position + 1}. {effect}",
                'current_player': room.current_player,
                'board': [field.serialize() for field in room.game_engine.board],
                'just_moved': True,
                'can_perform_action': True
            }, room=game_code)

            if players_on_field:
                emit('confrontation_available', {
                    'players': [p.name for p in players_on_field]
                }, room=player_id)

            field = room.game_engine.board[new_position]
            emit('field_actions', {
                'fieldType': field.type,
                'actions': [action.serialize() for action in field.actions]
            }, room=player_id)

        elif action_type == 'field_action':
            field_action_type = data.get('action_type')
            logging.info(f"Akcja pola: {field_action_type}")

            if field_action_type == 'buy_item':
                item_name = data.get('item_name')
                if not item_name:
                    emit('error', {'message': 'Nie wybrano przedmiotu!'})
                    return
                response = room.game_engine.buy_item(player_id, item_name)
            else:
                response = room.game_engine.handle_field_action(player, field_action_type)

            emit('game_update', {
                'players': [{
                    **p.serialize(),
                    'is_host': (p.name == room.host_name)
                } for p in room.game_engine.players.values()],
                'effect': response,
                'current_player': room.current_player,
                'board': [field.serialize() for field in room.game_engine.board],
                'just_moved': False,
                'can_perform_action': False
            }, room=game_code)

            room.next_turn()
            emit('turn_ended', {'next_player': room.current_player}, room=game_code)

        elif action_type == 'start_confrontation':
            players_on_field = [p for p in room.game_engine.players.values() if p.position == player.position]
            for p in players_on_field:
                emit('start_confrontation', {
                    'players': [{'id': pl.id, 'name': pl.name} for pl in players_on_field]
                }, room=p.id)

        elif action_type == 'end_turn':
            room.next_turn()
            emit('turn_ended', {'next_player': room.current_player}, room=game_code)

        elif action_type == 'get_items':
            items = room.game_engine.items
            emit('item_list', {'items': items})

        else:
            emit('error', {'message': 'Nieznana akcja!'})

    except Exception as e:
        logging.error(f"Błąd akcji: {str(e)}")
        emit('error', {'message': 'Błąd wykonania akcji!'})
        
@socketio.on('confrontation_roll')
def handle_confrontation_roll():
    try:
        player_id = request.sid
        print(f"Confrontation roll received from player {player_id}")
        if player_id not in players:
            print(f"Player {player_id} not found")
            emit('error', {'message': 'Nie znaleziono gracza!'})
            return

        game_code, player = players[player_id]
        print(f"Player {player.name} in game {game_code}")
        room = active_games.get(game_code)

        if not room or room.status != "in_progress":
            print(f"Game {game_code} is not active")
            emit('error', {'message': 'Gra nie jest aktywna!'})
            return

        roll = random.randint(1, 6)
        print(f"Player {player.name} rolled {roll}")
        emit('confrontation_roll_result', {
            'player_id': player_id,
            'player_name': player.name,
            'roll': roll,
            'popularity': player.popularity,
            'influence': player.influence
        }, room=game_code)
        print(f"Confrontation roll result sent for player {player.name}")

    except Exception as e:
        logging.error(f"Błąd rzutu w konfrontacji: {str(e)}")
        emit('error', {'message': 'Błąd wykonania akcji!'})

@socketio.on('end_confrontation')
def handle_end_confrontation(data):
    try:
        player_id = request.sid
        if player_id not in players:
            emit('error', {'message': 'Nie znaleziono gracza!'})
            return

        game_code, player = players[player_id]
        room = active_games.get(game_code)

        if not room or room.status != "in_progress":
            emit('error', {'message': 'Gra nie jest aktywna!'})
            return

        winner_id = data.get('winner_id')
        loser_id = data.get('loser_id')

        winner = room.game_engine.players.get(winner_id)
        loser = room.game_engine.players.get(loser_id)

        if winner and loser:
            winner.popularity += 10
            winner.influence += 5
            loser.popularity = max(0, loser.popularity - 10)
            loser.influence = max(0, loser.influence - 5)

        emit('confrontation_result', {
            'winner': winner.name,
            'loser': loser.name
        }, room=game_code)

        # Zmiana tury po konfrontacji
        room.current_player_index = (room.current_player_index + 1) % len(room.players)

        emit('game_update', {
            'players': [{
                **p.serialize(),
                'is_host': (p.name == room.host_name)
            } for p in room.game_engine.players.values()],
            'board': [field.serialize() for field in room.game_engine.board],
            'current_player': room.current_player
        }, room=game_code)

    except Exception as e:
        logging.error(f"Błąd zakończenia konfrontacji: {str(e)}")
        emit('error', {'message': 'Błąd wykonania akcji!'})

@socketio.on('field_action')
def handle_field_action(data):
    try:
        player_id = request.sid
        if player_id not in players:
            emit('error', {'message': 'Nie znaleziono gracza!'})
            return

        game_code, player = players[player_id]
        room = active_games.get(game_code)

        if not room or room.status != "in_progress":
            emit('error', {'message': 'Gra nie jest aktywna!'})
            return

        action_type = data.get('action_type')

        if action_type == "buy_item":
            item_name = data.get("item_name")
            response = room.game_engine.buy_item(player_id, item_name)
            emit('game_update', {
                'effect': response,
                'players': [{
                    **p.serialize(),
                    'is_host': (p.name == room.host_name)
                } for p in room.game_engine.players.values()],
                'current_player': room.current_player,
                'board': [field.serialize() for field in room.game_engine.board]
            }, room=game_code)
            return

        effect = room.game_engine.handle_field_action(player, action_type)

        emit('game_update', {
            'players': [{
                **p.serialize(),
                'is_host': (p.name == room.host_name)
            } for p in room.game_engine.players.values()],
            'effect': effect,
            'current_player': room.current_player,
            'board': [field.serialize() for field in room.game_engine.board],
            'just_moved': False
        }, room=game_code)

    except Exception as e:
        logging.error(f"Błąd akcji pola: {str(e)}")
        emit('error', {'message': 'Błąd wykonania akcji!'})

@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    if player_id in players:
        game_code, _ = players[player_id]
        room = active_games.get(game_code)
        if room:
            if player_id in room.game_engine.players:
                del room.game_engine.players[player_id]
            if player_id in room.players:
                room.players.remove(player_id)
            leave_room(game_code)
            del players[player_id]
            emit('players_update', {
                'players': [{
                    'id': p.id, 
                    'name': p.name, 
                    'is_host': (p.name == room.host_name)
                } for p in room.game_engine.players.values()],
                'game_code': game_code
            }, room=game_code)
            broadcast_games_list()

if __name__ == '__main__':
    socketio.run(app, debug=True)