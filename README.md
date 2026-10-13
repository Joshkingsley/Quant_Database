**Repository Description**

An open-source quantitative research ecosystem dedicated to building, testing, and validating 100 computational models. We bridge academic theory and applied statistical execution through rigorous distribution analysis, explicitly challenging the "confluence fallacy" in classical system design. To ensure accessibility for different research pipelines, all strategy blueprints and statistical validations are provided in both Python (via Jupyter Notebooks) and R, allowing you to choose the environment that best fits your workflow.

---

# The 100 Quant Project: Empirical Validation & Distribution Analysis

Welcome to the 100 Quant Project. This repository is an ongoing, open-source initiative dedicated to translating 3,000 theories, academic papers, and market hypotheses into strictly validated computational models.

Our objective is simple: **We do not trust theories; we trust distributions.** Every model hosted here undergoes rigorous distribution analysis to strip away market noise and assess whether a proposed theory possesses a genuine, statistically sane edge. We host these models interactively online so researchers, quants, and engineers can view, test, and challenge the math.

## Cross-platform setup

The repository contains source code, notebooks, and research data only. Create a
virtual environment locally; do not commit it. The commands below work on Linux,
macOS, and Windows (with the platform-specific activation command).

```bash
python -m venv .venv
```

Activate it with one of the following commands:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\\Scripts\\Activate.ps1

# Windows Command Prompt
.venv\\Scripts\\activate.bat
```

Then install the shared dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Git normalizes source-file line endings to LF, while Windows command scripts use
CRLF on checkout. This keeps the same clone usable on Linux and Windows without
changing the individual research projects.

## 🧠 Our Core Philosophy: The Confluence Fallacy

A foundational tenet of this repository is a mathematical stance against the traditional concept of "confluence."

Classical trading and baseline predictive modeling often preach that stacking conditions (e.g., waiting for an indicator crossover *plus* a structural break *plus* a volume spike) creates a safer, higher-probability setup. We strongly argue, and statistically prove within these logs, that **excessive confluence is detrimental to robust system design.** Forcing multiple arbitrary filters:

1. Drastically reduces the sample size ($N$), destroying the Law of Large Numbers.
2. Introduces overfitting and compounding noise into the system.
3. Propagates massive error variances when calculating the final probability distribution of expected returns.

**Our Approach:** We build models based on a combination of isolated, statistically sound tests that are proven to work independently. When combined, they form a robust aggregate model rather than a fragile, hyper-filtered one.

## 🛠️ Multi-Language Support: Python & R

Because quantitative research spans multiple disciplines and preferences, the testing and validation layers of this repository are bilingual.

All statistical validation, distribution analysis, and backtesting scripts within the `tests/` directory are written in both **Python** (primarily utilizing Jupyter Notebooks for interactive breakdowns) and **R** (leveraging its superior econometric packages like `rugarch`). You are encouraged to choose and execute the scripts in whichever environment best fits your technical stack.

## 📂 Repository Architecture & Workflow

To maintain order across thousands of scripts, the repository is structured around a strict research pipeline: Theory $\rightarrow$ Baseline Strategy $\rightarrow$ Statistical Validation $\rightarrow$ Advanced AI/RL Integration.

```text
quant_database/
├── README.md                  # You are here
├── strategies/                # Abstract strategy blueprints
│   └── sweep_and_breakout/
│       └── theory_overview.ipynb  # Non-code explanation of the core logic
├── tests/                     # The proving grounds (Available in Python & R)
│   └── sweep_and_breakout/
│       ├── distribution_analysis.py # Validates the raw statistical edge (Python)
│       ├── distribution_analysis.R  # Validates the raw statistical edge (R)
│       ├── backtest_engine.ipynb    # Proves the raw strategy works (Python)
│       └── backtest_engine.R        # Proves the raw strategy works (R)
└── models/                    # The finalized, optimized engines
    └── sweep_and_breakout/
        ├── classical_garch.py       # Econometric baseline
        ├── ml_prob_filter.py        # XGBoost layer added to a proven edge
        └── rl_agent_execution.py    # AI optimized for dynamic reward/penalty

```

### The Workflow in Practice (Example: `sweep_and_breakout`)

1. **The Blueprint:** We start in `strategies/` with a simple Jupyter Notebook (`.ipynb`). This contains *no code*, only the theoretical breakdown of what the strategy entails (e.g., predicting movement ranges and identifying structural points).
2. **The Proving Ground:** The blueprint points to the `tests/` directory. Here, we analyze the different methodologies, error distributions, and run raw backtests. **If the strategy fails here, it is discarded or logged as a failed theory.**
3. **The AI Layer:** If the bare-nature strategy yields a statistically sane and profitable distribution, we move it to `models/`. Only then do we introduce complexity, such as training an ML classification model to filter setups or deploying Reinforcement Learning (RL) agents optimally penalized for drawdowns and rewarded for realized PnL.

## 🔬 Beyond Finance: Expanding the Scope

While this repository originates in quantitative finance, market microstructure, and algorithmic trading, the statistical frameworks developed here (GARCH variance modeling, Markov Decision Processes, gradient boosting) are universally applicable.

As the project scales toward script 100, our research and modeling sections will actively expand into:

* **Epidemiologic Health:** Modeling viral spread, containment distributions, and healthcare capacity forecasting.
* **Computing & Automation:** IoT network state predictions and hardware sensor data cleaning.
* **Molecular & Quantum Modeling:** Statistical mechanics and probabilistic state approximations.

## ⚖️ Disclaimer: Not Financial Advice

**None of the models, code, theories, or datasets provided in this repository constitute financial advice, investment recommendations, or an offer to buy or sell any assets.** This is purely a scientific, statistical, and academic research project. Financial markets are highly volatile, and deploying algorithmic models carries a massive risk of capital loss. Any use of these scripts in live trading environments is done entirely at your own risk. The author and contributors accept absolutely no liability for financial losses incurred through the use of this repository.

## 📄 License

This project is licensed under the **MIT License**. You are free to use, modify, distribute, and integrate this code into your own commercial or private projects, provided that the original license and copyright notice are included.

## 📬 Contact & Contributions

This ecosystem is built and maintained by **Joshua Mwangi**, an automation engineer and quantitative analyst.

If you are a student, researcher, or engineer interested in challenging these distributions, proposing a new mathematical theory to test, or collaborating on the codebase, feel free to reach out.

* **Organization:** CyberNet Africa.
* **LinkedIn:** https://www.linkedin.com/in/joshua-kingsly101/
* **Email:** kingsleymwangi05@gmail.com
