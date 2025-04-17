document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://localhost:5000/api';
    const responseDiv = document.getElementById('response');
    const loadingDiv = document.getElementById('loading');
    const mathInput = document.getElementById('mathExpression');
    const evaluateBtn = document.getElementById('evaluate');
    
    // Preferences state
    let preferencesSet = false;

    // Initialize collapsible preferences section
    const collapsible = document.querySelector('.collapsible');
    collapsible.addEventListener('click', function() {
        this.classList.toggle('active');
        const content = this.nextElementSibling;
        content.classList.toggle('active');
    });

    // Save preferences
    document.getElementById('savePreferences').addEventListener('click', async () => {
        const selectedTopics = Array.from(document.querySelectorAll('#topics input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);

        const preferences = {
            detail_level: document.getElementById('detail_level').value,
            notation_style: document.getElementById('notation_style').value,
            topics: selectedTopics,
            decimal_places: parseInt(document.getElementById('decimal_places').value)
        };

        try {
            loadingDiv.style.display = 'block';
            const response = await fetch(`${API_BASE_URL}/preferences`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(preferences),
            });

            const data = await response.json();
            
            if (data.error) {
                responseDiv.textContent = `Error: ${data.error}`;
                responseDiv.className = 'error';
                preferencesSet = false;
            } else {
                responseDiv.textContent = 'Preferences saved successfully!';
                responseDiv.className = 'success';
                preferencesSet = true;
                
                // Close preferences panel
                collapsible.classList.remove('active');
                collapsible.nextElementSibling.classList.remove('active');
                
                // Store preferences in chrome.storage
                chrome.storage.local.set({ 'mathPreferences': preferences });
            }
        } catch (error) {
            responseDiv.textContent = 'Error connecting to Flask API';
            responseDiv.className = 'error';
            preferencesSet = false;
        } finally {
            loadingDiv.style.display = 'none';
        }
    });

    // Load saved preferences if they exist
    chrome.storage.local.get('mathPreferences', (result) => {
        if (result.mathPreferences) {
            const prefs = result.mathPreferences;
            document.getElementById('detail_level').value = prefs.detail_level;
            document.getElementById('notation_style').value = prefs.notation_style;
            document.getElementById('decimal_places').value = prefs.decimal_places;
            
            // Set checkboxes
            document.querySelectorAll('#topics input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = prefs.topics.includes(checkbox.value);
            });

            // Try to restore preferences to server
            document.getElementById('savePreferences').click();
        }
    });

    // Test API connection
    document.getElementById('testApi').addEventListener('click', async () => {
        try {
            loadingDiv.style.display = 'block';
            const response = await fetch(`${API_BASE_URL}/test`);
            const data = await response.json();
            responseDiv.textContent = JSON.stringify(data, null, 2);
            responseDiv.className = 'success';
        } catch (error) {
            responseDiv.textContent = 'Error connecting to Flask API';
            responseDiv.className = 'error';
        } finally {
            loadingDiv.style.display = 'none';
        }
    });

    // Evaluate math expression
    document.getElementById('evaluate').addEventListener('click', async () => {
        if (!preferencesSet) {
            responseDiv.textContent = 'Please set your preferences first';
            responseDiv.className = 'error';
            
            // Open preferences panel
            collapsible.classList.add('active');
            collapsible.nextElementSibling.classList.add('active');
            return;
        }

        const expression = mathInput.value.trim();
        
        if (!expression) {
            responseDiv.textContent = 'Please enter a math expression';
            responseDiv.className = 'error';
            return;
        }

        try {
            loadingDiv.style.display = 'block';
            responseDiv.textContent = 'Evaluating expression...';
            
            const response = await fetch(`${API_BASE_URL}/evaluate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ expression }),
            });

            const data = await response.json();
            
            if (data.error) {
                responseDiv.textContent = `Error: ${data.error}`;
                responseDiv.className = 'error';
            } else {
                responseDiv.textContent = `Result: ${data.result}`;
                responseDiv.className = 'success';
            }
        } catch (error) {
            responseDiv.textContent = 'Error connecting to Flask API';
            responseDiv.className = 'error';
        } finally {
            loadingDiv.style.display = 'none';
        }
    });

    // Handle Enter key in input field
    mathInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            document.getElementById('evaluate').click();
        }
    });
});