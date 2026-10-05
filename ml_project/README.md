# 🤖 BTCUSDT Return Prediction and Trading Strategy

## 📌 Overview

This project explores whether a linear regression model can predict future BTCUSDT returns using historical hourly returns. It covers market-data loading, feature engineering, walk-forward model evaluation, parameter comparisons, and a simulated trading strategy.

---

## 🎯 Problem Statement

**Objective:** Predict the 37-hour forward log return of BTCUSDT from historical return features, then use the prediction to generate long, short, or flat trading positions.

This is a **regression** problem. The model’s predictions are also evaluated for directional accuracy and used in a historical trading simulation.

### Target Variable

**`future_log_return_h`** — the log return from the current close to the close 37 hourly bars later.

---

## 📊 Dataset

The notebook retrieves **hourly BTCUSDT market data** from Binance’s public market-data API.

- **Processed observations:** 78,086
- **Model input features:** 6
- **Bar interval:** 1 hour
- **Configured data window:** July 1, 2015 through August 1, 2026

The notebook requests data from July 2015, but the available BTCUSDT data shown in its output begins on August 17, 2017.

### Data Source

The dataset is retrieved from the **Binance public market-data API** during notebook execution.

---

## 🔎 Exploratory Data Analysis

The notebook inspects the loaded market data and summarizes the target and engineered features.

Key observations include:

- The processed dataset contains 78,086 rows and six model input features.
- The target is a 37-hour forward log return.
- The target’s recorded mean is approximately 0.00128, with a standard deviation of approximately 0.04348.
- The prediction-to-target correlation in the recorded run is low, at approximately 0.0347.

---

## 🧹 Data Preprocessing

The notebook prepares the data by:

- Loading hourly BTCUSDT market data.
- Constructing historical log-return features and a forward-return target.
- Removing rows that cannot be used after feature and target construction.
- Using walk-forward simulation to evaluate predictions over time rather than reporting a conventional random train/test split.

---

## ⚙️ Feature Engineering

The model uses six historical log-return features:

- `ret_125`
- `ret_150`
- `ret_175`
- `ret_200`
- `ret_225`
- `ret_250`

The target horizon is configurable. The selected configuration uses a 37-bar horizon.

---

## 🤖 Machine Learning Models

The notebook uses a **linear regression model** in a walk-forward simulation. It evaluates prediction quality and applies a threshold-based rule to translate predictions into long, short, or flat positions.

The notebook also compares parameter combinations, including:

- Forecast horizons of 36, 37, and 38 bars
- Threshold multipliers of 0.80, 1.0, and 1.2
- Learning rates of 0.00300, 0.00325, and 0.00350
- L2 regularization values of 0.400, 0.425, and 0.450

The recorded selected configuration uses a 37-bar horizon, a 1.0 threshold multiplier, a 0.00325 learning rate, and 0.425 L2 regularization.

---

## 🏆 Final Model

The selected model is the notebook’s **linear regression model evaluated using walk-forward simulation**.

Recorded prediction results:

- **Mean squared error (MSE):** 0.001979
- **Mean absolute error (MAE):** 0.030154
- **Prediction/target correlation:** 0.034685
- **Directional accuracy:** 51.70%

The notebook’s baseline and final prediction summaries show the same metrics for the recorded run.

---

## 📈 Results

The recorded strategy simulation starts with an initial balance of 10,000.

| Metric | Recorded result |
|---|---:|
| Final equity | 16,424.98 |
| Total return | 64.25% |
| Sharpe ratio | 0.840 |
| Maximum drawdown | -8.39% |
| Trades | 658 |
| Long positions | 162 |
| Short positions | 167 |
| Flat positions | 329 |

Important findings include:

- The recorded directional accuracy is 51.70%.
- The recorded prediction/target correlation is low, at approximately 0.0347.
- The simulated trading result includes a 0.10% taker fee rate and a 0.05% slippage rate.

These are historical notebook results, not a guarantee of future performance or live-trading results.

### Model Comparison

The notebook’s recorded baseline and final summaries are identical:

| Evaluation | MSE | MAE | Correlation | Directional accuracy |
|---|---:|---:|---:|---:|
| Baseline prediction | 0.001979 | 0.030154 | 0.034685 | 51.70% |
| Final prediction | 0.001979 | 0.030154 | 0.034685 | 51.70% |

---

## 🧠 Model Interpretation

The notebook reports the following feature coefficients for the recorded model:

| Feature | Coefficient |
|---|---:|
| `ret_125` | -0.000312 |
| `ret_150` | -0.000389 |
| `ret_175` | -0.000396 |
| `ret_200` | -0.000506 |
| `ret_225` | -0.000797 |
| `ret_250` | -0.000921 |

The notebook also generates visualizations of price, equity, positions, and predicted versus actual returns.

---

## 🛠️ Technologies Used

- **Python**
- **Jupyter Notebook**
- **Pandas**
- **NumPy**
- **Matplotlib**
- **Requests**

---

## 📁 Project Structure

```text
ml_project/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── notebooks/
│   └── model_development.ipynb
│
├── data/
│   └── README.md
```

---

## 🚀 How to Run

### 1. Clone the repository

```bash
git clone https://github.com/Tedo2001/GIT/tree/main/ml_project.git
cd ml_project
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows:**

```bash
.venv\Scripts\activate
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the notebook

```bash
jupyter notebook
```

Open:

```text
notebooks/model_development.ipynb
```

and run the cells from top to bottom.

---

## 💡 Future Improvements

Possible improvements to the project include:

* Testing additional features and forecast horizons.
* Comparing the linear model with other forecasting approaches.
* Evaluating performance over separate market regimes.
* Reviewing transaction-cost and execution assumptions.
* Testing the strategy on data not used during parameter selection.
* Monitoring results on new market data.

---

## 📚 Key Takeaways

This project demonstrates practical experience with:

* Loading and inspecting market data
* Time-series feature engineerin
* Regression metrics
* Walk-forward evaluation
* Parameter comparisons
* Simulated trading metrics
* Data visualization with Python

---

## 👤 Author

**[Teodor Lechev]**

[GitHub](https://github.com/Tedo2001) · [LinkedIn](https://nl.linkedin.com/in/teodor-lechev-7068aa29a)

---

## 📄 License

This project is licensed under the **MIT License**.
