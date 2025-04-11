import pandas as pd
import os
import numpy as np
from dotenv import load_dotenv
from pymongo import MongoClient


def main():
    # Load environment variables from .env
    load_dotenv()

    # Access the variables
    mongo_url = os.getenv("MONGO_URI")

    if mongo_url:
        # Load Excel File
        df = pd.read_excel("emdat.xlsx")
        print("Excel file loaded successfully!")
        print(df.head())

        # Connect to MongoDB Atlas
        client = MongoClient(mongo_url)
        db = client.get_database('test_db')
        collection = db["emdat_test1"]
        print(f"Database connected successfully: {db.name}: {collection.name}")

        # Clean Data
        cleaned_df = clean_data(df)

        # Transform Data
        print("Transforming data...")
        transformed_df = transform_data(cleaned_df)
        print("Transforming data done.")

        # Load Data
        try:
            print("Loading data...")
            collection.delete_many({})  # wipe all existing documents
            collection.insert_many(transformed_df, ordered=False)
            print(f"Inserted {collection.count_documents({})} documents.")
            print("Loading data done")

        except Exception as e:
            print("Failed to insert documents.")
            print(f"Error: {e}")

    else:
        print("Missing environment variables. Please check your environment file.")


# Format data from Excel
def clean_data(df):
    # Remove duplicates
    df.drop_duplicates(subset="DisNo.", keep="first", inplace=True)

    # Drop unused columns
    df.drop(['Admin Units', 'Entry Date', 'Last Update', 'Origin', 'Associated Types',
             'Latitude', 'Longitude'], axis=1, inplace=True)

    # Dictionary to custom fill NaN values
    fillna_values = {'External IDs': np.nan, 'Event Name': np.nan, 'Location': np.nan, 'AID Contribution': np.nan,
                     'Magnitude': np.nan, 'Magnitude Scale': np.nan, 'River Basin': np.nan, 'Start Month': 0, 'Start Day': 0,
                     'End Month': 0, 'End Day': 0,
                     'Total Deaths': np.nan, 'No. Injured': np.nan, 'No. Affected': np.nan, 'No. Homeless': np.nan,
                     'Total Affected': np.nan, 'Reconstruction Costs (\'000 US$)': np.nan,
                     'Insured Damage (\'000 US$)': np.nan, 'Total Damage (\'000 US$)': np.nan,
                     'AID Contribution (\'000 US$)': np.nan, 'CPI': np.nan,
                     'Reconstruction Costs, Adjusted (\'000 US$)': np.nan, 'Insured Damage, Adjusted (\'000 US$)': np.nan,
                     'Total Damage, Adjusted (\'000 US$)': np.nan}

    df.fillna(fillna_values, inplace=True)

    # Format data
    df.replace({"Country": {"Taiwan (Province of China)": "Taiwan"}}, inplace=True)

    # Numeric format to 1000
    money_columns = {
        "AID Contribution ('000 US$)": "AID Contribution (US$)",
        "Reconstruction Costs ('000 US$)": "Reconstruction Costs (US$)",
        "Insured Damage ('000 US$)": "Insured Damage (US$)",
        "Total Damage ('000 US$)": "Total Damage (US$)",
        "Total Damage, Adjusted ('000 US$)": "Total Damage, Adjusted (US$)",
        "Insured Damage, Adjusted ('000 US$)": "Insured Damage, Adjusted (US$)",
        "Reconstruction Costs, Adjusted ('000 US$)": "Reconstruction Costs, Adjusted (US$)"
    }

    df.rename(columns=money_columns, inplace=True)

    return df


# Transform data from Excel into MongoDB Atlas
def transform_data(df):
    transformed_data = []
    for _, row in df.iterrows():
        data = {
            "_id": row["DisNo."],
            "disaster_info": {
                "historic": True if row["Historic"].lower() == "yes" else False,
                "classification_key": row["Classification Key"],
                "disaster_group": row["Disaster Group"],
                "disaster_subgroup": row["Disaster Subgroup"],
                "disaster_type": row["Disaster Type"],
                "disaster_subtype": row["Disaster Subtype"],
                "external_id": row["External IDs"],
                "event_name": row["Event Name"],
                "magnitude": to_numeric(row["Magnitude"]),
                "magnitude_scale": row["Magnitude Scale"]
            },
            "location_info": {
                "iso": row["ISO"],
                "country": row["Country"],
                "region": row["Region"],
                "subregion": row["Subregion"],
                "location": row["Location"],
            },
            "response_info": {
                "ofda_response": row["OFDA/BHA Response"],
                "appeal_launched": row["Appeal"],
                "gov_declaration": row["Declaration"]
            },
            "impact_info": {
                "river_basin": row["River Basin"],
                "total_deaths": to_numeric(row["Total Deaths"]),
                "injured_number": to_numeric(row["No. Injured"]),
                "affected_number": to_numeric(row["No. Affected"]),
                "homeless_number": to_numeric(row["No. Homeless"]),
                "total_affected": to_numeric(row["Total Affected"]),
            },
            "financial_info": {
                "aid_contribution_usd": to_numeric(row["AID Contribution (US$)"])*1000,
                "reconstruction_cost_usd": to_numeric(row["Reconstruction Costs (US$)"])*1000,
                "reconstruction_cost_usd_adjusted": to_numeric(row["Reconstruction Costs, Adjusted (US$)"])*1000,
                "insured_damage_usd": to_numeric(row["Insured Damage (US$)"])*1000,
                "insured_damage_usd_adjusted": to_numeric(row["Insured Damage, Adjusted (US$)"])*1000,
                "total_damage_usd": to_numeric(row["Total Damage (US$)"])*1000,
                "total_damage_usd_adjusted": to_numeric(row["Total Damage, Adjusted (US$)"])*1000,
                "cpi": to_numeric(row["CPI"])
            },
            "timeline": {
                "start_year": to_numeric(row["Start Year"]),
                "start_month": to_numeric(row["Start Month"]),
                "start_day": to_numeric(row["Start Day"]),
                "end_year": to_numeric(row["End Year"]),
                "end_month": to_numeric(row["End Month"]),
                "end_day": to_numeric(row["End Day"])
            }
        }
        transformed_data.append(data)

    return transformed_data


def to_numeric(value):
    try:
        num = float(value)
        return num
    except (ValueError, TypeError):
        return np.nan


if __name__ == "__main__":
    main()
