# LLM-EvacuationSim

## Basic Information

**Repository:** LLM-EvacuationSim  

**Project Description**

LLM-EvacuationSim is a **multi-agent crowd evacuation simulator** implemented in **Unity 3D**.

The system models pedestrian evacuation using a **Cellular Automaton environment combined with game-theoretic decision models**, and extends the model by integrating **Large Language Model based decision policies**.

The simulator studies how different decision strategies influence **cooperation behavior** and **evacuation efficiency** in emergency scenarios.

This project is inspired by the research:

Evacuation Simulation with Consideration of Obstacle Removal and Using Game Theory (PhysRevE 97, 062303)

The goal of this project is to explore whether **LLM-based reasoning agents (LLM推理代理)** can improve cooperative behavior in crowd evacuation scenarios.

---

# System Requirements

- Unity 2022+ or Unity 2023 LTS  
- C# (Unity scripting)  
- Python (optional for LLM interface)  
- OpenAI API or other LLM provider  
- Windows / macOS / Linux (Unity supported platforms)

No GPU is required for the simulation itself.

---

# Problem Statement

Crowd evacuation is a critical problem in safety engineering, urban planning, and simulation systems. Traditional evacuation models often rely on rule-based navigation or probabilistic decision-making, such as shortest-path planning and game-theoretic strategies. While these approaches can capture certain aspects of crowd behavior, they lack the ability to perform context-aware reasoning and adaptive decision-making in complex and dynamic environments.

In real-world evacuation scenarios, individuals do not only follow fixed rules. Instead, they make decisions based on local observations, social interactions, and situational awareness. For example, individuals may decide whether to yield in crowded situations, choose alternative exits, or voluntarily assist in removing obstacles blocking an exit. Modeling such behaviors requires a more flexible and interpretable decision-making framework.

This project investigates whether Large Language Models (LLMs) can serve as a decision-making layer for agents in evacuation simulations. By incorporating LLM-based reasoning, agents can evaluate their local environment and produce adaptive behaviors that go beyond predefined probabilistic policies.

We focus on the following research questions:

- RQ1: Can LLM-driven decision policies reduce overall evacuation time compared to rule-based and game-theoretic approaches?
- RQ2: Can LLM improve cooperative behaviors such as yielding and volunteering?
- RQ3: Does LLM perform better in high-density or blocked-exit scenarios?
- RQ4: Can LLM provide interpretable and context-aware decisions compared to probabilistic models?

To answer these questions, we design a multi-agent evacuation simulation framework that integrates traditional methods (e.g., greedy navigation, A*, and game theory) with LLM-based decision policies, and evaluate their performance under various scenarios.

---

# Prospective Users

This system may benefit:

### Students and researchers studying

- Multi-agent systems
- Crowd dynamics
- Evacuation modeling
- AI-based decision making

### Researchers interested in

- Applying LLMs to agent-based simulations  
- Studying cooperation behavior in emergencies  
- Experimenting with decision policies in simulated societies  

Users can:

1. Define evacuation environments with exits and obstacles  
2. Run multi-agent simulations with configurable parameters  
3. Compare baseline game-theoretic policies with LLM decision policies  
4. Analyze evacuation performance metrics  

---

# Project Structure and Architecture

## Software Architecture (Scripts Organization)

The codebase is organized into modular systems for clarity and extensibility:

```
Assets/scripts/
├── Core/
│   ├── CellType.cs              (Grid cell types)
│   ├── GridWorld.cs             (Grid environment)
│   └── SimulationManager.cs      (Main simulation controller)
│
├── Agent/
│   ├── PedestrianAgent.cs       (Individual agent)
│   └── AgentManager.cs          (Agent pool management)
│
├── Navigation/  (Week 2-6)
│   ├── FloorField.cs            (Base class)
│   ├── StaticFloorField.cs      (Distance to exits)
│   ├── DynamicFloorField.cs     (Path following)
│   └── AnticipationFloorField.cs (Volunteer areas)
│
├── Decision/  (Week 4-7)
│   ├── DecisionModel.cs         (Base class)
│   ├── RandomWalk.cs            (Baseline: random movement)
│   ├── GreedyStrategy.cs        (Baseline: greedy navigation)
│   ├── AStarPathfinding.cs      (Advanced pathfinding)
│   ├── YielderGame.cs           (Game-theoretic model)
│   ├── VolunteerDilemma.cs      (Bystander effect model)
│   └── LLMDecisionPolicy.cs     (LLM-based reasoning)
│
├── Experiment/  (Week 8-9)
│   ├── ExperimentRunner.cs      (Experiment orchestration)
│   ├── ExperimentConfig.cs      (Parameter configuration)
│   ├── ExperimentResults.cs     (Results object)
│   └── ExperimentAnalyzer.cs    (Statistical analysis)
│
├── Data/
│   ├── SimulationData.cs        (Comprehensive logging)
│   └── DataExporter.cs          (CSV export functionality)
│
├── Visualization/
│   ├── TrajectoryVisualizer.cs  (Agent trajectory playback)
│   ├── HeatmapRenderer.cs       (Crowd density heatmaps)
│   ├── StatisticsPanel.cs       (Real-time metrics display)
│   ├── ComparisonChart.cs       (Multi-strategy comparison charts)
│   └── LLMDecisionExplainer.cs  (Decision explanation UI)
│
└── Utils/
    ├── Utils.cs                 (Utility functions)
    ├── Constants.cs             (Project constants)
    └── Logger.cs                (Logging system)
```

---

## Environment Model

The environment is represented as a **grid-based space**.

Each grid cell may contain:

- Empty space  
- Wall  
- Exit  
- Obstacle  
- Pedestrian agent  

The simulation proceeds in **discrete time steps**, where all agents update simultaneously.

---

## Multi-Agent System

Each pedestrian is modeled as an independent **agent**.

Agent properties include:

- grid position  
- movement direction  
- role (evacuee or volunteer)  
- decision policy  

At each simulation step, agents must decide:

- which neighboring cell to move to  
- whether to yield in movement conflicts  
- whether to volunteer to remove obstacles  

---

# Navigation Model

Agent movement is influenced by three **floor fields**.

## Movement Model

Agent movement is determined by a probabilistic transition model.

At each time step, an agent selects a neighboring cell based on three floor fields:

- Static Floor Field (SFF)
- Dynamic Floor Field (DFF)
- Anticipation Floor Field (AFF)

The transition probability is defined as:

p(i → j) ∝ exp(-k_s S_j + k_d D_j - k_a A_j)

where:

- S_j: static floor field value (distance to exit)
- D_j: dynamic floor field value (crowd trace)
- A_j: anticipation field value (volunteer influence)
- k_s, k_d, k_a: weighting parameters controlling influence strength

The probability is normalized over all valid neighboring cells.

---

## Static Floor Field (SFF)

Represents the distance to exits.

Agents prefer moving toward cells with lower SFF values.

---

## Dynamic Floor Field (DFF)

Represents traces left by previous pedestrians.

Agents tend to follow paths frequently used by others, modeling **herding behavior**.

The dynamic floor field evolves over time using diffusion and decay:

D(t+1) = (1 - δ) * D(t) + α * diffusion

where:

- δ: decay rate (controls how fast traces disappear)
- α: diffusion coefficient (controls how traces spread)

This allows frequently used paths to gradually emerge while preventing long-term accumulation.

---

## Anticipation Floor Field (AFF)

Represents areas around volunteers removing obstacles.

Evacuees avoid these regions to prevent blocking volunteers.

---

# Game-Theoretic Decision Models

Two game-theoretic interaction models are implemented.

## Yielder Game

Occurs when multiple agents attempt to move into the same cell.

Each agent chooses between:

- cooperate (yield)
- defect (insist on moving)

Conflict resolution follows these rules:

- If all agents cooperate, one agent is randomly selected to move
- If one agent defects while others cooperate, the defector moves
- If multiple agents defect, a random tie-break is applied

This models strategic interaction under congestion and captures cooperative behavior in movement conflicts.

---

## Volunteer’s Dilemma

Occurs when agents encounter a blocked exit.

Agents decide whether to:

- volunteer to remove obstacles
- avoid the cost and rely on others

In probabilistic models, the decision to volunteer follows:

q = (c / a)^(1/(N-1))

where:

- c: cost of volunteering
- a: benefit of clearing the obstacle
- N: number of nearby agents

This captures the **bystander effect**, where individuals are less likely to act when more people are present.

---

# Decision Strategy Comparison

This project implements **multiple decision-making strategies** to rigorously evaluate LLM effectiveness:

## Baseline Strategies

### 1. Random Walk
- Agents move randomly in valid directions
- No goal-oriented behavior
- Purpose: Lowest bound on performance

### 2. Greedy Navigation
- Agents always move toward nearest exit
- Simple distance-based priority
- Purpose: Reasonable baseline

### 3. A* Pathfinding
- Optimal path planning with heuristics
- Considers obstacles and congestion
- Purpose: Sophisticated baseline

## Game-Theoretic Models

### 4. Probabilistic Game Theory
- Fixed probability distributions for decisions
- Traditional approach in evacuation research
- Purpose: Standard comparison point

### 5. Context-Aware Game Theory
- Decision probabilities adjust based on environment
- Incorporates floor fields
- Purpose: Intermediate approach

## LLM-Based Strategy

### 6. LLM Reasoning Policy
- Large Language Model makes context-aware decisions
- Receives sensory information (agent density, obstacles, etc.)
- Returns decisions with explanations
- Purpose: Novel AI-driven approach

**Hypothesis**: LLM strategy is expected to improve cooperation and adaptability compared to baseline approaches.

---

# LLM Decision Policy (Extension)

The baseline simulation uses probabilistic game-theoretic decision models.

This project introduces **LLM-based decision policies** as a reasoning layer.

Each agent constructs a structured observation:

{
  "distance_to_exit": int,
  "nearby_agents": int,
  "obstacle_detected": bool,
  "volunteers": int
}

The LLM receives this input and outputs:

{
  "action": ["move", "yield", "volunteer"],
  "reason": string
}

The decision replaces fixed probabilistic rules and enables:

- context-aware reasoning
- adaptive behavior
- interpretable decision-making

This allows agents to dynamically respond to complex situations rather than relying on predefined policies.

---

# Explainable LLM Decisions

To improve interpretability, each LLM decision will include:

- **Decision**
- **Short explanation**

Example:
AgentID: 24

Observation

distance_to_exit: 4

nearby_agents: 7

obstacle_detected: true

volunteers: 0

Decision
volunteer

Explanation
The exit is blocked and no other agents are volunteering.
Removing the obstacle may improve evacuation efficiency.


This allows analysis of **agent reasoning behavior** during evacuation.

---

# Simulation Workflow

Simulation workflow:

Initialize Simulation

- Create environment grid  
- Spawn pedestrian agents  
- Initialize floor fields  

Simulation Step

- Identify potential volunteers  
- Select volunteers  
- Update anticipation field  
- Agents propose moves  
- Resolve movement conflicts  
- Commit movements  
- Update dynamic floor field  

Simulation outputs include:

- agent trajectories  
- evacuation time  
- volunteer statistics  
- exit flow rate  

---

# Evaluation Metrics

Simulation results are evaluated from multiple perspectives:

## (A) Efficiency Metrics
- Average Evacuation Time: Average time required for all agents to exit
- Total Evacuation Time: Time until the last agent exits
- Exit Throughput: Number of agents exiting per unit time

## (B) Behavioral Metrics
- Cooperation Rate: Frequency of yielding behavior in movement conflicts
- Volunteer Rate: Proportion of agents volunteering to remove obstacles

## (C) Spatial Metrics
- Congestion Level: Density of agents near exits

## (D) Statistical Metrics
- Standard Deviation: Variability across multiple runs (robustness measure)

---

# Experimental Design

## Independent Variables

We vary the following factors:

### Strategy
- Random Walk
- Greedy Navigation
- A* Pathfinding
- Probabilistic Game Theory
- Context-Aware Game Theory
- LLM-Based Policy

### Crowd Density
- Small (25 agents)
- Medium (50 agents)
- Large (100 agents)

### Scenario Types
- S1: Single exit (no obstacle)
- S2: Single exit (blocked)
- S3: Dual exits (one blocked)
- S4: High-density congestion scenario

---

## Controlled Variables

To ensure fair comparison across strategies, the following are fixed:

- Grid size
- Agent movement speed
- Observation range
- Simulation time step
- LLM input format (prompt structure)

---

## Experimental Procedure

1. Run each configuration **30 times** with different random seeds
2. Record all evaluation metrics for each run
3. Compute mean and standard deviation
4. Perform cross-strategy comparison

---

## Data Collection

For each simulation run, the system records:

- Evacuation time
- Agent trajectories
- Conflict events
- Volunteer decisions
- Exit usage statistics

All results are exported in CSV format for analysis.

---

# Visualization and Analysis

## Real-Time Visualization

During simulation, the system displays:

- **Agent positions and movements** on the grid
- **Heat maps** showing crowd density
- **Statistics panel** with real-time evacuation metrics
- **LLM decision explanations** (when LLM strategy is active)

## Post-Experiment Analysis

After experiments complete, generate:

### 1. Performance Comparison Charts
- Bar charts comparing evacuation time across strategies
- Line graphs showing convergence over time
- Box plots for variability analysis

### 2. Spatial Analysis
- Trajectory heatmaps for each strategy
- Congestion patterns around exits
- Comparison of agent paths

### 3. Behavioral Analysis
- Cooperation rate trends over time
- Volunteer frequency distributions
- Decision-making pattern analysis

### 4. LLM Decision Explainability
- Sample decision logs with explanations
- Distribution of decision types
- Correlation between context and decisions

### 5. Statistical Reports
- Detailed comparison tables
- Significance tests (t-tests, ANOVA)
- Effect size analysis
- CSV exports for further analysis

---

# Expected Contributions

## Scientific Contributions

This project aims to contribute:

1. **Novel AI Integration**: First application of LLM reasoning in cellular automaton evacuation models
2. **Empirical Evidence**: Rigorous experimental comparison of 6 decision strategies with statistical validation
3. **Cooperation Insights**: Quantitative analysis of how agent reasoning affects collective behavior
4. **Explainability Framework**: Methods for interpreting and validating AI decisions in crowd simulations
5. **Methodology**: Replicable experimental protocol for agent-based evacuation research

## Practical Outputs

- **Comprehensive Dataset**: 30+ runs × 4 scenarios × 6 strategies = 720+ simulations
- **Visualization Tools**: Real-time and post-hoc analysis capabilities
- **Reusable Codebase**: Modular architecture extensible for future research
- **Research Paper**: Publication-ready analysis of results
- **Open-Source Contribution**: Community-accessible simulation framework

---

# Development Schedule

Development timeline (9 weeks)

## Phase 1: Core Framework (Week 1-6)

### Week 1
Project initialization, grid environment, and basic agent system
- Complete: GridWorld, PedestrianAgent, SimulationManager
- Begin: AgentManager

### Week 2
Agent system and Static Floor Field navigation
- Complete: AgentManager, StaticFloorField
- Begin: First baseline strategy (Greedy)

### Week 3
Parallel movement updates and conflict resolution
- Complete: Movement synchronization, YielderGame
- Begin: Probabilistic decision model

### Week 4
Obstacle system and advanced navigation
- Complete: Obstacle mechanics, A* Pathfinding
- Begin: ExperimentConfig and ExperimentRunner

### Week 5
Volunteer dilemma and obstacle removal mechanics
- Complete: VolunteerDilemma, obstacle removal logic
- Enhance: Data collection infrastructure

### Week 6
Dynamic Floor Field, Anticipation Field, and visualization
- Complete: DynamicFloorField, AnticipationFloorField
- Implement: Basic visualization (heatmaps, statistics panel)
- Prepare: ExperimentConfig and initial testing scenarios

## Phase 2: Advanced Systems (Week 7-9)

### Week 7
LLM decision policy integration and explainability
- Integrate: LLMDecisionPolicy with decision explanation
- Complete: LLMDecisionExplainer visualization
- Run: Initial experiments to validate system behavior
- Debug: LLM decision consistency and performance

### Week 8
Comprehensive simulation experiments and statistical analysis
- Run: Full parameter sweep with all 6 strategies
- Collect: All metrics across 30 runs per scenario
- Complete: ExperimentAnalyzer, comparison charts
- Analyze: Mean, standard deviation, and performance comparison

### Week 9
Data analysis, visualization, and final presentation
- Generate: Performance reports and statistical comparisons
- Create: Publication-quality charts and visualizations
- Prepare: Final presentation and research paper
- Interpret: Differences between LLM and baseline strategies

---

# References

1. Lin, G. W., & Wong, S. K. (2018).  
Evacuation simulation with consideration of obstacle removal and using game theory. Physical Review E.

2. Helbing, D., Farkas, I., & Vicsek, T. (2000).  
Simulating dynamical features of escape panic.

3. Nishinari, K., Kirchner, A., Namazi, A., & Schadschneider, A. (2004).  
Cellular automaton approach to pedestrian dynamics.