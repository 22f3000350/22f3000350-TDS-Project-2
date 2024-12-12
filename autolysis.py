# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "seaborn",
#     "matplotlib",
#     "requests",
#     "chardet"
# ]
# ///

import os
import sys
import subprocess
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests
import chardet

# Function to ensure all dependencies are installed
def install_dependencies():
    required_packages = ["pandas", "seaborn", "matplotlib", "requests", "chardet"]
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions" 
MODEL = "gpt-4o-mini"
AIPROXY_TOKEN = os.environ.get("AIPROXY_TOKEN")

if not AIPROXY_TOKEN:
    raise EnvironmentError("AIPROXY_TOKEN environment variable not set.")

def send_to_openai(prompt, detail="default"):
    """Send a prompt to the OpenAI API and return the response."""
    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {AIPROXY_TOKEN}"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Summarize the data analysis."},
                {"role": "user", "content": prompt}
            ]
        }
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def summarize_data_overview(df):
    info = df.info(buf=None)
    description = df.describe().to_string()
    nulls = df.isnull().sum().to_string()
    summary = f"Info:\n{info}\n\nDescription:\n{description}\n\nNulls:\n{nulls}"
    return send_to_openai(summary)

def clean_missing_data(df):
    threshold = 0.5
    df_cleaned = df.dropna(axis=1, thresh=len(df) * (1 - threshold))
    df_cleaned = df_cleaned.dropna()
    return df_cleaned

def detect_outliers_and_anomalies(df):
    results = []
    for column in df.select_dtypes(include=['number']):
        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)
        iqr = q3 - q1
        min_val = q1 - 1.5 * iqr
        max_val = q3 + 1.5 * iqr
        results.append(f"{column}: Q1={q1}, Q3={q3}, IQR={iqr}, Min={min_val}, Max={max_val}")
    return send_to_openai("\n".join(results))

def compute_correlation_summary(df):
    try:
        numerical_df = df.select_dtypes(include=["number"])
        correlation = numerical_df.corr()
        correlation_str = correlation.to_string()
        prompt = f"Here is the correlation matrix:\n{correlation_str}\nSummarize the key insights."
        summary = send_to_openai(prompt)
        return summary
    except Exception as e:
        return f"Error in computing correlation: {e}"

def visualize_numerical_columns(df):
    """Visualize numerical columns using pair plots."""
    numerical_cols = df.select_dtypes(include=['number'])
    if not numerical_cols.empty:
        # Ensure there are valid numerical columns with non-NaN values
        valid_cols = numerical_cols.dropna(axis=1, how='all')
        if not valid_cols.empty:
            plt.figure(figsize=(10, 10), dpi=100)
            sns.pairplot(valid_cols)
            img_path = "numerical_plot.png"
            plt.savefig(img_path)
            plt.close()
            print(f"Numerical columns visualization saved as {img_path}.")
            return img_path
        else:
            print("No valid numerical columns with data found for visualization.")
    else:
        print("No numerical columns found for visualization.")


def visualize_categorical_columns(df):
    """Visualize categorical columns using bar plots."""
    categorical_cols = df.select_dtypes(include=['object', 'category'])
    if not categorical_cols.empty:
        for col in categorical_cols.columns:
            unique_values_count = df[col].nunique()  # Count unique values in the column
            if unique_values_count > 30:
                print(f"Skipping {col} as it has {unique_values_count} unique values.")
                continue  # Skip columns with more than 20 unique values
            
            # Proceed to plot if unique values are <= 20
            plt.figure(figsize=(8, 8), dpi=100)
            sns.countplot(y=col, data=df, order=df[col].value_counts().index)
            img_path = f"{col}_plot.png"
            plt.title(f"Distribution of {col}")
            plt.savefig(img_path)
            plt.close()
            return img_path
    else:
        print("No categorical columns found for visualization.")


def main(csv_file):
    with open(csv_file, 'rb') as f:
        result = chardet.detect(f.read())
        encoding = result['encoding']

    df = pd.read_csv(csv_file, encoding=encoding)
    all_summaries = []  # To accumulate all summaries for final context

    with open("README.md", "w") as readme:
        readme.write("# Automated Data Analysis\n\n")

        # Data Overview
        summary_1 = summarize_data_overview(df)
        all_summaries.append(f"## Data Overview\n{summary_1}")
        readme.write(f"## Data Overview\n{summary_1}\n\n")

        # Clean Data
        df = clean_missing_data(df)

        # Outlier Detection
        summary_3 = detect_outliers_and_anomalies(df)
        all_summaries.append(f"## Outlier Detection\n{summary_3}")
        readme.write(f"## Outlier Detection\n{summary_3}\n\n")

        # Correlation Analysis
        summary_4 = compute_correlation_summary(df)
        all_summaries.append(f"## Correlation Matrix\n{summary_4}")
        readme.write(f"## Correlation Matrix\n{summary_4}\n\n")

        # Numerical Visualization
        img_path_5 = visualize_numerical_columns(df)
        if img_path_5:
            numerical_summary = f"Numerical data has been visualized. The plot is saved as {img_path_5}."
            all_summaries.append(numerical_summary)
            readme.write(f"## Numerical Visualization\n![Numerical Plot]({img_path_5})\n\n")

        # Categorical Visualization
        img_path_6 = visualize_categorical_columns(df)
        if img_path_6:
            categorical_summary = f"Categorical data has been visualized. The plot is saved as {img_path_6}."
            all_summaries.append(categorical_summary)
            readme.write(f"## Categorical Visualization\n![Categorical Plot]({img_path_6})\n\n")

        # Final Story Generation
        full_context = "\n\n".join(all_summaries)
        final_story = send_to_openai(f"Here is the complete analysis:\n\n{full_context}\n\nSummarize this analysis into a cohesive story.")
        readme.write(f"## Final Story\n{final_story}\n\n## Numerical Visualization\n![Numerical Plot]({img_path_5})\n\n## Categorical Visualization\n![Categorical Plot]({img_path_6})\n\n")


if __name__ == "__main__":
    install_dependencies()
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <csv_file>")
        sys.exit(1)
    main(sys.argv[1])
