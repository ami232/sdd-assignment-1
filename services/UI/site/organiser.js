// Organiser dashboard: list every trip and create new ones.

async function showTrips() {
    const trips = await api(`${TRIPS}/trips`);
    const list = document.getElementById("trips");

    if (trips.length === 0) {
        list.innerHTML = `<div class="empty">No trips yet. Create the first one below.</div>`;
        return;
    }

    list.innerHTML = trips.map((trip) => `
        <a class="trip-card" href="trip.html?id=${trip.id}">
            <h3>${escapeHtml(trip.name)}</h3>
            <p class="muted">${escapeHtml(trip.destination)}</p>
            <p class="dates">${formatDates(trip.start_date, trip.end_date)}</p>
            <div class="bar"><div style="width: ${trip.stats.occupancy_percent}%"></div></div>
            <p class="muted">
                ${trip.stats.places_remaining} of ${trip.capacity} places free ·
                ${trip.stats.waitlisted} waiting
            </p>
        </a>
    `).join("");
}

onSubmit(document.getElementById("create-trip"), async (values) => {
    await api(`${TRIPS}/trips`, { ...values, capacity: Number(values.capacity) });
    await showTrips();
    return `${values.name} created.`;
});

showTrips().catch((error) => showMessage(error.message, "error"));
