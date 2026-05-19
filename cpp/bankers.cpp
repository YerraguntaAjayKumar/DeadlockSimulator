/*
 * bankers.cpp
 * -----------
 * Implements the Banker's Algorithm for Deadlock Avoidance.
 *
 * HOW IT WORKS:
 * The Banker's Algorithm checks if the system is in a "safe state".
 * A safe state means there exists at least one sequence (called a safe sequence)
 * in which all processes can finish without causing a deadlock.
 *
 * INPUTS (via stdin):
 *   Line 1: n (number of processes), m (number of resources)
 *   Next n lines: Allocation matrix (n x m)
 *   Next n lines: Max matrix (n x m)
 *   Last line: Available vector (1 x m)
 *
 * OUTPUT (via stdout):
 *   SAFE or UNSAFE
 *   Step-by-step explanation
 *   Safe sequence (if safe)
 */

#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    int n, m; // n = number of processes, m = number of resources
    cin >> n >> m;

    // Allocation[i][j] = number of resource j currently held by process i
    vector<vector<int>> allocation(n, vector<int>(m));
    // Max[i][j] = maximum demand of resource j by process i
    vector<vector<int>> maxMatrix(n, vector<int>(m));
    // Available[j] = number of available instances of resource j
    vector<int> available(m);

    // Read allocation matrix
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            cin >> allocation[i][j];

    // Read max matrix
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            cin >> maxMatrix[i][j];

    // Read available vector
    for (int j = 0; j < m; j++)
        cin >> available[j];

    // Calculate Need matrix: Need[i][j] = Max[i][j] - Allocation[i][j]
    // This tells us how many more resources process i might still need
    vector<vector<int>> need(n, vector<int>(m));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            need[i][j] = maxMatrix[i][j] - allocation[i][j];

    // Print the Need matrix for transparency
    cout << "STEP: Calculated Need Matrix (Max - Allocation):" << endl;
    for (int i = 0; i < n; i++) {
        cout << "  Process P" << i << ": ";
        for (int j = 0; j < m; j++)
            cout << need[i][j] << " ";
        cout << endl;
    }
    cout << endl;

    // Banker's Safety Algorithm
    // finish[i] = true means process i has been allocated and finished
    vector<bool> finish(n, false);
    // work = copy of available; simulates freeing resources as processes finish
    vector<int> work = available;
    // safeSeq stores the safe sequence of processes
    vector<int> safeSeq;

    cout << "STEP: Starting Safety Check..." << endl;
    cout << "  Initial Work (Available): ";
    for (int j = 0; j < m; j++) cout << work[j] << " ";
    cout << endl << endl;

    int count = 0; // counts how many processes have finished
    while (count < n) {
        bool found = false;
        for (int i = 0; i < n; i++) {
            // Try to find an unfinished process whose needs can be satisfied
            if (!finish[i]) {
                bool canAllocate = true;
                for (int j = 0; j < m; j++) {
                    // If the process needs more than what's available, skip it
                    if (need[i][j] > work[j]) {
                        canAllocate = false;
                        break;
                    }
                }

                if (canAllocate) {
                    // Process i can proceed — simulate giving it resources
                    cout << "STEP: Process P" << i << " can proceed." << endl;
                    cout << "  Need: ";
                    for (int j = 0; j < m; j++) cout << need[i][j] << " ";
                    cout << "<= Work: ";
                    for (int j = 0; j < m; j++) cout << work[j] << " ";
                    cout << endl;

                    // After it finishes, it releases all its allocated resources
                    for (int j = 0; j < m; j++)
                        work[j] += allocation[i][j];

                    finish[i] = true;
                    safeSeq.push_back(i);
                    count++;
                    found = true;

                    cout << "  After P" << i << " releases, Work becomes: ";
                    for (int j = 0; j < m; j++) cout << work[j] << " ";
                    cout << endl << endl;
                }
            }
        }

        // If no process could proceed in this full pass, the system is UNSAFE
        if (!found) {
            cout << "RESULT: UNSAFE" << endl;
            cout << "No process could proceed with current available resources." << endl;
            cout << "DEADLOCK may occur!" << endl;
            return 0;
        }
    }

    // All processes finished — system is SAFE
    cout << "RESULT: SAFE" << endl;
    cout << "Safe Sequence: ";
    for (int i = 0; i < n; i++) {
        cout << "P" << safeSeq[i];
        if (i != n - 1) cout << " -> ";
    }
    cout << endl;

    return 0;
}
