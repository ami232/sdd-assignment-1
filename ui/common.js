// Helpers shared by every page.

// Base URLs of the two services, from config.js. The browser calls them
// directly; each service allows this page's origin through CORS.
const TRIPS = window.CONFIG.TRIPS_URL;
const ROOMS = window.CONFIG.ROOMS_URL;

// Call a service. With `data` it is a POST with a JSON body, otherwise a GET.
// If the service answers with an error, throw it so the page can show it.
async function api(url, data) {
    const options = data === undefined ? {} : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    };

    const response = await fetch(url, options);
    const result = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(result?.error || "Something went wrong, please try again");
    }
    return result;
}

// Run `action` with the form's values when it is submitted, and show its
// success message or the error the service sent back.
function onSubmit(form, action) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const values = Object.fromEntries(new FormData(form));
        try {
            const success = await action(values);
            form.reset();
            showMessage(success, "success");
        } catch (error) {
            showMessage(error.message, "error");
        }
    });
}

function showMessage(text, kind) {
    const box = document.getElementById("message");
    box.textContent = text;
    box.className = `message ${kind}`;
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "center" });
}

// Names and emails come from users, so escape them before putting them in HTML.
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function plural(count, word) {
    return `${count} ${word}${count === 1 ? "" : "s"}`;
}

// "2027-01-20" and "2027-01-24" become "20 – 24 Jan 2027".
function formatDates(start, end) {
    const options = { day: "numeric", month: "short", year: "numeric" };
    const startDate = new Date(start + "T00:00");
    const endDate = new Date(end + "T00:00");

    if (startDate.getMonth() === endDate.getMonth()) {
        return `${startDate.getDate()} – ${endDate.toLocaleDateString("en-GB", options)}`;
    }
    return `${startDate.toLocaleDateString("en-GB", options)} – ${endDate.toLocaleDateString("en-GB", options)}`;
}

function statusLabel(status) {
    return status.replace("_", " ");
}

// Light snow over every page: small white dots with a random size, speed,
// starting point and sideways drift. A negative delay means some flakes are
// already halfway down when the page opens.
function letItSnow() {
    const snow = document.createElement("div");
    snow.className = "snow";

    for (let i = 0; i < 40; i++) {
        const flake = document.createElement("span");
        const size = 2 + Math.random() * 4;
        flake.className = "flake";
        flake.style.width = `${size}px`;
        flake.style.height = `${size}px`;
        flake.style.left = `${Math.random() * 100}%`;
        flake.style.opacity = 0.5 + Math.random() * 0.5;
        flake.style.animationDuration = `${10 + Math.random() * 12}s`;
        flake.style.animationDelay = `${-Math.random() * 20}s`;
        flake.style.setProperty("--drift", `${Math.random() * 80 - 40}px`);
        snow.append(flake);
    }

    document.body.append(snow);
}

letItSnow();
