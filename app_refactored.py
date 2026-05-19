# app_refactored.py
# ------------------
# REFACTORED: Resource Control Focus
# 
# Key Changes:
# 1. Resource Allocation as ground truth
# 2. Request Handler with Banker's Safety Check (Trial Allocation)
# 3. Dynamic Need Matrix (Need = Max - Allocation)
# 4. Work and Finish arrays visualization
# 5. Deadlock Detection: Request vs Available (no cycle detection)
# 6. Recovery System with Process Termination and Resource Preemption
# 7. Visual distinction between Requesting and Allocated states

import streamlit as st
import pandas as pd
import copy
from utils import (
    matrix_to_dataframe,
    vector_to_dataframe,
    validate_matrices,
    calculate_need_matrix,
    suggest_recovery,
    bankers_safety_check,
    check_deadlock_state,
    run_cpp_executable,
    build_bankers_input,
    parse_bankers_result
)

# Page config
st.set_page_config(page_title="Deadlock Simulator - Resource Control", page_icon="🔐", layout="wide")

st.markdown("""
<style>
    .stNumberInput > div > div > input { text-align: center; }
    .resource-granted { background-color: #d4edda; border-left: 4px solid #28a745; padding: 10px; }
    .resource-requesting { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; }
    .resource-waiting { background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🔐 Resource-Controlled Deadlock Management System")
st.caption("Resource Allocation as Ground Truth | Trial Allocation | Dynamic Need Matrix | Recovery System")
st.divider()

# Session State Initialization
def initialize_session_state():
    """Initialize all session state variables for Resource Control."""
    
    # Banker's Algorithm with Resource Control
    if "b_n" not in st.session_state: st.session_state.b_n = 3
    if "b_m" not in st.session_state: st.session_state.b_m = 3
    
    # Resource Allocation (Ground Truth - what processes actually hold)
    if "b_allocation" not in st.session_state: 
        st.session_state.b_allocation = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    
    # Max claims (maximum a process may need)
    if "b_max" not in st.session_state: 
        st.session_state.b_max = [[3, 2, 2], [2, 2, 2], [2, 2, 2]]
    
    # Available resources (free pool)
    if "b_available" not in st.session_state: 
        st.session_state.b_available = [2, 2, 2]
    
    # Resource Requests (pending requests waiting for approval)
    if "b_request" not in st.session_state: 
        st.session_state.b_request = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    
    # Need Matrix (calculated as Max - Allocation)
    if "b_need" not in st.session_state:
        st.session_state.b_need = [[2, 2, 2], [2, 2, 2], [2, 2, 2]]
    
    # Work and Finish arrays for visualization
    if "b_work" not in st.session_state:
        st.session_state.b_work = []
    if "b_finish" not in st.session_state:
        st.session_state.b_finish = []
    if "b_safe_sequence" not in st.session_state:
        st.session_state.b_safe_sequence = []
    
    # Deadlock Detection state
    if "d_n" not in st.session_state: st.session_state.d_n = 3
    if "d_m" not in st.session_state: st.session_state.d_m = 2
    if "d_allocation" not in st.session_state: 
        st.session_state.d_allocation = [[0, 1], [1, 0], [0, 0]]
    if "d_request" not in st.session_state: 
        st.session_state.d_request = [[0, 0], [0, 0], [1, 0]]
    if "d_available" not in st.session_state:
        st.session_state.d_available = [0, 0]
    
    # Recovery System state
    if "terminated_processes" not in st.session_state:
        st.session_state.terminated_processes = []
    if "preempted_resources" not in st.session_state:
        st.session_state.preempted_resources = []

initialize_session_state()

def update_need_matrix():
    """Dynamically update Need Matrix: Need = Max - Allocation"""
    n = st.session_state.b_n
    m = st.session_state.b_m
    need = [[0 for _ in range(m)] for _ in range(n)]
    
    for i in range(n):
        for j in range(m):
            need[i][j] = max(0, st.session_state.b_max[i][j] - st.session_state.b_allocation[i][j])
    
    st.session_state.b_need = need
    return need

def request_handler(process_id, resource_id, amount):
    """
    Resource Request Handler with Banker's Safety Check (Trial Allocation)
    
    Steps:
    1. Check if request <= Need
    2. Check if request <= Available
    3. TRIAL ALLOCATION: Pretend to allocate
    4. Run Safety Check
    5. If safe: COMMIT allocation
    6. If unsafe: ROLLBACK (deny request)
    """
    # Step 1: Check if request is valid
    need = st.session_state.b_need[process_id][resource_id]
    available = st.session_state.b_available[resource_id]
    
    if amount > need:
        return False, f"❌ Error: Request ({amount}) exceeds Need ({need}) for P{process_id}"
    
    if amount > available:
        return False, f"⏳ Wait: Request ({amount}) exceeds Available ({available}) for R{resource_id}"
    
    # Step 2: TRIAL ALLOCATION
    # Create temporary copies for trial
    trial_allocation = copy.deepcopy(st.session_state.b_allocation)
    trial_available = copy.deepcopy(st.session_state.b_available)
    
    # Pretend to allocate
    trial_allocation[process_id][resource_id] += amount
    trial_available[resource_id] -= amount
    
    # Step 3: Run Safety Check on trial state
    trial_need = calculate_need_matrix(trial_allocation, st.session_state.b_max)
    is_safe, safe_sequence = bankers_safety_check(trial_allocation, st.session_state.b_max, trial_available)
    
    if is_safe:
        # Step 4a: COMMIT - Request is safe, apply changes
        st.session_state.b_allocation = trial_allocation
        st.session_state.b_available = trial_available
        st.session_state.b_safe_sequence = safe_sequence
        
        # Update Need Matrix dynamically
        update_need_matrix()
        
        # Clear the request since it's been granted
        st.session_state.b_request[process_id][resource_id] = 0
        
        return True, f"✅ GRANTED: P{process_id} allocated {amount} of R{resource_id}. Safe sequence: {safe_sequence}"
    else:
        # Step 4b: ROLLBACK - Request would lead to unsafe state
        return False, f"🚫 DENIED: Allocating {amount} to P{process_id} would lead to UNSAFE state"

def draw_resource_graph(allocation, request, available):
    """Draw graph showing Allocated vs Requesting resources with clear distinction"""
    n = len(allocation)
    m = len(available)
    
    svg_parts = ['<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">']
    svg_parts.append('<rect width="600" height="400" fill="#f8f9fa"/>')
    
    # Draw title
    svg_parts.append('<text x="300" y="25" text-anchor="middle" font-size="16" font-weight="bold">Resource Allocation State</text>')
    
    # Draw Available Pool (top center)
    avail_x, avail_y = 300, 60
    svg_parts.append(f'<rect x="{avail_x-40}" y="{avail_y-20}" width="80" height="40" fill="#dc3545" stroke="#000" rx="5"/>')
    svg_parts.append(f'<text x="{avail_x}" y="{avail_y+5}" text-anchor="middle" font-size="12" fill="white">Available</text>')
    avail_text = ",".join([f"R{j}:{available[j]}" for j in range(m) if available[j] > 0])
    svg_parts.append(f'<text x="{avail_x}" y="{avail_y+55}" text-anchor="middle" font-size="10">{avail_text or "None"}</text>')
    
    # Draw Processes (bottom row)
    process_y = 320
    process_spacing = 550 // max(n, 1)
    
    for i in range(n):
        x = 50 + i * process_spacing
        # Check if process has requests pending
        has_request = sum(request[i]) > 0
        has_allocation = sum(allocation[i]) > 0
        
        # Color based on state
        if has_request and not has_allocation:
            color = "#ffc107"  # Yellow - Waiting (Requesting)
            status = "WAITING"
        elif has_request and has_allocation:
            color = "#fd7e14"  # Orange - Holding + Waiting
            status = "HOLD+WAIT"
        elif has_allocation:
            color = "#28a745"  # Green - Holding
            status = "HOLDING"
        else:
            color = "#6c757d"  # Gray - Inactive
            status = "INACTIVE"
        
        # Draw process circle
        svg_parts.append(f'<circle cx="{x}" cy="{process_y}" r="30" fill="{color}" stroke="#000" stroke-width="2"/>')
        svg_parts.append(f'<text x="{x}" cy="{process_y+5}" text-anchor="middle" font-size="14" font-weight="bold" fill="white">P{i}</text>')
        svg_parts.append(f'<text x="{x}" y="{process_y+50}" text-anchor="middle" font-size="9">{status}</text>')
        
        # Draw allocation arrows (from available/processes to process)
        for j in range(m):
            if allocation[i][j] > 0:
                # Arrow from available/resources to process
                res_x = 100 + j * 80
                res_y = 150
                svg_parts.append(f'<line x1="{res_x}" y1="{res_y+20}" x2="{x}" y2="{process_y-30}" stroke="#28a745" stroke-width="2" marker-end="url(#arrowhead)"/>')
                svg_parts.append(f'<text x="{(res_x+x)//2}" y="{(res_y+process_y)//2 - 10}" font-size="10" fill="#28a745">A:{allocation[i][j]}</text>')
        
        # Draw request arrows (dashed, from process to resources)
        for j in range(m):
            if request[i][j] > 0:
                res_x = 100 + j * 80
                res_y = 150
                svg_parts.append(f'<line x1="{x}" y1="{process_y-30}" x2="{res_x}" y2="{res_y+20}" stroke="#ffc107" stroke-width="2" stroke-dasharray="5,5" marker-end="url(#arrowhead)"/>')
                svg_parts.append(f'<text x="{(x+res_x)//2}" y="{(process_y+res_y)//2 + 20}" font-size="10" fill="#ffc107">R:{request[i][j]}</text>')
    
    # Draw Resources (middle row)
    for j in range(m):
        x = 100 + j * 80
        y = 150
        svg_parts.append(f'<rect x="{x-25}" y="{y-25}" width="50" height="50" fill="#007bff" stroke="#000" rx="5"/>')
        svg_parts.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="14" font-weight="bold" fill="white">R{j}</text>')
        svg_parts.append(f'<text x="{x}" y="{y+65}" text-anchor="middle" font-size="10">Avail:{available[j]}</text>')
    
    # Arrow marker
    svg_parts.append('<defs><marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><polygon points="0 0, 10 3, 0 6" fill="#000"/></marker></defs>')
    
    # Legend
    legend_y = 380
    svg_parts.append(f'<rect x="50" y="{legend_y}" width="15" height="15" fill="#28a745"/>')
    svg_parts.append(f'<text x="70" y="{legend_y+12}" font-size="10">Allocated (Holding)</text>')
    svg_parts.append(f'<rect x="180" y="{legend_y}" width="15" height="15" fill="#ffc107"/>')
    svg_parts.append(f'<text x="200" y="{legend_y+12}" font-size="10">Requesting (Waiting)</text>')
    svg_parts.append(f'<rect x="330" y="{legend_y}" width="15" height="15" fill="#fd7e14"/>')
    svg_parts.append(f'<text x="350" y="{legend_y+12}" font-size="10">Holding + Waiting</text>')
    
    svg_parts.append('</svg>')
    return "".join(svg_parts)

# Sidebar Module Selection
st.sidebar.header("⚙️ Module")
mode = st.sidebar.radio("Select:", [
    "🏦 Banker's Algorithm (Resource Control)",
    "🔍 Deadlock Detection (Request vs Available)",
    "🛠️ Recovery System"
])

# Main content based on selection
if mode == "🏦 Banker's Algorithm (Resource Control)":
    st.header("🏦 Banker's Algorithm with Resource Control")
    
    # Process and Resource controls
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl1:
        st.markdown(f"**Processes: {st.session_state.b_n}**")
    with ctrl2:
        ca, cb = st.columns(2)
        if ca.button("➕", key="bp_add"): 
            st.session_state.b_n = min(st.session_state.b_n + 1, 10)
        if cb.button("➖", key="bp_rm"):  
            st.session_state.b_n = max(st.session_state.b_n - 1, 1)
    with ctrl3:
        st.markdown(f"**Resources: {st.session_state.b_m}**")
    with ctrl4:
        ca, cb = st.columns(2)
        if ca.button("➕", key="br_add"): 
            st.session_state.b_m = min(st.session_state.b_m + 1, 8)
        if cb.button("➖", key="br_rm"):  
            st.session_state.b_m = max(st.session_state.b_m - 1, 1)
    
    n_p = st.session_state.b_n
    n_r = st.session_state.b_m
    
    # Update Need Matrix dynamically
    update_need_matrix()
    
    st.markdown("---")
    
    # Two-column layout
    left, right = st.columns([3, 2])
    
    with left:
        # 1. ALLOCATION MATRIX (Ground Truth)
        st.subheader("📦 Allocation Matrix (Ground Truth)")
        st.caption("Resources CURRENTLY HELD by each process")
        
        alloc_hdr = st.columns([1.2] + [1]*n_r)
        alloc_hdr[0].markdown("**P\\R**")
        for j in range(n_r): alloc_hdr[j+1].markdown(f"**R{j}**")
        
        for i in range(n_p):
            row = st.columns([1] + [1]*n_r)
            row[0].markdown(f"**P{i}**")
            for j in range(n_r):
                with row[j+1]:
                    col_val, col_ctrl = st.columns([3, 1])
                    v = col_val.number_input("", min_value=0, max_value=99, 
                                            value=st.session_state.b_allocation[i][j],
                                            key=f"alloc_{i}_{j}", label_visibility="collapsed")
                    inc, dec = col_ctrl.columns(2)
                    if inc.button("➕", key=f"alloc_inc_{i}_{j}"):
                        st.session_state.b_allocation[i][j] = min(v + 1, 99)
                        update_need_matrix()
                        st.rerun()
                    if dec.button("➖", key=f"alloc_dec_{i}_{j}"):
                        st.session_state.b_allocation[i][j] = max(v - 1, 0)
                        update_need_matrix()
                        st.rerun()
        
        st.markdown("---")
        
        # 2. MAX MATRIX
        st.subheader("📋 Max Matrix (Maximum Claims)")
        st.caption("Maximum resources each process MAY NEED")
        
        max_hdr = st.columns([1.2] + [1]*n_r)
        max_hdr[0].markdown("**P\\R**")
        for j in range(n_r): max_hdr[j+1].markdown(f"**R{j}**")
        
        for i in range(n_p):
            row = st.columns([1] + [1]*n_r)
            row[0].markdown(f"**P{i}**")
            for j in range(n_r):
                with row[j+1]:
                    col_val, col_ctrl = st.columns([3, 1])
                    v = col_val.number_input("", min_value=0, max_value=99, 
                                            value=st.session_state.b_max[i][j],
                                            key=f"max_{i}_{j}", label_visibility="collapsed")
                    inc, dec = col_ctrl.columns(2)
                    if inc.button("➕", key=f"max_inc_{i}_{j}"):
                        st.session_state.b_max[i][j] = min(v + 1, 99)
                        update_need_matrix()
                        st.rerun()
                    if dec.button("➖", key=f"max_dec_{i}_{j}"):
                        st.session_state.b_max[i][j] = max(v - 1, 0)
                        update_need_matrix()
                        st.rerun()
        
        st.markdown("---")
        
        # 3. AVAILABLE RESOURCES
        st.subheader("💎 Available Resources (Free Pool)")
        st.caption("Resources currently FREE for allocation")
        
        avail_row = st.columns([1.2] + [1]*n_r)
        avail_row[0].markdown("**Avail**")
        for j in range(n_r):
            with avail_row[j+1]:
                col_val, col_ctrl = st.columns([3, 1])
                v = col_val.number_input("", min_value=0, max_value=99, 
                                        value=st.session_state.b_available[j],
                                        key=f"avail_{j}", label_visibility="collapsed")
                inc, dec = col_ctrl.columns(2)
                if inc.button("➕", key=f"avail_inc_{j}"):
                    st.session_state.b_available[j] = min(v + 1, 99)
                    st.rerun()
                if dec.button("➖", key=f"avail_dec_{j}"):
                    st.session_state.b_available[j] = max(v - 1, 0)
                    st.rerun()
        
        st.markdown("---")
        
        # 4. DYNAMIC NEED MATRIX
        st.subheader("🧮 Need Matrix (Dynamic: Max - Allocation)")
        st.caption("Additional resources each process STILL NEEDS")
        
        need_df = pd.DataFrame(st.session_state.b_need, 
                               columns=[f"R{j}" for j in range(n_r)],
                               index=[f"P{i}" for i in range(n_p)])
        st.dataframe(need_df, use_container_width=True)
        
        st.markdown("---")
        
        # 5. RESOURCE REQUEST HANDLER
        st.subheader("📨 Resource Request Handler")
        st.caption("Submit resource requests with Banker's Safety Check (Trial Allocation)")
        
        req_col1, req_col2, req_col3 = st.columns(3)
        with req_col1:
            req_process = st.selectbox("Process:", [f"P{i}" for i in range(n_p)], key="req_proc")
        with req_col2:
            req_resource = st.selectbox("Resource:", [f"R{j}" for j in range(n_r)], key="req_res")
        with req_col3:
            req_amount = st.number_input("Amount:", min_value=1, max_value=99, value=1, key="req_amt")
        
        if st.button("📝 Submit Request", type="primary", use_container_width=True):
            p_id = int(req_process.replace("P", ""))
            r_id = int(req_resource.replace("R", ""))
            
            # Call Request Handler with Banker's Safety Check
            granted, message = request_handler(p_id, r_id, req_amount)
            
            if granted:
                st.success(message)
                st.balloons()
            else:
                st.error(message)
            
            st.rerun()
        
        st.markdown("---")
        
        # 6. WORK AND FINISH ARRAYS VISUALIZATION
        if st.session_state.b_safe_sequence:
            st.subheader("📊 Safety Algorithm Execution")
            st.caption("Work and Finish arrays during safety check")
            
            # Display current Work array
            work_col, finish_col = st.columns(2)
            with work_col:
                st.markdown("**Work Array (Available):**")
                work_df = pd.DataFrame([st.session_state.b_available], 
                                       columns=[f"R{j}" for j in range(n_r)])
                st.dataframe(work_df, use_container_width=True)
            
            with finish_col:
                st.markdown("**Safe Sequence:**")
                safe_seq_str = " → ".join([f"P{p}" for p in st.session_state.b_safe_sequence])
                st.info(safe_seq_str)
    
    with right:
        # Resource Graph Visualization
        st.subheader("📊 Resource Allocation Graph")
        st.markdown("""
        <style>
        .legend-box { padding: 5px; margin: 2px; border-radius: 3px; font-size: 12px; }
        .green { background-color: #d4edda; }
        .yellow { background-color: #fff3cd; }
        .orange { background-color: #ffe5cc; }
        </style>
        <div style="font-size: 12px; margin-bottom: 10px;">
        <span class="legend-box green">🟢 Holding</span>
        <span class="legend-box yellow">🟡 Waiting</span>
        <span class="legend-box orange">🟠 Hold+Wait</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(draw_resource_graph(st.session_state.b_allocation, 
                                        st.session_state.b_request, 
                                        st.session_state.b_available), 
                    unsafe_allow_html=True)
        
        # System Status
        st.subheader("📋 System Status")
        
        # Check if safe
        is_safe, safe_seq = bankers_safety_check(st.session_state.b_allocation, 
                                                  st.session_state.b_max, 
                                                  st.session_state.b_available)
        
        if is_safe:
            st.success(f"✅ SAFE STATE\nSafe Sequence: {' → '.join([f'P{p}' for p in safe_seq])}")
        else:
            st.error("⚠️ UNSAFE STATE\nPotential deadlock detected!")
    
    st.markdown("---")
    
    # Action Buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("▶️ Run Safety Check", type="primary", use_container_width=True):
            is_safe, safe_seq = bankers_safety_check(st.session_state.b_allocation, 
                                                      st.session_state.b_max, 
                                                      st.session_state.b_available)
            st.session_state.b_safe_sequence = safe_seq
            
            if is_safe:
                st.success(f"✅ System is in SAFE STATE\nSafe Sequence: {' → '.join([f'P{p}' for p in safe_seq])}")
            else:
                st.error("⚠️ System is in UNSAFE STATE\nDeadlock may occur!")
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset System", use_container_width=True):
            st.session_state.b_allocation = [[0 for _ in range(n_r)] for _ in range(n_p)]
            st.session_state.b_available = [5 for _ in range(n_r)]  # Reset with some resources
            st.session_state.b_request = [[0 for _ in range(n_r)] for _ in range(n_p)]
            st.session_state.b_safe_sequence = []
            update_need_matrix()
            st.success("System reset to initial state")
            st.rerun()
    
    with col3:
        if st.button("🛠️ Open Recovery", use_container_width=True):
            st.session_state.show_recovery = True
            st.rerun()

# DEADLOCK DETECTION MODULE (Request vs Available - NO CYCLE DETECTION)
elif mode == "🔍 Deadlock Detection (Request vs Available)":
    st.header("🔍 Deadlock Detection: Request vs Available")
    st.caption("Detects deadlock by comparing current requests against available resources (No cycle detection)")
    
    # Process/Resource controls
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl1:
        st.markdown(f"**Processes: {st.session_state.d_n}**")
    with ctrl2:
        ca, cb = st.columns(2)
        if ca.button("➕", key="dp_add"): 
            st.session_state.d_n = min(st.session_state.d_n + 1, 10)
        if cb.button("➖", key="dp_rm"):  
            st.session_state.d_n = max(st.session_state.d_n - 1, 1)
    with ctrl3:
        st.markdown(f"**Resources: {st.session_state.d_m}**")
    with ctrl4:
        ca, cb = st.columns(2)
        if ca.button("➕", key="dr_add"): 
            st.session_state.d_m = min(st.session_state.d_m + 1, 8)
        if cb.button("➖", key="dr_rm"):  
            st.session_state.d_m = max(st.session_state.d_m - 1, 1)
    
    dn = st.session_state.d_n
    dm = st.session_state.d_m
    
    st.markdown("---")
    
    # Two-column layout for matrices
    left, right = st.columns(2)
    
    with left:
        # ALLOCATION MATRIX (Ground Truth)
        st.subheader("📦 Allocation Matrix")
        st.caption("Resources CURRENTLY HELD by processes")
        
        alloc_hdr = st.columns([1.2] + [1]*dm)
        alloc_hdr[0].markdown("**P\\R**")
        for j in range(dm): alloc_hdr[j+1].markdown(f"**R{j}**")
        
        for i in range(dn):
            row = st.columns([1] + [1]*dm)
            row[0].markdown(f"**P{i}**")
            for j in range(dm):
                with row[j+1]:
                    col_val, col_ctrl = st.columns([3, 1])
                    v = col_val.number_input("", min_value=0, max_value=1, 
                                            value=st.session_state.d_allocation[i][j],
                                            key=f"d_alloc_{i}_{j}", label_visibility="collapsed")
                    inc, dec = col_ctrl.columns(2)
                    if inc.button("➕", key=f"d_alloc_inc_{i}_{j}"):
                        st.session_state.d_allocation[i][j] = min(v + 1, 1)
                        st.rerun()
                    if dec.button("➖", key=f"d_alloc_dec_{i}_{j}"):
                        st.session_state.d_allocation[i][j] = max(v - 1, 0)
                        st.rerun()
    
    with right:
        # REQUEST MATRIX (Current Requests)
        st.subheader("📋 Current Request Matrix")
        st.caption("Resources CURRENTLY REQUESTED by processes")
        
        req_hdr = st.columns([1.2] + [1]*dm)
        req_hdr[0].markdown("**P\\R**")
        for j in range(dm): req_hdr[j+1].markdown(f"**R{j}**")
        
        for i in range(dn):
            row = st.columns([1] + [1]*dm)
            row[0].markdown(f"**P{i}**")
            for j in range(dm):
                with row[j+1]:
                    col_val, col_ctrl = st.columns([3, 1])
                    v = col_val.number_input("", min_value=0, max_value=1, 
                                            value=st.session_state.d_request[i][j],
                                            key=f"d_req_{i}_{j}", label_visibility="collapsed")
                    inc, dec = col_ctrl.columns(2)
                    if inc.button("➕", key=f"d_req_inc_{i}_{j}"):
                        st.session_state.d_request[i][j] = min(v + 1, 1)
                        st.rerun()
                    if dec.button("➖", key=f"d_req_dec_{i}_{j}"):
                        st.session_state.d_request[i][j] = max(v - 1, 0)
                        st.rerun()
    
    st.markdown("---")
    
    # AVAILABLE RESOURCES
    st.subheader("💎 Available Resources")
    st.caption("Resources NOT currently allocated")
    
    avail_row = st.columns([1.2] + [1]*dm)
    avail_row[0].markdown("**Avail**")
    for j in range(dm):
        with avail_row[j+1]:
            col_val, col_ctrl = st.columns([3, 1])
            v = col_val.number_input("", min_value=0, max_value=99, 
                                    value=st.session_state.d_available[j],
                                    key=f"d_avail_{j}", label_visibility="collapsed")
            inc, dec = col_ctrl.columns(2)
            if inc.button("➕", key=f"d_avail_inc_{j}"):
                st.session_state.d_available[j] = min(v + 1, 99)
                st.rerun()
            if dec.button("➖", key=f"d_avail_dec_{j}"):
                st.session_state.d_available[j] = max(v - 1, 0)
                st.rerun()
    
    st.markdown("---")
    
    # DEADLOCK DETECTION LOGIC (Request vs Available)
    st.subheader("🔍 Deadlock Detection Analysis")
    
    # Find processes whose requests can be satisfied
    deadlocked = []
    can_proceed = []
    
    for i in range(dn):
        can_satisfy = True
        for j in range(dm):
            if st.session_state.d_request[i][j] > st.session_state.d_available[j]:
                can_satisfy = False
                break
        
        if can_satisfy and sum(st.session_state.d_request[i]) > 0:
            can_proceed.append(i)
        elif sum(st.session_state.d_request[i]) > 0:
            deadlocked.append(i)
    
    # Display results
    result_col1, result_col2 = st.columns(2)
    
    with result_col1:
        st.markdown("**✅ Can Proceed:**")
        if can_proceed:
            for p in can_proceed:
                st.success(f"P{p} - Request can be satisfied")
        else:
            st.info("No processes can proceed with current requests")
    
    with result_col2:
        st.markdown("**🚫 Potentially Deadlocked:**")
        if deadlocked:
            for p in deadlocked:
                req_str = ", ".join([f"R{j}:{st.session_state.d_request[p][j]}" 
                                    for j in range(dm) if st.session_state.d_request[p][j] > 0])
                avail_str = ", ".join([f"R{j}:{st.session_state.d_available[j]}" for j in range(dm)])
                st.error(f"P{p} - Request ({req_str}) exceeds Available ({avail_str})")
        else:
            st.success("No deadlocked processes detected")
    
    # Visualization
    st.markdown("---")
    st.subheader("📊 Resource State Visualization")
    st.markdown(draw_resource_graph(st.session_state.d_allocation, 
                                    st.session_state.d_request, 
                                    st.session_state.d_available), 
                unsafe_allow_html=True)
    
    # Detect Deadlock Button
    if st.button("🔍 Run Deadlock Detection", type="primary", use_container_width=True):
        if deadlocked:
            st.error(f"⚠️ DEADLOCK DETECTED!\nDeadlocked Processes: {[f'P{p}' for p in deadlocked]}")
            st.session_state.deadlocked_processes = deadlocked
        else:
            st.success("✅ No deadlock detected. System can proceed.")

# RECOVERY SYSTEM MODULE (Process Termination & Resource Preemption)
elif mode == "🛠️ Recovery System":
    st.header("🛠️ Recovery System")
    st.caption("Process Termination and Resource Preemption to resolve deadlocks")
    
    # Load current state from Banker's or Deadlock Detection
    st.markdown("---")
    
    # Source selection
    source = st.radio("Select Source System:", ["Banker's Algorithm", "Deadlock Detection"], horizontal=True)
    
    if source == "Banker's Algorithm":
        n = st.session_state.b_n
        m = st.session_state.b_m
        allocation = st.session_state.b_allocation
        request = st.session_state.b_request
        available = st.session_state.b_available
        need = st.session_state.b_need
    else:
        n = st.session_state.d_n
        m = st.session_state.d_m
        allocation = st.session_state.d_allocation
        request = st.session_state.d_request
        available = st.session_state.d_available
        need = [[0 for _ in range(m)] for _ in range(n)]  # Calculate if needed
    
    # Display current state
    st.subheader("📋 Current System State")
    
    state_col1, state_col2 = st.columns(2)
    
    with state_col1:
        st.markdown("**Allocation Matrix:**")
        alloc_df = pd.DataFrame(allocation, 
                               columns=[f"R{j}" for j in range(m)],
                               index=[f"P{i}" for i in range(n)])
        st.dataframe(alloc_df, use_container_width=True)
    
    with state_col2:
        st.markdown(f"**Available Resources:** {available}")
        st.markdown(f"**Processes:** {n}")
        st.markdown(f"**Resource Types:** {m}")
    
    st.markdown("---")
    
    # RECOVERY OPTIONS
    st.subheader("🛠️ Recovery Options")
    
    recovery_tabs = st.tabs(["🔪 Process Termination", "⚡ Resource Preemption"])
    
    # TAB 1: Process Termination
    with recovery_tabs[0]:
        st.markdown("### 🔪 Process Termination")
        st.caption("Kill a process to free all its allocated resources")
        
        # Select process to terminate
        term_process = st.selectbox("Select Process to Terminate:", 
                                   [f"P{i}" for i in range(n)],
                                   key="term_proc")
        
        if st.button("🔪 Terminate Process", type="primary", use_container_width=True):
            p_id = int(term_process.replace("P", ""))
            
            # Release all resources held by this process
            freed_resources = allocation[p_id].copy()
            
            # Add freed resources back to available pool
            for j in range(m):
                available[j] += freed_resources[j]
                allocation[p_id][j] = 0
            
            # Clear any pending requests
            for j in range(m):
                request[p_id][j] = 0
            
            # Save back to session state
            if source == "Banker's Algorithm":
                st.session_state.b_available = available
                st.session_state.b_allocation = allocation
                st.session_state.b_request = request
            else:
                st.session_state.d_available = available
                st.session_state.d_allocation = allocation
                st.session_state.d_request = request
            
            st.success(f"🔪 P{p_id} terminated!\nFreed resources: {freed_resources}\nNew Available: {available}")
            
            # Add to terminated list
            if f"P{p_id}" not in st.session_state.terminated_processes:
                st.session_state.terminated_processes.append(f"P{p_id}")
            
            st.balloons()
            st.rerun()
    
    # TAB 2: Resource Preemption
    with recovery_tabs[1]:
        st.markdown("### ⚡ Resource Preemption")
        st.caption("Forcefully take resources from a process")
        
        # Select source process (to preempt from)
        preempt_col1, preempt_col2 = st.columns(2)
        
        with preempt_col1:
            source_proc = st.selectbox("Preempt From Process:", 
                                      [f"P{i}" for i in range(n)],
                                      key="preempt_src")
        
        with preempt_col2:
            target_proc = st.selectbox("Allocate To Process:", 
                                      [f"P{i}" for i in range(n) if f"P{i}" != source_proc],
                                      key="preempt_tgt")
        
        # Show resources held by source process
        src_id = int(source_proc.replace("P", ""))
        tgt_id = int(target_proc.replace("P", ""))
        
        st.markdown(f"**Resources held by {source_proc}:** {allocation[src_id]}")
        
        # Select resources to preempt
        st.markdown("**Select Resources to Preempt:**")
        preempt_amounts = []
        for j in range(m):
            max_preempt = allocation[src_id][j]
            if max_preempt > 0:
                amt = st.number_input(f"R{j} (max {max_preempt}):", 
                                     min_value=0, max_value=max_preempt, value=1,
                                     key=f"preempt_{j}")
                preempt_amounts.append(amt)
            else:
                preempt_amounts.append(0)
        
        if st.button("⚡ Execute Preemption", type="primary", use_container_width=True):
            # Check if any resources to preempt
            if sum(preempt_amounts) == 0:
                st.error("❌ No resources selected for preemption!")
            else:
                # Preempt resources from source
                for j in range(m):
                    allocation[src_id][j] -= preempt_amounts[j]
                    allocation[tgt_id][j] += preempt_amounts[j]
                
                # Save back to session state
                if source == "Banker's Algorithm":
                    st.session_state.b_allocation = allocation
                else:
                    st.session_state.d_allocation = allocation
                
                st.success(f"⚡ Preemption Complete!\n{source_proc} → {target_proc}\nResources moved: {preempt_amounts}")
                
                # Add to preempted list
                preempt_record = {
                    "from": source_proc,
                    "to": target_proc,
                    "resources": preempt_amounts
                }
                st.session_state.preempted_resources.append(preempt_record)
                
                st.rerun()
    
    st.markdown("---")
    
    # Recovery History
    st.subheader("📋 Recovery History")
    
    hist_col1, hist_col2 = st.columns(2)
    
    with hist_col1:
        st.markdown("**Terminated Processes:**")
        if st.session_state.terminated_processes:
            for proc in st.session_state.terminated_processes:
                st.error(f"🔪 {proc}")
        else:
            st.info("No processes terminated yet")
    
    with hist_col2:
        st.markdown("**Preempted Resources:**")
        if st.session_state.preempted_resources:
            for record in st.session_state.preempted_resources:
                st.warning(f"⚡ {record['from']} → {record['to']}: {record['resources']}")
        else:
            st.info("No resources preempted yet")
    
    # Reset Recovery
    if st.button("🔄 Reset Recovery History", use_container_width=True):
        st.session_state.terminated_processes = []
        st.session_state.preempted_resources = []
        st.success("Recovery history cleared")
        st.rerun()
