"""
Dual Coding Service for NAMASTE ↔ ICD-11 MMS Mapping
Implements dual coding for traditional medicine and biomedicine
"""

import logging
import re
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple, Any, Union
from fuzzywuzzy import fuzz
from difflib import SequenceMatcher
import unicodedata
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class DualCodingService:
    """
    Service for creating dual coding mappings between traditional medicine and ICD-11.
    Handles semantic matching, fuzzy matching, and mapping between traditional medicine
    terminologies and ICD-11 codes.
    """
    
    def __init__(self, model_manager, data_manager, icd_manager):
        """
        Initialize the DualCodingService with required managers.
        
        Args:
            model_manager: Handles ML models for embeddings and predictions
            data_manager: Manages traditional medicine data
            icd_manager: Handles ICD-11 API interactions
        """
        self.model_manager = model_manager
        self.data_manager = data_manager
        self.icd_manager = icd_manager
        
        # Configuration
        self.similarity_threshold = 0.6
        self.fuzzy_threshold = 75
        self.cache_enabled = True
        
        # Initialize caches
        self._init_caches()
        
        # Initialize mappings
        self._init_ontology_keywords()
        self._init_predefined_mappings()
        self._init_mms_categories()
    
    def _init_caches(self):
        """Initialize in-memory caches for performance optimization"""
        self.embedding_cache = {}
        self.mapping_cache = {}
        self.search_cache = {}
    
    def _init_ontology_keywords(self):
        """Initialize ontology keywords for semantic validation"""
        self.ontology_keywords = {
            "disease": ["disease", "disorder", "syndrome", "condition", "ailment"],
            "symptoms": ["pain", "ache", "fever", "inflammation", "swelling"],
            "body_parts": ["heart", "liver", "kidney", "stomach", "head", "joint"],
            "traditional": ["vata", "pitta", "kapha", "dosha", "rasa", "virya"]
        }
    
    def _init_predefined_mappings(self):
        """Initialize predefined mappings between traditional and modern medicine terms"""
        self.predefined_mappings = {
            # Diabetes - Madhumeha mapping
            "diabetes": {
                "mms_category": "05", 
                "mms_code": "5A11", 
                "confidence": 0.98, 
                "display": "Madhumeha (Diabetes)", 
                "synonyms": ["diabetes mellitus", "hyperglycemia", "madhumeha"], 
                "type": "predefined"
            },
            "madhumeha": {
                "mms_category": "05", 
                "mms_code": "5A11", 
                "confidence": 0.98, 
                "display": "Madhumeha (Diabetes)", 
                "synonyms": ["मधुमेह", "diabetes", "prameha"], 
                "type": "predefined"
            },
            
            # Dengue - Dandak Jwara mapping
            "dengue": {
                "mms_category": "01", 
                "mms_code": "1D20", 
                "confidence": 0.98, 
                "display": "Dandak Jwara (Dengue)", 
                "synonyms": ["breakbone fever", "dandak jwara", "dandaka jwara"], 
                "type": "predefined"
            },
            "dandak jwara": {
                "mms_category": "01", 
                "mms_code": "1D20", 
                "confidence": 0.98, 
                "display": "Dandak Jwara (Dengue)", 
                "synonyms": ["dengue", "breakbone fever"], 
                "type": "predefined"
            },
            
            # Fever - Jwara mapping
            "fever": {
                "mms_category": "01", 
                "mms_code": "MG26", 
                "confidence": 0.95, 
                "display": "Jwara (Fever)", 
                "synonyms": ["pyrexia", "hyperthermia", "jwara"], 
                "type": "predefined"
            },
            "jwara": {
                "mms_category": "01", 
                "mms_code": "MG26", 
                "confidence": 0.95, 
                "display": "Jwara (Fever)", 
                "synonyms": ["fever", "pyrexia", "ज्वर"], 
                "type": "predefined"
            },
            
            # Add more mappings as needed...
        }
    
    def _init_mms_categories(self):
        """Initialize ICD-11 MMS category mappings"""
        self.mms_categories = {
            "01": "Certain infectious or parasitic diseases",
            "02": "Neoplasms", 
            "03": "Diseases of the blood or blood-forming organs",
            "04": "Diseases of the immune system",
            "05": "Endocrine, nutritional or metabolic diseases",
            "06": "Mental, behavioural or neurodevelopmental disorders",
            "07": "Sleep-wake disorders",
            "08": "Diseases of the nervous system",
            "09": "Diseases of the visual system",
            "10": "Diseases of the ear or mastoid process",
            "0B": "Diseases of the respiratory system",
            "0C": "Diseases of the digestive system"
        }
    
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings"""
        if np.linalg.norm(emb1) == 0 or np.linalg.norm(emb2) == 0:
            return 0.0
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    def fuzzy_match_score(self, text1: str, text2: str) -> float:
        """Calculate fuzzy matching score with validation"""
        token_set_score = fuzz.token_set_ratio(text1, text2)
        partial_score = fuzz.partial_ratio(text1, text2)
        ratio_score = fuzz.ratio(text1, text2)
        
        combined_score = (token_set_score * 0.5 + partial_score * 0.3 + ratio_score * 0.2)
        
        if combined_score > 80 and self.validate_semantic_match(text1, text2):
            return combined_score / 100.0
        elif combined_score > 90:
            return combined_score / 100.0
        else:
            return 0.0
    
    def validate_semantic_match(self, text1: str, text2: str) -> bool:
        """Validate if two texts are semantically related"""
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        for category, keywords in self.ontology_keywords.items():
            if any(kw in text1_lower for kw in keywords) and any(kw in text2_lower for kw in keywords):
                return True
        
        words1 = set(text1_lower.split())
        words2 = set(text2_lower.split())
        
        if len(words1.intersection(words2)) >= min(len(words1), len(words2)) * 0.3:
            return True
        
        return False
    
    def transliterate_if_needed(self, text: str) -> str:
        """Transliterate text if it contains non-Latin characters"""
        try:
            if any(ord(char) > 127 for char in text) and hasattr(self.model_manager, 'transliterator') and self.model_manager.transliterator:
                transliterated = self.model_manager.transliterator.transform(text)
                logger.debug(f"Transliterated: {text} -> {transliterated}")
                return transliterated
            return text
        except Exception as e:
            logger.warning(f"Transliteration failed for '{text}': {e}")
            return text
    
    def find_best_traditional_match(self, query: str) -> Optional[Dict]:
        """Find best matching traditional medicine term"""
        normalized_query = self.data_manager.normalize_text(query)
        transliterated_query = self.transliterate_if_needed(normalized_query)
        
        biobert_emb = self.model_manager.get_biobert_embedding(query)
        xlm_emb = self.model_manager.get_xlm_embedding(query)
        
        best_match = None
        best_score = 0.0
        
        for system, df in self.data_manager.traditional_data.items():
            for _, row in df.iterrows():
                term = str(row["name"])
                normalized_term = row["name_normalized"]
                
                scores = []
                
                # 1. Semantic similarity using BioBERT
                term_biobert_emb = self.model_manager.get_biobert_embedding(term)
                biobert_sim = self.cosine_similarity(biobert_emb, term_biobert_emb)
                scores.append(biobert_sim * 0.4)
                
                # 2. Multilingual similarity using XLM-R
                term_xlm_emb = self.model_manager.get_xlm_embedding(term)
                xlm_sim = self.cosine_similarity(xlm_emb, term_xlm_emb)
                scores.append(xlm_sim * 0.3)
                
                # 3. Fuzzy string matching
                fuzzy_score1 = self.fuzzy_match_score(normalized_query, normalized_term)
                fuzzy_score2 = self.fuzzy_match_score(transliterated_query, normalized_term)
                fuzzy_score = max(fuzzy_score1, fuzzy_score2)
                scores.append(fuzzy_score * 0.3)
                
                combined_score = sum(scores)
                
                if combined_score > best_score and combined_score > self.similarity_threshold:
                    best_score = combined_score
                    best_match = {
                        "system": system,
                        "name": term,
                        "code": str(row["code"]),
                        "score": float(combined_score),
                        "biobert_similarity": float(biobert_sim),
                        "xlm_similarity": float(xlm_sim),
                        "fuzzy_score": float(fuzzy_score)
                    }
        
        return best_match
    
    def map_to_icd11(self, traditional_term: str) -> Dict:
        """Map a traditional medicine term to ICD-11"""
        if not traditional_term:
            return {"error": "No term provided"}
            
        # Get ICD-11 mapping
        icd_results = self.icd_manager.search_icd(traditional_term)
        
        # Get traditional medicine mapping
        traditional_result = self.find_best_traditional_match(traditional_term)
        
        # Prepare response
        return {
            "query": traditional_term,
            "icd11": {
                "results": icd_results,
                "count": len(icd_results)
            },
            "traditional": traditional_result
        }
    
    def create_dual_coding(self, namaste_term: str, namaste_code: str, system: str) -> Dict:
        """Create dual coding entry for a NAMASTE term with ICD-11 MMS mapping"""
        
        # Check cache first
        cache_key = f"{namaste_code}_{namaste_term.lower()}"
        if cache_key in self.mapping_cache:
            return self.mapping_cache[cache_key]
        
        # Find best MMS mapping
        mms_mapping = self._find_best_mms_mapping(namaste_term)
        
        dual_coding = {
            "namaste": {
                "system": "http://terminology.ayush.gov.in/CodeSystem/namaste",
                "code": namaste_code,
                "display": namaste_term,
                "traditional_system": system
            },
            "icd11_mms": mms_mapping,
            "mapping_confidence": mms_mapping.get("confidence", 0.0),
            "mapping_method": mms_mapping.get("method", "unknown"),
            "fhir_coding": self._create_fhir_coding(namaste_code, namaste_term, mms_mapping)
        }
        
        # Cache the result
        self.mapping_cache[cache_key] = dual_coding
        return dual_coding
    
    def _find_best_mms_mapping(self, namaste_term: str) -> Dict:
        """Find the best ICD-11 MMS mapping for a NAMASTE term"""
        # First, try direct semantic mapping (including predefined mappings)
        direct_mapping = self._check_semantic_mappings(namaste_term.lower())
        if direct_mapping:
            # For predefined mappings, ensure we have the correct format
            if direct_mapping.get('type') == 'predefined':
                return {
                    "mms_code": direct_mapping["mms_code"],
                    "mms_category": direct_mapping["mms_category"],
                    "display": direct_mapping.get("display", namaste_term),
                    "confidence": direct_mapping.get("confidence", 0.9),
                    "mapping_method": "predefined_mapping",
                    "is_predefined": True
                }
            return direct_mapping
            
        # Then try fuzzy semantic matching
        fuzzy_match = self._fuzzy_semantic_matching(namaste_term.lower())
        if fuzzy_match and fuzzy_match.get("confidence", 0) > 0.7:
            return fuzzy_match
            
        # For specific terms with known mappings
        term_lower = namaste_term.lower()
        specific_mappings = {
            'diabetes': {
                'mms_code': '5A11',
                'mms_category': '05',
                'display': 'Madhumeha (Diabetes)',
                'confidence': 0.98,
                'mapping_method': 'predefined_mapping',
                'is_predefined': True
            },
            'dengue': {
                'mms_code': '1D20',
                'mms_category': '01',
                'display': 'Dandak Jwara (Dengue)',
                'confidence': 0.98,
                'mapping_method': 'predefined_mapping',
                'is_predefined': True
            },
            'malaria': {
                'mms_code': '1F40',
                'mms_category': '01',
                'display': 'Vishama Jwara (Malaria)',
                'confidence': 0.98,
                'mapping_method': 'predefined_mapping',
                'is_predefined': True
            },
            'fever': {
                'mms_code': 'MG26',
                'mms_category': '01',
                'display': 'Jwara (Fever)',
                'confidence': 0.95,
                'mapping_method': 'predefined_mapping',
                'is_predefined': True
            },
            'typhoid': {
                'mms_code': '1A07',
                'mms_category': '01',
                'display': 'Santata Jwara (Typhoid)',
                'confidence': 0.98,
                'mapping_method': 'predefined_mapping',
                'is_predefined': True
            },
            'hypertension': {
                'mms_code': 'BA00',
                'mms_category': 'BA',
                'display': 'Raktagata Vata (Hypertension)',
                'confidence': 0.95,
                'mapping_method': 'predefined_mapping',
                'is_predefined': True
            }
        }
        
        if term_lower in specific_mappings:
            return specific_mappings[term_lower]
            
        # As a last resort, try the ICD-11 API
        api_result = self._enhanced_icd_api_search(namaste_term)
        if api_result:
            return {
                "mms_code": api_result.get("code", ""),
                "mms_category": self._extract_category_from_code(api_result.get("code", "")),
                "display": api_result.get("title", ""),
                "confidence": 0.8 if api_result.get("isPredefined", False) else 0.6,
                "mapping_method": "icd11_api_search" + ("_predefined" if api_result.get("isPredefined", False) else ""),
                "is_predefined": api_result.get("isPredefined", False)
            }
            
        # If all else fails, return a default unknown mapping
        return {
            "mms_code": "",
            "mms_category": "00",
            "display": f"{namaste_term} (Unmapped)",
            "confidence": 0.0,
            "mapping_method": "no_mapping_found",
            "is_predefined": False
        }
    
    def _fuzzy_semantic_matching(self, term_lower: str) -> Dict:
        """Fuzzy matching against semantic mappings and their synonyms with enhanced scoring"""
        matches = []
        
        for key, mapping in self.semantic_mappings.items():
            is_predefined = mapping.get("type") == "predefined"
            
            # Check main term
            main_term_score = fuzz.ratio(term_lower, key.lower())
            if main_term_score >= 75:  # Only consider good matches
                confidence_boost = 1.1 if is_predefined else 1.0
                matches.append({
                    "key": key,
                    "mapping": mapping,
                    "type": "main_term",
                    "score": main_term_score,
                    "confidence": mapping["confidence"] * (main_term_score / 100.0) * confidence_boost,
                    "is_predefined": is_predefined
                })
            
            # Check synonyms with partial matching
            for synonym in mapping.get("synonyms", []):
                synonym_lower = synonym.lower()
                # Use partial ratio for better substring matching
                partial_score = fuzz.partial_ratio(term_lower, synonym_lower)
                token_set_score = fuzz.token_set_ratio(term_lower, synonym_lower)
                
                # Take the best score between different fuzzy matching methods
                synonym_score = max(partial_score, token_set_score)
                
                if synonym_score >= 75:  # Only consider good matches
                    # Slightly reduce confidence for synonym matches
                    confidence = (mapping["confidence"] * 0.9) * (synonym_score / 100.0)
                    if is_predefined:
                        confidence *= 1.1  # Small boost for predefined matches
                        
                    matches.append({
                        "key": key,
                        "mapping": mapping,
                        "type": "synonym",
                        "synonym": synonym,
                        "score": synonym_score,
                        "confidence": confidence,
                        "is_predefined": is_predefined
                    })
        
        if not matches:
            return None
            
        # Sort by confidence (descending) and then by whether it's a predefined match
        matches.sort(key=lambda x: (-x["confidence"], -x["is_predefined"], -x["score"]))
        best_match = matches[0]
        
        return {
            "system": "http://id.who.int/icd/release/11/2025-01/mms",
            "code": best_match["mapping"]["mms_code"],
            "display": f"ICD-11 MMS: {self._get_icd_display_name(best_match['mapping']['mms_code'])}",
            "category": best_match["mapping"]["mms_category"],
            "category_name": self.mms_categories.get(best_match["mapping"]["mms_category"], "Unknown"),
            "confidence": best_match["confidence"],
            "method": f"fuzzy_{'predefined_' if best_match['is_predefined'] else ''}{best_match['type']}",
            "match_score": best_match["score"],
            "matched_term": best_match["synonym"] if best_match["type"] == "synonym" else best_match["key"],
            "is_predefined": best_match["is_predefined"]
        }
    
    def _enhanced_icd_api_search(self, namaste_term: str) -> Optional[Dict]:
        """Enhanced ICD-11 API search with priority to predefined mappings"""
        if not namaste_term.strip():
            return None
            
        # First check if we have a predefined mapping for this term
        predefined = self._check_semantic_mappings(namaste_term.lower())
        if predefined:
            return {
                "title": predefined.get("display", namaste_term),
                "code": predefined["mms_code"],
                "system": "http://id.who.int/icd/release/11/mms",
                "isPredefined": True
            }
            
        # If no predefined mapping, proceed with API search
        search_terms = self._generate_search_terms(namaste_term)
        all_results = []
        
        # Try each search term until we get a good result
        for term in search_terms[:5]:  # Limit to first 5 terms to avoid too many API calls
            try:
                # Search in MMS (Mortality and Morbidity Statistics)
                results = self.icd_manager.search_icd(term, max_results=5)
                if results and 'destination' in results and results['destination']:
                    # Check if any result matches our predefined codes
                    for result in results['destination']:
                        code = result.get('code', '')
                        for _, mapping in self.semantic_mappings.items():
                            if code == mapping.get("mms_code"):
                                return result  # Return immediately for predefined codes
                    
                    # If no predefined code matches, collect for later evaluation
                    all_results.extend(results['destination'])
                
                # Try TM2 (Traditional Medicine) if MMS fails
                tm2_results = self.icd_manager.search_icd(term, max_results=3, linearization="tm2")
                if tm2_results and 'destination' in tm2_results and tm2_results['destination']:
                    best_result = self._select_best_api_result(tm2_results['destination'], namaste_term)
                    if best_result:
                        return {
                            "title": best_result.get("title", ""),
                            "code": best_result.get("code", ""),
                            "system": "http://id.who.int/icd/release/11/2025-01/tm2",
                            "isPredefined": False,
                            "category": "TM2",
                            "category_name": "Traditional Medicine Module 2"
                        }
                        
            except Exception as e:
                logger.warning(f"ICD-11 API search failed for {term}: {e}")
                continue
        
        # If we have any results from MMS search, return the best one
        if all_results:
            best_result = self._select_best_api_result(all_results, namaste_term)
            if best_result:
                return best_result
        
        return None
    
    def _generate_search_terms(self, namaste_term: str) -> List[str]:
        """Generate multiple search terms for better matching"""
        search_terms = [namaste_term]
        term_lower = namaste_term.lower()
        
        # Add synonyms from semantic mappings
        for key, mapping in self.semantic_mappings.items():
            if fuzz.partial_ratio(term_lower, key.lower()) > 60:
                search_terms.extend(mapping.get("synonyms", []))
        
        # Add common English translations
        translation_map = {
            "jwara": ["fever", "pyrexia"],
            "kasa": ["cough"],
            "swasa": ["asthma", "dyspnea", "breathlessness"],
            "madhumeha": ["diabetes", "diabetes mellitus"],
            "kamala": ["jaundice", "icterus"],
            "apasmara": ["epilepsy", "seizure"],
            "unmada": ["psychosis", "mental disorder"],
            "shirashoola": ["headache"],
            "panduroga": ["anemia", "pallor"]
        }
        
        for ayur_term, english_terms in translation_map.items():
            if fuzz.partial_ratio(term_lower, ayur_term) > 70:
                search_terms.extend(english_terms)
        
        # Remove duplicates and empty strings
        return list(set([term.strip() for term in search_terms if term.strip()]))
    
    def _select_best_api_result(self, results: List[Dict], original_term: str) -> Dict:
        """Select the best result from API search results with priority to predefined mappings"""
        if not results:
            return None
            
        # First, check if we have a predefined mapping for this term
        predefined = self._check_semantic_mappings(original_term.lower())
        if predefined:
            # Return a result object that matches our predefined mapping
            return {
                "title": predefined.get("display", original_term),
                "code": predefined["mms_code"],
                "system": "http://id.who.int/icd/release/11/mms",
                "isPredefined": True
            }
        
        # If no predefined mapping, proceed with API results
        scored_results = []
        for result in results:
            title = result.get("title", "")
            code = result.get("code", "")
            
            # Start with basic similarity score
            score = fuzz.ratio(original_term.lower(), title.lower())
            
            # Boost factors
            if original_term.lower() in title.lower():
                score += 30  # Higher boost for exact matches
            
            # Boost for medical relevance
            medical_keywords = ["disease", "disorder", "syndrome", "condition", "infection"]
            if any(keyword in title.lower() for keyword in medical_keywords):
                score += 15
                
            # Check if this is one of our predefined codes
            for _, mapping in self.semantic_mappings.items():
                if code == mapping.get("mms_code"):
                    score += 50  # Big boost for predefined codes
                    break
            
            scored_results.append((score, result))
        
        # Sort by score and return best result if above threshold
        if not scored_results:
            return None
            
        scored_results.sort(key=lambda x: x[0], reverse=True)
        best_score, best_result = scored_results[0]
        
        # Only return if we have a reasonably good match
        if best_score > 60:
            return best_result
            
        return None
    
    def _get_icd_display_name(self, icd_code: str) -> str:
        """Get display name for ICD code"""
        code_names = {
            "MG26": "Fever, unspecified",
            "5A11": "Type 2 diabetes mellitus",
            "CA80": "Cough",
            "CA23": "Asthma",
            "ME10.1": "Jaundice, unspecified",
            "3A00": "Iron deficiency anaemia",
            "8A61": "Epilepsy",
            "6A00": "Schizophrenia or other primary psychotic disorders",
            "8A80": "Headache disorders",
            "1A00": "Cholera",
            "EA80": "Atopic dermatitis"
        }
        return code_names.get(icd_code, f"ICD-11 condition {icd_code}")
    
    def _fallback_category_mapping(self, namaste_term: str) -> Dict:
        """Fallback category inference with improved logic"""
        inferred_category = self._infer_mms_category(namaste_term)
        return {
            "system": "http://id.who.int/icd/release/11/2025-01/mms",
            "code": f"{inferred_category}.Z",
            "display": f"Unspecified condition in {self.mms_categories.get(inferred_category, 'Unknown category')}",
            "category": inferred_category,
            "category_name": self.mms_categories.get(inferred_category, "Unknown"),
            "confidence": 0.3,
            "method": "category_inference"
        }
    
    def _infer_mms_category(self, term: str) -> str:
        """Infer ICD-11 MMS category based on term characteristics"""
        
        term_lower = term.lower()
        
        # Infectious disease indicators
        if any(word in term_lower for word in ["fever", "jwara", "suram", "infection", "viral", "bacterial"]):
            return "01"
        
        # Metabolic/endocrine indicators
        if any(word in term_lower for word in ["diabetes", "madhumeha", "prameha", "metabolic", "thyroid"]):
            return "05"
        
        # Mental health indicators
        if any(word in term_lower for word in ["unmada", "mental", "anxiety", "depression", "psychosis"]):
            return "06"
        
        # Neurological indicators
        if any(word in term_lower for word in ["apasmara", "epilepsy", "seizure", "paralysis", "stroke"]):
            return "08"
        
        # Respiratory indicators
        if any(word in term_lower for word in ["kasa", "swasa", "cough", "asthma", "breathing"]):
            return "0B"
        
        # Digestive indicators
        if any(word in term_lower for word in ["kamala", "jaundice", "liver", "stomach", "digestive"]):
            return "0C"
        
        # Blood disorders
        if any(word in term_lower for word in ["panduroga", "anemia", "blood", "bleeding"]):
            return "03"
        
        # Default to general symptoms
        return "01"
    
    def _extract_category_from_code(self, icd_code: str) -> str:
        """Extract category from ICD-11 code"""
        if len(icd_code) >= 2:
            return icd_code[:2]
        return "01"  # Default
    
    def _get_category_name_from_code(self, icd_code: str) -> str:
        """Get category name from ICD-11 code"""
        category = self._extract_category_from_code(icd_code)
        return self.mms_categories.get(category, "Unknown category")
    
    def _create_fhir_coding(self, namaste_code: str, namaste_term: str, mms_mapping: Dict) -> Dict:
        """Create FHIR CodeableConcept with dual coding"""
        
        return {
            "coding": [
                {
                    "system": "http://terminology.ayush.gov.in/CodeSystem/namaste",
                    "code": namaste_code,
                    "display": namaste_term
                },
                {
                    "system": mms_mapping["system"],
                    "code": mms_mapping["code"],
                    "display": mms_mapping["display"]
                }
            ],
            "text": f"{namaste_term} (Traditional Medicine) mapped to {mms_mapping['display']} (ICD-11 MMS)"
        }
    
    def get_dual_coded_conditions(self, limit: int = 50) -> List[Dict]:
        """Get a list of dual-coded conditions for display"""
        
        dual_coded_conditions = []
        count = 0
        
        for system, df in self.data_manager.traditional_data.items():
            if count >= limit:
                break
                
            for _, row in df.iterrows():
                if count >= limit:
                    break
                    
                namaste_term = str(row["name"])
                namaste_code = str(row["code"])
                
                dual_coding = self.create_dual_coding(namaste_term, namaste_code, system)
                dual_coded_conditions.append(dual_coding)
                count += 1
        
        return dual_coded_conditions
    
    def search_dual_coded_conditions(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for dual-coded conditions matching query"""
        
        results = []
        query_lower = query.lower()
        
        for system, df in self.data_manager.traditional_data.items():
            if len(results) >= limit:
                break
                
            for _, row in df.iterrows():
                if len(results) >= limit:
                    break
                    
                namaste_term = str(row["name"])
                namaste_code = str(row["code"])
                
                # Check if query matches term
                if (query_lower in namaste_term.lower() or 
                    fuzz.partial_ratio(query_lower, namaste_term.lower()) > 70):
                    
                    dual_coding = self.create_dual_coding(namaste_term, namaste_code, system)
                    results.append(dual_coding)
        
        return results
    
    def reverse_lookup(self, icd_code: str, icd_system: str = "mms") -> List[Dict]:
        """Find NAMASTE terms that map to a given ICD-11 code"""
        matching_terms = []
        
        # Search through semantic mappings
        for term, mapping in self.semantic_mappings.items():
            if mapping.get("mms_code") == icd_code:
                # Find corresponding NAMASTE terms
                for system, df in self.data_manager.traditional_data.items():
                    for _, row in df.iterrows():
                        namaste_term = str(row["name"]).lower()
                        if (term.lower() in namaste_term or 
                            fuzz.ratio(term.lower(), namaste_term) > 80):
                            matching_terms.append({
                                "namaste_code": str(row["code"]),
                                "namaste_term": str(row["name"]),
                                "system": system,
                                "confidence": mapping["confidence"],
                                "method": "reverse_semantic_lookup"
                            })
        
        return matching_terms
    
    def bidirectional_search(self, query: str) -> Dict:
        """Search for mappings in both directions (traditional -> modern and modern -> traditional)"""
        results = {
            "traditional_to_modern": [],
            "modern_to_traditional": [],
            "query": query
        }
        
        # Traditional to Modern search
        traditional_results = self.search_dual_coded_conditions(query, limit=10)
        results["traditional_to_modern"] = traditional_results
        
        # Modern to Traditional search (reverse lookup)
        # Try to find ICD codes that match the query
        query_lower = query.lower()
        for term, mapping in self.semantic_mappings.items():
            if (query_lower in term.lower() or 
                any(query_lower in syn.lower() for syn in mapping.get("synonyms", []))):
                reverse_results = self.reverse_lookup(mapping["mms_code"])
                results["modern_to_traditional"].extend(reverse_results)
        
        return results
    
    def get_mapping_statistics(self) -> Dict:
        """Get statistics about dual coding mappings"""
        
        stats = {
            "total_namaste_terms": sum(len(df) for df in self.data_manager.traditional_data.values()),
            "semantic_mappings": len(self.semantic_mappings),
            "cached_mappings": len(self.mapping_cache),
            "mms_categories": len(self.mms_categories),
            "confidence_distribution": {
                "high": 0,  # > 0.8
                "medium": 0,  # 0.5 - 0.8
                "low": 0  # < 0.5
            }
        }
        
        # Analyze confidence distribution from cache
        for mapping in self.mapping_cache.values():
            confidence = mapping.get("mapping_confidence", 0.0)
            if confidence > 0.8:
                stats["confidence_distribution"]["high"] += 1
            elif confidence > 0.5:
                stats["confidence_distribution"]["medium"] += 1
            else:
                stats["confidence_distribution"]["low"] += 1
        
        return stats
