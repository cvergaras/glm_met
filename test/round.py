import pandas as pd

# Read the original CSV
input_file = "met.csv"  # Replace with your actual filename
df = pd.read_csv(input_file)

# Round numeric columns to 2 decimal places, skipping NaNs
numeric_cols = df.columns.drop("time")
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce').round(2)

# Export to a new CSV file
output_file = "output_rounded.csv"
df.to_csv(output_file, index=False)

print(f"Rounded data saved to {output_file}")
