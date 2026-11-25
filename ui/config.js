// Where the two services are. These are the compose ports for running
// locally; the deploy pipeline overwrites this file with the services'
// Azure URLs before uploading the UI, so no address is hardcoded elsewhere.
window.CONFIG = {
    TRIPS_URL: "http://localhost:8001",
    ROOMS_URL: "http://localhost:8002",
};
