"""
Data Ingestion Module
Reads Excel file, processes data, creates embeddings, and ingests into MongoDB
"""

import pandas as pd
import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import logging
from tqdm import tqdm
import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataIngestion:
    def __init__(self, excel_file: str, mongodb_uri: str):
        """Initialize data ingestion with Excel file and MongoDB connection"""
        self.excel_file = excel_file
        self.mongodb_uri = mongodb_uri
        self.client = None
        self.db = None
        self.embedding_model = None

    def connect_mongodb(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.mongodb_uri)
            self.db = self.client[config.DATABASE_NAME]
            logger.info(f"Connected to MongoDB database: {config.DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    # def load_embedding_model(self):
    #     """Load the sentence transformer model for embeddings"""
    #     try:
    #         logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
    #         self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
    #         logger.info("Embedding model loaded successfully")
    #     except Exception as e:
    #         logger.error(f"Failed to load embedding model: {e}")
    #         raise

    def read_excel(self) -> pd.DataFrame:
        """Read Excel file and return DataFrame"""
        try:
            logger.info(f"Reading Excel file: {self.excel_file}")
            df = pd.read_excel(self.excel_file)

            def merged(x):
                return ",".join(
                    [
                        t.strip()
                        for t in x.dropna()
                        .drop_duplicates()
                        .astype(str)
                        .str.cat(sep=",")
                        .split(",")
                    ]
                )

            df["Typical Titles"] = df[
                [
                    "Executive \nTypical Titles",
                    "Management \nTypical Titles",
                    "Professional \nTypical Titles",
                    "Para-Professional / \nSupport Typical Titles",
                ]
            ].apply(merged, axis=1)

            df = df.drop(
                columns=[
                    "Executive \nTypical Titles",
                    "Management \nTypical Titles",
                    "Professional \nTypical Titles",
                    "Para-Professional / \nSupport Typical Titles",
                ]
            )
            logger.info(f"Loaded {len(df)} rows from Excel")
            logger.info(f"Columns: {df.columns.tolist()}")
            return df
        except Exception as e:
            logger.error(f"Failed to read Excel file: {e}")
            raise

    # def create_embedding(self, text: str) -> List[float]:
    #     """Create embedding for given text"""
    #     if not text or pd.isna(text):
    #         text = ""
    #     embedding = self.embedding_model.encode(str(text), normalize_embeddings=True)
    #     return embedding.tolist()
    def create_embedding(self, text: str) -> List[float]:  # (texts):
        """
        Simple function to call MMC embeddings API
        """

        url = "https://stg1.mmc-bedford-int-non-prod-ingress.mgti.mmc.com/coreapi/llm/embeddings/v1/mmc-tech-text-embedding-3-large"

        headers = {
            "x-api-key": "3d0e6c31-7016-4038-883b-e7f97ef4439b-12e88bc6-e92f-4d26-98c9-74f164fe51e7",
            "Content-Type": "application/json",
        }

        data = {
            "input": text,
            "user": "user-123",
            "input_type": "query",
            "encoding_format": "float",
            "model": "text-embedding-3-large",
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json() if response.status_code == 200 else response.text
        embeddings_data = sorted(result["data"], key=lambda x: x["index"])
        embeddings = [item["embedding"] for item in embeddings_data]
        return embeddings

    def process_specialties(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Process job specialties data
        Combines spec title + spec description for embedding
        """
        logger.info("Processing job specialties data...")
        specialties = []
        # df["Specialization Code"].tolist(),
        # df["Family Code"].tolist(),
        # df["Sub Family Code"].tolist(),
        # df["Specialization Title"].tolist(),
        # df["Specialization Description"].tolist(),

        # Group by spec code to avoid duplicates
        grouped = df.groupby("Specialization Code").first().reset_index()

        for idx, row in tqdm(
            grouped.iterrows(), total=len(grouped), desc="Processing specialties"
        ):
            # Combine spec title and description for rich embedding
            spec_title = (
                str(row.get("Specialization Title", ""))
                if pd.notna(row.get("Specialization Title"))
                else ""
            )
            spec_description = (
                str(row.get("Specialization Description", ""))
                if pd.notna(row.get("Specialization Description"))
                else ""
            )
            combined_text = f"{spec_title}. {spec_description}".strip()

            # Create embedding
            embedding = self.create_embedding(combined_text)

            specialty_doc = {
                "spec_code": str(row["Specialization Code"]),
                "spec_title": spec_title,
                "spec_description": spec_description,
                "family_code": (
                    str(row.get("Family Code", ""))
                    if pd.notna(row.get("Family Code"))
                    else ""
                ),
                "family_title": (
                    str(row.get("Family Title", ""))
                    if pd.notna(row.get("Family Title"))
                    else ""
                ),
                "sub_family_code": (
                    str(row.get("Sub Family Code", ""))
                    if pd.notna(row.get("Sub Family Code"))
                    else ""
                ),
                "sub_family_title": (
                    str(row.get("Sub Family Title", ""))
                    if pd.notna(row.get("Sub Family Title"))
                    else ""
                ),
                "combined_text": combined_text,
                "embedding": embedding,
            }
            specialties.append(specialty_doc)

        logger.info(f"Processed {len(specialties)} specialties")
        return specialties

    def process_aliases(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Process alias titles
        Expands comma-separated alias titles into individual rows
        """
        logger.info("Processing alias titles...")
        aliases = []

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing aliases"):
            alias_titles = row.get("Typical Titles", "")

            if pd.isna(alias_titles) or not alias_titles:
                continue

            # Split comma-separated aliases
            alias_list = [
                alias.strip() for alias in str(alias_titles).split(",") if alias.strip()
            ]

            for alias_title in alias_list:
                # Create embedding for each alias
                embedding = self.create_embedding(alias_title)

                alias_doc = {
                    "alias_title": alias_title,
                    "spec_code": str(row["Specialization Code"]),
                    "spec_title": (
                        str(row.get("Specialization Title", ""))
                        if pd.notna(row.get("Specialization Title"))
                        else ""
                    ),
                    "family_code": (
                        str(row.get("Family Code", ""))
                        if pd.notna(row.get("Family Code"))
                        else ""
                    ),
                    "family_title": (
                        str(row.get("Family Title", ""))
                        if pd.notna(row.get("Family Title"))
                        else ""
                    ),
                    "sub_family_code": (
                        str(row.get("Sub Family Code", ""))
                        if pd.notna(row.get("Sub Family Code"))
                        else ""
                    ),
                    "sub_family_title": (
                        str(row.get("Sub Family Title", ""))
                        if pd.notna(row.get("Sub Family Title"))
                        else ""
                    ),
                    "embedding": embedding,
                }
                aliases.append(alias_doc)

        logger.info(f"Processed {len(aliases)} alias titles")
        return aliases

    def ingest_to_mongodb(self, collection_name: str, documents: List[Dict[str, Any]]):
        """Ingest documents into MongoDB collection"""
        try:
            collection = self.db[collection_name]

            # Clear existing data
            logger.info(f"Clearing existing data in {collection_name}...")
            collection.delete_many({})

            # Insert documents in batches
            batch_size = 1000
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                collection.insert_many(batch)
                logger.info(
                    f"Inserted {i + len(batch)}/{len(documents)} documents into {collection_name}"
                )

            logger.info(
                f"Successfully ingested {len(documents)} documents into {collection_name}"
            )

        except Exception as e:
            logger.error(f"Failed to ingest data into {collection_name}: {e}")
            raise

    def run(self):
        """Run the complete data ingestion pipeline"""
        try:
            # Step 1: Connect to MongoDB
            self.connect_mongodb()

            # Step 2: Load embedding model
            # self.load_embedding_model()

            # Step 3: Read Excel file
            df = self.read_excel()
            # df = df.head()

            # Step 4: Process specialties
            # specialties = self.process_specialties(df)

            # Step 5: Ingest specialties
            # self.ingest_to_mongodb(config.SPEC_COLLECTION, specialties)

            # Step 6: Process aliases
            aliases = self.process_aliases(df)

            # Step 7: Ingest aliases
            self.ingest_to_mongodb(config.ALIAS_COLLECTION, aliases)

            logger.info("Data ingestion completed successfully!")

        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            raise
        finally:
            if self.client:
                self.client.close()
                logger.info("MongoDB connection closed")


if __name__ == "__main__":
    # Run data ingestion
    ingestion = DataIngestion(
        excel_file=config.INPUT_EXCEL_FILE, mongodb_uri=config.MONGODB_URI
    )
    ingestion.run()
