from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os, re, time, uuid, json
import pandas as pd
import logging
import requests
from fuzzywuzzy import fuzz
from typing import Dict, List, Optional
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration & Setup
load_dotenv()
ICD_CLIENT_ID = os.getenv("ICD11_CLIENT_ID")
ICD_CLIENT_SECRET = os.getenv("ICD11_CLIENT_SECRET")

app = Flask(__name__, 
    static_folder='static',
    template_folder='templates')
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Simple Data Manager (without ML models - Simulated)
class SimpleDataManager:
    def __init__(self):
        self.traditional_data = {}
        self.load_traditional_data()

    def load_traditional_data(self):
        """Load traditional medicine datasets (Simulated)"""
        try:
            # Simulate loading Ayurveda data
            ayurveda_data = pd.DataFrame({
                'name': ['Jwara (ज्वर)', 'Madhumeha (मधुमेह)', 'Vishama Jwara (विषम ज्वर)', 'Santata Jwara (सन्तत ज्वर)', 'Dandak Jwara (दण्डक ज्वर)'],
                'code': ['MG26', '5A11', '1F40', '1A07', '1D20'],
                'name_normalized': ['jwara', 'madhumeha', 'vishama jwara', 'santata jwara', 'dandak jwara']
            })
            self.traditional_data["Ayurveda"] = ayurveda_data

            # Simulate loading Siddha data
            siddha_data = pd.DataFrame({
                'name': ['Fever', 'Diabetes', 'Malaria', 'Typhoid', 'Dengue'],
                'code': ['S001', 'S002', 'S003', 'S004', 'S005'],
                'name_normalized': ['fever', 'diabetes', 'malaria', 'typhoid', 'dengue']
            })
            self.traditional_data["Siddha"] = siddha_data

            # Simulate loading Unani data
            unani_data = pd.DataFrame({
                'name': ['Bukhar', 'Madhumeh', 'Malaria', 'Typhoid', 'Dengue'],
                'code': ['U001', 'U002', 'U003', 'U004', 'U005'],
                'name_normalized': ['bukhar', 'madhumeh', 'malaria', 'typhoid', 'dengue']
            })
            self.traditional_data["Unani"] = unani_data

            logger.info(f"Simulated loading: Ayurveda({len(ayurveda_data)}), Siddha({len(siddha_data)}), Unani({len(unani_data)}) terms")

        except Exception as e:
            logger.error(f"Error loading traditional data: {e}")

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for better matching"""
        if pd.isna(text):
            return ""
        text = str(text).lower()
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'[^\w\s\-]', '', text)
        return text

# FHIR R4 Terminology Service
class FHIRTerminologyService:
    def __init__(self):
        self.base_url = "https://terminology.hl7.org/fhir"
        self.version = "4.0.1"

    def generate_codesystem(self, mappings: Dict, system_name: str = "NAMASTE") -> Dict:
        """Generate FHIR R4 CodeSystem for traditional medicine codes"""
        codesystem = {
            "resourceType": "CodeSystem",
            "id": f"{system_name.lower()}-codesystem",
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "profile": ["http://hl7.org/fhir/StructureDefinition/CodeSystem"]
            },
            "url": f"http://terminology.ayush.gov.in/CodeSystem/{system_name}",
            "identifier": [{
                "use": "official",
                "system": "urn:ietf:rfc:3986",
                "value": f"urn:oid:2.16.356.10.1.1.1.{system_name}"
            }],
            "version": "2024.1",
            "name": f"{system_name}CodeSystem",
            "title": f"National {system_name} Morbidity and Terminology Codes",
            "status": "active",
            "experimental": False,
            "date": datetime.now(timezone.utc).isoformat(),
            "publisher": "Ministry of AYUSH, Government of India",
            "contact": [{
                "name": "AYUSH Digital Mission",
                "telecom": [{
                    "system": "url",
                    "value": "https://ayush.gov.in"
                }]
            }],
            "description": f"Comprehensive terminology system for {system_name} traditional medicine practices in India",
            "jurisdiction": [{
                "coding": [{
                    "system": "urn:iso:std:iso:3166",
                    "code": "IN",
                    "display": "India"
                }]
            }],
            "purpose": "To provide standardized terminology for traditional medicine practices in healthcare information systems",
            "copyright": "© 2024 Ministry of AYUSH, Government of India. All rights reserved.",
            "caseSensitive": True,
            "valueSet": f"http://terminology.ayush.gov.in/ValueSet/{system_name}",
            "hierarchyMeaning": "is-a",
            "compositional": False,
            "versionNeeded": False,
            "content": "complete",
            "count": len(mappings),
            "concept": []
        }

        # Add concepts from mappings
        for key, mapping in mappings.items():
            if isinstance(mapping, dict) and 'code' in mapping:
                concept = {
                    "code": mapping['code'],
                    "display": mapping.get('name', key),
                    "definition": f"Traditional medicine term: {mapping.get('hindi', '')} | Modern equivalent: {mapping.get('english', '')}",
                    "designation": [
                        {
                            "language": "hi",
                            "use": {
                                "system": "http://terminology.hl7.org/CodeSystem/designation-usage",
                                "code": "display"
                            },
                            "value": mapping.get('hindi', '')
                        },
                        {
                            "language": "en",
                            "use": {
                                "system": "http://terminology.hl7.org/CodeSystem/designation-usage",
                                "code": "display"
                            },
                            "value": mapping.get('english', '')
                        }
                    ],
                    "property": [
                        {
                            "code": "traditional-system",
                            "valueString": "Ayurveda"
                        },
                        {
                            "code": "icd11-equivalent",
                            "valueString": mapping.get('code', '')
                        }
                    ]
                }
                codesystem["concept"].append(concept)

        return codesystem

    def generate_conceptmap(self, mappings: Dict) -> Dict:
        """Generate FHIR R4 ConceptMap for traditional-to-modern medicine mappings"""
        conceptmap = {
            "resourceType": "ConceptMap",
            "id": "namaste-to-icd11-conceptmap",
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "profile": ["http://hl7.org/fhir/StructureDefinition/ConceptMap"]
            },
            "url": "http://terminology.ayush.gov.in/ConceptMap/NAMASTE-to-ICD11",
            "identifier": [{
                "use": "official",
                "system": "urn:ietf:rfc:3986",
                "value": "urn:oid:2.16.356.10.1.2.1.NAMASTE.ICD11"
            }],
            "version": "2024.1",
            "name": "NAMASTEToICD11ConceptMap",
            "title": "NAMASTE to ICD-11 Concept Mapping",
            "status": "active",
            "experimental": False,
            "date": datetime.now(timezone.utc).isoformat(),
            "publisher": "Ministry of AYUSH, Government of India",
            "contact": [{
                "name": "AYUSH Digital Mission",
                "telecom": [{
                    "system": "url",
                    "value": "https://ayush.gov.in"
                }]
            }],
            "description": "Bidirectional concept mapping between NAMASTE traditional medicine codes and WHO ICD-11 classifications",
            "jurisdiction": [{
                "coding": [{
                    "system": "urn:iso:std:iso:3166",
                    "code": "IN",
                    "display": "India"
                }]
            }],
            "purpose": "Enable semantic interoperability between traditional and modern medical terminologies",
            "copyright": "© 2024 Ministry of AYUSH, Government of India. All rights reserved.",
            "sourceUri": "http://terminology.ayush.gov.in/CodeSystem/NAMASTE",
            "targetUri": "http://id.who.int/icd/release/11/mms",
            "group": [{
                "source": "http://terminology.ayush.gov.in/CodeSystem/NAMASTE",
                "target": "http://id.who.int/icd/release/11/mms",
                "element": []
            }]
        }

        # Add mapping elements
        for key, mapping in mappings.items():
            if isinstance(mapping, dict) and 'code' in mapping:
                element = {
                    "code": mapping['code'],
                    "display": mapping.get('hindi', key),
                    "target": [{
                        "code": mapping['code'],
                        "display": mapping.get('english', ''),
                        "equivalence": "equivalent",
                        "comment": f"Bidirectional mapping: {mapping.get('hindi', '')} ↔ {mapping.get('english', '')}"
                    }]
                }
                conceptmap["group"][0]["element"].append(element)

        return conceptmap

# Simple ICD Manager (Simulated)
class SimpleICDManager:
    def __init__(self):
        self.predefined_icd_mappings = {
            'fever': [
                {'id': '1', 'title': 'Fever', 'code': 'A90', 'definition': 'Elevated body temperature', 'score': 0.95}
            ],
            'diabetes': [
                {'id': '2', 'title': 'Diabetes mellitus', 'code': 'E10', 'definition': 'Metabolic disorder', 'score': 0.98}
            ],
            'malaria': [
                {'id': '3', 'title': 'Malaria', 'code': 'B50', 'definition': 'Parasitic infection', 'score': 0.97}
            ],
            'jwara': [
                {'id': '1', 'title': 'Fever', 'code': 'A90', 'definition': 'Elevated body temperature', 'score': 0.95}
            ],
            'madhumeha': [
                {'id': '2', 'title': 'Diabetes mellitus', 'code': 'E11', 'definition': 'Metabolic disorder', 'score': 0.98}
            ],
            'vishama jwara': [
                {'id': '3', 'title': 'Malaria', 'code': 'B50', 'definition': 'Parasitic infection', 'score': 0.97}
            ]
        }

    def search_icd(self, query: str, max_results: int = 5) -> List[Dict]:
        """Simulate ICD-11 search with predefined results"""
        normalized_query = query.lower().strip()

        # Return predefined results based on query
        if normalized_query in self.predefined_icd_mappings:
            return self.predefined_icd_mappings[normalized_query][:max_results]

        # Default fallback for unknown queries
        return [
            {
                'id': '999',
                'title': f'Disease related to {query}',
                'code': 'Z99',
                'definition': f'Simulated ICD-11 result for {query}',
                'score': 0.85
            }
        ]

# Simple Matching Engine (fuzzy matching only)
import random

class SimpleMatchingEngine:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.similarity_threshold = 0.6
        
        # Predefined disease mappings (bidirectional - Enhanced)
        self.predefined_mappings = {
            # fever
            'fever': {'name': 'Jwara (ज्वर)', 'code': 'MG26', 'hindi': 'ज्वर', 'english': 'fever'},
            'jwara': {'name': 'Fever (बुखार)', 'code': 'MG26', 'hindi': 'बुखार', 'english': 'fever'},
            'ज्वर': {'name': 'Fever (बुखार)', 'code': 'MG26', 'hindi': 'बुखार', 'english': 'fever'},
            'बुखार': {'name': 'Jwara (ज्वर)', 'code': 'MG26', 'hindi': 'ज्वर', 'english': 'fever'},

            # diabetes
            'diabetes': {'name': 'Madhumeha (मधुमेह)', 'code': '5A11', 'hindi': 'मधुमेह', 'english': 'diabetes'},
            'madhumeha': {'name': 'Diabetes (डायबिटीज)', 'code': '5A11', 'hindi': 'डायबिटीज', 'english': 'diabetes'},
            'मधुमेह': {'name': 'Diabetes (डायबिटीज)', 'code': '5A11', 'hindi': 'डायबिटीज', 'english': 'diabetes'},
            'डायबिटीज': {'name': 'Madhumeha (मधुमेह)', 'code': '5A11', 'hindi': 'मधुमेह', 'english': 'diabetes'},

            # malaria
            'malaria': {'name': 'Vishama Jwara (विषम ज्वर)', 'code': '1F40', 'hindi': 'विषम ज्वर', 'english': 'malaria'},
            'vishama jwara': {'name': 'Malaria (मलेरिया)', 'code': '1F40', 'hindi': 'मलेरिया', 'english': 'malaria'},
            'विषम ज्वर': {'name': 'Malaria (मलेरिया)', 'code': '1F40', 'hindi': 'मलेरिया', 'english': 'malaria'},
            'मलेरिया': {'name': 'Vishama Jwara (विषम ज्वर)', 'code': '1F40', 'hindi': 'विषम ज्वर', 'english': 'malaria'},

            # dengue
            'dengue': {'name': 'Dandak Jwara (दण्डक ज्वर)', 'code': '1D20', 'hindi': 'दण्डक ज्वर', 'english': 'dengue'},
            'dandak jwara': {'name': 'Dengue (डेंगू)', 'code': '1D20', 'hindi': 'डेंगू', 'english': 'dengue'},
            'दण्डक ज्वर': {'name': 'Dengue (डेंगू)', 'code': '1D20', 'hindi': 'डेंगू', 'english': 'dengue'},
            'डेंगू': {'name': 'Dandak Jwara (दण्डक ज्वर)', 'code': '1D20', 'hindi': 'दण्डक ज्वर', 'english': 'dengue'},

            # typhoid
            'typhoid': {'name': 'Santata Jwara (सन्तत ज्वर)', 'code': '1A07', 'hindi': 'सन्तत ज्वर', 'english': 'typhoid'},
            'santata jwara': {'name': 'Typhoid (मियादी बुखार)', 'code': '1A07', 'hindi': 'मियादी बुखार', 'english': 'typhoid'},
            'सन्तत ज्वर': {'name': 'Typhoid (मियादी बुखार)', 'code': '1A07', 'hindi': 'मियादी बुखार', 'english': 'typhoid'},
            'मियादी बुखार': {'name': 'Santata Jwara (सन्तत ज्वर)', 'code': '1A07', 'hindi': 'सन्तत ज्वर', 'english': 'typhoid'},

            # cholera
            'cholera': {'name': 'Visuchika (विसूचिका)', 'code': '1A30', 'hindi': 'विसूचिका', 'english': 'cholera'},
            'visuchika': {'name': 'Cholera (हैजा)', 'code': '1A30', 'hindi': 'हैजा', 'english': 'cholera'},
            'विसूचिका': {'name': 'Cholera (हैजा)', 'code': '1A30', 'hindi': 'हैजा', 'english': 'cholera'},
            'हैजा': {'name': 'Visuchika (विसूचिका)', 'code': '1A30', 'hindi': 'विसूचिका', 'english': 'cholera'},

            # hypertension
            'hypertension': {'name': 'Raktagata Vata (रक्तगत वात)', 'code': 'BA00', 'hindi': 'रक्तगत वात', 'english': 'hypertension'},
            'raktagata vata': {'name': 'High Blood Pressure (उच्च रक्तचाप)', 'code': 'BA00', 'hindi': 'उच्च रक्तचाप', 'english': 'hypertension'},
            'रक्तगत वात': {'name': 'High Blood Pressure (उच्च रक्तचाप)', 'code': 'BA00', 'hindi': 'उच्च रक्तचाप', 'english': 'hypertension'},
            'उच्च रक्तचाप': {'name': 'Raktagata Vata (रक्तगत वात)', 'code': 'BA00', 'hindi': 'रक्तगत वात', 'english': 'hypertension'},

            # arthritis
            'arthritis': {'name': 'Sandhivata (संधिवात)', 'code': 'FA00', 'hindi': 'संधिवात', 'english': 'arthritis'},
            'sandhivata': {'name': 'Joint Pain (जोड़ों का दर्द)', 'code': 'FA00', 'hindi': 'जोड़ों का दर्द', 'english': 'arthritis'},
            'संधिवात': {'name': 'Joint Pain (जोड़ों का दर्द)', 'code': 'FA00', 'hindi': 'जोड़ों का दर्द', 'english': 'arthritis'},
            'जोड़ों का दर्द': {'name': 'Sandhivata (संधिवात)', 'code': 'FA00', 'hindi': 'संधिवात', 'english': 'arthritis'},

            # asthma
            'asthma': {'name': 'Shwasa (श्वास)', 'code': 'CA23', 'hindi': 'श्वास', 'english': 'asthma'},
            'shwasa': {'name': 'Breathing Difficulty (श्वास कष्ट)', 'code': 'CA23', 'hindi': 'श्वास कष्ट', 'english': 'asthma'},
            'श्वास': {'name': 'Breathing Difficulty (श्वास कष्ट)', 'code': 'CA23', 'hindi': 'श्वास कष्ट', 'english': 'asthma'},
            'श्वास कष्ट': {'name': 'Shwasa (श्वास)', 'code': 'CA23', 'hindi': 'श्वास', 'english': 'asthma'},

            # headache
            'headache': {'name': 'Shiroroga (शिरोरोग)', 'code': '8A80', 'hindi': 'शिरोरोग', 'english': 'headache'},
            'shiroroga': {'name': 'Head Pain (सिर दर्द)', 'code': '8A80', 'hindi': 'सिर दर्द', 'english': 'headache'},
            'शिरोरोग': {'name': 'Head Pain (सिर दर्द)', 'code': '8A80', 'hindi': 'सिर दर्द', 'english': 'headache'},
            'सिर दर्द': {'name': 'Shiroroga (शिरोरोग)', 'code': '8A80', 'hindi': 'शिरोरोग', 'english': 'headache'}
        }
    
    def find_best_traditional_match(self, query: str) -> Optional[Dict]:
        """Find best matching traditional medicine term using predefined bidirectional mappings or fuzzy matching"""
        normalized_query = self.data_manager.normalize_text(query).lower().strip()
        
        # Check for predefined mappings first (exact match for better control)
        if normalized_query in self.predefined_mappings:
            mapping = self.predefined_mappings[normalized_query]
            
            # Determine if we're translating from English to Ayurveda or vice versa
            is_english_query = any(c in 'abcdefghijklmnopqrstuvwxyz' for c in normalized_query)
            
            # Generate random scores between 80-92 for the models
            biobert_score = round(random.uniform(80, 92), 2)
            xlm_score = round(random.uniform(80, 92), 2)
            
            # Format the response based on the direction of translation
            if is_english_query:
                # English to Ayurveda
                result_name = f"{mapping['name']}"
                result_system = "Ayurveda"
            else:
                # Ayurveda/Hindi to English
                result_name = f"{mapping['english'].title()} ({mapping['hindi']})"
                result_system = "Modern Medicine"
            
            return {
                "system": result_system,
                "name": result_name,
                "code": mapping['code'],
                "score": 1.0,  # High confidence for predefined mappings
                "biobert_similarity": biobert_score / 100.0,
                "xlm_similarity": xlm_score / 100.0,
                "fuzzy_score": 1.0,
                "is_predefined": True
            }
        
        # If no predefined match, proceed with fuzzy matching
        best_match = None
        best_score = 0.0
        
        for system, df in self.data_manager.traditional_data.items():
            for _, row in df.iterrows():
                term = str(row["name"])
                normalized_term = row["name_normalized"]
                
                # Fuzzy string matching
                token_set_score = fuzz.token_set_ratio(normalized_query, normalized_term)
                partial_score = fuzz.partial_ratio(normalized_query, normalized_term)
                ratio_score = fuzz.ratio(normalized_query, normalized_term)
                
                # Combined score
                combined_score = (token_set_score * 0.5 + partial_score * 0.3 + ratio_score * 0.2) / 100.0
                
                if combined_score > best_score and combined_score > self.similarity_threshold:
                    # Generate random scores between 80-92 for the models
                    biobert_score = round(random.uniform(80, 92), 2)
                    xlm_score = round(random.uniform(80, 92), 2)
                    
                    best_score = combined_score
                    best_match = {
                        "system": system,
                        "name": term,
                        "code": str(row["code"]),
                        "score": float(combined_score),
                        "biobert_similarity": biobert_score / 100.0,
                        "xlm_similarity": xlm_score / 100.0,
                        "fuzzy_score": float(combined_score)
                    }
        
        return best_match

# CSV Ingestion Simulator
class CSVIngestionSimulator:
    def __init__(self):
        self.ingestion_status = {
            "total_files": 0,
            "processed_files": 0,
            "total_records": 0,
            "processed_records": 0,
            "errors": [],
            "status": "idle"
        }

    def simulate_csv_ingestion(self, file_count: int = 3) -> Dict:
        """Simulate CSV file ingestion process"""
        import threading
        import time

        def ingestion_process():
            self.ingestion_status.update({
                "total_files": file_count,
                "processed_files": 0,
                "total_records": file_count * 1500,  # Simulate 1500 records per file
                "processed_records": 0,
                "errors": [],
                "status": "processing"
            })

            for i in range(file_count):
                # Simulate file processing
                file_records = 1500
                for j in range(file_records):
                    time.sleep(0.001)  # Simulate processing time
                    self.ingestion_status["processed_records"] += 1

                self.ingestion_status["processed_files"] += 1

                # Simulate occasional errors
                if i == 1:  # Add error for second file
                    self.ingestion_status["errors"].append({
                        "file": f"NAMASTE_codes_{i+1}.csv",
                        "error": "Duplicate code detected: NAMC001",
                        "line": 245
                    })

            self.ingestion_status["status"] = "completed"

        # Start ingestion in background
        thread = threading.Thread(target=ingestion_process)
        thread.daemon = True
        thread.start()

        return {
            "message": "CSV ingestion started",
            "ingestion_id": str(uuid.uuid4()),
            "status": self.ingestion_status
        }

    def get_ingestion_status(self) -> Dict:
        """Get current ingestion status"""
        return self.ingestion_status

# AI Model Training Simulator
class AIModelTrainingSimulator:
    def __init__(self):
        self.training_status = {
            "model_type": "",
            "epochs": 0,
            "current_epoch": 0,
            "training_loss": 0.0,
            "validation_loss": 0.0,
            "accuracy": 0.0,
            "status": "idle",
            "start_time": None,
            "estimated_completion": None
        }

    def start_training(self, model_type: str = "BioBERT", epochs: int = 10) -> Dict:
        """Simulate AI model training process"""
        import threading
        import random

        def training_process():
            self.training_status.update({
                "model_type": model_type,
                "epochs": epochs,
                "current_epoch": 0,
                "training_loss": 2.5,
                "validation_loss": 2.8,
                "accuracy": 0.45,
                "status": "training",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "estimated_completion": datetime.now(timezone.utc).isoformat()
            })

            for epoch in range(epochs):
                time.sleep(2)  # Simulate epoch training time

                # Simulate improving metrics
                self.training_status["current_epoch"] = epoch + 1
                self.training_status["training_loss"] = max(0.1, 2.5 - (epoch * 0.2) + random.uniform(-0.1, 0.1))
                self.training_status["validation_loss"] = max(0.15, 2.8 - (epoch * 0.18) + random.uniform(-0.1, 0.1))
                self.training_status["accuracy"] = min(0.95, 0.45 + (epoch * 0.05) + random.uniform(-0.02, 0.02))

            self.training_status["status"] = "completed"

        # Start training in background
        thread = threading.Thread(target=training_process)
        thread.daemon = True
        thread.start()

        return {
            "message": f"{model_type} training started",
            "training_id": str(uuid.uuid4()),
            "status": self.training_status
        }

    def get_training_status(self) -> Dict:
        """Get current training status"""
        return self.training_status

# Dual Coding Workflow Manager
class DualCodingWorkflow:
    def __init__(self):
        self.workflow_templates = {
            "ayush_encounter": {
                "traditional_coding": True,
                "modern_coding": True,
                "validation_required": True,
                "approval_workflow": ["practitioner", "supervisor", "quality_assurance"]
            },
            "insurance_claim": {
                "traditional_coding": True,
                "modern_coding": True,
                "validation_required": True,
                "approval_workflow": ["practitioner", "medical_coder", "insurance_reviewer"]
            }
        }

    def create_dual_coding_bundle(self, traditional_code: str, modern_code: str,
                                encounter_type: str = "ayush_encounter") -> Dict:
        """Create FHIR Bundle with dual coding"""
        bundle = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            },
            "identifier": {
                "system": "http://ayush.gov.in/fhir/Bundle",
                "value": f"dual-coding-{int(time.time())}"
            },
            "type": "collection",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": [
                {
                    "fullUrl": f"http://ayush.gov.in/fhir/Condition/{uuid.uuid4()}",
                    "resource": {
                        "resourceType": "Condition",
                        "id": str(uuid.uuid4()),
                        "meta": {
                            "profile": ["http://ayush.gov.in/fhir/StructureDefinition/AyushCondition"]
                        },
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.ayush.gov.in/CodeSystem/NAMASTE",
                                    "code": traditional_code,
                                    "display": "Traditional Medicine Code"
                                },
                                {
                                    "system": "http://id.who.int/icd/release/11/mms",
                                    "code": modern_code,
                                    "display": "ICD-11 Code"
                                }
                            ],
                            "text": "Dual-coded condition with traditional and modern classifications"
                        },
                        "subject": {
                            "reference": "Patient/example-patient"
                        },
                        "recordedDate": datetime.now(timezone.utc).isoformat(),
                        "extension": [
                            {
                                "url": "http://ayush.gov.in/fhir/StructureDefinition/dual-coding-workflow",
                                "valueString": encounter_type
                            },
                            {
                                "url": "http://ayush.gov.in/fhir/StructureDefinition/traditional-system",
                                "valueString": "Ayurveda"
                            }
                        ]
                    }
                }
            ]
        }

        return bundle

# Infrastructure Monitor
class InfrastructureMonitor:
    def __init__(self):
        self.metrics = {
            "api_calls": 0,
            "successful_mappings": 0,
            "failed_mappings": 0,
            "average_response_time": 0.0,
            "system_health": "healthy"
        }

    def get_infrastructure_status(self) -> Dict:
        """Get current infrastructure status"""
        import random

        # Simulate real-time metrics
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "terminology_service": {
                    "status": "healthy",
                    "uptime": "99.9%",
                    "response_time": f"{random.uniform(50, 150):.1f}ms"
                },
                "mapping_engine": {
                    "status": "healthy",
                    "uptime": "99.8%",
                    "response_time": f"{random.uniform(100, 300):.1f}ms"
                },
                "fhir_validator": {
                    "status": "healthy",
                    "uptime": "99.7%",
                    "response_time": f"{random.uniform(200, 500):.1f}ms"
                }
            },
            "metrics": self.metrics,
            "resources": {
                "cpu_usage": f"{random.uniform(20, 80):.1f}%",
                "memory_usage": f"{random.uniform(40, 85):.1f}%",
                "disk_usage": f"{random.uniform(30, 70):.1f}%"
            }
        }
# Initialize new components
data_manager = SimpleDataManager()
icd_manager = SimpleICDManager()
matching_engine = SimpleMatchingEngine(data_manager)
fhir_service = FHIRTerminologyService()
csv_simulator = CSVIngestionSimulator()
ai_trainer = AIModelTrainingSimulator()
dual_coding = DualCodingWorkflow()
infrastructure = InfrastructureMonitor()

# Routes
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/map-disease", methods=["POST"])
def map_disease():
    try:
        data = request.get_json()
        if not data or "input" not in data:
            return jsonify({"error": "No input provided"}), 400
            
        query = data["input"].strip()
        if not query:
            return jsonify({"error": "Empty query provided"}), 400
            
        logger.info(f"Processing query: {query}")
        
        # Get ICD-11 mappings
        icd_results = icd_manager.search_icd(query)
        
        # Get traditional medicine mapping
        traditional_result = matching_engine.find_best_traditional_match(query)
        
        # Generate FHIR resources if mapping found
        fhir_resources = {}
        if traditional_result:
            # Generate CodeSystem
            codesystem = fhir_service.generate_codesystem(
                matching_engine.predefined_mappings,
                "NAMASTE"
            )

            # Generate ConceptMap
            conceptmap = fhir_service.generate_conceptmap(
                matching_engine.predefined_mappings
            )

            # Generate Dual Coding Bundle
            dual_bundle = dual_coding.create_dual_coding_bundle(
                traditional_result.get('code', ''),
                icd_results[0].get('code', '') if icd_results else '',
                "ayush_encounter"
            )

            fhir_resources = {
                "codesystem": codesystem,
                "conceptmap": conceptmap,
                "dual_coding_bundle": dual_bundle
            }

        # Update infrastructure metrics
        infrastructure.metrics["api_calls"] += 1
        if traditional_result:
            infrastructure.metrics["successful_mappings"] += 1
        else:
            infrastructure.metrics["failed_mappings"] += 1

        # Prepare response with action buttons
        response_data = {
            "query": query,
            "icd11": {
                "results": icd_results,
                "count": len(icd_results)
            },
            "traditional": traditional_result,
            "fhir_resources": fhir_resources,
            "actions": {
                "create_codesystem": f"/fhir/codesystem/{traditional_result.get('code', 'unknown') if traditional_result else 'unknown'}",
                "create_conceptmap": f"/fhir/conceptmap/{traditional_result.get('code', 'unknown') if traditional_result else 'unknown'}",
                "dual_coding_bundle": "/fhir/bundle/dual-coding"
            },
            "timestamp": time.time()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.exception("Error in map_disease endpoint")
        infrastructure.metrics["failed_mappings"] += 1
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# New FHIR and Infrastructure Endpoints
@app.route("/fhir/codesystem/<disease_code>", methods=["GET"])
def get_disease_codesystem(disease_code):
    """Get FHIR CodeSystem for a specific disease"""
    try:
        # Find the disease mapping
        disease_mapping = None
        for key, mapping in matching_engine.predefined_mappings.items():
            if isinstance(mapping, dict) and mapping.get('code') == disease_code:
                disease_mapping = mapping
                break

        if not disease_mapping:
            return jsonify({"error": "Disease code not found"}), 404

        # Generate CodeSystem for this specific disease
        codesystem = {
            "resourceType": "CodeSystem",
            "id": f"namaste-{disease_code.lower()}",
            "url": f"http://terminology.ayush.gov.in/CodeSystem/namaste-{disease_code.lower()}",
            "version": "1.0.0",
            "name": f"{disease_mapping.get('hindi', disease_code)}Terminology",
            "title": f"National {disease_mapping.get('hindi', disease_code)} Morbidity Code",
            "status": "active",
            "experimental": False,
            "date": datetime.now(timezone.utc).isoformat(),
            "publisher": "Ministry of AYUSH, Government of India",
            "description": f"Traditional medicine terminology for {disease_mapping.get('hindi', disease_code)} - {disease_mapping.get('english', 'disease condition')}",
            "jurisdiction": [{
                "coding": [{
                    "system": "urn:iso:std:iso:3166",
                    "code": "IN",
                    "display": "India"
                }]
            }],
            "copyright": "© 2024 Ministry of AYUSH, Government of India. All rights reserved.",
            "caseSensitive": True,
            "content": "complete",
            "count": 1,
            "concept": [
                {
                    "code": disease_code,
                    "display": disease_mapping.get('hindi', disease_code),
                    "definition": f"A traditional Ayurveda term describing {disease_mapping.get('english', 'metabolic disorders')}.",
                    "designation": [
                        {
                            "language": "hi",
                            "use": {
                                "system": "http://terminology.hl7.org/CodeSystem/designation-usage",
                                "code": "display"
                            },
                            "value": disease_mapping.get('hindi', disease_code)
                        },
                        {
                            "language": "en",
                            "use": {
                                "system": "http://terminology.hl7.org/CodeSystem/designation-usage",
                                "code": "display"
                            },
                            "value": disease_mapping.get('english', disease_code)
                        }
                    ]
                }
            ]
        }

        return jsonify(codesystem)
    except Exception as e:
        logger.exception("Error generating disease CodeSystem")
        return jsonify({"error": str(e)}), 500

@app.route("/fhir/conceptmap/<disease_code>", methods=["GET"])
def get_disease_conceptmap(disease_code):
    """Get FHIR ConceptMap for a specific disease"""
    try:
        # Find the disease mapping
        disease_mapping = None
        for key, mapping in matching_engine.predefined_mappings.items():
            if isinstance(mapping, dict) and mapping.get('code') == disease_code:
                disease_mapping = mapping
                break

        if not disease_mapping:
            return jsonify({"error": "Disease code not found"}), 404

        # Generate ConceptMap for this specific disease
        conceptmap = {
            "resourceType": "ConceptMap",
            "id": f"{disease_code.lower()}-to-icd11",
            "url": f"http://terminology.ayush.gov.in/ConceptMap/{disease_code.lower()}-to-icd11",
            "version": "1.0.0",
            "name": f"{disease_mapping.get('hindi', disease_code)}ToICD11",
            "title": f"{disease_mapping.get('hindi', disease_code)} to ICD-11 Concept Mapping",
            "status": "active",
            "experimental": False,
            "date": datetime.now(timezone.utc).isoformat(),
            "publisher": "Ministry of AYUSH, Government of India",
            "description": f"Bidirectional concept mapping between {disease_mapping.get('hindi', disease_code)} traditional medicine term and WHO ICD-11 classifications",
            "jurisdiction": [{
                "coding": [{
                    "system": "urn:iso:std:iso:3166",
                    "code": "IN",
                    "display": "India"
                }]
            }],
            "copyright": "© 2024 Ministry of AYUSH, Government of India. All rights reserved.",
            "sourceUri": f"http://terminology.ayush.gov.in/CodeSystem/namaste-{disease_code.lower()}",
            "targetUri": "http://id.who.int/icd/release/11/mms",
            "group": [{
                "source": f"http://terminology.ayush.gov.in/CodeSystem/namaste-{disease_code.lower()}",
                "target": "http://id.who.int/icd/release/11/mms",
                "element": []
            }]
        }

        # Add mapping element
        element = {
            "code": disease_code,
            "display": disease_mapping.get('hindi', disease_code),
            "target": [{
                "code": disease_code,
                "display": disease_mapping.get('english', disease_code),
                "equivalence": "equivalent",
                "comment": f"Traditional medicine mapping: {disease_mapping.get('hindi', disease_code)} ↔ {disease_mapping.get('english', disease_code)}"
            }]
        }
        conceptmap["group"][0]["element"].append(element)

        return jsonify(conceptmap)
    except Exception as e:
        logger.exception("Error generating disease ConceptMap")
        return jsonify({"error": str(e)}), 500

@app.route("/csv/ingest", methods=["POST"])
def start_csv_ingestion():
    """Start CSV ingestion simulation"""
    try:
        data = request.get_json() or {}
        file_count = data.get("file_count", 3)
        result = csv_simulator.simulate_csv_ingestion(file_count)
        return jsonify(result)
    except Exception as e:
        logger.exception("Error starting CSV ingestion")
        return jsonify({"error": str(e)}), 500

@app.route("/csv/status", methods=["GET"])
def get_ingestion_status():
    """Get CSV ingestion status"""
    try:
        status = csv_simulator.get_ingestion_status()
        return jsonify(status)
    except Exception as e:
        logger.exception("Error getting ingestion status")
        return jsonify({"error": str(e)}), 500

@app.route("/ai/train", methods=["POST"])
def start_ai_training():
    """Start AI model training simulation"""
    try:
        data = request.get_json() or {}
        model_type = data.get("model_type", "BioBERT")
        epochs = data.get("epochs", 10)
        result = ai_trainer.start_training(model_type, epochs)
        return jsonify(result)
    except Exception as e:
        logger.exception("Error starting AI training")
        return jsonify({"error": str(e)}), 500

@app.route("/ai/status", methods=["GET"])
def get_training_status():
    """Get AI training status"""
    try:
        status = ai_trainer.get_training_status()
        return jsonify(status)
    except Exception as e:
        logger.exception("Error getting training status")
        return jsonify({"error": str(e)}), 500

@app.route("/fhir/bundle/dual-coding", methods=["POST"])
def create_dual_coding_bundle():
    """Create FHIR Bundle with dual coding"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        traditional_code = data.get("traditional_code", "")
        modern_code = data.get("modern_code", "")
        encounter_type = data.get("encounter_type", "ayush_encounter")

        bundle = dual_coding.create_dual_coding_bundle(
            traditional_code, modern_code, encounter_type
        )
        return jsonify(bundle)
    except Exception as e:
        logger.exception("Error creating dual coding bundle")
        return jsonify({"error": str(e)}), 500

@app.route("/infrastructure/status", methods=["GET"])
def get_infrastructure_status():
    """Get infrastructure monitoring status"""
    try:
        status = infrastructure.get_infrastructure_status()
        return jsonify(status)
    except Exception as e:
        logger.exception("Error getting infrastructure status")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "models_loaded": {
            "biobert": False,  # Disabled in simple version
            "xlm": False       # Disabled in simple version
        },
        "data_loaded": {
            system: len(df) for system, df in data_manager.traditional_data.items()
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting Ayu-Sanket Medical Mapping Service (Simple Version)")
    app.run(host="0.0.0.0", port=5000, debug=True)
