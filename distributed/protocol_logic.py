import time
from distributed.config import M, STABILIZE_INTERVAL
import distributed.node as chord
import requests


def is_between(key, start, end, inclusive=False):
    if start < end:
        return start < key <= end if inclusive else start < key < end
    return key > start or key <= end if inclusive else key > start or key < end

def find_successor(key):
    with chord.current_node.lock:
        if not chord.current_node.successor:
            return chord.current_node.to_dict()
        
        if is_between(key, chord.current_node.id, chord.current_node.successor['id'], inclusive=True):
            return chord.current_node.successor
            
        closest = chord.current_node.to_dict()
        for i, entry in enumerate(reversed(chord.current_node.finger)):
            if entry and is_between(entry['id'], chord.current_node.id, key):
                # Verify if the finger entry is alive
                try:
                    requests.get(f"http://{entry['ip']}:{entry['port']}/state", timeout=2)
                    closest = entry
                    break
                except requests.RequestException:
                    continue  # Skip dead nodes
                
        try:
            response = requests.post(
                f"http://{closest['ip']}:{closest['port']}/find_successor",
                json={"key": key}
            )
            return response.json()
        except requests.RequestException:
            return chord.current_node.successor
        
def stabilize():
    while True:
        time.sleep(STABILIZE_INTERVAL)
        try:
            # 1. Get current state snapshot
            with chord.current_node.lock:
                successor = chord.current_node.successor.copy() if chord.current_node.successor else None
                node_id = chord.current_node.id
                local_state = chord.current_node.to_dict()

            # 2. Check successor's predecessor
            if successor:
                try:
                    # Get successor's state
                    response = requests.get(
                        f"http://{successor['ip']}:{successor['port']}/state",
                        timeout=2
                    )
                    successor_state = response.json()
                    successor_predecessor = successor_state.get("predecessor")

                    # Verify if successor's predecessor is alive and valid
                    if successor_predecessor:
                        # Check if the predecessor is actually alive
                        try:
                            requests.get(
                                f"http://{successor_predecessor['ip']}:{successor_predecessor['port']}/state",
                                timeout=2
                            )
                            predecessor_alive = True
                        except requests.RequestException:
                            predecessor_alive = False

                        # Update successor only if predecessor is alive and in range
                        if predecessor_alive and is_between(successor_predecessor['id'], node_id, successor['id']):
                            with chord.current_node.lock:
                                chord.current_node.successor = successor_predecessor
                                print(f"Updated successor to live node {successor_predecessor['id']}")

                    # Notify successor even if predecessor check fails
                    requests.post(
                        f"http://{successor['ip']}:{successor['port']}/notify",
                        json=local_state,
                        timeout=2
                    )

                except requests.RequestException as e:
                    print(f"Successor {successor['id']} unreachable: {str(e)}")
                    with chord.current_node.lock:
                        chord.current_node.successor = None

            # 3. Update finger table
            for i in range(M):
                start = (node_id + 2**i) % (2**M)
                finger_entry = find_successor(start)
                with chord.current_node.lock:
                    chord.current_node.finger[i] = finger_entry

        except Exception as e:
            print(f"Stabilization error: {str(e)}")

def check_predecessor():
    while True:
        time.sleep(STABILIZE_INTERVAL)
        try:
            with chord.current_node.lock:
                predecessor = chord.current_node.predecessor.copy() if chord.current_node.predecessor else None

            if predecessor:
                try:
                    # Check predecessor liveness
                    requests.get(
                        f"http://{predecessor['ip']}:{predecessor['port']}/state",
                        timeout=2
                    )
                except requests.RequestException:
                    print(f"Predecessor {predecessor['id']} is dead. Removing.")
                    with chord.current_node.lock:
                        chord.current_node.predecessor = None

        except Exception as e:
            print(f"Predecessor check error: {str(e)}")