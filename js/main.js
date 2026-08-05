document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing simple search functionality...');

    // Get elements
    const searchInput = document.getElementById('disease-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results');
    const loadingIndicator = document.getElementById('loading');
    const btnText = searchBtn ? searchBtn.querySelector('.btn-text') : null;
    const btnLoading = searchBtn ? searchBtn.querySelector('.btn-loading') : null;

    console.log('Elements found:', {
        searchInput: !!searchInput,
        searchBtn: !!searchBtn,
        resultsContainer: !!resultsContainer,
        loadingIndicator: !!loadingIndicator,
        btnText: !!btnText,
        btnLoading: !!btnLoading
    });

    // Simple predefined responses for demonstration
    const mockResponses = {
        'diabetes': {
            traditional: {
                system: 'Ayurveda',
                name: 'Madhumeha (मधुमेह)',
                code: '5A11',
                score: 1.0
            },
            icd11: {
                results: [{
                    code: '5A11',
                    title: 'Type 2 Diabetes Mellitus',
                    definition: 'A metabolic disorder characterized by high blood sugar levels'
                }],
                count: 1
            }
        },
        'madhumeha': {
            traditional: {
                system: 'Ayurveda',
                name: 'Madhumeha (मधुमेह)',
                code: '5A11',
                score: 1.0
            },
            icd11: {
                results: [{
                    code: '5A11',
                    title: 'Type 2 Diabetes Mellitus',
                    definition: 'A metabolic disorder characterized by high blood sugar levels'
                }],
                count: 1
            }
        },
        'fever': {
            traditional: {
                system: 'Ayurveda',
                name: 'Jwara (ज्वर)',
                code: 'MG26',
                score: 1.0
            },
            icd11: {
                results: [{
                    code: 'A90',
                    title: 'Fever',
                    definition: 'Elevated body temperature'
                }],
                count: 1
            }
        },
        'jwara': {
            traditional: {
                system: 'Ayurveda',
                name: 'Jwara (ज्वर)',
                code: 'MG26',
                score: 1.0
            },
            icd11: {
                results: [{
                    code: 'A90',
                    title: 'Fever',
                    definition: 'Elevated body temperature'
                }],
                count: 1
            }
        },
        'malaria': {
            traditional: {
                system: 'Ayurveda',
                name: 'Vishama Jwara (विषम ज्वर)',
                code: '1F40',
                score: 1.0
            },
            icd11: {
                results: [{
                    code: '1F40',
                    title: 'Malaria',
                    definition: 'Parasitic infection transmitted by mosquitoes'
                }],
                count: 1
            }
        }
    };

    function searchDisease(query) {
        console.log('Searching for:', query);

        if (!query || query.trim() === '') {
            alert('Please enter a disease name');
            return;
        }

        // Show loading state
        if (searchBtn) searchBtn.disabled = true;
        if (btnText) btnText.style.display = 'none';
        if (btnLoading) btnLoading.style.display = 'inline';
        if (loadingIndicator) loadingIndicator.style.display = 'block';

        // Simulate API delay
        setTimeout(() => {
            const normalizedQuery = query.toLowerCase().trim();
            console.log('Normalized query:', normalizedQuery);
            
            const response = mockResponses[normalizedQuery];
            console.log('Found response:', response);

            if (response) {
                displayResults(query, response);
            } else {
                // Show fallback result
                displayResults(query, {
                    traditional: {
                        system: 'Simulation',
                        name: `Simulated result for "${query}"`,
                        code: 'SIM001',
                        score: 0.8
                    },
                    icd11: {
                        results: [{
                            code: 'Z99',
                            title: `Disease related to ${query}`,
                            definition: `Simulated ICD-11 result for ${query}`
                        }],
                        count: 1
                    }
                });
            }

            // Reset button state
            if (searchBtn) searchBtn.disabled = false;
            if (btnText) btnText.style.display = 'inline';
            if (btnLoading) btnLoading.style.display = 'none';
            if (loadingIndicator) loadingIndicator.style.display = 'none';
        }, 1500); // 1.5 second delay for realism
    }

    function displayResults(query, data) {
        console.log('Displaying results for:', query, data);

        if (!resultsContainer) {
            console.error('Results container not found!');
            return;
        }

        let html = `<div style="margin-top: 2rem;"><h3>Search Results for "${query}"</h3>`;

        // Traditional medicine result
        if (data.traditional) {
            const traditional = data.traditional;
            html += `
                <div class="result-card" style="margin: 1rem 0; padding: 1.5rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 12px; border: 1px solid #0ea5e9; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                    <h4 style="color: #0369a1; margin-bottom: 1rem;">🌿 Traditional Medicine Mapping</h4>
                    <div style="display: grid; gap: 0.5rem; margin-bottom: 1rem;">
                        <p><strong>System:</strong> ${traditional.system}</p>
                        <p><strong>Traditional Term:</strong> ${traditional.name}</p>
                        <p><strong>Code:</strong> <code style="background: #e0f2fe; padding: 2px 6px; border-radius: 4px;">${traditional.code}</code></p>
                        <p><strong>Confidence:</strong> <span style="color: #059669; font-weight: bold;">${((traditional.score || 0) * 100).toFixed(1)}%</span></p>
                    </div>

                    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 1rem;">
                        <button onclick="createCodeSystem('${traditional.code}', '${traditional.name}')" style="padding: 10px 16px; background: linear-gradient(135deg, #059669, #10b981); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: transform 0.2s;">
                            🏥 Create CodeSystem
                        </button>
                        <button onclick="createConceptMap('${traditional.code}', '${traditional.name}')" style="padding: 10px 16px; background: linear-gradient(135deg, #f59e0b, #fbbf24); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: transform 0.2s;">
                            🗺️ Create ConceptMap
                        </button>
                        <button onclick="createBundle('${traditional.code}', '${traditional.name}')" style="padding: 10px 16px; background: linear-gradient(135deg, #3b82f6, #60a5fa); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: transform 0.2s;">
                            📦 Create Bundle
                        </button>
                    </div>
                </div>
            `;
        }

        // ICD-11 results
        if (data.icd11 && data.icd11.results && data.icd11.results.length > 0) {
            html += `
                <div class="result-card" style="margin: 1rem 0; padding: 1.5rem; background: linear-gradient(135deg, #fef3c7 0%, #fed7aa 100%); border-radius: 12px; border: 1px solid #f59e0b; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                    <h4 style="color: #92400e; margin-bottom: 1rem;">🏥 Modern Medicine (ICD-11) Results (${data.icd11.count})</h4>
                    ${data.icd11.results.map((item, index) => `
                        <div style="margin: 0.75rem 0; padding: 1rem; background: white; border-radius: 8px; border-left: 4px solid #f59e0b;">
                            <p style="margin: 0 0 0.5rem 0;"><strong><code style="background: #fef3c7; padding: 2px 6px; border-radius: 4px;">${item.code}</code>:</strong> ${item.title}</p>
                            <p style="margin: 0; color: #6b7280; font-size: 0.9rem;">${item.definition}</p>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // FHIR Resources Display Area
        html += `
            <div id="fhir-display" style="margin-top: 2rem; display: none;">
                <h4 style="color: #374151; margin-bottom: 1rem;">📋 Generated FHIR Resources</h4>
                <div style="border: 2px solid #e5e7eb; border-radius: 8px; padding: 1.5rem; background: #f9fafb;">
                    <div style="margin-bottom: 1rem; display: flex; gap: 10px; flex-wrap: wrap;">
                        <button onclick="showResource('codesystem')" style="padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500;">CodeSystem</button>
                        <button onclick="showResource('conceptmap')" style="padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500;">ConceptMap</button>
                        <button onclick="showResource('bundle')" style="padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500;">Bundle</button>
                    </div>
                    <pre id="resource-content" style="background: white; padding: 1rem; border-radius: 6px; overflow: auto; max-height: 400px; font-size: 12px; border: 1px solid #d1d5db; font-family: 'Courier New', monospace;"></pre>
                </div>
            </div>
        `;

        html += '</div>';

        resultsContainer.innerHTML = html;
        console.log('Results displayed successfully');
    }

    // Global functions for buttons
    window.createCodeSystem = function(code) {
        const fhirDisplay = document.getElementById('fhir-display');
        const resourceContent = document.getElementById('resource-content');

        if (fhirDisplay && resourceContent) {
            fhirDisplay.style.display = 'block';
            resourceContent.textContent = JSON.stringify({
                resourceType: 'CodeSystem',
                id: `namaste-${code.toLowerCase()}`,
                name: `Disease CodeSystem for ${code}`,
                status: 'active',
                content: 'complete',
                concept: [{
                    code: code,
                    display: `Disease code ${code}`,
                    definition: `Traditional medicine code for disease ${code}`
                }]
            }, null, 2);
        }
    };

    window.createConceptMap = function(code) {
        const fhirDisplay = document.getElementById('fhir-display');
        const resourceContent = document.getElementById('resource-content');

        if (fhirDisplay && resourceContent) {
            fhirDisplay.style.display = 'block';
            resourceContent.textContent = JSON.stringify({
                resourceType: 'ConceptMap',
                id: `${code.toLowerCase()}-to-icd11`,
                name: `Concept Map for ${code}`,
                status: 'active',
                group: [{
                    source: `http://example.org/fhir/CodeSystem/namaste-${code.toLowerCase()}`,
                    target: 'http://id.who.int/icd/release/11/mms',
                    element: [{
                        code: code,
                        target: [{
                            code: code,
                            display: `ICD-11 equivalent for ${code}`,
                            equivalence: 'equivalent'
                        }]
                    }]
                }]
            }, null, 2);
        }
    };

    window.createBundle = function(code) {
        const fhirDisplay = document.getElementById('fhir-display');
        const resourceContent = document.getElementById('resource-content');

        if (fhirDisplay && resourceContent) {
            fhirDisplay.style.display = 'block';
            resourceContent.textContent = JSON.stringify({
                resourceType: 'Bundle',
                id: `dual-coding-${Date.now()}`,
                type: 'collection',
                entry: [{
                    resource: {
                        resourceType: 'Condition',
                        code: {
                            coding: [
                                { system: 'http://example.org/fhir/CodeSystem/namaste', code: code },
                                { system: 'http://id.who.int/icd/release/11/mms', code: code }
                            ]
                        }
                    }
                }]
            }, null, 2);
        }
    };

    window.showResource = function(type) {
        const resourceContent = document.getElementById('resource-content');
        if (resourceContent) {
            if (type === 'codesystem') {
                createCodeSystem('DEMO');
            } else if (type === 'conceptmap') {
                createConceptMap('DEMO');
            } else if (type === 'bundle') {
                createBundle('DEMO');
            }
        }
    };

    // Event listeners
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            const query = searchInput.value.trim();
            searchDisease(query);
        });
    }

    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const query = searchInput.value.trim();
                searchDisease(query);
            }
        });
    }

    console.log('Simple search functionality initialized');
});
