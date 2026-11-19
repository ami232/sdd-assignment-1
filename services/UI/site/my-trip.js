// A student's own trip: their place, their room, a countdown and a
// packing list. Ticks on the list are kept in this browser only.

const PACKING_LIST = [
    "Ski jacket", "Ski trousers", "Thermal base layers", "Warm socks",
    "Gloves or mittens", "Hat", "Neck warmer", "Goggles", "Sunglasses",
    "Helmet", "Sun cream", "Lip balm", "ID or passport", "Health card",
    "Phone charger", "Swimsuit for the spa", "Reusable water bottle",
    "Hand warmers",
];

const STATUS_NOTES = {
    pending_payment: "Your place is held for you. Pay before the deadline or it goes to the next person on the waiting list.",
    confirmed: "You are paid and confirmed. See you on the slopes!",
    waitlisted: "The trip is full right now. If a place frees up it is offered to the waiting list in order, and you will have 48 hours to pay.",
    cancelled: "This registration is cancelled. Ask your organiser if you would like to sign up again.",
};

let timer;

onSubmit(document.getElementById("find-trip"), async (values) => {
    const { registration, trip } = await api(`${TRIPS}/my-trip`, values);
    const room = await api(`${ROOMS}/registrations/${registration.id}/room`);

    showTrip(registration, trip, room);
    return `Welcome back, ${registration.name}!`;
});

function showTrip(registration, trip, room) {
    document.getElementById("lookup").hidden = true;
    document.getElementById("my-trip").hidden = false;

    document.getElementById("greeting").textContent = `Hi ${registration.name}, you are going to`;
    document.getElementById("trip-title").textContent = `${trip.name} · ${trip.destination}`;
    document.getElementById("trip-dates").textContent = formatDates(trip.start_date, trip.end_date);

    const status = document.getElementById("status");
    status.textContent = statusLabel(registration.status);
    status.className = `pill ${registration.status}`;

    let note = STATUS_NOTES[registration.status];
    if (registration.status === "pending_payment") {
        const deadline = new Date(registration.payment_deadline).toLocaleString("en-GB", {
            weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit",
        });
        note += ` Deadline: ${deadline}.`;
    }
    document.getElementById("status-note").textContent = note;

    document.getElementById("room").innerHTML = room
        ? `<strong>${escapeHtml(room.name)}</strong><br>
           <span class="muted">${room.occupied > 1
               ? `Sharing with ${plural(room.occupied - 1, "other student")}`
               : "Just you so far"}, ${room.capacity} beds</span>`
        : `<span class="muted">No room yet. Your organiser shares out rooms once everyone has paid.</span>`;

    clearInterval(timer);
    countDown(trip);
    timer = setInterval(() => countDown(trip), 1000);

    showChecklist(registration.id);
}

function countDown(trip) {
    const start = new Date(trip.start_date + "T00:00");
    const end = new Date(trip.end_date + "T23:59:59");
    const now = new Date();
    const box = document.getElementById("countdown");
    const note = document.getElementById("countdown-note");

    if (now >= end) {
        box.innerHTML = "";
        note.textContent = "This trip is over. Hope the snow was good!";
        return;
    }
    if (now >= start) {
        box.innerHTML = "";
        note.textContent = "You are on the mountain right now. Enjoy every run!";
        return;
    }

    const seconds = Math.floor((start - now) / 1000);
    const parts = [
        [Math.floor(seconds / 86400), "days"],
        [Math.floor(seconds / 3600) % 24, "hours"],
        [Math.floor(seconds / 60) % 60, "minutes"],
        [seconds % 60, "seconds"],
    ];
    box.innerHTML = parts.map(([value, label]) =>
        `<div><strong>${value}</strong><span>${label}</span></div>`
    ).join("");
    note.textContent = "until the first lift.";
}

// Ticks are saved in localStorage under this student's registration, so
// they survive a page reload. Storage can be blocked (private windows), so
// every read and write is allowed to fail quietly.
function showChecklist(registrationId) {
    const key = `packing-${registrationId}`;
    let ticked = [];
    try {
        ticked = JSON.parse(localStorage.getItem(key)) || [];
    } catch {
        ticked = [];
    }

    const list = document.getElementById("checklist");
    list.innerHTML = PACKING_LIST.map((item) => `
        <li><label>
            <input type="checkbox" value="${item}" ${ticked.includes(item) ? "checked" : ""}>
            <span>${item}</span>
        </label></li>
    `).join("");

    const update = () => {
        ticked = [...list.querySelectorAll("input:checked")].map((box) => box.value);
        document.getElementById("packed").textContent =
            `${ticked.length} of ${PACKING_LIST.length} packed`;
        try {
            localStorage.setItem(key, JSON.stringify(ticked));
        } catch {
            // Nothing to do: the list still works, it just will not be remembered.
        }
    };

    list.addEventListener("change", update);
    update();
}
