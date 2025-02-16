import distributed.node
import requests
from flask import request, jsonify, render_template, Blueprint
from distributed.protocol_logic import find_successor, is_between
import distributed.node as chord

chord_routes = Blueprint('chord', __name__)


@chord_routes.route('/find_successor', methods=['POST'])
def find_successor_endpoint():
    """ print("\n[find_successor_endpoint] Received request") """
    try:
        data = request.json
        key = int(data['key'])
        """ print(f"Looking for successor of {key}") """
        successor = find_successor(key)
        """ print(f"Returning successor: {successor}") """
        return jsonify(successor)
    except (KeyError, ValueError) as e:
        print(f"Invalid request: {str(e)}")
        return jsonify({"error": "Invalid key format"}), 400


@chord_routes.route('/join', methods=['POST'])
def join_network():
    try:
        data = request.json
        bootstrap = data

        # Get successor from bootstrap node
        response = requests.post(
            f"http://{bootstrap['ip']}:{bootstrap['port']}/find_successor",
            json={"key": chord.current_node.id}
        )
        successor = response.json()

        # Set initial state
        with chord.current_node.lock:
            chord.current_node.successor = successor
            chord.current_node.predecessor = None

            # Immediate notification to successor
            requests.post(
                f"http://{successor['ip']}:{successor['port']}/notify",
                json=chord.current_node.to_dict()
            )

        return jsonify(chord.current_node.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        print(f"Join failed: {str(e)}")
        return jsonify({"error": str(e)}), 503


@chord_routes.route('/notify', methods=['POST'])
def handle_notify():
    candidate = request.json
    with chord.current_node.lock:
        # Always accept first notification
        if chord.current_node.predecessor is None:
            chord.current_node.predecessor = candidate
            print(f"Set initial predecessor to {candidate['id']}")
        # Update if candidate is between current predecessor and self
        elif is_between(candidate['id'], chord.current_node.predecessor['id'], chord.current_node.id):
            chord.current_node.predecessor = candidate
            print(f"Updated predecessor to {candidate['id']}")

        # Ensure successor is set if null
        if chord.current_node.successor is None:
            chord.current_node.successor = candidate
            print(f"Set successor to {candidate['id']}")

    return jsonify({"status": "ok"})


@chord_routes.route('/finger', methods=['GET'])
def get_finger():
    with chord.current_node.lock:
        return jsonify([entry for entry in chord.current_node.finger]), 200


@chord_routes.route('/gui', methods=['GET'])
def chord_gui():
    return render_template('gui.html', node=chord.current_node.to_dict())


@chord_routes.route('/state', methods=['GET'])
def get_state():
    return jsonify(chord.current_node.to_dict())

# @chord_routes.route('/network_size', methods=['GET'])
# def network_size():
#     visited = set()
#     size = 1
#     current = chord.current_node.successor

#     while current and current['id'] != chord.current_node.id:
#         if current['id'] in visited:
#             break
#         visited.add(current['id'])
#         size += 1
#         try:
#             current = requests.get(
#                 f"http://{current['ip']}:{current['port']}/find_successor"
#             ).json()
#         except requests.RequestException:
#             break

# return jsonify({"size": size})
