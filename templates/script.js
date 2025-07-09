document.getElementById("riskForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const data = {
        name: form.name.value,
        description: form.description.value,
        has_public_ip: form.has_public_ip.checked,
        has_sensitive_data: form.has_sensitive_data.checked
    };

    const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    const result = await res.json();
    document.getElementById("result").textContent = JSON.stringify(result, null, 2);
});
