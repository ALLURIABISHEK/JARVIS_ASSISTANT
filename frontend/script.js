async function send() {
  const query = document.getElementById("query").value;
  const res = await fetch("http://127.0.0.1:5000/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query })
  });
  const data = await res.json();
  document.getElementById("chatbox").innerHTML += `<p><b>You:</b> ${query}</p>`;
  document.getElementById("chatbox").innerHTML += `<p><b>Jarvis:</b> ${data.response}</p>`;
}
