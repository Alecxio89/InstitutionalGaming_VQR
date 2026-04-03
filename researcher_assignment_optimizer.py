"""
Researcher-Publication Assignment Optimizer
============================================

A mixed-integer programming (MIP) system for assigning researchers and their 
publications to academic departments. This system uses Gurobi's solver 
to solve a complex assignment problem.

PROBLEM OVERVIEW:
- Assigns researchers (ric) to departments (dep)
- Assigns publications (pub) to researchers and departments
- Optimizes publication scores
- Respects constraints: author counts, department capacity, pre-assignment requirements

ALGORITHM STAGES:
1. Data Loading: Load researcher-publication data from Excel

2. Model Building:
   - Define decision variables (x, z)
   - Add constraints (capacity, uniqueness, thresholds)
   - Define objective function

3. Optimization:
   - Solve the MIP model

DEPENDENCIES:
- pandas, numpy: Data manipulation
- openpyxl: Excel I/O
- gurobipy: Mixed-Integer Programming solver
- collections.Counter: Statistical analysis

OUTPUT:
- Solution data (assignments, scores, metadata) exported to CSV

AUTHOR: Alessio [Original project]
TRANSLATION & ENHANCEMENT: 2025
"""

import openpyxl
from openpyxl.utils import get_column_letter
import pandas as pd
import numpy as np
from collections import Counter
from gurobipy import Model, GRB, quicksum


def load_data(file_name, preprocess=True):
    """
    Load researcher-publication data from Excel.
    
    This function reads raw Excel data and builds derived data structures 
    needed for optimization.
    
    PARAMETERS:
    -----------
    file_name : str
        Path to Excel file with sheet "Data"
        Expected columns: Author_ID, Publication_ID, Department, 
                         Score, Class, Internal_Authors_Count, Total_Authors_Count, Assignment_Value
    
    RETURNS:
    --------
    dict: Structured optimization data
        Keys:
        - dep: set of unique department IDs
        - ric: set of unique researcher IDs
        - pub: set of unique publication IDs
        - ric_dep_initial_assignment: dict mapping (dept, researcher) -> assignment value
        - ric_initial_dep: dict mapping researcher -> initial department
        - allowed_pairs: set of valid (researcher, publication) pairs
        - allowed_couples: dict of metrics per (researcher, publication) pair
        - pub_int_aut: dict of internal authors count per publication
        - pub_tot_aut: dict of total authors count per publication
        - min_allowed_ric_dep: minimum researchers per department
        - tot_ric: total number of researchers
        - df: preprocessed DataFrame
    """
    global dep, ric, pub, ric_dep_initial_assignment, ric_initial_dep
    global allowed_couples, allowed_pairs, pub_int_aut, pub_tot_aut
    global min_allowed_ric_dep, tot_ric

    # Load raw data
    df = pd.read_excel(file_name, sheet_name="Data", engine="openpyxl")
    n_rows_start = len(df)

    # Normalize numeric columns: Score and class
    for col_name in ["Score", "class"]:
        if col_name in df.columns:
            df[col_name] = pd.to_numeric(df[col_name], errors="coerce").replace([np.inf, -np.inf], pd.NA).fillna(0)

    # ====================================================================
    # BUILD DERIVED DATA STRUCTURES FOR OPTIMIZATION
    # ====================================================================
    
    dep = set(df["Department"])
    ric = set(df["Author_ID"])
    pub = set(df["Publication_ID"])

    ric_dep_initial_assignment = df.set_index(["Department", "Author_ID"]).to_dict()["Assignment_Value"]
    ric_initial_dep = {i: k for (k, i), v in ric_dep_initial_assignment.items() if v == 1}

    allowed_couples = df.set_index(["Author_ID", "Publication_ID"]).to_dict()
    first_metric = next(iter(allowed_couples.keys()))
    allowed_pairs = set(allowed_couples[first_metric].keys())

    pub_int_aut = df.set_index(["Publication_ID"]).to_dict()["Internal_Authors_Count"]
    pub_tot_aut = df.set_index(["Publication_ID"]).to_dict()["Total_Authors_Count"]

    ric_info = df.set_index(["Author_ID"]).to_dict()
    ric_dep_counts = Counter(ric_info["Department"].values())
    min_ric_dep = min(ric_dep_counts.values())
    tot_ric = sum(ric_dep_counts.values())
    min_allowed_ric_dep = 40 if min_ric_dep >= 40 else min_ric_dep

    return {
        "dep": dep,
        "ric": ric,
        "pub": pub,
        "ric_dep_initial_assignment": ric_dep_initial_assignment,
        "ric_initial_dep": ric_initial_dep,
        "allowed_couples": allowed_couples,
        "allowed_pairs": allowed_pairs,
        "pub_int_aut": pub_int_aut,
        "pub_tot_aut": pub_tot_aut,
        "min_allowed_ric_dep": min_allowed_ric_dep,
        "tot_ric": tot_ric,
        "df": df,
    }


def build_model(allowed_change, researchers_subset=None, publications_subset=None):
    """
    Build the Gurobi mixed-integer programming model.
    This function constructs the MIP model with decision variables, constraints, and objective functions based on the global data structures.
    """
    global dep, ric, pub, allowed_pairs, ric_dep_initial_assignment, min_allowed_ric_dep, tot_ric, pub_tot_aut, allowed_couples

    researchers_local = researchers_subset if researchers_subset is not None else ric
    publications_local = publications_subset if publications_subset is not None else pub
    
    model = Model('researcher_assignment')
    model.ModelSense = GRB.MAXIMIZE

    # Decision Variables
    x = {
        k: {
            i: {
                j: model.addVar(vtype=GRB.BINARY, name=f"x_{k}_{i}_{j}")
                for j in publications_local if (i, j) in allowed_pairs
            }
            for i in researchers_local
        }
        for k in dep
    }
    
    z = {
        k: {i: model.addVar(vtype=GRB.BINARY, name=f"z_{k}_{i}") for i in researchers_local}
        for k in dep
    }

    # Constraints
    for k in dep:
        # Publication capacity constraint
        model.addConstr(
            quicksum(x[k][i][j] for i in researchers_local for j in publications_local if (i, j) in allowed_pairs) 
            <= 2.5 * quicksum(z[k][i] for i in researchers_local),
            name=f"publication_capacity_{k}"
        )
        
        # Minimum researchers per department
        model.addConstr(
            quicksum(z[k][i] for i in researchers_local) >= min_allowed_ric_dep,
            name=f"min_researchers_{k}"
        )

    for i in researchers_local:
        # Each researcher assigned to exactly one department
        model.addConstr(
            quicksum(z[k][i] for k in dep) == 1,
            name=f"researcher_assignment_{i}"
        )
        
        for k in dep:
            # Publication limits for (researcher, department)
            model.addConstr(
                quicksum(x[k][i][j] for j in publications_local if (i, j) in allowed_pairs) <= 4 * z[k][i],
                name=f"max_publications_{k}_{i}"
            )
            model.addConstr(
                quicksum(x[k][i][j] for j in publications_local if (i, j) in allowed_pairs) >= z[k][i],
                name=f"min_publications_{k}_{i}"
            )

    for j in publications_local:
        for k in dep:
            # Publication assigned to at most one researcher per department
            model.addConstr(
                quicksum(x[k][i][j] for i in researchers_local if (i, j) in allowed_pairs) <= 1,
                name=f"publication_uniqueness_{k}_{j}"
            )
        
        # Author count threshold based on total authors
        if pub_tot_aut[j] < 6:
            # Low-author publications: max 2 internal authors
            model.addConstr(
                quicksum(x[k][i][j] for k in dep for i in researchers_local if (i, j) in allowed_pairs) <= 2,
                name=f"author_threshold_low_{j}"
            )
        else:
            # High-author publications: max 1 internal author
            model.addConstr(
                quicksum(x[k][i][j] for k in dep for i in researchers_local if (i, j) in allowed_pairs) <= 1,
                name=f"author_threshold_high_{j}"
            )
    
    # Pre-assignment constraint
    constr_preassign = model.addConstr(
        quicksum(ric_dep_initial_assignment.get((k, i), 0) * z[k][i] for k in dep for i in researchers_local) 
        >= tot_ric - allowed_change,
        name="preassignment"
    )

    # Objective functions
    of_class = quicksum(
        allowed_couples["Class"].get((i, j), 0) * x[k][i][j]
        for k in dep for i in researchers_local for j in publications_local if (i, j) in allowed_pairs
    )
    
    of_score = quicksum(
        allowed_couples["Score"].get((i, j), 0) * x[k][i][j]
        for k in dep for i in researchers_local for j in publications_local if (i, j) in allowed_pairs
    )

    return model, x, z, of_class, of_score, constr_preassign


def run_scenarios(scenario_list):
    """
    Run optimization across multiple flexibility scenarios.
    
    For each scenario, builds and solves the MIP model with the given 
    flexibility percentage (allowed researcher reassignments).
    
    PARAMETERS:
    -----------
    scenario_list : list
        List of scenario percentages [0, 1, 2, ..., 10] - 0=0% flexibility (no changes), 1=10%, 2=20%, ..., 10=100% (full reassignment allowed)
    
    RETURNS:
    --------
    dict: scenario_key -> optimization results
        Keys per scenario: "scenario_0", "scenario_1", ..., "scenario_10"
        Each contains solution data and metadata
    """
    global dep, ric, pub, ric_dep_initial_assignment, tot_ric, allowed_couples, ric_initial_dep

    def compute_allowed_change(flexibility_percent):
        """Convert flexibility percentage to allowed reassignments."""
        if flexibility_percent == 0:
            return 0
        if flexibility_percent == 10:
            return tot_ric
        return int(tot_ric * float("0." + str(flexibility_percent)))

    def extract_solution(x_var, z_var):
        """Extract solution from model variables into lists."""
        assigned_x = [
            (k, i, j)
            for k in dep for i in ric for j in pub
            if x_var[k][i].get(j) and x_var[k][i][j].X > 0.5
        ]
        assigned_z = [
            (k, i)
            for k in dep for i in ric
            if z_var[k][i].X > 0.5
        ]
        return assigned_x, assigned_z

    results = {}
    eps = 1e-10

    # ========================================================================
    # PHASE 1: MCMS (Class-first then Score) for all scenarios
    # ========================================================================
    print(f"\n{'='*60}")
    print("PHASE 1: CLASS-FIRST WITH SCORE (MCMS)")
    print(f"{'='*60}")

    for flexibility_percent in scenario_list:
        allowed_change = compute_allowed_change(flexibility_percent)
        scenario_key = f"scenario_{flexibility_percent}"

        print(f"\n>>> Running scenario {flexibility_percent * 10}%")

        results[scenario_key] = {
            "allowed_couples": allowed_couples,
            "ric_initial_dep": ric_initial_dep,
            "allowed_change": allowed_change,
        }

        # STAGE 1: Maximize Classes (MC)
        model_c, x_c, z_c, of_class_c, of_score_c, constr_preassign_c = build_model(allowed_change=allowed_change)
        model_c.setObjective(of_class_c, GRB.MAXIMIZE)
        model_c.optimize()

        assigned_x_class, assigned_z_class = extract_solution(x_c, z_c)
        best_class = model_c.ObjVal

        # STAGE 2: Maximize Score with Classes Constraints (MCMS)
        constr_fix_class = model_c.addConstr(of_class_c >= best_class - eps, name=f"fix_class_{flexibility_percent}")
        model_c.update()
        model_c.setObjective(of_score_c, GRB.MAXIMIZE)
        model_c.optimize()

        assigned_x_mcms, assigned_z_mcms = extract_solution(x_c, z_c)
        best_score_class_first = model_c.ObjVal
        print(f"    Classes: {best_class:.4f}, Scores: {best_score_class_first:.4f}, Status: {model_c.Status}, Gap: {model_c.MIPGap:.2%}")

        results[scenario_key]["MCMS"] = {
            "x": assigned_x_mcms,
            "z": assigned_z_mcms,
            "obj": best_score_class_first,
            "stage": "MCMS",
            "chain": "class_first",
            "optimized_objective": "scores",
            "fixed_objectives": {"classes": best_class},
            "from_scenario": flexibility_percent,
            "status": model_c.Status,
            "obj_bound": model_c.ObjBound if model_c.SolCount > 0 else None,
            "mip_gap": model_c.MIPGap if model_c.SolCount > 0 else None,
            "sol_count": model_c.SolCount,
        }

    # ========================================================================
    # PHASE 2: MS (Direct Score Optimization) for all scenarios
    # ========================================================================
    print(f"\n\n")
    print(f"{'='*60}")
    print("PHASE 2: SCORE-ONLY OPTIMIZATION (MS)")
    print(f"{'='*60}")

    for flexibility_percent in scenario_list:
        allowed_change = compute_allowed_change(flexibility_percent)
        scenario_key = f"scenario_{flexibility_percent}"

        print(f"\n>>> Running scenario {flexibility_percent * 10}%")

        # Optimize Score (MS)
        model_s, x_s, z_s, of_score_s, _, constr_preassign_s = build_model(allowed_change=allowed_change)
        model_s.setObjective(of_score_s, GRB.MAXIMIZE)
        model_s.optimize()

        assigned_x_score, assigned_z_score = extract_solution(x_s, z_s)
        best_score = model_s.ObjVal
        print(f"      Status: {model_s.Status}, Scores: {best_score:.4f}, Gap: {model_s.MIPGap:.2%}")

        results[scenario_key]["MS"] = {
            "x": assigned_x_score,
            "z": assigned_z_score,
            "obj": best_score,
            "stage": "MS",
            "chain": "score_first",
            "optimized_objective": "scores",
            "fixed_objectives": {},
            "from_scenario": flexibility_percent,
            "status": model_s.Status,
            "obj_bound": model_s.ObjBound if model_s.SolCount > 0 else None,
            "mip_gap": model_s.MIPGap if model_s.SolCount > 0 else None,
            "sol_count": model_s.SolCount,
        }

    return results


def export_results_to_csv(results, output_file="optimization_results.csv"):
    """
    Export optimization results to CSV format for easy analysis and sharing.

    Creates a flattened CSV with one row per scenario-stage combination,
    containing key metrics and solution information.

    PARAMETERS:
    -----------
    results : dict
        Results dictionary from run_scenarios()
    output_file : str, default "optimization_results.csv"
        Path to output CSV file

    OUTPUT CSV COLUMNS:
    -------------------
    scenario: Scenario identifier (scenario_0, scenario_1, etc.)
    flexibility_percent: Percentage of researchers that can be reassigned
    stage: Optimization stage (MC, MCMS, MS)
    chain: Optimization chain (class_first, score_first)
    optimized_objective: Which objective was optimized (classes, scores)
    fixed_objectives: Objectives held fixed (JSON string)
    objective_value: Final objective value achieved
    status: Gurobi status code (2=optimal, 9=time_limit, etc.)
    obj_bound: Best bound found (lower bound on optimal)
    mip_gap: Optimality gap percentage
    sol_count: Number of solutions found
    n_assignments_x: Number of publication assignments (x variables)
    n_assignments_z: Number of researcher assignments (z variables)
    runtime_seconds: Solution time in seconds (if available)

    EXAMPLE OUTPUT:
    ---------------
    scenario,flexibility_percent,stage,chain,optimized_objective,fixed_objectives,objective_value,status,obj_bound,mip_gap,sol_count,n_assignments_x,n_assignments_z
    scenario_0,0,MC,class_first,classes,{},1234.56,2,1234.56,0.0015,1,456,78
    scenario_0,0,MCMS,class_first,scores,{"classes": 1234.56},5678.90,2,5678.90,0.0020,1,456,78
    scenario_0,0,MS,score_first,scores,{},5555.40,2,5555.40,0.0018,1,456,78
    ...
    """
    rows = []

    for scenario_key, scenario_data in results.items():
        # Extract flexibility percentage from scenario key
        flexibility_percent = int(scenario_key.split('_')[1])

        # Skip non-stage keys
        for stage_key, stage_data in scenario_data.items():
            if stage_key in ['allowed_couples', 'ric_initial_dep', 'allowed_change']:
                continue

            # Build row data
            row = {
                'scenario': scenario_key,
                'flexibility_percent': flexibility_percent,
                'stage': stage_data.get('stage', stage_key),
                'chain': stage_data.get('chain', 'unknown'),
                'optimized_objective': stage_data.get('optimized_objective', 'unknown'),
                'fixed_objectives': str(stage_data.get('fixed_objectives', {})),
                'objective_value': stage_data.get('obj', None),
                'status': stage_data.get('status', None),
                'obj_bound': stage_data.get('obj_bound', None),
                'mip_gap': stage_data.get('mip_gap', None),
                'sol_count': stage_data.get('sol_count', None),
                'n_assignments_x': len(stage_data.get('x', [])),
                'n_assignments_z': len(stage_data.get('z', [])),
                'runtime_seconds': None,  # Could be added if model runtime is tracked
            }

            rows.append(row)

    # Create DataFrame and sort
    df = pd.DataFrame(rows)
    df = df.sort_values(['flexibility_percent', 'stage'])

    # Export to CSV
    df.to_csv(output_file, index=False, float_format='%.6f')

    print(f"\n✓ Results exported to CSV: {output_file}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {len(df.columns)}")
    print(f"  Scenarios: {len(df['scenario'].unique())}")
    print(f"  Stages: {len(df['stage'].unique())}")

    return df


def main():
    """
    Main execution function.
    
    Workflow:
    1. Load data from Excel
    2. Run optimization across scenarios
    3. Export results to CSV
    """
    # CONFIGURATION: Change the input file name here
    input_file = "P1.xlsx"
    
    print("=" * 70)
    print("RESEARCHER-PUBLICATION ASSIGNMENT OPTIMIZER")
    print("=" * 70)
    print(f"\n[1/3] Loading data from {input_file}...\n")

    # Load data
    data = load_data(input_file)
    
    # Define scenarios
    scenarios = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
     
    print(f"\n[2/3] Running optimization across {len(scenarios)} scenarios...\n")
    results = run_scenarios(scenarios)
    
    print(f"\n[3/3] Exporting results to CSV...\n")
    export_results_to_csv(results, "optimization_results.csv")
    
    print("\n" + "=" * 70)
    print("OPTIMIZATION COMPLETE. Results exported to CSV.")
    print("=" * 70)    

if __name__ == "__main__":
    main()
