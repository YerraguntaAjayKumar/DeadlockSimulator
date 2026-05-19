/*
 * cycle_detection.cpp
 * --------------------
 * Detects cycles in a directed graph using Depth First Search (DFS).
 *
 * WHY CYCLE DETECTION?
 * In a Resource Allocation Graph (RAG), a cycle means a deadlock exists
 * (when each resource type has exactly one instance).
 *
 * INPUTS (via stdin):
 *   Line 1: V (number of vertices/nodes), E (number of edges)
 *   Next E lines: u v (directed edge from u to v)
 *
 * OUTPUT (via stdout):
 *   CYCLE_FOUND or NO_CYCLE
 *   Step-by-step DFS traversal
 */

#include <iostream>
#include <vector>
#include <string>

using namespace std;

// Adjacency list to represent the directed graph
vector<vector<int>> adj;
int V; // number of vertices

/*
 * DFS function to detect cycle.
 * visited[v] = true means node v has been visited in some DFS call.
 * recStack[v] = true means node v is currently in the DFS recursion stack.
 * If we reach a node that's already in the recursion stack, we found a cycle!
 */
bool dfsCycleDetect(int node, vector<bool>& visited, vector<bool>& recStack, vector<int>& path) {
    visited[node] = true;
    recStack[node] = true;
    path.push_back(node); // track current DFS path

    cout << "  Visiting node " << node << " | Path: ";
    for (int p : path) cout << p << " ";
    cout << endl;

    // Explore all neighbors of current node
    for (int neighbor : adj[node]) {
        if (!visited[neighbor]) {
            // Neighbor not yet visited — recurse deeper
            if (dfsCycleDetect(neighbor, visited, recStack, path))
                return true;
        } else if (recStack[neighbor]) {
            // Neighbor is already in the current path — CYCLE FOUND!
            cout << "  Cycle detected! Node " << neighbor << " is already in the current path." << endl;
            return true;
        }
    }

    // Backtrack: remove current node from recursion stack
    recStack[node] = false;
    path.pop_back();
    return false;
}

int main() {
    int E; // number of edges
    cin >> V >> E;

    adj.resize(V);

    cout << "STEP: Reading graph with " << V << " nodes and " << E << " edges." << endl;

    // Read each directed edge
    for (int i = 0; i < E; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        cout << "  Edge: " << u << " -> " << v << endl;
    }
    cout << endl;

    vector<bool> visited(V, false);
    vector<bool> recStack(V, false);
    vector<int> path;

    cout << "STEP: Running DFS Cycle Detection..." << endl;

    // Run DFS from every unvisited node (graph may be disconnected)
    for (int i = 0; i < V; i++) {
        if (!visited[i]) {
            cout << "STEP: Starting DFS from node " << i << endl;
            if (dfsCycleDetect(i, visited, recStack, path)) {
                cout << endl << "RESULT: CYCLE_FOUND" << endl;
                cout << "A cycle exists in the graph — DEADLOCK detected!" << endl;
                return 0;
            }
        }
    }

    cout << endl << "RESULT: NO_CYCLE" << endl;
    cout << "No cycle found — system is DEADLOCK FREE." << endl;

    return 0;
}
