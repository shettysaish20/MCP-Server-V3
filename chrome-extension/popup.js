document.getElementById('testApi').addEventListener('click', async () => {
    const responseDiv = document.getElementById('response');
    try {
        const response = await fetch('http://localhost:5000/api/test');
        const data = await response.json();
        responseDiv.textContent = JSON.stringify(data, null, 2);
        responseDiv.style.color = 'green';
    } catch (error) {
        responseDiv.textContent = 'Error connecting to Flask API';
        responseDiv.style.color = 'red';
    }
});