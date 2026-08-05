"""
FHIR R4 Models and Resources for NAMASTE-ICD11 Integration
Compliant with India's 2016 EHR Standards
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from fhir.resources.codesystem import CodeSystem, CodeSystemConcept, CodeSystemProperty
from fhir.resources.conceptmap import ConceptMap, ConceptMapGroup, ConceptMapGroupElement, ConceptMapGroupElementTarget
from fhir.resources.valueset import ValueSet, ValueSetCompose, ValueSetComposeInclude
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.condition import Condition
from fhir.resources.coding import Coding
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.reference import Reference
from fhir.resources.meta import Meta
import uuid
import logging

logger = logging.getLogger(__name__)

class FHIRNAMASTEManager:
    """Manages FHIR R4 compliant NAMASTE CodeSystem and ConceptMap resources"""
    
    def __init__(self):
        self.namaste_codesystem_url = "http://terminology.ayush.gov.in/CodeSystem/namaste"
        self.icd11_tm2_url = "http://id.who.int/icd/release/11/2025-01/tm2"
        self.icd11_mms_url = "http://id.who.int/icd/release/11/2025-01/mms"
        self.conceptmap_url = "http://terminology.ayush.gov.in/ConceptMap/namaste-to-icd11"
        
    def create_namaste_codesystem(self, traditional_data: Dict) -> CodeSystem:
        """Create FHIR CodeSystem for NAMASTE codes"""
        
        concepts = []
        
        for system, df in traditional_data.items():
            for _, row in df.iterrows():
                # Clean code to ensure FHIR compliance (no spaces, valid format)
                clean_code = str(row["code"]).strip().replace(" ", "_")
                if not clean_code:
                    continue
                    
                concept = CodeSystemConcept(
                    code=clean_code,
                    display=str(row["name"]),
                    definition=f"{system} terminology from NAMASTE classification",
                    property=[
                        {
                            "code": "system",
                            "valueString": system
                        },
                        {
                            "code": "source",
                            "valueString": "NAMASTE"
                        }
                    ]
                )
                concepts.append(concept)
        
        codesystem = CodeSystem(
            id="namaste-codesystem",
            url=self.namaste_codesystem_url,
            identifier=[{
                "system": "http://terminology.ayush.gov.in",
                "value": "NAMASTE-CS-2025"
            }],
            version="2025.1",
            name="NAMASTECodeSystem",
            title="National AYUSH Morbidity & Standardized Terminologies Electronic (NAMASTE)",
            status="active",
            experimental=False,
            date=datetime.now().isoformat(),
            publisher="Ministry of AYUSH, Government of India",
            description="Standardized terminologies for Ayurveda, Siddha and Unani disorders as per NAMASTE classification",
            jurisdiction=[{
                "coding": [{
                    "system": "urn:iso:std:iso:3166",
                    "code": "IN",
                    "display": "India"
                }]
            }],
            caseSensitive=True,
            content="complete",
            count=len(concepts),
            concept=concepts,
            property=[
                {
                    "code": "system",
                    "type": "string",
                    "description": "Traditional medicine system (Ayurveda/Siddha/Unani)"
                },
                {
                    "code": "source", 
                    "type": "string",
                    "description": "Source terminology system"
                }
            ]
        )
        
        return codesystem
    
    def create_conceptmap(self, mappings: List[Dict]) -> ConceptMap:
        """Create FHIR ConceptMap for NAMASTE to ICD-11 mappings"""
        
        # Group mappings by source system
        groups = {}
        
        for mapping in mappings:
            source_system = mapping.get("source_system", "unknown")
            if source_system not in groups:
                groups[source_system] = []
            groups[source_system].append(mapping)
        
        concept_map_groups = []
        
        for system, system_mappings in groups.items():
            elements = []
            
            for mapping in system_mappings:
                targets = []
                
                # Add TM2 mapping if available
                if mapping.get("tm2_code"):
                    targets.append(ConceptMapGroupElementTarget(
                        code=mapping["tm2_code"],
                        display=mapping.get("tm2_display", ""),
                        equivalence="equivalent"
                    ))
                
                # Add MMS mapping if available  
                if mapping.get("mms_code"):
                    targets.append(ConceptMapGroupElementTarget(
                        code=mapping["mms_code"],
                        display=mapping.get("mms_display", ""),
                        equivalence="wider"
                    ))
                
                if targets:
                    element = ConceptMapGroupElement(
                        code=mapping["namaste_code"],
                        display=mapping["namaste_display"],
                        target=targets
                    )
                    elements.append(element)
            
            if elements:
                group = ConceptMapGroup(
                    source=self.namaste_codesystem_url,
                    target=self.icd11_tm2_url,
                    element=elements
                )
                concept_map_groups.append(group)
        
        conceptmap = ConceptMap(
            id="namaste-icd11-conceptmap",
            url=self.conceptmap_url,
            identifier=[{
                "system": "http://terminology.ayush.gov.in",
                "value": "NAMASTE-ICD11-CM-2025"
            }],
            version="2025.1",
            name="NAMASTEToICD11ConceptMap",
            title="NAMASTE to ICD-11 (TM2 & Biomedicine) Concept Map",
            status="active",
            experimental=False,
            date=datetime.now().isoformat(),
            publisher="Ministry of AYUSH, Government of India",
            description="Mapping between NAMASTE codes and WHO ICD-11 Traditional Medicine Module 2 and Biomedicine codes",
            jurisdiction=[{
                "coding": [{
                    "system": "urn:iso:std:iso:3166", 
                    "code": "IN",
                    "display": "India"
                }]
            }],
            sourceUri=self.namaste_codesystem_url,
            targetUri=self.icd11_tm2_url,
            group=concept_map_groups
        )
        
        return conceptmap
    
    def create_valueset(self, system: str = None) -> ValueSet:
        """Create FHIR ValueSet for NAMASTE codes"""
        
        includes = []
        
        if system:
            # System-specific ValueSet
            include = ValueSetComposeInclude(
                system=self.namaste_codesystem_url,
                filter=[{
                    "property": "system",
                    "op": "=",
                    "value": system
                }]
            )
            includes.append(include)
            vs_id = f"namaste-{system.lower()}-valueset"
            vs_name = f"NAMASTE{system}ValueSet"
            vs_title = f"NAMASTE {system} Terminology Value Set"
        else:
            # Complete ValueSet
            include = ValueSetComposeInclude(
                system=self.namaste_codesystem_url
            )
            includes.append(include)
            vs_id = "namaste-complete-valueset"
            vs_name = "NAMASTECompleteValueSet"
            vs_title = "Complete NAMASTE Terminology Value Set"
        
        valueset = ValueSet(
            id=vs_id,
            url=f"http://terminology.ayush.gov.in/ValueSet/{vs_id}",
            identifier=[{
                "system": "http://terminology.ayush.gov.in",
                "value": f"NAMASTE-VS-{system or 'ALL'}-2025"
            }],
            version="2025.1",
            name=vs_name,
            title=vs_title,
            status="active",
            experimental=False,
            date=datetime.now().isoformat(),
            publisher="Ministry of AYUSH, Government of India",
            description=f"Value set containing {system + ' ' if system else ''}NAMASTE terminology codes",
            jurisdiction=[{
                "coding": [{
                    "system": "urn:iso:std:iso:3166",
                    "code": "IN", 
                    "display": "India"
                }]
            }],
            compose=ValueSetCompose(include=includes)
        )
        
        return valueset
    
    def create_condition_resource(self, namaste_code: str, namaste_display: str, 
                                icd11_mappings: List[Dict], patient_ref: str) -> Condition:
        """Create FHIR Condition resource with dual coding"""
        
        codings = [
            Coding(
                system=self.namaste_codesystem_url,
                code=namaste_code,
                display=namaste_display
            )
        ]
        
        # Add ICD-11 mappings
        for mapping in icd11_mappings:
            if mapping.get("system") == "tm2":
                codings.append(Coding(
                    system=self.icd11_tm2_url,
                    code=mapping["code"],
                    display=mapping.get("display", "")
                ))
            elif mapping.get("system") == "mms":
                codings.append(Coding(
                    system=self.icd11_mms_url,
                    code=mapping["code"],
                    display=mapping.get("display", "")
                ))
        
        condition = Condition(
            id=str(uuid.uuid4()),
            meta=Meta(
                versionId="1",
                lastUpdated=datetime.now().isoformat(),
                profile=["http://hl7.org/fhir/StructureDefinition/Condition"]
            ),
            clinicalStatus=CodeableConcept(
                coding=[Coding(
                    system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                    code="active"
                )]
            ),
            verificationStatus=CodeableConcept(
                coding=[Coding(
                    system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    code="confirmed"
                )]
            ),
            code=CodeableConcept(coding=codings),
            subject=Reference(reference=f"Patient/{patient_ref}"),
            recordedDate=datetime.now().isoformat()
        )
        
        return condition
    
    def create_fhir_bundle(self, conditions: List[Condition]) -> Bundle:
        """Create FHIR Bundle with Condition resources"""
        
        entries = []
        for condition in conditions:
            entry = BundleEntry(
                resource=condition,
                request={
                    "method": "POST",
                    "url": "Condition"
                }
            )
            entries.append(entry)
        
        bundle = Bundle(
            id=str(uuid.uuid4()),
            type="transaction",
            timestamp=datetime.now().isoformat(),
            entry=entries
        )
        
        return bundle
