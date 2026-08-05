"""
FHIR R4 Compliant REST Endpoints for NAMASTE-ICD11 Integration
Implements India's 2016 EHR Standards with OAuth 2.0 and audit trails
"""

from flask import Flask, request, jsonify, g
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import uuid
import logging
from typing import Dict, List, Optional, Any
from fhir_models import FHIRNAMASTEManager
from fhir.resources.operationoutcome import OperationOutcome, OperationOutcomeIssue
from fhir.resources.parameters import Parameters, ParametersParameter
import json

logger = logging.getLogger(__name__)

class FHIRTerminologyService:
    """FHIR R4 compliant terminology service for NAMASTE-ICD11 integration"""
    
    def __init__(self, app: Flask, data_manager, icd_manager):
        self.app = app
        self.data_manager = data_manager
        self.icd_manager = icd_manager
        self.fhir_manager = FHIRNAMASTEManager()
        self.audit_log = []
        
        # Initialize JWT
        app.config['JWT_SECRET_KEY'] = 'your-secret-key-change-in-production'
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
        self.jwt = JWTManager(app)
        
        self._register_fhir_endpoints()
    
    def _register_fhir_endpoints(self):
        """Register FHIR R4 compliant endpoints"""
        
        # FHIR Capability Statement
        @self.app.route("/fhir/metadata", methods=["GET"])
        def capability_statement():
            return self._create_capability_statement()
        
        # CodeSystem endpoints
        @self.app.route("/fhir/CodeSystem/namaste", methods=["GET"])
        def get_namaste_codesystem():
            return self._get_namaste_codesystem()
        
        # ConceptMap endpoints
        @self.app.route("/fhir/ConceptMap/namaste-icd11", methods=["GET"])
        def get_conceptmap():
            return self._get_conceptmap()
        
        # ValueSet endpoints
        @self.app.route("/fhir/ValueSet/<system>", methods=["GET"])
        @self.app.route("/fhir/ValueSet", methods=["GET"])
        def get_valueset(system=None):
            return self._get_valueset(system)
        
        # ValueSet $expand operation
        @self.app.route("/fhir/ValueSet/$expand", methods=["GET", "POST"])
        def expand_valueset():
            return self._expand_valueset()
        
        # ConceptMap $translate operation
        @self.app.route("/fhir/ConceptMap/$translate", methods=["GET", "POST"])
        def translate_concept():
            return self._translate_concept()
        
        # Auto-complete lookup endpoint
        @self.app.route("/fhir/ValueSet/$lookup", methods=["GET", "POST"])
        def lookup_concept():
            return self._lookup_concept()
        
        # Bundle upload for encounters
        @self.app.route("/fhir/Bundle", methods=["POST"])
        @jwt_required()
        def upload_bundle():
            return self._upload_bundle()
        
        # OAuth 2.0 token endpoint (ABHA integration placeholder)
        @self.app.route("/fhir/oauth/token", methods=["POST"])
        def oauth_token():
            return self._oauth_token()
        
        # Audit log endpoint
        @self.app.route("/fhir/AuditEvent", methods=["GET"])
        @jwt_required()
        def get_audit_events():
            return self._get_audit_events()
    
    def _create_capability_statement(self):
        """Create FHIR CapabilityStatement"""
        capability = {
            "resourceType": "CapabilityStatement",
            "id": "namaste-terminology-service",
            "url": "http://terminology.ayush.gov.in/fhir/CapabilityStatement/namaste-terminology-service",
            "version": "2025.1",
            "name": "NAMASTETerminologyService",
            "title": "NAMASTE Terminology Service",
            "status": "active",
            "experimental": False,
            "date": datetime.now().isoformat(),
            "publisher": "Ministry of AYUSH, Government of India",
            "description": "FHIR R4 terminology service for NAMASTE codes with ICD-11 integration",
            "jurisdiction": [{
                "coding": [{
                    "system": "urn:iso:std:iso:3166",
                    "code": "IN",
                    "display": "India"
                }]
            }],
            "kind": "instance",
            "software": {
                "name": "InsightNexus FHIR Terminology Service",
                "version": "1.0.0"
            },
            "implementation": {
                "description": "NAMASTE-ICD11 FHIR Terminology Service",
                "url": "http://terminology.ayush.gov.in/fhir"
            },
            "fhirVersion": "4.0.1",
            "format": ["json", "xml"],
            "rest": [{
                "mode": "server",
                "security": {
                    "cors": True,
                    "service": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/restful-security-service",
                            "code": "OAuth",
                            "display": "OAuth2 using SMART-on-FHIR profile"
                        }]
                    }],
                    "description": "OAuth 2.0 with ABHA integration"
                },
                "resource": [
                    {
                        "type": "CodeSystem",
                        "interaction": [{"code": "read"}, {"code": "search-type"}],
                        "searchParam": [
                            {"name": "url", "type": "uri"},
                            {"name": "version", "type": "token"},
                            {"name": "name", "type": "string"}
                        ]
                    },
                    {
                        "type": "ConceptMap", 
                        "interaction": [{"code": "read"}, {"code": "search-type"}],
                        "operation": [{"name": "translate"}]
                    },
                    {
                        "type": "ValueSet",
                        "interaction": [{"code": "read"}, {"code": "search-type"}],
                        "operation": [{"name": "expand"}, {"name": "lookup"}]
                    },
                    {
                        "type": "Bundle",
                        "interaction": [{"code": "create"}]
                    }
                ]
            }]
        }
        
        self._log_audit_event("read", "CapabilityStatement", "metadata")
        return jsonify(capability)
    
    def _get_namaste_codesystem(self):
        """Get NAMASTE CodeSystem resource"""
        try:
            codesystem = self.fhir_manager.create_namaste_codesystem(self.data_manager.traditional_data)
            self._log_audit_event("read", "CodeSystem", "namaste")
            return jsonify(codesystem.dict())
        except Exception as e:
            logger.error(f"Error creating CodeSystem: {e}")
            return self._create_operation_outcome("error", f"Failed to create CodeSystem: {str(e)}"), 500
    
    def _get_conceptmap(self):
        """Get NAMASTE to ICD-11 ConceptMap"""
        try:
            # Generate sample mappings (in production, this would come from a mapping database)
            mappings = self._generate_sample_mappings()
            conceptmap = self.fhir_manager.create_conceptmap(mappings)
            self._log_audit_event("read", "ConceptMap", "namaste-icd11")
            return jsonify(conceptmap.dict())
        except Exception as e:
            logger.error(f"Error creating ConceptMap: {e}")
            return self._create_operation_outcome("error", f"Failed to create ConceptMap: {str(e)}"), 500
    
    def _get_valueset(self, system=None):
        """Get ValueSet resource"""
        try:
            valueset = self.fhir_manager.create_valueset(system)
            self._log_audit_event("read", "ValueSet", system or "all")
            return jsonify(valueset.dict())
        except Exception as e:
            logger.error(f"Error creating ValueSet: {e}")
            return self._create_operation_outcome("error", f"Failed to create ValueSet: {str(e)}"), 500
    
    def _expand_valueset(self):
        """ValueSet $expand operation for auto-complete"""
        try:
            # Get parameters
            filter_text = request.args.get('filter', '')
            count = int(request.args.get('count', 20))
            system = request.args.get('system')
            
            # Search NAMASTE codes
            results = []
            for sys, df in self.data_manager.traditional_data.items():
                if system and sys.lower() != system.lower():
                    continue
                    
                for _, row in df.iterrows():
                    term = str(row["name"]).lower()
                    if not filter_text or filter_text.lower() in term:
                        results.append({
                            "system": self.fhir_manager.namaste_codesystem_url,
                            "code": str(row["code"]),
                            "display": str(row["name"])
                        })
                        
                        if len(results) >= count:
                            break
                
                if len(results) >= count:
                    break
            
            expansion = {
                "resourceType": "ValueSet",
                "id": "expanded-namaste-valueset",
                "expansion": {
                    "identifier": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "total": len(results),
                    "parameter": [
                        {"name": "filter", "valueString": filter_text},
                        {"name": "count", "valueInteger": count}
                    ],
                    "contains": results
                }
            }
            
            self._log_audit_event("operation", "ValueSet", "$expand")
            return jsonify(expansion)
            
        except Exception as e:
            logger.error(f"Error in ValueSet $expand: {e}")
            return self._create_operation_outcome("error", f"Failed to expand ValueSet: {str(e)}"), 500
    
    def _translate_concept(self):
        """ConceptMap $translate operation"""
        try:
            # Get parameters
            code = request.args.get('code') or request.json.get('code') if request.json else None
            system = request.args.get('system') or request.json.get('system') if request.json else None
            target_system = request.args.get('targetsystem') or request.json.get('targetsystem') if request.json else None
            
            if not code or not system:
                return self._create_operation_outcome("error", "Missing required parameters: code and system"), 400
            
            # Find NAMASTE term
            namaste_term = None
            for sys, df in self.data_manager.traditional_data.items():
                match = df[df["code"].astype(str) == code]
                if not match.empty:
                    namaste_term = {
                        "system": sys,
                        "code": code,
                        "display": str(match.iloc[0]["name"])
                    }
                    break
            
            if not namaste_term:
                return self._create_operation_outcome("error", f"Code {code} not found in system {system}"), 404
            
            # Search ICD-11 mappings
            icd_results = []
            try:
                # Search TM2
                tm2_results = self.icd_manager.search_icd(namaste_term["display"], max_results=3, linearization="tm2")
                for result in tm2_results:
                    icd_results.append({
                        "system": self.fhir_manager.icd11_tm2_url,
                        "code": result["code"],
                        "display": result["title"],
                        "equivalence": "equivalent"
                    })
                
                # Search MMS if no TM2 results or if targeting biomedicine
                if not tm2_results or target_system == self.fhir_manager.icd11_mms_url:
                    mms_results = self.icd_manager.search_icd(namaste_term["display"], max_results=2, linearization="mms")
                    for result in mms_results:
                        icd_results.append({
                            "system": self.fhir_manager.icd11_mms_url,
                            "code": result["code"],
                            "display": result["title"],
                            "equivalence": "wider"
                        })
            
            except Exception as e:
                logger.warning(f"ICD-11 search failed: {e}")
            
            # Create Parameters response
            parameters = {
                "resourceType": "Parameters",
                "parameter": [
                    {
                        "name": "result",
                        "valueBoolean": len(icd_results) > 0
                    },
                    {
                        "name": "message",
                        "valueString": f"Found {len(icd_results)} mappings for {namaste_term['display']}"
                    }
                ]
            }
            
            # Add matches
            for result in icd_results:
                parameters["parameter"].append({
                    "name": "match",
                    "part": [
                        {"name": "equivalence", "valueCode": result["equivalence"]},
                        {"name": "concept", "valueCoding": {
                            "system": result["system"],
                            "code": result["code"],
                            "display": result["display"]
                        }}
                    ]
                })
            
            self._log_audit_event("operation", "ConceptMap", "$translate")
            return jsonify(parameters)
            
        except Exception as e:
            logger.error(f"Error in ConceptMap $translate: {e}")
            return self._create_operation_outcome("error", f"Translation failed: {str(e)}"), 500
    
    def _lookup_concept(self):
        """ValueSet $lookup operation for concept details"""
        try:
            code = request.args.get('code')
            system = request.args.get('system')
            
            if not code:
                return self._create_operation_outcome("error", "Missing required parameter: code"), 400
            
            # Find concept in NAMASTE data
            for sys, df in self.data_manager.traditional_data.items():
                match = df[df["code"].astype(str) == code]
                if not match.empty:
                    row = match.iloc[0]
                    
                    parameters = {
                        "resourceType": "Parameters",
                        "parameter": [
                            {"name": "name", "valueString": "NAMASTE"},
                            {"name": "version", "valueString": "2025.1"},
                            {"name": "display", "valueString": str(row["name"])},
                            {"name": "system", "valueString": sys},
                            {"name": "code", "valueString": str(row["code"])}
                        ]
                    }
                    
                    self._log_audit_event("operation", "ValueSet", "$lookup")
                    return jsonify(parameters)
            
            return self._create_operation_outcome("error", f"Code {code} not found"), 404
            
        except Exception as e:
            logger.error(f"Error in ValueSet $lookup: {e}")
            return self._create_operation_outcome("error", f"Lookup failed: {str(e)}"), 500
    
    def _upload_bundle(self):
        """Upload FHIR Bundle with encounters"""
        try:
            bundle_data = request.json
            
            if not bundle_data or bundle_data.get("resourceType") != "Bundle":
                return self._create_operation_outcome("error", "Invalid Bundle resource"), 400
            
            # Process bundle entries
            processed_entries = []
            for entry in bundle_data.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Condition":
                    # Validate dual coding
                    codings = resource.get("code", {}).get("coding", [])
                    has_namaste = any(c.get("system") == self.fhir_manager.namaste_codesystem_url for c in codings)
                    has_icd11 = any(c.get("system") in [self.fhir_manager.icd11_tm2_url, self.fhir_manager.icd11_mms_url] for c in codings)
                    
                    if has_namaste and has_icd11:
                        processed_entries.append({
                            "id": str(uuid.uuid4()),
                            "resource": resource,
                            "status": "created"
                        })
                    else:
                        processed_entries.append({
                            "id": entry.get("resource", {}).get("id", str(uuid.uuid4())),
                            "status": "error",
                            "error": "Missing dual coding (NAMASTE + ICD-11)"
                        })
            
            # Create response Bundle
            response_bundle = {
                "resourceType": "Bundle",
                "id": str(uuid.uuid4()),
                "type": "transaction-response",
                "timestamp": datetime.now().isoformat(),
                "entry": [
                    {
                        "response": {
                            "status": "201 Created" if entry["status"] == "created" else "400 Bad Request",
                            "location": f"Condition/{entry['id']}" if entry["status"] == "created" else None,
                            "outcome": self._create_operation_outcome("information" if entry["status"] == "created" else "error", 
                                                                   "Resource created successfully" if entry["status"] == "created" else entry.get("error", "Unknown error"))
                        }
                    } for entry in processed_entries
                ]
            }
            
            self._log_audit_event("create", "Bundle", f"Processed {len(processed_entries)} entries")
            return jsonify(response_bundle), 201
            
        except Exception as e:
            logger.error(f"Error uploading Bundle: {e}")
            return self._create_operation_outcome("error", f"Bundle upload failed: {str(e)}"), 500
    
    def _oauth_token(self):
        """OAuth 2.0 token endpoint (ABHA integration placeholder)"""
        try:
            grant_type = request.form.get('grant_type')
            client_id = request.form.get('client_id')
            client_secret = request.form.get('client_secret')
            
            # In production, validate against ABHA system
            if grant_type == "client_credentials" and client_id and client_secret:
                # Create JWT token
                access_token = create_access_token(
                    identity=client_id,
                    additional_claims={
                        "scope": "system/CodeSystem.read system/ConceptMap.read system/ValueSet.read system/Bundle.write",
                        "client_id": client_id
                    }
                )
                
                response = {
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": 86400,  # 24 hours
                    "scope": "system/CodeSystem.read system/ConceptMap.read system/ValueSet.read system/Bundle.write"
                }
                
                self._log_audit_event("auth", "OAuth", f"Token issued for {client_id}")
                return jsonify(response)
            
            return jsonify({"error": "invalid_client"}), 401
            
        except Exception as e:
            logger.error(f"OAuth error: {e}")
            return jsonify({"error": "server_error"}), 500
    
    def _get_audit_events(self):
        """Get audit events (ISO 22600 compliance)"""
        try:
            # Return recent audit events
            recent_events = self.audit_log[-100:]  # Last 100 events
            
            bundle = {
                "resourceType": "Bundle",
                "id": str(uuid.uuid4()),
                "type": "searchset",
                "total": len(recent_events),
                "entry": [
                    {
                        "resource": {
                            "resourceType": "AuditEvent",
                            "id": str(uuid.uuid4()),
                            "type": {
                                "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
                                "code": event["action"]
                            },
                            "recorded": event["timestamp"],
                            "agent": [{
                                "who": {"display": event.get("user", "system")},
                                "requestor": True
                            }],
                            "source": {
                                "site": "NAMASTE Terminology Service",
                                "identifier": {"value": "namaste-terminology-service"}
                            },
                            "entity": [{
                                "what": {"display": f"{event['resource_type']}/{event['resource_id']}"}
                            }]
                        }
                    } for event in recent_events
                ]
            }
            
            return jsonify(bundle)
            
        except Exception as e:
            logger.error(f"Error getting audit events: {e}")
            return self._create_operation_outcome("error", f"Failed to retrieve audit events: {str(e)}"), 500
    
    def _generate_sample_mappings(self):
        """Generate sample mappings for demonstration"""
        mappings = []
        
        # Sample mappings (in production, these would come from a curated mapping database)
        sample_mappings = [
            {
                "namaste_code": "AY001", "namaste_display": "Jwara (ज्वर)",
                "tm2_code": "TM2.A01", "tm2_display": "Fever pattern in Ayurveda",
                "mms_code": "MG26", "mms_display": "Fever, unspecified",
                "source_system": "Ayurveda"
            },
            {
                "namaste_code": "SI001", "namaste_display": "Suram",
                "tm2_code": "TM2.S01", "tm2_display": "Fever pattern in Siddha",
                "mms_code": "MG26", "mms_display": "Fever, unspecified", 
                "source_system": "Siddha"
            }
        ]
        
        return sample_mappings
    
    def _create_operation_outcome(self, severity: str, message: str):
        """Create FHIR OperationOutcome"""
        outcome = {
            "resourceType": "OperationOutcome",
            "id": str(uuid.uuid4()),
            "issue": [{
                "severity": severity,
                "code": "processing",
                "diagnostics": message
            }]
        }
        return outcome
    
    def _log_audit_event(self, action: str, resource_type: str, resource_id: str, user: str = None):
        """Log audit event for ISO 22600 compliance"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user": user or get_jwt_identity() if hasattr(g, 'jwt_identity') else "anonymous",
            "ip_address": request.remote_addr if request else None
        }
        
        self.audit_log.append(event)
        logger.info(f"Audit: {action} {resource_type}/{resource_id} by {event['user']}")
