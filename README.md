# InstitutionalGaming_VQR

# Faculty Shuffle: Simulating Institutional Gaming in Research Evaluation

A **mixed-integer programming (MIP)** system for optimally assigning researchers and their publications to academic departments, developed for the Italian VQR (Valutazione della Qualità della Ricerca) research evaluation framework.

Based on mathematical optimization as described in the research paper on researcher assignment algorithms.

## Problem Summary

**Objective:** Assign researchers and their publications to departments while optimizing publication impact scores

**Constraints:**
- Each researcher assigned to exactly one department
- Each publication assigned to at most one researcher per department
- Department capacity limits (publications per researcher ratio)
- Pre-assignment preservation (maintain original assignments with flexibility)
- Author count thresholds (limit number of internal authors per publication)
- Minimum researchers per department (balanced distribution)

## Features

### 1. **Data Loading**
   - Load researcher-publication data from Excel (sheet "Data")
   - Parse and validate all required columns
   - Build optimization data structures

### 2. **Multi-Scenario Analysis**
   - Run optimization across 11 scenarios (0% to 100% flexibility)
   - 0% = strictly maintain original assignments
   - 100% = complete reassignment freedom
   - Each scenario with two optimization strategies

### 3. **Dual Optimization Strategies**
   For each scenario, solve two different approaches:
   
   **Strategy 1: Class-then-Score (MCMS)**
   - Stage 1: Maximize publication classes
   - Stage 2: Maximize scores while maintaining best class value
   - Use case: Quality-focused with score optimization
   
   **Strategy 2: Score-Only (MS)**
   - Direct maximization of publication scores
   - Use case: Impact-focused evaluation

### 4. **CSV Export**
   Exports detailed results for all scenarios and strategies:
   - Optimization metrics (objective value, MIP gap, solver status)
   - Assignment solutions (researcher-publication pairs)
   - Easy analysis in Excel or analysis tools

## Algorithm Overview

### Step 1: Data Loading

Load researcher-publication data from Excel file with required columns:
- Author_ID, Publication_ID, Department
- Score, Class, Internal_Authors_Count, Total_Authors_Count, Assignment_Value

### Step 2: Model Building

**Decision Variables:**
- `x[k,i,j]` ∈ {0,1}: Publication j assigned to researcher i in department k
- `z[k,i]` ∈ {0,1}: Researcher i assigned to department k

**Key Constraints:**
1. Publication capacity: `∑x[k,i,j] ≤ 2.5 × ∑z[k,i]` per department
2. Researcher uniqueness: `∑z[k,i] = 1` per researcher
3. Publication uniqueness: `∑x[k,i,j] ≤ 1` per publication per department
4. Author thresholds: ≤2 internal authors (if total_authors < 6) or ≤1 (if ≥ 6)
5. Pre-assignment: `∑(initial[k,i] × z[k,i]) ≥ tot_researchers - allowed_change`

### Step 3: Multi-Scenario Optimization & Export

For each of 11 scenarios:
1. Compute `allowed_change` based on flexibility percentage
2. PHASE 1: Run MCMS (class-then-score) for all scenarios
3. PHASE 2: Run MS (score-only) for all scenarios
4. Export all results to CSV

## Installation

### Prerequisites
- Python 3.8+
- **Gurobi Optimizer** (free academic license available)
  - [Register for free academic license](https://www.gurobi.com/academia/academic-program-and-licenses/)
  - [Installation guide](https://www.gurobi.com/documentation/current/quickstart.html)
- Excel file with data (see **Input Data Format** below)

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/researcher-assignment-optimizer.git
cd researcher-assignment-optimizer

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Quick Start

**Before running:**
1. Prepare your Excel data file with format specified in **Input Data Format** section below
2. Edit `researcher_assignment_optimizer.py` line 535 to specify your file:
   ```python
   input_file = "your_data.xlsx"  # Change this to your Excel file name
   ```

### Basic Execution

```bash
python researcher_assignment_optimizer.py
```

The script will:
1. Load data from the specified Excel file
2. Run optimization across 11 scenarios (0% to 100% flexibility)
3. Export all results to `optimization_results.csv`
4. Show progress with scenario-by-scenario output

### Customization

Edit the variables in `main()` function (around line 535):

```python
# CONFIGURATION: Change the input file name here
input_file = "P1.xlsx"  # ← MODIFY THIS: use your Excel filename
scenarios = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # ← MODIFY THIS: flexibility scenarios
# Explained: 0=0% flexibility (no changes), 1=10%, 2=20%, ..., 10=100% (full reassignment allowed)
# Example: [0, 5, 10] runs only 3 scenarios for faster results
```

**Example:** If your file is named `researcher_data.xlsx`:
```python
input_file = "researcher_data.xlsx"
```

### Expected Output

```
============================================================
RESEARCHER-PUBLICATION ASSIGNMENT OPTIMIZER
============================================================

[1/3] Loading data from P1.xlsx...

[2/3] Running optimization across 11 scenarios...

============================================================
PHASE 1: CLASS-FIRST WITH SCORE (MCMS)
============================================================

>>> Running scenario 0%
    Classes: 1234.56, Scores: 5678.90, Status: 2, Gap: 0.15%

>>> Running scenario 10%
    Classes: 1289.12, Scores: 5834.45, Status: 2, Gap: 0.18%


============================================================
PHASE 2: SCORE-ONLY OPTIMIZATION (MS)
============================================================

>>> Running scenario 0%
    Scores: 5555.40, Status: 2, Gap: 0.20%

>>> Running scenario 10%
    Scores: 5721.33, Status: 2, Gap: 0.22%

[3/3] Exporting results to CSV...

✓ Results exported to CSV: optimization_results.csv
  Rows: 22
  Columns: 13
  Scenarios: 11
  Stages: 2
```

## Input Data Format

### Excel File Requirements

**Sheet Name:** "Data"

**Required Columns:**
| Column | Type | Description |
|--------|------|-------------|
| Author_ID | Integer | Researcher unique identifier |
| Publication_ID | Integer | Publication unique identifier |
| Department | String | Department assignment |
| Score | Float | Publication impact score |
| Class | Float | Publication class score |
| Internal_Authors_Count | Integer | Number of internal authors |
| Total_Authors_Count | Integer | Total number of authors |
| Assignment_Value | Integer | Pre-assignment value (0 or 1) |

### Example Data

```
Author_ID | Publication_ID | Department | Score | Class | Internal_Authors_Count | Total_Authors_Count | Assignment_Value
----------|----------------|------------|-------|-------|------------------------|---------------------|-------------------
1001      | 20001          | Dept-A     | 85.5  | 3     | 1                      | 4                   | 1
1001      | 20002          | Dept-A     | 72.3  | 2     | 2                      | 5                   | 1
1002      | 20003          | Dept-B     | 91.2  | 3     | 1                      | 3                   | 1
...
```

## Output Files

### CSV Results Export
Automatically exports optimization results to `optimization_results.csv`:

**Structure:**
- One row per scenario-strategy combination
- 11 scenarios × 2 strategies = 22 rows
- Sorted by flexibility percentage and stage

**CSV Columns:**
```
scenario, flexibility_percent, stage, chain, optimized_objective, 
fixed_objectives, objective_value, status, obj_bound, mip_gap, 
sol_count, n_assignments_x, n_assignments_z
```

**Example CSV Content:**
```csv
scenario,flexibility_percent,stage,chain,optimized_objective,fixed_objectives,objective_value,status,obj_bound,mip_gap,sol_count,n_assignments_x,n_assignments_z
scenario_0,0,MCMS,class_first,scores,{"classes": 1234.56},5678.90,2,5678.90,0.0020,1,456,78
scenario_0,0,MS,score_first,scores,{},5555.40,2,5555.40,0.0018,1,456,78
scenario_1,1,MCMS,class_first,scores,{"classes": 1245.33},5701.12,2,5701.12,0.0019,1,458,79
scenario_1,1,MS,score_first,scores,{},5588.76,2,5588.76,0.0021,1,459,80
...
```

### Console Output
- Preprocessing status (data loading confirmation)
- Progress updates for each scenario and optimization phase
- Optimization metrics (status, objective, gap) per scenario/stage
- CSV export summary (rows, columns, scenarios processed)

## Understanding Results

### Optimization Status Codes (Gurobi)
- **2:** Optimal solution found
- **9:** Time limit reached (feasible solution found)
- **3:** Infeasible (no solution exists)
- **4:** Unbounded (objective can be arbitrarily large)

### Key Metrics
- **objective_value:** Final objective value achieved (sum of scores)
- **obj_bound:** Best possible bound from relaxation (lower bound)
- **mip_gap:** (obj_bound - obj) / obj × 100% (optimality gap %)
- **sol_count:** Number of solutions found during optimization

### Comparing Strategies
- **MCMS (Class-then-Score):** Prioritizes publication classes first, then optimizes scores
  - Better when quality ranking matters
  - Guarantees the maximum class value before seeking score improvement
  
- **MS (Score-Only):** Direct score maximization
  - Better for impact/citation-focused metrics
  - Ignores class constraints, pure score optimization

The difference between MCMS and MS objective values reveals the quality-impact trade-off for your dataset.

## Advanced Configuration

### Optimization Parameters

Edit in `run_scenarios()` or `build_model()`:

```python
model.setParam("TimeLimit", 900)        # 15-minute limit per optimization
# model.setParam("MIPGap", 0.001)       # 0.1% optimality tolerance (optional)
```

### Scenario Selection

Modify in `main()`:

```python
scenarios = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # All 11 scenarios (100%)
scenarios = [0, 5, 10]                          # Only 3 scenarios (faster)
```

## Performance Considerations

| Dataset Size | Est. Runtime | Memory | Notes |
|--------------|--------------|--------|-------|
| 500 rows | 10-20 min | 500 MB | Typical, often optimal |
| 1000 rows | 40-80 min | 1 GB | More scenarios may hit time limit |
| 2000+ rows | 2+ hours | 2+ GB | Very slow, consider subset |

**Tips:**
- Start with fewer scenarios (e.g., [0, 10]) for quick testing
- Increase `TimeLimit` for larger datasets
- Run scenarios in parallel on multi-core systems

## Troubleshooting

### Gurobi License Error
```
GurobiError: API call failed with error code 1
```
**Solution:** Install and activate Gurobi academic license
```bash
pip install gurobipy
# Then follow: https://www.gurobi.com/documentation/current/quickstart.html
```

### Out of Memory
**Solution:** Reduce dataset size or run fewer scenarios

### Optimization Takes Too Long
**Solution:** Reduce `TimeLimit` parameter or increase `MIPGap` tolerance

### Empty or Invalid CSV Output
**Solution:** Verify input data columns match required format

## Development

### Project Structure
```
researcher-assignment-optimizer/
├── researcher_assignment_optimizer.py  # Main module
├── README.md                           # This file
├── requirements.txt                    # Dependencies
├── LICENSE                             # Gurobi License
└── P1.xlsx                             # Input data file
```
