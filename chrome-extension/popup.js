document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://localhost:5000/api';
    const responseDiv = document.getElementById('response');
    const loadingDiv = document.getElementById('loading');
    const mathInput = document.getElementById('mathExpression');

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