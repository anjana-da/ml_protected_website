document.getElementById("threat-detection-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    // Collect form data
    const formData = new FormData(event.target);
    const formObject = Object.fromEntries(formData.entries());

    // Send POST request to Flask backend
    const response = await fetch("/detect-threat", {
        method: "POST",
        body: new URLSearchParams(formObject),
    });

    // Handle response
    const result = await response.json();
    const resultDiv = document.getElementById("result");
    if (result.error) {
        resultDiv.innerHTML = `<p style="color:red;">Error: ${result.error}</p>`;
    } else {
        resultDiv.innerHTML = `<p style="color:green;">${result.result}</p>`;
    }
});