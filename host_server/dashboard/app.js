async function fetchStudents() {
    const response = await fetch("/students");
    const students = await response.json();

    let total = 0, active = 0, passive = 0, distracted = 0;
    const table = document.getElementById("studentTable");
    table.innerHTML = "";

    for (const id in students) {
        total++;
        const fatigue = students[id].fatigue;

        let status = "Active";
        if (fatigue >= 70) {
            status = "Distracted";
            distracted++;
        } else if (fatigue >= 40) {
            status = "Passive";
            passive++;
        } else {
            active++;
        }

        table.innerHTML += `
            <tr>
                <td>${id}</td>
                <td>${students[id].ear}</td>
                <td>${fatigue}</td>
                <td>${status}</td>
            </tr>
        `;
    }

    document.getElementById("total").innerText = total;
    document.getElementById("active").innerText = active;
    document.getElementById("passive").innerText = passive;
    document.getElementById("distracted").innerText = distracted;
}

setInterval(fetchStudents, 2000);
