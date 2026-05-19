/*
 * deadlock.cpp
 * ------------
 * Detects deadlock using a simplified Resource Allocation Graph (RAG).
 *
 * HOW IT WORKS:
 * - Each process and resource is a node in the graph.
 * - A "request edge" goes from a Process → Resource (process waiting for resource).
 * - An "assignment edge" goes from Resource → Process (resource held by process).
 * - If we find a CYCLE in this graph, a DEADLOCK exists.
 *
 * This file builds the RAG and then uses DFS to detect any cycle.
 *
 * INPUTS (via stdin):
 *   Line 1: n (processes), m (resources)
 *   Next n lines: Allocation matrix (which resources each process holds)
 *   Next n lines: Request matrix (which resources each process is waiting for)
 *
 * OUTPUT:
 *   Deadlock status and list of deadlocked processes (if any)
 */

#include <iostream>
#include <vector>
#include <string>

using namespace std;

/*
 * Node numbering scheme:
 *   Processes: nodes 0 to n-1
 *   Resources: nodes n to n+m-1
 *
 * This lets us put both in one graph for the RAG.
 */

int totalNodes;
vector<vector<int>> adj;

// DFS to detect cycle
bool dfs(int node, vector<bool>& visited, vector<bool>& recStack) {
    visited[node] = true;
    recStack[node] = true;

    for (int neighbor : adj[node]) {
        if (!visited[neighbor]) {
            if (dfs(neighbor, visited, recStack))
                return true;
        } else if (recStack[neighbor]) {
            return true; // cycle found
        }
    }

    recStack[node] = false;
    return false;
}

int main() {
    int n, m;
    cin >> n >> m;

    // Allocation[i][j] = 1 means process i holds resource j
    vector<vector<int>> allocation(n, vector<int>(m));
    // Request[i][j] = 1 means process i is waiting for resource j
    vector<vector<int>> request(n, vector<int>(m));

    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            cin >> allocation[i][j];

    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            cin >> request[i][j];

    // Total nodes = n processes + m resources
    totalNodes = n + m;
    adj.resize(totalNodes);

    cout << "STEP: Building Resource Allocation Graph (RAG)..." << endl;
    cout << "  Processes: P0 to P" << n-1 << " (nodes 0 to " << n-1 << ")" << endl;
    cout << "  Resources: R0 to R" << m-1 << " (nodes " << n << " to " << n+m-1 << ")" << endl << endl;

    // Build assignment edges: Resource j -> Process i (resource held by process)
    cout << "STEP: Adding Assignment Edges (Resource -> Process):" << endl;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (allocation[i][j] == 1) {
                int resourceNode = n + j; // resource j's node index
                adj[resourceNode].push_back(i); // R_j -> P_i
                cout << "  R" << j << " -> P" << i << endl;
            }
        }
    }
    cout << endl;

    // Build request edges: Process i -> Resource j (process waiting for resource)
    cout << "STEP: Adding Request Edges (Process -> Resource):" << endl;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (request[i][j] == 1) {
                int resourceNode = n + j; // resource j's node index
                adj[i].push_back(resourceNode); // P_i -> R_j
                cout << "  P" << i << " -> R" << j << endl;
            }
        }
    }
    cout << endl;

    // Run cycle detection on the RAG
    cout << "STEP: Running DFS to detect cycle in RAG..." << endl;
    vector<bool> visited(totalNodes, false);
    vector<bool> recStack(totalNodes, false);
    vector<int> deadlockedProcesses;

    bool deadlockFound = false;
    for (int i = 0; i < totalNodes; i++) {
        if (!visited[i]) {
            if (dfs(i, visited, recStack)) {
                deadlockFound = true;
            }
        }
    }

    // Identify which processes are deadlocked
    // (those that are waiting AND their requests cannot be satisfied)
    if (deadlockFound) {
        cout << endl << "RESULT: DEADLOCK_DETECTED" << endl;
        cout << "A cycle was found in the Resource Allocation Graph." << endl;

        // Find processes that are waiting for at least one resource
        cout << "Processes involved in deadlock: ";
        for (int i = 0; i < n; i++) {
            bool waiting = false;
            for (int j = 0; j < m; j++) {
                if (request[i][j] == 1) { waiting = true; break; }
            }
            if (waiting) {
                cout << "P" << i << " ";
                deadlockedProcesses.push_back(i);
            }
        }
        cout << endl;
    } else {
        cout << endl << "RESULT: NO_DEADLOCK" << endl;
        cout << "No cycle in RAG — system is safe from deadlock." << endl;
    }

    return 0;
}
