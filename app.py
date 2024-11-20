from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
import pandas as pd
import io

app = FastAPI()

# Global variable to store uploaded data
uploaded_data = None

# Utility function to analyze data and provide metrics
def analyze_data(data, num_customers=2):
    # Least-performing customers
    low_performers = data.nsmallest(num_customers, "Total")
    return low_performers

# Utility function to generate suggestions
def generate_suggestions(data, low_performers):
    high_performers = data.nlargest(int(len(data) * 0.25), "Total")
    high_avg = high_performers[["Interactions", "Total Contacts", "Discount Q1", "Discount Q2", "Discount Q3", "Discount Q4"]].mean()

    suggestions = []
    for _, row in low_performers.iterrows():
        reasons = []

        # Interactions suggestion
        interaction_diff = (high_avg["Interactions"] - row["Interactions"]) / high_avg["Interactions"] * 100
        if interaction_diff > 0:
            reasons.append(f"Increase interactions by {interaction_diff:.1f}% to match high performers.")

        # Total contacts suggestion
        contacts_diff = (high_avg["Total Contacts"] - row["Total Contacts"]) / high_avg["Total Contacts"] * 100
        if contacts_diff > 0:
            reasons.append(f"Increase total contacts by {contacts_diff:.1f}% to strengthen relationships.")

        # Discounts suggestion
        for q in ["Discount Q1", "Discount Q2", "Discount Q3", "Discount Q4"]:
            discount_diff = (high_avg[q] - row[q]) / high_avg[q] * 100
            if discount_diff > 0:
                reasons.append(f"Increase {q} by {discount_diff:.1f}% to align with high performers.")

        suggestions.append({
            "Customer": row["Customer"],
            "Region": row["Region"],
            "Total Sales": row["Total"],
            "Suggestions": reasons
        })
    return suggestions

# Utility function to determine reasons for low business
def reasons_for_low_business(low_performers):
    reasons = []
    for _, row in low_performers.iterrows():
        customer_reasons = []

        if row["Interactions"] < 10:
            customer_reasons.append("Number of interactions has been low; try increasing them.")
        avg_discount = (row["Discount Q1"] + row["Discount Q2"] + row["Discount Q3"] + row["Discount Q4"]) / 4
        if avg_discount < 20:
            customer_reasons.append("Discounts are below 20%; consider offering better price offers.")
        if row["Total Contacts"] < 10:
            customer_reasons.append("Number of contacts is low; focus on strengthening relationships.")

        reasons.append({
            "Customer": row["Customer"],
            "Region": row["Region"],
            "Total Sales": row["Total"],
            "Reasons": customer_reasons
        })
    return reasons

# POST endpoint to upload the CSV
@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    try:
        global uploaded_data

        # Read the uploaded file
        contents = await file.read()
        data = pd.read_csv(io.BytesIO(contents))

        # Validate required columns
        required_columns = ["Customer", "Region", "Q1", "Discount Q1", "Q2", "Discount Q2", "Q3", "Discount Q3", "Q4", "Discount Q4", "Total", "Interactions", "Total Contacts"]
        if not all(column in data.columns for column in required_columns):
            return JSONResponse(content={"error": "Invalid CSV format. Missing required columns."}, status_code=400)

        # Store the data globally
        uploaded_data = data

        return JSONResponse(content={"message": "File uploaded successfully."}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# POST endpoint to get least-performing customers
@app.post("/least-performing-customers/")
async def least_performing_customers(num_customers: int = Query(2, ge=1)):
    if uploaded_data is None:
        return JSONResponse(content={"error": "No data uploaded. Please upload a CSV first."}, status_code=400)
    
    low_performers = analyze_data(uploaded_data, num_customers)
    return JSONResponse(content=low_performers.to_dict(orient="records"), status_code=200)

# POST endpoint to get suggestions for improvement
@app.post("/suggestions/")
async def suggestions(num_customers: int = Query(2, ge=1)):
    if uploaded_data is None:
        return JSONResponse(content={"error": "No data uploaded. Please upload a CSV first."}, status_code=400)
    
    low_performers = analyze_data(uploaded_data, num_customers)
    suggestions = generate_suggestions(uploaded_data, low_performers)
    return JSONResponse(content=suggestions, status_code=200)

# POST endpoint to get reasons for low business
@app.post("/reasons-for-low-business/")
async def reasons_low_business(num_customers: int = Query(2, ge=1)):
    if uploaded_data is None:
        return JSONResponse(content={"error": "No data uploaded. Please upload a CSV first."}, status_code=400)
    
    low_performers = analyze_data(uploaded_data, num_customers)
    reasons = reasons_for_low_business(low_performers)
    return JSONResponse(content=reasons, status_code=200)
