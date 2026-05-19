# utils.py
# --------
# Helper functions for input parsing, formatting, and subprocess calls.
# Keeps app.py clean by separating logic from UI.

import subprocess
import os
import pandas as pd


# ─── Path helpers ────────────────────────────────────────────────────────────

def get_executable_path(name):
    """
    Returns the full path to a compiled C++ executable.
    Looks inside the 'executables/' folder.
    Automatically adds .exe extension on Windows.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Add .exe extension on Windows if not already present
    if os.name == 'nt' and not name.endswith('.exe'):
        name += '.exe'
    return os.path.join(base_dir, "executables", name)


# ─── Input builders ──────────────────────────────────────────────────────────

def build_bankers_input(allocation, max_matrix, available):
    """
    Formats Python matrices into a string that bankers.cpp expects on stdin.

    Format:
      n m
      allocation row 0
      allocation row 1
      ...
      max row 0
      ...
      available values
    """
    n = len(allocation)
    m = len(available)
    lines = [f"{n} {m}"]

    for row in allocation:
        lines.append(" ".join(map(str, row)))

    for row in max_matrix:
        lines.append(" ".join(map(str, row)))

    lines.append(" ".join(map(str, available)))

    return "\n".join(lines)


def build_deadlock_input(allocation, request):
    """
    Formats matrices into stdin string for deadlock.cpp.

    Format:
      n m
      allocation matrix (n x m), values 0 or 1
      request matrix (n x m), values 0 or 1
    """
    n = len(allocation)
    m = len(allocation[0])
    lines = [f"{n} {m}"]

    for row in allocation:
        lines.append(" ".join(map(str, row)))

    for row in request:
        lines.append(" ".join(map(str, row)))

    return "\n".join(lines)


def build_cycle_input(num_nodes, edges):
    """
    Formats graph data for cycle_detection.cpp.

    Format:
      V E
      u v  (for each edge)
    """
    lines = [f"{num_nodes} {len(edges)}"]
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines)


# ─── Subprocess runner ───────────────────────────────────────────────────────

def run_cpp_executable(executable_name, input_data):
    """
    Runs a compiled C++ executable, passes input_data via stdin,
    and returns the output (stdout) as a string.

    Returns (output_string, error_string).
    """
    exe_path = get_executable_path(executable_name)

    # Check if the executable exists
    if not os.path.isfile(exe_path):
        return None, (
            f"Executable '{executable_name}' not found at {exe_path}.\n"
            "Please run: bash cpp/compile.sh"
        )

    try:
        result = subprocess.run(
            [exe_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10  # safety timeout (seconds)
        )
        return result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return None, "The C++ program took too long to respond (timeout)."

    except Exception as e:
        return None, f"Unexpected error running executable: {str(e)}"


# ─── Output parsers ──────────────────────────────────────────────────────────

def parse_bankers_result(output):
    """
    Parses bankers.cpp output.
    Returns dict: { 'safe': bool, 'sequence': list, 'steps': str }
    """
    if output is None:
        return {"safe": False, "sequence": [], "steps": ""}

    lines = output.strip().split("\n")
    is_safe = False
    sequence = []

    for line in lines:
        if "RESULT: SAFE" in line:
            is_safe = True
        if "Safe Sequence:" in line:
            # Extract P0 -> P2 -> P1 etc.
            seq_part = line.split("Safe Sequence:")[-1].strip()
            tokens = seq_part.replace("->", "").split()
            sequence = [t.strip() for t in tokens if t.strip()]

    return {
        "safe": is_safe,
        "sequence": sequence,
        "steps": output
    }


def parse_deadlock_result(output):
    """
    Parses deadlock.cpp output.
    Returns dict: { 'deadlock': bool, 'steps': str }
    """
    if output is None:
        return {"deadlock": False, "steps": ""}

    deadlock = "DEADLOCK_DETECTED" in output
    return {
        "deadlock": deadlock,
        "steps": output
    }


def parse_cycle_result(output):
    """
    Parses cycle_detection.cpp output.
    Returns dict: { 'cycle': bool, 'steps': str }
    """
    if output is None:
        return {"cycle": False, "steps": ""}

    cycle = "CYCLE_FOUND" in output
    return {
        "cycle": cycle,
        "steps": output
    }


# ─── Recovery logic ──────────────────────────────────────────────────────────

def suggest_recovery(allocation, max_matrix=None, available=None, process_names=None):
    """
    Suggests which process to terminate to recover from deadlock.
    
    Enhanced strategy: considers multiple factors:
    1. Resource efficiency (resources held vs remaining need)
    2. Total resource consumption (minimize wasted work)
    3. Priority to processes that would free the most critical resources
    
    Returns: (suggested_process_index, explanation_string)
    """
    if not allocation:
        return None, "No processes to analyze."

    n = len(allocation)
    
    # Calculate metrics for each process
    process_scores = []
    for i in range(n):
        total_held = sum(allocation[i])
        total_needed = sum(max_matrix[i]) if max_matrix and i < len(max_matrix) else total_held
        remaining_need = total_needed - total_held
        
        # Calculate efficiency score (lower is better for termination)
        # Factor 1: Resource efficiency (how much of their total need they've consumed)
        efficiency = total_held / max(total_needed, 1)
        
        # Factor 2: Resource consumption (lower is better)
        consumption = total_held
        
        # Factor 3: Critical resource impact (prioritize processes holding rare resources)
        critical_impact = 0
        if available:
            for j, av in enumerate(available):
                if allocation[i][j] > 0 and av == 0:  # Holding a scarce resource
                    critical_impact += allocation[i][j]
        
        # Combined score (lower is better candidate for termination)
        # Weight factors: efficiency (40%), consumption (30%), critical impact (30%)
        score = (efficiency * 0.4) + (consumption * 0.3) + (critical_impact * 0.3)
        
        process_scores.append({
            'index': i,
            'score': score,
            'total_held': total_held,
            'total_needed': total_needed,
            'remaining_need': remaining_need,
            'efficiency': efficiency,
            'critical_impact': critical_impact
        })
    
    # Sort by score (ascending - best candidate first)
    process_scores.sort(key=lambda x: x['score'])
    best_candidate = process_scores[0]
    
    name = process_names[best_candidate['index']] if process_names else f"P{best_candidate['index']}"
    
    explanation = (
        f"🛠️ **Recovery Suggestion: Terminate {name}**\n\n"
        f"**Analysis:**\n"
        f"• Total resources held: {best_candidate['total_held']} units\n"
        f"• Total resources needed: {best_candidate['total_needed']} units\n"
        f"• Completion percentage: {best_candidate['efficiency']:.1%}\n"
        f"• Critical resources held: {best_candidate['critical_impact']} units\n\n"
        f"**Reasoning:** This process has the optimal balance of:\n"
        f"1. **Low resource waste** - Minimal work lost\n"
        f"2. **High recovery impact** - Frees critical resources\n"
        f"3. **Strategic efficiency** - Best cost-benefit ratio\n\n"
        f"**All Process Rankings:**\n"
    )
    
    for rank, proc in enumerate(process_scores, 1):
        pname = process_names[proc['index']] if process_names else f"P{proc['index']}"
        marker = " ← **RECOMMENDED**" if proc['index'] == best_candidate['index'] else ""
        explanation += (
            f"{rank}. {pname}: Score={proc['score']:.2f} "
            f"(held={proc['total_held']}, efficiency={proc['efficiency']:.1%}){marker}\n"
        )
    
    return best_candidate['index'], explanation


# ─── Matrix display helpers ───────────────────────────────────────────────────

def matrix_to_dataframe(matrix, row_prefix="P", col_prefix="R"):
    """
    Converts a 2D Python list into a pandas DataFrame
    with nice row/column labels for display in Streamlit.
    """
    n = len(matrix)
    m = len(matrix[0]) if n > 0 else 0

    rows = [f"{row_prefix}{i}" for i in range(n)]
    cols = [f"{col_prefix}{j}" for j in range(m)]

    return pd.DataFrame(matrix, index=rows, columns=cols)


def vector_to_dataframe(vector, col_prefix="R"):
    """
    Converts a 1D Python list into a single-row pandas DataFrame.
    """
    m = len(vector)
    cols = [f"{col_prefix}{j}" for j in range(m)]
    return pd.DataFrame([vector], index=["Available"], columns=cols)


# ─── Resource Control Functions ────────────────────────────────────────────────────

def calculate_need_matrix(allocation, max_matrix):
    """
    Calculate Need matrix dynamically: Need = Max - Allocation
    Returns the need matrix.
    """
    n = len(allocation)
    m = len(allocation[0]) if n > 0 else 0
    
    need = [[0 for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for j in range(m):
            need[i][j] = max_matrix[i][j] - allocation[i][j]
    
    return need

def handle_resource_request(process_id, request, allocation, max_matrix, available):
    """
    Handle resource request using Banker's Safety Check (Trial Allocation)
    Returns (can_grant: bool, updated_allocation, updated_available, explanation)
    """
    n = len(allocation)
    m = len(available)
    
    # Calculate current need
    need = calculate_need_matrix(allocation, max_matrix)
    
    # Check if request exceeds need
    for j in range(m):
        if request[j] > need[process_id][j]:
            return False, allocation, available, f"❌ Request exceeds maximum claim. Process P{process_id} requested {request[j]} of R{j} but only needs {need[process_id][j]} more."
    
    # Check if request exceeds available
    for j in range(m):
        if request[j] > available[j]:
            return False, allocation, available, f"❌ Insufficient resources. Process P{process_id} must wait for {request[j]} of R{j} but only {available[j]} available."
    
    # Trial allocation: pretend to grant the request
    trial_available = available.copy()
    trial_allocation = [row.copy() for row in allocation]
    
    for j in range(m):
        trial_available[j] -= request[j]
        trial_allocation[process_id][j] += request[j]
    
    # Run Banker's Safety Algorithm on trial state
    can_proceed_safely, safe_sequence = bankers_safety_check(trial_allocation, max_matrix, trial_available)
    
    if can_proceed_safely:
        # Grant the request
        explanation = f"✅ Request GRANTED to P{process_id}. Safe sequence found: {' → '.join([f'P{p}' for p in safe_sequence])}"
        return True, trial_allocation, trial_available, explanation
    else:
        # Deny the request
        explanation = f"❌ Request DENIED to P{process_id}. Granting would lead to unsafe state."
        return False, allocation, available, explanation

def bankers_safety_check(allocation, max_matrix, available):
    """
    Banker's Safety Algorithm with Work and Finish arrays
    Returns (is_safe: bool, safe_sequence: list)
    """
    n = len(allocation)
    m = len(available)
    
    # Calculate Need matrix
    need = calculate_need_matrix(allocation, max_matrix)
    
    # Initialize Work and Finish arrays
    work = available.copy()
    finish = [False] * n
    safe_sequence = []
    
    count = 0
    while count < n:
        found = False
        for i in range(n):
            if not finish[i]:
                # Check if Need[i] <= Work
                can_proceed = True
                for j in range(m):
                    if need[i][j] > work[j]:
                        can_proceed = False
                        break
                
                if can_proceed:
                    # Process can finish
                    for j in range(m):
                        work[j] += allocation[i][j]
                    finish[i] = True
                    safe_sequence.append(i)
                    count += 1
                    found = True
                    break
        
        if not found:
            break
    
    return count == n, safe_sequence

def release_process_resources(process_id, allocation, available):
    """
    Release all resources held by a process when it finishes
    Returns (updated_allocation, updated_available)
    """
    updated_available = available.copy()
    updated_allocation = [row.copy() for row in allocation]
    
    # Add process's allocated resources back to available
    for j in range(len(available)):
        updated_available[j] += updated_allocation[process_id][j]
        updated_allocation[process_id][j] = 0
    
    return updated_allocation, updated_available

def check_deadlock_state(allocation, max_matrix, available):
    """
    Check if system is in deadlock state
    Returns (is_deadlocked: bool, deadlocked_processes: list, explanation)
    """
    n = len(allocation)
    
    # Run safety check
    is_safe, safe_sequence = bankers_safety_check(allocation, max_matrix, available)
    
    if not is_safe:
        # Find processes that cannot proceed
        need = calculate_need_matrix(allocation, max_matrix)
        deadlocked = []
        
        for i in range(n):
            can_proceed = True
            for j in range(len(available)):
                if need[i][j] > available[j]:
                    can_proceed = False
                    break
            if not can_proceed:
                deadlocked.append(i)
        
        explanation = f"⚠️ DEADLOCK DETECTED! Processes {deadlocked} cannot proceed."
        return True, deadlocked, explanation
    else:
        explanation = f"✅ System is SAFE. Safe sequence: {' → '.join([f'P{p}' for p in safe_sequence])}"
        return False, [], explanation

# ─── Input validators ────────────────────────────────────────────────────────

def validate_matrices(allocation, max_matrix, available):
    """
    Checks for common input errors.
    Returns (is_valid: bool, error_message: str).
    """
    n = len(allocation)
    m = len(available)

    for i in range(n):
        for j in range(m):
            # Need[i][j] should never be negative (Max < Allocation is invalid)
            if max_matrix[i][j] < allocation[i][j]:
                return False, (
                    f"Invalid input: Max[{i}][{j}] = {max_matrix[i][j]} is less than "
                    f"Allocation[{i}][{j}] = {allocation[i][j]}. "
                    f"A process cannot hold more resources than its maximum claim."
                )
            # Allocations can't be negative
            if allocation[i][j] < 0:
                return False, f"Invalid input: Allocation[{i}][{j}] is negative."
            if max_matrix[i][j] < 0:
                return False, f"Invalid input: Max[{i}][{j}] is negative."

    for j in range(m):
        if available[j] < 0:
            return False, f"Invalid input: Available[{j}] is negative."

    return True, ""
