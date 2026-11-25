// One trip, for organisers. Registrations come from Trip Management and
// rooms from Room Allocation; this page is the only place the two meet.

const tripId = Number(new URLSearchParams(location.search).get("id"));

async function showTrip() {
    const [trip, registrations, rooms, assignments, preferences] = await Promise.all([
        api(`${TRIPS}/trips/${tripId}`),
        api(`${TRIPS}/trips/${tripId}/registrations`),
        api(`${ROOMS}/trips/${tripId}/rooms`),
        api(`${ROOMS}/trips/${tripId}/assignments`),
        api(`${ROOMS}/trips/${tripId}/preferences`),
    ]);

    // Look up names and rooms by registration ID.
    const names = Object.fromEntries(registrations.map((r) => [r.id, r.name]));
    const roomOf = Object.fromEntries(assignments.map((a) => [a.registration_id, a.room_name]));
    const confirmed = registrations.filter((r) => r.status === "confirmed");
    const withoutRoom = confirmed.filter((r) => !roomOf[r.id]);

    document.title = `${trip.name} · Ski Club`;
    document.getElementById("trip-name").textContent = trip.name;
    document.getElementById("trip-where").textContent =
        `${trip.destination} · ${formatDates(trip.start_date, trip.end_date)}`;

    showStats(trip.stats, confirmed.length - withoutRoom.length, withoutRoom.length);
    showRegistrations(registrations, roomOf);
    showRooms(rooms, withoutRoom);
    showPreferences(confirmed, preferences, names);
}

function showStats(stats, roomed, needRoom) {
    const stat = (label, value, extra = "") =>
        `<div class="stat ${extra}"><span>${label}</span><strong>${value}</strong></div>`;

    document.getElementById("stats").innerHTML =
        stat("Places free", stats.places_remaining, "highlight") +
        stat("Paid", stats.confirmed) +
        stat("Waiting to pay", stats.pending_payment) +
        stat("Waiting list", stats.waitlisted) +
        stat("Have a room", roomed) +
        stat("Need a room", needRoom);
}

function showRegistrations(registrations, roomOf) {
    document.getElementById("registration-count").textContent =
        plural(registrations.length, "registration");

    if (registrations.length === 0) {
        document.getElementById("registrations").innerHTML =
            `<tr><td colspan="6" class="muted">No one has registered yet.</td></tr>`;
        return;
    }

    document.getElementById("registrations").innerHTML = registrations.map((r) => `
        <tr>
            <td class="muted">#${r.id}</td>
            <td><strong>${escapeHtml(r.name)}</strong></td>
            <td>${escapeHtml(r.email)}</td>
            <td><span class="pill ${r.status}">${statusLabel(r.status)}</span></td>
            <td>${escapeHtml(roomOf[r.id] || "—")}</td>
            <td class="actions"><div>
                ${r.status === "pending_payment"
                    ? `<button class="small" onclick="act('payment', ${r.id}, 'Payment confirmed.')">Paid</button>` : ""}
                ${r.status !== "cancelled"
                    ? `<button class="small danger" onclick="act('cancel', ${r.id}, 'Registration cancelled.')">Cancel</button>` : ""}
            </div></td>
        </tr>
    `).join("");
}

function showRooms(rooms, withoutRoom) {
    document.getElementById("need-room").textContent =
        `${plural(withoutRoom.length, "paid student")} still without a room`;

    document.getElementById("rooms").innerHTML = rooms.length === 0
        ? `<div class="empty">No rooms yet. Add the first one below.</div>`
        : rooms.map((room) => `
            <div class="panel">
                <div class="section-heading">
                    <h3>${escapeHtml(room.name)}</h3>
                    <span class="pill confirmed">${room.occupied}/${room.capacity} beds</span>
                </div>
                <div class="bar"><div style="width: ${room.occupied / room.capacity * 100}%"></div></div>
            </div>
        `).join("");

    fillSelect(document.getElementById("unassigned"), withoutRoom, "Choose a student");
    fillSelect(
        document.getElementById("free-rooms"),
        rooms.filter((room) => room.occupied < room.capacity)
             .map((room) => ({ id: room.id, name: `${room.name} (${room.capacity - room.occupied} free)` })),
        "Choose a room",
    );
}

function showPreferences(confirmed, preferences, names) {
    for (const select of document.querySelectorAll(".confirmed-students")) {
        fillSelect(select, confirmed, "Choose a student");
    }

    document.getElementById("preferences").innerHTML = preferences.map((p) => `
        <p><strong>${escapeHtml(names[p.registration_id])}</strong> would like to share with
           <strong>${escapeHtml(names[p.preferred_registration_id])}</strong></p>
    `).join("");
}

function fillSelect(select, items, placeholder) {
    select.innerHTML = `<option value="">${placeholder}</option>` + items.map(
        (item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`
    ).join("");
}

// The Paid and Cancel buttons in the table.
async function act(action, registrationId, success) {
    try {
        await api(`${TRIPS}/registrations/${registrationId}/${action}`, {});
        await showTrip();
        showMessage(success, "success");
    } catch (error) {
        showMessage(error.message, "error");
    }
}

onSubmit(document.getElementById("register"), async (values) => {
    const { id } = await api(`${TRIPS}/trips/${tripId}/registrations`, values);
    await showTrip();
    return `${values.name} is registered with number #${id}.`;
});

onSubmit(document.getElementById("create-room"), async (values) => {
    await api(`${ROOMS}/trips/${tripId}/rooms`, { ...values, capacity: Number(values.capacity) });
    await showTrip();
    return `${values.name} added.`;
});

onSubmit(document.getElementById("assign"), async (values) => {
    await api(`${ROOMS}/rooms/${values.room_id}/assignments`,
              { registration_id: Number(values.registration_id) });
    await showTrip();
    return "Student assigned to the room.";
});

onSubmit(document.getElementById("preference"), async (values) => {
    await api(`${ROOMS}/preferences`, {
        registration_id: Number(values.registration_id),
        preferred_registration_id: Number(values.preferred_registration_id),
    });
    await showTrip();
    return "Roommate request saved.";
});

showTrip().catch((error) => showMessage(error.message, "error"));
